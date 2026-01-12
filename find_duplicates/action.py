from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from functools import partial

try:
    from qt.core import QMenu, QToolButton, QApplication, QUrl, Qt
except ImportError:
    from PyQt5.Qt import QMenu, QToolButton, QApplication, QUrl, Qt

import json, os
from datetime import datetime
try:
    from calibre.utils.iso8601 import local_tz
except ImportError:
    from calibre.utils.date import local_tz

from calibre.debug import iswindows
from calibre.gui2 import info_dialog, error_dialog, open_url, choose_save_file
from calibre.gui2.actions import InterfaceAction
from calibre.gui2.dialogs.confirm_delete import confirm

from calibre_plugins.find_duplicates.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.find_duplicates.common_menus import unregister_menu_actions, create_menu_action_unique
from calibre_plugins.find_duplicates.dialogs import (FindBookDuplicatesDialog, FindVariationsDialog,
                                FindLibraryDuplicatesDialog, ManageExemptionsDialog)
from calibre_plugins.find_duplicates.duplicates import DuplicateFinder, CrossLibraryDuplicateFinder

try:
    load_translations()
except NameError:
    pass

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/Find-Duplicates'

PLUGIN_ICONS = ['images/find_duplicates.png',
                'images/next_result.png', 'images/previous_result.png']

class FindDuplicatesAction(InterfaceAction):

    name = 'Find Duplicates'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (_('Find Duplicates'), None, None, None)
    popup_type = QToolButton.MenuButtonPopup
    action_type = 'current'

    def genesis(self):
        self.menu = QMenu()

        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)

        self.rebuild_menus()

        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.qaction.triggered.connect(self.toolbar_button_clicked)
        self.menu.aboutToShow.connect(self.about_to_show_menu)

    def initialization_complete(self):
        # Delay instantiating our finder as we require access to the library view
        self.duplicate_finder = DuplicateFinder(self.gui)
        self.has_advanced_results = False
        self.update_actions_enabled()
        self.gui.search.cleared.connect(self.user_has_cleared_search) 
        self.gui.search_restriction.currentIndexChanged.connect(self.user_has_changed_restriction)

    def library_changed(self, db):
        # We need to reset our duplicate finder after switching libraries
        self.duplicate_finder = DuplicateFinder(self.gui)
        self.update_actions_enabled()

    def shutting_down(self):
        if self.duplicate_finder.is_showing_duplicate_exemptions() or self.duplicate_finder.has_results():
            self.duplicate_finder.clear_duplicates_mode()

    def rebuild_menus(self):
        # Ensure any keyboard shortcuts from previous display of plugin menu are cleared
        unregister_menu_actions(self)

        m = self.menu
        m.clear()
        create_menu_action_unique(self, m, _('&Find book duplicates')+'...', image=PLUGIN_ICONS[0],
                         triggered=self.find_book_duplicates)
        create_menu_action_unique(self, m, _('Find library duplicates')+'...', image='library.png',
                         tooltip=_('Find books that are duplicated in another library compared to this one'),
                         triggered=self.find_library_duplicates)
        m.addSeparator()
        create_menu_action_unique(self, m, _('Find metadata &variations')+'...', image='user_profile.png',
                         tooltip=_('Find & rename variations in author, publisher, series or tags names that may indicate duplicates'),
                         triggered=self.find_variations)
        m.addSeparator()
        self.next_group_action = create_menu_action_unique(self, m, _('&Next result'), image='images/next_result.png',
                                tooltip=_('Display the next duplicate result group'),
                                triggered=partial(self.show_next_result, forward=True))
        self.previous_group_action = create_menu_action_unique(self, m, _('&Previous result'), image='images/previous_result.png',
                                tooltip=_('Display the previous duplicate result group'),
                                triggered=partial(self.show_next_result, forward=False))
        m.addSeparator()
        self.mark_group_exempt_action = create_menu_action_unique(self, m, _('&Mark current group as exempt'),
                                tooltip=_('Mark the current group as not duplicates and exempt from future consideration'),
                                triggered=partial(self.mark_groups_as_duplicate_exemptions, all_groups=False))
        self.mark_all_groups_exempt_action = create_menu_action_unique(self, m,
                                _('Mark &all groups as exempt'),
                                tooltip=_('Mark all remaining duplicate groups as exempt from future consideration'),
                                triggered=partial(self.mark_groups_as_duplicate_exemptions, all_groups=True))
        m.addSeparator()
        self.show_book_exempt_action = create_menu_action_unique(self, m,
                                _('&Show all book duplicate exemptions'),
                                tooltip=_('Show all books that have book duplicate exemption pairings'),
                                triggered=partial(self.show_all_exemptions, for_books=True))
        self.show_author_exempt_action = create_menu_action_unique(self, m,
                                _('&Show all author duplicate exemptions'),
                                tooltip=_('Show all books that have author duplicate exemption pairings'),
                                triggered=partial(self.show_all_exemptions, for_books=False))
        self.manage_exemptions_action = create_menu_action_unique(self, m,
                                _('&Manage exemptions for this book'),
                                tooltip=_('Show duplicate exemptions for this book to enable removal'),
                                triggered=self.manage_exemptions_for_book)
        self.remove_exemptions_action = create_menu_action_unique(self, m,
                                _('&Remove selected exemptions'),
                                tooltip=_('Remove any duplicate book/author exemptions for the selected books'),
                                triggered=self.remove_from_duplicate_exemptions)
        m.addSeparator()
        self.clear_duplicate_mode_action = create_menu_action_unique(self, m,
                                _('&Clear duplicate results'), image='clear_left.png',
                                tooltip=_('Exit duplicate search mode'),
                                triggered=self.clear_duplicate_results)
        m.addSeparator()
        self.export_duplicates_action = create_menu_action_unique(self, m,
                                _('&Export duplicate groups'),
                                tooltip=_('Export duplicates groups to a json file'),
                                triggered=self.export_duplicates)
        m.addSeparator()

        create_menu_action_unique(self, m, _('&Customize plugin')+'...', 'config.png',
                                  shortcut=False, triggered=self.show_configuration)
        create_menu_action_unique(self, m, _('&Help'), 'help.png',
                                  shortcut=False, triggered=self.show_help)
        self.gui.keyboard.finalize()

    def about_to_show_menu(self):
        self.update_actions_enabled()
        # As we are showing a menu we can refine the enabled state of the
        # actions that are based on the selected rows
        has_duplicate_exemptions = self.duplicate_finder.has_duplicate_exemptions()
        if has_duplicate_exemptions:
            book_ids = self.gui.library_view.get_selected_ids()
            remove_enabled = len(book_ids) > 0
            manage_enabled = len(book_ids) == 1
            if manage_enabled:
                manage_enabled = self.duplicate_finder.is_book_in_exemption(book_ids[0])
            for book_id in book_ids:
                if not self.duplicate_finder.is_book_in_exemption(book_id):
                    remove_enabled = False
                    break
            self.manage_exemptions_action.setEnabled(manage_enabled)
            self.remove_exemptions_action.setEnabled(remove_enabled)

    def update_actions_enabled(self):
        has_results = self.duplicate_finder.has_results()
        self.next_group_action.setEnabled(has_results)
        self.previous_group_action.setEnabled(has_results)
        self.mark_group_exempt_action.setEnabled(has_results)
        self.mark_all_groups_exempt_action.setEnabled(has_results)
        is_showing_exemptions = self.duplicate_finder.is_showing_duplicate_exemptions()
        self.clear_duplicate_mode_action.setEnabled(has_results or is_showing_exemptions or self.has_advanced_results)
        self.export_duplicates_action.setEnabled(has_results)

        # As some actions could be via shortcut keys we need them enabled
        # regardless of row selections
        has_duplicate_exemptions = self.duplicate_finder.has_duplicate_exemptions()
        self.show_book_exempt_action.setEnabled(self.duplicate_finder.has_book_exemptions())
        self.show_author_exempt_action.setEnabled(self.duplicate_finder.has_author_exemptions())
        self.manage_exemptions_action.setEnabled(has_duplicate_exemptions)
        self.remove_exemptions_action.setEnabled(has_duplicate_exemptions)

    def find_book_duplicates(self):
        d = FindBookDuplicatesDialog(self.gui)
        if d.exec_() == d.Accepted:
            self.duplicate_finder.run_book_duplicates_check()
            self.update_actions_enabled()

    def find_library_duplicates(self):
        if self.clear_duplicate_mode_action.isEnabled():
            self.clear_duplicate_results()
        else:
            self.gui.search.clear()
        d = FindLibraryDuplicatesDialog(self.gui)
        if d.exec_() == d.Accepted:
            self.library_finder = CrossLibraryDuplicateFinder(self.gui)
            self.library_finder.run_library_duplicates_check()
            self.has_advanced_results = self.library_finder.display_results
            self.update_actions_enabled()

    def find_variations(self):
        if self.clear_duplicate_mode_action.isEnabled():
            self.clear_duplicate_results()
        ids = self.gui.library_view.get_selected_ids()
        query = self.gui.search.text()
        d = FindVariationsDialog(self.gui)
        d.exec_()
        if d.is_changed():
            # Signal the library view and tags panel to refresh.
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                self.gui.library_view.model().refresh()
            finally:
                QApplication.restoreOverrideCursor()
        # If the user is displaying books simultaneously from the dialog then we do
        # not want to change the search in case they intentionally cancelled to make
        # some changes to those visible rows
        if not d.is_showing_books():
            self.gui.search.set_search_string(query)
            self.gui.library_view.select_rows(ids)        
        self.gui.tags_view.recount()
        if d.is_showing_books():
            self.gui.search.do_search()

    def toolbar_button_clicked(self):
        if not self.duplicate_finder.has_results():
            return self.find_book_duplicates()
        # If the user control-clicks on this button/menu, reverse the direction of search
        forward = True
        mods = QApplication.keyboardModifiers()
        if mods & Qt.ControlModifier or mods & Qt.ShiftModifier:
            forward = False
        self.show_next_result(forward)

    def show_next_result(self, forward=True):
        self.duplicate_finder.show_next_result(forward)
        self.update_actions_enabled()

    def mark_groups_as_duplicate_exemptions(self, all_groups):
        can_exempt = self.duplicate_finder.check_can_mark_exemption(all_groups)
        if can_exempt:
            # Ensure that the selection is moved onto the current duplicate group
            duplicate_ids = self.duplicate_finder.get_current_duplicate_group_ids()
            self.gui.library_view.select_rows(duplicate_ids)
            exemption_type = 'books'
            if self.duplicate_finder.is_searching_for_authors():
                exemption_type = 'authors'
            dialog_name = 'find_duplicates_mark_all_groups' if all_groups else 'find_duplicates_mark_group'
            if not confirm('<p>' + _(
                            'This action will ensure that each of the {0} in the group '
                            'are exempt from appearing together again in future.').format(exemption_type)+'<p>'+ 
                            _('Are you <b>sure</b> you want to proceed?'),
                            dialog_name, self.gui):
                return
            if all_groups:
                self.duplicate_finder.mark_groups_as_duplicate_exemptions()
            else:
                self.duplicate_finder.mark_current_group_as_duplicate_exemptions()
        else:
            info_dialog(self.gui, _('No duplicates in group'),
                        _('There are no duplicates remaining in this group.'),
                        show=True, show_copy_button=False)
        self.update_actions_enabled()

    def show_all_exemptions(self, for_books=True):
        self.duplicate_finder.show_all_exemptions(for_books)
        self.update_actions_enabled()

    def manage_exemptions_for_book(self):
        row = self.gui.library_view.currentIndex()
        if not row.isValid():
            return error_dialog(self.gui, _('Cannot manage exemptions'),
                    _('No book selected'), show=True)
        book_id = self.gui.library_view.model().id(row)
        book_exemptions, author_exemptions_map = self.duplicate_finder.get_exemptions_for_book(book_id)
        if not book_exemptions and not author_exemptions_map:
            return info_dialog(self.gui, _('Cannot manage exemptions'),
                    _('This book has no duplicate exemptions'), show=True)

        d = ManageExemptionsDialog(self.gui, self.gui.current_db,
                                   book_id, book_exemptions, author_exemptions_map)
        d.exec_()
        if d.result() == d.Accepted:
            exempt_book_ids = d.get_checked_book_ids()
            if exempt_book_ids:
                self.duplicate_finder.remove_from_book_exemptions(
                                            exempt_book_ids, from_book_id=book_id)
            exempt_authors_map = d.get_checked_authors_map()
            if exempt_authors_map:
                for author, exempt_authors in list(exempt_authors_map.items()):
                    self.duplicate_finder.remove_from_author_exemptions(
                                            authors=exempt_authors, from_author=author)

        self.update_actions_enabled()

    def remove_from_duplicate_exemptions(self):
        book_ids = self.gui.library_view.get_selected_ids()
        if len(book_ids) < 1:
            return error_dialog(self.gui, _('Invalid selection'),
                    _('You must select at least one book.'), show=True)
        if not confirm('<p>' + _(
                 'This action will remove any duplicate exemptions for your '
                 'selection. This will allow them to potentially appear '
                 'as duplicates together in a future duplicate search.')+'<p>'+
                 _('Are you <b>sure</b> you want to proceed?'),
                 'find_duplicates_remove_exemption', self.gui):
            return
        self.duplicate_finder.remove_from_book_exemptions(book_ids)
        self.duplicate_finder.remove_from_author_exemptions(book_ids)
        self.update_actions_enabled()

    def clear_duplicate_results(self, clear_search=True, reapply_restriction=True):
        if not self.clear_duplicate_mode_action.isEnabled():
            return
        if self.has_advanced_results:
            self.library_finder.clear_gui_duplicates_mode(clear_search, reapply_restriction)
            self.has_advanced_results = False
        else:
            self.duplicate_finder.clear_duplicates_mode(clear_search, reapply_restriction)
        self.update_actions_enabled()

    def user_has_cleared_search(self):
        if self.has_advanced_results or self.duplicate_finder.is_valid_to_clear_search():
            self.clear_duplicate_results(clear_search=False)

    def user_has_changed_restriction(self, idx):
        if self.has_advanced_results or self.duplicate_finder.is_valid_to_clear_search():
            self.clear_duplicate_results(clear_search=False, reapply_restriction=False)

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)
    
    def export_duplicates(self):
        '''
        export all duplicate books to a json file.
        '''
        self.duplicate_finder._cleanup_deleted_books()

        json_path = choose_save_file(self.gui, 'export-duplicates', _('Choose file'), filters=[
            (_('Saved duplicates'), ['json'])], all_files=False)
        if json_path:
            if not json_path.lower().endswith('.json'):
                json_path += '.json'
        if not json_path:
            return
            
        if iswindows:
            json_path = os.path.normpath(json_path)

        entangled_books = {}
        for book_id, groups in self.duplicate_finder._groups_for_book_map.items():
            if len(groups) > 1:
                entangled_books[book_id] = list(groups)

        data = {
            'books_for_group': self.duplicate_finder._books_for_group_map,
            'entangled_groups_for_book': entangled_books,
            'library_uuid': self.gui.current_db.library_id,
            'library_path': self.gui.current_db.library_path,
            'timestamp': datetime.now().replace(tzinfo=local_tz).isoformat()
        }
            
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
        
        info_dialog(self.gui, _('Export completed'),
                    _('Exported to: {}').format(json_path),
                    show=True, show_copy_button=False)

    def show_help(self):
        open_url(QUrl(HELP_URL))
