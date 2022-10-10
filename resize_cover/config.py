from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

# calibre Python 3 compatibility.
from six import text_type as unicode

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (Qt, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
                      QPushButton, QTableWidgetItem, QIcon, QAbstractItemView,
                      QToolButton, QSpacerItem, QModelIndex, QUrl)
except ImportError:
    from PyQt5.Qt import (Qt, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
                      QPushButton, QTableWidgetItem, QIcon, QAbstractItemView,
                      QToolButton, QSpacerItem, QModelIndex, QUrl)

from calibre.gui2 import question_dialog, info_dialog, open_url
from calibre.utils.config import JSONConfig

from calibre_plugins.resize_cover.common_compatibility import qSizePolicy_Minimum, qSizePolicy_Expanding
from calibre_plugins.resize_cover.common_dialogs import KeyboardConfigDialog
from calibre_plugins.resize_cover.common_icons import get_icon
from calibre_plugins.resize_cover.common_widgets import ReadOnlyTableWidgetItem, CheckableTableWidgetItem


try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

# {
#    'sizes': [ {'width':xxx, 'height':yyy, default:true},... ]
# }

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/Resize-Cover'

STORE_NAME = 'Options'
KEY_SIZES = 'sizes'
KEY_WIDTH = 'width'
KEY_HEIGHT = 'height'
KEY_DEFAULT = 'default'
KEY_KEEP_ASPECT_RATIO = 'keep_aspect_ratio'
KEY_ONLY_SHRINK = 'only_shrink_larger_images'

DEFAULT_STORE_VALUES = {
    KEY_SIZES: [{ KEY_WIDTH: 450, KEY_HEIGHT: 680, KEY_DEFAULT: True }],
    KEY_DEFAULT: False,
    KEY_KEEP_ASPECT_RATIO: False,
    KEY_ONLY_SHRINK: False
}

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Resize Cover')

# Set defaults
plugin_prefs.defaults[STORE_NAME] = DEFAULT_STORE_VALUES

def show_help():
    open_url(QUrl(HELP_URL))


class SizesTableWidget(QTableWidget):

    def __init__(self, parent):
        QTableWidget.__init__(self, parent)

    def populate_table(self, data_items):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(data_items))
        header_labels = [_('Width'), _('Height'), _('Default'), _('Keep aspect ratio'), _('Only shrink larger images')]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(30)
        self.horizontalHeader().setStretchLastSection(True)

        for row, data in enumerate(data_items):
            self.populate_table_row(row, data)

        for col in range(0,4):
            self.resizeColumnToContents(col)
        self.setSortingEnabled(False)
        self.setMinimumSize(200, 50)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        if len(data_items) > 0:
            self.selectRow(0)

    def populate_table_row(self, row, data_item):
        self.setItem(row, 0, QTableWidgetItem(str(data_item[KEY_WIDTH])))
        self.setItem(row, 1, QTableWidgetItem(str(data_item[KEY_HEIGHT])))

        default_text = _('Default') if data_item[KEY_DEFAULT] else ''
        self.setItem(row, 2, ReadOnlyTableWidgetItem(default_text))

        keep_aspect_ratio = data_item.get(KEY_KEEP_ASPECT_RATIO, DEFAULT_STORE_VALUES[KEY_KEEP_ASPECT_RATIO])
        self.setItem(row, 3, CheckableTableWidgetItem(keep_aspect_ratio))

        only_shrink = data_item.get(KEY_ONLY_SHRINK, DEFAULT_STORE_VALUES[KEY_ONLY_SHRINK])
        self.setItem(row, 4, CheckableTableWidgetItem(only_shrink))

    def get_data(self):
        data_items = []
        for row in range(self.rowCount()):
            data_item = {}
            data_item[KEY_WIDTH] = int(unicode(self.item(row, 0).text()).strip())
            data_item[KEY_HEIGHT] = int(unicode(self.item(row, 1).text()).strip())
            data_item[KEY_DEFAULT] = (unicode(self.item(row, 2).text()).strip() == _('Default'))
            data_item[KEY_KEEP_ASPECT_RATIO] = self.item(row, 3).get_boolean_value()
            data_item[KEY_ONLY_SHRINK] = self.item(row, 4).get_boolean_value()
            if data_item[KEY_WIDTH] > 0 and data_item[KEY_HEIGHT] > 0:
                data_items.append(data_item)
        if len(data_items) == 0:
            data_items[0][KEY_DEFAULT] = True
        return data_items

    def create_blank_row_data(self):
        data_item = {}
        data_item[KEY_WIDTH] = 0
        data_item[KEY_HEIGHT] = 0
        data_item[KEY_DEFAULT] = DEFAULT_STORE_VALUES[KEY_DEFAULT]
        data_item[KEY_KEEP_ASPECT_RATIO] = DEFAULT_STORE_VALUES[KEY_KEEP_ASPECT_RATIO]
        data_item[KEY_ONLY_SHRINK] = DEFAULT_STORE_VALUES[KEY_ONLY_SHRINK]
        return data_item

    def select_and_scroll_to_row(self, row):
        self.selectRow(row)
        self.scrollToItem(self.currentItem())

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
        if self.rowCount() == 1 or self.rowCount() == len(selrows):
            return info_dialog(self, _('Cannot delete'), _('You must have at least one resize menu item'))

        message = '<p>' + _('Are you sure you want to delete this resize menu item?')
        if len(selrows) > 1:
            message = '<p>' + _('Are you sure you want to delete the selected {0} resize menu items?').format(len(selrows))
        if not question_dialog(self, _('Are you sure?'), message, show_copy_button=False):
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

    def set_as_default(self):
        row = self.currentRow()
        if unicode(self.item(row, 2).text()).strip() == _('Default'):
            return
        self.item(row, 2).setText(_('Default'))
        for update_row in range(0, self.rowCount()):
            if update_row != row:
                self.item(update_row, 2).setText('')

class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        heading_label = QLabel(_('Cover resize options:'), self)
        layout.addWidget(heading_label)

        # Add a horizontal layout containing the table and the buttons next to it
        table_layout = QHBoxLayout()
        layout.addLayout(table_layout)

        self._table = SizesTableWidget(self)
        heading_label.setBuddy(self._table)
        table_layout.addWidget(self._table)

        # Add a vertical layout containing the the buttons to add/remove.
        button_layout = QVBoxLayout()
        table_layout.addLayout(button_layout)

        add_button = QToolButton(self)
        add_button.setToolTip(_('Add resize menu item row'))
        add_button.setIcon(QIcon(I('plus.png')))
        button_layout.addWidget(add_button)
        spacerItem = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem)

        delete_button = QToolButton(self)
        delete_button.setToolTip(_('Delete resize menu item row'))
        delete_button.setIcon(QIcon(I('minus.png')))
        button_layout.addWidget(delete_button)

        add_button.clicked.connect(self._table.add_row)
        delete_button.clicked.connect(self._table.delete_rows)

        other_layout = QHBoxLayout()
        layout.addLayout(other_layout)

        set_default_button = QPushButton(' '+_('Set as Toolbar Button Default')+' ', self)
        set_default_button.setToolTip(_('Set this size as the default on the menu button'))
        set_default_button.clicked.connect(self._table.set_as_default)

        other_layout.addWidget(set_default_button)

        keyboard_shortcuts_button = QPushButton(' '+_('Keyboard shortcuts')+'... ', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        other_layout.addWidget(keyboard_shortcuts_button)

        help_button = QPushButton(' '+_('&Help'), self)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(show_help)
        other_layout.addWidget(help_button)
        other_layout.insertStretch(-1)

        c = plugin_prefs[STORE_NAME]
        self._table.populate_table(c[KEY_SIZES])

    def save_settings(self):
        new_prefs = {}
        new_prefs[KEY_SIZES] = self._table.get_data()
        plugin_prefs[STORE_NAME] = new_prefs

    def edit_shortcuts(self):
        self.save_settings()
        # Force the menus to be rebuilt immediately, so we have all our actions registered
        self.plugin_action.rebuild_menus()
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()
