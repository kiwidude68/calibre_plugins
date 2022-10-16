from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from collections import OrderedDict
from functools import partial

# calibre Python 3 compatibility.
from six import text_type as unicode

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (Qt, QWidget, QVBoxLayout, QLabel, QLineEdit, QGridLayout, QUrl,
                          QGroupBox, QHBoxLayout, QComboBox, QCheckBox, QFormLayout,
                          QIcon, QTableWidget, QTableWidgetItem, QPushButton, QInputDialog,
                          QAbstractItemView, QDialog, QDialogButtonBox, QAction, QToolButton, 
                          QSpacerItem, QModelIndex)
except ImportError:
    from PyQt5.Qt import (Qt, QWidget, QVBoxLayout, QLabel, QLineEdit, QGridLayout, QUrl,
                          QGroupBox, QHBoxLayout, QComboBox, QCheckBox, QFormLayout,
                          QIcon, QTableWidget, QTableWidgetItem, QPushButton, QInputDialog,
                          QAbstractItemView, QDialog, QDialogButtonBox, QAction, QToolButton,
                          QSpacerItem, QModelIndex)

from calibre import prints
from calibre.constants import DEBUG
from calibre.gui2 import error_dialog, question_dialog, info_dialog, open_url
from calibre.gui2.complete2 import EditWithComplete
from calibre.utils.config import JSONConfig
from calibre.utils.icu import sort_key
from calibre.devices.usbms.driver import debug_print

from calibre_plugins.goodreads_sync.common_compatibility import qSizePolicy_Expanding, qSizePolicy_Minimum
from calibre_plugins.goodreads_sync.common_icons import get_icon
from calibre_plugins.goodreads_sync.common_dialogs import SizePersistedDialog, KeyboardConfigDialog
from calibre_plugins.goodreads_sync.common_widgets import (NoWheelComboBox, ReadOnlyTextIconWidgetItem,
                                                    CheckableTableWidgetItem, ReadOnlyTableWidgetItem,
                                                    ImageTitleLayout, CustomColumnComboBox)

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/Goodreads-Sync'

SUPPORTS_CREATE_CUSTOM_COLUMN = False
try:
    from calibre.gui2.preferences.create_custom_column import CreateNewCustomColumn
    SUPPORTS_CREATE_CUSTOM_COLUMN = True
except ImportError:
    SUPPORTS_CREATE_CUSTOM_COLUMN = False

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

# Top-level store contains our DEVKEY and any other configuration for plugin to work
STORE_PLUGIN = 'Goodreads'
KEY_DEV_TOKEN = 'devkeyToken'
KEY_DEV_SECRET = 'devkeySecret'
KEY_UPDATE_ISBN = 'updateISBN'
KEY_DISPLAY_ADD = 'displayAddMenu'
KEY_DISPLAY_REMOVE = 'displayRemoveMenu'
KEY_DISPLAY_UPDATE_PROGRESS = 'displayUpdateProgressMenu'
KEY_PROGRESS_IS_PERCENT = 'progressIsPercent'
KEY_DISPLAY_SYNC = 'displaySyncMenu'
KEY_DISPLAY_VIEW_SHELF = 'displayViewShelfMenu'
KEY_AUTHOR_SWAP = 'swapAuthor'
KEY_TAG_MAPPING_COLUMN = 'tagMappingColumn'
KEY_RATING_COLUMN = 'ratingColumn'
KEY_DATE_READ_COLUMN = 'dateReadColumn'
KEY_READING_PROGRESS_COLUMN = 'readingProgressColumn'
KEY_REVIEW_TEXT_COLUMN = 'reviewTextColumn'

DEFAULT_STORE_VALUES = {
    KEY_DEV_TOKEN: 'UxvtOM3ogQWjfgiCnMleA',
    KEY_DEV_SECRET: 'AwXtlLJJquCXa2O0L9W6g6MjCoHXEMPZ1eZT6K0Wo',
    KEY_UPDATE_ISBN: 'NEVER',
    KEY_DISPLAY_ADD: True,
    KEY_DISPLAY_REMOVE: True,
    KEY_DISPLAY_UPDATE_PROGRESS: True,
    KEY_PROGRESS_IS_PERCENT: True,
    KEY_DISPLAY_SYNC: True,
    KEY_DISPLAY_VIEW_SHELF: True,
    KEY_AUTHOR_SWAP: False,
    KEY_TAG_MAPPING_COLUMN: 'tags',
    KEY_RATING_COLUMN: '',
    KEY_DATE_READ_COLUMN: '',
    KEY_READING_PROGRESS_COLUMN: '',
    KEY_REVIEW_TEXT_COLUMN: ''
}

KEY_TAG_MAPPINGS = 'tagMappings'
KEY_ADD_ACTIONS = 'add_actions'
KEY_ADD_RATING = 'add_rating'
KEY_ADD_DATE_READ = 'add_date_read'
KEY_ADD_REVIEW_TEXT = 'add_review_text'

KEY_SYNC_ACTIONS = 'sync_actions'
KEY_SYNC_RATING = 'sync_rating'
KEY_SYNC_DATE_READ = 'sync_date_read'
KEY_SYNC_REVIEW_TEXT = 'sync_review_text'

STORE_SCHEMA_VERSION = 'SchemaVersion'
DEFAULT_SCHEMA_VERSION = 1.68

# Store of users will be a dictionary by user id of options
# e.g. 'Grant': {KEY_USER_ID: '12345', KEY_USER_TOKEN: 'xxx', KEY_USER_SECRET: 'yyy',
#                KEY_SHELVES: []}
# Structure of shelves per user will be a list of dictionaries:
# e.g. [{'name': 'to-read', 'exclusive': True, 'active': True, 'book_count': 1, KEY_TAG_MAPPINGS: [],
#        KEY_ADD_ACTIONS: [], KEY_ADD_RATING: False, KEY_ADD_DATE_READ: False, KEY_ADD_REVIEW_TEXT: False,
#        KEY_SYNC_ACTIONS: [], KEY_SYNC_RATING: False, KEY_SYNC_DATE_READ: False, KEY_SYNC_REVIEW_TEXT: False },
#       {...}]
# Structure of add_actions and sync_actions will be an ordered list of dictionaries
# e.g. [{'action': 'Add', 'column': '#read', 'value': 'Y'}, {...}]

STORE_USERS = 'Users'
KEY_USER_ID = 'userId'
KEY_USER_TOKEN = 'userToken'
KEY_USER_SECRET = 'userSecret'
KEY_SHELVES = 'shelves'
DEFAULT_USERS_STORE = {}

SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_TAGS               = '#goodreads_tags'
SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_RATING             = '#goodreads_rating'
SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_DATE_READ          = '#goodreads_date_read'
SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_REVIEW_TEXT        = '#goodreads_review'
SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_READING_PROGRESS   = '#goodreads_reading_progress'
CUSTOM_COLUMN_DEFAULTS = {
                SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_TAGS : {
                    'column_heading': _("Goodreads Tags"),
                    'datatype' : 'text',
                    'is_multiple' : True,
                    'description' : _("Goodreads tags used for mapping to calbre."),
                    'columns_list' : 'avail_text_columns',
                    'config_label' : _('Tags column:'),
                    'config_tool_tip' : _('For use with the "Download tags from shelves" and "Upload tags as shelves" menu items'),
                    'initial_items': ['tags']
                },
                SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_RATING : {
                    'column_heading': _("Goodreads Rating"),
                    'datatype' : 'rating',
                    'description' : _("Rating for the book."),
                    'columns_list' : 'avail_rating_columns',
                    'config_label' : _('Rating column:'),
                    'config_tool_tip' : _('For use with the "Add to shelf" and "Sync from shelf" menu items\nto synchronise with your Goodreads review for a book'),
                    'initial_items': ['']
                },
                SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_DATE_READ : {
                    'column_heading': _("Date Read"),
                    'datatype' : 'datetime',
                    'description' : _("Date when the book was last read."),
                    'columns_list' : 'avail_date_columns',
                    'config_label' : _('Date read column:'),
                    'config_tool_tip' : _('For use with the "Add to shelf" and "Sync from shelf" menu items\nto synchronise with your Goodreads review for a book'),
                    'initial_items': ['']
                },
                SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_REVIEW_TEXT : {
                    'column_heading': _("Goodreads Review"),
                    'datatype' : 'comments',
                    'description' : _("Review of book."),
                    'columns_list' : 'get_long_text_custom_columns',
                    'config_label' : _('Review text column:'),
                    'config_tool_tip' : _('For use with the "Add to shelf" and "Sync from shelf" menu items\nto synchronise with your Goodreads review for a book'),
                    'initial_items': ['','comments']
                },
                SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_READING_PROGRESS : {
                    'column_heading': _("Goodreads Progress"),
                    'datatype' : 'int',
                    'description' : _("Reading progress for the book"),
                    'columns_list' : 'avail_number_columns',
                    'config_label' : _('Reading progress column:'),
                    'config_tool_tip' : _('For use with the "Add to shelf" and "Sync from shelf" menu items\nto synchronise with your Goodreads review for a book'),
                    'initial_items': ['']
                },
            }


URL = 'http://www.goodreads.com'
URL_HTTPS = 'https://www.goodreads.com'

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Goodreads Sync')

# Set defaults
plugin_prefs.defaults[STORE_PLUGIN] = DEFAULT_STORE_VALUES
plugin_prefs.defaults[STORE_USERS] = DEFAULT_USERS_STORE


def migrate_config_if_required():
    # Contains code for migrating versions of json schema
    # Make sure we store our schema version in the file
    schema_version = plugin_prefs.get(STORE_SCHEMA_VERSION, 0)
    if schema_version != DEFAULT_SCHEMA_VERSION:
        plugin_prefs[STORE_SCHEMA_VERSION] = DEFAULT_SCHEMA_VERSION

    # Check for user upgrading from prior to 1.6
    if schema_version < 1.6:
        if DEBUG:
            prints('Migrating Goodreads Sync schema from prior to 1.6')
        tag_mapping_column = 'tags'
        users_settings = plugin_prefs[STORE_USERS]
        for user_info in users_settings.values():
            if KEY_TAG_MAPPINGS in user_info.keys():
                tag_mappings = user_info[KEY_TAG_MAPPINGS]
                for shelf in user_info[KEY_SHELVES]:
                    shelf[KEY_TAG_MAPPINGS] = tag_mappings.get(shelf['name'], [])
                del user_info[KEY_TAG_MAPPINGS]
            if KEY_TAG_MAPPING_COLUMN in user_info.keys():
                tag_mapping_column = user_info.get(KEY_TAG_MAPPING_COLUMN, tag_mapping_column)
                del user_info[KEY_TAG_MAPPING_COLUMN]
            for shelf in user_info[KEY_SHELVES]:
                shelf[KEY_ADD_RATING] = False
                shelf[KEY_ADD_DATE_READ] = False
                shelf[KEY_SYNC_RATING] = False
                shelf[KEY_SYNC_DATE_READ] = False
        plugin_prefs[STORE_USERS] = users_settings

        goodreads_settings = plugin_prefs[STORE_PLUGIN]
        goodreads_settings[KEY_TAG_MAPPING_COLUMN] = tag_mapping_column
        if 'searchLinkShortcut' in goodreads_settings:
            del goodreads_settings['searchLinkShortcut']
        if 'viewLinkShortcut' in goodreads_settings:
            del goodreads_settings['viewLinkShortcut']
        plugin_prefs[STORE_PLUGIN] = goodreads_settings

    # Check for user upgrading from prior to 1.68
    if schema_version < 1.68:
        if DEBUG:
            prints('Migrating Goodreads Sync schema from prior to 1.68')
        users_settings = plugin_prefs[STORE_USERS]
        for user_info in users_settings.values():
            for shelf in user_info[KEY_SHELVES]:
                shelf[KEY_ADD_REVIEW_TEXT] = False
                shelf[KEY_SYNC_REVIEW_TEXT] = False
        plugin_prefs[STORE_USERS] = users_settings

        goodreads_settings = plugin_prefs[STORE_PLUGIN]
        goodreads_settings[KEY_REVIEW_TEXT_COLUMN] = ''
        plugin_prefs[STORE_PLUGIN] = goodreads_settings

def show_help():
    open_url(QUrl(HELP_URL))
   

class UserComboBox(QComboBox):

    def __init__(self, parent, users):
        QComboBox.__init__(self, parent)
        self.populate_combo(users)

    def populate_combo(self, users, selected_text=None):
        self.blockSignals(True)
        self.clear()
        for user_name in sorted(users.keys()):
            self.addItem(user_name)
        if selected_text:
            idx = self.findText(selected_text)
            self.setCurrentIndex(idx)
        elif self.count() > 0:
            self.setCurrentIndex(0)
        self.blockSignals(False)
        self.currentIndexChanged.emit(self.currentIndex())


class ISBNComboBox(QComboBox):

    VALUES = [('NEVER', _('Never modify the calibre ISBN')),
              ('MISSING', _('Replace calibre ISBN only if none present')),
              ('ALWAYS', _('Always overwrite calibre ISBN value'))]

    def __init__(self, parent, value):
        QComboBox.__init__(self, parent)
        self.populate_combo(value)

    def populate_combo(self, selected_value):
        self.clear()
        selected_idx = idx = -1
        for value, text in self.VALUES:
            idx = idx + 1
            self.addItem(text)
            if value == selected_value:
                selected_idx = idx
        self.setCurrentIndex(selected_idx)

    def selected_value(self):
        for value, text in self.VALUES:
            if text == unicode(self.currentText()).strip():
                return value


class ActionTypeComboBox(NoWheelComboBox):

    def __init__(self, parent, selected_action):
        NoWheelComboBox.__init__(self, parent)
        self.populate_combo(selected_action)

    def populate_combo(self, selected_action):
        self.addItems([_('Add value to column'), _('Remove value from column')])
        if selected_action == 'ADD':
            self.setCurrentIndex(0)
        else:
            self.setCurrentIndex(1)

    def get_selected_action(self):
        if self.currentIndex() == 0:
            return 'ADD'
        else:
            return 'REMOVE'


class BoolColumnComboBox(NoWheelComboBox):

    def __init__(self, parent, selected_text='Y'):
        NoWheelComboBox.__init__(self, parent)
        self.populate_combo(selected_text)

    def populate_combo(self, selected_text):
        self.clear()
        self.addItem(QIcon(I('ok.png')), 'Y')
        self.addItem(QIcon(I('list_remove.png')), 'N')
        idx = self.findText(selected_text)
        self.setCurrentIndex(idx)


class EnumColumnComboBox(NoWheelComboBox):

    def __init__(self, parent, selected_text, values):
        NoWheelComboBox.__init__(self, parent)
        self.populate_combo(selected_text, values)

    def populate_combo(self, selected_text, values):
        self.clear()
        self.addItem('')
        self.addItems(values)
        idx = self.findText(selected_text)
        self.setCurrentIndex(idx)


class DateTimeColumnComboBox(NoWheelComboBox):

    VALUE_ADD_MAP = OrderedDict([
                       ('none', _('None')),
                       ('today', _('Today'))
                     ])

    VALUE_SYNC_MAP = OrderedDict([
                       ('none', _('None')),
                       ('today', _('Today')),
                       ('read_at', _('Goodreads Date Read')),
                       ('date_added', _('Goodreads Date Added')),
                       ('date_updated', _('Goodreads Date Updated')),
                       ('started_at', _('Goodreads Date Started'))
                      ])

    def __init__(self, parent, selected_key='today', is_add_values=True):
        NoWheelComboBox.__init__(self, parent)
        if is_add_values:
            self.values_map = self.VALUE_ADD_MAP
        else:
            self.values_map = self.VALUE_SYNC_MAP
        self.populate_combo(selected_key)

    def populate_combo(self, selected_key):
        self.clear()
        selected_text = self.values_map[selected_key]
        for text in self.values_map.values():
            self.addItem(text)
        idx = self.findText(selected_text)
        self.setCurrentIndex(idx)

    def selected_key(self):
        text = unicode(self.currentText()).strip()
        for key, value in self.values_map.items():
            if value == text:
                return key


class AddShelfDialog(QDialog):

    def __init__(self, parent=None, shelves=[]):
        QDialog.__init__(self, parent)
        self.setWindowTitle(_('Create Goodreads shelf'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        content_layout = QGridLayout()
        layout.addLayout(content_layout)
        content_layout.addWidget(QLabel(_('Shelf name:'), self), 0, 0, 1, 1)
        self.name_ledit = QLineEdit('', self)
        content_layout.addWidget(self.name_ledit, 0, 1, 1, 2)

        for key, row, col, tooltip in [('Exclusive', 1, 0, _('A book can only be on one of your exclusive shelves')),
                                       ('Sortable',  1, 1, _('Allowing customizing the order of books on this shelf')),
                                       ('Featured',  1, 2, _('One shelf only can be featured at the top of your profile'))]:
            checkbox = QCheckBox(key, self)
            checkbox.setToolTip(tooltip)
            setattr(self, '_option_'+key.lower(), checkbox)
            content_layout.addWidget(checkbox, row, col, 1, 1)

        layout.addSpacing(20)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        self.resize(self.sizeHint())

    @property
    def shelf_name(self):
        return unicode(self.name_ledit.text()).strip().lower().replace('  ', ' ').replace(' ','-')

    @property
    def is_featured(self):
        return getattr(self, '_option_featured').isChecked()

    @property
    def is_exclusive(self):
        return getattr(self, '_option_exclusive').isChecked()

    @property
    def is_sortable(self):
        return getattr(self, '_option_sortable').isChecked()


class MaintainActionsTableWidget(QTableWidget):

    def __init__(self, parent, is_shelf_add_actions, custom_columns, all_tags):
        QTableWidget.__init__(self, parent)
        self.is_shelf_add_actions = is_shelf_add_actions
        self.custom_columns = custom_columns
        self.all_tags = all_tags
        self.db = parent.db

    def populate_table(self, sync_actions):
        self.clear()
        self.setAlternatingRowColors(True)
        header_labels = [_('Action'), _('Column'), _('Value')]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(24)
        self.horizontalHeader().setStretchLastSection(True)

        # Validate to check if any actions need to be removed.
        valid_sync_actions = []
        for sync_action in sync_actions:
            column_key = sync_action['column']
            if column_key == 'tags' or column_key in self.custom_columns:
                valid_sync_actions.append(sync_action)
            else:
                # The custom column has been edited/renamed so we will remove it
                info_dialog(self, _('Invalid column'),
                    _("Removing the column '{0}' action as the column cannot be found").format(column_key),
                    show=True)
        self.setRowCount(len(valid_sync_actions))

        for row, sync_action in enumerate(valid_sync_actions):
            self.populate_table_row(row, sync_action)

        self.setColumnWidth(0, 180)
        self.setColumnWidth(1, 200)
        self.setSortingEnabled(False)
        self.setMinimumSize(500, 0)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        if len(valid_sync_actions) > 0:
            self.selectRow(0)

    def populate_table_row(self, row, sync_action):
        column_key = sync_action['column']
        self.setCellWidget(row, 0, ActionTypeComboBox(self, sync_action['action']))
        combo = CustomColumnComboBox(self, self.custom_columns, column_key, initial_items=['tags'])
        combo.currentIndexChanged.connect(partial(self.column_type_changed, combo, row))
        self.setCellWidget(row, 1, combo)
        if self.is_bool_custom_column(column_key):
            self.setCellWidget(row, 2, BoolColumnComboBox(self, sync_action['value']))
        elif self.is_datetime_custom_column(column_key):
            self.setCellWidget(row, 2, DateTimeColumnComboBox(self, sync_action['value'], is_add_values=self.is_shelf_add_actions))
        elif self.is_enumeration_custom_column(column_key):
            values = self.custom_columns[column_key]['display']['enum_values']
            self.setCellWidget(row, 2, EnumColumnComboBox(self, sync_action['value'], values))
        elif column_key == 'tags':
            self.setCellWidget(row, 2, self.create_tags_edit(sync_action['value'], self.all_tags))
        elif self.custom_columns[column_key]['is_multiple'] is not None:
            values = self.get_taglike_column_values(column_key)
            self.setCellWidget(row, 2, self.create_tags_edit(sync_action['value'], values))
        else:
            self.setItem(row, 2, QTableWidgetItem(sync_action['value']))

    def column_type_changed(self, combo, row):
        column_key = combo.get_selected_column()
        if self.is_bool_custom_column(column_key):
            self.setCellWidget(row, 2, BoolColumnComboBox(self))
        elif self.is_datetime_custom_column(column_key):
            self.setCellWidget(row, 2, DateTimeColumnComboBox(self, is_add_values=self.is_shelf_add_actions))
        elif self.is_enumeration_custom_column(column_key):
            values = self.custom_columns[column_key]['display']['enum_values']
            self.setCellWidget(row, 2, EnumColumnComboBox(self, '', values))
        elif column_key == 'tags':
            self.setCellWidget(row, 2, self.create_tags_edit('', self.all_tags))
        elif self.custom_columns[column_key]['is_multiple'] is not None:
            values = self.get_taglike_column_values(column_key)
            self.setCellWidget(row, 2, self.create_tags_edit('', values))
        else:
            self.removeCellWidget(row, 2)
            self.setItem(row, 2, QTableWidgetItem(''))

    def create_tags_edit(self, value, all_values):
        tags = EditWithComplete(self)
        tags.set_add_separator(False)
        tags.update_items_cache(all_values)
        tags.setText(value)
        return tags

    def get_taglike_column_values(self, column_key):
        label = self.db.field_metadata.key_to_label(column_key)
        values = list(self.db.all_custom(label=label))
        return values

    def is_bool_custom_column(self, column_key):
        return column_key.startswith('#') and self.custom_columns[column_key]['datatype'] == 'bool'

    def is_datetime_custom_column(self, column_key):
        return column_key.startswith('#') and self.custom_columns[column_key]['datatype'] == 'datetime'

    def is_enumeration_custom_column(self, column_key):
        return column_key.startswith('#') and self.custom_columns[column_key]['datatype'] == 'enumeration'

    def add_row(self):
        self.setFocus()
        # We will insert a blank row at the end
        row = self.rowCount()
        self.insertRow(row)
        self.populate_table_row(row, self.create_blank_row_data())
        self.select_and_scroll_to_row(row)

    def delete_rows(self):
        self.setFocus()
        selrows = self.selectionModel().selectedRows()
        selrows = sorted(selrows, key=lambda x: x.row())
        if len(selrows) == 0:
            return
        message = _("Are you sure you want to delete this action?")
        if len(selrows) > 1:
            message = _("Are you sure you want to delete the selected {0} actions?").format(len(selrows))
        if not question_dialog(self, _('Are you sure?'), '<p>' + message, show_copy_button=False):
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

    def select_and_scroll_to_row(self, row):
        self.selectRow(row)
        self.scrollToItem(self.currentItem())

    def create_blank_row_data(self):
        sync_action = {}
        sync_action['action'] = 'ADD'
        sync_action['column'] = 'tags'
        sync_action['value'] = ''
        return sync_action

    def get_data(self):
        sync_actions = []
        for row in range(self.rowCount()):
            sync_action = {}
            sync_action['action'] = self.cellWidget(row, 0).get_selected_action()
            column_key = sync_action['column'] = self.cellWidget(row, 1).get_selected_column()
            if self.is_bool_custom_column(column_key) or self.is_enumeration_custom_column(column_key):
                value = unicode(self.cellWidget(row, 2).currentText()).strip()
            elif self.is_datetime_custom_column(column_key):
                value = self.cellWidget(row, 2).selected_key()
            elif column_key == 'tags' or self.custom_columns[column_key]['is_multiple'] is not None:
                value = unicode(self.cellWidget(row, 2).text()).strip()
            else:
                value = unicode(self.item(row, 2).text()).strip()
            if not value:
                continue
            sync_action['value'] = value
            sync_actions.append(sync_action)
        return sync_actions


class MaintainActionsDialog(SizePersistedDialog):
    '''
    This dialog allows the user to specify which actions if any to perform when
    using the "Add to shelf" or "Sync from shelf" actions
    '''
    def __init__(self, parent, is_shelf_add_actions, shelves, custom_columns, all_tags):
        SizePersistedDialog.__init__(self, parent, 'goodreads sync plugin:maintain sync action dialog')
        
        self.db = parent.db

        if is_shelf_add_actions:
            self.setWindowTitle(_('Edit Shelf Add Actions'))
            title = _("Edit add to shelf actions for {0} shelves").format(len(shelves))
            if len(shelves) == 1:
                title = _("Edit add to shelf actions for '{0}' shelf").format(shelves[0]['name'])
            message = _("&What should calibre do with matching linked books when you click 'Add to shelf'?")
            title_layout = ImageTitleLayout(self, 'images/edit_shelf_add_action_lg.png', title)
        else:
            self.setWindowTitle(_('Edit Shelf Sync Actions'))
            title = _("Edit sync actions for {0} shelves").format(len(shelves))
            if len(shelves) == 1:
                title = _("Edit sync actions for '{0}' shelf").format(shelves[0]['name'])
            message = _("&What should calibre do with matching linked books when you click 'Sync from shelf'?")
            title_layout = ImageTitleLayout(self, 'images/edit_sync_action_lg.png', title)

        layout = QVBoxLayout(self)
        self.setLayout(layout)
        layout.addLayout(title_layout)

        heading_label = QLabel(message, self)
        layout.addWidget(heading_label)

        # Add a horizontal layout containing the table and the buttons next to it
        table_layout = QHBoxLayout()
        layout.addLayout(table_layout)

        # Create a table the user can edit the data values in
        self.sync_actions_table = MaintainActionsTableWidget(self, is_shelf_add_actions, custom_columns, all_tags)
        layout.addWidget(self.sync_actions_table)
        heading_label.setBuddy(self.sync_actions_table)
        table_layout.addWidget(self.sync_actions_table)

        # Add a vertical layout containing the the buttons to add/remove actions.
        button_layout = QVBoxLayout()
        table_layout.addLayout(button_layout)

        add_button = QToolButton(self)
        add_button.setToolTip(_('Add action'))
        add_button.setIcon(QIcon(I('plus.png')))
        add_button.clicked.connect(self.sync_actions_table.add_row)
        button_layout.addWidget(add_button)

        delete_button = QToolButton(self)
        delete_button.setToolTip(_('Delete action'))
        delete_button.setIcon(QIcon(I('minus.png')))
        delete_button.clicked.connect(self.sync_actions_table.delete_rows)
        button_layout.addWidget(delete_button)
        spacerItem1 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem1)

        # Do not allow ticking checkboxes for these items when the 'currently-reading' shelf,
        # as they should only be applied on the 'read' shelf for reading progress purposes.
        is_currently_reading_shelf = False
        for shelf in shelves:
            if shelf['name'] == 'currently-reading':
                is_currently_reading_shelf = True
                
        if is_shelf_add_actions:
            rating_title = _('Upload rating to Goodreads when adding to this shelf')
            date_read_title = _('Upload date read to Goodreads when adding to this shelf')
            review_text_title = _('Upload review text to Goodreads when adding to this shelf')
            upload_rating_enabled = shelves[0].get(KEY_ADD_RATING, False) and not is_currently_reading_shelf
            upload_date_read_enabled = shelves[0].get(KEY_ADD_DATE_READ, False) and not is_currently_reading_shelf
            upload_review_text_enabled = shelves[0].get(KEY_ADD_REVIEW_TEXT, False) and not is_currently_reading_shelf
        else:
            rating_title = _('Sync rating from Goodreads when syncing from this shelf')
            date_read_title = _('Sync date read from Goodreads when syncing from this shelf')
            review_text_title = _('Sync review text from Goodreads when syncing from this shelf')
            upload_rating_enabled = shelves[0].get(KEY_SYNC_RATING, False) and not is_currently_reading_shelf
            upload_date_read_enabled = shelves[0].get(KEY_SYNC_DATE_READ, False) and not is_currently_reading_shelf
            upload_review_text_enabled = shelves[0].get(KEY_SYNC_REVIEW_TEXT, False) and not is_currently_reading_shelf

        self.upload_rating = QCheckBox(rating_title)
        layout.addWidget(self.upload_rating)
        self.upload_rating.setChecked(upload_rating_enabled)
        if (is_currently_reading_shelf):
            self.upload_rating.setDisabled(True)

        self.upload_date_read = QCheckBox(date_read_title)
        layout.addWidget(self.upload_date_read)
        self.upload_date_read.setChecked(upload_date_read_enabled)
        if (is_currently_reading_shelf):
            self.upload_date_read.setDisabled(True)

        self.upload_review_text = QCheckBox(review_text_title)
        layout.addWidget(self.upload_review_text)
        self.upload_review_text.setChecked(upload_review_text_enabled)
        if (is_currently_reading_shelf):
            self.upload_review_text.setDisabled(True)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        if is_shelf_add_actions:
            shelf_actions = shelves[0].get(KEY_ADD_ACTIONS, [])
        else:
            shelf_actions = shelves[0].get(KEY_SYNC_ACTIONS, [])
        self.sync_actions_table.populate_table(shelf_actions)

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def get_shelf_actions(self):
        return self.sync_actions_table.get_data()


class ShelvesTableWidget(QTableWidget):

    def __init__(self, parent, custom_columns, all_tags):
        QTableWidget.__init__(self, parent)
        self.custom_columns = custom_columns
        self.all_tags = all_tags
        self.create_context_menu()
        self.db = parent.db

    def populate_table(self, shelves):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(shelves))
        header_labels = [_('Active'), _('Shelf Name'), _('Count*'), _('calibre Tags'), _('Shelf Add Actions'), _('Sync Actions')]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(24)
        #self.horizontalHeader().setStretchLastSection(True)

        self.shelves = shelves
        for row, data in enumerate(shelves):
            self.populate_table_row(row, data)

        self.resizeColumnsToContents()
        self.setSortingEnabled(False)
        self.setMinimumSize(500, 100)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        if len(shelves) > 0:
            self.selectRow(0)

    def create_context_menu(self):
        self.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.edit_shelf_add_action = QAction(get_icon('images/edit_shelf_add_action.png'), _('Edit shelf add actions')+'...', self)
        self.edit_shelf_add_action.triggered.connect(self.edit_shelf_add_actions)
        self.addAction(self.edit_shelf_add_action)
        self.edit_sync_action = QAction(get_icon('images/edit_sync_action.png'), _('Edit sync actions')+'...', self)
        self.edit_sync_action.triggered.connect(self.edit_shelf_sync_actions)
        self.addAction(self.edit_sync_action)
        sep1 = QAction(self)
        sep1.setSeparator(True)
        self.addAction(sep1)
        self.display_all_action = QAction(_('Make all Active'), self)
        self.display_all_action.triggered.connect(partial(self.toggle_display, True))
        self.addAction(self.display_all_action)
        self.display_none_action = QAction(_('Make none Active'), self)
        self.display_none_action.triggered.connect(partial(self.toggle_display, False))
        self.addAction(self.display_none_action)
        sep2 = QAction(self)
        sep2.setSeparator(True)
        self.addAction(sep2)
        self.edit_shelves_action = QAction(get_icon('images/view_book.png'), _('Edit Shelves on Goodreads'), self)
        self.edit_shelves_action.triggered.connect(self.edit_shelves_on_goodreads)
        self.addAction(self.edit_shelves_action)

    def toggle_display(self, toggle_all):
        for row in range(self.rowCount()):
            if toggle_all:
                self.item(row, 0).setCheckState(Qt.Checked)
            else:
                self.item(row, 0).setCheckState(Qt.Unchecked)

    def populate_table_row(self, row, shelf):
        self.setItem(row, 0, CheckableTableWidgetItem(shelf['active']))
        icon_name = 'images/shelf.png'
        if shelf['exclusive']:
            icon_name = 'images/shelf_exclusive.png'
        item = ReadOnlyTextIconWidgetItem(shelf['name'], get_icon(icon_name))
        if shelf['exclusive']:
            item.setToolTip(_('Shelf marked as exclusive'))
        self.setItem(row, 1, item)
        item = ReadOnlyTableWidgetItem(shelf['book_count'])
        item.setToolTip(_('Count as at last shelves list refresh'))
        self.setItem(row, 2, item)

        self.setCellWidget(row, 3, self._create_tags_edit(', '.join(shelf.get(KEY_TAG_MAPPINGS, []))))
        text, image = self._build_actions_text(shelf, add=True)
        self.setItem(row, 4, ReadOnlyTextIconWidgetItem(text, image))
        text, image = self._build_actions_text(shelf, add=False)
        self.setItem(row, 5, ReadOnlyTextIconWidgetItem(text, image))

    def _create_tags_edit(self, value):
        tags = EditWithComplete(self)
        tags.set_add_separator(False)
        tags.update_items_cache(self.tags_values)
        tags.setText(value)
        return tags

    def set_tags_values(self, values):
        self.tags_values = values
        # Iterate through all of the rows and switch the cache values
        for row in range(self.rowCount()):
            widget = self.cellWidget(row, 3)
            widget.update_items_cache(values)

    def _build_actions_text(self, shelf, add):
        # Convert our sync action(s) if any for this shelf to readable text
        message = ''
        image_name = ''
        if add:
            actions_key = KEY_ADD_ACTIONS
            if shelf.get(KEY_ADD_RATING, False) and shelf.get(KEY_ADD_DATE_READ, False):
                image_name = 'images/rating_dateread_add.png'
            elif shelf.get(KEY_ADD_RATING, False):
                image_name = 'images/rating_add.png'
            elif shelf.get(KEY_ADD_DATE_READ, False):
                image_name = 'images/dateread_add.png'
            elif shelf.get(KEY_ADD_REVIEW_TEXT, False):
                image_name = 'images/review_add.png'
        else:
            actions_key = KEY_SYNC_ACTIONS
            if shelf.get(KEY_SYNC_RATING, False) and shelf.get(KEY_SYNC_DATE_READ, False):
                image_name = 'images/rating_dateread_sync.png'
            elif shelf.get(KEY_SYNC_RATING, False):
                image_name = 'images/rating_sync.png'
            elif shelf.get(KEY_SYNC_DATE_READ, False):
                image_name = 'images/dateread_sync.png'
            elif shelf.get(KEY_SYNC_REVIEW_TEXT, False):
                image_name = 'images/review_sync.png'

        if actions_key not in shelf:
            shelf[actions_key] = []
        else:
            for sync_action in shelf[actions_key]:
                sync_action_type = sync_action['action']
                if sync_action_type == 'ADD':
                    message = message + _("Add '{0}' to column '{1}', ").format(sync_action['value'], sync_action['column'])
                elif sync_action_type == 'REMOVE':
                    message = message + _("Remove '{0}' from column '{1}', ").format(sync_action['value'], sync_action['column'])
        if len(message) > 2:
            message = message[:-2]
        icon = None
        if image_name:
            icon = get_icon(image_name)
        return message, icon

    def get_data(self):
        for row in range(self.rowCount()):
            shelf = self.shelves[row]
            shelf['active'] = self.item(row, 0).checkState() == Qt.Checked
            shelf['book_count'] = unicode(self.item(row, 2).text()).strip()
            shelf[KEY_TAG_MAPPINGS] = self._get_tags_data(row)
        return self.shelves

    def _get_tags_data(self, row):
        tags_text = unicode(self.cellWidget(row, 3).text()).strip()
        tag_values = tags_text.split(',')
        tags_list = []
        for tag in tag_values:
            if len(tag.strip()) > 0:
                tags_list.append(tag.strip())
        return tags_list

    def edit_shelf_add_actions(self):
        self.edit_actions(is_shelf_add_actions=True)

    def edit_shelf_sync_actions(self):
        self.edit_actions(is_shelf_add_actions=False)

    def edit_actions(self, is_shelf_add_actions):
        if self.currentRow() < 0:
            return None
        shelves = self.get_data()
        rows = self.selectionModel().selectedRows()
        selected_shelves = [shelves[row.row()] for row in rows]
        d = MaintainActionsDialog(self, is_shelf_add_actions, selected_shelves,
                                        self.custom_columns, self.all_tags)
        d.exec_()
        if d.result() == d.Accepted:
            actions = d.get_shelf_actions()
            for row in rows:
                shelf = shelves[row.row()]
                if is_shelf_add_actions:
                    shelf[KEY_ADD_ACTIONS] = actions
                    shelf[KEY_ADD_RATING] = d.upload_rating.isChecked()
                    shelf[KEY_ADD_DATE_READ] = d.upload_date_read.isChecked()
                    shelf[KEY_ADD_REVIEW_TEXT] = d.upload_review_text.isChecked()
                else:
                    shelf[KEY_SYNC_ACTIONS] = actions
                    shelf[KEY_SYNC_RATING] = d.upload_rating.isChecked()
                    shelf[KEY_SYNC_DATE_READ] = d.upload_date_read.isChecked()
                    shelf[KEY_SYNC_REVIEW_TEXT] = d.upload_review_text.isChecked()
                self.populate_table_row(row.row(), shelf)

    def edit_shelves_on_goodreads(self):
        url = '%s/shelf/edit' % URL
        open_url(QUrl(url))


class ConfigWidget(QWidget):

    def __init__(self, plugin_action, grhttp):
        super(ConfigWidget, self).__init__()
        self.plugin_action = plugin_action
        self.db = plugin_action.gui.library_view.model().db
        self.grhttp = grhttp
        # Shared users config information reflecting current selections
        self.users = plugin_prefs[STORE_USERS]
        self.user_name = None
        other_options = plugin_prefs[STORE_PLUGIN]
        self.must_restart = False
        self._get_create_new_custom_column_instance = None
        self.supports_create_custom_column = SUPPORTS_CREATE_CUSTOM_COLUMN

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        user_layout = QHBoxLayout()
        layout.addLayout(user_layout)
        user_label = QLabel(_('Select Goodreads user:'), self)
        user_layout.addWidget(user_label)
        self._user_combo = UserComboBox(self, self.users)
        self._user_combo.currentIndexChanged.connect(self.user_combo_index_changed)
        self._user_combo.setMinimumSize(150, 20)
        user_layout.addWidget(self._user_combo)
        self._add_user_button = QToolButton(self)
        self._add_user_button.setToolTip(_('Add user profile'))
        self._add_user_button.setIcon(QIcon(I('plus.png')))
        self._add_user_button.clicked.connect(self.add_user_profile)
        user_layout.addWidget(self._add_user_button)
        self._delete_user_button = QToolButton(self)
        self._delete_user_button.setToolTip(_('Delete user profile'))
        self._delete_user_button.setIcon(QIcon(I('minus.png')))
        self._delete_user_button.clicked.connect(self.delete_user_profile)
        user_layout.addWidget(self._delete_user_button)
        self._auth_button = QPushButton(_('Authorize Plugin with Goodreads'), self)
        self._auth_button.setIcon(get_icon('images/authorise.png'))
        self._auth_button.clicked.connect(self.authorize_plugin)
        user_layout.addWidget(self._auth_button)
        user_layout.addStretch()

        user_group_box = QGroupBox(_('User Shelves:'), self)
        layout.addWidget(user_group_box, 2)
        user_group_box_layout = QVBoxLayout()
        user_group_box.setLayout(user_group_box_layout)

        action_custom_columns = self.get_custom_columns(['bool', 'text', 'comments', 'datetime', 'enumeration'])
        self.all_tags = self.plugin_action.gui.library_view.model().db.all_tags()
        self._shelves_table = ShelvesTableWidget(self, action_custom_columns, self.all_tags)
        user_group_box_layout.addWidget(self._shelves_table)

        user_buttons_layout = QHBoxLayout()
        layout.addLayout(user_buttons_layout)
        self._sync_shelves_button = QPushButton(_('Refresh Shelves'), self)
        self._sync_shelves_button.setToolTip(_('Refresh the list of shelves and book counts from Goodreads'))
        self._sync_shelves_button.setIcon(get_icon('images/refresh.png'))
        self._sync_shelves_button.clicked.connect(self.refresh_shelves_list)
        user_buttons_layout.addWidget(self._sync_shelves_button)
        self._add_shelf_action_button = QPushButton(_('Add Shelf')+'...', self)
        self._add_shelf_action_button.setToolTip(_('Add a new shelf'))
        self._add_shelf_action_button.setIcon(get_icon('plus.png'))
        self._add_shelf_action_button.clicked.connect(self.add_shelf)
        user_buttons_layout.addWidget(self._add_shelf_action_button)
        user_buttons_layout.addStretch()
        self._edit_add_to_shelf_action_button = QPushButton(_("Edit 'Shelf Add' Actions")+'...', self)
        self._edit_add_to_shelf_action_button.setToolTip(_("Edit actions to apply when using 'Add to shelf'"))
        self._edit_add_to_shelf_action_button.setIcon(get_icon('images/edit_shelf_add_action.png'))
        self._edit_add_to_shelf_action_button.clicked.connect(self._shelves_table.edit_shelf_add_actions)
        user_buttons_layout.addWidget(self._edit_add_to_shelf_action_button)
        self._edit_sync_action_button = QPushButton(_("Edit 'Sync' Actions")+'...', self)
        self._edit_sync_action_button.setToolTip(_("Edit actions to apply when using 'Sync from shelf'"))
        self._edit_sync_action_button.setIcon(get_icon('images/edit_sync_action.png'))
        self._edit_sync_action_button.clicked.connect(self._shelves_table.edit_shelf_sync_actions)
        user_buttons_layout.addWidget(self._edit_sync_action_button)

        layout.addSpacing(10)
        bottom_options_layout = QHBoxLayout()
        layout.addLayout(bottom_options_layout)

        other_group_box = QGroupBox(_('Other Options:'), self)
        bottom_options_layout.addWidget(other_group_box)
        other_group_box_layout = QGridLayout()
        other_group_box.setLayout(other_group_box_layout)

        isbn_label = QLabel(_('When linking to Goodreads:'), self)
        self._isbn_combo = ISBNComboBox(self, other_options.get(KEY_UPDATE_ISBN, 'NEVER'))
        isbn_label.setBuddy(self._isbn_combo)
        other_group_box_layout.addWidget(isbn_label, 0, 0)
        other_group_box_layout.addWidget(self._isbn_combo, 0, 1)
        for row, key, display, tooltip in [
                                (1, KEY_DISPLAY_ADD, _("Display the 'Add to shelf' menu option"), ''),
                                (2, KEY_DISPLAY_REMOVE, _("Display the 'Remove from shelf' menu option"), ''),
                                (3, KEY_DISPLAY_UPDATE_PROGRESS, _("Display the 'Update reading progress' menu option"), ''),
                                (4, KEY_DISPLAY_SYNC, _("Display the 'Sync from shelf' menu option"), ''),
                                (5, KEY_DISPLAY_VIEW_SHELF, _("Display the 'View shelf' menu option"), ''),
                                (6, KEY_PROGRESS_IS_PERCENT, _("Reading progress is percent read"), _("If the reading progress is the percent read, check this. Otherwise, the reading progress the page number.")),
                                (7, KEY_AUTHOR_SWAP, _("If adding empty books, store author as LN,FN"), ''),
                                ]:
            enabled_checkbox = QCheckBox(display, self)
            enabled_checkbox.setChecked(other_options.get(key, True))
            if len(tooltip) > 0:
                enabled_checkbox.setToolTip(tooltip)
            setattr(self, '_other_'+key, enabled_checkbox)
            other_group_box_layout.addWidget(enabled_checkbox, row, 0, 1, 2)

        columns_group_box = QGroupBox(_('Synchronisable Custom Columns:'), self)
        bottom_options_layout.addWidget(columns_group_box)
        columns_group_box_layout = QHBoxLayout()
        columns_group_box.setLayout(columns_group_box_layout)
        columns_group_box_layout2 = QFormLayout()
        columns_group_box_layout.addLayout(columns_group_box_layout2)
        columns_group_box_layout.addStretch()

        self.sync_custom_columns = {}
        self.sync_custom_columns[SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_TAGS] = {'current_columns' : self.get_text_custom_columns}
        self.sync_custom_columns[SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_RATING] = {'current_columns': self.get_rating_custom_columns}
        self.sync_custom_columns[SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_DATE_READ] = {'current_columns': self.get_date_custom_columns}
        self.sync_custom_columns[SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_REVIEW_TEXT] = {'current_columns': self.get_long_text_custom_columns}
        self.sync_custom_columns[SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_READING_PROGRESS] = {'current_columns': self.get_number_custom_columns}

        self._tag_column_combo = self.create_custom_column_controls(columns_group_box_layout2, SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_TAGS)
        self._tag_column_combo.currentIndexChanged[int].connect(self.tag_column_combo_changed)
        self._rating_column_combo = self.create_custom_column_controls(columns_group_box_layout2, SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_RATING)
        self._dateread_column_combo = self.create_custom_column_controls(columns_group_box_layout2, SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_DATE_READ)
        self._review_text_column_combo = self.create_custom_column_controls(columns_group_box_layout2, SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_REVIEW_TEXT)
        self._reading_progress_column_combo = self.create_custom_column_controls(columns_group_box_layout2, SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_READING_PROGRESS)

        self._tag_column_combo.populate_combo(
                    self.sync_custom_columns[SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_TAGS]['current_columns'](), 
                    other_options.get(KEY_TAG_MAPPING_COLUMN, 'tags'), 
                    initial_items=CUSTOM_COLUMN_DEFAULTS[SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_TAGS]['initial_items']
                    )
        self._rating_column_combo.populate_combo(
                    self.sync_custom_columns[SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_RATING]['current_columns'](), 
                    other_options.get(KEY_RATING_COLUMN, ''),
                    initial_items=CUSTOM_COLUMN_DEFAULTS[SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_RATING]['initial_items']
                    )
        self._dateread_column_combo.populate_combo(
                    self.sync_custom_columns[SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_DATE_READ]['current_columns'](), 
                    other_options.get(KEY_DATE_READ_COLUMN, ''),
                    initial_items=CUSTOM_COLUMN_DEFAULTS[SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_DATE_READ]['initial_items']
                    )
        self._review_text_column_combo.populate_combo(
                    self.sync_custom_columns[SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_REVIEW_TEXT]['current_columns'](), 
                    other_options.get(KEY_REVIEW_TEXT_COLUMN, ''),
                    initial_items=CUSTOM_COLUMN_DEFAULTS[SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_REVIEW_TEXT]['initial_items']
                    )
        self._reading_progress_column_combo.populate_combo(
                    self.sync_custom_columns[SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_READING_PROGRESS]['current_columns'](), 
                    other_options.get(KEY_READING_PROGRESS_COLUMN, ''),
                    initial_items=CUSTOM_COLUMN_DEFAULTS[SYNC_CUSTOM_COLUMN_DEFAULT_LOOKUP_READING_PROGRESS]['initial_items']
                    )

        keyboard_layout = QHBoxLayout()
        layout.addLayout(keyboard_layout)
        keyboard_shortcuts_button = QPushButton(' '+_('Keyboard shortcuts')+'... ', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        keyboard_layout.addWidget(keyboard_shortcuts_button)

        help_button = QPushButton(' '+_('Help'), self)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(show_help)
        keyboard_layout.addWidget(help_button)
        keyboard_layout.addStretch()

        # Force the possible tags values to be set based on the initial tag column setting
        self.tag_column_combo_changed()
        # Force an initial display of shelves for this user
        self.user_combo_index_changed()

        # If this is the first time into the dialog (no users defined), force the user to add one
        if len(self.users) == 0:
            self.add_user_profile()

    def save_settings(self):
        # We only need to update the store for the current user, as switching users
        # will have updated the other stores
        self.persist_user_config()
        plugin_prefs[STORE_USERS] = self.users

        other_options = plugin_prefs[STORE_PLUGIN]
        other_options[KEY_TAG_MAPPING_COLUMN] = self._tag_column_combo.get_selected_column()
        other_options[KEY_RATING_COLUMN] = self._rating_column_combo.get_selected_column()
        other_options[KEY_READING_PROGRESS_COLUMN] = self._reading_progress_column_combo.get_selected_column()
        other_options[KEY_DATE_READ_COLUMN] = self._dateread_column_combo.get_selected_column()
        other_options[KEY_REVIEW_TEXT_COLUMN] = self._review_text_column_combo.get_selected_column()
        for key in [KEY_DISPLAY_ADD, KEY_DISPLAY_REMOVE, KEY_DISPLAY_SYNC, 
                    KEY_AUTHOR_SWAP, KEY_DISPLAY_UPDATE_PROGRESS, KEY_PROGRESS_IS_PERCENT,
                    KEY_DISPLAY_VIEW_SHELF
                    ]:
            other_options[key] = getattr(self, '_other_'+key).isChecked()
        other_options[KEY_UPDATE_ISBN] = self._isbn_combo.selected_value()

        plugin_prefs[STORE_PLUGIN] = other_options

    def get_number_custom_columns(self):
        column_types = ['float','int']
        return self.get_custom_columns(column_types)

    def get_rating_custom_columns(self):
        column_types = ['rating','int']
        custom_columns = self.get_custom_columns(column_types)
        ratings_column_name = self.plugin_action.gui.library_view.model().orig_headers['rating']
        custom_columns['rating'] = {'name': ratings_column_name}
        return custom_columns

    def get_text_custom_columns(self):
        column_types = ['text']
        return self.get_custom_columns(column_types)

    def get_long_text_custom_columns(self):
        column_types = ['text', 'comments']
        return self.get_custom_columns(column_types)

    def get_date_custom_columns(self):
        column_types = ['datetime']
        return self.get_custom_columns(column_types)

    def get_custom_columns(self, column_types):
        if self.supports_create_custom_column:
            custom_columns = self.get_create_new_custom_column_instance.current_columns()
        else:
            custom_columns = self.plugin_action.gui.library_view.model().custom_columns
        available_columns = {}
        for key, column in custom_columns.items():
            typ = column['datatype']
            if typ in column_types:
                available_columns[key] = column
        return available_columns

    def persist_user_config(self):
        if not self.user_name:
            return
        # Update all of the current user information in the store
        user_info = self.users[self.user_name]
        user_info[KEY_SHELVES] = self._shelves_table.get_data()
        self.users[self.user_name] = user_info

    def user_combo_index_changed(self):
        # Update the dialog contents with metadata for the selected item
        if self._user_combo.count() == 0:
            self.user_name = None
        else:
            self.user_name = unicode(self._user_combo.currentText()).strip()
        is_controls_enabled = is_sync_shelf_enabled = is_delete_enabled = False
        shelves = []
        if self.user_name:
            is_controls_enabled = True
            user_info = self.users[self.user_name]
            shelves = user_info[KEY_SHELVES]
            is_sync_shelf_enabled = user_info[KEY_USER_TOKEN] is not None
            is_delete_enabled = self._user_combo.count() > 0
        self._shelves_table.populate_table(shelves)
        self._auth_button.setEnabled(is_controls_enabled)
        self._shelves_table.setEnabled(is_controls_enabled)
        self._sync_shelves_button.setEnabled(is_sync_shelf_enabled)
        self._delete_user_button.setEnabled(is_delete_enabled)

    def tag_column_combo_changed(self):
        selected_column = self._tag_column_combo.get_selected_column()
        values = []
        if selected_column == 'tags':
            values = self.all_tags
        elif selected_column is not None:
            # Need to get all the possible values for this custom column
            try: # Catch an error when new columns are being added.
                label = self.db.field_metadata.key_to_label(selected_column)
                values = list(self.db.all_custom(label=label))
                values.sort(key=sort_key)
            except:
                pass 
        self._shelves_table.set_tags_values(values)

    def add_user_profile(self):
        # Display a prompt allowing user to specify a new user name
        new_user_name, ok = QInputDialog.getText(self, _('Add new user'),
                    _('You must create a profile for each Goodreads user you will connect to.<br>Enter a unique display name for this user profile:'), text='Default')
        if not ok:
            # Operation cancelled
            return
        new_user_name = unicode(new_user_name).strip()
        # Verify it does not clash with any other users in the list
        for user_name in self.users.keys():
            if user_name.lower() == new_user_name.lower():
                return error_dialog(self, _('Add Failed'), _('A user with the same name already exists'), show=True)
        user_info = {}
        user_info[KEY_USER_ID] = None
        user_info[KEY_USER_TOKEN] = None
        user_info[KEY_USER_SECRET] = None
        user_info[KEY_SHELVES] = []
        self.users[new_user_name] = user_info
        # As we are about to switch user, persist the current users's details if any
        self.persist_user_config()
        # Now update the combobox
        self._user_combo.populate_combo(self.users, new_user_name)
        self.user_combo_index_changed()

    def delete_user_profile(self):
        if not question_dialog(self, _('Are you sure?'), '<p>'+
                _("Do you want to delete the user profile for '{0}'").format(self.user_name),
                show_copy_button=False):
            return
        del self.users[self.user_name]
        # Now update the combobox
        self._user_combo.populate_combo(self.users)
        self.user_combo_index_changed()

    def authorize_plugin(self):
        # Construct the authorization URL to open in a web browser
        (request_token, request_secret) = self.grhttp.get_request_token_secret()
        if not request_token:
            return
        authorize_link = '%s/oauth/authorize/?oauth_token=%s' % (URL, request_token)
        open_url(QUrl(authorize_link))
        # Display dialog waiting for the user to confirm they have authorized in web browser
        if not question_dialog(self, 
                               _('Confirm Authorization'), 
                               '<p>'+_("Have you clicked 'Allow access' for this plugin on the Goodreads website?")):
            return

        # If user has authorized, we can get their user token information
        (user_token, user_secret) = self.grhttp.get_user_token_secret(oauth_token=request_token,
                                                                      oauth_secret=request_secret)
        if not user_token:
            return
        user_info = self.users[self.user_name]
        user_info[KEY_USER_TOKEN] = user_token
        user_info[KEY_USER_SECRET] = user_secret

        # Now also retrieve the Goodreads user id so we can use it in web queries
        user_id = self.grhttp.get_goodreads_user_id(oauth_token=user_token, oauth_secret=user_secret)
        if not user_id:
            return error_dialog(self, _('Goodreads failure'), _('Unable to obtain the user id'), show=True)
        user_info[KEY_USER_ID] = user_id

        # Read the list of shelves for this user
        self.refresh_shelves_list()

    def refresh_shelves_list(self):
        user_info = self.users[self.user_name]
        self._sync_shelves_button.setEnabled(False)
        try:
            new_shelves = self.grhttp.get_shelf_list(user_info[KEY_USER_ID])
            if not new_shelves:
                return
            # Mark as inactive any shelves that were inactive previously and copy across
            # sync actions, and delete info for shelves that don't exist any more.
            old_shelves = self._shelves_table.get_data()
            for old_shelf_info in old_shelves:
                for new_shelf_info in new_shelves:
                    if new_shelf_info['name'] == old_shelf_info['name']:
                        new_shelf_info['active'] = old_shelf_info['active']
                        new_shelf_info[KEY_ADD_ACTIONS] = old_shelf_info.get(KEY_ADD_ACTIONS, [])
                        new_shelf_info[KEY_ADD_RATING] = old_shelf_info.get(KEY_ADD_RATING, False)
                        new_shelf_info[KEY_ADD_DATE_READ] = old_shelf_info.get(KEY_ADD_DATE_READ, False)
                        new_shelf_info[KEY_SYNC_ACTIONS] = old_shelf_info.get(KEY_SYNC_ACTIONS, [])
                        new_shelf_info[KEY_SYNC_RATING] = old_shelf_info.get(KEY_SYNC_RATING, False)
                        new_shelf_info[KEY_SYNC_DATE_READ] = old_shelf_info.get(KEY_SYNC_DATE_READ, False)
                        new_shelf_info[KEY_SYNC_REVIEW_TEXT] = old_shelf_info.get(KEY_SYNC_REVIEW_TEXT, False)
                        new_shelf_info[KEY_TAG_MAPPINGS] = old_shelf_info.get(KEY_TAG_MAPPINGS, [])
                        break

            user_info[KEY_SHELVES] = new_shelves
        finally:
            self._shelves_table.populate_table(user_info[KEY_SHELVES])
            self._sync_shelves_button.setEnabled(True)

    def add_shelf(self):
        d = AddShelfDialog(self)
        d.exec_()
        new_shelf_name = d.shelf_name
        if d.result() != d.Accepted or not new_shelf_name:
            # Operation cancelled or user did not actually choose a shelf name
            return
        # Verify the name does not exist already
        user_info = self.users[self.user_name]
        shelves = user_info[KEY_SHELVES]
        if new_shelf_name in shelves:
            return error_dialog(self, _('Duplicate shelf name'),
                _('There is already a shelf named:') +' '+ new_shelf_name, show=True)
        # Perform the update with Goodreads
        if self.grhttp.create_shelf(self.user_name, new_shelf_name, d.is_featured,
                                    d.is_exclusive, d.is_sortable):
            # Update the shelves list
            self.refresh_shelves_list()

    def edit_shortcuts(self):
        self.save_settings()
        # Force the menus to be rebuilt immediately, so we have all our actions registered
        self.plugin_action.rebuild_menus()
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()

    def create_custom_column_controls(self, columns_group_box_layout, custom_col_name, min_width=120):
        current_Location_label = QLabel(CUSTOM_COLUMN_DEFAULTS[custom_col_name]['config_label'], self)
        current_Location_label.setToolTip(CUSTOM_COLUMN_DEFAULTS[custom_col_name]['config_tool_tip'])
        initial_items = CUSTOM_COLUMN_DEFAULTS[custom_col_name].get('initial_items', [])
        create_column_callback=partial(self.create_custom_column, custom_col_name) if self.supports_create_custom_column else None
        avail_columns = self.sync_custom_columns[custom_col_name]['current_columns']()
        custom_column_combo = CustomColumnComboBox(self, avail_columns, initial_items=initial_items, create_column_callback=create_column_callback)
        custom_column_combo.setMinimumWidth(min_width)
        current_Location_label.setBuddy(custom_column_combo)
        columns_group_box_layout.addRow(current_Location_label, custom_column_combo)
        self.sync_custom_columns[custom_col_name]['combo_box'] = custom_column_combo

        return custom_column_combo

    def create_custom_column(self, lookup_name=None):
        display_params = {
            'description': CUSTOM_COLUMN_DEFAULTS[lookup_name]['description']
        }
        datatype = CUSTOM_COLUMN_DEFAULTS[lookup_name]['datatype']
        column_heading  = CUSTOM_COLUMN_DEFAULTS[lookup_name]['column_heading']
        is_multiple = CUSTOM_COLUMN_DEFAULTS[lookup_name].get('is_multiple', False)

        new_lookup_name = lookup_name

        create_new_custom_column_instance = self.get_create_new_custom_column_instance
        result = create_new_custom_column_instance.create_column(new_lookup_name, column_heading, datatype, is_multiple, display=display_params, generate_unused_lookup_name=True, freeze_lookup_name=False)
        if result[0] == CreateNewCustomColumn.Result.COLUMN_ADDED:
            # print(self.get_text_custom_columns())
            # print(self.plugin_action.gui.current_db.field_metadata.custom_field_metadata())
            self.sync_custom_columns[lookup_name]['combo_box'].populate_combo(
                                self.sync_custom_columns[lookup_name]['current_columns'](), 
                                result[1],
                                initial_items=CUSTOM_COLUMN_DEFAULTS[lookup_name]['initial_items']
                                )
            self.must_restart = True
            return True
        
        return False

    @property
    def get_create_new_custom_column_instance(self):
        if self._get_create_new_custom_column_instance is None and self.supports_create_custom_column:
            self._get_create_new_custom_column_instance = CreateNewCustomColumn(self.plugin_action.gui)
        return self._get_create_new_custom_column_instance


# Ensure our config gets migrated
migrate_config_if_required()