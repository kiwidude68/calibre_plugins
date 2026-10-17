from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from collections import OrderedDict
try:
    from qt.core import (QWidget, QVBoxLayout, QCheckBox, QGroupBox, QPushButton,
                         QHBoxLayout, QUrl, QLabel, QListWidget, QListWidgetItem,
                         QAbstractItemView, QComboBox, QGridLayout, Qt)
except ImportError:
    from PyQt5.Qt import (QWidget, QVBoxLayout, QCheckBox, QGroupBox, QPushButton,
                          QHBoxLayout, QUrl, QLabel, QListWidget, QListWidgetItem,
                          QAbstractItemView, QComboBox, QGridLayout, Qt)
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
CUSTOM_COLUMNS_KEY = 'CustomColumns'

DEFAULT_STORE_VALUES = {
    MENUS_KEY: { 'authors': True,
                 'series': True,
                 'publisher': False,
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


def is_custom_column_category(column):
    return (
        (column.get('is_category', False) and column.get('kind') not in ('user', 'search'))
        or (column.get('datatype') == 'composite'
            and column.get('display', {}).get('make_category', False))
    )


class TypeComboBox(QComboBox):

    def __init__(self, placeholder, parent=None):
        QComboBox.__init__(self, parent)
        self.placeholder = placeholder
        self.setMinimumWidth(150)

    def set_choices(self, choices):
        self.clear()
        self.addItem(self.placeholder, None)
        for key, display in choices:
            self.addItem(display, key)

    def selected_key(self):
        return self.currentData()

class ConfigWidget(QWidget):

    other_display_keys  = OrderedDict([('add', _('Add to user category')),
                                       ('move', _('Move to user category')),
                                       ('remove', _('Remove from user category')),
                                       ('view', 'Show in tag browser'),
                                       ('manage', 'Manage user categories')])
    display_keys  = OrderedDict([('authors', _('Authors')),
                                 ('series', _('Series')),
                                 ('formats', _('Formats')),
                                 ('identifiers', _('Identifiers')),
                                 ('languages', _('Languages')),
                                 ('publisher', _('Publisher')),
                                 ('rating', _('Rating')),
                                 ('tags', _('Tags'))])

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.setMinimumSize(400, 300)

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
        self.selected_types = QListWidget(self)
        self.selected_types.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.selected_types.setMaximumHeight(120)
        selected_layout = QHBoxLayout()
        selected_layout.addWidget(self.selected_types)
        self.remove_selected_button = QPushButton(_('Remove selected'), self)
        self.remove_selected_button.setEnabled(False)
        self.remove_selected_button.clicked.connect(self.remove_selected_types)
        selected_layout.addWidget(self.remove_selected_button, alignment=Qt.AlignTop)
        menus_layout.addWidget(QLabel(_('Selected types:'), self))
        menus_layout.addLayout(selected_layout)
        self.selected_types.itemSelectionChanged.connect(self.update_remove_button)

        self.metadata_choices = list(self.display_keys.items())
        self.metadata_combo = TypeComboBox(_('Select metadata type...'), self)
        add_metadata_button = QPushButton(_('Add'), self)
        add_metadata_button.clicked.connect(self.add_metadata_types)

        custom_columns = self.plugin_action.gui.library_view.model().custom_columns
        self.custom_column_labels = {}
        self.custom_column_choices = []
        for key, column in sorted(custom_columns.items()):
            if not is_custom_column_category(column):
                continue
            display = '%s (%s)' % (column['name'], key)
            self.custom_column_labels[key] = display
            self.custom_column_choices.append((key, display))
        self.custom_column_combo = TypeComboBox(_('Select custom column...'), self)
        add_custom_button = QPushButton(_('Add'), self)
        add_custom_button.clicked.connect(self.add_custom_columns)

        type_picker_layout = QGridLayout()
        type_picker_layout.addWidget(QLabel(_('Metadata types:'), self), 0, 0)
        type_picker_layout.addWidget(self.metadata_combo, 0, 1)
        type_picker_layout.addWidget(add_metadata_button, 0, 2)
        type_picker_layout.addWidget(QLabel(_('Custom columns:'), self), 1, 0)
        type_picker_layout.addWidget(self.custom_column_combo, 1, 1)
        type_picker_layout.addWidget(add_custom_button, 1, 2)
        type_picker_layout.setColumnStretch(1, 1)
        type_picker_layout.setColumnMinimumWidth(2, 70)
        menus_layout.addLayout(type_picker_layout)
        menus_box.setLayout(menus_layout)

        self.selected_type_keys = set()
        for key, display in list(self.display_keys.items()):
            if c[MENUS_KEY].get(key, False):
                self.add_type_to_list('metadata', key, display)
        for key in c.get(CUSTOM_COLUMNS_KEY, []):
            display = self.custom_column_labels.get(key)
            if display is not None:
                self.add_type_to_list('custom', key, display)
        self.refresh_type_choices()

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
            menu_options[key] = ('metadata', key) in self.selected_type_keys
        other_menu_options = {}
        for key in list(self.other_display_keys.keys()):
            other_menu_options[key] = getattr(self, '_other_'+key).isChecked()
        custom_column_options = [self.selected_types.item(row).data(Qt.UserRole + 1)
                                 for row in range(self.selected_types.count())
                                 if self.selected_types.item(row).data(Qt.UserRole) == 'custom']
        new_prefs = { MENUS_KEY: menu_options,
                      OTHER_MENUS_KEY: other_menu_options,
                      CUSTOM_COLUMNS_KEY: custom_column_options }

        plugin_prefs[STORE_NAME] = new_prefs

    def add_type_to_list(self, source, key, display):
        type_key = (source, key)
        if type_key in self.selected_type_keys:
            return
        item = QListWidgetItem(display)
        item.setData(Qt.UserRole, source)
        item.setData(Qt.UserRole + 1, key)
        self.selected_types.addItem(item)
        self.selected_type_keys.add(type_key)

    def add_metadata_types(self):
        key = self.metadata_combo.selected_key()
        if key is not None:
            self.add_type_to_list('metadata', key, self.display_keys[key])
            self.refresh_type_choices()

    def add_custom_columns(self):
        key = self.custom_column_combo.selected_key()
        if key is not None:
            display = self.custom_column_labels.get(key, key)
            self.add_type_to_list('custom', key, display)
            self.refresh_type_choices()

    def remove_selected_types(self):
        for item in self.selected_types.selectedItems():
            source = item.data(Qt.UserRole)
            key = item.data(Qt.UserRole + 1)
            self.selected_type_keys.discard((source, key))
            self.selected_types.takeItem(self.selected_types.row(item))
        self.refresh_type_choices()
        self.update_remove_button()

    def refresh_type_choices(self):
        selected_metadata = {key for source, key in self.selected_type_keys
                             if source == 'metadata'}
        selected_custom = {key for source, key in self.selected_type_keys
                           if source == 'custom'}
        self.metadata_combo.set_choices(
            [(key, display) for key, display in self.metadata_choices
             if key not in selected_metadata])
        self.custom_column_combo.set_choices(
            [(key, display) for key, display in self.custom_column_choices
             if key not in selected_custom])

    def update_remove_button(self):
        self.remove_selected_button.setEnabled(bool(self.selected_types.selectedItems()))

    def edit_shortcuts(self):
        self.save_settings()
        # Force the menus to be rebuilt immediately, so we have all our actions registered
        self.plugin_action.rebuild_menus()
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()
