from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import os
from functools import partial
try:
    from qt.core import QMenu, QToolButton
except ImportError:
    from PyQt5.Qt import QMenu, QToolButton

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.gui2 import error_dialog, question_dialog
from calibre.gui2.actions import InterfaceAction

import calibre_plugins.goodreads_sync.config as cfg
from calibre_plugins.goodreads_sync.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.goodreads_sync.common_menus import unregister_menu_actions, create_menu_action_unique
from calibre_plugins.goodreads_sync.common_dialogs import ProgressBarDialog
from calibre_plugins.goodreads_sync.core import (CalibreSearcher, HttpHelper, IdCaches,
                                                 update_calibre_isbn_if_required)
from calibre_plugins.goodreads_sync.dialogs import (DoAddRemoveDialog, DoShelfSyncDialog, SwitchEditionDialog,
                                            PickGoodreadsBookDialog, ActionStatus, ChooseShelvesToSyncDialog,
                                            UpdateReadingProgressDialog)

PLUGIN_ICONS = ['images/goodreads_sync.png',        'images/refresh.png',
                'images/shelf.png',                 'images/shelf_exclusive.png',
                'images/add_to_shelf.png',          'images/remove_from_shelf.png',
                'images/sync_from_shelf.png',       'images/sync_from_shelf_lg.png',
                'images/add_to_shelf_lg.png',       'images/remove_from_shelf_lg.png',
                'images/view_book.png',             'images/view_shelf.png',
                'images/edit_shelf_add_action.png', 'images/edit_shelf_add_action_lg.png',
                'images/edit_sync_action.png',      'images/edit_sync_action_lg.png',
                'images/link.png',                  'images/link_add.png',
                'images/link_add_lg.png',           'images/link_delete.png',
                'images/tag_maps_lg.png',           'images/authorise.png',
                'images/tags_download.png',         'images/tags_upload.png',
                'images/rating_add.png',            'images/rating_sync.png',
                'images/dateread_add.png',          'images/dateread_sync.png',
                'images/rating_dateread_add.png',   'images/rating_dateread_sync.png',
                'images/review_add.png',            'images/review_sync.png'
                ]

class GoodreadsSyncAction(InterfaceAction):

    name = 'Goodreads Sync'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (_('Goodreads'), None, None, None)
    popup_type = QToolButton.InstantPopup
    action_type = 'current'
    pb = None

    def genesis(self):
        self.menu = QMenu(self.gui)

        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)

        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.menu.aboutToShow.connect(self.about_to_show_menu)

    def initialization_complete(self):
        self.grhttp = HttpHelper(self.gui, self)
        self.id_caches = IdCaches(self.gui)
        self.calibre_searcher = CalibreSearcher(self.id_caches)
        self.rebuild_menus()

    def library_changed(self, db):
        # We need to invalidate our caches and references when the library is changed
        # so that we do not write data into the wrong database.
        self.id_caches.invalidate_caches()

    def rebuild_menus(self):
        # Ensure any keyboard shortcuts from previous display of plugin menu are cleared
        unregister_menu_actions(self)

        self.users = cfg.plugin_prefs[cfg.STORE_USERS]
        c = cfg.plugin_prefs[cfg.STORE_PLUGIN]
        m = self.menu
        m.clear()
        
        # Only display action submenus if a user has been defined via config dialog
        if len(self.users) > 0:
            # Create menu items for the Add to shelf items
            if c.get(cfg.KEY_DISPLAY_ADD, True):
                self.create_action_with_users_sub_menu(m, _('Add to shelf')+'...', 'add', 'images/add_to_shelf.png')
            if c.get(cfg.KEY_DISPLAY_REMOVE, True):
                self.create_action_with_users_sub_menu(m, _('Remove from shelf')+'...', 'remove', 'images/remove_from_shelf.png')
            if c.get(cfg.KEY_DISPLAY_UPDATE_PROGRESS, True):
                self.create_action_with_users_sub_menu(m, _('Update reading progress')+'...', 'progress', 'images/remove_from_shelf.png')
            if c.get(cfg.KEY_DISPLAY_SYNC, True):
                m.addSeparator()
                self.create_action_with_users_sub_menu(m, _('Sync from shelf')+'...', 'sync', 'images/sync_from_shelf.png')
            if c.get(cfg.KEY_DISPLAY_VIEW_SHELF, True):
                m.addSeparator()
                self.create_sub_menu_for_users_action(m, _('View shelf'), 'view', 'images/view_shelf.png')
            m.addSeparator()

            # Create menus for linking to Goodreads and working with linked books
            create_menu_action_unique(self, m, _('Link to Goodreads')+'...', 'images/link_add.png',
                    _('Add, replace or clear link to a Goodreads book'),
                    triggered=self.search_goodreads_to_link_book)
            self.linked_book_submenu = m.addMenu(get_icon('images/link.png'), _('Linked book'))

            create_menu_action_unique(self, self.linked_book_submenu, _('View linked book'),
                    'images/view_book.png', _('Open a web browser page showing the linked Goodreads book'),
                    triggered=self.view_linked_books)
            create_menu_action_unique(self, self.linked_book_submenu, _('Switch Goodreads Edition')+'...',
                    'images/link_add.png', _('Link to a different edition of a Goodreads book'),
                    triggered=self.switch_linked_edition)
            self.linked_book_submenu.addSeparator()

            self.create_shelves_tags_menu_item(self.linked_book_submenu)
            self.linked_book_submenu.addSeparator()

            create_menu_action_unique(self, self.linked_book_submenu, _('Remove link'),
                    'images/link_delete.png', _('Clear the link with Goodreads'),
                    triggered=self.remove_links)

        m.addSeparator()
        create_menu_action_unique(self, m, _('&Customize plugin') + '...', 'config.png',
                                  shortcut=False, triggered=self.show_configuration)
        create_menu_action_unique(self, m, _('&Help'), 'help.png',
                                  shortcut=False, triggered=cfg.show_help)

        self.gui.keyboard.finalize()

    def about_to_show_menu(self):
        if hasattr(self, 'linked_book_submenu'):
            selected_linked = self.are_selected_books_linked()
            self.linked_book_submenu.setEnabled(selected_linked)

    def create_action_with_users_sub_menu(self, parent_menu, title, action, image_name):
        if len(list(self.users.keys())) > 1:
            # If we have more than one user, define a sub-menu with user names
            sub_menu = parent_menu.addMenu(get_icon(image_name), title)
            sub_menu.setStatusTip(title)
            for user_name in sorted(self.users.keys()):
                user_sub_menu = sub_menu.addMenu(get_icon('user_profile.png'), _('User: {0}').format(user_name))
                user_sub_menu.setStatusTip(user_sub_menu.title())
                unique_name = 'User "%s" %s' % (user_name, title)
                if action in ['add','remove']:
                    triggered_action = partial(self.add_or_remove_to_shelf, action, user_name)
                elif action in ['progress']:
                    triggered_action = partial(self.update_reading_progress, action, user_name)
                else:
                    triggered_action = partial(self.sync_shelves, user_name)
                create_menu_action_unique(self, user_sub_menu, user_name, image_name,
                                         shortcut_name=unique_name, unique_name=unique_name,
                                         triggered=triggered_action)
        else:
            # No user submenu so just have the action directly
            user_name = list(self.users.keys())[0]
            unique_name = 'User "%s" %s' % (user_name, title)
            if action in ['add','remove']:
                triggered_action = partial(self.add_or_remove_to_shelf, action, user_name)
            elif action in ['progress']:
                triggered_action = partial(self.update_reading_progress, action, user_name)
            else:
                triggered_action = partial(self.sync_shelves, user_name)
            create_menu_action_unique(self, parent_menu, title, image_name,
                                     shortcut_name=unique_name, unique_name=unique_name,
                                     triggered=triggered_action)

    def create_sub_menu_for_users_action(self, parent_menu, title, action, image_name):
        sub_menu = parent_menu.addMenu(get_icon(image_name), title)
        sub_menu.setStatusTip(title)
        # If we have more than one user, define a second level sub-menu with user names
        if len(self.users) > 1:
            for user_name in sorted(self.users.keys()):
                user_sub_menu = sub_menu.addMenu(get_icon('user_profile.png'), _('User: {0}').format(user_name))
                user_sub_menu.setStatusTip(user_sub_menu.title())
                self.create_sub_menu_for_shelves_action(user_sub_menu, user_name, title, action)
        else:
            user_name = list(self.users.keys())[0]
            self.create_sub_menu_for_shelves_action(sub_menu, user_name, title, action)

    def create_sub_menu_for_shelves_action(self, parent_menu, user_name, title, action):
        user_info = self.users[user_name]
        shelves = user_info.get(cfg.KEY_SHELVES)
        if shelves:
            for shelf in shelves:
                active = shelf['active']
                shelf_name = shelf['name']
                is_exclusive = shelf['exclusive']
                image_name = 'images/shelf_exclusive.png' if is_exclusive else 'images/shelf.png'
                if active:
                    unique_name = 'User "%s" %s "%s"' % (user_name, title, shelf_name)
                    ac = create_menu_action_unique(self, parent_menu, shelf_name, image_name,
                                                  shortcut_name=unique_name, unique_name=unique_name)
                    ac.triggered.connect(partial(self.grhttp.view_shelf, user_name, shelf_name))

    def create_shelves_tags_menu_item(self, parent_menu):
        # Download tags menu needs to support multiple users
        # If we have more than one user, define a second level sub-menu with user names
        if len(self.users) > 1:
            sub_menu = parent_menu.addMenu(get_icon('images/tags_download.png'), _('Download tags from shelves'))
            sub_menu.setStatusTip(_('Download shelves your book is on as tags'))
            for user_name in sorted(self.users.keys()):
                self.create_shelves_tags_action(sub_menu, user_name, _('User: {0}').format(user_name), 'user_profile.png',
                                   _('Download shelves your book is on as tags'), is_download=True,
                                   unique_name='User "%s" Download tags from shelves' % (user_name,))
            sub_menu = parent_menu.addMenu(get_icon('images/tags_upload.png'), _('Upload tags as shelves'))
            sub_menu.setStatusTip(_('Add book to shelves represented by your tags'))
            for user_name in sorted(self.users.keys()):
                self.create_shelves_tags_action(sub_menu, user_name, _('User: {0}').format(user_name), 'user_profile.png',
                                   _('Add book to shelves represented by your tags'), is_download=False,
                                   unique_name='User "%s" Upload tags as shelves' % (user_name,))
        else:
            user_name = list(self.users.keys())[0]
            self.create_shelves_tags_action(parent_menu, user_name, _('Download tags from shelves'), 'images/tags_download.png',
                                   _('Download shelves your book is on as tags'), is_download=True)
            self.create_shelves_tags_action(parent_menu, user_name, _('Upload tags as shelves'), 'images/tags_upload.png',
                                   _('Add book to shelves represented by your tags'), is_download=False)

    def create_shelves_tags_action(self, parent, user_name, title, image, tooltip, is_download, unique_name=''):
        if not unique_name:
            unique_name = 'User "%s" %s' % (user_name, title)
        if is_download:
            triggered = partial(self.download_tags, user_name)
        else:
            triggered = partial(self.upload_tags, user_name)
        create_menu_action_unique(self, parent, title, image, tooltip, unique_name=unique_name,
                                 shortcut_name=unique_name, triggered=triggered)

    def are_selected_books_linked(self):
        all_has_goodreads_id = True
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return False
        db = self.gui.library_view.model().db
        for row in rows:
            calibre_id = db.id(row.row())
            identifiers = db.get_identifiers(calibre_id, index_is_id=True)
            if 'goodreads' not in identifiers:
                all_has_goodreads_id = False
                break
        return all_has_goodreads_id

    def add_or_remove_to_shelf(self, action, user_name):
        if not self._is_valid_selection():
            return
        #if action == 'remove' and not self.warn_if_exclusive_shelf(user_name, shelf_name):
        #    return
        previous = self.gui.library_view.currentIndex()
        # Ensure our Goodreads id mapping caches are reset
        self.id_caches.invalidate_caches()
        # Convert the selected row(s) into a summarised set of books we can work with
        calibre_books = self._convert_selection_to_books()
        if not calibre_books:
            return

        # Display the books indicating which are linked allowing user to apply/cancel
        d = DoAddRemoveDialog(self.gui, self.grhttp, self.id_caches, user_name,
                              action, calibre_books)
        d.exec_()
        if d.result() == d.Accepted:
            if action == 'add':
                msg = _('Added {0} books to shelf').format(d.valid_count)
            else:
                msg = _('Removed {0} books from shelf').format(d.valid_count)

            self.progressbar_label(msg)
            self.progressbar_show(len(calibre_books))
            self._update_goodreads_ids(calibre_books, msg, previous)
        self.progressbar_hide()

    def update_reading_progress(self, action, user_name):
        if not self._is_valid_selection():
            return
        previous = self.gui.library_view.currentIndex()
        # Ensure our Goodreads id mapping caches are reset
        self.id_caches.invalidate_caches()
        # Convert the selected row(s) into a summarised set of books we can work with
        calibre_books = self._convert_selection_to_books()
        if not calibre_books:
            return

        # Display the books indicating which are linked allowing user to apply/cancel
        d = UpdateReadingProgressDialog(self.gui, self, self.grhttp, self.id_caches, user_name,
                                        action, calibre_books)

        d.exec_()
        if d.result() == d.Accepted:
            msg = _('Updated progress for {0} books').format(d.valid_count)
            self.progressbar_label(msg)
            self.progressbar_show(len(calibre_books))
            self._update_goodreads_ids(calibre_books, msg, previous)
        self.progressbar_hide()

    def sync_shelves(self, user_name):
        # Build a list of shelves that are valid to sync from
        self.progressbar(_("Syncing books from shelves"), show=False)
        shelves = self._get_shelves_valid_for_sync(user_name)
        if len(shelves) == 0:
            return error_dialog(self.gui, _('Unable to Sync'),
                                _('You must specify sync actions or columns for at least one shelf first.'), show=True)

        choose_dialog = ChooseShelvesToSyncDialog(self.gui, self, self.grhttp, user_name, shelves)
        choose_dialog.exec_()
        if choose_dialog.result() != choose_dialog.Accepted:
            return

        if choose_dialog.goodreads_shelf_books is None:
            return error_dialog(self.gui, _('Unable to Sync'),
                                _('Unable to retrieve books for selected shelves.'), show=True)

        previous = self.gui.library_view.currentIndex()
        # Ensure our Goodreads id mapping caches are reset
        self.id_caches.invalidate_caches()
        # Display the books indicating which are linked allowing user to apply/cancel
        d = DoShelfSyncDialog(self.gui, self, self.grhttp, user_name, choose_dialog.selected_shelves,
                              choose_dialog.goodreads_shelf_books, self.calibre_searcher)
        d.exec_()
        if d.result() == d.Accepted:
            msg = _('Synchronised {0} books from shelf').format(d.valid_count)
            self.progressbar(_("Syncing books from shelves"), show=False)
            self.progressbar_label(_("Updating books"))
            self.progressbar_format(_("Book: %v"))
            self.progressbar_show(len(d.goodreads_books))
            # When finally exiting, update the Goodreads Id and ISBN where any were changed
            self._update_calibre_database_ids_after_sync(d.goodreads_books)

            num_added_books = d.num_added_books
            if num_added_books > 0:
                self.gui.library_view.model().books_added(num_added_books)
                if hasattr(self.gui, 'db_images'):
                    self.gui.db_images.reset()
            updated_ids = [book['calibre_id'] for book in d.goodreads_books if book['updated']]
            if len(updated_ids) > 0:
                self.gui.library_view.model().refresh_ids(updated_ids)
                current = self.gui.library_view.currentIndex()
                self.gui.library_view.model().current_changed(current, previous)
                self.gui.tags_view.recount()
        self.progressbar_hide()

    def _update_goodreads_ids(self, calibre_books, msg, previous):
        # When finally exiting, update the Goodreads Id and ISBN where any were changed
        self._update_calibre_database_ids_for_selection(calibre_books)

        self.gui.status_bar.showMessage(msg)
        updated_ids = [book['calibre_id'] for book in calibre_books if book['updated']]
        if len(updated_ids) > 0:
            self.gui.library_view.model().refresh_ids(updated_ids)
            current = self.gui.library_view.currentIndex()
            self.gui.library_view.model().current_changed(current, previous)
            self.gui.tags_view.recount()


    def _get_shelves_valid_for_sync(self, user_name):
        # We will only allow syncing to shelves that have either actions or sync of rating/date read
        user_info = self.users[user_name]
        user_shelves = user_info.get(cfg.KEY_SHELVES, [])
        rating_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_RATING_COLUMN, None)
        date_read_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_DATE_READ_COLUMN, None)
        sync_shelves = []
        for shelf in user_shelves:
            if len(shelf.get(cfg.KEY_SYNC_ACTIONS, [])) > 0:
                sync_shelves.append(shelf)
            elif rating_column and shelf.get(cfg.KEY_SYNC_RATING, False):
                sync_shelves.append(shelf)
            elif date_read_column and shelf.get(cfg.KEY_SYNC_DATE_READ, False):
                sync_shelves.append(shelf)
        return sync_shelves

    def _update_calibre_database_ids_after_sync(self, goodreads_books):
        # Our collection of books are Goodreads books on the shelf
        db = self.gui.library_view.model().db
        gr_cache = self.id_caches.goodreads_to_calibre_ids()
        cb_cache = self.id_caches.calibre_to_goodreads_ids()
        for book in goodreads_books:
            self.progressbar_label(_("Updating book") + " %s" % book['calibre_id'])
            self.progressbar_increment()
            # As 'updated' will be used to determine whether to update the gui rows,
            # we also consider whether user changed the calibre rating, date read or review text columns
            book['updated'] = book['status'] in [ActionStatus.ADD_EMPTY, ActionStatus.VALID] \
                              or book.get('rating_changed',False) \
                              or book.get('date_read_changed',False) \
                              or book.get('review_text_changed',False)
            calibre_id = book['calibre_id']
            goodreads_id = book['goodreads_id']
            orig_calibre_id = book['orig_calibre_id']
            isbn = book['calibre_isbn']
            orig_isbn = book['orig_calibre_isbn']
            if isbn and isbn != orig_isbn:
                book['updated'] = True
                db.set_isbn(calibre_id, isbn, notify=False, commit=False)
            if calibre_id == orig_calibre_id:
                continue
            book['updated'] = True
            if calibre_id:
                # A Calibre book has been linked to a goodreads one
                db.set_identifier(calibre_id, 'goodreads', goodreads_id, commit=False)
                cb_cache[calibre_id] = goodreads_id
                # We need to maintain our in-memory cache of mapped ids.
                calibre_ids_mapped = gr_cache.get(goodreads_id, [])
                calibre_ids_mapped.append(calibre_id)
                if orig_calibre_id and orig_calibre_id in calibre_ids_mapped:
                    # Book was mapped to a different id previously. Remove old mapping if exists
                    calibre_ids_mapped.remove(orig_calibre_id)
                gr_cache[goodreads_id] = calibre_ids_mapped
            else:
                # We have "unlinked" a Calibre id. This will happen when the user chooses
                # a different Goodreads id for a Calibre book.
                db.set_identifier(orig_calibre_id, 'goodreads', '', commit=False)
                # Be careful when updating caches as may have already overwritten data
                if cb_cache[orig_calibre_id] == goodreads_id:
                    del cb_cache[orig_calibre_id]
                # We need to maintain our in-memory cache of mapped ids.
                calibre_ids_mapped = gr_cache.get(goodreads_id, [])
                calibre_ids_mapped.remove(orig_calibre_id)
                if len(calibre_ids_mapped) == 0:
                    del gr_cache[goodreads_id]
                else:
                    gr_cache[goodreads_id] = calibre_ids_mapped

        db.commit()

    def search_goodreads_to_link_book(self):
        if not self._is_valid_selection():
            return
        previous = self.gui.library_view.currentIndex()
        calibre_books = self._convert_selection_to_books()
        if not calibre_books:
            return
        # Ensure our Goodreads id mapping caches are reset
        self.id_caches.invalidate_caches()
        self.search_to_link_books(calibre_books)
        # Once iteration is complete, apply the changes to Calibre database
        self._update_calibre_database_ids_for_selection(calibre_books)
        # Refresh our view in case anything critical changed like ISBN updated etc
        updated_ids = [b['calibre_id'] for b in calibre_books]
        self.gui.library_view.model().refresh_ids(updated_ids)
        current = self.gui.library_view.currentIndex()
        self.gui.library_view.model().current_changed(current, previous)
        self.gui.tags_view.recount()

    def search_to_link_books(self, calibre_books):
        update_isbn = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_UPDATE_ISBN, 'NEVER')
        updated_ids = []
        for row, calibre_book in enumerate(calibre_books):
            isbn = calibre_book['calibre_isbn']
            title = calibre_book['calibre_title']
            author = calibre_book['calibre_author']
            goodreads_id_for_isbn = ''
            goodreads_isbn = None
            goodreads_books = []
            if isbn:
                # As we have a Calibre ISBN, lets attempt a lookup by that first
                goodreads_id_for_isbn = self.grhttp.get_goodreads_id_for_isbn(isbn)
                if goodreads_id_for_isbn:
                    goodreads_book = self.grhttp.get_goodreads_book_for_id(goodreads_id_for_isbn)
                    if goodreads_book is None:
                        # Have a really unusual situation!
                        # Lets pretend we don't have a goodreads id after all
                        goodreads_id_for_isbn = None
                    else:
                        goodreads_books = [goodreads_book]
                        goodreads_isbn = goodreads_book['goodreads_isbn']
            if len(goodreads_books) == 0:
                goodreads_books = self.grhttp.search_for_goodreads_books(title, author)
            next_book = None
            if row < len(calibre_books) - 1:
                next_book = calibre_books[row + 1]['calibre_title']

            is_isbn_match = goodreads_id_for_isbn is not None and len(goodreads_id_for_isbn) > 0
            d = PickGoodreadsBookDialog(self.gui, self.grhttp, self.id_caches, calibre_book,
                                        goodreads_books, next_book, is_isbn_match)
            d.exec_()
            if d.result() != d.Accepted:
                break
            if d.skip:
                continue
            goodreads_book = d.selected_goodreads_book()
            if goodreads_book is None:
                continue
            goodreads_id = goodreads_book['goodreads_id']
            if calibre_book['orig_goodreads_id'] != goodreads_id:
                calibre_book['goodreads_id'] = goodreads_id
            missing_isbn = not calibre_book['calibre_isbn'] and update_isbn == 'MISSING'
            if update_isbn == 'ALWAYS' or missing_isbn:
                # We will do an additional API call to get the ISBN value for this book
                # Necessary because ISBN is not returned by the Goodreads search API
                # However we "might" have already done this above
                if goodreads_id != goodreads_id_for_isbn:
                    goodreads_isbn = None
                    goodreads_book = self.grhttp.get_goodreads_book_for_id(goodreads_id)
                    if goodreads_book:
                        goodreads_isbn = goodreads_book['goodreads_isbn']
                if goodreads_isbn is not None:
                    update_calibre_isbn_if_required(calibre_book, goodreads_isbn, update_isbn)
            updated_ids.append(calibre_book['calibre_id'])
        if len(updated_ids) > 0:
            self.gui.library_view.model().refresh_ids(updated_ids)
            current = self.gui.library_view.currentIndex()
            self.gui.library_view.model().current_changed(current, current)
            self.gui.tags_view.recount()

    def _update_calibre_database_ids_for_selection(self, calibre_books):
        # Our collection of books are a selection in calibre
        db = self.gui.library_view.model().db
        _gr_cache = self.id_caches.goodreads_to_calibre_ids()
        _cb_cache = self.id_caches.calibre_to_goodreads_ids()
        for book in calibre_books:
            self.progressbar_label(_("Updating book") + " %s" % book['calibre_id'])
            self.progressbar_increment()
            book['updated'] = False
            calibre_id = book['calibre_id']
            goodreads_id = book['goodreads_id']
            orig_goodreads_id = book.get('orig_goodreads_id', None)
            isbn = book['calibre_isbn']
            orig_isbn = book['orig_calibre_isbn']
            if isbn and isbn != orig_isbn:
                db.set_isbn(calibre_id, isbn, notify=False, commit=False)
                book['updated'] = True
            if goodreads_id == orig_goodreads_id:
                continue
            db.set_identifier(calibre_id, 'goodreads', goodreads_id, notify=False, commit=False)
            book['updated'] = True
        db.commit()

    def _is_valid_selection(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return False
        if len(rows) > 50:
            error_dialog(self.gui, _('Too Many Rows'),
                _('Reduce your selection to at most 50 rows.'),
                show=True)
            return False
        return True

    def _convert_selection_to_books(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        db = self.gui.library_view.model().db
        calibre_books = []
        self.progressbar("_convert_selection_to_books")
        self.progressbar_label("testing")
        self.progressbar_show(len(rows))
        for row in rows:
            self.progressbar_increment()
            calibre_id = db.id(row.row())
            book = {}
            if not self.calibre_searcher.get_calibre_data_for_book(book, calibre_id):
                continue
            book['orig_calibre_isbn'] = book['calibre_isbn']
            book['orig_goodreads_id'] = book['goodreads_id']
            calibre_books.append(book)
        self.progressbar_hide()
        return calibre_books

    def remove_links(self):
        db = self.gui.library_view.model().db
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return
        if not question_dialog(self.gui, _('Are you sure?'), '<p>' +
                               _("Removing any linked Goodreads ids may result in you having to manually " 
                               "select the link again for these book(s).")+'<p>' +
                               _('Are you sure you want to remove the link(s)?'), show_copy_button=False):
            return
        previous = self.gui.library_view.currentIndex()
        # Ensure our Goodreads id mapping caches are reset
        self.id_caches.invalidate_caches()
        try:
            gr_cache = self.id_caches.goodreads_to_calibre_ids()
            cb_cache = self.id_caches.calibre_to_goodreads_ids()
            updated_ids = []
            self.gui.status_bar.showMessage(_('Removing Goodreads ids from books')+'...')
            for row in rows:
                calibre_id = db.id(row.row())
                db.set_identifier(calibre_id, 'goodreads', '', commit=False)
                goodreads_id = cb_cache[calibre_id]
                del cb_cache[calibre_id]
                calibre_ids_mapped = gr_cache.get(goodreads_id, [])
                calibre_ids_mapped.remove(calibre_id)
                gr_cache[goodreads_id] = calibre_ids_mapped
                updated_ids.append(calibre_id)
            db.commit()
            if len(updated_ids) > 0:
                self.gui.library_view.model().refresh_ids(updated_ids)
                current = self.gui.library_view.currentIndex()
                self.gui.library_view.model().current_changed(current, previous)
                self.gui.tags_view.recount()
        finally:
            self.gui.status_bar.clearMessage()

    def view_linked_books(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return
        db = self.gui.library_view.model().db
        for row in rows:
            calibre_id = db.id(row.row())
            identifiers = db.get_identifiers(calibre_id, index_is_id=True)
            goodreads_id = identifiers.get('goodreads', None)
            if goodreads_id:
                self.grhttp.view_book_on_goodreads(goodreads_id)

    def switch_linked_edition(self):
        if not self._is_valid_selection():
            return
        previous = self.gui.library_view.currentIndex()
        rows = self.gui.library_view.selectionModel().selectedRows()
        self.db = self.gui.library_view.model().db
        for row in rows:
            calibre_id = self.db.id(row.row())
            identifiers = self.db.get_identifiers(calibre_id, index_is_id=True)
            goodreads_id = identifiers.get('goodreads', None)
            if not goodreads_id:
                error_dialog(self.gui, _('No Goodreads Id'),
                   _('You cannot switch editions for a book that is not already linked to Goodreads.<br>'),
                   show=True)
                return
        calibre_books = self._convert_selection_to_books()
        if not calibre_books:
            return
        # Ensure our Goodreads id mapping caches are reset
        self.id_caches.invalidate_caches()
        self.switch_edition_for_linked_books(calibre_books)
        # Once iteration is complete, apply the changes to Calibre database
        self._update_calibre_database_ids_for_selection(calibre_books)
        # Refresh our view in case anything critical changed like ISBN updated etc
        updated_ids = [b['calibre_id'] for b in calibre_books]
        self.gui.library_view.model().refresh_ids(updated_ids)
        current = self.gui.library_view.currentIndex()
        self.gui.library_view.model().current_changed(current, previous)
        self.gui.tags_view.recount()

    def switch_edition_for_linked_books(self, calibre_books):
        update_isbn = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_UPDATE_ISBN, 'NEVER')
        updated_ids = []
        for row, calibre_book in enumerate(calibre_books):
            calibre_id = calibre_book['calibre_id']
            identifiers = self.db.get_identifiers(calibre_id, index_is_id=True)
            goodreads_id = identifiers.get('goodreads', None)
            # Lookup the book to get the goodreads work id to query for editions
            goodreads_book = self.grhttp.get_goodreads_book_with_work_id(goodreads_id)
            if goodreads_book is None:
                # Eeek!
                continue
            work_id = goodreads_book['goodreads_work_id']
            if work_id is None:
                # Eeek!
                continue
            # Now we need to lookup the edition information for this work id.
            # There is an API call for this, but for some reason Goodreads have it permissioned
            # that you must request access. Can't be arsed with that at the moment.
            edition_books = self.grhttp.get_edition_books_for_work_id(work_id)
            if edition_books is None:
                # Eeek!
                continue

            next_book = None
            if row < len(calibre_books) - 1:
                next_book = calibre_books[row + 1]['calibre_title']

            d = SwitchEditionDialog(self.gui, self.id_caches, calibre_book,
                                        edition_books, next_book)
            d.exec_()
            if d.result() != d.Accepted:
                break
            if d.skip:
                continue
            goodreads_book = d.selected_goodreads_book()
            if goodreads_book is None:
                continue
            goodreads_id = goodreads_book['goodreads_id']
            if calibre_book['orig_goodreads_id'] != goodreads_id:
                calibre_book['goodreads_id'] = goodreads_id
            missing_isbn = not calibre_book['calibre_isbn'] and update_isbn == 'MISSING'
            if update_isbn == 'ALWAYS' or missing_isbn:
                # We may need to do an additional API call to get the ISBN value for this book
                goodreads_isbn = goodreads_book['goodreads_isbn']
                if not goodreads_isbn:
                    goodreads_book = self.grhttp.get_goodreads_book_for_id(goodreads_id)
                    if goodreads_book:
                        goodreads_isbn = goodreads_book['goodreads_isbn']
                if goodreads_isbn is not None:
                    update_calibre_isbn_if_required(calibre_book, goodreads_isbn, update_isbn)
            updated_ids.append(calibre_id)
        if len(updated_ids) > 0:
            self.gui.library_view.model().refresh_ids(updated_ids)
            current = self.gui.library_view.currentIndex()
            self.gui.library_view.model().current_changed(current, current)
            self.gui.tags_view.recount()

    def download_tags(self, user_name, is_download):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return
        previous = self.gui.library_view.currentIndex()
        # Ensure our Goodreads id mapping caches are reset
        self.id_caches.invalidate_caches()

        user_config = cfg.plugin_prefs[cfg.STORE_USERS][user_name]
        tag_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_TAG_MAPPING_COLUMN, 'tags')
        is_multiple = True
        db = self.gui.library_view.model().db
        tag_column_label = None
        if tag_column != 'tags':
            tag_column_label = db.field_metadata.key_to_label(tag_column)
            is_multiple = db.custom_column_label_map[tag_column_label]['is_multiple']

        # Build a tag mappings dictionary by shelf name for all non zero mappings
        tag_mappings = self._get_tag_mappings(user_config)
        updated_ids = []
        for row in rows:
            calibre_id = db.id(row.row())
            goodreads_id = self.id_caches.calibre_to_goodreads_ids().get(calibre_id, None)
            if not goodreads_id:
                continue
            book = self.grhttp.get_review_book(user_name, goodreads_id)
            if not book:
                continue
            orig_calibre_tags = self._get_calibre_tags_for_book(db, calibre_id, tag_column, tag_column_label, is_multiple)
            # For a custom column we will always overwrite with fresh values
            # For the tags column we will always append
            calibre_tags = set(list(orig_calibre_tags)) if tag_column == 'tags' else set()
            for shelf_name in book['goodreads_shelves'].split(', '):
                if shelf_name not in tag_mappings:
                    continue
                calibre_tags |= set(tag_mappings[shelf_name])
            # Save if we have made any changes to this column
            if calibre_tags != orig_calibre_tags:
                if tag_column == 'tags':
                    db.set_tags(calibre_id, list(calibre_tags), append=True, commit=False)
                else:
                    if is_multiple:
                        val = list(calibre_tags)
                    else:
                        val = ', '.join(sorted(list(calibre_tags)))
                    db.set_custom(calibre_id, val, label=tag_column_label, append=False, commit=False)
                updated_ids.append(calibre_id)
        db.commit()
        if len(updated_ids) > 0:
            self.gui.library_view.model().refresh_ids(updated_ids)
            current = self.gui.library_view.currentIndex()
            self.gui.library_view.model().current_changed(current, previous)
            self.gui.tags_view.recount()
            msg = _('Updated tags for {0} books').format(len(updated_ids))
        else:
            msg = _('No books required tags updating')
        self.gui.status_bar.showMessage(msg)

    def upload_tags(self, user_name, is_download):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return
        # Ensure our Goodreads id mapping caches are reset
        self.id_caches.invalidate_caches()
        db = self.gui.library_view.model().db
        user_config = cfg.plugin_prefs[cfg.STORE_USERS][user_name]

        tag_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_TAG_MAPPING_COLUMN, 'tags')
        is_multiple = True
        tag_column_label = None
        if tag_column != 'tags':
            tag_column_label = db.field_metadata.key_to_label(tag_column)
            is_multiple = db.custom_column_label_map[tag_column_label]['is_multiple']

        # Build a tag mappings dictionary by shelf name for all non zero mappings
        tag_mappings = self._get_tag_mappings(user_config)
        shelve_additions = 0
        oauth_client = self.grhttp.create_oauth_client(user_name=user_name)
        for row in rows:
            calibre_id = db.id(row.row())
            goodreads_id = self.id_caches.calibre_to_goodreads_ids().get(calibre_id, None)
            if not goodreads_id:
                continue
            book = self.grhttp.get_review_book(user_name, goodreads_id)
            if book:
                current_shelves = book['goodreads_shelves'].split(', ')
            else:
                current_shelves = []
            calibre_tags = self._get_calibre_tags_for_book(db, calibre_id, tag_column, tag_column_label, is_multiple)
            for calibre_tag in calibre_tags:
                for shelf_name, mapped_tag_values in tag_mappings.items():
                    if calibre_tag not in mapped_tag_values:
                        continue
                    if len(mapped_tag_values) > 1:
                        # Cater for a user possibly having a 1:m relationship between shelves and tags
                        # So a paranormal-romance shelf could map to tags "Paranormal, Romance"
                        # Will require all of those tags on the Calibre book to attempt to add to shelf
                        if len(set(mapped_tag_values) - set(calibre_tags)) != 0:
                            continue
                    # Check we don't already have the book on this shelf
                    if shelf_name in current_shelves:
                        continue
                    # If we got to here then we need to add this book to the shelf.
                    current_shelves.append(shelf_name)
                    self.grhttp.add_remove_book_to_shelf(oauth_client, shelf_name, goodreads_id)
                    shelve_additions += 1
        if shelve_additions > 0:
            msg = _('Updated {0} shelves for selected books').format(shelve_additions)
        else:
            msg = _('No shelves required updating')
        self.gui.status_bar.showMessage(msg)

    def _get_calibre_tags_for_book(self, db, calibre_id, tag_column, tag_column_label, is_multiple):
        if tag_column == 'tags':
            # For a tags column we will only ever append values, as it would not be safe
            # to blow away all of the user's other tags in that column
            tags = db.tags(calibre_id, index_is_id=True)
        else:
            tags = db.get_custom(calibre_id, label=tag_column_label, index_is_id=True)
        calibre_tags = set()
        if tags is not None:
            if tag_column == 'tags':
                calibre_tags = set([t.strip() for t in tags.split(',')])
            elif is_multiple:
                calibre_tags = set(tags)
            else:
                calibre_tags = set([t.strip() for t in tags.split(',')])
        return calibre_tags

    def _get_tag_mappings(self, user_config):
        tag_mappings = {}
        for shelf in user_config[cfg.KEY_SHELVES]:
            mappings_for_shelf = shelf.get(cfg.KEY_TAG_MAPPINGS, [])
            if len(mappings_for_shelf) > 0:
                tag_mappings[shelf['name']] = mappings_for_shelf
        return tag_mappings

    def show_configuration(self):
        restart_message=_("Calibre must be restarted before the plugin can be configured.")
        # Check if a restart is needed. If the restart is needed, but the user does not
        # trigger it, the result is true and we do not do the configuration.
        if self.check_if_restart_needed(restart_message=restart_message):
            return

        self.interface_action_base_plugin.do_user_config(self.gui)
        restart_message= _("New custom colums have been created."
                            "\nYou will need to restart calibre for this change to be applied."
                        )
        self.check_if_restart_needed(restart_message=restart_message)

    def check_if_restart_needed(self, restart_message=None, restart_needed=False):
        if self.gui.must_restart_before_config or restart_needed:
            if restart_message is None:
                restart_message = _("Calibre must be restarted before the plugin can be configured.")
            from calibre.gui2 import show_restart_warning
            do_restart = show_restart_warning(restart_message)
            if do_restart:
                self.gui.quit(restart=True)
            else:
                return True
        return False

    def progressbar(self, window_title=_("Goodreads Sync progress"), on_top=False, show=False):
        self.pb = ProgressBarDialog(parent=self.gui, window_title=window_title, on_top=on_top)
        if show:
            self.pb.show()

    def progressbar_show(self, maximum_count):
        if self.pb is None:
            self.progressbar(show=True)
        self.pb.set_maximum(maximum_count)
        self.pb.set_value(0)
        self.pb.show()

    def progressbar_label(self, label):
        if self.pb is not None:
            self.pb.set_label(label)

    def progressbar_increment(self):
        if self.pb is not None:
            self.pb.increment()

    def progressbar_hide(self):
        if self.pb is not None:
            self.pb.hide()

    def progressbar_format(self, progress_format):
        if self.pb is not None:
            self.pb.set_progress_format(progress_format)
