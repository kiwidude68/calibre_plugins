from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import time, traceback
from collections import OrderedDict, defaultdict

try:
    from qt.core import QModelIndex
except ImportError:
    from PyQt5.Qt import QModelIndex

from calibre import prints
from calibre.constants import DEBUG

from calibre_plugins.find_duplicates.matching import (authors_to_list, similar_title_match,
                                get_author_algorithm_fn, get_title_algorithm_fn)

try:
    load_translations()
except NameError:
    pass

DUPLICATE_SEARCH_FOR_BOOK = 'BOOK'
DUPLICATE_SEARCH_FOR_AUTHOR = 'AUTHOR'

# --------------------------------------------------------------
#             Find Duplicate Book Algorithm Classes
# --------------------------------------------------------------

class AlgorithmBase(object):
    '''
    All duplicate search algorithms should inherit from this class
    '''
    def __init__(self, gui, db, exemptions_map):
        self.gui = gui
        self.db = db
        self.model = self.gui.library_view.model()
        self._exemptions_map = exemptions_map

    def duplicate_search_mode(self):
        return DUPLICATE_SEARCH_FOR_BOOK

    def run_duplicate_check(self, sort_groups_by_title=True, include_languages=False):
        '''
        The entry point for running the algorithm
        '''
        book_ids = self.get_book_ids_to_consider()
        start = time.time()

        # Get our map of potential duplicate candidates
        self.gui.status_bar.showMessage(_('Analysing {0} books for duplicates').format(len(book_ids)))
        candidates_map = self.find_candidates(book_ids, include_languages)

        # Perform a quick pass through removing all groups with < 2 members
        self.shrink_candidates_map(candidates_map)

        # Now ask for these candidate groups to be ordered so that our numbered
        # groups will have some kind of consistent order to them.
        candidates_map = self.sort_candidate_groups(candidates_map, sort_groups_by_title)

        # Convert our dictionary of potential candidates into sets of more than one
        books_for_groups_map, groups_for_book_map = self.convert_candidates_to_groups(candidates_map)
        if DEBUG:
            prints('Completed duplicate analysis in:', time.time() - start)
            prints('Found %d duplicate groups covering %d books'%(len(books_for_groups_map),
                                                                   len(groups_for_book_map)))
        return books_for_groups_map, groups_for_book_map

    def get_book_ids_to_consider(self):
        '''
        Default implementation will iterate over the current subset of books
        in our current library model
        '''
        rows = list(range(self.model.rowCount(QModelIndex())))
        book_ids = list(map(self.model.id, rows))
        return book_ids

    def find_candidates(self, book_ids, include_languages=False):
        '''
        Default implementation will iterate across the book ids to consider
        and call find_candidate. Return a dictionary of candidates.
        '''
        candidates_map = defaultdict(set)
        for book_id in book_ids:
            self.find_candidate(book_id, candidates_map, include_languages)
        return candidates_map

    def find_candidate(self, book_id, candidates_map, include_languages=False):
        '''
        Derived classes must provide an implementation
        '''
        pass

    def shrink_candidates_map(self, candidates_map):
        for key in list(candidates_map.keys()):
            if len(candidates_map[key]) < 2:
                del candidates_map[key]

    def convert_candidates_to_groups(self, candidates_map):
        '''
        Given a dictionary keyed by some sort of common duplicate group
        key (like a fuzzy of title/author) remove all of the groups that
        have less than two members, repartition as required for any
        duplicate exemptions and return as a tuple of:
          (books_for_group_map, groups_for_book_map)
        books_for_group_map - for each group id, contains a list of book ids
        groups_for_book_map - for each book id, contains a list of group ids
        '''
        books_for_group_map = dict()
        groups_for_book_map = defaultdict(set)
        group_id = 0
        # Convert our map of groups into a list of sets with any duplicate groups removed
        candidates_list = self.clean_dup_groups(candidates_map)
        for book_ids in candidates_list:
            partition_groups = self.partition_using_exemptions(book_ids)
            for partition_group in partition_groups:
                if len(partition_group) > 1:
                    group_id += 1
                    partition_book_ids = self.get_book_ids_for_candidate_group(partition_group)
                    books_for_group_map[group_id] = partition_book_ids
                    for book_id in partition_book_ids:
                        groups_for_book_map[book_id].add(group_id)
        return books_for_group_map, groups_for_book_map

    def clean_dup_groups(self, candidates_map):
        '''
        Given a dictionary of sets, convert into a list of sets removing any sets
        that are subsets of other sets.
        '''
        res = [set(d) for d in list(candidates_map.values())]
        res.sort(key=lambda x: len(x))
        candidates_list = []
        for i,a in enumerate(res):
            for b in res[i+1:]:
                if a.issubset(b):
                    break
            else:
                candidates_list.append(a)
        return candidates_list

    def get_book_ids_for_candidate_group(self, candidate_group):
        '''
        Return the book ids representing this candidate group
        Default implementation is given a book ids so just return them
        '''
        return candidate_group

    def sort_candidate_groups(self, candidates_map, by_title=True):
        '''
        Responsible for returning an ordered dict of how to order the groups
        Default implementation will just sort by the fuzzy key of our candidates
        '''
        if by_title:
            skeys = sorted(candidates_map.keys())
        else:
            skeys = sorted(list(candidates_map.keys()),
                       key=lambda ckey: '%04d%s' % (len(candidates_map[ckey]), ckey),
                       reverse=True)
        return OrderedDict([(key, candidates_map[key]) for key in skeys])

    def partition_using_exemptions(self, data_items):
        '''
        Given a set of data items, see if any of these combinations should
        be excluded due to being marked as not duplicates of each other
        If we find items that should not appear together, then we will
        repartition into multiple groups. Returns a list where each item
        is a sublist containing the data items for that partitioned group.
        '''
        data_items = sorted(data_items)
        # Initial condition -- the group contains 1 set of all elements
        results = [set(data_items)]
        partitioning_ids = [None]
        # Loop through the set of duplicates, checking to see if the entry is in a non-dup set
        for one_dup in data_items:
            if one_dup in self._exemptions_map:
                ndm_entry = self._exemptions_map.merge_sets(one_dup)
                # The entry is indeed in a non-dup set. We may need to partition
                for i,res in enumerate(results):
                    if one_dup in res:
                        # This result group contains the item with a non-dup set. If the item
                        # was the one that caused this result group to partition in the first place,
                        # then we must not partition again or we will make subsets of the group
                        # that split this partition off. Consider a group of (1,2,3,4) and
                        # non-dups of [(1,2), (2,3)]. The first partition will give us (1,3,4)
                        # and (2,3,4). Later when we discover (2,3), if we partition (2,3,4)
                        # again, we will end up with (2,4) and (3,4), but (3,4) is a subset
                        # of (1,3,4). All we need to do is remove 3 from the (2,3,4) partition.
                        if one_dup == partitioning_ids[i]:
                            results[i] = (res - ndm_entry) | set([one_dup])
                            continue
                        # Must partition. We already have one partition, the one in our hand.
                        # Remove the dups from it, then create new partitions for each of the dups.
                        results[i] = (res - ndm_entry) | set([one_dup])
                        for nd in ndm_entry:
                            # Only partition if the duplicate is larger than the one we are looking
                            # at. This is necessary because the non-dup set map is complete,
                            # map[2] == (2,3), and map[3] == (2,3). We know that when processing
                            # the set for 3, we have already done the work for the element 2.
                            if nd > one_dup and nd in res:
                                results.append((res - ndm_entry - set([one_dup])) | set([nd]))
                                partitioning_ids.append(nd)
        sr = []
        for r in results:
            if len(r) > 1:
                sr.append(sorted(list(r)))
        sr.sort()
        return sr


class IdentifierAlgorithm(AlgorithmBase):
    '''
    This algorithm simply finds books that have duplicate identifier values
    '''
    def __init__(self, gui, db, exemptions_map, identifier_type='isbn'):
        AlgorithmBase.__init__(self, gui, db, exemptions_map)
        self.identifier_type = identifier_type

    def get_book_ids_to_consider(self):
        '''
        Override base function as we will only consider books that have an identifier
        rather than every book in the library.
        '''
        return self.db.data.search_getting_ids('identifier:'+self.identifier_type+':True', self.db.data.search_restriction)

    def find_candidate(self, book_id, candidates_map, include_languages=False):
        identifiers = self.db.get_identifiers(book_id, index_is_id=True)
        identifier = identifiers.get(self.identifier_type, '')
        if identifier:
            candidates_map[identifier].add(book_id)

    def sort_candidate_groups(self, candidates_map, by_title=True):
        '''
        Responsible for returning an ordered dict of how to order the groups
        Override to just do a fuzzy title sort to give a better sort than by identifier
        '''
        title_map = {}
        for key in list(candidates_map.keys()):
            book_id = list(candidates_map[key])[0]
            title_map[key] = similar_title_match(self.db.title(book_id, index_is_id=True))
        if by_title:
            skeys = sorted(list(candidates_map.keys()), key=lambda identifier: title_map[identifier])
        else:
            skeys = sorted(list(candidates_map.keys()),
                       key=lambda identifier: '%04d%s' % (len(candidates_map[identifier]), identifier),
                       reverse=True)
        return OrderedDict([(identifier, candidates_map[identifier]) for identifier in skeys])


class BinaryCompareAlgorithm(IdentifierAlgorithm):
    '''
    This algorithm simply finds books that have binary duplicates of their format files
    Inheriting from IdentifierAlgorithm only to reuse the sort_candidate_groups override
    '''
    def get_book_ids_to_consider(self):
        '''
        Override base function as we will only consider books that have a format
        rather than every book in the library.
        '''
        return self.db.data.search_getting_ids('formats:True', self.db.data.search_restriction)

    def find_candidates(self, book_ids, include_languages=False):
        '''
        Override the default implementation so we can do multiple passes as a more
        efficient approach to finding binary duplicates.
        '''
        # Our first pass will be to find all books that have an identical file size
        candidates_size_map = defaultdict(set)
        formats_count = 0
        for book_id in book_ids:
            formats_count += self._find_candidate_by_file_size(book_id, candidates_size_map)

        # Perform a quick pass through removing all groups with < 2 members
        self.shrink_candidates_map(candidates_size_map)
        if DEBUG:
            prints('Pass 1: %d formats created %d size collisions' % (formats_count, len(candidates_size_map)))

        # Our final pass is to build our result set for this function
        candidates_map = defaultdict(set)
        hash_map = self.db.get_all_custom_book_data('find_duplicates', default={})
        result_hash_map = {}
        for size, size_group in list(candidates_size_map.items()):
            for book_id, fmt, mtime in size_group:
                self._find_candidate_by_hash(book_id, fmt, mtime, size, candidates_map, hash_map, result_hash_map)
        self.db.add_multiple_custom_book_data('find_duplicates', result_hash_map)
        return candidates_map

    def _find_candidate_by_file_size(self, book_id, candidates_map):
        formats = self.db.formats(book_id, index_is_id=True, verify_formats=False)
        count = 0
        for fmt in formats.split(','):
            try:
                stat_metadata = self.db.format_metadata(book_id, fmt)
                mtime = stat_metadata['mtime']
                size = stat_metadata['size']
                candidates_map[size].add((book_id, fmt, mtime))
                count += 1
            except:
                traceback.print_exc()
        return count

    def _add_to_hash_map(self, hash_map, book_id, fmt, book_data):
        if book_id not in hash_map:
            hash_map[book_id] = {}
        hash_map[book_id][fmt] = book_data

    def _find_candidate_by_hash(self, book_id, fmt, mtime, size, candidates_map, hash_map, result_hash_map):
        # Work out whether we need to calculate a hash for this file from
        # book plugin data from a previous run
        book_data = hash_map.get(book_id, {}).get(fmt, {})
        if book_data.get('mtime', None) == mtime:
            sha = book_data.get('sha', None)
            size = book_data.get('size', None)
            if sha and size:
                candidates_map[(sha, size)].add(book_id)
                self._add_to_hash_map(result_hash_map, book_id, fmt, book_data)
                return
        try:
            format_hash = self.db.format_hash(book_id, fmt)
            hash_key = (format_hash, size)
            candidates_map[hash_key].add(book_id)
            # Store our plugin book data for future repeat scanning
            book_data['mtime'] = mtime
            book_data['sha'] = format_hash
            book_data['size'] = size
            self._add_to_hash_map(result_hash_map, book_id, fmt, book_data)
        except:
            traceback.print_exc()


class TitleAuthorAlgorithm(AlgorithmBase):
    '''
    This algorithm is used for all the permutations requiring
    some evaluation of book titles and an optional author evaluation
    '''
    def __init__(self, gui, db, book_exemptions_map, title_eval, author_eval):
        AlgorithmBase.__init__(self, gui, db, exemptions_map=book_exemptions_map)
        self._title_eval = title_eval
        self._author_eval = author_eval

    def find_candidate(self, book_id, candidates_map, include_languages=False):
        lang = None
        if include_languages:
            lang = self.db.languages(book_id, index_is_id=True)
        title_hash = self._title_eval(self.db.title(book_id, index_is_id=True), lang)
        if self._author_eval:
            authors = authors_to_list(self.db, book_id)
            if authors:
                for author in authors:
                    author_hash, rev_author_hash = self._author_eval(author)
                    candidates_map[title_hash+author_hash].add(book_id)
                    if rev_author_hash and rev_author_hash != author_hash:
                        candidates_map[title_hash+rev_author_hash].add(book_id)
                return
        candidates_map[title_hash].add(book_id)


class AuthorOnlyAlgorithm(AlgorithmBase):
    '''
    This algorithm is used for all the permutations requiring
    some evaluation of authors without considering the book titles.
    '''
    def __init__(self, gui, db, author_exemptions_map, author_eval):
        AlgorithmBase.__init__(self, gui, db, exemptions_map=author_exemptions_map)
        self._author_eval = author_eval
        self.author_bookids_map = defaultdict(set)

    def duplicate_search_mode(self):
        return DUPLICATE_SEARCH_FOR_AUTHOR

    def find_candidate(self, book_id, candidates_map, include_languages=False):
        '''
        Override the base implementation because it differs in several ways:
        - Our candidates map contains authors per key, not book ids
        - Our exclusions are per author rather than per book
        '''
        authors = authors_to_list(self.db, book_id)
        if not authors:
            # A book with no authors will not be considered
            return
        for author in authors:
            self.find_author_candidate(author, candidates_map, book_id)

    def find_author_candidate(self, author, candidates_map, book_id=None):
        '''
        Split into a separate method (making book id optional) for the purposes
        of re-use by the cross library duplicates comparison logic
        '''
        author_hash, rev_author_hash = self._author_eval(author)
        if book_id:
            self.author_bookids_map[author].add(book_id)
        candidates_map[author_hash].add(author)
        if rev_author_hash and rev_author_hash != author_hash:
            candidates_map[rev_author_hash].add(author)

    def get_book_ids_for_candidate_group(self, candidate_group):
        '''
        Override as our candidate group contains a list of authors
        We need to lookup the book ids for each author to build our set
        '''
        book_ids = set()
        for author in candidate_group:
            book_ids |= self.author_bookids_map[author]
        return sorted(list(book_ids))


# --------------------------------------------------------------
#           Find Duplicates Book Algorithm Factory
# --------------------------------------------------------------


def create_algorithm(gui, db, search_type, identifier_type, title_match, author_match, bex_map, aex_map):
    '''
    Our factory responsible for returning the appropriate algorithm
    based on the permutation of title/author matching desired.
    Returns a tuple of the algorithm and a summary description
    '''
    if search_type == 'identifier':
        display_identifier = identifier_type if len(identifier_type) <+ 50 else identifier_type[0:47]+'...'
        return IdentifierAlgorithm(gui, db, bex_map, identifier_type), \
                    _("matching '{0}' identifier").format(display_identifier)
    elif search_type == 'binary':
        return BinaryCompareAlgorithm(gui, db, bex_map), \
                    _('binary compare')
    else:
        author_fn = get_author_algorithm_fn(author_match)
        if title_match == 'ignore':
            return AuthorOnlyAlgorithm(gui, db, aex_map, author_fn), \
                   _('ignore title, {0} author').format(author_match)
        else:
            title_fn = get_title_algorithm_fn(title_match)
            return TitleAuthorAlgorithm(gui, db, bex_map, title_fn, author_fn), \
                   _('{0} title, {1} author').format(title_match, author_match)


