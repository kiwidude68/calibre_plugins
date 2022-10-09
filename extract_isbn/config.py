from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from collections import OrderedDict

# calibre Python 3 compatibility.
from six import text_type as unicode

try:
    from qt.core import (QWidget, QGridLayout, QLabel, QLineEdit, QPushButton, QSpinBox, 
                         QCheckBox, QHBoxLayout, QUrl)
except ImportError:
    from PyQt5.Qt import (QWidget, QGridLayout, QLabel, QLineEdit, QPushButton, QSpinBox, 
                         QCheckBox, QHBoxLayout, QUrl)

from calibre.gui2 import open_url
from calibre.utils.config import JSONConfig

from calibre_plugins.extract_isbn.common_icons import get_icon
from calibre_plugins.extract_isbn.common_dialogs import KeyboardConfigDialog
from calibre_plugins.extract_isbn.common_widgets import KeyValueComboBox

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/Extract-ISBN'

STORE_NAME = 'Options'
KEY_VALID_ISBN13_PREFIX = 'validISBN13Prefix'
KEY_POST_TASK = 'postTask'
KEY_WORKER_THRESHOLD = 'workerThreshold'
KEY_BATCH_SIZE = 'batchSize'
KEY_DISPLAY_FAILURES = 'displayFailures'
KEY_ASK_FOR_CONFIRMATION = 'askForConfirmation'

SHOW_TASKS = OrderedDict([('none', _('Do not change my search')),
                        ('updated', _('Show the books that have new or updated ISBNs'))])

DEFAULT_STORE_VALUES = {
    KEY_POST_TASK: 'none',
    KEY_VALID_ISBN13_PREFIX: ['977', '978', '979'],
    KEY_WORKER_THRESHOLD: 1,
    KEY_BATCH_SIZE: 100,
    KEY_DISPLAY_FAILURES: True,
    KEY_ASK_FOR_CONFIRMATION: True
}

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Extract ISBN')

# Set defaults
plugin_prefs.defaults[STORE_NAME] = DEFAULT_STORE_VALUES

def show_help():
    open_url(QUrl(HELP_URL))

class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QGridLayout(self)
        self.setLayout(layout)

        c = plugin_prefs[STORE_NAME]

        layout.addWidget(QLabel(_('When the scan completes:'), self), 0, 0, 1, 2)
        post_show = c.get(KEY_POST_TASK, DEFAULT_STORE_VALUES[KEY_POST_TASK])
        self.showCombo = KeyValueComboBox(self, SHOW_TASKS, post_show)
        layout.addWidget(self.showCombo, 1, 0, 1, 2)

        layout.addWidget(QLabel(_('Valid prefixes for ISBN-13 (comma separated):'), self), 2, 0, 1, 2)
        prefixes = c.get(KEY_VALID_ISBN13_PREFIX, DEFAULT_STORE_VALUES[KEY_VALID_ISBN13_PREFIX])
        self.isbn13_ledit = QLineEdit(','.join(prefixes), self)
        layout.addWidget(self.isbn13_ledit, 3, 0, 1, 2)

        lbl = QLabel(_('Selected books before running as a background job:'), self)
        lbl.setToolTip(_('Running as a background job is slower but is the only way to avoid\n') +
                       _('memory leaks and will keep the UI more responsive.'))
        layout.addWidget(lbl, 4, 0, 1, 1)
        worker_threshold = c.get(KEY_WORKER_THRESHOLD, DEFAULT_STORE_VALUES[KEY_WORKER_THRESHOLD])
        self.threshold_spin = QSpinBox(self)
        self.threshold_spin.setMinimum(0)
        self.threshold_spin.setMaximum(20)
        self.threshold_spin.setProperty('value', worker_threshold)
        layout.addWidget(self.threshold_spin, 4, 1, 1, 1)

        batch_lbl = QLabel(_('Batch size running as a background job:'), self)
        batch_lbl.setToolTip(_('Books will be broken into batches to ensure that if you run\n'
                       'extract for a large group you can cancel/close calibre without\n'
                       'losing all of your results as you can cancel the pending groups.'))
        layout.addWidget(batch_lbl, 5, 0, 1, 1)
        batch_size = c.get(KEY_BATCH_SIZE, DEFAULT_STORE_VALUES[KEY_BATCH_SIZE])
        self.batch_spin = QSpinBox(self)
        self.batch_spin.setMinimum(1)
        self.batch_spin.setMaximum(10000)
        self.batch_spin.setProperty('value', batch_size)
        layout.addWidget(self.batch_spin, 5, 1, 1, 1)

        display_failures = c.get(KEY_DISPLAY_FAILURES, DEFAULT_STORE_VALUES[KEY_DISPLAY_FAILURES])
        self.display_failures_checkbox = QCheckBox(_('Display failure dialog if ISBN not found or identical'), self)
        self.display_failures_checkbox.setToolTip(_('Uncheck this option if you want do not want to be prompted\n'
                                                        'about no ISBN being found in the book or it is the same as\n'
                                                        'your current value.'))
        self.display_failures_checkbox.setChecked(display_failures)
        layout.addWidget(self.display_failures_checkbox, 6, 0, 1, 2)

        ask_for_confirmation = c.get(KEY_ASK_FOR_CONFIRMATION, DEFAULT_STORE_VALUES[KEY_ASK_FOR_CONFIRMATION])
        self.ask_for_confirmation_checkbox = QCheckBox(_('Prompt to apply ISBN changes'), self)
        self.ask_for_confirmation_checkbox.setToolTip(_('Uncheck this option if you want changes applied without\n'
                                                        'a confirmation dialog. There is a small risk with this\n'
                                                        'option unchecked that if you are making other changes to\n'
                                                        'this book record at the same time they will be lost.'))
        self.ask_for_confirmation_checkbox.setChecked(ask_for_confirmation)
        layout.addWidget(self.ask_for_confirmation_checkbox,7, 0, 1, 2)

        button_layout = QHBoxLayout()
        keyboard_shortcuts_button = QPushButton(' '+_('Keyboard shortcuts')+'... ', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        button_layout.addWidget(keyboard_shortcuts_button)

        help_button = QPushButton(' '+_('Help'), self)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(show_help)
        button_layout.addWidget(help_button)
        layout.addLayout(button_layout, 8, 0, 1, 2)

    def save_settings(self):
        new_prefs = {}
        new_prefs[KEY_POST_TASK] = self.showCombo.selected_key()
        prefixes = unicode(self.isbn13_ledit.text()).replace(' ','')
        new_prefs[KEY_VALID_ISBN13_PREFIX] = prefixes.split(',')
        new_prefs[KEY_WORKER_THRESHOLD] = int(unicode(self.threshold_spin.value()))
        new_prefs[KEY_BATCH_SIZE] = int(unicode(self.batch_spin.value()))
        new_prefs[KEY_DISPLAY_FAILURES] = self.display_failures_checkbox.isChecked()
        new_prefs[KEY_ASK_FOR_CONFIRMATION] = self.ask_for_confirmation_checkbox.isChecked()

        plugin_prefs[STORE_NAME] = new_prefs

    def edit_shortcuts(self):
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()
