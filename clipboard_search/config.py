from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (QWidget, QVBoxLayout, QPushButton, QUrl,
                        QGroupBox, QRadioButton, QHBoxLayout)
except ImportError:
    from PyQt5.Qt import (QWidget, QVBoxLayout, QPushButton, QUrl,
                        QGroupBox, QRadioButton, QHBoxLayout)

# Pull in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.gui2 import open_url
from calibre.utils.config import JSONConfig
from calibre_plugins.clipboard_search.common_icons import get_icon
from calibre_plugins.clipboard_search.common_dialogs import KeyboardConfigDialog

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/Clipboard-Search'

STORE_NAME = 'Shortcuts'
KEY_TEXT_SEARCH = 'textSearch'
KEY_EXACT_SEARCH = 'exactSearch'
KEY_DEFAULT_SEARCH = 'defaultSearch'

DEFAULT_STORE_VALUES = {
    KEY_DEFAULT_SEARCH: KEY_TEXT_SEARCH
}

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Clipboard Search')

# Set defaults
plugin_prefs.defaults[STORE_NAME] = DEFAULT_STORE_VALUES

class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        group_box_default = QGroupBox(_('Default action for toolbar button click')+':', self)
        layout.addWidget(group_box_default)
        group_box_default_layout = QHBoxLayout()
        group_box_default.setLayout(group_box_default_layout)

        self._text_radio = QRadioButton(_('Text search'), self)
        self._exact_radio = QRadioButton(_('Exact text search'), self)
        c = plugin_prefs[STORE_NAME]
        if c.get(KEY_DEFAULT_SEARCH) == KEY_TEXT_SEARCH:
            self._text_radio.setChecked(True)
        else:
            self._exact_radio.setChecked(True)
        group_box_default_layout.addWidget(self._text_radio)
        group_box_default_layout.addWidget(self._exact_radio)

        button_layout = QHBoxLayout()
        keyboard_shortcuts_button = QPushButton(' '+_('Keyboard shortcuts')+'... ', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        button_layout.addWidget(keyboard_shortcuts_button)

        help_button = QPushButton(' '+_('Help'), self)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(self.show_help)
        button_layout.addWidget(help_button)
        layout.addLayout(button_layout)

    def save_settings(self):
        new_prefs = {}
        if self._text_radio.isChecked():
            new_prefs[KEY_DEFAULT_SEARCH] = KEY_TEXT_SEARCH
        else:
            new_prefs[KEY_DEFAULT_SEARCH] = KEY_EXACT_SEARCH

        plugin_prefs[STORE_NAME] = new_prefs

    def edit_shortcuts(self):
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()

    def show_help(self):
        open_url(QUrl(HELP_URL))
