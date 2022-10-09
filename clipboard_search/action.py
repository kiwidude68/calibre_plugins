from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import QMenu, QToolButton, QApplication
except ImportError:
    from PyQt5.Qt import QMenu, QToolButton, QApplication

from six import text_type as unicode
from functools import partial

from calibre.gui2.actions import InterfaceAction

import calibre_plugins.clipboard_search.config as cfg
from calibre_plugins.clipboard_search.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.clipboard_search.common_menus import unregister_menu_actions, create_menu_action_unique

# Pull in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

PLUGIN_ICONS = ['images/clipboard_search.png', 'images/exact_search.png']

class ClipboardSearchAction(InterfaceAction):

    name = 'Clipboard Search'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (_('Clipboard Search'), None, None, None)
    popup_type = QToolButton.MenuButtonPopup
    action_type = 'current'

    def genesis(self):
        self.default_search_is_exact = False
        self.menu = QMenu(self.gui)

        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)

        self.rebuild_menus()

        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.qaction.triggered.connect(self.default_search_using_clipboard_text)

    def rebuild_menus(self):
        # Ensure any keyboard shortcuts from previous display of plugin menu are cleared
        unregister_menu_actions(self)

        c = cfg.plugin_prefs[cfg.STORE_NAME]
        m = self.menu
        m.clear()
        create_menu_action_unique(self, m, _('Text search'), shortcut='Ctrl+S',
                         triggered=partial(self.search_using_clipboard_text, is_exact_search=False))
        create_menu_action_unique(self, m, _('Exact text search'), PLUGIN_ICONS[1], shortcut='Ctrl+Shift+S',
                         triggered=partial(self.search_using_clipboard_text, is_exact_search=True))
        m.addSeparator()
        create_menu_action_unique(self, m, _('&Customize plugin')+'...', 'config.png',
                                  shortcut=False, triggered=self.show_configuration)
        create_menu_action_unique(self, m, _('&Help'), 'help.png',
                                  shortcut=False, triggered=cfg.show_help)
        self.gui.keyboard.finalize()
        # Set the desired default action for the toolbar button when clicked on
        self.default_search_is_exact = c[cfg.KEY_DEFAULT_SEARCH] == cfg.KEY_EXACT_SEARCH

    def default_search_using_clipboard_text(self):
        self.search_using_clipboard_text(is_exact_search=self.default_search_is_exact)

    def search_using_clipboard_text(self, is_exact_search=False):
        cb = QApplication.instance().clipboard()
        txt = unicode(cb.text()).strip()
        if txt:
            if is_exact_search:
                # Surround search text with quotes if it does not have any already
                if not txt.startswith('"'):
                    txt = '"' + txt
                if not txt.endswith('"'):
                    txt += '"'
            self.gui.search.set_search_string(txt, store_in_history=True)

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)
