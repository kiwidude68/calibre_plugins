from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (Qt, QWidget, QVBoxLayout, QLabel, QPushButton, QCheckBox,
                          QGroupBox, QHBoxLayout, QRadioButton, QSpinBox)
except ImportError:
    from PyQt5.Qt import (Qt, QWidget, QVBoxLayout, QLabel, QPushButton, QCheckBox,
                          QGroupBox, QHBoxLayout, QRadioButton, QSpinBox)

# Pull in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.utils.config import JSONConfig
from calibre_plugins.walk_search_history.common_dialogs import KeyboardConfigDialog

STORE_NAME = 'Shortcuts'
KEY_DEFAULT_ACTION = 'defaultAction'
KEY_LIMIT = 'limitItems'
KEY_PREVIOUS = 'gotoPrevious'
KEY_NEXT = 'gotoNext'
KEY_PER_LIBRARY = 'perLibrary'

DEFAULT_STORE_VALUES = {
    KEY_DEFAULT_ACTION: KEY_PREVIOUS,
    KEY_LIMIT: 0,
    KEY_PER_LIBRARY: False
  }

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Walk Search History')

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

        self.previous_radio = QRadioButton(_('Previous search'), self)
        self.dropdown_radio = QRadioButton(_('Dropdown menu'), self)
        group_box_default_layout.addWidget(self.previous_radio)
        group_box_default_layout.addWidget(self.dropdown_radio)

        c = plugin_prefs[STORE_NAME]
        if c[KEY_DEFAULT_ACTION] == KEY_PREVIOUS:
            self.previous_radio.setChecked(True)
        else:
            self.dropdown_radio.setChecked(True)

        limit_label = QLabel(_('Display last x searches in menu (0=Unlimited)')+':', self)
        layout.addWidget(limit_label)
        self.limit_spinbox = QSpinBox(self)
        self.limit_spinbox.setRange(0, 25)
        self.limit_spinbox.setValue(c[KEY_LIMIT])
        limit_label.setBuddy(self.limit_spinbox)
        layout.addWidget(self.limit_spinbox)

        self.per_library_checkbox = QCheckBox(_('Keep separate history per library'), self)
        self.per_library_checkbox.setToolTip(_('When checked will maintain a separate history per library\n'
                                              'when you switch between them.'))
        self.per_library_checkbox.setChecked(c.get(KEY_PER_LIBRARY, False))
        layout.addWidget(self.per_library_checkbox)

        keyboard_shortcuts_button = QPushButton(_('Keyboard shortcuts')+'...', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        layout.addWidget(keyboard_shortcuts_button)

    def save_settings(self):
        new_prefs = {}
        if self.previous_radio.isChecked():
            new_prefs[KEY_DEFAULT_ACTION] = KEY_PREVIOUS
        else:
            new_prefs[KEY_DEFAULT_ACTION] = KEY_NEXT
        new_prefs[KEY_LIMIT] = self.limit_spinbox.value()
        new_prefs[KEY_PER_LIBRARY] = self.per_library_checkbox.checkState() == Qt.Checked
        plugin_prefs[STORE_NAME] = new_prefs

    def edit_shortcuts(self):
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()
