from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

import copy, traceback
import six
from six import text_type as unicode

try:
    from qt.core import (QWidget, QVBoxLayout, QLabel, QLineEdit, Qt, QUrl,
                        QGroupBox, QComboBox, QHBoxLayout, QIcon,
                        QInputDialog, QGridLayout, QPushButton,
                        QCheckBox, QTableWidget, QAbstractItemView, QSize,
                        QScrollArea, QTabWidget, QToolButton, QSpacerItem)
except ImportError:
    from PyQt5.Qt import (QWidget, QVBoxLayout, QLabel, QLineEdit, Qt, QUrl,
                        QGroupBox, QComboBox, QHBoxLayout, QIcon,
                        QInputDialog, QGridLayout, QPushButton,
                        QCheckBox, QTableWidget, QAbstractItemView, QSize,
                        QScrollArea, QTabWidget, QToolButton, QSpacerItem)

from calibre.gui2 import error_dialog, dynamic, info_dialog, question_dialog, open_url
from calibre.gui2.complete2 import EditWithComplete
from calibre.gui2.dialogs.confirm_delete import confirm
from calibre.utils.config import JSONConfig
from calibre.utils.icu import sort_key

from calibre_plugins.reading_list.common_icons import get_icon
from calibre_plugins.reading_list.common_dialogs import KeyboardConfigDialog, PrefsViewerDialog
from calibre_plugins.reading_list.common_widgets import (CheckableTableWidgetItem, 
                        ReadOnlyTableWidgetItem, ReadOnlyTextIconWidgetItem,
                        CustomColumnComboBox, NoWheelComboBox)

# Per library settings are persisted in the calibre library database.
# Devices and other option settings are stored in the JSON file

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/Reading-List'

PREFS_NAMESPACE = 'ReadingListPlugin'

PREFS_KEY_SETTINGS = 'settings'
# 'settings': { 'default':'DefaultListName',
#               'lists': { 'name': {'content':[],
#                          'tagsColumn':'tags', 'tagsText: '',
#                          'seriesColumn':'#foo', 'seriesName: '',
#                          'syncDevice':'xxx_uuid',
#                          'syncAuto':False, 'syncClear':False,
#                          'shortcutAdd': '',
#                          'listType': 'xxx',
#                          'populateType': 'xxx',
#                          'populateSearch': 'xxx',
#                        }, ...
KEY_LISTS = 'lists'
KEY_DEFAULT_LIST = 'default'
KEY_QUICK_ACCESS = 'quickAccess'
KEY_QUICK_ACCESS_LIST = 'quickAccessList'
KEY_CONTENT = 'content'
KEY_MODIFY_ACTION = 'modifyAction'
KEY_TAGS_COLUMN = 'tagsColumn'
KEY_TAGS_TEXT = 'tagsText'
KEY_SERIES_COLUMN = 'seriesColumn'
KEY_SERIES_NAME = 'seriesName'
KEY_SYNC_DEVICE = 'syncDevice'
KEY_SYNC_AUTO = 'syncAuto'
KEY_SYNC_CLEAR = 'syncClear'
KEY_LIST_TYPE = 'listType'
KEY_POPULATE_TYPE = 'populateType'
KEY_POPULATE_SEARCH = 'populateSearch'
KEY_SORT_LIST = 'sortList'
KEY_RESTORE_SORT = 'restoreSort'
KEY_DISPLAY_TOP_MENU = 'displayTopMenu'

TOKEN_ANY_DEVICE = _('*Any Device')

POPULATE_TYPES = [('POPMANUAL', _('Manually add/remove items')),
                  ('POPDEVICE', _('Auto populated from books on device')),
                  ('POPSEARCH', _('Auto populated from search'))]

SYNC_TYPES = [('SYNCNEW',    _('Add new list items to device')),
              ('SYNCALL',    _('Add/overwrite all list items to device')),
              ('SYNCREM',    _('Remove list items from device')),
              ('SYNCREPNEW', _('Replace device with list, add new items only')),
              ('SYNCREPOVR', _('Replace device with list, add/overwrite all'))]

SYNC_AUTO_DESC = _('Auto populate list from books on device')

MODIFY_TYPES = [('TAGNONE',      _('Do not update calibre column')),
                ('TAGADDREMOVE', _('Update column for add or remove')),
                ('TAGADD',       _('Update column for add to list only')),
                ('TAGREMOVE',    _('Update column for remove from list only'))]

KEY_SCHEMA_VERSION = STORE_SCHEMA_VERSION = 'SchemaVersion'
DEFAULT_SCHEMA_VERSION = 1.65

STORE_OPTIONS = 'Options'
KEY_REMOVE_DIALOG = 'removeDialog'

STORE_DEVICES = 'Devices'
# Devices store consists of:
# 'Devices': { 'dev_uuid': {'type':'xxx', 'uuid':'xxx', 'name:'xxx', 'location_code':'main',
#                           'active':True, 'collections':False} ,
# For iTunes
#              'iTunes':   {'type':'iTunes', 'uuid':iTunes', 'name':'iTunes', 'location_code':'',
#                           'active':True, 'collections':False}, ...}
DEFAULT_DEVICES_VALUES = {}

DEFAULT_LIST_VALUES = {
                        KEY_CONTENT: [],
                        KEY_MODIFY_ACTION: 'TAGADDREMOVE',
                        KEY_TAGS_COLUMN: '',
                        KEY_TAGS_TEXT: '',
                        KEY_SERIES_COLUMN: '',
                        KEY_SERIES_NAME: '',
                        KEY_SYNC_DEVICE: None,
                        KEY_SYNC_AUTO: False,
                        KEY_SYNC_CLEAR: True,
                        KEY_LIST_TYPE: 'SYNCNEW',
                        KEY_POPULATE_TYPE: 'POPMANUAL',
                        KEY_POPULATE_SEARCH: '',
                        KEY_SORT_LIST: True,
                        KEY_RESTORE_SORT: False,
                        KEY_DISPLAY_TOP_MENU: False
                      }

DEFAULT_LIBRARY_VALUES = {
                          KEY_DEFAULT_LIST: 'Default',
                          KEY_QUICK_ACCESS_LIST: 'Default',
                          KEY_LISTS: { 'Default': DEFAULT_LIST_VALUES },
                          KEY_SCHEMA_VERSION: DEFAULT_SCHEMA_VERSION
                         }

DEFAULT_LIST_OPTIONS = { 
                        KEY_REMOVE_DIALOG: True,
                        KEY_QUICK_ACCESS: False,
                       }

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Reading List')

# Set defaults
plugin_prefs.defaults[STORE_DEVICES] = DEFAULT_DEVICES_VALUES
plugin_prefs.defaults[STORE_OPTIONS] = DEFAULT_LIST_OPTIONS


def migrate_json_config_if_required():
    # Contains code for migrating versions of JSON schema
    # Make sure we update our schema version in the file
    schema_version = plugin_prefs.get(STORE_SCHEMA_VERSION, 0)
    if schema_version != DEFAULT_SCHEMA_VERSION:
        plugin_prefs[STORE_SCHEMA_VERSION] = DEFAULT_SCHEMA_VERSION

    if schema_version < 1.5:
        # Cleanup some leftovers from an earlier release which changed Options to OPTIONS
        if 'OPTIONS' in plugin_prefs:
            options = plugin_prefs['OPTIONS']
            del plugin_prefs['OPTIONS']
            plugin_prefs[STORE_OPTIONS] = options


def migrate_library_config_if_required(db, library_config):
    schema_version = library_config.get(KEY_SCHEMA_VERSION, 0)
    if schema_version == DEFAULT_SCHEMA_VERSION:
        return
    # We have changes to be made - mark schema as updated
    library_config[KEY_SCHEMA_VERSION] = DEFAULT_SCHEMA_VERSION

    if schema_version < 1.6:
        # Change to the new populate type
        lists = library_config[KEY_LISTS]
        for list_info in six.itervalues(lists):
            if list_info.get(KEY_LIST_TYPE, 'SYNCNEW') == 'SYNCAUTO':
                list_info[KEY_POPULATE_TYPE] = 'POPDEVICE'
            else:
                list_info[KEY_POPULATE_TYPE] = 'POPMANUAL'
            list_info[KEY_POPULATE_SEARCH] = ''
        library_config[KEY_LISTS] = lists

    if schema_version < 1.61:
        # Remove POPCOLUMN list type and replace it with POPSEARCH
        lists = library_config[KEY_LISTS]
        for list_info in six.itervalues(lists):
            list_info[KEY_POPULATE_SEARCH] = ''
            if list_info.get(KEY_POPULATE_TYPE, 'POPMANUAL') == 'POPCOLUMN':
                list_info[KEY_POPULATE_TYPE] = 'POPSEARCH'
                if 'populateColumn' in list_info:
                    col = list_info['populateColumn']
                    val = list_info['populateValue']
                    del list_info['populateColumn']
                    del list_info['populateValue']
                    list[KEY_SYNC_CLEAR] = False
                    # Going to make a supremely crude attempt to migrate existing user lists
                    if val == 'Y':
                        list_info[KEY_POPULATE_SEARCH] = col+':true'
                    elif val == 'N':
                        list_info[KEY_POPULATE_SEARCH] = col+':false'
                    else:
                        list_info[KEY_POPULATE_SEARCH] = col+':"='+val+'"'
        library_config[KEY_LISTS] = lists

    if schema_version < 1.62:
        # Insure all pre-existing POPDEVICE lists have modify option
        # set to TAGADDREMOVE so past behavior doesn't change.
        lists = library_config[KEY_LISTS]
        for list_info in six.itervalues(lists):
            if list_info.get(KEY_POPULATE_TYPE, 'POPMANUAL') == 'POPDEVICE':
                list_info[KEY_MODIFY_ACTION] = 'TAGADDREMOVE'
        library_config[KEY_LISTS] = lists

    if schema_version < 1.63:
        # Ensure all lists have a sort property when viewing set to true to keep legacy behaviour.
        # Ensure any auto populated lists are not displayed on the top level menu to keep legacy behaviour.
        lists = library_config[KEY_LISTS]
        for list_info in six.itervalues(lists):
            list_info[KEY_SORT_LIST] = True
            list_info[KEY_DISPLAY_TOP_MENU] = False
        library_config[KEY_LISTS] = lists

    if schema_version < 1.65:
        # Ensure all lists have a restore sort property.
        lists = library_config[KEY_LISTS]
        for list_info in six.itervalues(lists):
            list_info[KEY_RESTORE_SORT] = False

    set_library_config(db, library_config)

def show_help():
    open_url(QUrl(HELP_URL))


def get_library_config(db):
    library_id = db.library_id
    library_config = None
    # Check whether this is a reading list needing to be migrated from json into database
    if 'Libraries' in plugin_prefs:
        libraries = plugin_prefs['Libraries']
        if library_id in libraries:
            # We will migrate this below
            library_config = libraries[library_id]
            # Cleanup from json file so we don't ever do this again
            del libraries[library_id]
            if len(libraries) == 0:
                # We have migrated the last library for this user
                del plugin_prefs['Libraries']
            else:
                plugin_prefs['Libraries'] = libraries

    if library_config is None:
        library_config = db.prefs.get_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS,
                                                 copy.deepcopy(DEFAULT_LIBRARY_VALUES))
    if len(library_config[KEY_LISTS]) < 1:
        # no lists, assume broken and get a new copy.
        library_config = copy.deepcopy(DEFAULT_LIBRARY_VALUES)
    migrate_library_config_if_required(db, library_config)

    ## A user some how got to a state where the default list was
    ## deleted, but still set.  Not actually *saved* until user saves
    ## config
    if library_config[KEY_DEFAULT_LIST] not in library_config[KEY_LISTS]:
        ## set to first list
        lists = sorted(library_config[KEY_LISTS].keys())
        library_config[KEY_DEFAULT_LIST] = lists[0]
    return library_config

def set_library_config(db, library_config):
    db.prefs.set_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS, library_config)

def get_list_info(db, list_name):
    library_config = get_library_config(db)
    lists = library_config[KEY_LISTS]
    list_map = lists.get(list_name, DEFAULT_LIST_VALUES)
    return list_map

def get_book_list(db, list_name):
    list_map = get_list_info(db, list_name)
    book_ids = list_map[KEY_CONTENT]
    valid_book_ids = [book_id for book_id in book_ids if db.data.has_id(book_id)]
    if len(book_ids) != len(valid_book_ids):
        set_book_list(db, list_name, valid_book_ids)
    return valid_book_ids

def set_book_list(db, list_name, book_ids):
    library_config = get_library_config(db)
    lists = library_config[KEY_LISTS]
    lists[list_name][KEY_CONTENT] = book_ids
    set_library_config(db, library_config)

def set_default_list(db, list_name):
    library_config = get_library_config(db)
    library_config[KEY_DEFAULT_LIST] = list_name
    set_library_config(db, library_config)

def get_book_lists_for_device(db, device_uuid, exclude_auto=True):
    library_config = get_library_config(db)
    lists_map = library_config[KEY_LISTS]
    device_lists = {}
    for list_name, list_info in six.iteritems(lists_map):
        if list_info[KEY_SYNC_DEVICE] in [device_uuid, TOKEN_ANY_DEVICE]:
            if not exclude_auto:
                device_lists[list_name] = list_info
            elif list_info.get(KEY_POPULATE_TYPE, DEFAULT_LIST_VALUES[KEY_POPULATE_TYPE]) == 'POPMANUAL':
                device_lists[list_name] = list_info
    return device_lists

def get_list_names(db, exclude_auto=True):
    library_config = get_library_config(db)
    lists = library_config[KEY_LISTS]
    if not exclude_auto:
        return sorted(lists.keys())

    list_names = []
    for list_name, list_info in six.iteritems(lists):
        if list_info.get(KEY_POPULATE_TYPE, DEFAULT_LIST_VALUES[KEY_POPULATE_TYPE]) == 'POPMANUAL':
            list_names.append(list_name)
    return sorted(list_names)

def get_view_topmenu_list_names(db):
    library_config = get_library_config(db)
    lists = library_config[KEY_LISTS]
    default_list_name = library_config[KEY_DEFAULT_LIST]

    list_names = []
    for list_name, list_info in six.iteritems(lists):
        if (list_info.get(KEY_DISPLAY_TOP_MENU, DEFAULT_LIST_VALUES[KEY_DISPLAY_TOP_MENU]) and list_name != default_list_name):
            list_names.append(list_name)
    return sorted(list_names)

def create_list(db, list_name, book_ids):
    new_list = copy.deepcopy(DEFAULT_LIST_VALUES)
    new_list[KEY_CONTENT] = list(book_ids)
    library_config = get_library_config(db)
    lists = library_config[KEY_LISTS]
    lists[list_name] = new_list
    set_library_config(db, library_config)


class ListComboBox(QComboBox):

    def __init__(self, parent, lists, selected_text=None):
        QComboBox.__init__(self, parent)
        self.populate_combo(lists, selected_text)

    def populate_combo(self, lists, selected_text=None):
        self.blockSignals(True)
        self.clear()
        for list_name in sorted(lists.keys()):
            self.addItem(list_name)
        self.blockSignals(False)
        self.select_view(selected_text)

    def select_view(self, selected_text):
        self.blockSignals(True)
        if selected_text:
            idx = self.findText(selected_text)
            self.setCurrentIndex(idx)
        elif self.count() > 0:
            self.setCurrentIndex(0)
        self.blockSignals(False)


class ListTypeComboBox(QComboBox):

    def __init__(self, parent, listKeyValues):
        QComboBox.__init__(self, parent)
        self.listKeyValues = listKeyValues

    def populate_combo(self, selected_type):
        self.blockSignals(True)
        self.clear()
        idx = 0
        selected_idx = 0
        for key, desc in self.listKeyValues:
            self.addItem(desc)
            self.setItemData(idx, key)
            if key == selected_type:
                selected_idx = idx
            idx += 1
        self.blockSignals(False)
        self.setCurrentIndex(selected_idx)

    def get_selected_type(self):
        return unicode(self.itemData(self.currentIndex()))


class DeviceColumnComboBox(QComboBox):

    def __init__(self, parent):
        QComboBox.__init__(self, parent)

    def populate_combo(self, devices, selected_device_uuid):
        self.clear()
        self.device_ids = [None, TOKEN_ANY_DEVICE]
        self.addItem('')
        self.addItem(TOKEN_ANY_DEVICE)
        selected_idx = 0
        if selected_device_uuid == TOKEN_ANY_DEVICE:
            selected_idx = 1
        for idx, key in enumerate(devices.keys()):
            self.addItem('%s (%s)'%(devices[key]['name'], devices[key]['location_code']))
            self.device_ids.append(key)
            if key == selected_device_uuid:
                selected_idx = idx + 2
        self.setCurrentIndex(selected_idx)

    def get_selected_device(self):
        return self.device_ids[self.currentIndex()]


class BoolColumnComboBox(NoWheelComboBox):

    def __init__(self, parent, selected=True):
        NoWheelComboBox.__init__(self, parent)
        self.populate_combo(selected)

    def populate_combo(self, selected):
        self.clear()
        self.addItem(QIcon(I('ok.png')), 'Y')
        self.addItem(QIcon(I('list_remove.png')), 'N')
        if selected:
            self.setCurrentIndex(0)
        else:
            self.setCurrentIndex(1)


class DevicesTableWidget(QTableWidget):

    def __init__(self, parent):
        QTableWidget.__init__(self, parent)
        self.setSortingEnabled(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setMinimumSize(380, 0)

    def populate_table(self, devices, connected_device_info):
        self.clear()
        self.setRowCount(len(devices))
        header_labels = [_('Menu'), _('Name'), _('Location'), _('Status'), _('Kindle Collections')]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(32)
        self.horizontalHeader().setStretchLastSection(False)
        self.setIconSize(QSize(32, 32))

        for row, uuid in enumerate(devices.keys()):
            self.populate_table_row(row, uuid, devices[uuid], connected_device_info)

        self.resizeColumnsToContents()
        self.setMinimumColumnWidth(1, 100)

    def setMinimumColumnWidth(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def populate_table_row(self, row, uuid, device_config, connected_device_info):
        device_type = device_config['type']
        device_uuid = device_config['uuid']
        if device_type == 'Folder Device':
            device_icon = 'devices/folder.png'
        elif 'iTunes' in device_type:
            device_icon = 'devices/itunes.png'
        else:
            device_icon = 'reader.png'
        is_connected = False
        if connected_device_info is not None:
            drive_info = connected_device_info[4]
            if not drive_info:
                is_connected = True
            else:
                for connected_info in drive_info.values():
                    if connected_info['device_store_uuid'] == device_uuid:
                        is_connected = True
                        break
        connected_icon = 'images/device_connected.png' if is_connected else None

        name_widget = ReadOnlyTextIconWidgetItem(device_config['name'], get_icon(device_icon))
        name_widget.setData(Qt.UserRole, (device_config, is_connected))
        self.setItem(row, 0, CheckableTableWidgetItem(device_config['active']))
        self.setItem(row, 1, name_widget)
        self.setItem(row, 2, ReadOnlyTableWidgetItem(device_config['location_code']))
        self.setItem(row, 3, ReadOnlyTextIconWidgetItem('', get_icon(connected_icon)))
        is_kindle = device_type == 'Amazon Kindle'
        if is_kindle:
            self.setCellWidget(row, 4, BoolColumnComboBox(self, device_config.get('collections', False)))

    def get_data(self):
        devices = {}
        for row in range(self.rowCount()):
            (device_config, _is_connected) = self.item(row, 1).data(Qt.UserRole)
            device_config['active'] = self.item(row, 0).get_boolean_value()
            w = self.cellWidget(row, 4)
            if w:
                device_config['collections'] = unicode(w.currentText()).strip() == 'Y'
            else:
                device_config['collections'] = False
            devices[device_config['uuid']] = device_config
        return devices

    def get_selected_device_info(self):
        if self.currentRow() >= 0:
            (device_config, is_connected) = self.item(self.currentRow(), 1).data(Qt.UserRole)
            return (device_config, is_connected)
        return None, None

    def set_current_row_device_name(self, device_name):
        if self.currentRow() >= 0:
            widget = self.item(self.currentRow(), 1)
            (device_config, is_connected) = widget.data(Qt.UserRole)
            device_config['name'] = device_name
            widget.setData(Qt.UserRole, (device_config, is_connected))
            widget.setText(device_name)

    def delete_selected_row(self):
        if self.currentRow() >= 0:
            self.removeRow(self.currentRow())


class ListsTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        QWidget.__init__(self)

        self.plugin_action = plugin_action
        self.gui = plugin_action.gui
        self.library_config = get_library_config(self.gui.current_db)
        self.lists = self.library_config[KEY_LISTS]
        self.default_list = self.library_config[KEY_DEFAULT_LIST]
        self.populate_custom_columns = self._get_custom_columns(['text','bool','enumeration'])
        self.tags_custom_columns = self._get_custom_columns(['text','bool','enumeration'])
        self.series_custom_columns = self._get_custom_columns(['series'])

        self.all_tags = self.gui.current_db.all_tags()
        self.list_name = None

        layout = QVBoxLayout()
        self.setLayout(layout)

        # -------- Lists configuration ---------
        select_list_layout = QHBoxLayout()
        layout.addLayout(select_list_layout)
        lists_label = QLabel(_('Lists:'), self)
        select_list_layout.addWidget(lists_label)
        self.select_list_combo = ListComboBox(self, self.lists, self.default_list)
        self.select_list_combo.setMinimumSize(150, 20)
        self.select_list_combo.currentIndexChanged.connect(self._select_list_combo_changed)
        select_list_layout.addWidget(self.select_list_combo)
        self.add_list_button = QToolButton(self)
        self.add_list_button.setToolTip(_('Add list'))
        self.add_list_button.setIcon(QIcon(I('plus.png')))
        self.add_list_button.clicked.connect(self.add_list)
        select_list_layout.addWidget(self.add_list_button)
        self.delete_list_button = QToolButton(self)
        self.delete_list_button.setToolTip(_('Delete list'))
        self.delete_list_button.setIcon(QIcon(I('minus.png')))
        self.delete_list_button.clicked.connect(self.delete_list)
        select_list_layout.addWidget(self.delete_list_button)
        self.rename_list_button = QToolButton(self)
        self.rename_list_button.setToolTip(_('Rename list'))
        self.rename_list_button.setIcon(QIcon(I('edit-undo.png')))
        self.rename_list_button.clicked.connect(self.rename_list)
        select_list_layout.addWidget(self.rename_list_button)
        select_list_layout.insertStretch(-1)

        # -------- Population Options configuration ---------
        layout.addSpacing(5)
        populate_group_box = QGroupBox(_('Population Options:'), self)
        layout.addWidget(populate_group_box)
        populate_group_box_layout = QVBoxLayout()
        populate_group_box.setLayout(populate_group_box_layout)

        populate_grid_layout = QGridLayout()
        populate_group_box_layout.addLayout(populate_grid_layout)

        populate_type_label = QLabel(_('&List type:'), self)
        populate_type_label.setToolTip(_('Choose how this list will be populated'))
        self.populate_type_combo = ListTypeComboBox(self, POPULATE_TYPES)
        self.populate_type_combo.currentIndexChanged.connect(self._populate_type_combo_changed)
        populate_type_label.setBuddy(self.populate_type_combo)
        populate_grid_layout.addWidget(populate_type_label, 0, 0, 1, 1)
        populate_grid_layout.addWidget(self.populate_type_combo, 0, 1, 1, 1)

        self.populate_search_label = QLabel(_('&Auto populate from search:'), self)
        self.populate_search_label.setToolTip(_('If list is populated from a search, specify the calibre search expression'))
        self.populate_search_ledit = QLineEdit(self)
        self.populate_search_label.setBuddy(self.populate_search_ledit)
        populate_grid_layout.addWidget(self.populate_search_label, 1, 0, 1, 1)
        populate_grid_layout.addWidget(self.populate_search_ledit, 1, 1, 1, 1)

        # -------- Sync Options configuration ---------
        layout.addSpacing(5)
        sync_lists_group_box = QGroupBox(_('Sync Options:'), self)
        layout.addWidget(sync_lists_group_box)
        sync_lists_group_box_layout = QVBoxLayout()
        sync_lists_group_box.setLayout(sync_lists_group_box_layout)

        sync_lists_grid_layout = QGridLayout()
        sync_lists_group_box_layout.addLayout(sync_lists_grid_layout)

        device_label = QLabel(_('&Device to sync this list to:'), self)
        device_label.setToolTip(_('By specifying a device you can sync either manually or\n'
                                'automatically the contents of a list to that device.\n'
                                'This replaces the Book Sync plugin functionality'))
        self.device_combo = DeviceColumnComboBox(self)
        device_label.setBuddy(self.device_combo)
        sync_lists_grid_layout.addWidget(device_label, 0, 0, 1, 1)
        sync_lists_grid_layout.addWidget(self.device_combo, 0, 1, 1, 1)

        sync_type_label = QLabel(_('&When syncing this list:'), self)
        sync_type_label.setToolTip(_('Control how your items are synced to the device.\n'
                                'Sync only new items, sync all items overwriting existing\n'
                                'or use this list to just remove items from your device.'))
        self.sync_type_combo = ListTypeComboBox(self, SYNC_TYPES)
        sync_type_label.setBuddy(self.sync_type_combo)
        sync_lists_grid_layout.addWidget(sync_type_label, 1, 0, 1, 1)
        sync_lists_grid_layout.addWidget(self.sync_type_combo, 1, 1, 1, 1)

        self.sync_auto_checkbox = QCheckBox(_('Sync to this device as soon as it is connected'), self)
        self.sync_auto_checkbox.setToolTip(_('Uncheck this option if you prefer to manually sync to your device.\n'
                                           'If no device is specified this checkbox has no effect'))
        sync_lists_grid_layout.addWidget(self.sync_auto_checkbox, 2, 0, 1, 2)

        self.sync_clear_checkbox = QCheckBox(_('Clear this list after a sync to this device'), self)
        self.sync_clear_checkbox.setToolTip(_('If unchecked, only items not on the device already will be synced.\n'
                                            'If no device is specified this checkbox has no effect.\n'
                                            'This option can only be used with manual type lists.'))
        self.sync_clear_checkbox.stateChanged.connect(self._enable_series_settings)
        sync_lists_grid_layout.addWidget(self.sync_clear_checkbox, 3, 0, 1, 2)

        # -------- Column Update Options configuration ---------
        layout.addSpacing(5)
        col_update_group_box = QGroupBox(_('Column Update Options:'), self)
        layout.addWidget(col_update_group_box)
        col_update_group_box_layout = QVBoxLayout()
        col_update_group_box.setLayout(col_update_group_box_layout)

        col_update_grid_layout = QGridLayout()
        col_update_group_box_layout.addLayout(col_update_grid_layout)

        self.modify_type_label = QLabel(_('When &changing this list:'), self)
        self.modify_type_label.setToolTip(_('Optionally modify tags or a custom column when you\n'
                                'add and/or remove items from this list.'))
        self.modify_type_combo = ListTypeComboBox(self, MODIFY_TYPES)
        self.modify_type_label.setBuddy(self.modify_type_combo)
        col_update_grid_layout.addWidget(self.modify_type_label, 0, 0, 1, 1)
        col_update_grid_layout.addWidget(self.modify_type_combo, 0, 1, 1, 1)

        self.tags_column_label = QLabel(_('&Column to update:'), self)
        self.tags_column_label.setToolTip(_('Optionally specify a column to add/remove a value from\n'
                                     'when adding or removing items from this list'))
        self.tags_column_combo = CustomColumnComboBox(self)
        self.tags_column_combo.currentIndexChanged.connect(self._tags_column_combo_changed)
        self.tags_column_label.setBuddy(self.tags_column_combo)
        col_update_grid_layout.addWidget(self.tags_column_label, 1, 0, 1, 1)
        col_update_grid_layout.addWidget(self.tags_column_combo, 1, 1, 1, 1)

        self.tags_value_label = QLabel(_('&Value in column to add/remove:'), self)
        self.tags_value_label.setToolTip(_('Specify the tag or custom column value to be added when adding\n'
                              'to this list or removed when the book is taken off the list'))
        self.tags_value_ledit = EditWithComplete(self)
        self.tags_value_ledit.set_add_separator(False)
        self.tags_value_label.setBuddy(self.tags_value_ledit)
        col_update_grid_layout.addWidget(self.tags_value_label, 2, 0, 1, 1)
        col_update_grid_layout.addWidget(self.tags_value_ledit, 2, 1, 1, 1)

        # -------- Reading Series Column configuration ---------
        layout.addSpacing(5)
        series_col_group_box = QGroupBox(_('Reading Order Options:'), self)
        layout.addWidget(series_col_group_box)
        series_col_group_box_layout = QVBoxLayout()
        series_col_group_box.setLayout(series_col_group_box_layout)

        series_col_grid_layout = QGridLayout()
        series_col_group_box_layout.addLayout(series_col_grid_layout)

        self.series_column_label = QLabel(_('&Store in series column:'), self)
        self.series_column_label.setToolTip(_('You can optionally display the current reading list order\n'
                                'in a custom series column. You should not edit this column directly!\n'
                                'Only usable with Manually managed lists that are not Cleared on Sync.'))
        self.series_column_combo = CustomColumnComboBox(self)
        self.series_column_label.setBuddy(self.series_column_combo)
        series_col_grid_layout.addWidget(self.series_column_label, 0, 0, 1, 1)
        series_col_grid_layout.addWidget(self.series_column_combo, 0, 1, 1, 1)

        self.series_name_label = QLabel(_('&Series name:'), self)
        self.series_name_label.setToolTip(_('Specify the name for this reading order series\n'
                                     'If left blank, will use the name of the list this book is on.'))
        self.series_name_edit = QLineEdit(self)
        self.series_name_label.setBuddy(self.series_name_edit)
        series_col_grid_layout.addWidget(self.series_name_label, 1, 0, 1, 1)
        series_col_grid_layout.addWidget(self.series_name_edit, 1, 1, 1, 1)

        # -------- Display Options configuration ---------
        layout.addSpacing(5)
        display_opt_group_box = QGroupBox(_('Display Options:'), self)
        layout.addWidget(display_opt_group_box)
        display_opt_group_box_layout = QVBoxLayout()
        display_opt_group_box.setLayout(display_opt_group_box_layout)

        display_opt_grid_layout = QGridLayout()
        display_opt_group_box_layout.addLayout(display_opt_grid_layout)

        self.display_top_menu_checkbox = QCheckBox(_('Move "View list" to the top level of the plugin menu for this list'), self)
        self.display_top_menu_checkbox.setToolTip(_('By default Reading List creates a View List submenu for all your lists when you have multiple.\n'
                                            'If checked, this list will be moved to the top level menu for ease of access.\n'
                                            'NOTE: Your "default" list will always appear on the top menu, regardless of this checkbox'))
        display_opt_grid_layout.addWidget(self.display_top_menu_checkbox, 0, 0, 1, 1)

        self.sort_list_checkbox = QCheckBox(_('Apply reading list order when viewing list'), self)
        self.sort_list_checkbox.setToolTip(_('If checked, viewing a reading list will also change your Calibre sort order.\n'
                                           'Lists can be manually reordered using this plugin, defaulting to order added to list.\n'
                                            'If unchecked, current calibre sort will be left unchanged when you view the list.'))
        self.sort_list_checkbox.stateChanged.connect(self._sort_list_checkbox_state_changed)
        display_opt_grid_layout.addWidget(self.sort_list_checkbox, 1, 0, 1, 1)

        self.restore_sort_checkbox = QCheckBox(_('Restore sort after viewing list'), self)
        self.restore_sort_checkbox.setToolTip(_("If checked, calibre sort will be restored to its original state after\n"
                                                "the user quits the reading list view by changing or clearing calibre's\n"
                                                "search, switching libraries, or quitting calibre."))
        horz = QHBoxLayout()
        horz.addItem(QSpacerItem(20, 1))
        vertright = QVBoxLayout()
        horz.addLayout(vertright)
        vertright.addWidget(self.restore_sort_checkbox)
        display_opt_grid_layout.addLayout(horz, 2, 0, 1, 1)

        self._sort_list_checkbox_state_changed(self.sort_list_checkbox.checkState())
        layout.insertStretch(-1)

    def _sort_list_checkbox_state_changed(self, state):
        if self.sort_list_checkbox.isChecked():
            self.restore_sort_checkbox.setEnabled(True)
        else:
            self.restore_sort_checkbox.setCheckState(Qt.Unchecked)
            self.restore_sort_checkbox.setEnabled(False)

    def _select_list_combo_changed(self):
        self.persist_list_config()
        self.refresh_current_list_info()

    def _enable_series_settings(self):
        populate_type = self.populate_type_combo.get_selected_type()
        if populate_type == 'POPMANUAL' and not self.sync_clear_checkbox.isChecked():
            self.series_column_combo.setEnabled(True)
            self.series_name_edit.setEnabled(True)
            self.series_column_label.setEnabled(True)
            self.series_name_label.setEnabled(True)
        else:
            self.series_column_combo.setEnabled(False)
            self.series_column_combo.setCurrentIndex(0)
            self.series_name_edit.setEnabled(False)
            self.series_name_edit.setText('')
            self.series_column_label.setEnabled(False)
            self.series_name_label.setEnabled(False)

    def _populate_type_combo_changed(self):
        populate_type = self.populate_type_combo.get_selected_type()
        if populate_type == 'POPDEVICE':
            self.sync_type_combo.listKeyValues.insert(0, ('SYNCAUTO', SYNC_AUTO_DESC))
            self.sync_type_combo.populate_combo('SYNCAUTO')
            self.sync_type_combo.setEnabled(False)
            self.sync_auto_checkbox.setCheckState(Qt.Checked)
            self.sync_auto_checkbox.setEnabled(False)
            self.sync_clear_checkbox.setCheckState(Qt.Unchecked)
        else:
            self.sync_type_combo.setEnabled(True)
            if self.sync_type_combo.listKeyValues[0][0] == 'SYNCAUTO':
                val = self.sync_type_combo.get_selected_type()
                self.sync_type_combo.listKeyValues.pop(0)
                if val == 'SYNCAUTO':
                    # only reset value if it was 'SYNCAUTO'. This was
                    # getting tripped on the switched-to list.
                    self.sync_type_combo.populate_combo('SYNCNEW')
            self.sync_auto_checkbox.setEnabled(True)

        if populate_type in ['POPSEARCH', 'POPDEVICE']:
            self.sync_clear_checkbox.setEnabled(False)
            self.sync_clear_checkbox.setChecked(False)
        else:
            self.sync_clear_checkbox.setEnabled(True)
        self._enable_series_settings()

        if populate_type == 'POPSEARCH':
            self.populate_search_label.setEnabled(True)
            self.populate_search_ledit.setEnabled(True)
            self.modify_type_combo.populate_combo('TAGNONE')
            self.modify_type_label.setEnabled(False)
            self.modify_type_combo.setEnabled(False)
            self.tags_column_combo.setCurrentIndex(0)
            self.tags_value_ledit.setText('')
            self.tags_column_label.setEnabled(False)
            self.tags_column_combo.setEnabled(False)
            self.tags_value_label.setEnabled(False)
            self.tags_value_ledit.setEnabled(False)
        else:
            self.populate_search_ledit.setText('')
            self.populate_search_label.setEnabled(False)
            self.populate_search_ledit.setEnabled(False)
            self.modify_type_combo.setEnabled(True)
            self.modify_type_label.setEnabled(True)
            self.tags_column_label.setEnabled(True)
            self.tags_column_combo.setEnabled(True)
            self.tags_value_label.setEnabled(True)
            self.tags_value_ledit.setEnabled(True)

    def refresh_current_list_info(self):
        # Get configuration for the selected list
        self.list_name = unicode(self.select_list_combo.currentText()).strip()
        list_map = get_list_info(self.gui.current_db, self.list_name)
        populate_type = list_map.get(KEY_POPULATE_TYPE, DEFAULT_LIST_VALUES[KEY_POPULATE_TYPE])
        populate_search = list_map.get(KEY_POPULATE_SEARCH, DEFAULT_LIST_VALUES[KEY_POPULATE_SEARCH])
        sync_device_uuid = list_map.get(KEY_SYNC_DEVICE, DEFAULT_LIST_VALUES[KEY_SYNC_DEVICE])
        list_type = list_map.get(KEY_LIST_TYPE, DEFAULT_LIST_VALUES[KEY_LIST_TYPE])
        sync_automatically = list_map.get(KEY_SYNC_AUTO, DEFAULT_LIST_VALUES[KEY_SYNC_AUTO])
        clear_after_sync = list_map.get(KEY_SYNC_CLEAR, DEFAULT_LIST_VALUES[KEY_SYNC_CLEAR])
        modify_type = list_map.get(KEY_MODIFY_ACTION, DEFAULT_LIST_VALUES[KEY_MODIFY_ACTION])
        tags_column = list_map.get(KEY_TAGS_COLUMN, DEFAULT_LIST_VALUES[KEY_TAGS_COLUMN])
        tags_text = list_map.get(KEY_TAGS_TEXT, DEFAULT_LIST_VALUES[KEY_TAGS_TEXT])
        series_column = list_map.get(KEY_SERIES_COLUMN, DEFAULT_LIST_VALUES[KEY_SERIES_COLUMN])
        series_name = list_map.get(KEY_SERIES_NAME, DEFAULT_LIST_VALUES[KEY_SERIES_NAME])
        display_top_menu = list_map.get(KEY_DISPLAY_TOP_MENU, DEFAULT_LIST_VALUES[KEY_DISPLAY_TOP_MENU])
        sort_list = list_map.get(KEY_SORT_LIST, DEFAULT_LIST_VALUES[KEY_SORT_LIST])
        restore_sort = list_map.get(KEY_RESTORE_SORT, DEFAULT_LIST_VALUES[KEY_RESTORE_SORT])

        # Display list configuration in the controls
        self.populate_type_combo.populate_combo(populate_type)
        self.sync_type_combo.populate_combo(list_type)
        self.populate_search_ledit.setText(populate_search)
        self.device_combo.populate_combo(self.parent_dialog.get_devices_list(), sync_device_uuid)
        self.sync_auto_checkbox.setCheckState(Qt.Checked if sync_automatically else Qt.Unchecked)
        self.sync_clear_checkbox.setCheckState(Qt.Checked if clear_after_sync else Qt.Unchecked)
        self.tags_column_combo.populate_combo(self.tags_custom_columns, tags_column, ['', 'tags'])
        self._tags_column_combo_changed()
        self.series_column_combo.populate_combo(self.series_custom_columns, series_column, [''])
        self.series_name_edit.setText(series_name)
        self.display_top_menu_checkbox.setCheckState(Qt.Checked if display_top_menu else Qt.Unchecked)
        self.sort_list_checkbox.setCheckState(Qt.Checked if sort_list else Qt.Unchecked)
        self.restore_sort_checkbox.setCheckState(Qt.Checked if restore_sort else Qt.Unchecked)
        self.modify_type_combo.populate_combo(modify_type)
        self.tags_value_ledit.setText(tags_text)
        self._populate_type_combo_changed()

    def persist_list_config(self):
        if not self.list_name:
            return
        # Update all of the current list information in the store
        list_info = self.lists[self.list_name]
        list_info[KEY_POPULATE_TYPE] = self.populate_type_combo.get_selected_type()
        if list_info[KEY_POPULATE_TYPE] == 'POPSEARCH':
            list_info[KEY_POPULATE_SEARCH] = unicode(self.populate_search_ledit.text())
        else:
            list_info[KEY_POPULATE_SEARCH] = ''
        list_info[KEY_SYNC_DEVICE] = self.device_combo.get_selected_device()
        list_info[KEY_LIST_TYPE] = self.sync_type_combo.get_selected_type()
        list_info[KEY_SYNC_AUTO] = self.sync_auto_checkbox.checkState() == Qt.Checked
        list_info[KEY_SYNC_CLEAR] = self.sync_clear_checkbox.checkState() == Qt.Checked
        list_info[KEY_MODIFY_ACTION] = self.modify_type_combo.get_selected_type()
        list_info[KEY_TAGS_COLUMN] = self.tags_column_combo.get_selected_column()
        tags = [t.strip() for t in unicode(self.tags_value_ledit.text()).split(',')]
        list_info[KEY_TAGS_TEXT] = tags[0]
        list_info[KEY_SERIES_COLUMN] = self.series_column_combo.get_selected_column()
        list_info[KEY_SERIES_NAME] = unicode(self.series_name_edit.text())
        list_info[KEY_DISPLAY_TOP_MENU] = self.display_top_menu_checkbox.checkState() == Qt.Checked
        list_info[KEY_SORT_LIST] = self.sort_list_checkbox.checkState() == Qt.Checked
        list_info[KEY_RESTORE_SORT] = self.restore_sort_checkbox.checkState() == Qt.Checked
        self.lists[self.list_name] = list_info

    def _get_custom_columns(self, column_types):
        custom_columns = self.plugin_action.gui.library_view.model().custom_columns
        available_columns = {}
        for key, column in six.iteritems(custom_columns):
            typ = column['datatype']
            if typ in column_types:
                available_columns[key] = column
        return available_columns

    def _tags_column_combo_changed(self):
        selected_column = self.tags_column_combo.get_selected_column()
        self.tags_value_ledit.setText('')
        set_default_value = False
        if selected_column == '':
            values = []
        elif selected_column == 'tags':
            values = self.all_tags
        else:
            # Need to get all the possible values for this custom column
            col = self.tags_custom_columns[selected_column]
            typ = col['datatype']
            if typ == 'enumeration':
                values = col['display']['enum_values']
                set_default_value = True
            elif typ == 'bool':
                values = list(['Y','N'])
                set_default_value = True
            else:
                db = self.plugin_action.gui.current_db
                label = db.field_metadata.key_to_label(selected_column)
                values = list(db.all_custom(label=label))

        values.sort(key=sort_key)
        self.tags_value_ledit.update_items_cache(values)
        if set_default_value:
            self.tags_value_ledit.setText(values[0])

    def add_list(self):
        # Display a prompt allowing user to specify a new list
        new_list_name, ok = QInputDialog.getText(self, _('Add new list'),
                    _('Enter a unique display name for this list:'), text=_('Default'))
        if not ok:
            # Operation cancelled
            return
        new_list_name = unicode(new_list_name).strip()
        # Verify it does not clash with any other lists in the list
        for list_name in self.lists.keys():
            if list_name.lower() == new_list_name.lower():
                return error_dialog(self, _('Add failed'),
                                    _('A list with the same name already exists'),
                                    show=True)

        # As we are about to switch list, persist the current lists details if any
        self.persist_list_config()
        self.list_name = new_list_name
        self.lists[new_list_name] = copy.deepcopy(DEFAULT_LIST_VALUES)
        # Now update the lists combobox
        self.select_list_combo.populate_combo(self.lists, new_list_name)
        self.refresh_current_list_info()

    def rename_list(self):
        if not self.list_name:
            return
        # Display a prompt allowing user to specify a rename list
        old_list_name = self.list_name
        new_list_name, ok = QInputDialog.getText(self, _('Rename list'),
                    _('Enter a new display name for this list:'), text=old_list_name)
        if not ok:
            # Operation cancelled
            return
        new_list_name = unicode(new_list_name).strip()
        if new_list_name == old_list_name:
            return
        # Verify it does not clash with any other lists in the list
        for list_name in self.lists.keys():
            if list_name == old_list_name:
                continue
            if list_name.lower() == new_list_name.lower():
                return error_dialog(self, _('Add failed'),
                                    _('A list with the same name already exists'),
                                    show=True, show_copy_button=False)

        # As we are about to rename list, persist the current lists details if any
        self.persist_list_config()
        self.lists[new_list_name] = self.lists[old_list_name]
        if self.default_list == old_list_name:
            self.default_list = new_list_name
        del self.lists[old_list_name]
        self.list_name = new_list_name
        # Now update the lists combobox
        self.select_list_combo.populate_combo(self.lists, new_list_name)
        self.refresh_current_list_info()

    def delete_list(self):
        if not self.list_name:
            return
        if len(self.lists) == 1:
            return error_dialog(self, _('Cannot delete'),
                                _('You must have at least one list'),
                                show=True, show_copy_button=False)
        if not confirm(_('Do you want to delete the list named \'%s\'')%self.list_name,
                        'reading_list_delete_list', self):
            return
        book_ids = get_book_list(self.gui.current_db, self.list_name)
        self.plugin_action.apply_tags_to_list(self.list_name, book_ids, add=False)
        self.plugin_action.update_series_custom_column(self.list_name, book_ids)
        del self.lists[self.list_name]
        if self.default_list == self.list_name:
            # Set new default first by manual vs auto, then by name
            # order instead of previous random.
            lists = get_list_names(self.gui.current_db, exclude_auto=True) + get_list_names(self.gui.current_db, exclude_auto=False)
            self.default_list = lists[0]
        # Now update the lists combobox
        self.select_list_combo.populate_combo(self.lists)
        self.refresh_current_list_info()


class DevicesTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        QWidget.__init__(self)

        self.plugin_action = plugin_action
        self.gui = plugin_action.gui
        self._connected_device_info = plugin_action.connected_device_info
        self.library_config = get_library_config(self.gui.current_db)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # -------- Device configuration ---------
        devices_group_box = QGroupBox(_('Devices:'), self)
        layout.addWidget(devices_group_box)
        devices_group_box_layout = QVBoxLayout()
        devices_group_box.setLayout(devices_group_box_layout)

        self.devices_table = DevicesTableWidget(self)
        devices_group_box_layout.addWidget(self.devices_table)

        buttons_layout = QHBoxLayout()
        devices_group_box_layout.addLayout(buttons_layout)

        self.add_device_btn = QPushButton(_('Add connected device'), self)
        self.add_device_btn.setToolTip(
                _('If you do not have a device connected currently, either plug one\n'
                'in now or exit the dialog and connect to folder/iTunes first'))
        self.add_device_btn.setIcon(QIcon(I('plus.png')))
        self.add_device_btn.clicked.connect(self._add_device_clicked)
        buttons_layout.addWidget(self.add_device_btn, 1)
        self.rename_device_btn = QToolButton(self)
        self.rename_device_btn.setIcon(get_icon('edit-undo.png'))
        self.rename_device_btn.setToolTip(_('Rename the currently connected device'))
        self.rename_device_btn.clicked.connect(self._rename_device_clicked)
        buttons_layout.addWidget(self.rename_device_btn)
        self.delete_device_btn = QToolButton(self)
        self.delete_device_btn.setIcon(QIcon(I('trash.png')))
        self.delete_device_btn.setToolTip(_('Delete this device from the device list'))
        self.delete_device_btn.clicked.connect(self._delete_device_clicked)
        buttons_layout.addWidget(self.delete_device_btn)

        layout.insertStretch(-1)

    def on_device_connection_changed(self, is_connected):
        if not is_connected:
            self._connected_device_info = None
            self.update_from_connection_status()

    def on_device_metadata_available(self):
        self._connected_device_info = self.gui.device_manager.get_current_device_information().get('info', None)
        self.update_from_connection_status()

    def _add_device_clicked(self):
        devices = self.devices_table.get_data()
        drive_info = self._connected_device_info[4]
        if not drive_info:
            # this is an iTunes type device - use the gui name as the uuid
            new_device = {}
            new_device['type'] = self._connected_device_info[0]
            new_device['active'] = True
            new_device['kindle_col'] = False
            new_device['uuid'] = new_device['type']
            new_device['name'] = new_device['type']
            new_device['location_code'] = ''
            devices[new_device['uuid']] = new_device
        else:
            for location_info in drive_info.values():
                new_device = {}
                new_device['type'] = self._connected_device_info[0]
                new_device['active'] = True
                new_device['kindle_col'] = False
                new_device['uuid'] = location_info['device_store_uuid']
                new_device['name'] = location_info['device_name']
                new_device['location_code'] = location_info['location_code']
                devices[new_device['uuid']] = new_device
        self.devices_table.populate_table(devices, self._connected_device_info)
        self.update_from_connection_status(update_table=False)
        # Ensure the devices combo is refreshed for the current list
        self.parent_dialog.lists_tab.refresh_current_list_info()

    def _rename_device_clicked(self):
        (device_info, is_connected) = self.devices_table.get_selected_device_info()
        if not device_info:
            return error_dialog(self, _('Rename failed'),
                                _('You must select a device first'),
                                show=True, show_copy_button=False)
        if not is_connected:
            return error_dialog(self, _('Rename failed'),
                                _('You can only rename a device that is currently connected'),
                                show=True, show_copy_button=False)

        old_name = device_info['name']
        new_device_name, ok = QInputDialog.getText(self, _('Rename device'),
                    _('Enter a new display name for this device:'), text=old_name)
        if not ok:
            # Operation cancelled
            return
        new_device_name = unicode(new_device_name).strip()
        if new_device_name == old_name:
            return
        try:
            self.gui.device_manager.set_driveinfo_name(device_info['location_code'], new_device_name)
            self.devices_table.set_current_row_device_name(new_device_name)
            # Ensure the devices combo is refreshed for the current list
            self.parent_dialog.lists_tab.refresh_current_list_info()
        except:
            return error_dialog(self, _('Rename failed'),
                                _('An error occured while renaming.'),
                                det_msg=traceback.format_exc(), show=True)

    def _delete_device_clicked(self):
        (device_info, _is_connected) = self.devices_table.get_selected_device_info()
        if not device_info:
            return error_dialog(self, _('Delete failed'),
                                _('You must select a device first'),
                                show=True, show_copy_button=False)
        name = device_info['name']
        if not question_dialog(self, _('Are you sure?'), '<p>'+
                _('You are about to remove the <b>%s</b> device from this list. ')%name +
                _('Are you sure you want to continue?')):
            return
        self.parent_dialog.lists_tab.persist_list_config()
        self.devices_table.delete_selected_row()
        self.update_from_connection_status(update_table=False)

        # Ensure any lists are no longer associated with this device
        # NOTE: As of version 1.5 we can no longer do this since we only know the lists
        #       for the current library, not all libraries. So just reset this library
        #       and put some "self-healing" logic elsewhere to ensure a user loading a
        #       list for a deleted device in another library gets it reset at that point.
        self.parent_dialog.delete_device_from_lists(self.library_config, device_info['uuid'])
        # Ensure the devices combo is refreshed for the current list
        self.parent_dialog.lists_tab.refresh_current_list_info()

    def update_from_connection_status(self, first_time=False, update_table=True):
        if first_time:
            devices = plugin_prefs[STORE_DEVICES]
        else:
            devices = self.devices_table.get_data()

        if self._connected_device_info is None:
            self.add_device_btn.setEnabled(False)
            self.rename_device_btn.setEnabled(False)
        else:
            # Check to see whether we are connected to a device we already know about
            is_new_device = True
            can_rename = False
            drive_info = self._connected_device_info[4]
            if drive_info:
                # This is a non iTunes device that we can check to see if we have the UUID for
                device_uuid = drive_info['main']['device_store_uuid']
                if device_uuid in devices:
                    is_new_device = False
                    can_rename = True
            else:
                # This is a device without drive info like iTunes
                device_type = self._connected_device_info[0]
                if device_type in devices:
                    is_new_device = False
            self.add_device_btn.setEnabled(is_new_device)
            self.rename_device_btn.setEnabled(can_rename)
        if update_table:
            self.devices_table.populate_table(devices, self._connected_device_info)


class OtherTab(QWidget):

    def __init__(self, parent_dialog, plugin_action):
        self.parent_dialog = parent_dialog
        QWidget.__init__(self)
        layout = QVBoxLayout()
        self.setLayout(layout)

        keyboard_shortcuts_button = QPushButton(_('Keyboard shortcuts')+'...', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(parent_dialog.edit_shortcuts)
        layout.addWidget(keyboard_shortcuts_button)

        reset_confirmation_button = QPushButton(_('Reset &confirmation dialogs'), self)
        reset_confirmation_button.setToolTip(_('Reset all show me again dialogs for the Reading List plugin'))
        reset_confirmation_button.clicked.connect(self.reset_dialogs)
        layout.addWidget(reset_confirmation_button)

        view_prefs_button = QPushButton(_('&View library preferences')+'...', self)
        view_prefs_button.setToolTip(_('View data stored in the library database for this plugin'))
        view_prefs_button.clicked.connect(parent_dialog.view_prefs)
        layout.addWidget(view_prefs_button)

        help_button = QPushButton(_('&Help'), self)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(show_help)
        layout.addWidget(help_button)

        # -------- Quick Access configuration ---------
        layout.addSpacing(5)
        quick_group_box = QGroupBox(_('Quick Access Options:'), self)
        layout.addWidget(quick_group_box)
        quick_group_box_layout = QVBoxLayout()
        quick_group_box.setLayout(quick_group_box_layout)
        quick_grid_layout = QGridLayout()
        quick_group_box_layout.addLayout(quick_grid_layout)

        self.quick_access_checkbox = QCheckBox(_('Allow toolbar button click to view list'), self)
        self.quick_access_checkbox.setToolTip(_('By default the toolbar button shows the plugin menu.\n'
                                           'Check this option to instead display a reading list.'))
        quick_grid_layout.addWidget(self.quick_access_checkbox, 0, 0, 1, 2)

        library_config = get_library_config(plugin_action.gui.current_db)
        self.lists = library_config[KEY_LISTS]
        selected_list = library_config.get(KEY_QUICK_ACCESS_LIST, library_config[KEY_DEFAULT_LIST])
        quick_list_name_label = QLabel(_('List to view:'), self)
        self.select_quick_list_combo = ListComboBox(self, self.lists, selected_list)
        quick_grid_layout.addWidget(quick_list_name_label, 1, 0, 1, 1)
        quick_grid_layout.addWidget(self.select_quick_list_combo, 1, 1, 1, 1)
        quick_grid_layout.setColumnStretch(0, 1)
        quick_grid_layout.setColumnStretch(1, 4)

        # -------- Other configuration ---------
        layout.addSpacing(5)
        self.delete_confirmation_checkbox = QCheckBox(_('Show dialog when removing books from device'), self)
        self.delete_confirmation_checkbox.setToolTip(_('If syncing your list means books are removed from your device, then\n'
                                           'a dialog will be displayed allowing you to confirm first.\n'
                                           'Uncheck this option to allow unattended syncing to your device.'))
        layout.addWidget(self.delete_confirmation_checkbox)

        layout.insertStretch(-1)

    def reset_dialogs(self):
        for key in dynamic.keys():
            if key.startswith('reading_list_') and key.endswith('_again') \
                                                  and dynamic[key] is False:
                dynamic[key] = True
        info_dialog(self, _('Done'),
                _('Confirmation dialogs have all been reset'), show=True)


class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area)

        tab_widget = QTabWidget(self)
        self.scroll_area.setWidget(tab_widget)

        self.lists_tab = ListsTab(self, plugin_action)
        self.devices_tab = DevicesTab(self, plugin_action)
        self.other_tab = OtherTab(self, plugin_action)
        tab_widget.addTab(self.lists_tab, _('Lists'))
        tab_widget.addTab(self.devices_tab, _('Devices'))
        tab_widget.addTab(self.other_tab, _('Other'))

        # Force an initial display of list information
        self.devices_tab.update_from_connection_status(first_time=True)
        self.lists_tab.refresh_current_list_info()

        remove_dialog = plugin_prefs[STORE_OPTIONS].get(KEY_REMOVE_DIALOG, True)
        self.other_tab.delete_confirmation_checkbox.setCheckState(Qt.Checked if remove_dialog else Qt.Unchecked)
        quick_access = plugin_prefs[STORE_OPTIONS].get(KEY_QUICK_ACCESS, False)
        self.other_tab.quick_access_checkbox.setCheckState(Qt.Checked if quick_access else Qt.Unchecked)

    def connect_signals(self):
        self.plugin_action.plugin_device_connection_changed.connect(self.devices_tab.on_device_connection_changed)
        self.plugin_action.plugin_device_metadata_available.connect(self.devices_tab.on_device_metadata_available)

    def disconnect_signals(self):
        self.plugin_action.plugin_device_connection_changed.disconnect()
        self.plugin_action.plugin_device_metadata_available.disconnect()

    def refresh_devices_dropdown(self):
        self.lists_tab.refresh_current_list_info()

    def get_devices_list(self):
        return self.devices_tab.devices_table.get_data()

    def delete_device_from_lists(self, library_config, device_uuid):
        for list_info in six.itervalues(library_config[KEY_LISTS]):
            if list_info[KEY_SYNC_DEVICE] == device_uuid:
                list_info[KEY_SYNC_DEVICE] = DEFAULT_LIST_VALUES[KEY_SYNC_DEVICE]
                list_info[KEY_SYNC_AUTO] = DEFAULT_LIST_VALUES[KEY_SYNC_AUTO]
                list_info[KEY_SYNC_CLEAR] = DEFAULT_LIST_VALUES[KEY_SYNC_CLEAR]
        set_library_config(self.plugin_action.gui.current_db, library_config)

    def save_settings(self):
        device_prefs = self.get_devices_list()
        plugin_prefs[STORE_DEVICES] = device_prefs

        # We only need to update the store for the current list, as switching lists
        # will have updated the other lists
        self.lists_tab.persist_list_config()

        library_config = self.lists_tab.library_config
        library_config[KEY_LISTS] = self.lists_tab.lists
        library_config[KEY_DEFAULT_LIST] = self.lists_tab.default_list
        quick_list_name = unicode(self.other_tab.select_quick_list_combo.currentText()).strip()
        library_config[KEY_QUICK_ACCESS_LIST] = quick_list_name
        set_library_config(self.plugin_action.gui.current_db, library_config)

        options = {}
        options[KEY_REMOVE_DIALOG] = self.other_tab.delete_confirmation_checkbox.checkState() == Qt.Checked
        options[KEY_QUICK_ACCESS] = self.other_tab.quick_access_checkbox.checkState() == Qt.Checked
        plugin_prefs[STORE_OPTIONS] = options

        self.plugin_action.set_popup_mode()

    def edit_shortcuts(self):
        self.save_settings()
        # Force the menus to be rebuilt immediately, so we have all our actions registered
        self.plugin_action.rebuild_menus()
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()

    def view_prefs(self):
        d = PrefsViewerDialog(self.plugin_action.gui, PREFS_NAMESPACE)
        d.exec_()

# Ensure our config gets migrated
migrate_json_config_if_required()
