from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import threading, re
from collections import OrderedDict
from functools import partial

import six
from six import text_type as unicode

try:
    from qt.core import QMenu, QToolButton, pyqtSignal
except ImportError:
    from PyQt5.Qt import QMenu, QToolButton, pyqtSignal

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre import prints
from calibre.constants import DEBUG
from calibre.ebooks.metadata import authors_to_string
from calibre.gui2 import error_dialog, question_dialog, info_dialog
from calibre.gui2.actions import InterfaceAction
from calibre.gui2.device import device_signals
from calibre.gui2.dialogs.confirm_delete import confirm
from calibre.gui2.dialogs.delete_matching_from_device import DeleteMatchingFromDeviceDialog
from calibre.utils.config import tweaks

import calibre_plugins.reading_list.config as cfg
from calibre_plugins.reading_list.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.reading_list.common_menus import unregister_menu_actions, create_menu_action_unique
from calibre_plugins.reading_list.dialogs import EditListDialog, MoveBooksDialog

PLUGIN_ICONS = ['images/reading_list.png', 'images/device.png',
                'images/device_connected.png', 'images/book_sync.png',
                'images/arrow_down_double.png', 'images/arrow_down_double_bar.png',
                'images/arrow_down_single.png', 'images/arrow_up_double.png',
                'images/arrow_up_double_bar.png', 'images/arrow_up_single.png',
                'images/plusminus.png']

class ReadingListAction(InterfaceAction):

    name = 'Reading List'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (_('Reading List'), None, _('View or edit lists of books'), None)
    popup_type = QToolButton.InstantPopup
    action_type = 'current'

    plugin_device_connection_changed = pyqtSignal(object);
    plugin_device_metadata_available = pyqtSignal();

    def __init__(self, parent, site_customization):
        '''
        This plugin will uniquely have an __init__ method override, purely just to make it
        easier to test the plugin API when instantiating an ad-hoc instance via a main() func.
        '''
        InterfaceAction.__init__(self, parent, site_customization)

    def genesis(self):
        self.menus_lock = threading.RLock()
        self.sync_lock = threading.RLock()
        self.menu = QMenu(self.gui)

        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)

        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.qaction.triggered.connect(self._view_quick_access_list)
        self.menu.aboutToShow.connect(self.about_to_show_menu)

    def initialization_complete(self):
        self.connected_device_info = None
        self.view_list_name = None

        self.set_popup_mode()
        self.rebuild_menus()
        # Subscribe to device connection events
        device_signals.device_connection_changed.connect(self._on_device_connection_changed)
        device_signals.device_metadata_available.connect(self._on_device_metadata_available)
        self.sort_history = []
        self.gui.search.cleared.connect(self.restore_state)
        self.gui.search.changed.connect(self.restore_state)

    def set_popup_mode(self):
        quick_access = cfg.plugin_prefs[cfg.STORE_OPTIONS].get(cfg.KEY_QUICK_ACCESS, False)
        if quick_access:
            self.popup_type = QToolButton.MenuButtonPopup
        else:
            self.popup_type = QToolButton.InstantPopup
        for bar in self.gui.bars_manager.bars:
            w = bar.widgetForAction(self.qaction)
            if w is not None:
                w.setPopupMode(self.popup_type)
                w.update()
    
    def save_state(self):
        # Backup sort history
        self.sort_history = self.gui.library_view.get_state().get('sort_history', [])

    def restore_state(self):
        if self.view_list_name:
            list_info = cfg.get_list_info(self.gui.current_db, self.view_list_name)
            if list_info[cfg.KEY_RESTORE_SORT]:
                try:
                    max_sort_levels = min(tweaks['maximum_resort_levels'], len(self.sort_history))
                    self.gui.library_view.apply_sort_history(self.sort_history, max_sort_levels=max_sort_levels)
                    if DEBUG:
                        prints('Reading List: sort columns restored: {}'.format(self.sort_history[:max_sort_levels]))
                except Exception as e:
                    if DEBUG:
                        prints('Reading List: Error(s) when restoring sort history: {}'.format(e))
        self.view_list_name = None

    def library_about_to_change(self, olddb, db):
        self.restore_state()

    def shutting_down(self):
        self.restore_state()

    def library_changed(self, db):
        # We need to reset our menus after switching libraries
        self.rebuild_menus()
        # If a device is connected, check to see whether any lists for this library to sync
        if self.connected_device_info:
            with self.sync_lock:
                self.sync_now(force_sync=False)

    def rebuild_menus(self):
        with self.menus_lock:
            # Ensure any keyboard shortcuts from previous display of plugin menu are cleared
            unregister_menu_actions(self)
            
            m = self.menu
            m.clear()

            db = self.gui.current_db

            library = cfg.get_library_config(db)
            list_names = cfg.get_list_names(db, exclude_auto=True)
            all_list_names = cfg.get_list_names(db, exclude_auto=False)
            auto_list_names = list(set(all_list_names) - set(list_names))

            default_list_name = library[cfg.KEY_DEFAULT_LIST]
            default_list = library[cfg.KEY_LISTS][default_list_name]
            is_default_list_manual = default_list.get(cfg.KEY_POPULATE_TYPE, cfg.DEFAULT_LIST_VALUES[cfg.KEY_POPULATE_TYPE]) == 'POPMANUAL'

           # The list view menu items by default appear in a View list submenu
            # Now users can choose specific lists they want to appear at the top level rather than the submenu
            view_topmenu_names = cfg.get_view_topmenu_list_names(db)
            default_list_names_list = list([default_list_name])
            view_submenu_names = list(set(all_list_names) - set(view_topmenu_names) - set(default_list_names_list))
            view_submenu_list_names = sorted(list(set(list_names) - set(view_topmenu_names) - set(default_list_names_list)))
            view_submenu_auto_names = sorted(list(set(auto_list_names) - set(view_topmenu_names) - set(default_list_names_list)))

            # used to be just len(manual lists) > 1, but now allowing
            # auto lists to be default.
            show_sub_menus = len(list_names) > 1 or (not is_default_list_manual and len(list_names) > 0)

            std_name = _('Add to default list')
            unq_name = 'Add to default list'
            if is_default_list_manual:
                self.add_action = create_menu_action_unique(self, m, _('Add to %s list') % default_list_name,
                                                      image='plus.png', unique_name=unq_name,
                                                      shortcut_name=std_name, favourites_menu_unique_name=std_name,
                                                      triggered=partial(self._add_selected_to_list, default_list_name))
            if show_sub_menus:
                self.add_sub_menu = m.addMenu(get_icon('plus.png'), _('Add to list'))
                self.add_sub_menu.setStatusTip(_('Add to the specified list'))
                for list_name in list_names:
                    std_name = _('Add to the "%s" list') % list_name
                    unq_name = 'Add to the "%s" list' % list_name
                    create_menu_action_unique(self, self.add_sub_menu, list_name,
                                        tooltip=std_name, unique_name=unq_name, shortcut_name=std_name,
                                        favourites_menu_unique_name=_('Add to list: %s') % list_name,
                                        triggered=partial(self._add_selected_to_list, list_name))
                self.add_all_action = create_menu_action_unique(self, m, _('Add to all lists'),
                                                          unique_name='Add to all lists',
                                                          image='plus.png',
                                                          triggered=self._add_selected_to_all_lists)
            m.addSeparator()

            std_series_name = _('Add series to default list')
            unq_series_name = 'Add series to default list'
            if is_default_list_manual:
                self.add_action = create_menu_action_unique(self, m, _('Add series to %s list') % default_list_name,
                                                      image='plusplus.png', unique_name=unq_series_name,
                                                      shortcut_name=std_series_name, favourites_menu_unique_name=std_series_name,
                                                      triggered=partial(self._add_selected_series_to_list, default_list_name))
            if show_sub_menus:
                self.add_sub_menu = m.addMenu(get_icon('plusplus.png'), _('Add series to list'))
                self.add_sub_menu.setStatusTip(_('Add all books in series to the specified list'))
                for list_name in list_names:
                    std_series_name = _('Add series to the "%s" list') % list_name
                    unq_series_name = 'Add series to the "%s" list' % list_name
                    create_menu_action_unique(self, self.add_sub_menu, list_name,
                                        tooltip=std_series_name, unique_name=unq_series_name, shortcut_name=std_series_name,
                                        favourites_menu_unique_name=_('Add series to list: %s') % list_name,
                                        triggered=partial(self._add_selected_series_to_list, list_name))
                self.add_series_all_action = create_menu_action_unique(self, m, _('Add series to all lists'),
                                                          unique_name='Add series to all lists',
                                                          image='plusplus.png',
                                                          triggered=self._add_selected_series_to_all_lists)

            m.addSeparator()
            self.move_to_list_action = create_menu_action_unique(self, m, _('Move to list')+'...',
                                                        image='images/reading_list.png', unique_name='Move to list',
                                                        shortcut_name=_('Move to list'),
                                                        triggered=self._move_selected_to_list)

            m.addSeparator()
            std_name = _('Remove from default list')
            unq_name = 'Remove from default list'
            if is_default_list_manual:
                self.remove_action = create_menu_action_unique(self, m, _('Remove from %s list') % default_list_name,
                                                         image='minus.png', unique_name=unq_name,
                                                         shortcut_name=std_name, favourites_menu_unique_name=std_name,
                                                         triggered=partial(self._remove_selected_from_list, default_list_name))
            if show_sub_menus:
                self.remove_sub_menu = m.addMenu(get_icon('minus.png'), _('Remove from list'))
                self.remove_sub_menu.setStatusTip(_('Remove from the specified list'))
                for list_name in list_names:
                    std_name = _('Remove from the "%s" list') % list_name
                    unq_name = 'Remove from the "%s" list' % list_name
                    create_menu_action_unique(self, self.remove_sub_menu, list_name,
                                        tooltip=std_name, unique_name=unq_name, shortcut_name=std_name,
                                        favourites_menu_unique_name=_('Remove from list: %s') % list_name,
                                        triggered=partial(self._remove_selected_from_list, list_name))
                self.remove_all_action = create_menu_action_unique(self, m, _('Remove from all lists'),
                                                             image='minus.png',
                                                             unique_name='Remove from all lists',
                                                             triggered=self._remove_selected_from_all_lists)

            m.addSeparator()
            std_name = _('Toggle on default list')
            unq_name = 'Toggle on default list'
            if is_default_list_manual:
                self.toggle_action = create_menu_action_unique(self, m, std_name,
                                                         image=get_icon('images/plusminus.png'), unique_name=unq_name,
                                                         shortcut_name=std_name, favourites_menu_unique_name=std_name,
                                                         triggered=partial(self._toggle_selected_on_list, default_list_name))
            if show_sub_menus:
                self.toggle_sub_menu = m.addMenu(get_icon('images/plusminus.png'), _('Toggle on list'))
                self.toggle_sub_menu.setStatusTip(_('Toggle on the specified list'))
                for list_name in list_names:
                    std_name = _('Toggle on the "%s" list') % list_name
                    unq_name = 'Toggle on the "%s" list' % list_name
                    create_menu_action_unique(self, self.toggle_sub_menu, list_name,
                                        tooltip=std_name, unique_name=unq_name, shortcut_name=std_name,
                                        favourites_menu_unique_name=_('Toggle on list: %s') % list_name,
                                        triggered=partial(self._toggle_selected_on_list, list_name))

            m.addSeparator()
            list_content = library[cfg.KEY_LISTS][default_list_name][cfg.KEY_CONTENT]
            std_name = _('View default list')
            unq_name = 'View default list'
            self.view_list_action = create_menu_action_unique(self, m, _('View %s list (%d)') % (default_list_name, len(list_content)),
                                                        image='search.png', unique_name=unq_name,
                                                        shortcut_name=std_name, favourites_menu_unique_name=std_name,
                                                        triggered=partial(self.view_list, default_list_name))
            if view_topmenu_names:
                for list_name in view_topmenu_names:
                    list_content = library[cfg.KEY_LISTS][list_name][cfg.KEY_CONTENT]
                    std_name = _('View books on the "%s" list') % list_name
                    unq_name = 'View books on the "%s" list' % list_name
                    create_menu_action_unique(self, m, _('View %s list (%d)') % (list_name, len(list_content)),
                                        image='search.png',
                                        tooltip=std_name, unique_name=unq_name, shortcut_name=std_name,
                                        favourites_menu_unique_name=_('View list: %s') % list_name,
                                        triggered=partial(self.view_list, list_name))
            if view_submenu_names:
                self.view_sub_menu = m.addMenu(get_icon('search.png'), _('View list'))
                self.view_sub_menu.setStatusTip(_('View books on the specified list'))
                self.view_sub_menu_action = self.view_sub_menu.menuAction()
                self.view_sub_menu_action.favourites_menu_unique_name = _('View list')
                self.view_sub_menu_action.unique_name = 'View list'
                if view_submenu_list_names:
                    for list_name in view_submenu_list_names:
                        list_content = library[cfg.KEY_LISTS][list_name][cfg.KEY_CONTENT]
                        std_name = _('View books on the "%s" list') % list_name
                        unq_name = 'View books on the "%s" list' % list_name
                        create_menu_action_unique(self, self.view_sub_menu, '%s (%d)' % (list_name, len(list_content)),
                                            tooltip=std_name, unique_name=unq_name, shortcut_name=std_name,
                                            favourites_menu_unique_name=_('View list: %s') % list_name,
                                            triggered=partial(self.view_list, list_name))
                if view_submenu_auto_names:
                    if view_submenu_list_names:
                        self.view_sub_menu.addSeparator()
                    for list_name in view_submenu_auto_names:
                        list_content = library[cfg.KEY_LISTS][list_name][cfg.KEY_CONTENT]
                        std_name = _('View books on the "%s" list') % list_name
                        unq_name = 'View books on the "%s" list' % list_name
                        create_menu_action_unique(self, self.view_sub_menu, '%s (%d)' % (list_name, len(list_content)),
                                            tooltip=std_name, unique_name=unq_name, shortcut_name=std_name,
                                            favourites_menu_unique_name=_('View list: %s') % list_name,
                                            triggered=partial(self.view_list, list_name))

            m.addSeparator()

            std_name = _('Edit default list')
            unq_name = 'Edit default list'
            if is_default_list_manual:
                self.edit_list_action = create_menu_action_unique(self, m, _('Edit %s list') % default_list_name,
                                                        image='images/reading_list.png', unique_name=unq_name,
                                                        shortcut_name=std_name, favourites_menu_unique_name=std_name,
                                                        triggered=partial(self.edit_list, default_list_name))
            if show_sub_menus:
                self.edit_sub_menu = m.addMenu(get_icon('images/reading_list.png'), _('Edit list'))
                self.edit_sub_menu.setStatusTip(_('Edit books on the specified list'))
                for list_name in list_names:
                    std_name = _('Edit books on the "%s" list') % list_name
                    unq_name = 'Edit books on the "%s" list' % list_name
                    create_menu_action_unique(self, self.edit_sub_menu, list_name,
                                        tooltip=std_name, unique_name=unq_name, shortcut_name=unq_name,
                                        favourites_menu_unique_name=_('Edit list: %s') % list_name,
                                        triggered=partial(self.edit_list, list_name))

            m.addSeparator()
            std_name = _('Clear default list')
            unq_name = 'Clear default list'
            if is_default_list_manual:
                self.clear_action = create_menu_action_unique(self, m, _('Clear %s list') % default_list_name,
                                                     image='edit-clear.png', unique_name=unq_name,
                                                     shortcut_name=std_name, favourites_menu_unique_name=std_name,
                                                     triggered=partial(self._clear_list, default_list_name))
            if show_sub_menus:
                self.clear_sub_menu = m.addMenu(get_icon('edit-clear.png'), _('Clear list'))
                self.clear_sub_menu.setStatusTip(_('Clear all from the specified list'))
                self.clear_sub_menu_action = self.clear_sub_menu.menuAction()
                self.clear_sub_menu_action.favourites_menu_unique_name = _('Clear list')
                total_count = 0
                for list_name in list_names:
                    list_content = library[cfg.KEY_LISTS][list_name][cfg.KEY_CONTENT]
                    total_count += len(list_content)
                    std_name = _('Clear the "%s" list') % list_name
                    unq_name = 'Clear the "%s" list' % list_name
                    create_menu_action_unique(self, self.clear_sub_menu, '%s (%d)' % (list_name, len(list_content)),
                                        tooltip=std_name, unique_name=unq_name, shortcut_name=std_name,
                                        favourites_menu_unique_name=_('Clear list: %s') % list_name,
                                        triggered=partial(self._clear_list, list_name))
                self.clear_sub_menu.setTitle(_('Clear list (%d)') % total_count)

            m.addSeparator()
            if len(all_list_names) > 1:
                self.default_sub_menu = m.addMenu(get_icon('chapters.png'), _('Set default list'))
                self.default_sub_menu.setStatusTip(_('Switch the list to use as the current default'))
                for list_name in list_names:
                    is_checked = list_name == default_list_name
                    std_name = _('Set your default list to "%s"') % list_name
                    unq_name = 'Set your default list to "%s"' % list_name
                    create_menu_action_unique(self, self.default_sub_menu, list_name, is_checked=is_checked,
                                        tooltip=std_name, unique_name=unq_name, shortcut_name=std_name,
                                        favourites_menu_unique_name=_('Set default list: %s') % list_name,
                                        triggered=partial(self.switch_default_list, list_name))
                if auto_list_names:
                    self.default_sub_menu.addSeparator()
                    for list_name in auto_list_names:
                        is_checked = list_name == default_list_name
                        std_name = _('Set your default list to "%s"') % list_name
                        unq_name = 'Set your default list to "%s"' % list_name
                        create_menu_action_unique(self, self.default_sub_menu, list_name, is_checked=is_checked,
                                                 tooltip=std_name, unique_name=unq_name, shortcut_name=std_name,
                                                 favourites_menu_unique_name=_('Set default list: %s') % list_name,
                                                 triggered=partial(self.switch_default_list, list_name))
            m.addSeparator()
            self.sync_now_action = create_menu_action_unique(self, m, _('Sync Now'), 'images/book_sync.png',
                                        favourites_menu_unique_name=_('Sync Now'),
                                        unique_name='Sync Now',
                                        triggered=partial(self.sync_now, force_sync=True))
            m.addSeparator()
            create_menu_action_unique(self, m, _('&Customize plugin') + '...', 'config.png',
                                      unique_name='&Customize plugin',
                                      shortcut=False, triggered=self.show_configuration)
            create_menu_action_unique(self, m, _('&Help'), 'help.png',
                                      unique_name='&Help', shortcut=False, triggered=cfg.show_help)

            self.sync_now_action.setEnabled(False)
            if self.gui.device_manager.is_device_connected:
                sync_total = self._count_books_for_connected_device()
                self.sync_now_action.setEnabled(bool(sync_total > 0) or len(auto_list_names) > 0)
                if sync_total > 0:
                    self.sync_now_action.setText(_('Sync Now (%d)') % sync_total)

            self.gui.keyboard.finalize()
            
    def about_to_show_menu(self):
        self.rebuild_menus()
       
    def _add_selected_to_list(self, list_name):
        if list_name is None:
            return error_dialog(self.gui, _('Cannot add to list'),
                                _('No list name specified'), show=True)

        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return
        selected_ids = self.gui.library_view.get_selected_ids()
        self.add_books_to_list(list_name, selected_ids, refresh_screen=True)

    def _add_selected_to_all_lists(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return
        selected_ids = self.gui.library_view.get_selected_ids()
        self.add_books_to_all_lists(selected_ids)

    def _add_selected_series_to_list(self, list_name):
        if list_name is None:
            return error_dialog(self.gui, _('Cannot add to list'),
                                _('No list name specified'), show=True)
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return
        selected_ids = self.gui.library_view.get_selected_ids()
        series_ids = self._get_ids_for_books_in_same_series(selected_ids)
        for book_id in series_ids:
            if book_id not in selected_ids:
                selected_ids.append(book_id)
        self.add_books_to_list(list_name, selected_ids, refresh_screen=True)

    def _add_selected_series_to_all_lists(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return
        selected_ids = self.gui.library_view.get_selected_ids()
        series_ids = self._get_ids_for_books_in_same_series(selected_ids)
        for book_id in series_ids:
            if book_id not in selected_ids:
                selected_ids.append(book_id)
        self.add_books_to_all_lists(selected_ids)

    def _get_ids_for_books_in_same_series(self, ids_list):
        extraids = set()
        unique_series = set()
        db = self.gui.current_db
        for book_id in ids_list:
            # Get the current metadata for this book from the db
            mi = db.get_metadata(book_id, index_is_id=True, get_cover=False)
            if mi.series is not None:
                unique_series.add(mi.series)
        # Now find all the books for each series
        for series in unique_series:
            search = 'series:"=' + series + '"'
            series_book_ids = db.search_getting_ids(search, '')
            extraids |= set(series_book_ids)
        return extraids

    def _remove_selected_from_list(self, list_name):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return
        selected_ids = self.gui.library_view.get_selected_ids()
        self.remove_books_from_list(list_name, selected_ids, refresh_screen=True)

    def _remove_selected_from_all_lists(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return
        selected_ids = self.gui.library_view.get_selected_ids()
        self.remove_books_from_all_lists(selected_ids)
       
    def _toggle_selected_on_list(self, list_name):
        if list_name is None:
            return error_dialog(self.gui, _('Cannot toggle on list'),
                                _('No list name specified'), show=True)

        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return
        selected_ids = self.gui.library_view.get_selected_ids()
        self.toggle_books_on_list(list_name, selected_ids, refresh_screen=True)

    def _move_selected_to_list(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return
        selected_ids = self.gui.library_view.get_selected_ids()
        # Identify all the lists(s) the selected books are on if any.
        db = self.gui.current_db
        list_names = sorted(cfg.get_list_names(db))

        lists_in_use = []
        for list_name in list_names:
            book_ids = cfg.get_book_list(db, list_name)
            id_map = dict([(book_id, True) for book_id in book_ids])
            for book_id in selected_ids:
                if book_id in id_map:
                    lists_in_use.append(list_name)
                    break

        # Prompt user to figure out which lists to remove from and move to
        d = MoveBooksDialog(self.gui, lists_in_use, list_names)
        d.exec_()
        if d.result() != d.Accepted:
            return
        source_list_names = d.get_source_list_names()
        dest_list_names = d.get_dest_list_names()
        self.move_books_to_lists(source_list_names, dest_list_names, selected_ids)

    def _clear_list(self, list_name):
        if not question_dialog(self.gui, _('Are you sure?'), '<p>' +
                _('Are you sure you want to clear the \'%s\' reading list?') % list_name,
                show_copy_button=False):
            return
        self.clear_list(list_name)

    def _view_quick_access_list(self):
        library = cfg.get_library_config(self.gui.current_db)
        list_name = library.get(cfg.KEY_QUICK_ACCESS_LIST, 'Default')
        if list_name == 'Default':
            list_name = library.get(cfg.KEY_DEFAULT_LIST, None)
        if list_name:
            self.view_list(list_name)

    def get_list_names(self, exclude_auto=True):
        '''
        This method is designed to be called from other plugins
        It is a convenience wrapper to return a sorted list of reading list names
        exclude_auto - controls whether to exclude automatically generated device lists
                       which cannot be added/removed from manually.
        '''
        return cfg.get_list_names(self.gui.current_db, exclude_auto)

    def get_book_list(self, list_name):
        '''
        This method is designed to be called from other plugins
        It is a convenience wrapper to return the contents of a list by name in current db
        Returns a list containing calibre ids of books on this list
        '''
        return cfg.get_book_list(self.gui.current_db, list_name)

    def toggle_books_on_list(self, list_name, book_id_list, refresh_screen=True, display_warnings=True):
        '''
        This method is designed to be called from other plugins
        list_name - must be a valid list name
        book_id_list - list of calibre book ids to be added if not on list otherwise removed
        refresh_screen - indicates whether to refresh the book details displayed in library view
        display_warnings - option to suppress any error/warning dialogs if books already on list
        '''
        if refresh_screen:
            previous = self.gui.library_view.currentIndex()
        db = self.gui.current_db

        with self.sync_lock:
            book_ids = cfg.get_book_list(db, list_name)
            id_map = OrderedDict([(book_id, True) for book_id in book_ids])
            new_ids = []
            removed_ids = []
            for calibre_id in book_id_list:
                if calibre_id not in id_map:
                    new_ids.append(calibre_id)
                    book_ids.append(calibre_id)
                else:
                    removed_ids.append(calibre_id)
                    book_ids.remove(calibre_id)

            cfg.set_book_list(db, list_name, book_ids)

            # Add /remove tags to the books if necessary
            any_tags_changed = False
            if new_ids:
                any_tags_changed |= self.apply_tags_to_list(list_name, new_ids, add=True)
            if removed_ids:
                any_tags_changed |= self.apply_tags_to_list(list_name, removed_ids, add=False)
            changed_series_id_list = self.update_series_custom_column(list_name, book_ids)

            if refresh_screen:
                message = _('Added %d books, removed %d books on your %s list') % (len(new_ids), len(removed_ids), list_name)
                self.gui.status_bar.showMessage(message, 3000)
                if any_tags_changed:
                    refresh_book_ids = set(changed_series_id_list).union(set(book_id_list))
                    self.gui.library_view.model().refresh_ids(refresh_book_ids)
                    current = self.gui.library_view.currentIndex()
                    self.gui.library_view.model().current_changed(current, previous)
                    self.gui.tags_view.recount()
            return True

    def add_books_to_list(self, list_name, book_id_list, refresh_screen=True, display_warnings=True):
        '''
        This method is designed to be called from other plugins
        list_name - must be a valid list name
        book_id_list - list of calibre book ids to be added
        refresh_screen - indicates whether to refresh the book details displayed in library view
        display_warnings - option to suppress any error/warning dialogs if books already on list
        '''
        if refresh_screen:
            previous = self.gui.library_view.currentIndex()
        db = self.gui.current_db

        with self.sync_lock:
            book_ids = cfg.get_book_list(db, list_name)
            id_map = OrderedDict([(book_id, True) for book_id in book_ids])
            new_ids = []
            for calibre_id in book_id_list:
                if calibre_id not in id_map:
                    new_ids.append(calibre_id)
                    book_ids.append(calibre_id)

            if not new_ids:
                if display_warnings:
                    return confirm(_('The selected book(s) already exist on this list: <b>%s</b>') % list_name,
                                'reading_list_already_on_list', self.gui,
                                title=_('Failed to add to list'))
                return False
            cfg.set_book_list(db, list_name, book_ids)

            # Add tags to the books if necessary
            any_tags_changed = self.apply_tags_to_list(list_name, new_ids, add=True)
            changed_series_id_list = self.update_series_custom_column(list_name, book_ids)

            if refresh_screen:
                message = _('Added %d books to your %s list') % (len(new_ids), list_name)
                self.gui.status_bar.showMessage(message, 3000)
                if any_tags_changed:
                    refresh_book_ids = set(changed_series_id_list).union(set(new_ids))
                    self.gui.library_view.model().refresh_ids(refresh_book_ids)
                    current = self.gui.library_view.currentIndex()
                    self.gui.library_view.model().current_changed(current, previous)
                    self.gui.tags_view.recount()
            return True

    def add_books_to_all_lists(self, book_id_list, refresh_screen=True):
        '''
        This method is designed to be called from other plugins
        book_id_list - list of calibre book ids to be added
        refresh_screen - indicates whether to refresh the book details displayed in library view
        '''
        if refresh_screen:
            previous = self.gui.library_view.currentIndex()
        db = self.gui.current_db

        with self.sync_lock:
            list_names = cfg.get_list_names(db)
            updated_lists = 0
            any_tags_changed = False
            changed_series_ids = set()
            for list_name in list_names:
                book_ids = cfg.get_book_list(db, list_name)
                id_map = OrderedDict([(book_id, True) for book_id in book_ids])
                new_ids = []
                for calibre_id in book_id_list:
                    if calibre_id not in id_map:
                        new_ids.append(calibre_id)
                        book_ids.append(calibre_id)
                if new_ids:
                    updated_lists += 1
                    cfg.set_book_list(db, list_name, book_ids)
                    # Add tags to the books if necessary
                    any_tags_changed |= self.apply_tags_to_list(list_name, new_ids, add=True)
                changed_series_id_list = self.update_series_custom_column(list_name, book_ids)
                changed_series_ids.union(set(changed_series_id_list))

            if refresh_screen and updated_lists:
                message = _('Added to %d reading lists') % updated_lists
                self.gui.status_bar.showMessage(message, 3000)
                if any_tags_changed:
                    refresh_book_ids = changed_series_ids.union(set(book_id_list))
                    self.gui.library_view.model().refresh_ids(refresh_book_ids)
                    current = self.gui.library_view.currentIndex()
                    self.gui.library_view.model().current_changed(current, previous)
                    self.gui.tags_view.recount()
            return True

    def remove_books_from_list(self, list_name, book_id_list, refresh_screen=True, display_warnings=True):
        '''
        This method is designed to be called from other plugins
        list_name - must be a valid list name
        book_id_list - should be a list of calibre book ids to be removed
        refresh_screen - indicates whether to refresh the book details displayed in library view
        display_warnings - option to suppress any error/warning dialogs if books already on list
        Returns a tuple of (removed_lids_ist, any_tags_changed)
        '''
        if list_name is None:
            if display_warnings:
                return error_dialog(self.gui, _('Cannot remove from list'),
                                    _('No list name specified'), show=True)
            return None, False

        if refresh_screen:
            previous = self.gui.library_view.currentIndex()
        db = self.gui.current_db

        with self.sync_lock:
            book_ids = cfg.get_book_list(db, list_name)
            id_map = OrderedDict([(book_id, True) for book_id in book_ids])
            removed_ids = []
            for calibre_id in book_id_list:
                if calibre_id in id_map:
                    removed_ids.append(calibre_id)
                    book_ids.remove(calibre_id)

            if not removed_ids:
                if display_warnings:
                    confirm(_('The selected book(s) do not exist on this list'),
                                'reading_list_not_on_list', self.gui)
                return None, False
            cfg.set_book_list(db, list_name, book_ids)

            # Remove tags from the books if necessary
            any_tags_changed = self.apply_tags_to_list(list_name, removed_ids, add=False)
            changed_series_id_list = self.update_series_custom_column(list_name, book_ids)

            if refresh_screen:
                message = _('Removed %d books from your %s list') % (len(removed_ids), list_name)
                self.gui.status_bar.showMessage(message)
                if any_tags_changed:
                    self.gui.tags_view.recount()
                if unicode(self.gui.search.text()).startswith('marked:reading_list_'):
                    self.view_list(list_name)
                else:
                    refresh_book_ids = set(changed_series_id_list).union(set(removed_ids))
                    self.gui.library_view.model().refresh_ids(refresh_book_ids)
                    current = self.gui.library_view.currentIndex()
                    self.gui.library_view.model().current_changed(current, previous)
                return None, False
            else:
                return (removed_ids, any_tags_changed)

    def remove_books_from_all_lists(self, book_id_list, refresh_screen=True):
        '''
        This method is designed to be called from other plugins
        book_id_list - should be a list of calibre book ids to be removed
        refresh_screen - indicates whether to refresh the book details displayed in library view
        '''
        if refresh_screen:
            previous = self.gui.library_view.currentIndex()
        db = self.gui.current_db

        with self.sync_lock:
            list_names = cfg.get_list_names(db)
            updated_lists = 0
            any_tags_changed = False
            changed_series_ids = set()
            for list_name in list_names:
                book_ids = cfg.get_book_list(db, list_name)
                id_map = OrderedDict([(book_id, True) for book_id in book_ids])
                removed_ids = []
                for calibre_id in book_id_list:
                    if calibre_id in id_map:
                        removed_ids.append(calibre_id)
                        book_ids.remove(calibre_id)
                if removed_ids:
                    updated_lists += 1
                    cfg.set_book_list(db, list_name, book_ids)
                    # Add tags to the books if necessary
                    any_tags_changed |= self.apply_tags_to_list(list_name, removed_ids, add=False)
                changed_series_id_list = self.update_series_custom_column(list_name, book_ids)
                changed_series_ids.union(set(changed_series_id_list))

            if refresh_screen and updated_lists:
                message = _('Removed from %d reading lists') % updated_lists
                self.gui.status_bar.showMessage(message, 3000)
                if any_tags_changed:
                    changed_series_ids.union(set(book_id_list))
                    self.gui.library_view.model().refresh_ids(changed_series_ids)
                    current = self.gui.library_view.currentIndex()
                    self.gui.library_view.model().current_changed(current, previous)
                    self.gui.tags_view.recount()
                if unicode(self.gui.search.text()).startswith('marked:reading_list_'):
                    self.view_list(self.view_list_name)
            return True

    def move_books_to_list(self, source_list_names_list, dest_list_name, book_id_list, refresh_screen=True, display_warnings=True):
        '''
        This method is designed to be called from other plugins
        source_list_names_list - list of list names for the books to be removed from (can be empty list)
        dest_list_name - name of list the books will be moved to
        book_id_list - a list of calibre book ids to be moved from source list to dest list
        refresh_screen - indicates whether to refresh the book details displayed in library view
        display_warnings - option to suppress any error/warning dialogs for invalid list names or books on list already
        '''
        dest_list_names_list = list([dest_list_name])
        return self.move_books_to_lists(source_list_names_list, dest_list_names_list,
                                 book_id_list, refresh_screen, display_warnings)

    def move_books_to_lists(self, source_list_names_list, dest_list_names_list, book_id_list, refresh_screen=True, display_warnings=True):
        '''
        This method is designed to be called from other plugins
        source_list_names_list - list of list names for the books to be removed from (can be empty list)
        dest_list_names_list - list of list names the books will be moved to
        book_id_list - a list of calibre book ids to be moved from source list to dest list
        refresh_screen - indicates whether to refresh the book details displayed in library view
        display_warnings - option to suppress any error/warning dialogs for invalid list names or books on list already
        '''
        if source_list_names_list is None:
            if display_warnings:
                return error_dialog(self.gui, _('Cannot move to list'),
                                    _('No source list names specified'), show=True)
            return False
        if dest_list_names_list is None or len(dest_list_names_list) == 0:
            if display_warnings:
                return error_dialog(self.gui, _('Cannot move to list'),
                                    _('No list name specified'), show=True)
            return False

        db = self.gui.current_db
        if refresh_screen:
            previous = self.gui.library_view.currentIndex()
        any_tags_changed = False
        books_moved_count = 0
        for dest_list_name in dest_list_names_list:
            list_initial_count = len(cfg.get_book_list(db, dest_list_name))
            for source_list_name in source_list_names_list:
                if not source_list_name in dest_list_names_list:
                    (_removed_ids, tags_changed) = self.remove_books_from_list(source_list_name, book_id_list,
                                                                              refresh_screen=False, display_warnings=False)
                    if tags_changed:
                        any_tags_changed = True
            self.add_books_to_list(dest_list_name, book_id_list, refresh_screen=False, display_warnings=display_warnings)
            books_moved_count += len(cfg.get_book_list(db, dest_list_name)) - list_initial_count

        if book_id_list and refresh_screen:
            message = _('Moved %d books to your list(s)') % (books_moved_count,)
            self.gui.status_bar.showMessage(message, 3000)
            if any_tags_changed:
                self.gui.library_view.model().refresh_ids(book_id_list)
                current = self.gui.library_view.currentIndex()
                self.gui.library_view.model().current_changed(current, previous)
                self.gui.tags_view.recount()
            for source_list_name in source_list_names_list:
                if self._is_list_currently_viewed(source_list_name):
                    self.view_list(source_list_name)
                    break
        return True

    def clear_list(self, list_name, refresh_screen=True, display_warnings=True):
        '''
        This method is designed to be called from other plugins
        list_name - must be a valid list name
        refresh_screen - indicates whether to refresh the book details displayed in library view
        display_warnings - option to suppress any error/warning dialogs for invalid list name or list empty
        Returns a tuple of (removed_lids_ist, any_tags_changed)
        '''
        if list_name is None:
            if display_warnings:
                return error_dialog(self.gui, _('Cannot clear list'),
                                    _('No list name specified'), show=True)
            return None, False

        if refresh_screen:
            previous = self.gui.library_view.currentIndex()
        db = self.gui.current_db

        with self.sync_lock:
            removed_ids = cfg.get_book_list(db, list_name)
            if not removed_ids:
                if display_warnings:
                    confirm(_('No books exist on this list'),
                            'reading_list_clear_list_empty', self.gui)
                return None, False
            cfg.set_book_list(db, list_name, [])

            # Remove tags from the books if necessary
            any_tags_changed = self.apply_tags_to_list(list_name, removed_ids, add=False)
            changed_series_id_list = self.update_series_custom_column(list_name, [])

            if refresh_screen:
                message = _('Removed %d books from your %s list') % (len(removed_ids), list_name)
                self.gui.status_bar.showMessage(message)
                if any_tags_changed:
                    self.gui.tags_view.recount()
                if unicode(self.gui.search.text()).startswith('marked:reading_list_'):
                    self.view_list(list_name)
                else:
                    refresh_book_ids = set(changed_series_id_list).union(set(removed_ids))
                    self.gui.library_view.model().refresh_ids(refresh_book_ids)
                    current = self.gui.library_view.currentIndex()
                    self.gui.library_view.model().current_changed(current, previous)
                return None, False
            else:
                return (removed_ids, any_tags_changed)

    def edit_list(self, list_name, refresh_screen=True):
        '''
        This method is designed to be called from other plugins
        list_name - must be a valid list name
        refresh_screen - indicates whether to refresh the book details displayed in library view
        '''
        if list_name is None:
            return error_dialog(self.gui, _('Cannot edit list'),
                                _('No list name specified'), show=True)

        if refresh_screen:
            previous = self.gui.library_view.currentIndex()
        db = self.gui.current_db
        book_ids = cfg.get_book_list(db, list_name)
        books = self._convert_calibre_ids_to_books(db, book_ids)
        selected_book_ids = self.gui.library_view.get_selected_ids()

        d = EditListDialog(self.gui, books, list_name, selected_book_ids)
        d.exec_()
        if d.result() != d.Accepted:
            return
        new_book_ids = d.get_calibre_ids()
        cfg.set_book_list(db, list_name, new_book_ids)

        # Remove tags from removed books if necessary
        removed_ids = set(book_ids) - set(new_book_ids)
        any_tags_changed = self.apply_tags_to_list(list_name, removed_ids, add=False)
        changed_series_id_list = self.update_series_custom_column(list_name, new_book_ids)

        if refresh_screen and removed_ids:
            message = _('Removed %d books from your %s list') % (len(removed_ids), list_name)
            self.gui.status_bar.showMessage(message)
            if any_tags_changed:
                self.gui.tags_view.recount()
            if self._is_list_currently_viewed(list_name):
                self.view_list(list_name)
            else:
                refresh_book_ids = set(changed_series_id_list).union(set(removed_ids))
                self.gui.library_view.model().refresh_ids(refresh_book_ids)
                current = self.gui.library_view.currentIndex()
                self.gui.library_view.model().current_changed(current, previous)

    def view_list(self, list_name):
        '''
        This method is designed to be called from other plugins
        list_name - must be a valid list name
        '''
        if list_name is None:
            return error_dialog(self.gui, _('Cannot view list'),
                                _('No list name specified'), show=True)
        # In case another reading list is already displayed, otherwise
        # sort history will not be backed up properly
        self.restore_state()

        self.save_state()
        db = self.gui.current_db

        list_info = cfg.get_list_info(db, list_name)
        if list_info.get(cfg.KEY_POPULATE_TYPE, 'POPMANUAL') == 'POPSEARCH':
            self._rebuild_auto_search_list(db, list_name)

        book_ids = cfg.get_book_list(db, list_name)
        marked_text = 'reading_list_' + self._get_list_safe_name(list_name)
        marked_ids = dict()
        # Build our dictionary of list items in desired order
        for index, book_id in enumerate(book_ids):
            marked_ids[book_id] = '%s_%04d' % (marked_text, index)
        # Mark the results in our database
        db.set_marked_ids(marked_ids)
        # Search to display the list contents
        self.gui.search.set_search_string('marked:' + marked_text)
        # Sort by our marked column to display the books in order
        if list_info[cfg.KEY_SORT_LIST]:
            self.gui.library_view.sort_by_named_field('marked', True)
        self.view_list_name = list_name

    def create_list(self, list_name, book_id_list, display_warnings=True):
        '''
        This method is designed to be called from other plugins
        list_name - must be a valid list name
        book_id_list - a list of calibre book ids to be put on the list
        display_warnings - option to suppress any error/warning dialogs if books already on list
        Returns: True if list was created, otherwise False
        '''
        if list_name is None:
            if display_warnings:
                return error_dialog(self.gui, _('Cannot create list'),
                                    _('No list name specified'), show=True)
            elif DEBUG:
                print(_('Reading List: Cannot create list as list_name not specified'))
            return False
        list_names = cfg.get_list_names(self.gui.current_db, exclude_auto=False)
        for existing_list_name in list_names:
            if list_name.lower() == existing_list_name.lower():
                if display_warnings:
                    return error_dialog(self.gui, _('Cannot create list'),
                                        _('A list already exists with this name'), show=True)
                elif DEBUG:
                    print((_('Reading List: Cannot create list as list_name is duplicate:'), list_name))
                return False
        cfg.create_list(self.gui.current_db, list_name, book_id_list)
        return True

    def _get_list_safe_name(self, list_name):
        safe_name = list_name.lower().replace(' ', '_')
        safe_name = re.sub('([^a-z0-9_])', '', safe_name)
        return safe_name

    def _is_list_currently_viewed(self, list_name):
        marked_text = 'reading_list_' + self._get_list_safe_name(list_name)
        return unicode(self.gui.search.text()).startswith('marked:' + marked_text)

    def switch_default_list(self, list_name):
        cfg.set_default_list(self.gui.current_db, list_name)
        self.rebuild_menus()

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def apply_tags_to_list(self, list_name, book_ids, add=True, modify_action=None):
        db = self.gui.current_db
        list_map = cfg.get_list_info(db, list_name)
        if not modify_action:
            modify_action = list_map.get(cfg.KEY_MODIFY_ACTION, cfg.DEFAULT_LIST_VALUES[cfg.KEY_MODIFY_ACTION])
        if modify_action == 'TAGNONE':
            return False
        elif modify_action == 'TAGADD' and not add:
            return False
        elif modify_action == 'TAGREMOVE' and add:
            return False
        tags_column = list_map.get(cfg.KEY_TAGS_COLUMN, cfg.DEFAULT_LIST_VALUES[cfg.KEY_TAGS_COLUMN])
        tag_to_apply = list_map.get(cfg.KEY_TAGS_TEXT, cfg.DEFAULT_LIST_VALUES[cfg.KEY_TAGS_TEXT])
        any_tags_changed = False

        if tag_to_apply and book_ids:
            if tags_column == 'tags':
                if add:
                    db.bulk_modify_tags(book_ids, add=[tag_to_apply])
                else:
                    db.bulk_modify_tags(book_ids, remove=[tag_to_apply])
                return True
            elif tags_column:
                custom_columns = db.field_metadata.custom_field_metadata()
                col = custom_columns[tags_column]
                typ = col['datatype']
                label = db.field_metadata.key_to_label(tags_column)
                if col['is_multiple']:
                    # Will do the add or remove actions in bulk
                    if add:
                        db.set_custom_bulk_multiple(book_ids, add=[tag_to_apply], label=label)
                    else:
                        db.set_custom_bulk_multiple(book_ids, remove=[tag_to_apply], label=label)
                    return True
                else:
                    # We have a custom column that is text or boolean
                    for book_id in book_ids:
                        existing_value = db.get_custom(book_id, label=label, index_is_id=True)
                        if typ == 'bool':
                            new_value = tag_to_apply == 'Y'
                            if not add:
                                if db.prefs.get('bools_are_tristate'):
                                    new_value = None
                                else:
                                    new_value = not new_value
                        else:
                            if add:
                                new_value = tag_to_apply
                            elif existing_value:
                                new_value = existing_value.replace(tag_to_apply, '')
                            else:
                                continue # Removing but has no current text
                        if new_value != existing_value:
                            db.set_custom(book_id, new_value, label=label, commit=False)
                            any_tags_changed = True
                    db.commit()
        return any_tags_changed

    def update_series_custom_column(self, list_name, book_ids):
        changed_series_book_ids = []
        db = self.gui.current_db
        list_map = cfg.get_list_info(db, list_name)
        series_column = list_map.get(cfg.KEY_SERIES_COLUMN, cfg.DEFAULT_LIST_VALUES[cfg.KEY_SERIES_COLUMN])
        if not series_column:
            return changed_series_book_ids

        series_name = list_map.get(cfg.KEY_SERIES_NAME, cfg.DEFAULT_LIST_VALUES[cfg.KEY_SERIES_NAME])
        if not series_name:
            series_name = list_name

        custom_columns = db.field_metadata.custom_field_metadata()
        col = custom_columns.get(series_column, None)
        if col is None:
            return
        label = db.field_metadata.key_to_label(series_column)

        # Find all the books currently with this series name:
        query = '#%s:"%s"' % (label, series_name)
        existing_series_book_ids = db.data.search_getting_ids(query, search_restriction='', use_virtual_library=False)

        # Go through all the books on our list and assign the series name/index
        for idx, book_id in enumerate(book_ids):
            series_idx = idx + 1
            existing_series_name = db.get_custom(book_id, label=label, index_is_id=True)
            existing_series_idx = db.get_custom_extra(book_id, label=label, index_is_id=True)
            if series_name != existing_series_name or series_idx != existing_series_idx:
                db.set_custom(book_id, series_name, label=label, commit=False, extra=series_idx)
                changed_series_book_ids.append(book_id)
            if book_id in existing_series_book_ids:
                existing_series_book_ids.remove(book_id)

        # Any books left on the existing series list are no longer on our reading list
        for book_id in existing_series_book_ids:
            db.set_custom(book_id, '', label=label, commit=False, extra=None)
            changed_series_book_ids.append(book_id)
        db.commit()
        return changed_series_book_ids

    def _convert_calibre_ids_to_books(self, db, ids):
        books = []
        for calibre_id in ids:
            mi = db.get_metadata(calibre_id, index_is_id=True)
            book = {}
            book['calibre_id'] = mi.id
            book['title'] = mi.title
            book['author'] = authors_to_string(mi.authors)
            book['author_sort'] = mi.author_sort
            book['series'] = mi.series
            if mi.series:
                book['series_index'] = mi.series_index
            else:
                book['series_index'] = 0
            books.append(book)
        return books

    def _on_device_connection_changed(self, is_connected):
        self.plugin_device_connection_changed.emit(is_connected)
        if not is_connected:
            if DEBUG:
                prints(_('READING LIST: Device disconnected'))
            self.connected_device_info = None
            self.rebuild_menus()

    def _on_device_metadata_available(self):
        self.plugin_device_metadata_available.emit()
        self.connected_device_info = self.gui.device_manager.get_current_device_information().get('info', None)
        drive_info = self.connected_device_info[4]
        if DEBUG:
            prints(_('READING LIST: Metadata available:'), drive_info)
        self.rebuild_menus()
        with self.sync_lock:
            self.sync_now(force_sync=False)

    def _count_books_for_connected_device(self):
        db = self.gui.current_db
        all_lists_map = {}
        if self.connected_device_info:
            if not self.connected_device_info[4]:
                # Will use the device type as the UUID
                device_uuid = self.connected_device_info[0]
                lists_map = cfg.get_book_lists_for_device(db, device_uuid)
                if lists_map:
                    all_lists_map.update(lists_map)
            else:
                for location_info in six.itervalues(self.connected_device_info[4]):
                    device_uuid = location_info['device_store_uuid']
                    lists_map = cfg.get_book_lists_for_device(db, device_uuid)
                    if lists_map:
                        all_lists_map.update(lists_map)
        total_count = 0
        for list_info in all_lists_map.values():
            total_count += len(list_info[cfg.KEY_CONTENT])
        return total_count

    def _get_connected_uuids_to_sync(self):
        device_uuids = []
        if self.connected_device_info:
            if not self.connected_device_info[4]:
                # Will use the device type as the UUID
                uuid = self.connected_device_info[0]
                self._add_device_to_list_if_should_sync(device_uuids, uuid)
            else:
                for location_info in six.itervalues(self.connected_device_info[4]):
                    uuid = location_info['device_store_uuid']
                    self._add_device_to_list_if_should_sync(device_uuids, uuid)
        return device_uuids

    def _add_device_to_list_if_should_sync(self, device_uuids, uuid):
        c = cfg.plugin_prefs[cfg.STORE_DEVICES]
        device = c.get(uuid, None)
        if device:
            if device['active']:
                if DEBUG:
                    prints(_('READING LIST: Device found to sync to:'), device['name'], device['uuid'])
                device_uuids.append(uuid)
            elif DEBUG:
                prints(_('READING LIST: Not syncing to device as not active'))

    def sync_now(self, force_sync=True):
        # Identify all the active device_uuid(s) for the connected device(s)
        if DEBUG:
            prints(_('READING LIST: Sync Now - force_sync='), force_sync)
        device_uuids = self._get_connected_uuids_to_sync()
        if not device_uuids:
            return
        previous = self.gui.library_view.currentIndex()
        db = self.gui.current_db
        # Get all the ids for books already on the device so we can be sure to sync
        # only books that are not already on the device
        on_device_ids = set(db.search_getting_ids('ondevice:True', None, use_virtual_library=False))

        c = cfg.plugin_prefs[cfg.STORE_DEVICES]
        ids_changed = set()
        for device_uuid in device_uuids:
            device = c.get(device_uuid, None)
            if device is None:
                return error_dialog(self.gui, _('Cannot sync to device'),
                                    _('No device found for UUID: %s') % device_uuid, show=True)
            loc = None
            if device['location_code'] == 'A':
                loc = 'carda'
            elif device['location_code'] == 'B':
                loc = 'cardb'
            # Find all the lists that are associated with this device uuid
            lists_map = cfg.get_book_lists_for_device(db, device_uuid, exclude_auto=False)

            # Refresh the contents of any lists auto-populated by a search
            auto_pop_column_list_names = [k for k, v in six.iteritems(lists_map) if
                                   v.get(cfg.KEY_POPULATE_TYPE, 'POPMANUAL') == 'POPSEARCH']
            if auto_pop_column_list_names:
                if DEBUG:
                    prints(_('READING LIST: Updating automatic column list(s) '), auto_pop_column_list_names)
                for list_name in auto_pop_column_list_names:
                    self._rebuild_auto_search_list(db, list_name)

            # If a user has a list marked as a "Replace list" always process it first.
            replace_list_names = [k for k, v in six.iteritems(lists_map) if
                                   v.get(cfg.KEY_LIST_TYPE, 'SYNCNEW') in ['SYNCREPNEW', 'SYNREPOVR']]
            # Lists that remove are processed next
            remove_list_names = [k for k, v in six.iteritems(lists_map) if
                                   v.get(cfg.KEY_LIST_TYPE, 'SYNCNEW') == 'SYNCREM']
            # Other lists are processed last
            other_list_names = [k for k, v in six.iteritems(lists_map) if
                                   v.get(cfg.KEY_LIST_TYPE, 'SYNCNEW') not in ['SYNCREM', 'SYNCREPNEW', 'SYNREPOVR', 'SYNCAUTO']
                                   and v.get(cfg.KEY_POPULATE_TYPE, 'POPMANUAL') != 'POPDEVICE']
            combined_list_names = replace_list_names + remove_list_names + other_list_names
            # Automatic device lists built from device are built at end
            auto_device_list_names = [k for k, v in six.iteritems(lists_map) if
                                   v.get(cfg.KEY_POPULATE_TYPE, 'POPMANUAL') == 'POPDEVICE']

            change_collections = False
            for list_name in combined_list_names:
                list_info = lists_map[list_name]
                if not force_sync:
                    if not list_info[cfg.KEY_SYNC_AUTO]:
                        if DEBUG:
                            prints(_('READING LIST: Not syncing \'%s\' to device as autosync is false') % list_name)
                        continue
                change_collections, book_ids_changed, on_device_ids = self._sync_list(
                                db, list_name, list_info, device_uuid, loc, on_device_ids)
                ids_changed |= set(book_ids_changed)

            if auto_device_list_names:
                if DEBUG:
                    prints(_('READING LIST: Updating automatic device list(s) '), auto_device_list_names)
                for list_name in auto_device_list_names:
                    book_ids_changed = self._rebuild_auto_device_list(db, list_name, on_device_ids)
                    ids_changed |= set(book_ids_changed)

            # If user has a Kindle and set to update collections then do so
            if change_collections:
                create_collections = device.get('collections', False)
                if create_collections:
                    self._create_kindle_collections()
        if ids_changed:
            if unicode(self.gui.search.text()).startswith('marked:reading_list_'):
                self.view_list(list_name)
            else:
                self.gui.library_view.model().refresh_ids(ids_changed)
                current = self.gui.library_view.currentIndex()
                self.gui.library_view.model().current_changed(current, previous)
            self.gui.tags_view.recount()

    def _sync_list(self, db, list_name, list_info, device_uuid, loc, on_device_ids):
        '''
        Returns a tuple of: (change_collections, book_ids_updated, on_device_ids)
        Indicates whether the Kindle Collections plugin should be considered, and
        what ids in the gui should be refreshed to reflect changes in their tags/custom columns
        '''
        # We have the books in list_info, but if get via the cfg call then
        # any that no longer exist in the database will be removed
        ids = set(cfg.get_book_list(db, list_name))
        # Check the list type to figure out what action to take:
        list_type = list_info.get(cfg.KEY_LIST_TYPE, cfg.DEFAULT_LIST_VALUES[cfg.KEY_LIST_TYPE])
        if list_type in ['SYNCREPNEW', 'SYNCREPOVR']:
            # Remove all books on the device that are not on this list
            ids_to_remove = on_device_ids - ids
            self._remove_matching_books_from_device(db, list_name, list_info, ids_to_remove, loc, on_device_ids)
            if list_type == 'SYNCREPNEW':
                # Only add books on this list that are not already on the device
                ids = ids - on_device_ids
        elif list_type == 'SYNCREM':
            # Remove all books on this list from the device
            return self._remove_matching_books_from_device(db, list_name, list_info, ids, loc, on_device_ids)
        elif list_type == 'SYNCNEW':
            # Do not bother to sync any books that are already on the device
            ids = ids - on_device_ids

        # Will only be able to sync books that have a format
        # Any that do not we will keep in our list and not attempt to sync
        book_ids_changed = []
        no_format_ids = []
        for _id in ids:
            dbfmts = db.formats(_id, index_is_id=True)
            if not dbfmts:
                no_format_ids.append(_id)
        ids_to_sync = ids - set(no_format_ids)
        if DEBUG and no_format_ids:
            prints(_('READING LIST: Skipping %d books in \'%s\' list with no formats') % (len(no_format_ids), list_name))

        changed = False
        if ids_to_sync:
            message = _('READING LIST: Syncing %d books in \'%s\' to: %s (location:%s)') % (len(ids_to_sync),
                                                                        list_name, device_uuid, loc)
            self.gui.status_bar.showMessage(message)
            if DEBUG:
                prints(message)
            self.gui.sync_to_device(on_card=loc, delete_from_library=False, send_ids=ids_to_sync)
            on_device_ids |= ids_to_sync
            changed = True
        elif DEBUG:
            prints(_('READING LIST: No books on \'%s\' list need to be synced') % list_name)

        if list_info[cfg.KEY_SYNC_CLEAR]:
            # The difference between the old list and no_format_ids is the books updated
            remove_list_ids = set(cfg.get_book_list(db, list_name)) - set(no_format_ids)
            cfg.set_book_list(db, list_name, no_format_ids)
            self.apply_tags_to_list(list_name, remove_list_ids, add=False)
            book_ids_changed = remove_list_ids
        return changed, book_ids_changed, on_device_ids

    def _remove_matching_books_from_device(self, db, list_name, list_info, ids_to_remove, loc, on_device_ids):
        '''
        Returns a tuple of: (change_collections, book_ids_updated, on_device_ids)
        Indicates whether the Kindle Collections plugin should be considered, and
        what ids in the gui should be refreshed to reflect changes in their tags/custom columns
        '''
        if len(ids_to_remove) == 0:
            return False, [], on_device_ids
        clear_list = list_info.get(cfg.KEY_SYNC_CLEAR, cfg.DEFAULT_LIST_VALUES[cfg.KEY_SYNC_CLEAR])
        list_type = list_info.get(cfg.KEY_LIST_TYPE, cfg.DEFAULT_LIST_VALUES[cfg.KEY_LIST_TYPE])
        to_delete = {}
        # Unlike the Remove from device action in the GUI, a sync list is associated with a
        # specific storage card, so we will only look books up on that specific model
        if loc is None:
            list_model = self.gui.memory_view.model()
            list_model_name = _('Main memory')
        elif loc == 'carda':
            list_model = self.gui.card_a_view.model()
            list_model_name = _('Storage Card A')
        else:
            list_model = self.gui.card_b_view.model()
            list_model_name = _('Storage Card B')

        to_delete[list_model_name] = (list_model, list_model.paths_for_db_ids(ids_to_remove))
        if len(to_delete[list_model_name][1]) == 0:
            if DEBUG:
                prints(_('READING LIST: No books on \'%s\' list found on device to remove') % list_name)
            # Only apply the clear list action at this point if we are not working with a "Replace items" type list.
            if clear_list and list_type not in ['SYNCREPNEW', 'SYNCREPOVR']:
                cfg.set_book_list(db, list_name, [])
                # As the list has had all the synced books removed, apply tags
                self.apply_tags_to_list(list_name, ids_to_remove, add=False)
                return False, ids_to_remove, on_device_ids
            return False, [], on_device_ids

        delete_action = self.gui.iactions.get('Remove Books', None)
        if not delete_action:
            error_dialog(self.gui, _('Reading List error'),
                         _('Unable to find the Remove Books plugin'), show=True)
            return False, [], on_device_ids

        remove_dialog = cfg.plugin_prefs[cfg.STORE_OPTIONS].get(cfg.KEY_REMOVE_DIALOG, True)
        continue_delete = True
        if remove_dialog:
            (continue_delete, result) = self._get_confirmed_delete_paths(to_delete)
        else:
            result = self._get_unattended_delete_paths(to_delete)

        if continue_delete:
            paths = {}
            ids = {}
            removed_ids = []
            for (model, _id, path) in result:
                if model not in paths:
                    paths[model] = []
                    ids[model] = []
                paths[model].append(path)
                ids[model].append(_id)
                calibre_id = model.db[_id].application_id
                if calibre_id in ids_to_remove:
                    removed_ids.append(calibre_id)
            for model in paths:
                job = self.gui.remove_paths(paths[model])
                delete_action.delete_memory[job] = (paths[model], model)
                model.mark_for_deletion(job, ids[model], rows_are_ids=True)
            self.gui.status_bar.show_message(_('Deleting books from device.'), 1000)
            on_device_ids = on_device_ids - set(removed_ids)

            # Only apply the clear list action at this point if we are not working with a "Replace items" type list.
            if clear_list and list_type not in ['SYNCREPNEW', 'SYNCREPOVR']:
                # The remaining books in our list should just be those that the user
                # did not select in our dialog. So we want to discard all the ids that
                # the user removed, as well as all the ids that were not relevant
                # because the book was not found on the device.
                remaining_ids = []
                (model, books) = to_delete[list_model_name]
                for (_id, _book) in books:
                    calibre_id = list_model.db[_id].application_id
                    if calibre_id not in removed_ids:
                        remaining_ids.append(calibre_id)
                cfg.set_book_list(db, list_name, remaining_ids)
                # As the list has had at least some books removed, apply tags
                all_removed_ids = set(ids_to_remove) - set(remaining_ids)
                self.apply_tags_to_list(list_name, all_removed_ids, add=False)
            return True, removed_ids, on_device_ids
        return False, [], on_device_ids

    def _get_confirmed_delete_paths(self, to_delete):
        d = DeleteMatchingFromDeviceDialog(self.gui, to_delete)
        if d.exec_():
            return True, d.result
        return False, None

    def _get_unattended_delete_paths(self, to_delete):
        result = []
        for card in to_delete:
            (model, books) = to_delete[card]
            for (_id, book) in books:
                path = unicode(book.path)
                result.append((model, _id, path))
        return result

    def _rebuild_auto_device_list(self, db, list_name, on_device_ids):
        if DEBUG:
            prints(_('READING LIST: Auto-populating device list: '), list_name)
        existing_book_ids = set(cfg.get_book_list(db, list_name))
        ids_to_remove = list(existing_book_ids - on_device_ids)
        ids_to_add = list(on_device_ids - existing_book_ids)
        if DEBUG:
            prints(_('READING LIST: Removing %d ids from automatic list: %s') % (len(ids_to_remove), list_name))
        self.apply_tags_to_list(list_name, ids_to_remove, add=False)
        if DEBUG:
            prints(_('READING LIST: Adding %d ids to automatic list: %s') % (len(ids_to_add), list_name))
        # We will force the apply of tags to ALL items on the list, just in case the user
        # has only just specified a tag.
        self.apply_tags_to_list(list_name, list(on_device_ids), add=True)
        cfg.set_book_list(db, list_name, list(on_device_ids))
        ids_to_remove.extend(ids_to_add)
        return ids_to_remove

    def _rebuild_auto_search_list(self, db, list_name):
        if DEBUG:
            prints(_('READING LIST: Auto-populating search list: '), list_name)
        list_info = cfg.get_list_info(db, list_name)
        query = list_info.get(cfg.KEY_POPULATE_SEARCH, '')
        if not query:
            if DEBUG:
                prints(_('READING LIST: Aborting updating auto-search list as has no expression: '), list_name)
            return
        matching_ids = db.data.search_getting_ids(query, search_restriction='')
        if DEBUG:
            prints(_('READING LIST: Now %d ids on automatic list: %s') % (len(matching_ids), list_name))
        cfg.set_book_list(db, list_name, list(matching_ids))

    def _create_kindle_collections(self):
        # Check for the Kindle Collections plugin being installed
        if DEBUG:
            prints(_('READING LIST: Attempting to recreate Kindle collections'))
        plugin = self.gui.iactions.get('Kindle Collections', None)
        if not plugin:
            return info_dialog(self.gui, _('Kindle Collections Failed'),
                               _('You must have the Kindle Collections plugin installed '
                                 'in order to recreate collections after a sync.'),
                               show=True)
        else:
            plugin.create_kindle_collections()
