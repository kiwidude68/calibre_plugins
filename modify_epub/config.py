from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from calibre.utils.config import JSONConfig
try:
    from qt.core import (QWidget, QGridLayout, QGroupBox,  QVBoxLayout, QCheckBox)
except ImportError:
    from PyQt5.Qt import (QWidget, QGridLayout, QGroupBox,  QVBoxLayout, QCheckBox)

from calibre_plugins.modify_epub.common_dialogs import PrefsViewerDialog

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

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
     
    def save_settings(self):
        new_prefs = {}
        new_prefs[KEY_ASK_FOR_CONFIRMATION] = self.ask_for_confirmation_checkbox.isChecked()
        plugin_prefs[STORE_NAME] = new_prefs
