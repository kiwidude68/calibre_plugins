from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

try:
    from qt.core import QMenu, QToolButton
except ImportError:
    from PyQt5.Qt import QMenu, QToolButton

from functools import partial
from calibre.gui2 import error_dialog, gprefs
from calibre.gui2.actions import InterfaceAction
from calibre.utils.config import prefs
from calibre.devices.usbms.driver import debug_print

import calibre_plugins.quick_preferences.config as cfg
from calibre_plugins.quick_preferences.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.quick_preferences.common_menus import unregister_menu_actions, create_menu_action_unique

# pulls in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

PLUGIN_ICONS = ['images/quick_preferences.png']

class QuickPreferencesAction(InterfaceAction):

    name = 'Quick Preferences'
    action_spec = (_('Quick Preferences'), None, None, None)
    action_type = 'current'
    popup_type = QToolButton.InstantPopup

    automerge_choices = [
                (_('Ignore duplicate incoming formats'), 'ignore'),
                (_('Overwrite existing duplicate formats'), 'overwrite'),
                (_('Create new record for each duplicate format'), 'new record')]

    def genesis(self):
        self.menu = QMenu(self.gui)

        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)

        self.rebuild_menus()

        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        # Setup hooks so that we rebuild the dropdown menus each time to represent latest history
        self.menu.aboutToShow.connect(self.about_to_show_menu)

    def rebuild_menus(self):
        # Ensure any keyboard shortcuts from previous display of plugin menu are cleared
        unregister_menu_actions(self)

        m = self.menu
        m.clear()
        cfp = cfg.plugin_prefs[cfg.STORE_FILE_PATTERN_NAME]
        ces = cfg.plugin_prefs[cfg.STORE_ENABLE_SOURCES_NAME]
        cos = cfg.plugin_prefs[cfg.STORE_OTHER_SHORTCUTS_NAME]

        # Add the file pattern regular expression menu items
        self.pattern_menus = []
        for menu_item in cfp[cfg.KEY_MENUS]:
            if menu_item[cfg.KEY_ACTIVE]:
                text = menu_item[cfg.KEY_TITLE]
                file_pattern = menu_item[cfg.KEY_REGEX]
                swap_names = menu_item[cfg.KEY_SWAP_NAMES]
                ac = create_menu_action_unique(self, m, text, tooltip=file_pattern,
                         triggered=partial(self.switch_file_pattern, file_pattern, swap_names),
                         is_checked=False, shortcut_name='Apply Add Filename Pattern: ' + text)
                self.pattern_menus.append((ac, file_pattern, swap_names))
        m.addSeparator()

        # Add the enabled metadata sources menu items
        self.sources_menus = []
        for menu_item in ces[cfg.KEY_MENUS]:
            if menu_item[cfg.KEY_ACTIVE]:
                text = menu_item[cfg.KEY_TITLE]
                sources = menu_item[cfg.KEY_SOURCES]
                ac = create_menu_action_unique(self, m, text, tooltip='Enable sources' + ', '.join(sources),
                         triggered=partial(self.enable_metadata_sources, sources),
                         shortcut_name='Enable Metadata Sources: ' + text)
                self.sources_menus.append((ac, sources))
        if len(self.sources_menus) > 0:
            m.addSeparator()

        # Add the static checkbox driven menu items
        self.swap_author_names = create_menu_action_unique(self, m, _('Swap author names'),
                        is_checked=False, shortcut_name='Toggle Add Option: Swap author names',
                        triggered=partial(self.switch_checkbox_preference, 'swap_author_names'))
        self.swap_author_names.setVisible(cos[cfg.OPT_SWAP_AUTHOR_NAMES][0])
        self.read_file_metadata = create_menu_action_unique(self, m, _('Read metadata from file contents'),
                        is_checked=False, shortcut_name='Toggle Add Option: Read metadata from file contents',
                        triggered=partial(self.switch_checkbox_preference, 'read_file_metadata'))
        self.read_file_metadata.setVisible(cos[cfg.OPT_READ_FILE_METADATA][0])
        self.add_formats_to_existing = create_menu_action_unique(self, m, _('Automerge added books if exist'),
                        is_checked=False, shortcut_name='Toggle Add Option: Automerge added books if exist',
                        triggered=partial(self.switch_checkbox_preference, 'add_formats_to_existing'))
        self.add_formats_to_existing.setVisible(cos[cfg.OPT_ADD_FORMAT_EXISTING][0])
        self.automerge_sub_menu = QMenu(_('Automerge type'), self.gui)
        if cos[cfg.OPT_ADD_FORMAT_EXISTING][0]:
            m.addMenu(self.automerge_sub_menu)
        self.automerge_menus = []
        for row, value in enumerate(self.automerge_choices):
            text, key = value
            ac = create_menu_action_unique(self, self.automerge_sub_menu, text, is_checked=False, shortcut=False,
                                           triggered=partial(self.switch_automerge_setting, key))
            self.automerge_menus.append(ac)

        # Add a menu item to invoke the standard preferences dialog
        m.addSeparator()
        create_menu_action_unique(self, m, _('Preferences')+'...', 'config.png',
                                  shortcut=False, triggered=self.open_preferences_dialog)
        create_menu_action_unique(self, m, _('&Customize plugin')+'...', 'config.png',
                                  shortcut=False, triggered=self.show_configuration)
        self.gui.keyboard.finalize()

    def about_to_show_menu(self):
        # Look to set the checked state of the file pattern menu items
        cfp = cfg.plugin_prefs[cfg.STORE_FILE_PATTERN_NAME]
        current_file_pattern = prefs['filename_pattern']

        is_swap_names_checked = prefs['swap_author_names']
        for action, file_pattern, swap_names in self.pattern_menus:
            checked = False
            if file_pattern == current_file_pattern:
                # We have a match on the regex, but it might not be our row
                if swap_names is None:
                    # This file pattern doesn't alter the swap names value
                    checked = True
                elif swap_names == is_swap_names_checked:
                    checked = True
            action.setChecked(checked)

        # Now set the checked state of other static menu items
        self.swap_author_names.setChecked(prefs['swap_author_names'])
        self.read_file_metadata.setChecked(prefs['read_file_metadata'])
        self.add_formats_to_existing.setChecked(prefs['add_formats_to_existing'])

        # Set the checked state of the automerge submenu
        automerge_type = gprefs['automerge']
        for row, action in enumerate(self.automerge_menus):
            text, key = self.automerge_choices[row]
            action.setChecked(automerge_type == key)

    def switch_file_pattern(self, file_pattern, swap_names):
        if len(file_pattern) == 0:
            return error_dialog(self.gui, _('Cannot switch regular expression'),
                        _('No regular expression specified in this menu item.'),
                        show=True)
        prefs['filename_pattern'] = file_pattern
        if swap_names is not None:
            prefs['swap_author_names'] = swap_names

    def enable_metadata_sources(self, sources):
        from calibre.customize.ui import all_metadata_plugins, enable_plugin, disable_plugin
        if len(sources) == 0:
            return error_dialog(self.gui, _('Cannot change enabled metadata sources'),
                        _('List of metadata sources is empty'),
                        show=True)
        metadata_plugins = list(all_metadata_plugins())
        for plugin in metadata_plugins:
            if plugin.name in sources:
                enable_plugin(plugin)
            else:
                disable_plugin(plugin)

    def switch_checkbox_preference(self, prefs_name):
        prefs[prefs_name] = not prefs[prefs_name]

    def switch_automerge_setting(self, automerge_type):
        gprefs['automerge'] = automerge_type

    def open_preferences_dialog(self):
        self.gui.iactions['Preferences'].do_config()

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)
