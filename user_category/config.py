from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from collections import OrderedDict
try:
    from qt.core import QWidget, QVBoxLayout, QCheckBox, QGroupBox, QPushButton, QHBoxLayout, QUrl
except ImportError:
    from PyQt5.Qt import QWidget, QVBoxLayout, QCheckBox, QGroupBox, QPushButton, QHBoxLayout, QUrl
from calibre.utils.config import JSONConfig
from calibre.gui2 import open_url

from calibre_plugins.user_category.common_icons import get_icon
from calibre_plugins.user_category.common_dialogs import KeyboardConfigDialog

# Pull in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/User-Category'

STORE_NAME = 'UserCategories'
MENUS_KEY = 'Menus'
OTHER_MENUS_KEY = 'OtherMenus'

DEFAULT_STORE_VALUES = {
    MENUS_KEY: { 'authors': True,
                 'series': True,
                 'publishers': False,
                 'tags': False },
    OTHER_MENUS_KEY: { 'add': True,
                       'move': True,
                       'remove': True,
                       'view': True,
                       'manage': True }
}

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/User Category')

# Set defaults
plugin_prefs.defaults[STORE_NAME] = DEFAULT_STORE_VALUES

def show_help():
    open_url(QUrl(HELP_URL))

class ConfigWidget(QWidget):

    other_display_keys  = OrderedDict([('add', _('Add to user category')),
                                       ('move', _('Move to user category')),
                                       ('remove', _('Remove from user category')),
                                       ('view', 'Show in tag browser'),
                                       ('manage', 'Manage user categories')])
    display_keys  = OrderedDict([('authors', _('Authors')),
                                 ('series', _('Series')),
                                 ('publishers', _('Publishers')),
                                 ('tags', _('Tags'))])

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        c = plugin_prefs[STORE_NAME]

        other_menus_box = QGroupBox(_('Menu actions to display:'), self)
        layout.addWidget(other_menus_box)
        other_menus_layout = QVBoxLayout()
        for key, display in list(self.other_display_keys.items()):
            enabled_checkbox = QCheckBox(display, self)
            enabled_checkbox.setChecked(c[OTHER_MENUS_KEY].get(key, True))
            setattr(self, '_other_'+key, enabled_checkbox)
            other_menus_layout.addWidget(enabled_checkbox)
        other_menus_box.setLayout(other_menus_layout)

        layout.addSpacing(10)
        menus_box = QGroupBox(_('Book metadata types to add/remove:'), self)
        layout.addWidget(menus_box)
        menus_layout = QVBoxLayout()
        for key, display in list(self.display_keys.items()):
            enabled_checkbox = QCheckBox(display, self)
            enabled_checkbox.setChecked(c[MENUS_KEY][key])
            setattr(self, '_enabled_'+key, enabled_checkbox)
            menus_layout.addWidget(enabled_checkbox)
        menus_box.setLayout(menus_layout)

        keyboard_layout = QHBoxLayout()
        layout.addLayout(keyboard_layout)
        keyboard_shortcuts_button = QPushButton(' '+_('Keyboard shortcuts')+'... ', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        keyboard_layout.addWidget(keyboard_shortcuts_button)

        help_button = QPushButton(' '+_('&Help'), self)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(show_help)
        keyboard_layout.addWidget(help_button)
        keyboard_layout.insertStretch(-1)

    def save_settings(self):
        menu_options = {}
        for key in list(self.display_keys.keys()):
            menu_options[key] = getattr(self, '_enabled_'+key).isChecked()
        other_menu_options = {}
        for key in list(self.other_display_keys.keys()):
            other_menu_options[key] = getattr(self, '_other_'+key).isChecked()
        new_prefs = { MENUS_KEY: menu_options,
                      OTHER_MENUS_KEY: other_menu_options }

        plugin_prefs[STORE_NAME] = new_prefs

    def edit_shortcuts(self):
        self.save_settings()
        # Force the menus to be rebuilt immediately, so we have all our actions registered
        self.plugin_action.rebuild_menus()
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()
