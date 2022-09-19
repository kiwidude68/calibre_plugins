#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~

__license__ = 'GPL v3'
__copyright__ = '2020, Ahmed Zaki <azaki00.dev@gmail.com>'


from collections import defaultdict
from functools import partial
import time

from calibre import prints
from calibre.constants import DEBUG

from calibre_plugins.find_duplicates.duplicates import DuplicateFinder, CrossLibraryDuplicateFinder
from calibre_plugins.find_duplicates.book_algorithms import AlgorithmBase
from calibre_plugins.find_duplicates.dialogs import SummaryMessageBox
from calibre_plugins.find_duplicates.advanced.match_rules import HashBuilder
from calibre_plugins.find_duplicates.variation_algorithms import VariationAlgorithm
from calibre_plugins.find_duplicates.advanced.gui.sort import get_sort_value
from calibre_plugins.find_duplicates.advanced.common import column_metadata

try:
    load_translations()
except NameError:
    pass

class AdvancedAlgorithm(AlgorithmBase):
    def __init__(self, gui, db, match_rules, exemptions_map, sort_filters=[]):
        AlgorithmBase.__init__(self, gui, db, exemptions_map)
        self.match_rules = match_rules
        algorithms = gui.iactions['Find Duplicates'].algorithms
        self.hash_builder = HashBuilder(self.gui, algorithms, self.match_rules)
        self.sort_filters = sort_filters or [{'field': 'authors', 'is_reversed':False},{'field': 'title', 'is_reversed':False}]

    def find_candidates(self, book_ids, include_languages=False):
        '''
        Default implementation will iterate across the book ids to consider
        and call find_candidate. Return a dictionary of candidates.
        '''
        candidates_map = defaultdict(set)
        # initialize dict to be persistent for all books
        data = {}
        for book_id in book_ids:
            self.find_candidate(book_id, candidates_map, include_languages=include_languages, data=data)
        return candidates_map

    def find_candidate(self, book_id, candidates_map, include_languages=False, data={}):

        mi = self.db.new_api.get_proxy_metadata(book_id)

        all_hashes = self.hash_builder.from_book_metadata(mi, data=data)

        for hash_ in all_hashes:
            # empty hashes are not allowed. they can match thousands of books and hog the system
            # especially in cross library compare.
            if hash_:
                candidates_map[hash_].add(book_id)

    def convert_candidates_to_groups(self, candidates_map):
        books_for_group_map, groups_for_book_map = AlgorithmBase.convert_candidates_to_groups(self, candidates_map)
        # Update: sort filters {
        books_for_group_map = self.sort_books_for_group(books_for_group_map, groups_for_book_map)
        # }        
        return books_for_group_map, groups_for_book_map

    def sort_books_for_group(self, books_for_group_map, groups_for_book_map):
        book_ids = groups_for_book_map.keys()
        for group_id, group in books_for_group_map.items():
            # python sort is stable, so we loop in reverse to apply from lowest to highest sort filters
            for sort_filter in reversed(self.sort_filters):
                sort_field = sort_filter['field']
                is_reversed = sort_filter['is_reversed']
                template_type = sort_filter.get('template_type')
                sort_function = partial(get_sort_value, self.db, sort_field, template_type)
                group.sort(key=lambda x: sort_function(x), reverse=is_reversed)
            books_for_group_map[group_id] = group
        return books_for_group_map

class AdvancedDuplicateFinder(DuplicateFinder):

    # Update: add extra marks
    FIRST_DUPLICATE_MARK = 'first_duplicate'
    LAST_DUPLICATE_MARK = 'last_duplicate'
    GROUP_SORT_MARK = '_sort_'
    DELETED_BINARY_MARK = 'deleted_binary_duplicate'
    ENTANGLED_GROUP_MARK = 'entangled_group'
    ENTANGLED_BOOK_MARK = 'entangled_book'
    #}

    def clear_duplicates_mode(self, clear_search=True, reapply_restriction=True):
        self.deleted_binary_duplicates = []
        DuplicateFinder.clear_duplicates_mode(self, clear_search, reapply_restriction)

    def run_book_duplicates_check_advanced(
        self,
        match_rules,
        sort_groups_by_title,
        show_all_duplicates_mode,
        sort_filters,
        description=_('Advanced algorithm'),
        exemptions_type='book'):
        '''
        Execute a duplicates search using the specified algorithm and display results
        '''
        self.advanced_mode = True
        self.sort_filters = sort_filters
        
        if not self.is_showing_duplicate_exemptions() and not self.has_results():
            # We are in a safe state to preserve the users current restriction/highlighting
            self._persist_gui_state()
        self.clear_duplicates_mode()

        self._is_show_all_duplicates_mode = show_all_duplicates_mode
        
        exemptions_map = self._book_exemptions_map
        if exemptions_type == 'author':
            exemptions_map = self._author_exemptions_map
          
        algorithm = AdvancedAlgorithm(self.gui, self.db, match_rules, exemptions_map, sort_filters)
        self._algorithm_text = description
        self._duplicate_search_mode = algorithm.duplicate_search_mode()

        bfg_map, gfb_map = algorithm.run_duplicate_check(sort_groups_by_title)

        self._display_run_duplicate_results(bfg_map, gfb_map)

    # udpate: entangled_books
    def _get_entangled_gooks_and_groups(self):
        '''
        entangled books: books that are part of more than one group
        entangled groups: groups that have one or more entangled books
        '''
        entangled_books = set()
        entangled_groups = set()
        
        if self._groups_for_book_map:
            for book_id, groups in self._groups_for_book_map.items():
                if len(groups) > 1:
                    entangled_books.add(book_id)
        
        if entangled_books and self._books_for_group_map:
            for group_id, group in self._books_for_group_map.items():
                if set(group).intersection(set(entangled_books)) != set():
                    entangled_groups.add(group_id)
        
        return entangled_books, entangled_groups
    #}

    def _update_marked_books(self, mark_author_exemptions=False):
        '''
        Mark the books using the special 'marked' temp column in Calibre
        Note that we need to store multiple types of marked books at once
        The first is marking all of the duplicate groups
        The second is all duplicate book ids, marked with 'duplicates'
        The third is exemptions marked as 'not_book_duplicate' or 'not_author_duplicate'

        This will allow us to apply a search restriction of 'marked:duplicates'
        at the same time as doing a search of 'marked:xxx' for our subset,
        while also allowing the user to refresh to get updated results

        The only limitation is making sure that we don't overlap the sets by
        using the same substrings like 'duplicates' in the value of marked_text.
        '''
        # update: 
        entangled_books, entangled_groups = self._get_entangled_gooks_and_groups()
        #
        marked_ids = dict()
        # Build our dictionary of current marked duplicate groups
        if self._books_for_group_map:
            remaining_group_ids = list(sorted(self._books_for_group_map.keys()))
            for group_id in remaining_group_ids:
                marked_text = '%s%04d' % (self.DUPLICATE_GROUP_MARK, group_id)
                for idx, book_id in enumerate(self._books_for_group_map[group_id], 1):
                    # Update: add sort to books inside group {
                    if self.advanced_mode:
                        book_marked_text = '%s%s%04d' % (marked_text, self.GROUP_SORT_MARK, idx)
                        if idx == len(self._books_for_group_map[group_id]):
                            book_marked_text = '{},{}'.format(book_marked_text, self.LAST_DUPLICATE_MARK)
                        if idx == 1:
                            book_marked_text = '{},{}'.format(book_marked_text, self.FIRST_DUPLICATE_MARK)
                        if group_id in entangled_groups:
                            book_marked_text = '{},{}'.format(book_marked_text, self.ENTANGLED_GROUP_MARK)
                            if book_id in entangled_books:
                                book_marked_text = '{},{}'.format(book_marked_text, self.ENTANGLED_BOOK_MARK)
                    # }
                    else:
                        book_marked_text = marked_text
                    # }
                    if book_id not in marked_ids:
                        marked_ids[book_id] = book_marked_text
                    else:
                        marked_ids[book_id] = '%s,%s' % (marked_ids[book_id], book_marked_text)

        # Now add the marks to indicate each book that is in a duplicate group
        if self._groups_for_book_map:
            for book_id in list(self._groups_for_book_map.keys()):
                if book_id not in marked_ids:
                    marked_ids[book_id] = self.DUPLICATES_MARK
                else:
                    # We need to store two bits of text in the one value
                    marked_ids[book_id] = '%s,%s' % (marked_ids[book_id], self.DUPLICATES_MARK)

        # Add the marks for author duplicate exemptions. This is an expensive operation so
        # we only do it when we really have to (i.e. user is showing author exemptions)
        if mark_author_exemptions:
            if self._author_exemptions_map:
                # Rebuild the map of authors to books
                books_for_author_map = self._create_books_for_author_map()
                for author in list(self._author_exemptions_map.keys()):
                    if author in books_for_author_map:
                        for book_id in books_for_author_map[author]:
                            if book_id not in marked_ids:
                                marked_ids[book_id] = self.AUTHOR_EXEMPTION_MARK
                            else:
                                # We need to store two bits of text in the one value
                                marked_ids[book_id] = '%s,%s' % (marked_ids[book_id],
                                                                 self.AUTHOR_EXEMPTION_MARK)
        else:
            # Add the marks for book duplicate exemptions
            if self._book_exemptions_map:
                for book_id in list(self._book_exemptions_map.keys()):
                    if book_id not in marked_ids:
                        marked_ids[book_id] = self.BOOK_EXEMPTION_MARK
                    else:
                        # We need to store two bits of text in the one value
                        marked_ids[book_id] = '%s,%s' % (marked_ids[book_id], self.BOOK_EXEMPTION_MARK)

        # Update: mark deleted binaries {
        if self.deleted_binary_duplicates:
            for book_id in self.deleted_binary_duplicates:
                marked_ids[book_id] = '%s,%s' % (marked_ids[book_id], self.DELETED_BINARY_MARK)
        #}

        # Assign the results to our database
        self.gui.current_db.set_marked_ids(marked_ids)

    def _delete_binary_duplicate_formats(self, books_for_group_map):      
        if DEBUG:
            prints('Automatically removing binary format duplicates')

        hash_map = self.db.get_all_custom_book_data('find_duplicates', default={})
        for books_list in list(books_for_group_map.values()):
            # Determine the oldest book format in this group
            earliest_book_id = books_list[0]
            earliest_date = self.db.timestamp(earliest_book_id, index_is_id=True)
            for idx in list(range(1, len(books_list))):
                book_date = self.db.timestamp(books_list[idx], index_is_id=True)
                if book_date < earliest_date:
                    earliest_book_id = books_list[idx]
                    earliest_date = book_date
            other_book_ids = [book_id for book_id in books_list if book_id != earliest_book_id]

            book_map = hash_map[earliest_book_id]
            # Now iterate through the formats for this oldest book
            for fmt, info in list(book_map.items()):
                for other_book_id in other_book_ids:
                    other_book_map = hash_map[other_book_id]
                    if fmt not in other_book_map:
                        continue
                    other_info = other_book_map[fmt]
                    if info['size'] == other_info['size'] and info['sha'] == other_info['sha']:
                        if DEBUG:
                            prints('Removing duplicate format: %s from book: %d'%(fmt, other_book_id))
                        self.db.remove_format(other_book_id, fmt, index_is_id=True, notify=False)
                        # Update: mark entries whose duplicate format is deleted automatically during binary compare {
                        self.deleted_binary_duplicates.append(other_book_id)
                        #}

class AdvancedCrossLibraryDuplicateFinder(CrossLibraryDuplicateFinder):
    def run_library_duplicates_check(self, library_path, match_rules):
        self.library_path = library_path
        self.match_rules = match_rules
        from calibre.library import db as DB
        self.target_db = DB(self.library_path, read_only=True)

        # We will re-use the elements of the same basic algorithm code, but
        # only by calling specific functions to control what gets executed
        # since the approach for comparing all books in one library with another
        # significantly differs. Also of course book exemptions will not apply.

        message = self._do_comparison()

        self.gui.status_bar.showMessage('Duplicate search completed', 3000)
        txt = self.log.plain_text
        if txt:
            txt = _('Results of {0} comparison:\n    Source library: {1}\n    Target library: {2}\n\n{3}').format(
                    self.algorithm_text, self.db.library_path, self.library_path, txt)
        d = SummaryMessageBox(self.gui, 'Library Duplicates', message, det_msg=txt)
        d.exec_()

    def _do_comparison(self):
        '''
        When analysing the current database, we do not want to hash every book with
        every other book in this database. Instead we want to determine the hash
        and then compare it with the hashes we have from the other database.
        So we will not be reporting duplicates within this database, only duplicates
        from each individual book in this database with the target database.
        '''
        algorithm = AdvancedAlgorithm(self.gui, self.db, self.match_rules, exemptions_map=None)
        self.algorithm_text = 'Advanced Algorithm'
        duplicates_count = 0
        duplicate_book_ids = None

        duplicates_count, duplicate_book_ids, msg = self._do_advanced_comparison(algorithm)

        if duplicates_count > 0:
            msg += "<br/><br/>" + _("Click 'Show details' to see the results.")
            if duplicate_book_ids is not None:
                marked_ids = {}
                for book_id in duplicate_book_ids:
                    marked_ids[book_id] = 'library_duplicate'
                self.gui.current_db.set_marked_ids(marked_ids)
                self.gui.search.set_search_string('marked:library_duplicate')
        return msg

    def _do_advanced_comparison(self, algorithm):
        self.gui.status_bar.showMessage(_('Analysing duplicates in target database')+'...', 0)
        target_candidates_map, author_bookids_map_unused = self._analyse_target_database()

        # Use the standard approach to get current library book ids for consideration
        book_ids = algorithm.get_book_ids_to_consider()
        duplicate_book_ids = []

        self.gui.status_bar.showMessage(_('Analysing duplicates in current database')+'...', 0)
        # Iterate through these books getting our hashes

        # initialize dict to be persistent for all books        
        data = {}
        
        for book_id in book_ids:
            # We will create a temporary candidates map for each book, since we are
            # not interested in hashing the current library's books together. And we
            # can't give it the map from the target database, because we won't know
            # which database each group's ids belong to!
            book_candidates_map = defaultdict(set)
            algorithm.find_candidate(book_id, book_candidates_map, include_languages=False, data=data)
            # We now have any hash(s) for the current book in our candidates map.
            # See if we have them in our target library map too to indicate a duplicate
            duplicate_books = set()
            for book_hash in book_candidates_map:
                if book_hash in target_candidates_map:
                    duplicate_books |= target_candidates_map[book_hash]
            if len(duplicate_books) > 0:
                duplicate_book_ids.append(book_id)
                self.log('Book in this library: %s'%self._get_book_display_info(self.db, book_id, include_identifier=False))
                dups = [self._get_book_display_info(self.target_db, dup_book_id)
                        for dup_book_id in duplicate_books]
                for dup_text in sorted(dups):
                    self.log('   Target library: %s'%dup_text)
                self.log('')

        msg = _('Found <b>{0} books</b> with potential duplicates using <b>{1}</b> against the library at: {2}').format(len(duplicate_book_ids), self.algorithm_text, self.library_path)
        return len(duplicate_book_ids), duplicate_book_ids, msg

    def _analyse_target_database(self):
        '''
        Get the candidates using algorithm against the target database.
        Similar to a regular duplicate check except that:
        (a) it applies to a different database
        (b) it will not apply restrictions (all_ids, not model ids)
        (c) we do *not* want to shrink the candidates map as we must use it to
            "add" candidates from *this* database too.
        '''
        algorithm = AdvancedAlgorithm(self.gui, self.target_db, self.match_rules, exemptions_map=None)
        self.algorithm_text = 'Advanced Algorithm'

        book_ids = self.target_db.all_ids()

        target_candidates_map = algorithm.find_candidates(book_ids, include_languages=False)
        author_bookids_map = None
        # Bit of a bodge. If we are running an author only comparison, we want
        # the additional map that algorithm creates listing the books per author
        # in order to display that information in the log results.
        if hasattr(algorithm, 'author_bookids_map'):
            author_bookids_map = algorithm.author_bookids_map
        return target_candidates_map, author_bookids_map

class AdvancedVariationAlgorithm(VariationAlgorithm):

    def __init__(self, db, gui):
        VariationAlgorithm.__init__(self, db)
        self.gui = gui

    def run_variation_check(self, match_rules):
        '''
        The entry point for running the algorithm
        '''
        
        item_type = match_rules[0]['field']
        
        data_map = self._get_items_to_consider(item_type)

        algorithms = self.gui.iactions['Find Duplicates'].algorithms
        hash_builder = HashBuilder(self.gui, algorithms, match_rules)

        data = {}        
        self.fn = partial(hash_builder.from_category_item, data)
        start = time.time()

        # Get our map of potential duplicate candidates
        if DEBUG:
            prints('Find Duplicates: Analysing %d %s for duplicates...' % (len(data_map), item_type))
        candidates_map = self._find_candidates(data_map)

        # Convert our dictionary of potential candidates into a map by
        # item id that has flattened the results out.
        matches_for_item_map = self._flatten_candidates_for_item(candidates_map, data_map)

        # Now lookup how many books there are for each candidate
        count_map = self._get_counts_for_candidates(matches_for_item_map, item_type)

        if DEBUG:
            prints('Find Duplicates: Completed duplicate analysis in:', time.time() - start)
            prints('Find Duplicates: Found %d duplicate groups'%(len(matches_for_item_map),))

        return data_map, count_map, matches_for_item_map

    def _get_items_to_consider(self, item_type):
        '''
        Return a map of id:text appropriate to the item being analysed
        '''
        if item_type == 'authors':
            results = self.db.get_authors_with_ids()
            results = [(a[0], a[1].replace('|',',')) for a in results]
        elif item_type == 'series':
            results = self.db.get_series_with_ids()
        elif item_type == 'publisher':
            results = self.db.get_publishers_with_ids()
        elif item_type == 'tags':
            results = self.db.get_tags_with_ids()
        else:
            #raise Exception('Unknown item type:', item_type)
            # Update: add custom column to metadata variations {
            results = self.db.get_custom_items_with_ids(column_metadata(self.db, item_type)['label'])
            #}
        return dict((x[0],x[1]) for x in results)
