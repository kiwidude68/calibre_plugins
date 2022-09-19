from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import six, copy
from six import text_type as unicode

try:
    from qt.core import QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox, QGridLayout, QLineEdit
except ImportError:
    from PyQt5.Qt import QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox, QGridLayout, QLineEdit

# Pull in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre_plugins.cover_url.common_dialogs import KeyboardConfigDialog, PrefsViewerDialog
from calibre_plugins.cover_url.common_widgets import CustomColumnComboBox

KEY_COL_GCOVER = 'colCoverColumn'
KEY_INTERVAL = 'interval'
DEFAULT_LIBRARY_VALUES = {
                          KEY_COL_GCOVER: '',
                          KEY_INTERVAL: 15,
                         }

PREFS_NAMESPACE = 'CoverUrlPlugin'
PREFS_KEY_SETTINGS = 'settings'


def get_library_config(db):
    library_config = db.prefs.get_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS, copy.deepcopy(DEFAULT_LIBRARY_VALUES))
    return library_config

def set_library_config(db, library_config):
    db.prefs.set_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS, library_config)


class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        self.library_config = get_library_config(plugin_action.gui.current_db)
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        group_box = QGroupBox(_('Options:'), self)
        layout.addWidget(group_box)
        group_box_layout = QGridLayout()
        group_box.setLayout(group_box_layout)

        cover_avail_columns = self.get_custom_columns(['text'])
        gcover_col = self.library_config.get(KEY_COL_GCOVER, DEFAULT_LIBRARY_VALUES[KEY_COL_GCOVER])

        gcover_label = QLabel(_('&Cover URL column:'), self)
        self.gcover_col_combo = CustomColumnComboBox(self, cover_avail_columns, gcover_col)
        gcover_label.setBuddy(self.gcover_col_combo)
        group_box_layout.addWidget(gcover_label, 0, 0, 1, 1)
        group_box_layout.addWidget(self.gcover_col_combo, 0, 1, 1, 2)
        
        interval = self.library_config.get(KEY_INTERVAL, DEFAULT_LIBRARY_VALUES[KEY_INTERVAL])

        interval_label = QLabel(_('&Interval (secs):'), self)
        self.interval_lineEdit = QLineEdit(self)
        self.interval_lineEdit.setText(str(interval))
        interval_label.setBuddy(self.interval_lineEdit)
        group_box_layout.addWidget(interval_label, 1, 0, 1, 1)
        group_box_layout.addWidget(self.interval_lineEdit, 1, 1, 1, 2)

        keyboard_shortcuts_button = QPushButton(_('Keyboard shortcuts')+'...', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        layout.addWidget(keyboard_shortcuts_button)

        view_prefs_button = QPushButton(_('&View library preferences')+'...', self)
        view_prefs_button.setToolTip(_('View data stored in the library database for this plugin'))
        view_prefs_button.clicked.connect(self.view_prefs)
        layout.addWidget(view_prefs_button)

    def save_settings(self):
        self.library[KEY_COL_GCOVER] = self.gcover_col_combo.get_selected_column()
        self.library[KEY_INTERVAL] = int(unicode(self.interval_lineEdit.text()))
        set_library_config(self.plugin_action.gui.current_db, self.library)

    def get_custom_columns(self, column_types):
        custom_columns = self.plugin_action.gui.library_view.model().custom_columns
        available_columns = {}
        for key, column in six.iteritems(custom_columns):
            typ = column['datatype']
            if typ in column_types:
                available_columns[key] = column
        return available_columns

    def edit_shortcuts(self):
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()

    def view_prefs(self):
        d = PrefsViewerDialog(self.plugin_action.gui, PREFS_NAMESPACE)
        d.exec_()
