from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from collections import defaultdict, deque, OrderedDict

try:
    from qt.core import QApplication, Qt
except ImportError:
    from PyQt5.Qt import QApplication, Qt

from calibre import prints
from calibre.constants import DEBUG
from calibre.gui2 import config, info_dialog, error_dialog
from calibre.gui2.dialogs.confirm_delete import confirm
from calibre.utils.logging import GUILog
from calibre.utils.config import tweaks
from calibre.devices.usbms.driver import debug_print

import calibre_plugins.find_duplicates.config as cfg
from calibre_plugins.find_duplicates.book_algorithms import (create_algorithm,
                    DUPLICATE_SEARCH_FOR_BOOK, DUPLICATE_SEARCH_FOR_AUTHOR)
from calibre_plugins.find_duplicates.dialogs import SummaryMessageBox
from calibre_plugins.find_duplicates.matching import (authors_to_list, get_field_pairs,
                            set_title_soundex_length, set_author_soundex_length)


try:
    load_translations()
except NameError:
    pass


class ExemptionMap(defaultdict):
    '''
    Exemptions are stored as a list of lists (each inner list represents an exemption group)
    This wrapper class provides dictionary type access to that structure without the
    original cartesian based approach of storing each id with every other id.
    '''
    def __init__(self, exemptions_list):
        defaultdict.__init__(self, list)
        # Convert list of lists into a dictionary of lists for each member
        # So for a given member
        for group_list in exemptions_list:
            group_set = set(group_list)
            for member in group_list:
                self[member].append(group_set)
        # Retain our original list or lists for persistence purposes
        self.exemptions_list = exemptions_list

    def merge_sets(self, key):
        list_of_sets = self.get(key, [])
        if len(list_of_sets) == 0:
            return set()
        if len(list_of_sets) == 1:
            return list_of_sets[0] - set([key])
        return set().union(*list_of_sets) - set([key])


class DuplicateFinder(object):
    '''
    Responsible for executing a duplicates search and navigating the results
    '''
    DUPLICATES_MARK = 'duplicates'
    BOOK_EXEMPTION_MARK = 'not_book_duplicate'
    AUTHOR_EXEMPTION_MARK = 'not_author_duplicate'
    DUPLICATE_GROUP_MARK = 'duplicate_group_'

    def __init__(self, gui):
        self.gui = gui
        self.db = gui.library_view.model().db
        self._ignore_clear_signal = False
        book_exemptions, author_exemptions = cfg.get_exemption_lists(self.db)
        self._book_exemptions_map = ExemptionMap(book_exemptions)
        self._author_exemptions_map = ExemptionMap(author_exemptions)
        self._is_showing_duplicate_exemptions = False
        self._books_for_group_map = None
        self._groups_for_book_map = None
        self._persist_gui_state()
        self.clear_duplicates_mode()

    def is_valid_to_clear_search(self):
        return not self._ignore_clear_signal

    def clear_duplicates_mode(self, clear_search=True, reapply_restriction=True):
        '''
        We call this method when all duplicates have been resolved
        Reset the gui, clear the marked column data and all our duplicate state.
        '''
        if self.is_showing_duplicate_exemptions() or self.has_results():
            restore_sort = True
        else:
            restore_sort = False
        self._is_new_search = True
        self._is_showing_duplicate_exemptions = False
        self._is_show_all_duplicates_mode = False
        self._is_duplicate_exemptions_changed = False
        self._books_for_group_map = None
        self._groups_for_book_map = None
        self._authors_for_group_map = None
        self._is_group_changed = False
        self._group_ids_queue = None
        self._algorithm_text = None
        self._duplicate_search_mode = None
        self._current_group_id = None
        self._clear_all_book_marks()
        if clear_search:
            self.gui.search.clear()
        self._restore_previous_gui_state(reapply_restriction, restore_sort)

    def _clear_all_book_marks(self):
        marked_ids = dict()
        self.gui.current_db.set_marked_ids(marked_ids)

    def run_book_duplicates_check(self):
        '''
        Execute a duplicates search using the specified algorithm and display results
        '''
        
        if not self.is_showing_duplicate_exemptions() and not self.has_results():
            # We are in a safe state to preserve the users current restriction/highlighting
            self._persist_gui_state()
        self.clear_duplicates_mode()

        search_type = cfg.plugin_prefs.get(cfg.KEY_SEARCH_TYPE, 'titleauthor')
        identifier_type = cfg.plugin_prefs.get(cfg.KEY_IDENTIFIER_TYPE, 'isbn')
        title_match = cfg.plugin_prefs.get(cfg.KEY_TITLE_MATCH, 'identical')
        author_match  = cfg.plugin_prefs.get(cfg.KEY_AUTHOR_MATCH, 'identical')
        sort_groups_by_title = cfg.plugin_prefs.get(cfg.KEY_SORT_GROUPS_TITLE, True)
        title_soundex_length = cfg.plugin_prefs.get(cfg.KEY_TITLE_SOUNDEX, 6)
        author_soundex_length = cfg.plugin_prefs.get(cfg.KEY_AUTHOR_SOUNDEX, 8)
        set_title_soundex_length(title_soundex_length)
        set_author_soundex_length(author_soundex_length)
        include_languages = cfg.plugin_prefs.get(cfg.KEY_INCLUDE_LANGUAGES, False)
        self._is_show_all_duplicates_mode = cfg.plugin_prefs.get(cfg.KEY_SHOW_ALL_GROUPS, True)
        auto_delete_binary_dups = cfg.plugin_prefs.get(cfg.KEY_AUTO_DELETE_BINARY_DUPS, False)

        algorithm, self._algorithm_text = create_algorithm(self.gui, self.db,
                        search_type, identifier_type, title_match, author_match,
                        self._book_exemptions_map, self._author_exemptions_map)
        self._duplicate_search_mode = algorithm.duplicate_search_mode()


        bfg_map, gfb_map = algorithm.run_duplicate_check(sort_groups_by_title, include_languages)
        
        if search_type == 'binary' and auto_delete_binary_dups:
            self._delete_binary_duplicate_formats(bfg_map)

        self._display_run_duplicate_results(bfg_map, gfb_map)

    def _display_run_duplicate_results(self, books_for_group_map, groups_for_book_map):
        '''
        Invoked after run_book_duplicates_check has completed
        '''
        self._books_for_group_map = books_for_group_map
        self._groups_for_book_map = groups_for_book_map
        self._group_ids_queue = deque(sorted(self._books_for_group_map.keys()))

        if len(self._group_ids_queue) == 0:
            self.gui.status_bar.showMessage('')
            confirm('<p>' + _(
                    'No duplicate groups were found when searching with: <b>{0}</b>').format(self._algorithm_text),
                    'find_duplicates_no_results', self.gui, title=_('No duplicates'),
                    show_cancel_button=False, pixmap='dialog_information.png',
                    confirm_msg=_('Show this information again'))
        else:
            self.show_next_result()
            confirm('<p>' + _(
                    'Found {0} duplicate groups when searching with: <b>{1}</b>').format(len(self._group_ids_queue), self._algorithm_text),
                    'find_duplicates_count_results', self.gui, title=_('Find Duplicates'),
                    show_cancel_button=False, pixmap='dialog_information.png',
                    confirm_msg=_('Show this information again'))

    def has_results(self):
        '''
        Returns whether there is any duplicate groups outstanding from
        the last search run in the current session.
        '''
        if self._books_for_group_map:
            return len(self._books_for_group_map) > 0
        return False

    def is_searching_for_authors(self):
        '''
        Returns whether the current algorithm is a search by authors ignoring title
        rather than by books. For use with more contextual messages in the gui.
        '''
        return self._duplicate_search_mode == DUPLICATE_SEARCH_FOR_AUTHOR

    def has_duplicate_exemptions(self):
        '''
        Returns whether we have any duplicate exemptions configured for
        any books or authors.
        '''
        return self.has_book_exemptions() or  self.has_author_exemptions()

    def has_book_exemptions(self):
        '''
        Returns whether we have any duplicate exemptions configured for
        any books.
        '''
        return len(self._book_exemptions_map) > 0

    def has_author_exemptions(self):
        '''
        Returns whether we have any duplicate exemptions configured for
        any authors.
        '''
        return len(self._author_exemptions_map) > 0

    def is_book_in_exemption(self, book_id):
        '''
        Returns whether this book id currently has any duplicate exemption
        pairings. Note that it is possible that the pairing is no longer
        valid due to the paired book having been deleted.
        '''
        if book_id in self._book_exemptions_map:
            return True
        coauthors = authors_to_list(self.db, book_id)
        for author in coauthors:
            if author in self._author_exemptions_map:
                return True
        return False

    def get_exemptions_for_book(self, book_id):
        '''
        Returns the (book_ids, author_map) of all the duplicate exemptions for this book
        book_ids is a set of all the book exemptions for this book if any
        author_map is an OrderedDict of all the authors for this book as keys with
         their authors exemptions as a set of values
        '''
        book_exemptions = set()
        if book_id in self._book_exemptions_map:
            book_exemptions = self._book_exemptions_map.merge_sets(book_id)

        author_exemptions_map = OrderedDict()
        coauthors = authors_to_list(self.db, book_id)
        for author in coauthors:
            if author in self._author_exemptions_map:
                author_exemptions = self._author_exemptions_map.merge_sets(author)
                author_exemptions_map[author] = author_exemptions
        return book_exemptions, author_exemptions_map

    def is_showing_duplicate_exemptions(self):
        '''
        Returns whether we are currently displaying all duplicate exemptions
        '''
        return self._is_showing_duplicate_exemptions

    def get_current_duplicate_group_ids(self):
        '''
        Returns the book ids of all the contents in the current duplicate group
        Returns None if no current group
        '''
        if self._current_group_id is not None:
            return self._books_for_group_map[self._current_group_id]
        return None

    def show_next_result(self, forward=True):
        '''
        Navigate/highlight the next or previous result group if any available
        Checks for any merged/deleted books and recomputes all the remaining
        duplicate groups before moving on.
        '''
        if self._is_duplicate_exemptions_changed:
            # Re-run the duplicate search again using the current algorithm and display results
            self.run_book_duplicates_check()
            return

        self._is_showing_duplicate_exemptions = False
        self._cleanup_deleted_books()

        if len(self._books_for_group_map) == 0:
            self.clear_duplicates_mode()
            confirm('<p>' + _('No more duplicate groups exist from your search.'),
                    'find_duplicates_no_more_results', self.gui, title=_('No duplicates'),
                    show_cancel_button=False, pixmap='dialog_information.png',
                    confirm_msg=_('Show this information again'))
            return

        next_group_id = self._get_next_group_to_display(forward)
        if next_group_id == self._current_group_id:
            # The user has changed direction but not merged the current group - repeat move
            next_group_id = self._get_next_group_to_display(forward)
        self._current_group_id = next_group_id
        self._update_marked_books()
        self._refresh_duplicate_display_mode()
        self._search_for_duplicate_group(self._current_group_id)

        show_tag_author = cfg.plugin_prefs.get(cfg.KEY_SHOW_TAG_AUTHOR, True)
        if show_tag_author and self._duplicate_search_mode == DUPLICATE_SEARCH_FOR_AUTHOR:
            self._view_authors_in_tag_viewer()
        self._is_new_search = False

    def check_can_mark_exemption(self, all_groups=False):
        '''
        Return whether it is valid to mark desired group(s) as exempt
        '''
        # First make sure we cater for any merged/deleted book ids
        self._cleanup_deleted_books()
        if all_groups:
            group_ids = list(self._books_for_group_map.keys())
        else:
            if self._current_group_id is None:
                # Should not happen due to validation elsewhere
                return
            if self._current_group_id not in self._books_for_group_map:
                # The user must have resolved all the merges for this group
                error_dialog(self.gui, _('No duplicates'),
                            _('The current duplicate group no longer exists. '
                              'You cannot perform this action.'),
                            show=True, show_copy_button=False)
                return False
            group_ids = [self._current_group_id]
        if len(group_ids) == 0:
            info_dialog(self.gui, _('No duplicates'),
                _('No more duplicate groups exist from your search.'),
                show=True, show_copy_button=False)
            return False
        return True

    def mark_current_group_as_duplicate_exemptions(self):
        '''
        Invoke for the current duplicate group to flag all books it
        contains as not being duplicates of each other within the group.
        Persists these combinations to the config file.
        Moves on to the next duplicate group to display when done.
        If we have marked all groups, clears the search results.
        NOTE: This method relies on get_mark_exemption_preview_text() having been
              called first, to ensure the group is valid and in the case of author
              duplicate searches that the authors_for_group_map is populated
        '''
        # Update our duplicates map
        self._mark_group_ids_as_exemptions([self._current_group_id])
        # Remove the current group from consideration and move to the next group
        self._remove_duplicate_group(self._current_group_id)
        self.show_next_result(forward=True)

    def mark_groups_as_duplicate_exemptions(self):
        '''
        Invoke for all remaining duplicate groups to flag all books they
        contain as not being duplicates of each other within each group.
        Persists these combinations to the config file.
        Clears the search results when done.
        NOTE: This method relies on get_mark_exemption_preview_text() having been
              called first, to ensure the group is valid and in the case of author
              duplicate searches that the authors_for_group_map is populated
        '''
        # Update our duplicates map
        self._mark_group_ids_as_exemptions(list(self._books_for_group_map.keys()))
        # There must be no more duplicate groups so clear the search mode
        self.clear_duplicates_mode()

    def _mark_group_ids_as_exemptions(self, group_ids):
        if self._duplicate_search_mode == DUPLICATE_SEARCH_FOR_BOOK:
            exemptions_list = self._book_exemptions_map.exemptions_list
            for group_id in group_ids:
                book_ids = self._books_for_group_map.get(group_id, [])
                if book_ids:
                    exemptions_list.append(book_ids)
            cfg.set_exemption_list(self.db, cfg.KEY_BOOK_EXEMPTIONS, exemptions_list)
            # Rather than trying to keep the map up to date, just create a new one
            self._book_exemptions_map = ExemptionMap(exemptions_list)

        elif self._duplicate_search_mode == DUPLICATE_SEARCH_FOR_AUTHOR:
            exemptions_list = self._author_exemptions_map.exemptions_list
            for group_id in group_ids:
                authors = self._authors_for_group_map.get(group_id, [])
                if authors:
                    exemptions_list.append(list(authors))
            cfg.set_exemption_list(self.db, cfg.KEY_AUTHOR_EXEMPTIONS, exemptions_list)
            # Rather than trying to keep the map up to date, just create a new one
            self._author_exemptions_map = ExemptionMap(exemptions_list)

    def show_all_exemptions(self, for_books=True):
        '''
        Display for the user all the books which have been flagged as a duplicate
        exemption - either the book exemptions or the author exemptions.
        '''
        if not self.is_showing_duplicate_exemptions() and not self.has_results():
            # We are in a safe state to preserve the users current restriction/highlighting
            self._persist_gui_state()

        # Make sure we prune any deleted books from our book exemptions map
        marked = self.BOOK_EXEMPTION_MARK
        mark_author_exemptions = False
        if for_books and self._book_exemptions_map:
            self._remove_book_exemptions()
        elif not for_books:
            marked = self.AUTHOR_EXEMPTION_MARK
            mark_author_exemptions = True

        self._update_marked_books(mark_author_exemptions)
        self._refresh_exemption_display_mode(marked)
        self.gui.library_view.set_current_row(0)

    def remove_from_book_exemptions(self, book_ids, from_book_id=None):
        '''
        Allow a user to specify that this set of ids should no longer be part
        of any duplicate exemption mappings.
        If from_book_id is specified then only mappings from that book to others
        in the set are removed. This scenario is from the Manage exemptions dialog.
        If from_book_id is not specified, all permutations of mappings between
        this set of books are removed.
        '''
        exl = self._book_exemptions_map.exemptions_list
        if from_book_id:
            # We are removing mappings from this book to the other books
            exl = self._remove_master_child_exemptions(exl, from_book_id, book_ids)
        else:
            exl = self._remove_items_from_exemptions(exl, book_ids)

        cfg.set_exemption_list(self.db, cfg.KEY_BOOK_EXEMPTIONS, exl)
        # Rather than trying to keep the map up to date, just create a new one
        self._book_exemptions_map = ExemptionMap(exl)
        self._is_duplicate_exemptions_changed = True
        self._update_marked_books()
        self.gui.search.do_search()

    def _remove_book_exemptions(self, book_ids=None):
        if book_ids is None:
            book_ids = []
            for book_id in list(self._book_exemptions_map.keys()):
                if self.db.data.has_id(book_id):
                    continue
                # Ensure it is removed from the exemptions map if present
                book_ids.append(book_id)
        if book_ids:
            exl = self._book_exemptions_map.exemptions_list
            exl = self._remove_items_from_exemptions(exl, book_ids)
            cfg.set_exemption_list(self.db, cfg.KEY_BOOK_EXEMPTIONS, exl)
            # Rather than trying to keep the map up to date, just create a new one
            self._book_exemptions_map = ExemptionMap(exl)

    def _remove_author_exemptions(self, authors):
        exl = self._author_exemptions_map.exemptions_list
        exl = self._remove_items_from_exemptions(exl, authors)
        cfg.set_exemption_list(self.db, cfg.KEY_AUTHOR_EXEMPTIONS, exl)
        # Rather than trying to keep the map up to date, just create a new one
        self._author_exemptions_map = ExemptionMap(exl)

    def _remove_master_child_exemptions(self, exemptions_list, master, to_remove_items):
        # We are removing mappings from a master to one or more other items
        new_exemptions_list = []
        to_remove = set(to_remove_items)
        for s in exemptions_list:
            s = set(s)
            n = s - to_remove
            if len(n) > 1:
                new_exemptions_list.append(list(n))
            n = (s - set([master]))
            if len(n) > 1:
                new_exemptions_list.append(list(n))
        return new_exemptions_list

    def _remove_items_from_exemptions(self, exemptions_list, to_remove_items):
        # We are removing mappings between each of the items.
        # Do this by just removing the ids from all the exemption groups they are in
        new_exemptions_list = []
        to_remove = set(to_remove_items)
        for s in exemptions_list:
            n = set(s) - to_remove
            if len(n) > 1:
                new_exemptions_list.append(list(n))
        return new_exemptions_list

    def remove_from_author_exemptions(self, book_ids=None, authors=None, from_author=None):
        '''
        Allow a user to specify that this set of authors should no longer be part
        of any author duplicate exemption mappings.
        If from_author is specified then only mappings from that author to others
        in the set are removed. This scenario is from the Manage exemptions dialog.
        If from_author is not specified, all permutations of mappings between
        this set of author are removed.
        If book_ids are specified, we need to lookup the authors for those books first
        '''
        exl = self._author_exemptions_map.exemptions_list
        if from_author:
            # We are removing mappings from this author to the other authors
            exl = self._remove_master_child_exemptions(exl, from_author, authors)
        else:
            # We are removing all of the mappings for these authors
            # If only book ids given we need to convert the book ids into a unique set of authors
            if book_ids:
                authors = self._get_authors_for_books(book_ids)
            exl = self._remove_items_from_exemptions(exl, authors)

        cfg.set_exemption_list(self.db, cfg.KEY_AUTHOR_EXEMPTIONS, exl)
        # Rather than trying to keep the map up to date, just create a new one
        self._author_exemptions_map = ExemptionMap(exl)
        self._is_duplicate_exemptions_changed = True
        self._update_marked_books(mark_author_exemptions=True)
        self.gui.search.do_search()

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
        marked_ids = dict()
        # Build our dictionary of current marked duplicate groups
        if self._books_for_group_map:
            remaining_group_ids = list(sorted(self._books_for_group_map.keys()))
            for group_id in remaining_group_ids:
                marked_text = '%s%04d' % (self.DUPLICATE_GROUP_MARK, group_id)
                for book_id in self._books_for_group_map[group_id]:
                    if book_id not in marked_ids:
                        marked_ids[book_id] = marked_text
                    else:
                        marked_ids[book_id] = '%s,%s' % (marked_ids[book_id], marked_text)

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
        # Assign the results to our database
        self.gui.current_db.set_marked_ids(marked_ids)

    def _get_authors_for_books(self, book_ids):
        authors = set()
        for book_id in book_ids:
            coauthors = authors_to_list(self.db, book_id)
            for author in coauthors:
                authors.add(author)
        return authors

    def _create_books_for_author_map(self):
        books_for_author_map = defaultdict(set)
        for book_id in self.db.all_ids():
            coauthors = authors_to_list(self.db, book_id)
            for author in coauthors:
                books_for_author_map[author].add(book_id)
        # Use this opportunity to purge any author exemptions that we do not have books for
        deleted_authors = []
        for author in list(self._author_exemptions_map.keys()):
            if author in books_for_author_map:
                continue
            deleted_authors.append(author)
        if deleted_authors:
            self._remove_author_exemptions(deleted_authors)
        return books_for_author_map

    def _cleanup_deleted_books(self):
        # First pass is to remove delete/merged books and their associated groups
        book_ids = list(self._groups_for_book_map.keys())
        deleted_ids = []
        for book_id in sorted(book_ids):
            if not self.db.data.has_id(book_id):
                # We have a book that has been merged/deleted
                # Remove the book from all of its groups.
                for group_id in self._groups_for_book_map[book_id]:
                    group = self._books_for_group_map[group_id]
                    group.remove(book_id)
                del self._groups_for_book_map[book_id]
                # Ensure it is removed from the exemptions map if present
                deleted_ids.append(book_id)

        # Second action is to ensure deleted books are removed from exemptions map
        if deleted_ids:
            self._remove_book_exemptions(deleted_ids)

        # Third pass is through the groups to remove all groups...
        #   with < 2 members if we are viewing a book based duplicate search, or
        #   with < 2 authors if we are viewing and author based duplicate search
        self._authors_for_group_map = defaultdict(set)
        for group_id in list(self._books_for_group_map.keys()):
            if self._duplicate_search_mode == DUPLICATE_SEARCH_FOR_BOOK:
                count = len(self._books_for_group_map[group_id])
            elif self._duplicate_search_mode == DUPLICATE_SEARCH_FOR_AUTHOR:
                authors = set()
                for book_id in self._books_for_group_map[group_id]:
                    coauthors = authors_to_list(self.db, book_id)
                    for author in coauthors:
                        if author not in authors:
                            authors.add(author)
                            self._authors_for_group_map[group_id].add(author)
                count = len(authors)
            if count > 1:
                continue
            if count == 1:
                # There is one book left in this group, so the group can be deleted
                # However we need to cleanup entries for the book too.
                last_book_id = self._books_for_group_map[group_id][0]
                self._groups_for_book_map[last_book_id].remove(group_id)
            del self._books_for_group_map[group_id]
            self._group_ids_queue.remove(group_id)
            if group_id in self._authors_for_group_map:
                del self._authors_for_group_map[group_id]

        # Our final pass is looking for books that can be removed from the maps because
        # they have no groups any more
        for book_id in list(self._groups_for_book_map.keys()):
            if len(self._groups_for_book_map[book_id]) == 0:
                del self._groups_for_book_map[book_id]

        # Set our flag to know whether to force a refresh of our search restriction
        # when we move to the next group, since the name of the restriction will be
        # the same when the marked groups get renumbered
        self._is_group_changed = self._current_group_id not in self._groups_for_book_map

    def _get_next_group_to_display(self, forward):
        if forward:
            next_group_id = self._group_ids_queue.popleft()
            self._group_ids_queue.append(next_group_id)
        else:
            next_group_id = self._group_ids_queue.pop()
            self._group_ids_queue.appendleft(next_group_id)
        return next_group_id

    def _refresh_duplicate_display_mode(self):
        self.gui.library_view.multisort((('marked', True), ('authors', True), ('title', True)),
                                        only_if_different=not self._is_new_search)
        self._apply_highlight_if_different(self._is_show_all_duplicates_mode)
        if self._is_show_all_duplicates_mode:
            restriction = 'marked:%s' % self.DUPLICATES_MARK
            self._apply_restriction_if_different(restriction)

    def _search_for_duplicate_group(self, group_id):
        marked_text = 'marked:%s%04d' % (self.DUPLICATE_GROUP_MARK, group_id)
        if self._is_show_all_duplicates_mode:
            self.gui.search.set_search_string(marked_text)
        else:
            self._apply_restriction_if_different(marked_text)
            # When displaying groups one at a time, we need to move selection
            self.gui.library_view.set_current_row(0)

        remaining_group_ids = list(sorted(self._books_for_group_map.keys()))
        position = remaining_group_ids.index(group_id) + 1
        msg = _('Showing #{0} of {0} remaining duplicate groups for {0}').format(position, len(remaining_group_ids), self._algorithm_text)
        self.gui.status_bar.showMessage(msg)

    def _refresh_exemption_display_mode(self, marked):
        self._is_showing_duplicate_exemptions = True
        self._apply_highlight_if_different(False)
        restriction = 'marked:%s' % marked
        self._apply_restriction_if_different(restriction)

    def _persist_gui_state(self):
        r = self.gui.search_restriction
        self._restore_restriction = str(r.currentText())
        self._restore_restriction_is_text = False
        if self._restore_restriction:
            # How do we know whether this is a named search or a text search?
            # TODO: hacks below will work for 0.7.56 and later, will change it when 0.7.57 released
            special_menu = str(r.itemText(1))
            self._restore_restriction_is_text = special_menu == self._restore_restriction
            if self._restore_restriction.startswith('*') and r.currentIndex() == 2:
                self._restore_restriction_is_text = True
                self._restore_restriction = self._restore_restriction[1:]
        self._restore_highlighting_state = config['highlight_search_matches']
        self.sort_history = self.gui.library_view.get_state().get('sort_history', [])

    def _restore_previous_gui_state(self, reapply_restriction=True, restore_sort=False):
        # Restore the user's GUI to it's previous glory
        self._apply_highlight_if_different(self._restore_highlighting_state)
        if reapply_restriction:
            self._apply_restriction_if_different(self._restore_restriction,
                                                 self._restore_restriction_is_text)
        if restore_sort:
            try:
                max_sort_levels = min(tweaks['maximum_resort_levels'], len(self.sort_history))
                self.gui.library_view.apply_sort_history(self.sort_history, max_sort_levels=max_sort_levels)
            except Exception as e:
                if DEBUG:
                    prints('Find Duplicates: Error(s) when restoring sort history: {}'.format(e))

    def _apply_highlight_if_different(self, new_state):
        if config['highlight_search_matches'] != new_state:
            config['highlight_search_matches'] = new_state
            self.gui.set_highlight_only_button_icon()

    def _apply_restriction_if_different(self, restriction, is_text_restriction=True):
        prev_ignore = self._ignore_clear_signal
        self._ignore_clear_signal = True
        if str(self.gui.search_restriction.currentText()) not in [restriction, '*'+restriction]:
            if is_text_restriction:
                self.gui.apply_text_search_restriction(restriction)
            else:
                self.gui.apply_named_search_restriction(restriction)
        self._ignore_clear_signal = prev_ignore

    def _remove_duplicate_group(self, group_id):
        book_ids = self._books_for_group_map[group_id]
        for book_id in book_ids:
            self._groups_for_book_map[book_id].remove(group_id)
        del self._books_for_group_map[group_id]
        self._group_ids_queue.remove(group_id)

    def _view_authors_in_tag_viewer(self):
        draw_boxes = self._is_show_all_duplicates_mode and len(self._books_for_group_map) > 1
        if not self.gui.tags_view.pane_is_visible:
            self.gui.tb_splitter.show_side_pane()
            if draw_boxes:
                self.gui.tags_view.set_pane_is_visible(True)
        else:
            self.gui.tags_view.model().clear_boxed()

        if draw_boxes:
            book_ids = self._books_for_group_map[self._current_group_id]
            for book_id in book_ids:
                coauthors = authors_to_list(self.db, book_id)
                for author in coauthors:
                    p = self.gui.tags_view.model().find_item_node('authors', author, None)
                    if p:
                        idx = self.gui.tags_view.model().index_for_path(p)
                        self.gui.tags_view.setExpanded(idx, True)
                        self.gui.tags_view.show_item_at_path(p, box=True)
        else:
            p = self.gui.tags_view.model().find_category_node('authors')
            if p:
                self.gui.tags_view.show_item_at_path(p)
                idx = self.gui.tags_view.model().index_for_path(p)
                self.gui.tags_view.setExpanded(idx, True)

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


class CrossLibraryDuplicateFinder(object):

    def __init__(self, gui):
        self.gui = gui
        self.db = gui.current_db
        self.log = GUILog()

    def run_library_duplicates_check(self):
        library_config = cfg.get_library_config(self.db)
        self.library_path = library_config[cfg.KEY_LAST_LIBRARY_COMPARE]
        from calibre.library import db as DB
        self.target_db = DB(self.library_path, read_only=True)

        self.search_type = cfg.plugin_prefs.get(cfg.KEY_SEARCH_TYPE, 'titleauthor')
        self.identifier_type = cfg.plugin_prefs.get(cfg.KEY_IDENTIFIER_TYPE, 'isbn')
        self.title_match = cfg.plugin_prefs.get(cfg.KEY_TITLE_MATCH, 'identical')
        self.author_match  = cfg.plugin_prefs.get(cfg.KEY_AUTHOR_MATCH, 'identical')
        title_soundex_length = cfg.plugin_prefs.get(cfg.KEY_TITLE_SOUNDEX, 6)
        author_soundex_length = cfg.plugin_prefs.get(cfg.KEY_AUTHOR_SOUNDEX, 8)
        set_title_soundex_length(title_soundex_length)
        set_author_soundex_length(author_soundex_length)
        self.include_languages = cfg.plugin_prefs.get(cfg.KEY_INCLUDE_LANGUAGES, False)
        self.display_results = cfg.plugin_prefs.get(cfg.KEY_DISPLAY_LIBRARY_RESULTS, True)

        # We will re-use the elements of the same basic algorithm code, but
        # only by calling specific functions to control what gets executed
        # since the approach for comparing all books in one library with another
        # significantly differs. Also of course book exemptions will not apply.

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            message = self._do_comparison()
        finally:
            QApplication.restoreOverrideCursor()
        self.gui.status_bar.showMessage('Duplicate search completed', 3000)
        txt = self.log.plain_text
        if txt:
            txt = _('Results of {0} comparison:\n    Source library: {1}\n    Target library: {2}\n\n{3}').format(
                    self.algorithm_text, self.db.library_path, self.library_path, txt)
        d = SummaryMessageBox(self.gui, 'Library Duplicates', message, det_msg=txt)
        d.exec_()

    def _get_book_display_info(self, db, book_id, include_author=True, include_formats=True,
                               include_identifier=False):
        if hasattr(db, 'new_api'):
            # Requires calibre 5.9 or later
            mi = db.new_api.get_proxy_metadata(book_id)
            text = mi.title
            if include_author:
                authors = ' & '.join(mi.authors)
                text = '%s / %s'%(text, authors)
            if include_formats:
                formats = mi.formats
                if formats is None:
                    formats = '[No formats]'
                text = '%s %s'%(text, formats)
            if include_identifier:
                identifiers = mi.identifiers
                identifier = identifiers.get(self.identifier_type, '')
                text = '%s {%s:%s}'%(text, self.identifier_type, identifier)
            return text
        else:
            text = db.title(book_id, index_is_id=True)
            if include_author:
                authors = ' & '.join(authors_to_list(db, book_id))
                text = '%s / %s'%(text, authors)
            if include_formats:
                formats = db.formats(book_id, index_is_id=True)
                if formats is None:
                    formats = 'No formats'
                text = '%s [%s]'%(text, formats)
            if include_identifier:
                identifiers = db.get_identifiers(book_id, index_is_id=True)
                identifier = identifiers.get(self.identifier_type, '')
                text = '%s {%s:%s}'%(text, self.identifier_type, identifier)
            return text

    def _do_comparison(self):
        '''
        When analysing the current database, we do not want to hash every book with
        every other book in this database. Instead we want to determine the hash
        and then compare it with the hashes we have from the other database.
        So we will not be reporting duplicates within this database, only duplicates
        from each individual book in this database with the target database.
        '''
        debug_print('Find Duplicates -> Library -> Start ({})'.format(self.search_type))
        algorithm, self.algorithm_text = create_algorithm(self.gui, self.db,
                        self.search_type, self.identifier_type,
                        self.title_match, self.author_match, None, None)
        duplicates_count = 0
        duplicate_book_ids = None

        if algorithm.duplicate_search_mode() == DUPLICATE_SEARCH_FOR_AUTHOR:
            # Author only comparisons need to be treated specially because we want to
            # iterate through authors, not book ids
            duplicates_count, duplicate_book_ids, msg = self._do_author_only_comparison(algorithm)

        elif self.search_type == 'binary':
            # Binary comparison searches are a headache we can't solve by reusing the
            # existing algorithm because shrinking of the resultsets takes place.
            # Effectively must rewrite the algorithm code
            duplicates_count, duplicate_book_ids, msg = self._do_binary_comparison(algorithm)

        else:
            # This is an identifier or title/author search
            duplicates_count, duplicate_book_ids, msg = self._do_title_author_identifier_comparison(algorithm)

        debug_print('Find Duplicates -> Library -> Search completed')
        if duplicates_count > 0:
            msg += "<br/><br/>" + _("Click 'Show details' to see the results.")
            if self.display_results and duplicate_book_ids is not None:
                marked_ids = {}
                for book_id in duplicate_book_ids:
                    marked_ids[book_id] = 'library_duplicate'
                self.gui.current_db.set_marked_ids(marked_ids)
                self.gui.search.set_search_string('marked:library_duplicate')
                debug_print('Find Duplicates -> Library -> Marked results displayed')
        return msg

    def _do_author_only_comparison(self, algorithm):
        self.gui.status_bar.showMessage(_('Analysing duplicates in target database')+'...', 0)
        target_candidates_map, target_author_bookids_map = self._analyse_target_database()
        self.gui.status_bar.showMessage(_('Analysing duplicates in current database')+'...', 0)
        duplicates_count = 0
        duplicate_book_ids = []

        # We will just look at an author by author basis, rather than by book id
        # However in order to display the books affected afterwards, we need to keep track of them.
        book_ids = algorithm.get_book_ids_to_consider()
        author_books_map = defaultdict(set)
        for book_id in book_ids:
            book_authors = authors_to_list(self.db, book_id)
            for author in book_authors:
                author_books_map[author].add(book_id)

        authors = get_field_pairs(self.db, 'authors')
        author_names = [a[1].replace('|',',') for a in authors]
        for author in author_names:
            author_candidates_map = defaultdict(set)
            algorithm.find_author_candidate(author, author_candidates_map)
            for author_hash in author_candidates_map:
                if author_hash in target_candidates_map:
                    self.log('Author in this library: %s'%author)
                    # Find the books for this author
                    for book_id in author_books_map[author]:
                        duplicate_book_ids.append(book_id)
                    duplicates_count += 1
                    for dup_author in sorted(list(target_candidates_map[author_hash])):
                        self.log('   Target library author: %s'%dup_author)
                        for book_id in target_author_bookids_map[dup_author]:
                            self.log('      Has book: %s'%self._get_book_display_info(self.target_db, book_id))
                    self.log('')

        msg = _('Found <b>{0} authors</b> with potential duplicates using <b>{1}</b> against the library at: {2}').format(
                    duplicates_count, self.algorithm_text, self.library_path)
        return duplicates_count, duplicate_book_ids, msg

    def _do_binary_comparison(self, algorithm):
        local_book_ids = algorithm.get_book_ids_to_consider()

        def shrink_map(source_map, other_map):
            new_map = {}
            for k,v in list(source_map.items()):
                if k in other_map:
                    new_map[k] = v
            return new_map

        def get_format(results_hash_map, book_id):
            book_format = ''
            for fmt, book_data in list(results_hash_map[book_id].items()):
                if book_data['sha'] == k[0] and book_data['size'] == k[1]:
                    book_format = fmt
                    break
            return book_format

        self.gui.status_bar.showMessage('Analysing binary duplicates...', 0)
        from calibre_plugins.find_duplicates.book_algorithms import BinaryCompareAlgorithm
        target_algorithm = BinaryCompareAlgorithm(self.gui, self.target_db, None)
        # We can't just run the algorithm against the target database because its
        # optimisations mean that we aren't given the "raw" candidates map for us
        # to include books from this database before shrinking/refining.

        # Find all books that have an identical file size in the target database
        target_book_ids = target_algorithm.get_book_ids_to_consider()
        target_candidates_size_map = defaultdict(set)
        for book_id in target_book_ids:
            target_algorithm._find_candidate_by_file_size(book_id, target_candidates_size_map)
        # Find all books that have an identical file size in the current database
        local_candidates_size_map = defaultdict(set)
        for book_id in local_book_ids:
            algorithm._find_candidate_by_file_size(book_id, local_candidates_size_map)

        # Now reduce our candidates size maps to only those which intersect
        target_candidates_size_map = shrink_map(target_candidates_size_map, local_candidates_size_map)
        local_candidates_size_map = shrink_map(local_candidates_size_map, target_candidates_size_map)

        # Next compute file hashes for the target database candidates
        target_hash_map = self.target_db.get_all_custom_book_data('find_duplicates', default={})
        target_result_hash_map = {}
        target_candidates_map = defaultdict(set)
        for size, size_group in list(target_candidates_size_map.items()):
            for book_id, fmt, mtime in size_group:
                target_algorithm._find_candidate_by_hash(book_id, fmt, mtime, size, target_candidates_map, target_hash_map, target_result_hash_map)
        self.target_db.add_multiple_custom_book_data('find_duplicates', target_result_hash_map)

        # Now compute file hashes the current database candidates (just to get the hashes)
        local_hash_map = self.db.get_all_custom_book_data('find_duplicates', default={})
        local_result_hash_map = {}
        local_candidates_map = defaultdict(set)
        for size, size_group in list(local_candidates_size_map.items()):
            for book_id, fmt, mtime in size_group:
                algorithm._find_candidate_by_hash(book_id, fmt, mtime, size, local_candidates_map, local_hash_map, local_result_hash_map)
        self.db.add_multiple_custom_book_data('find_duplicates', local_result_hash_map)

        # Now we have all the raw data we need. The local_candidates_map contains
        # all the books that "might" have duplicates, but grouped together in case
        # there are duplicates within the current library. Lets remove all the local
        # candidates that definitely have no matches in the target library
        local_candidates_map = shrink_map(local_candidates_map, target_candidates_map)

        # Finally what is left are groups of current library books that have duplicates
        duplicates_count = 0
        duplicate_book_ids = []
        for k, book_ids in list(local_candidates_map.items()):
            target_book_ids = target_candidates_map[k]
            # We may have multiple duplicates within our own library
            # Unlike the other cross-library comparisons, will show these together
            for book_id in book_ids:
                duplicate_book_ids.append(book_id)
                duplicates_count += 1
                # Figure out what format was considered a duplicate
                book_format = get_format(local_result_hash_map, book_id)
                text = '%s [%s]'%(self._get_book_display_info(self.db, book_id, include_formats=False), book_format)
                self.log('Book format in this library: %s'%text)
                dups = []
                for dup_book_id in target_book_ids:
                    book_format = get_format(target_result_hash_map, dup_book_id)
                    dups.append('%s [%s]'%(self._get_book_display_info(self.target_db, dup_book_id, include_formats=False), book_format))
                for dup_text in sorted(dups):
                    self.log('   Target duplicate format: %s'%dup_text)
                self.log('')

        msg = _('Found <b>{0} books</b> with binary duplicates against the library at: {1}').format(duplicates_count, self.library_path)
        return duplicates_count, duplicate_book_ids, msg

    def _do_title_author_identifier_comparison(self, algorithm):
        self.gui.status_bar.showMessage(_('Analysing duplicates in target database')+'...', 0)
        target_candidates_map, author_bookids_map_unused = self._analyse_target_database()

        # Use the standard approach to get current library book ids for consideration
        book_ids = algorithm.get_book_ids_to_consider()
        include_identifier = self.search_type == 'identifier'
        duplicate_book_ids = []

        marked_ids = {}
        self.gui.status_bar.showMessage(_('Analysing duplicates in current database')+'...', 0)
        # Iterate through these books getting our hashes
        for book_id in book_ids:
            # We will create a temporary candidates map for each book, since we are
            # not interested in hashing the current library's books together. And we
            # can't give it the map from the target database, because we won't know
            # which database each group's ids belong to!
            book_candidates_map = defaultdict(set)
            algorithm.find_candidate(book_id, book_candidates_map, self.include_languages)
            # We now have any hash(s) for the current book in our candidates map.
            # See if we have them in our target library map too to indicate a duplicate
            duplicate_books = set()
            for book_hash in book_candidates_map:
                if book_hash in target_candidates_map:
                    duplicate_books |= target_candidates_map[book_hash]
            if len(duplicate_books) > 0:
                duplicate_book_ids.append(book_id)
                self.log('Book in this library: %s'%self._get_book_display_info(self.db, book_id, include_identifier=include_identifier))
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
        algorithm, self.algorithm_text = create_algorithm(self.gui, self.target_db,
                        self.search_type, self.identifier_type,
                        self.title_match, self.author_match, None, None)

        book_ids = self._get_target_db_book_ids(self.search_type)
        target_candidates_map = algorithm.find_candidates(book_ids, self.include_languages)
        author_bookids_map = None
        # Bit of a bodge. If we are running an author only comparison, we want
        # the additional map that algorithm creates listing the books per author
        # in order to display that information in the log results.
        if hasattr(algorithm, 'author_bookids_map'):
            author_bookids_map = algorithm.author_bookids_map
        return target_candidates_map, author_bookids_map

    def _get_target_db_book_ids(self, search_type):
        if search_type == 'identifier':
            return self.target_db.search_getting_ids('identifier:'+self.identifier_type+':True', None)
        elif search_type == 'binary':
            return self.target_db.search_getting_ids('formats:True', None)
        else:
            return self.target_db.all_ids()

