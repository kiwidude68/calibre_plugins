#!/usr/bin/env python
from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

# calibre Python 3 compatibility.
from six import text_type as unicode

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableView, QUrl,
                      QGroupBox, QGridLayout, QCheckBox, QTableWidget, QDialogButtonBox, QAbstractTableModel,
                      QTableWidgetItem, QIcon, QAbstractItemView, Qt, QPushButton, QStyledItemDelegate,
                      QToolButton, QSpacerItem, QModelIndex)
except ImportError:
    from PyQt5.Qt import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableView, QUrl,
                      QGroupBox, QGridLayout, QCheckBox, QTableWidget, QDialogButtonBox, QAbstractTableModel,
                      QTableWidgetItem, QIcon, QAbstractItemView, Qt, QPushButton, QStyledItemDelegate,
                      QToolButton, QSpacerItem, QModelIndex)

from calibre.gui2 import question_dialog, open_url
from calibre.gui2.actions import menu_action_unique_name
from calibre.utils.config import JSONConfig
from calibre.customize.ui import all_metadata_plugins, is_disabled

from calibre_plugins.quick_preferences.common_compatibility import qSizePolicy_Minimum, qSizePolicy_Expanding
from calibre_plugins.quick_preferences.common_icons import get_icon
from calibre_plugins.quick_preferences.common_dialogs import KeyboardConfigDialog, SizePersistedDialog
from calibre_plugins.quick_preferences.common_widgets import CheckableTableWidgetItem

# pulls in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/Quick-Preferences'

STORE_FILE_PATTERN_NAME = 'MenuFilePatterns'
KEY_COL_WIDTH = 'regexColWidth'
KEY_MENUS = 'menus'

KEY_ACTIVE = 'active'
KEY_TITLE = 'title'
KEY_REGEX = 'regex'
KEY_SWAP_NAMES = 'swapNames'
KEY_SOURCES = 'metadataSources'

DEFAULT_MENUS = [
    {
        KEY_ACTIVE: True,
        KEY_TITLE: 'Title - Author (Default)',
        KEY_REGEX: '(?P<title>.+) - (?P<author>[^_]+)',
        KEY_SWAP_NAMES: None
    },
    {
        KEY_ACTIVE: True,
        KEY_TITLE: 'Author [- Series #]- Title',
        KEY_REGEX: '^(?P<author>((?!\s-\s).)+)\s-\s(?:(?:\[\s*)?(?P<series>.+)\s(?P<series_index>[\d\.]+)(?:\s*\])?\s-\s)?(?P<title>[^(]+)(?:\(.*\))?',
        KEY_SWAP_NAMES: None
    }
]
DEFAULT_FILE_PATTERNS = {
                            KEY_MENUS: DEFAULT_MENUS,
                            KEY_COL_WIDTH: 180
                        }

DEFAULT_ENABLED_SOURCES_MENUS = [
    {
        KEY_ACTIVE: True,
        KEY_TITLE: 'Google and Amazon.com',
        KEY_SOURCES: ['Google','Amazon.com'],
    }
]
DEFAULT_ENABLED_SOURCES = {
                            KEY_MENUS: DEFAULT_ENABLED_SOURCES_MENUS,
                            KEY_COL_WIDTH: 180
                        }

STORE_OTHER_SHORTCUTS_NAME = 'OtherShortcuts'
OPT_SWAP_AUTHOR_NAMES = 'SwapAuthorNames'
OPT_READ_FILE_METADATA = 'ReadFileMetadata'
OPT_ADD_FORMAT_EXISTING = 'AddFormatToExisting'

DEFAULT_OTHER_SHORTCUTS = {
    OPT_SWAP_AUTHOR_NAMES: (True, ''),
    OPT_READ_FILE_METADATA: (True, ''),
    OPT_ADD_FORMAT_EXISTING: (True, '')
}

STORE_ENABLE_SOURCES_NAME = 'MenuEnableSources'

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Quick Preferences')

def migrate_old_prefs():
    old_file_patterns = plugin_prefs['FilePatterns']
    new_patterns = []
    for x in range(1,5):
        (title, pattern, shortcut) = old_file_patterns['SLOT'+str(x)]
        if title:
            new_patterns.append({ KEY_ACTIVE: True, KEY_TITLE: title,
                                  KEY_REGEX: pattern, KEY_SWAP_NAMES: None })
    if len(new_patterns) == 0:
        new_patterns = DEFAULT_MENUS
    plugin_prefs[STORE_FILE_PATTERN_NAME] = { KEY_MENUS: new_patterns,
                                             KEY_COL_WIDTH: DEFAULT_FILE_PATTERNS[KEY_COL_WIDTH] }
    del plugin_prefs['FilePatterns']

# Version 1.3 changes the configuration file layout
if 'FilePatterns' in plugin_prefs:
    # Need to migrate to the new layout
    migrate_old_prefs()

# Set defaults
plugin_prefs.defaults[STORE_FILE_PATTERN_NAME] = DEFAULT_FILE_PATTERNS
plugin_prefs.defaults[STORE_OTHER_SHORTCUTS_NAME] = DEFAULT_OTHER_SHORTCUTS
plugin_prefs.defaults[STORE_ENABLE_SOURCES_NAME] = DEFAULT_ENABLED_SOURCES

def show_help():
    open_url(QUrl(HELP_URL))


class PatternTableWidget(QTableWidget):

    def __init__(self, data_items, *args):
        QTableWidget.__init__(self, *args)
        self.populate_table(data_items)

    def regex_column_width(self):
        if self.columnCount() > 2:
            return self.columnWidth(2)
        else:
            c = plugin_prefs[STORE_FILE_PATTERN_NAME]
            return c.get(KEY_COL_WIDTH, DEFAULT_FILE_PATTERNS[KEY_COL_WIDTH])

    def populate_table(self, data_items):
        last_regex_column_width = self.regex_column_width()
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(data_items))
        header_labels = ['', _('Menu Title'), _('Regex File Pattern'), _('Swap Names')]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(24)

        for row, data in enumerate(data_items):
            self.populate_table_row(row, data)

        self.resizeColumnsToContents()
        # Special sizing for the file pattern column as it tends to dominate the dialog
        self.setColumnWidth(2, last_regex_column_width)
        self.setSortingEnabled(False)
        self.setMinimumSize(450, 0)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.selectRow(0)

    def populate_table_row(self, row, data):
        self.blockSignals(True)
        self.setItem(row, 0, CheckableTableWidgetItem(data[KEY_ACTIVE]))
        self.setItem(row, 1, QTableWidgetItem(data[KEY_TITLE]))
        self.setItem(row, 2, QTableWidgetItem(data[KEY_REGEX]))
        self.setItem(row, 3, CheckableTableWidgetItem(data[KEY_SWAP_NAMES], is_tristate=True))
        self.blockSignals(False)

    def append_data(self, data_items):
        for data in reversed(data_items):
            row = self.currentRow() + 1
            self.insertRow(row)
            self.populate_table_row(row, data)

    def get_data(self):
        data_items = []
        for row in range(self.rowCount()):
            data = self.convert_row_to_data(row)
            if data[KEY_TITLE]:
                data_items.append(data)
        return data_items

    def get_selected_data(self):
        data_items = []
        for row in self.selectionModel().selectedRows():
            data_items.append(self.convert_row_to_data(row.row()))
        return data_items

    def convert_row_to_data(self, row):
        data = self.create_blank_row_data()
        data[KEY_ACTIVE] = self.item(row, 0).get_boolean_value()
        data[KEY_TITLE] = unicode(self.item(row, 1).text()).strip()
        data[KEY_REGEX] = unicode(self.item(row, 2).text()).strip()
        data[KEY_SWAP_NAMES] = self.item(row, 3).get_boolean_value()
        return data

    def create_blank_row_data(self):
        data = {}
        data[KEY_ACTIVE] = True
        data[KEY_TITLE] = ''
        data[KEY_REGEX] = ''
        data[KEY_SWAP_NAMES] = None
        return data

    def add_row(self):
        self.setFocus()
        # We will insert a blank row below the currently selected row
        row = self.currentRow() + 1
        self.insertRow(row)
        self.populate_table_row(row, self.create_blank_row_data())
        self.select_and_scroll_to_row(row)

    def delete_rows(self):
        self.setFocus()
        selrows = self.selectionModel().selectedRows()
        selrows = sorted(selrows, key=lambda x: x.row())
        if len(selrows) == 0:
            return
        message = _('Are you sure you want to delete this menu item?')
        if len(selrows) > 1:
            message = _('Are you sure you want to delete the selected {0} menu items?').format(len(selrows))
        if not question_dialog(self, _('Are you sure?'), '<p>'+message, show_copy_button=False):
            return
        first_sel_row = selrows[0].row()
        for selrow in reversed(selrows):
            self.model().removeRow(selrow.row())
        if first_sel_row < self.model().rowCount(QModelIndex()):
            self.setCurrentIndex(self.model().index(first_sel_row, 0))
            self.select_and_scroll_to_row(first_sel_row)
        elif self.model().rowCount(QModelIndex()) > 0:
            self.setCurrentIndex(self.model().index(first_sel_row - 1, 0))
            self.select_and_scroll_to_row(first_sel_row - 1)

    def move_rows_up(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        first_sel_row = rows[0].row()
        if first_sel_row <= 0:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        for selrow in selrows:
            self.swap_row_widgets(selrow - 1, selrow + 1)
        scroll_to_row = first_sel_row - 1
        if scroll_to_row > 0:
            scroll_to_row = scroll_to_row - 1
        self.scrollToItem(self.item(scroll_to_row, 0))

    def move_rows_down(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        last_sel_row = rows[-1].row()
        if last_sel_row == self.rowCount() - 1:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        for selrow in reversed(selrows):
            self.swap_row_widgets(selrow + 2, selrow)
        scroll_to_row = last_sel_row + 1
        if scroll_to_row < self.rowCount() - 1:
            scroll_to_row = scroll_to_row + 1
        self.scrollToItem(self.item(scroll_to_row, 0))

    def swap_row_widgets(self, src_row, dest_row):
        self.blockSignals(True)
        self.insertRow(dest_row)
        for col in range(0, self.columnCount()):
            self.setItem(dest_row, col, self.takeItem(src_row, col))
        self.removeRow(src_row)
        self.blockSignals(False)

    def select_and_scroll_to_row(self, row):
        self.selectRow(row)
        self.scrollToItem(self.currentItem())


class MetadataSourcesTableWidget(QTableWidget):

    def __init__(self, data_items, *args):
        QTableWidget.__init__(self, *args)
        self.populate_table(data_items)
        self.setItemDelegateForColumn(2, MetadataSourcesTemplateDelegate(self))

    def sources_column_width(self):
        if self.columnCount() > 2:
            return self.columnWidth(2)
        else:
            c = plugin_prefs[STORE_FILE_PATTERN_NAME]
            return c.get(KEY_COL_WIDTH, DEFAULT_FILE_PATTERNS[KEY_COL_WIDTH])

    def populate_table(self, data_items):
        last_sources_column_width = self.sources_column_width()
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(data_items))
        header_labels = ['', _('Menu Title'), _('Enabled Sources')]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(24)

        for row, data in enumerate(data_items):
            self.populate_table_row(row, data)

        self.resizeColumnsToContents()
        # Special sizing for the file pattern column as it tends to dominate the dialog
        self.setColumnWidth(2, last_sources_column_width)
        self.setSortingEnabled(False)
        self.setMinimumSize(450, 0)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.selectRow(0)

    def populate_table_row(self, row, data):
        self.blockSignals(True)
        self.setItem(row, 0, CheckableTableWidgetItem(data[KEY_ACTIVE]))
        self.setItem(row, 1, QTableWidgetItem(data[KEY_TITLE]))
        self.setItem(row, 2, QTableWidgetItem(', '.join(data[KEY_SOURCES])))
        self.blockSignals(False)

    def append_data(self, data_items):
        for data in reversed(data_items):
            row = self.currentRow() + 1
            self.insertRow(row)
            self.populate_table_row(row, data)

    def get_data(self):
        data_items = []
        for row in range(self.rowCount()):
            data = self.convert_row_to_data(row)
            if len(data[KEY_TITLE]) > 0:
                data_items.append(data)
        return data_items

    def get_selected_data(self):
        data_items = []
        for row in self.selectionModel().selectedRows():
            data_items.append(self.convert_row_to_data(row.row()))
        return data_items

    def set_selected_row_enabled_sources(self, enabled_sources):
        row = self.selectionModel().selectedRows()[0]
        self.setItem(row.row(), 2, QTableWidgetItem(', '.join(enabled_sources)))

    def convert_row_to_data(self, row):
        data = self.create_blank_row_data()
        data[KEY_ACTIVE] = self.item(row, 0).get_boolean_value()
        data[KEY_TITLE] = unicode(self.item(row, 1).text()).strip()
        enabled_sources = self.item(row, 2).text().strip()
        enabled_sources = [unicode(source.strip()) for source in enabled_sources.split(',')] if len(enabled_sources) > 0 else []
        data[KEY_SOURCES] = enabled_sources
        return data

    def create_blank_row_data(self):
        data = {}
        data[KEY_ACTIVE] = True
        data[KEY_TITLE] = ''
        data[KEY_SOURCES] = []
        return data

    def add_row(self):
        self.setFocus()
        # We will insert a blank row below the currently selected row
        row = self.currentRow() + 1
        self.insertRow(row)
        self.populate_table_row(row, self.create_blank_row_data())
        self.select_and_scroll_to_row(row)

    def delete_rows(self):
        self.setFocus()
        selrows = self.selectionModel().selectedRows()
        selrows = sorted(selrows, key=lambda x: x.row())
        if len(selrows) == 0:
            return
        message = _('Are you sure you want to delete this menu item?')
        if len(selrows) > 1:
            message = _('Are you sure you want to delete the selected {0} menu items?').format(len(selrows))
        if not question_dialog(self, _('Are you sure?'), '<p>'+message, show_copy_button=False):
            return
        first_sel_row = selrows[0].row()
        for selrow in reversed(selrows):
            self.model().removeRow(selrow.row())
        if first_sel_row < self.model().rowCount(QModelIndex()):
            self.setCurrentIndex(self.model().index(first_sel_row, 0))
            self.select_and_scroll_to_row(first_sel_row)
        elif self.model().rowCount(QModelIndex()) > 0:
            self.setCurrentIndex(self.model().index(first_sel_row - 1, 0))
            self.select_and_scroll_to_row(first_sel_row - 1)

    def move_rows_up(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        first_sel_row = rows[0].row()
        if first_sel_row <= 0:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        for selrow in selrows:
            self.swap_row_widgets(selrow - 1, selrow + 1)
        scroll_to_row = first_sel_row - 1
        if scroll_to_row > 0:
            scroll_to_row = scroll_to_row - 1
        self.scrollToItem(self.item(scroll_to_row, 0))

    def move_rows_down(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        last_sel_row = rows[-1].row()
        if last_sel_row == self.rowCount() - 1:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        for selrow in reversed(selrows):
            self.swap_row_widgets(selrow + 2, selrow)
        scroll_to_row = last_sel_row + 1
        if scroll_to_row < self.rowCount() - 1:
            scroll_to_row = scroll_to_row + 1
        self.scrollToItem(self.item(scroll_to_row, 0))

    def swap_row_widgets(self, src_row, dest_row):
        self.blockSignals(True)
        self.insertRow(dest_row)
        for col in range(0, self.columnCount()):
            self.setItem(dest_row, col, self.takeItem(src_row, col))
        self.removeRow(src_row)
        self.blockSignals(False)

    def select_and_scroll_to_row(self, row):
        self.selectRow(row)
        self.scrollToItem(self.currentItem())


class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        heading_layout = QHBoxLayout()
        layout.addLayout(heading_layout)
        heading_label = QLabel(_('Configure the file pattern menu items to display:'), self)
        heading_layout.addWidget(heading_label)

        c = plugin_prefs[STORE_FILE_PATTERN_NAME]
        m = plugin_prefs[STORE_ENABLE_SOURCES_NAME]

        # Add a horizontal layout containing the table and the buttons next to it
        table_layout = QHBoxLayout()
        layout.addLayout(table_layout)
        menu_file_patterns = c[KEY_MENUS]
        menu_enabled_sources = m[KEY_MENUS]

        # Create a table the user can edit the file pattern values in
        self.pattern_table = PatternTableWidget(menu_file_patterns, self)
        heading_label.setBuddy(self.pattern_table)
        table_layout.addWidget(self.pattern_table)

        # Add a vertical layout containing the the buttons to move up/down etc.
        button_layout = QVBoxLayout()
        table_layout.addLayout(button_layout)
        move_up_button = QToolButton(self)
        move_up_button.setToolTip(_('Move row up'))
        move_up_button.setIcon(QIcon(I('arrow-up.png')))
        button_layout.addWidget(move_up_button)
        spacerItem = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem)

        add_button = QToolButton(self)
        add_button.setToolTip(_('Add menu item row'))
        add_button.setIcon(QIcon(I('plus.png')))
        button_layout.addWidget(add_button)
        spacerItem2 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem2)

        delete_button = QToolButton(self)
        delete_button.setToolTip(_('Delete menu item row'))
        delete_button.setIcon(QIcon(I('minus.png')))
        button_layout.addWidget(delete_button)
        spacerItem1 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem1)

        reset_button = QToolButton(self)
        reset_button.setToolTip(_('Reset to defaults'))
        reset_button.setIcon(get_icon('clear_left'))
        button_layout.addWidget(reset_button)
        spacerItem3 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem3)

        move_down_button = QToolButton(self)
        move_down_button.setToolTip(_('Move row down'))
        move_down_button.setIcon(QIcon(I('arrow-down.png')))
        button_layout.addWidget(move_down_button)

        move_up_button.clicked.connect(self.pattern_table.move_rows_up)
        move_down_button.clicked.connect(self.pattern_table.move_rows_down)
        add_button.clicked.connect(self.pattern_table.add_row)
        delete_button.clicked.connect(self.pattern_table.delete_rows)
        reset_button.clicked.connect(self.reset_file_patterns_to_defaults)

        heading_layout = QHBoxLayout()
        layout.addLayout(heading_layout)
        heading_label = QLabel(_('Configure the Enabled metadata sources menu items to display'), self)
        heading_layout.addWidget(heading_label)

        # Add a horizontal layout containing the table and the buttons next to it
        table_layout = QHBoxLayout()
        layout.addLayout(table_layout)

        # Create a table the user can edit the file pattern values in
        self.enabled_sources = MetadataSourcesTableWidget(menu_enabled_sources, self)
        heading_label.setBuddy(self.enabled_sources)
        table_layout.addWidget(self.enabled_sources)
#         self.enabled_sources.doubleClicked.connect(self.open_MetadataSourcesDialog)

        # Add a vertical layout containing the the buttons to move up/down etc.
        button_layout = QVBoxLayout()
        table_layout.addLayout(button_layout)
        move_up_button = QToolButton(self)
        move_up_button.setToolTip(_('Move row up'))
        move_up_button.setIcon(QIcon(I('arrow-up.png')))
        button_layout.addWidget(move_up_button)
        spacerItem = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem)

        add_button = QToolButton(self)
        add_button.setToolTip(_('Add menu item row'))
        add_button.setIcon(QIcon(I('plus.png')))
        button_layout.addWidget(add_button)
        spacerItem2 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem2)

        delete_button = QToolButton(self)
        delete_button.setToolTip(_('Delete menu item row'))
        delete_button.setIcon(QIcon(I('minus.png')))
        button_layout.addWidget(delete_button)
        spacerItem1 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem1)

        reset_button = QToolButton(self)
        reset_button.setToolTip(_('Reset to defaults'))
        reset_button.setIcon(get_icon('clear_left'))
        button_layout.addWidget(reset_button)
        spacerItem3 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem3)

        move_down_button = QToolButton(self)
        move_down_button.setToolTip(_('Move row down'))
        move_down_button.setIcon(QIcon(I('arrow-down.png')))
        button_layout.addWidget(move_down_button)

        move_up_button.clicked.connect(self.enabled_sources.move_rows_up)
        move_down_button.clicked.connect(self.enabled_sources.move_rows_down)
        add_button.clicked.connect(self.enabled_sources.add_row)
        delete_button.clicked.connect(self.enabled_sources.delete_rows)
        reset_button.clicked.connect(self.reset_metadata_sources_to_defaults)


        # Now add ability to configure menus for remaining options
        layout.addSpacing(10)

        other_groupbox = QGroupBox(_('Include in menu:'), self)
        layout.addWidget(other_groupbox)
        other_grid_layout = QGridLayout()
        other_groupbox.setLayout(other_grid_layout)
        c = plugin_prefs[STORE_OTHER_SHORTCUTS_NAME]
        for col, key, text in [(0, OPT_SWAP_AUTHOR_NAMES, _('Swap author names')),
                               (1, OPT_READ_FILE_METADATA, _('Read metadata from file')),
                               (2, OPT_ADD_FORMAT_EXISTING, _('Automerge added books'))]:
            data = c[key]
            is_visible = data[0]
            visible_checkbox = QCheckBox(text, self)
            visible_checkbox.setChecked(is_visible)
            setattr(self, '_visible_'+key, visible_checkbox)
            other_grid_layout.addWidget(visible_checkbox, 0, col)

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

        # Build a list of all the current names
        self.orig_unique_active_menus = self.get_active_unique_names(menu_file_patterns)

    def save_settings(self):
        file_patterns = {}
        file_patterns[KEY_MENUS] = self.pattern_table.get_data()
        file_patterns[KEY_COL_WIDTH] = self.pattern_table.regex_column_width()
        plugin_prefs[STORE_FILE_PATTERN_NAME] = file_patterns

        enabled_sources = {}
        enabled_sources[KEY_MENUS] = self.enabled_sources.get_data()
        enabled_sources[KEY_COL_WIDTH] = self.enabled_sources.sources_column_width()
        plugin_prefs[STORE_ENABLE_SOURCES_NAME] = enabled_sources

        other_shortcuts = {}
        for key in (OPT_SWAP_AUTHOR_NAMES, OPT_READ_FILE_METADATA, OPT_ADD_FORMAT_EXISTING):
            is_visible = getattr(self, '_visible_'+key).isChecked()
            other_shortcuts[key] = (is_visible, )
        plugin_prefs[STORE_OTHER_SHORTCUTS_NAME] = other_shortcuts

        # For each menu that was visible but now is not, we need to unregister any
        # keyboard shortcut associated with that action.
        menus_changed = False
        kb = self.plugin_action.gui.keyboard
        new_unique_active_menus = self.get_active_unique_names(file_patterns[KEY_MENUS])
        for raw_unique_name in self.orig_unique_active_menus.keys():
            if raw_unique_name not in new_unique_active_menus:
                unique_name = menu_action_unique_name(self.plugin_action, raw_unique_name)
                if unique_name in kb.shortcuts:
                    kb.unregister_shortcut(unique_name)
                    menus_changed = True
        if menus_changed:
            self.plugin_action.gui.keyboard.finalize()
        self.orig_unique_active_menus = new_unique_active_menus

    def get_active_unique_names(self, data_items):
        active_unique_names = {}
        for data in data_items:
            if data['active']:
                unique_name = data['title']
                active_unique_names[unique_name] = data['title']
        return active_unique_names

    def reset_file_patterns_to_defaults(self):
        if not question_dialog(self, _('Are you sure?'), '<p>'+
                _('Are you sure you want to reset to the plugin default menu?<br>' 
                'Any modifications to file pattern menu items will be discarded.'),
                show_copy_button=False):
            return
        self.pattern_table.populate_table(DEFAULT_MENUS)

    def reset_metadata_sources_to_defaults(self):
        if not question_dialog(self, _('Are you sure?'), '<p>'+
                _('Are you sure you want to reset to the plugin default menu?<br>' 
                'Any modifications to metadata source menu items will be discarded.'),
                show_copy_button=False):
            return
        self.enabled_sources.populate_table(DEFAULT_ENABLED_SOURCES_MENUS)

    def edit_shortcuts(self):
        self.save_settings()
        # Force the menus to be rebuilt immediately, so we have all our actions registered
        self.plugin_action.rebuild_menus()
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()


class MetadataSourcesDialog(SizePersistedDialog):

    def __init__(self, parent, enabled_sources=[]):
        super(MetadataSourcesDialog, self).__init__(parent, 'quick preferences:metadata source dialog')
        self.parent = parent
        self.enabled_sources = enabled_sources
        self.initialize_controls()
        self.initialize()
        
        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def initialize_controls(self):
        self.setWindowTitle(_("Metadata Source Plugins"))
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        heading_label = QLabel(_('Select the Metadata sources to be enabled'), self)
        layout.addWidget(heading_label)

        self.sources_view = QTableView()
        self.sources_model = SourcesModel(self, self.enabled_sources)
        self.sources_view.setModel(self.sources_model)

        layout.addWidget(self.sources_view)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._ok_clicked)
        button_box.rejected.connect(self.reject)
        get_current_button = button_box.addButton(_("Get Current"), QDialogButtonBox.ResetRole)
        get_current_button.setToolTip(_("Get the currently enabled Metadata sources"))
        get_current_button.clicked.connect(self.get_current_clicked)
        clear_button = button_box.addButton(_("Clear"), QDialogButtonBox.ResetRole)
        clear_button.setToolTip(_("Clear all selected sources"))
        clear_button.clicked.connect(self.deselect_all_clicked)
        layout.addWidget(button_box)

    def initialize(self):
#         ConfigWidgetBase.initialize(self)
        self.sources_model.initialize()
        self.sources_view.resizeColumnsToContents()

    def get_selected_sources(self):
        enable_sources = self.sources_model.selected_sources()
        return enable_sources

    def _ok_clicked(self):
        self.accept()
        return

    def get_current_clicked(self):
        self.sources_model.enabled_sources = []
        return

    def deselect_all_clicked(self):
        self.sources_model.deselect_all()
        return


class SourcesModel(QAbstractTableModel):  # {{{

    def __init__(self, parent=None, enabled_sources=[]):
        super(SourcesModel, self).__init__(parent)
        self.gui_parent = parent

        self.plugins = []
        self.enabled_sources = enabled_sources

    def initialize(self):
        self.beginResetModel()
        self.plugins = [[plugin.name, not is_disabled(plugin), plugin.description] for plugin in list(all_metadata_plugins())]
        if len(self._enabled_sources) > 0:
            for plugin in self.plugins:
                plugin[1] = plugin[0] in self.enabled_sources 
        self.plugins.sort()
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self.plugins)

    def columnCount(self, parent=None):
        return 1

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return _('Source')
        return None

    def data(self, index, role):
        try:
            plugin = self.plugins[index.row()]
        except:
            return None
        col = index.column()

        if role in (Qt.DisplayRole, Qt.EditRole):
            return plugin[0]
        elif role == Qt.CheckStateRole and col == 0:
            orig = Qt.Checked if plugin[1] else Qt.Unchecked
            return orig
        elif role == Qt.UserRole:
            return plugin
        elif role == Qt.ToolTipRole:
            return plugin[2]
        return None

    def setData(self, index, val, role):
        try:
            plugin = self.plugins[index.row()]
        except:
            return False
        col = index.column()
        ret = False
        if col == 0 and role == Qt.CheckStateRole:
            plugin[1] = val == Qt.Checked
            ret = True
        if ret:
            self.dataChanged.emit(index, index)
        return ret

    def flags(self, index):
        col = index.column()
        ans = QAbstractTableModel.flags(self, index)
        if col == 0:
            return ans | Qt.ItemIsUserCheckable
        return Qt.ItemIsEditable | ans

    def selected_sources(self):
        selected_sources = [plugin[0] for plugin in self.plugins if plugin[1]]
        return selected_sources

    def deselect_all(self):
        for plugin in self.plugins:
            plugin[1] = False
        self.enabled_sources = ['']
        
    @property
    def enabled_sources(self):
        return self._enabled_sources

    @enabled_sources.setter
    def enabled_sources(self, value):
        self._enabled_sources = value
        if len(self.plugins) > 0:
            self.initialize()


class MetadataSourcesTemplateDelegate(QStyledItemDelegate):  # {{{

    def __init__(self, parent):
        '''
        Delegate for selecting Metadata Sources.
        '''
        super(MetadataSourcesTemplateDelegate, self).__init__(parent)

    def createEditor(self, parent, option, index):
        m = index.model()
        enabled_sources = m.data(index).strip()
        enabled_sources = [unicode(source.strip()) for source in enabled_sources.split(',')] if len(enabled_sources) > 0 else []
        editor = MetadataSourcesDialog(parent, enabled_sources=enabled_sources)
        d = editor.exec_()
        if d:
            m.setData(index, (", ".join(editor.get_selected_sources())), Qt.EditRole)
        return None
