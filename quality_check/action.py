from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import os
from functools import partial
try:
    from qt.core import QMenu, QToolButton
except:
    from PyQt5.Qt import QMenu, QToolButton

from calibre.gui2 import error_dialog
from calibre.gui2.actions import InterfaceAction

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

import calibre_plugins.quality_check.config as cfg
from calibre_plugins.quality_check.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.quality_check.common_menus import unregister_menu_actions, create_menu_action_unique
from calibre_plugins.quality_check.check_covers import CoverCheck
from calibre_plugins.quality_check.check_epub import EpubCheck
from calibre_plugins.quality_check.check_fix import FixCheck
from calibre_plugins.quality_check.check_metadata import MetadataCheck
from calibre_plugins.quality_check.check_missing import MissingDataCheck
from calibre_plugins.quality_check.check_mobi import MobiCheck
from calibre_plugins.quality_check.dialogs import ExcludeAddDialog, ExcludeViewDialog

DEFAULT_ICON = 'images/quality_check.png'

class QualityCheckAction(InterfaceAction):

    name = 'Quality Check'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (_('Quality Check'), None, None, None)
    popup_type = QToolButton.InstantPopup
    action_type = 'current'

    def genesis(self):
        self.menu = QMenu(self.gui)
        self.last_menu_key = None
        self.last_menu_cat = None

        # Build the list of plugin icons from the configuration menus
        plugin_icons = set([DEFAULT_ICON])
        for menu_config in cfg.PLUGIN_MENUS.values():
            image_name = menu_config['image']
            if image_name.startswith('images/'):
                plugin_icons.add(image_name)
        for menu_config in cfg.PLUGIN_FIX_MENUS.values():
            image_name = menu_config['image']
            if image_name.startswith('images/'):
                plugin_icons.add(image_name)
        plugin_icons.add('images/repeat_check.png')
        plugin_icons.add('images/exclude_add.png')
        plugin_icons.add('images/exclude_view.png')
        plugin_icons.add('images/scope_selection.png')

        icon_resources = self.load_resources(list(plugin_icons))
        set_plugin_icon_resources(self.name, icon_resources)

        self.rebuild_menus()

        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(DEFAULT_ICON))

    def rebuild_menus(self):
        # Ensure any keyboard shortcuts from previous display of plugin menu are cleared
        unregister_menu_actions(self)

        m = self.menu
        m.clear()
        c = cfg.plugin_prefs[cfg.STORE_OPTIONS]
        self.scope = c.get(cfg.KEY_SEARCH_SCOPE, cfg.SCOPE_LIBRARY)

        hidden_menus = c.get(cfg.KEY_HIDDEN_MENUS, [])
        last_sub_menu = None
        last_group = 0
        parent_menu = m
        for key, menu_config in cfg.PLUGIN_MENUS.items():
            if key in hidden_menus:
                continue
            sub_menu = menu_config['sub_menu']
            if sub_menu:
                if sub_menu != last_sub_menu:
                    parent_menu = m.addMenu(sub_menu)
                    last_sub_menu = sub_menu
            elif last_sub_menu:
                parent_menu = m
                last_sub_menu = None
            group = menu_config['group']
            if group != last_group:
                parent_menu.addSeparator()
            last_group = group
            shortcut_name = menu_config['name']
            if sub_menu:
                shortcut_name = sub_menu + ' -> ' + shortcut_name
            create_menu_action_unique(self, parent_menu, menu_config['name'], image=menu_config['image'],
                             tooltip=menu_config['tooltip'], shortcut_name=shortcut_name, unique_name=key,
                             triggered=partial(self.perform_check, key, menu_config['cat']))
        m.addSeparator()

        last_group = 0
        parent_menu = m.addMenu(_('Fix'))
        for key, menu_config in cfg.PLUGIN_FIX_MENUS.items():
            group = menu_config['group']
            if group != last_group:
                parent_menu.addSeparator()
            last_group = group
            shortcut_name = _('Fix -> ') + menu_config['name']
            create_menu_action_unique(self, parent_menu, menu_config['name'], image=menu_config['image'],
                             tooltip=menu_config['tooltip'], shortcut_name=shortcut_name, unique_name=key,
                             triggered=partial(self.perform_check, key, menu_config['cat']))
        m.addSeparator()

        self.repeat_check_menu = create_menu_action_unique(self, m, _('Repeat last check'), image='images/repeat_check.png',
                         tooltip=self._get_last_action_description(),
                         triggered=self.repeat_check)
        if not self.last_menu_key:
            self.repeat_check_menu.setEnabled(False)
        m.addSeparator()

        search_menu = m.addMenu(_('Search scope'))
        if self.scope == cfg.SCOPE_LIBRARY:
            search_menu.setIcon(get_icon('library.png'))
        else:
            search_menu.setIcon(get_icon('images/scope_selection.png'))
        self.scope_library_menu = create_menu_action_unique(self, search_menu, _('Library'),
                         tooltip=_('Run check against entire library, unless a search restriction is applied'),
                         shortcut_name=_('Search Scope -> Library'), unique_name='SearchScopeLibrary',
                         triggered=partial(self.change_search_scope, cfg.SCOPE_LIBRARY),
                         is_checked = bool(self.scope == cfg.SCOPE_LIBRARY))
        self.scope_selection_menu = create_menu_action_unique(self, search_menu, _('Selected book(s)'),
                         tooltip=_('Run check against selected book(s) only'),
                         shortcut_name=_('Search Scope -> Selection'), unique_name='SearchScopeSelection',
                         triggered=partial(self.change_search_scope, cfg.SCOPE_SELECTION),
                         is_checked = bool(self.scope == cfg.SCOPE_SELECTION))
        m.addSeparator()

        self.exclude_add_menu = create_menu_action_unique(self, m, _('Exclude from check')+'...', image='images/exclude_add.png',
                         tooltip=_('Exclude selected book(s) from a particular Quality Check'),
                         shortcut_name='Exclude from check', unique_name='Exclude from check',
                         triggered=self.exclude_add)
        self.exclude_view_menu = create_menu_action_unique(self, m, _('View exclusions')+'...', image='images/exclude_view.png',
                         tooltip=_('View exclusions you have added for each Quality Check'),
                         shortcut_name='View exclusions', unique_name='View exclusions',
                         triggered=self.exclude_view)
        m.addSeparator()

        create_menu_action_unique(self, m, _('&Customize plugin')+'...', 'config.png',
                                  shortcut=False, triggered=self.show_configuration)
        create_menu_action_unique(self, m, _('&Help'), 'help.png',
                                  shortcut=False, triggered=cfg.show_help)
        self.gui.keyboard.finalize()

    def perform_check(self, menu_key, menu_cat):
        if menu_cat == 'epub':
            check = EpubCheck(self.gui)
        elif menu_cat == 'mobi':
            check = MobiCheck(self.gui)
        elif menu_cat == 'covers':
            check = CoverCheck(self.gui)
        elif menu_cat == 'metadata':
            check = MetadataCheck(self.gui)
        elif menu_cat == 'missing':
            check = MissingDataCheck(self.gui)
        else:
            check = FixCheck(self.gui)

        if self.scope == cfg.SCOPE_LIBRARY:
            check.set_search_scope(self.scope, [])
        else:
            book_ids = self.gui.library_view.get_selected_ids()
            if not book_ids:
                return error_dialog(self.gui, 'No rows selected',
                                    'You must select one of more books in this search scope mode.',
                                    show=True)
            check.set_search_scope(self.scope, book_ids)

        self.last_menu_key = menu_key
        self.last_menu_cat = menu_cat
        description = self._get_last_action_description()
        self.repeat_check_menu.setToolTip(description)
        self.repeat_check_menu.setStatusTip(description)
        self.repeat_check_menu.setWhatsThis(description)
        self.repeat_check_menu.setEnabled(True)

        check.menu_key = menu_key
        check.perform_check(menu_key)

    def _get_last_action_description(self):
        for key, menu_config in cfg.PLUGIN_MENUS.items():
            if key == self.last_menu_key and menu_config['cat'] == self.last_menu_cat:
                return 'Repeat last action: ' + menu_config['name']
        return 'Repeat the last Quality Check menu action performed'

    def repeat_check(self):
        if self.last_menu_key:
            self.perform_check(self.last_menu_key, self.last_menu_cat)

    def exclude_add(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return error_dialog(self.gui, 'No rows selected',
                                'You must select one of more books to add exclusions.',
                                show=True)
        d = ExcludeAddDialog(self.gui, self.last_menu_key)
        d.exec_()
        if d.result() == d.Accepted:
            selected_ids = self.gui.library_view.get_selected_ids()
            existing_ids = cfg.get_valid_excluded_books(self.gui.current_db, d.menu_key)
            existing_ids.extend(selected_ids)
            cfg.set_excluded_books(self.gui.current_db, d.menu_key, list(set(existing_ids)))

    def exclude_view(self):
        d = ExcludeViewDialog(self.gui, self.gui.current_db, self.last_menu_key)
        d.exec_()
        if d.result() == d.Accepted:
            cfg.set_excluded_books(self.gui.current_db, d.menu_key, d.get_calibre_ids())

    def change_search_scope(self, scope):
        self.scope = scope
        prefs = cfg.plugin_prefs[cfg.STORE_OPTIONS]
        prefs[cfg.KEY_SEARCH_SCOPE] = scope
        cfg.plugin_prefs[cfg.STORE_OPTIONS] = prefs
        self.rebuild_menus()

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)
