from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

try:
    from qt.core import (QWidget, QGridLayout, QGroupBox,  QVBoxLayout, QCheckBox, QPushButton, QUrl)
except ImportError:
    from PyQt5.Qt import (QWidget, QGridLayout, QGroupBox,  QVBoxLayout, QCheckBox, QPushButton, QUrl)

from calibre.gui2 import open_url
from calibre.utils.config import JSONConfig
from calibre_plugins.modify_epub.common_icons import get_icon
from calibre_plugins.modify_epub.common_dialogs import KeyboardConfigDialog

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/Modify-ePub'

STORE_SAVED_SETTINGS = 'SavedSettings'
STORE_NAME = 'Options'
KEY_ASK_FOR_CONFIRMATION = 'askForConfirmation'

DEFAULT_STORE_VALUES = {
                        KEY_ASK_FOR_CONFIRMATION : True
                       }

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Modify ePub')

# Set defaults
plugin_prefs.defaults[STORE_SAVED_SETTINGS] = []
plugin_prefs.defaults[STORE_NAME] = DEFAULT_STORE_VALUES

def show_help():
    open_url(QUrl(HELP_URL))

class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        
        c = plugin_prefs[STORE_NAME]
        ask_for_confirmation = c.get(KEY_ASK_FOR_CONFIRMATION, DEFAULT_STORE_VALUES[KEY_ASK_FOR_CONFIRMATION])
        
        other_group_box = QGroupBox(_('Other options:'), self)
        layout.addWidget(other_group_box)
        other_group_box_layout = QGridLayout()
        other_group_box.setLayout(other_group_box_layout)

        self.ask_for_confirmation_checkbox = QCheckBox(_('Prompt to save epubs'), self)
        self.ask_for_confirmation_checkbox.setToolTip(_('Uncheck this option if you want changes applied without '
                                                      'a confirmation dialog.'))
        self.ask_for_confirmation_checkbox.setChecked(ask_for_confirmation)
        other_group_box_layout.addWidget(self.ask_for_confirmation_checkbox, 0, 0, 1, 3)

        keyboard_shortcuts_button = QPushButton(_('Keyboard shortcuts')+'...', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        layout.addWidget(keyboard_shortcuts_button)
 
        help_button = QPushButton(' '+_('&Help'), self)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(show_help)
        layout.addWidget(help_button)
    
    def save_settings(self):
        new_prefs = {}
        new_prefs[KEY_ASK_FOR_CONFIRMATION] = self.ask_for_confirmation_checkbox.isChecked()
        plugin_prefs[STORE_NAME] = new_prefs

    def edit_shortcuts(self):
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()
