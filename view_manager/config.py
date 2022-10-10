from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake, 2019, Jim Miller'

from six import text_type as unicode
from six.moves import range

import copy, os
from functools import partial
try:
    from qt.core import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                        QGroupBox, QComboBox, QGridLayout, QListWidget,
                        QListWidgetItem, QIcon, QInputDialog, Qt,
                        QAction, QCheckBox, QPushButton, QScrollArea,
                        QAbstractItemView, QToolButton, QUrl)
except ImportError:
    from PyQt5.Qt import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                        QGroupBox, QComboBox, QGridLayout, QListWidget,
                        QListWidgetItem, QIcon, QInputDialog, Qt,
                        QAction, QCheckBox, QPushButton, QScrollArea,
                        QAbstractItemView, QToolButton, QUrl)

# Pull in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.gui2 import error_dialog, question_dialog, open_url
from calibre.utils.config import JSONConfig
from calibre.utils.icu import sort_key

from calibre_plugins.view_manager.common_icons import get_icon
from calibre_plugins.view_manager.common_dialogs import KeyboardConfigDialog, PrefsViewerDialog

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/View-Manager'

PREFS_NAMESPACE = 'ViewManagerPlugin'
PREFS_KEY_SETTINGS = 'settings'

# 'settings': { 'autoApplyView': False,
#               'views': { 'name':
#                             { 'sort': [],
#                               'applySearch': False,
#                               'searchToApply': '',
#                               'applyRestriction': False,
#                               'restrictionToApply': '',
#                               'columns': [ ['col1Name', col1Width], ... ]
#                             }, ...
#                        }
#               'lastView': '',
#               'viewToApply': '*Last View Used'
#             }

KEY_AUTO_APPLY_VIEW = 'autoApplyView'
STORE_LIBRARIES = 'libraries'
KEY_VIEWS = 'views'
KEY_LAST_VIEW = 'lastView'
KEY_VIEW_TO_APPLY = 'viewToApply'

KEY_COLUMNS = 'columns'
KEY_SORT = 'sort'
KEY_APPLY_VIRTLIB = 'applyVirtLib'
KEY_VIRTLIB = 'virtLibToApply'
KEY_APPLY_RESTRICTION = 'applyRestriction'
KEY_RESTRICTION = 'restrictionToApply'
KEY_APPLY_SEARCH = 'applySearch'
KEY_SEARCH = 'searchToApply'
KEY_APPLY_PIN_COLUMNS = 'applyPinColumns'
KEY_PIN_COLUMNS = 'pin_columns'
KEY_PIN_SPLITTER_STATE = 'pin_splitter_state' # splitter position
KEY_JUMP_TO_TOP = 'jump_to_top'

LAST_VIEW_ITEM = '*Last View Used'

DEFAULT_LIBRARY_VALUES = {
                          KEY_VIEWS: {},
                          KEY_LAST_VIEW: '',
                          KEY_AUTO_APPLY_VIEW: False,
                          KEY_VIEW_TO_APPLY: LAST_VIEW_ITEM
                         }

KEY_SCHEMA_VERSION = 'SchemaVersion'
DEFAULT_SCHEMA_VERSION = 1.5

def get_empty_view():
    return { KEY_COLUMNS: [],
             KEY_SORT: [],
             KEY_APPLY_VIRTLIB: False,
             KEY_VIRTLIB: '',
             KEY_APPLY_RESTRICTION: False,
             KEY_RESTRICTION: '',
             KEY_APPLY_SEARCH: False,
             KEY_SEARCH: '',
             KEY_APPLY_PIN_COLUMNS: False,
             KEY_PIN_COLUMNS: [],
             KEY_PIN_SPLITTER_STATE: None,
             KEY_JUMP_TO_TOP: False,
             }

# This is where preferences for this plugin used to be stored prior to 1.3
plugin_prefs = JSONConfig('plugins/View Manager')

def migrate_json_config_if_required():
    # As of version 1.3 we no longer require a local json file as
    # all configuration is stored in the database
    json_path = plugin_prefs.file_path
    if not os.path.exists(json_path):
        return
    # We have to wait for all libraries to have been migrated into
    # the database. Once they have, we can nuke the json file
    if 'libraries' not in plugin_prefs:
        try:
            os.remove(json_path)
        except:
            pass


def migrate_library_config_if_required(db, library_config):
    schema_version = library_config.get(KEY_SCHEMA_VERSION, 0)
    if schema_version == DEFAULT_SCHEMA_VERSION:
        return
    # We have changes to be made - mark schema as updated
    library_config[KEY_SCHEMA_VERSION] = DEFAULT_SCHEMA_VERSION

    # Any migration code in future will exist in here.
    #if schema_version < 1.x:

    set_library_config(db, library_config)

def show_help():
    open_url(QUrl(HELP_URL))

def get_library_config(db):
    library_id = db.library_id
    library_config = None
    # Check whether this is a view needing to be migrated from json into database
    if 'libraries' in plugin_prefs:
        libraries = plugin_prefs['libraries']
        if library_id in libraries:
            # We will migrate this below
            library_config = libraries[library_id]
            # Cleanup from json file so we don't ever do this again
            del libraries[library_id]
            if len(libraries) == 0:
                # We have migrated the last library for this user
                del plugin_prefs['libraries']
            else:
                plugin_prefs['libraries'] = libraries

    if library_config is None:
        library_config = db.prefs.get_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS,
                                                 copy.deepcopy(DEFAULT_LIBRARY_VALUES))
    migrate_library_config_if_required(db, library_config)
    # return a *copy* because add/rename/del_view change the contents
    # which then causes problems because what
    # db.prefs.get_namespaced() returns now disagrees with what's
    # actually saved.
    return copy.deepcopy(library_config)

def set_library_config(db, library_config):
    db.prefs.set_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS, library_config)


class ViewComboBox(QComboBox):

    def __init__(self, parent, views, special=None):
        QComboBox.__init__(self, parent)
        self.special = special
        self.populate_combo(views)

    def populate_combo(self, views, selected_text=None):
        self.blockSignals(True)
        self.clear()
        if self.special:
            self.addItem(self.special)
        for view_name in sorted(views.keys()):
            self.addItem(view_name)
        self.select_view(selected_text)

    def select_view(self, selected_text):
        self.blockSignals(True)
        if selected_text:
            idx = self.findText(selected_text)
            self.setCurrentIndex(idx)
        elif self.count() > 0:
            self.setCurrentIndex(0)
        self.blockSignals(False)


class SearchComboBox(QComboBox):

    def __init__(self, parent, entries={}, empty='(Clear)'):
        QComboBox.__init__(self, parent)
        self.empty=empty
        self.populate_combo(entries)

    def populate_combo(self, entries):
        self.clear()
        self.addItem(self.empty)
        p = sorted(entries, key=sort_key)
        for search_name in p:
            self.addItem(search_name)

    def select_value(self, search):
        if search == '':
            search = self.empty
        if search:
            idx = self.findText(search)
            self.setCurrentIndex(idx)
        elif self.count() > 0:
            self.setCurrentIndex(0)

    def currentText(self):
        t = super(SearchComboBox,self).currentText()
        if t == self.empty:
            t = ''
        return t


class ColumnListWidget(QListWidget):

    def __init__(self, parent, gui):
        QListWidget.__init__(self, parent)
        self.gui = gui
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def populate(self, columns, all_columns):
        self.saved_column_widths = dict(columns)
        self.all_columns_with_widths = all_columns
        self.blockSignals(True)
        self.clear()
        all_columns = [colname for colname, _width in all_columns]
        for colname, _width in columns:
            if colname in all_columns:
                all_columns.remove(colname)
                self.populate_column(colname, is_checked=True)
        if len(all_columns) > 0:
            for colname in all_columns:
                self.populate_column(colname, is_checked=False)
        self.blockSignals(False)

    def populate_column(self, colname, is_checked):
        item = QListWidgetItem(self.gui.library_view.model().headers[colname], self)
        item.setData(Qt.UserRole, colname)
        flags = Qt.ItemIsEnabled|Qt.ItemIsSelectable
        if colname != 'ondevice':
            flags |= Qt.ItemIsUserCheckable
        item.setFlags(flags)
        if colname != 'ondevice':
            item.setCheckState(Qt.Checked if is_checked else Qt.Unchecked)

    def get_data(self):
        cols = []
        for idx in range(self.count()):
            item = self.item(idx)
            data = item.data(Qt.UserRole).strip()
            if item.checkState() == Qt.Checked or data == 'ondevice':
                use_width = -1
                for colname, width in self.all_columns_with_widths:
                    if colname == data:
                        use_width = width
                        break
                ## first look for previously saved width; failing
                ## that, current column size; failing that -1 default.
                cols.append((data, self.saved_column_widths.get(data,use_width)))
        return cols

    def move_column_up(self):
        idx = self.currentRow()
        if idx > 0:
            self.insertItem(idx-1, self.takeItem(idx))
            self.setCurrentRow(idx-1)

    def move_column_down(self):
        idx = self.currentRow()
        if idx < self.count()-1:
            self.insertItem(idx+1, self.takeItem(idx))
            self.setCurrentRow(idx+1)


class SortColumnListWidget(ColumnListWidget):

    def __init__(self, parent, gui):
        ColumnListWidget.__init__(self, parent, gui)
        self.create_context_menu()
        self.itemChanged.connect(self.set_sort_icon)
        self.itemSelectionChanged.connect(self.item_selection_changed)

    def create_context_menu(self):
        self.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.sort_ascending_action = QAction(_('Sort ascending'), self)
        self.sort_ascending_action.setIcon(get_icon('images/sort_asc.png'))
        self.sort_ascending_action.triggered.connect(partial(self.change_sort, 0))
        self.addAction(self.sort_ascending_action)
        self.sort_descending_action = QAction(_('Sort descending'), self)
        self.sort_descending_action.setIcon(get_icon('images/sort_desc.png'))
        self.sort_descending_action.triggered.connect(partial(self.change_sort, 1))
        self.addAction(self.sort_descending_action)

    def populate(self, columns, all_columns):
        self.blockSignals(True)
        all_columns = [colname for colname, _width in all_columns]
        self.clear()
        for col, asc in columns:
            if col in all_columns:
                all_columns.remove(col)
                self.populate_column(col, asc, is_checked=True)
        if len(all_columns) > 0:
            for col in all_columns:
                self.populate_column(col, 0, is_checked=False)
        self.blockSignals(False)

    def populate_column(self, col, asc, is_checked):
        item = QListWidgetItem(self.gui.library_view.model().headers[col], self)
        item.setData(Qt.UserRole, col+'|'+str(asc))
        flags = Qt.ItemIsEnabled|Qt.ItemIsSelectable|Qt.ItemIsUserCheckable
        item.setFlags(flags)
        item.setCheckState(Qt.Checked if is_checked else Qt.Unchecked)
        self.set_sort_icon(item)

    def set_sort_icon(self, item):
        previous = self.blockSignals(True)
        if item.checkState() == Qt.Checked:
            data = item.data(Qt.UserRole).strip()
            asc = int(data.rpartition('|')[2])
            if asc == 0:
                item.setIcon(get_icon('images/sort_asc.png'))
            else:
                item.setIcon(get_icon('images/sort_desc.png'))
        else:
            item.setIcon(QIcon())
        self.item_selection_changed() ## otherwise asc/desc can be disabled if selected, then checked.
        self.blockSignals(previous)

    def item_selection_changed(self):
        self.sort_ascending_action.setEnabled(False)
        self.sort_descending_action.setEnabled(False)
        item = self.currentItem()
        if item and item.checkState() == Qt.Checked:
            self.sort_ascending_action.setEnabled(True)
            self.sort_descending_action.setEnabled(True)

    def change_sort(self, asc):
        item = self.currentItem()
        if item:
            self.blockSignals(True)
            data = item.data(Qt.UserRole).strip().split('|')
            col = data[0]
            item.setData(Qt.UserRole, col+'|'+str(asc))
            self.set_sort_icon(item)
            self.blockSignals(False)

    def get_data(self):
        cols = []
        for idx in range(self.count()):
            item = self.item(idx)
            data = item.data(Qt.UserRole).strip().split('|')
            if item.checkState() == Qt.Checked:
                cols.append((data[0], int(data[1])))
        return cols


class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        self.gui = plugin_action.gui
        self.db = self.gui.current_db
        self.library = get_library_config(self.db)
        self.views = self.library[KEY_VIEWS]
        self.all_columns = self.get_current_columns()
        self.view_name = None

        self.has_pin_view = hasattr(self.gui.library_view,'pin_view')

        toplayout = QVBoxLayout(self)
        self.setLayout(toplayout)
        ## wrap config in a scrollable area for smaller displays.
        scrollable = QScrollArea()
        scrollcontent = QWidget()
        scrollable.setWidget(scrollcontent)
        scrollable.setWidgetResizable(True)
        toplayout.addWidget(scrollable)

        layout = QVBoxLayout()
        scrollcontent.setLayout(layout)

        select_view_layout = QHBoxLayout()
        layout.addLayout(select_view_layout)
        select_view_label = QLabel(_('Select view to customize:'), self)
        select_view_layout.addWidget(select_view_label)
        self.select_view_combo = ViewComboBox(self, self.views)
        self.select_view_combo.setMinimumSize(150, 20)
        select_view_layout.addWidget(self.select_view_combo)
        self.add_view_button = QToolButton(self)
        self.add_view_button.setToolTip(_('Add view'))
        self.add_view_button.setIcon(QIcon(I('plus.png')))
        self.add_view_button.clicked.connect(self.add_view)
        select_view_layout.addWidget(self.add_view_button)
        self.delete_view_button = QToolButton(self)
        self.delete_view_button.setToolTip(_('Delete view'))
        self.delete_view_button.setIcon(QIcon(I('minus.png')))
        self.delete_view_button.clicked.connect(self.delete_view)
        select_view_layout.addWidget(self.delete_view_button)
        self.rename_view_button = QToolButton(self)
        self.rename_view_button.setToolTip(_('Rename view'))
        self.rename_view_button.setIcon(QIcon(I('edit-undo.png')))
        self.rename_view_button.clicked.connect(self.rename_view)
        select_view_layout.addWidget(self.rename_view_button)
        select_view_layout.insertStretch(-1)

        view_group_box = QGroupBox(_('Column Options'),self)
        layout.addWidget(view_group_box)
        view_group_box_layout = QVBoxLayout()
        view_group_box.setLayout(view_group_box_layout)

        customise_layout = QGridLayout()
        view_group_box_layout.addLayout(customise_layout, 1)

        if self.has_pin_view:
            columns_label = _('Columns in Default (Left) pane')
        else:
            columns_label = _('Columns in view')
        self.columns_label = QLabel(columns_label,self)
        self.columns_list = ColumnListWidget(self, self.gui)
        self.move_column_up_button = QToolButton(self)
        self.move_column_up_button.setToolTip(_('Move column up'))
        self.move_column_up_button.setIcon(QIcon(I('arrow-up.png')))
        self.move_column_down_button = QToolButton(self)
        self.move_column_down_button.setToolTip(_('Move column down'))
        self.move_column_down_button.setIcon(QIcon(I('arrow-down.png')))
        self.move_column_up_button.clicked.connect(self.columns_list.move_column_up)
        self.move_column_down_button.clicked.connect(self.columns_list.move_column_down)

        if self.has_pin_view:

            self.apply_pin_columns_checkbox = QCheckBox(_('Columns in Split (Right) Pane'), self)
            self.apply_pin_columns_checkbox.setToolTip(_('Split Book List will only be shown if this is checked. This will be checked if you save a Split View.'))
            self.pin_columns_list = ColumnListWidget(self, self.gui)
            self.move_pin_column_up_button = QToolButton(self)
            self.move_pin_column_up_button.setToolTip(_('Move column up'))
            self.move_pin_column_up_button.setIcon(QIcon(I('arrow-up.png')))
            self.move_pin_column_down_button = QToolButton(self)
            self.move_pin_column_down_button.setToolTip(_('Move column down'))
            self.move_pin_column_down_button.setIcon(QIcon(I('arrow-down.png')))
            self.move_pin_column_up_button.clicked.connect(self.pin_columns_list.move_column_up)
            self.move_pin_column_down_button.clicked.connect(self.pin_columns_list.move_column_down)

            def group_abled(elems,cb):
                for el in elems:
                    el.setEnabled(cb.isChecked())

            pin_abled = partial(group_abled,
                                [self.pin_columns_list,
                                 self.move_pin_column_up_button,
                                 self.move_pin_column_down_button],
                                self.apply_pin_columns_checkbox)
            pin_abled()
            self.apply_pin_columns_checkbox.stateChanged.connect(pin_abled)

        self.sort_label = QLabel(_('Sort order'), self)
        self.sort_list = SortColumnListWidget(self, self.gui)
        self.move_sort_up_button = QToolButton(self)
        self.move_sort_up_button.setToolTip(_('Move sort column up'))
        self.move_sort_up_button.setIcon(QIcon(I('arrow-up.png')))
        self.move_sort_down_button = QToolButton(self)
        self.move_sort_down_button.setToolTip(_('Move sort down'))
        self.move_sort_down_button.setIcon(QIcon(I('arrow-down.png')))
        self.move_sort_up_button.clicked.connect(self.sort_list.move_column_up)
        self.move_sort_down_button.clicked.connect(self.sort_list.move_column_down)

        layout_col = 0 # calculate layout because pin column only shown if available.
        customise_layout.addWidget(self.columns_label, 0, layout_col, 1, 1)
        customise_layout.addWidget(self.columns_list, 1, layout_col, 3, 1)
        layout_col = layout_col + 1
        customise_layout.addWidget(self.move_column_up_button, 1, layout_col, 1, 1)
        customise_layout.addWidget(self.move_column_down_button, 3, layout_col, 1, 1)
        layout_col = layout_col + 1

        if self.has_pin_view:
            customise_layout.addWidget(self.apply_pin_columns_checkbox, 0, layout_col, 1, 1)
            customise_layout.addWidget(self.pin_columns_list, 1, layout_col, 3, 1)
            layout_col = layout_col + 1
            customise_layout.addWidget(self.move_pin_column_up_button, 1, layout_col, 1, 1)
            customise_layout.addWidget(self.move_pin_column_down_button, 3, layout_col, 1, 1)
            layout_col = layout_col + 1

        customise_layout.addWidget(self.sort_label, 0, layout_col, 1, 1)
        customise_layout.addWidget(self.sort_list, 1, layout_col, 3, 1)
        layout_col = layout_col + 1

        customise_layout.addWidget(self.move_sort_up_button, 1, layout_col, 1, 1)
        customise_layout.addWidget(self.move_sort_down_button, 3, layout_col, 1, 1)
        layout_col = layout_col + 1

        search_group_box = QGroupBox(_('Search and Virtual Library Options'),self)
        layout.addWidget(search_group_box)
        search_group_box_layout = QVBoxLayout()
        search_group_box.setLayout(search_group_box_layout)

        other_layout = QGridLayout()
        search_group_box_layout.addLayout(other_layout)

        self.apply_search_checkbox = QCheckBox(_('Apply saved search'), self)
        self.apply_search_checkbox.setToolTip(_('Apply the selected saved search when the View is activated.'))
        # print("calling saved_searches:%s"%self.db.saved_search_names())
        self.saved_search_combo = SearchComboBox(self, entries=self.db.saved_search_names(),empty="(Clear Search)")
        self.saved_search_combo.setToolTip("Saved search to apply.")
        # enable/disable combo based on check.
        self.saved_search_combo.setEnabled(self.apply_search_checkbox.isChecked())
        self.apply_search_checkbox.stateChanged.connect(lambda x : self.saved_search_combo.setEnabled(self.apply_search_checkbox.isChecked()))

        self.apply_virtlib_checkbox = QCheckBox(_('Switch to Virtual library'), self)
        self.apply_virtlib_checkbox.setToolTip(_('Switch to the selected Virtual library when the View is activated.'))
        self.virtlib_combo = SearchComboBox(self,entries=self.db.prefs.get('virtual_libraries', {}),empty="(No Virtual library)")
        self.virtlib_combo.setToolTip(_('Virtual library to switch to.'))
        # enable/disable combo based on check.
        self.virtlib_combo.setEnabled(self.apply_virtlib_checkbox.isChecked())
        self.apply_virtlib_checkbox.stateChanged.connect(lambda x : self.virtlib_combo.setEnabled(self.apply_virtlib_checkbox.isChecked()))

        self.apply_restriction_checkbox = QCheckBox(_('Apply VL additional search restriction'), self)
        self.apply_restriction_checkbox.setToolTip(_('Apply the selected saved search as a Virtual library additional restriction when the View is activated.'))
        self.search_restriction_combo = SearchComboBox(self,entries=self.db.saved_search_names(),empty='('+_('Clear VL restriction search')+')')
        self.search_restriction_combo.setToolTip(_('Saved search to apply as VL additional search restriction.'))
        # enable/disable combo based on check.
        self.search_restriction_combo.setEnabled(self.apply_restriction_checkbox.isChecked())
        self.apply_restriction_checkbox.stateChanged.connect(lambda x : self.search_restriction_combo.setEnabled(self.apply_restriction_checkbox.isChecked()))

        other_layout.addWidget(self.apply_search_checkbox, 0, 0, 1, 1)
        other_layout.addWidget(self.saved_search_combo, 0, 1, 1, 1)
        other_layout.addWidget(self.apply_virtlib_checkbox, 1, 0, 1, 1)
        other_layout.addWidget(self.virtlib_combo, 1, 1, 1, 1)
        other_layout.addWidget(self.apply_restriction_checkbox, 2, 0, 1, 1)
        other_layout.addWidget(self.search_restriction_combo, 2, 1, 1, 1)
        # other_layout.setRowStretch(4, 1)

        #layout.addSpacing(10)
        other_group_box = QGroupBox(_('General Options'), self)
        layout.addWidget(other_group_box)
        other_group_box_layout = QGridLayout()
        other_group_box.setLayout(other_group_box_layout)

        self.jump_to_top_checkbox = QCheckBox(_('Jump to the top when applying this View'), self)
        jump_to_top = self.library.get(KEY_JUMP_TO_TOP, False)
        self.jump_to_top_checkbox.setCheckState(Qt.Checked if jump_to_top else Qt.Unchecked)

        restart_label = QLabel(_('When restarting Calibre or switching to this library')+'...')
        self.auto_apply_checkbox = QCheckBox(_('Automatically apply view:'), self)
        auto_apply = self.library.get(KEY_AUTO_APPLY_VIEW, False)
        self.auto_apply_checkbox.setCheckState(Qt.Checked if auto_apply else Qt.Unchecked)
        self.auto_view_combo = ViewComboBox(self, self.views, special=LAST_VIEW_ITEM)
        self.auto_view_combo.select_view(self.library.get(KEY_VIEW_TO_APPLY, LAST_VIEW_ITEM))
        self.auto_view_combo.setMinimumSize(150, 20)
        info_apply_label = QLabel(_('Enabling this option may override any startup search restriction or '
                                  'title sort set in Preferences -> Behaviour/Tweaks.'))
        info_apply_label.setWordWrap(True)
        other_group_box_layout.addWidget(self.jump_to_top_checkbox, 0, 0, 1, 2)
        other_group_box_layout.addWidget(restart_label, 1, 0, 1, 2)
        other_group_box_layout.addWidget(self.auto_apply_checkbox, 2, 0, 1, 1)
        other_group_box_layout.addWidget(self.auto_view_combo, 2, 1, 1, 1)
        other_group_box_layout.addWidget(info_apply_label, 3, 0, 1, 2)
        #other_group_box.setMaximumHeight(other_group_box.sizeHint().height())

        keyboard_layout = QHBoxLayout()
        layout.addLayout(keyboard_layout)
        keyboard_shortcuts_button = QPushButton(' '+_('Keyboard shortcuts')+'... ', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        view_prefs_button = QPushButton(' '+_('&View library preferences')+'... ', self)
        view_prefs_button.setToolTip(_('View data stored in the library database for this plugin'))
        view_prefs_button.clicked.connect(self.view_prefs)
        keyboard_layout.addWidget(keyboard_shortcuts_button)
        keyboard_layout.addWidget(view_prefs_button)

        help_button = QPushButton(' '+_('&Help'), self)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(show_help)
        keyboard_layout.addWidget(help_button)
        keyboard_layout.addStretch(1)

        # Force an initial display of view information
        if KEY_LAST_VIEW in list(self.library.keys()):
            last_view = self.library[KEY_LAST_VIEW]
            if last_view in self.views:
                self.select_view_combo.select_view(self.library[KEY_LAST_VIEW])
        self.select_view_combo_index_changed(save_previous=False)
        self.select_view_combo.currentIndexChanged.connect(
                    partial(self.select_view_combo_index_changed, save_previous=True))

    def save_settings(self):
        # We only need to update the store for the current view, as switching views
        # will have updated the other stores
        self.persist_view_config()

        library_config = get_library_config(self.gui.current_db)
        library_config[KEY_VIEWS] = self.views
        library_config[KEY_AUTO_APPLY_VIEW] = self.auto_apply_checkbox.checkState() == Qt.Checked
        library_config[KEY_VIEW_TO_APPLY] = unicode(self.auto_view_combo.currentText())
        set_library_config(self.gui.current_db, library_config)

    def persist_view_config(self):
        if not self.view_name:
            return
        # Update all of the current user information in the store
        view_info = self.views[self.view_name]
        view_info[KEY_COLUMNS] = self.columns_list.get_data()
        view_info[KEY_SORT] = self.sort_list.get_data()
        if self.has_pin_view:
            view_info[KEY_APPLY_PIN_COLUMNS] = self.apply_pin_columns_checkbox.checkState() == Qt.Checked
            view_info[KEY_PIN_COLUMNS] = self.pin_columns_list.get_data()
        view_info[KEY_APPLY_RESTRICTION] = self.apply_restriction_checkbox.checkState() == Qt.Checked
        if view_info[KEY_APPLY_RESTRICTION]:
            view_info[KEY_RESTRICTION] = unicode(self.search_restriction_combo.currentText()).strip()
        else:
            view_info[KEY_RESTRICTION] = ''
        view_info[KEY_APPLY_SEARCH] = self.apply_search_checkbox.checkState() == Qt.Checked
        if view_info[KEY_APPLY_SEARCH]:
            view_info[KEY_SEARCH] = unicode(self.saved_search_combo.currentText()).strip()
        else:
            view_info[KEY_SEARCH] = ''
        view_info[KEY_APPLY_VIRTLIB] = self.apply_virtlib_checkbox.checkState() == Qt.Checked
        if view_info[KEY_APPLY_VIRTLIB]:
            view_info[KEY_VIRTLIB] = unicode(self.virtlib_combo.currentText()).strip()
        else:
            view_info[KEY_VIRTLIB] = ''
        view_info[KEY_JUMP_TO_TOP] = self.jump_to_top_checkbox.checkState() == Qt.Checked

        self.views[self.view_name] = view_info

    def select_view_combo_index_changed(self, save_previous=True):
        # Update the dialog contents with data for the selected view
        if save_previous:
            # Switching views, persist changes made to the other view
            self.persist_view_config()
        if self.select_view_combo.count() == 0:
            self.view_name = None
        else:
            self.view_name = unicode(self.select_view_combo.currentText()).strip()
        columns = []
        sort_columns = []
        all_columns = []
        pin_columns = []
        apply_columns = True
        apply_pin_columns = False
        apply_sort = True
        apply_restriction = False
        restriction_to_apply = ''
        apply_search = False
        search_to_apply = ''
        apply_virtlib = False
        virtlib_to_apply = ''
        jump_to_top = False
        if self.view_name != None:
            view_info = self.views[self.view_name]
            columns = copy.deepcopy(view_info[KEY_COLUMNS])
            pin_columns = copy.deepcopy(view_info.get(KEY_PIN_COLUMNS,{}))
            sort_columns = copy.deepcopy(view_info[KEY_SORT])
            all_columns = self.all_columns
            apply_pin_columns = view_info.get(KEY_APPLY_PIN_COLUMNS,False)
            apply_restriction = view_info[KEY_APPLY_RESTRICTION]
            restriction_to_apply = view_info[KEY_RESTRICTION]
            apply_search = view_info[KEY_APPLY_SEARCH]
            search_to_apply = view_info[KEY_SEARCH]
            apply_virtlib = view_info.get(KEY_APPLY_VIRTLIB,False)
            virtlib_to_apply = view_info.get(KEY_VIRTLIB,'')
            jump_to_top = view_info.get(KEY_JUMP_TO_TOP,False)

        self.columns_list.populate(columns, all_columns)
        self.sort_list.populate(sort_columns, all_columns)
        if self.has_pin_view:
            self.pin_columns_list.populate(pin_columns, all_columns)
            self.apply_pin_columns_checkbox.setCheckState(Qt.Checked if apply_pin_columns else Qt.Unchecked)
        self.apply_restriction_checkbox.setCheckState(Qt.Checked if apply_restriction else Qt.Unchecked)
        self.search_restriction_combo.select_value(restriction_to_apply)
        self.apply_search_checkbox.setCheckState(Qt.Checked if apply_search else Qt.Unchecked)
        self.saved_search_combo.select_value(search_to_apply)
        self.apply_virtlib_checkbox.setCheckState(Qt.Checked if apply_virtlib else Qt.Unchecked)
        self.virtlib_combo.select_value(virtlib_to_apply)
        self.jump_to_top_checkbox.setCheckState(Qt.Checked if jump_to_top else Qt.Unchecked)

    def add_view(self):
        # Display a prompt allowing user to specify a new view
        new_view_name, ok = QInputDialog.getText(self, 'Add new view',
                    'Enter a unique display name for this view:', text='Default')
        if not ok:
            # Operation cancelled
            return
        new_view_name = unicode(new_view_name).strip()
        # Verify it does not clash with any other views in the list
        for view_name in self.views.keys():
            if view_name.lower() == new_view_name.lower():
                return error_dialog(self, _('Add Failed'), _('A view with the same name already exists'), show=True)

        self.persist_view_config()
        view_info = get_empty_view()

        if self.view_name != None:
            # We will copy values from the currently selected view
            old_view_info = self.views[self.view_name]
            view_info[KEY_COLUMNS] = copy.deepcopy(old_view_info[KEY_COLUMNS])
            view_info[KEY_APPLY_PIN_COLUMNS] = copy.deepcopy(old_view_info.get(KEY_APPLY_PIN_COLUMNS,False))
            view_info[KEY_PIN_COLUMNS] = copy.deepcopy(old_view_info.get(KEY_PIN_COLUMNS,{}))
            view_info[KEY_SORT] = copy.deepcopy(old_view_info[KEY_SORT])
            view_info[KEY_APPLY_RESTRICTION] = copy.deepcopy(old_view_info[KEY_APPLY_RESTRICTION])
            view_info[KEY_RESTRICTION] = copy.deepcopy(old_view_info[KEY_RESTRICTION])
            view_info[KEY_APPLY_SEARCH] = copy.deepcopy(old_view_info[KEY_APPLY_SEARCH])
            view_info[KEY_SEARCH] = copy.deepcopy(old_view_info[KEY_SEARCH])
            view_info[KEY_APPLY_VIRTLIB] = copy.deepcopy(old_view_info.get(KEY_APPLY_VIRTLIB,False))
            view_info[KEY_VIRTLIB] = copy.deepcopy(old_view_info.get(KEY_VIRTLIB,''))
            view_info[KEY_JUMP_TO_TOP] = copy.deepcopy(old_view_info[KEY_JUMP_TO_TOP])
        else:
            # We will copy values from the current library view
            view_info[KEY_COLUMNS] = self.get_current_columns(visible_only=True)

        self.view_name = new_view_name
        self.views[new_view_name] = view_info
        # Now update the views combobox
        self.select_view_combo.populate_combo(self.views, new_view_name)
        self.select_view_combo_index_changed(save_previous=False)
        self.auto_view_combo.populate_combo(self.views, unicode(self.auto_view_combo.currentText()))

    def rename_view(self):
        if not self.view_name != None:
            return
        # Display a prompt allowing user to specify a rename view
        old_view_name = self.view_name
        new_view_name, ok = QInputDialog.getText(self, _('Rename view'),
                    _('Enter a new display name for this view:'), text=old_view_name)
        if not ok:
            # Operation cancelled
            return
        new_view_name = unicode(new_view_name).strip()
        if new_view_name == old_view_name:
            return
        # Verify it does not clash with any other views in the list
        for view_name in self.views.keys():
            if view_name == old_view_name:
                continue
            if view_name.lower() == new_view_name.lower():
                return error_dialog(self, _('Add Failed'), _('A view with the same name already exists'), show=True)

        # Ensure any changes are persisted
        self.persist_view_config()
        view_info = self.views[old_view_name]
        del self.views[old_view_name]
        self.view_name = new_view_name
        self.views[new_view_name] = view_info
        # Now update the views combobox
        self.select_view_combo.populate_combo(self.views, new_view_name)
        self.select_view_combo_index_changed(save_previous=False)
        if unicode(self.auto_view_combo.currentText()) == old_view_name:
            self.auto_view_combo.populate_combo(self.views, new_view_name)
        else:
            self.auto_view_combo.populate_combo(self.views)

    def delete_view(self):
        if self.view_name == None:
            return
        if not question_dialog(self, _('Are you sure?'), '<p>'+
                _('Do you want to delete the view named')+' \'%s\''%self.view_name,
                show_copy_button=False):
            return
        del self.views[self.view_name]
        # Now update the views combobox
        self.select_view_combo.populate_combo(self.views)
        self.select_view_combo_index_changed(save_previous=False)
        self.auto_view_combo.populate_combo(self.views)

    def get_current_columns(self, defaults=False, visible_only=False):
        model = self.gui.library_view.model()
        colmap = list(model.column_map)
        state = self.columns_state(defaults)
        positions = state['column_positions']
        colmap.sort(key=lambda x: positions[x])
        hidden_cols = state['hidden_columns']
        if visible_only:
            colmap = [col for col in colmap if col not in hidden_cols or col == 'ondevice']
        # Convert our list of column names into a list of tuples with column widths
        colsizemap = []
        for col in colmap:
            if col in hidden_cols:
                colsizemap.append((col, -1))
            else:
                colsizemap.append((col, state['column_sizes'].get(col,-1)))
        return colsizemap

    def columns_state(self, defaults=False):
        if defaults:
            return self.gui.library_view.get_default_state()
        return self.gui.library_view.get_state()

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
