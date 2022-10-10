from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import six, copy
try:
    from qt.core import QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox, QGridLayout, QUrl
except ImportError:
    from PyQt5.Qt import QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox, QGridLayout, QUrl
from calibre.utils.config import JSONConfig

# Pull in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.gui2 import open_url

from calibre_plugins.ratings.common_icons import get_icon
from calibre_plugins.ratings.common_dialogs import KeyboardConfigDialog, PrefsViewerDialog
from calibre_plugins.ratings.common_widgets import CustomColumnComboBox

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/Ratings'

PREFS_NAMESPACE = 'RatingsPlugin'
PREFS_KEY_SETTINGS = 'settings'

KEY_COL_ARATING = 'colAmazonRating'
KEY_COL_ARATING_COUNT = 'colAmazonRatingCount'
KEY_COL_GRATING = 'colGoodreadsRating'
KEY_COL_GRATING_COUNT = 'colGoodreadsRatingCount'
DEFAULT_LIBRARY_VALUES = {
                          KEY_COL_ARATING: '',
                          KEY_COL_ARATING_COUNT: '',
                          KEY_COL_GRATING: '',
                          KEY_COL_GRATING_COUNT: ''
                         }


def get_library_config(db):
    library_config = db.prefs.get_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS, copy.deepcopy(DEFAULT_LIBRARY_VALUES))
    return library_config

def set_library_config(db, library_config):
    db.prefs.set_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS, library_config)

def show_help():
    open_url(QUrl(HELP_URL))

class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        self.library = get_library_config(plugin_action.gui.current_db)
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        group_box = QGroupBox('Custom columns:', self)
        layout.addWidget(group_box)
        group_box_layout = QGridLayout()
        group_box.setLayout(group_box_layout)

        rating_avail_columns = self.get_custom_columns(['float'])
        rating_count_avail_columns = self.get_custom_columns(['int'])
        arating_col = self.library.get(KEY_COL_ARATING, '')
        arating_count_col = self.library.get(KEY_COL_ARATING_COUNT, '')
        grating_col = self.library.get(KEY_COL_GRATING, '')
        grating_count_col = self.library.get(KEY_COL_GRATING_COUNT, '')

        arating_label = QLabel(_('Amazon Rating:'), self)
        self.arating_col_combo = CustomColumnComboBox(self, rating_avail_columns, arating_col)
        arating_label.setBuddy(self.arating_col_combo)
        group_box_layout.addWidget(arating_label, 0, 0, 1, 1)
        group_box_layout.addWidget(self.arating_col_combo, 0, 1, 1, 2)

        arating_count_label = QLabel(_('Amazon Rating Count:'), self)
        self.arating_count_col_combo = CustomColumnComboBox(self, rating_count_avail_columns, arating_count_col)
        arating_count_label.setBuddy(self.arating_count_col_combo)
        group_box_layout.addWidget(arating_count_label, 1, 0, 1, 1)
        group_box_layout.addWidget(self.arating_count_col_combo, 1, 1, 1, 2)

        grating_label = QLabel(_('Goodreads Rating:'), self)
        self.grating_col_combo = CustomColumnComboBox(self, rating_avail_columns, grating_col)
        grating_label.setBuddy(self.grating_col_combo)
        group_box_layout.addWidget(grating_label, 2, 0, 1, 1)
        group_box_layout.addWidget(self.grating_col_combo, 2, 1, 1, 2)

        grating_count_label = QLabel(_('Goodreads Rating Count:'), self)
        self.grating_count_col_combo = CustomColumnComboBox(self, rating_count_avail_columns, grating_count_col)
        grating_count_label.setBuddy(self.grating_count_col_combo)
        group_box_layout.addWidget(grating_count_label, 3, 0, 1, 1)
        group_box_layout.addWidget(self.grating_count_col_combo, 3, 1, 1, 2)

        keyboard_shortcuts_button = QPushButton(_('Keyboard shortcuts')+'...', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        layout.addWidget(keyboard_shortcuts_button)

        view_prefs_button = QPushButton(_('&View library preferences')+'...', self)
        view_prefs_button.setToolTip(_('View data stored in the library database for this plugin'))
        view_prefs_button.clicked.connect(self.view_prefs)
        layout.addWidget(view_prefs_button)

        help_button = QPushButton(' '+_('&Help'), self)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(show_help)
        layout.addWidget(help_button)

    def save_settings(self):
        self.library[KEY_COL_ARATING] = self.arating_col_combo.get_selected_column()
        self.library[KEY_COL_ARATING_COUNT] = self.arating_count_col_combo.get_selected_column()
        self.library[KEY_COL_GRATING] = self.grating_col_combo.get_selected_column()
        self.library[KEY_COL_GRATING_COUNT] = self.grating_count_col_combo.get_selected_column()
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
