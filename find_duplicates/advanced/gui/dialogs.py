#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~

__license__ = 'GPL v3'
__copyright__ = '2020, Ahmed Zaki <azaki00.dev@gmail.com>'

import copy

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (QApplication, Qt, QGridLayout, QHBoxLayout, QVBoxLayout,
                        QLabel, QGroupBox, QToolButton, QPushButton, QRadioButton,
                        QDialogButtonBox, QComboBox, QAbstractItemView, QCheckBox,
                        pyqtSignal, QListWidget, QSize, QIcon)
except ImportError:
    from PyQt5.Qt import (QApplication, Qt, QGridLayout, QHBoxLayout, QVBoxLayout,
                        QLabel, QGroupBox, QToolButton, QPushButton, QRadioButton,
                        QDialogButtonBox, QComboBox, QAbstractItemView, QCheckBox,
                        pyqtSignal, QListWidget, QSize, QIcon)


from calibre import patheq, prints
from calibre.constants import DEBUG
from calibre.gui2 import info_dialog, error_dialog, choose_dir
from calibre.library import db as DB

import calibre_plugins.find_duplicates.config as cfg
from calibre_plugins.find_duplicates.dialogs import FindVariationsDialog, ItemsComboBox
from calibre_plugins.find_duplicates.common_compatibility import qSizePolicy_Maximum, qSizePolicy_Preferred
from calibre_plugins.find_duplicates.common_icons import get_icon
from calibre_plugins.find_duplicates.common_dialogs import SizePersistedDialog
from calibre_plugins.find_duplicates.common_widgets import ImageTitleLayout
from calibre_plugins.find_duplicates.advanced.common import (get_cols, column_metadata)
from calibre_plugins.find_duplicates.advanced import AdvancedVariationAlgorithm
from calibre_plugins.find_duplicates.advanced.gui.rules_widget import RulesWidget
from calibre_plugins.find_duplicates.advanced.gui.save_restore import SaveRestoreGroup

try:
    load_translations()
except NameError:
    pass

class FileOpenCombo(QGroupBox):
    file_changed = pyqtSignal(str)
    def __init__(self, db, text='', choose_function=choose_dir, file_list=[], max_files=10):
        QGroupBox.__init__(self, text)
        self.db = db
        self.current_loc = None
        self.file_list = file_list
        self.max_files = max_files
        self.choose_function = choose_function
        l = QHBoxLayout()
        self.setLayout(l)
        self.file_combo = QComboBox()
        self.file_combo.setMaxCount(max_files)
        self.file_combo.activated.connect(self._rearrange_items)
        self.populate(self.file_list)
        
        self.browse_button = QToolButton(self)
        self.browse_button.setIcon(get_icon('document_open.png'))
        self.browse_button.clicked.connect(self._choose_location)
        
        l.addWidget(self.file_combo)
        l.addWidget(self.browse_button)
        
        self.setSizePolicy(qSizePolicy_Preferred, qSizePolicy_Maximum)

    def _choose_location(self, *args):
        loc = self.choose_function(self, 'choose duplicate library',
                _('Choose library location to compare against'))
        if loc:
            if patheq(loc, self.file_combo.currentText()):
                return
            exists = self.db.exists_at(loc)
            if patheq(loc, self.db.library_path):
                return error_dialog(self, _('Same as current'),
                        _('The location {0} contains the current calibre library').format(loc), show=True)
            if not exists:
                return error_dialog(self, _('No existing library found'),
                        _('There is no existing calibre library at {0}').format(loc),
                        show=True)

            idx = self.file_combo.findText(loc)
            if idx != -1:
                self.file_combo.removeItem(idx)
            self.file_combo.insertItem(0, loc)
            self.file_combo.setCurrentIndex(0)
            self.file_list = [ self.file_combo.itemText(x) for x in range(self.file_combo.count()) ]
            self.file_changed.emit(loc)

    def populate(self, file_list):
        self.file_combo.clear()
        self.file_combo.addItems(file_list)
        self.file_list = file_list
        self.file_changed.emit(self.file_combo.currentText())

    def _rearrange_items(self, idx):
        file_list = [ self.file_combo.itemText(x) for x in range(self.file_combo.count()) ]
        loc = file_list.pop(idx)
        file_list.insert(0, loc)
        self.populate(file_list)

    def text(self):
        return self.file_combo.currentText()

class AdvancedBookDuplicatesDialog(SizePersistedDialog):
    def __init__(self, plugin_action):
        self.plugin_action = plugin_action
        self.gui = plugin_action.gui
        self.db = self.gui.current_db
        SizePersistedDialog.__init__(self, self.gui, 'Advanced Book Duplicate Dialog')
        self.library_config = cfg.get_library_config(self.db)
        self.exemptions_type = 'book'
        self.possible_cols = get_cols(self.db)
        self._init_controls()
        self.resize_dialog()

    def _init_controls(self):
        self.setWindowTitle(_('Find book duplicates'))
        l = QVBoxLayout()
        self.setLayout(l)

        title_layout = ImageTitleLayout(self, 'images/find_duplicates.png', _('Duplicate Search Options'))
        l.addLayout(title_layout)
        l.addSpacing(5)

        self.srg = SaveRestoreGroup(self)
        l.addWidget(self.srg)

        algorithms = self.plugin_action.algorithms        
        self.rules_widget = RulesWidget(self, self.gui, algorithms, self.possible_cols, has_sort=True)
        l.addWidget(self.rules_widget, 1)
        
        self.rules_widget.match_rules_updated.connect(self._on_match_rules_updated)

        l.addSpacing(5)
        display_group_box = QGroupBox(_('Result Options:'), self)
        l.addWidget(display_group_box)
        display_group_box_layout = QGridLayout()
        display_group_box.setLayout(display_group_box_layout)
        self.show_all_button = QRadioButton(_('Show all groups at once with highlighting'), self)
        self.show_one_button = QRadioButton(_('Show one group at a time'), self)
        display_group_box_layout.addWidget(self.show_all_button, 0, 0, 1, 1)
        display_group_box_layout.addWidget(self.show_one_button, 0, 1, 1, 1)

        self.sort_numdups_checkbox = QCheckBox(_('Sort groups by number of duplicates'))
        self.sort_numdups_checkbox.setToolTip(_('When unchecked, will sort by an approximation of the title\n'
                                                'or by author if title is being ignored'))
        display_group_box_layout.addWidget(self.sort_numdups_checkbox, 2, 0, 1, 2)
        
        self.show_all_button.setChecked(True)
        self.sort_numdups_checkbox.setChecked(True)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._accept_clicked)
        self.button_box.rejected.connect(self.reject)
        l.addWidget(self.button_box)
        
        self.resize(600, 700)
        self.setSizePolicy(qSizePolicy_Preferred, qSizePolicy_Preferred)
        
        self.restore_settings()
        self._on_match_rules_updated(self.rules_widget.isComplete())

    def save_settings(self):
        self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_BOOK_DUPLICATES][cfg.KEY_SHOW_ALL_GROUPS] = self.show_all_button.isChecked()
        self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_BOOK_DUPLICATES][cfg.KEY_SORT_GROUPS_TITLE] = not self.sort_numdups_checkbox.isChecked()
        self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_BOOK_DUPLICATES][cfg.KEY_LAST_SETTINGS] = self.rules_widget.get_rules_and_filters()
        cfg.set_library_config(self.db, self.library_config)

    def restore_settings(self):
        show_all = self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_BOOK_DUPLICATES][cfg.KEY_SHOW_ALL_GROUPS]
        self.show_all_button.setChecked(show_all)
        self.show_one_button.setChecked(not show_all)
        self.sort_numdups_checkbox.setChecked(
            not self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_BOOK_DUPLICATES][cfg.KEY_SORT_GROUPS_TITLE]
        )
        rules_and_filters = self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_BOOK_DUPLICATES][cfg.KEY_LAST_SETTINGS]
        #is_restore = self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_RESTORE_LAST_SETTINGS]
        if rules_and_filters:
            # if some elements of match rules cannot be restored, clear all match rules as if no restore took place.
            if not self.rules_widget.restore_rules_and_filters(rules_and_filters, show_error_msg=False):
                self.rules_widget.reset()

    def _on_match_rules_updated(self, isComplete):
        self.srg.label.setText('')
        self.srg.save_button.setEnabled(isComplete)

    def _accept_clicked(self):
        if not self.rules_widget.isComplete():
            error_dialog(
                self,
                _('Match rule(s) has empty values'),
                _('Match rule(s) missing field or algorithm. To proceed, complete the missing data, or delete the match rule(s).'),
                show=True
            )
            return
        self.match_rules = copy.deepcopy(self.rules_widget.get_match_rules()) 
        self.sort_filters = self.rules_widget.sort_filters
        self.sort_groups_by_title = not self.sort_numdups_checkbox.isChecked()
        self.show_all_duplicates_mode = self.show_all_button.isChecked()
        self.save_settings()
        self.accept()

class AdvancedLibraryDuplicatesDialog(SizePersistedDialog):
    def __init__(self, plugin_action):
        self.plugin_action = plugin_action
        self.gui = plugin_action.gui
        self.db = self.gui.current_db
        SizePersistedDialog.__init__(self, self.gui, 'Advanced Library Dupliclate Dialog')
        self.library_config = cfg.get_library_config(self.db)
        self.exemptions_type = 'book'
        self.library_path = None
        self.target_db = None
        self.possible_cols = self.get_possible_cols()
        self._init_controls()
        self.resize_dialog()

    def _init_controls(self):
        self.setWindowTitle(_('Find library duplicates'))
        l = QVBoxLayout()
        self.setLayout(l)
        
        title_layout = ImageTitleLayout(self, 'library.png', _('Cross Library Search Options'))
        l.addLayout(title_layout)
        l.addSpacing(5)

        self.location = FileOpenCombo(self.db, _('Compare With Library:'))
        self.location.file_changed.connect(self._on_target_db_changed)
        l.addWidget(self.location)
        l.addSpacing(5)

        self.srg = SaveRestoreGroup(self)
        l.addWidget(self.srg)

        algorithms = self.plugin_action.algorithms
        self.rules_widget = RulesWidget(self, self.gui, algorithms, self.possible_cols, target_db=self.target_db)
        l.addWidget(self.rules_widget, 1)

        self.rules_widget.match_rules_updated.connect(self._on_match_rules_updated)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._accept_clicked)
        self.button_box.rejected.connect(self.reject)
        l.addWidget(self.button_box)
        
        self.resize(600, 700)
        self.setSizePolicy(qSizePolicy_Preferred, qSizePolicy_Preferred)
        
        self.rules_widget.setDisabled(True)
        self.srg.setDisabled(True)
        self.reset_target_db()
        
        self.restore_settings()
        self._on_match_rules_updated(self.rules_widget.isComplete())

    def reset_target_db(self):
        self.library_path = None
        loc = str(self.location.text()).strip()
        if not loc:
            return None
        exists = self.db.exists_at(loc)
        if patheq(loc, self.db.library_path):
            return None
        if not exists:
            return None
        self.library_path = loc
        self.target_db = DB(self.library_path, read_only=True)
        self.rules_widget.target_db = self.target_db

    def get_possible_cols(self):
        current_cols = get_cols(self.db)
        if self.target_db:
            target_cols = get_cols(self.target_db)
        else:
            target_cols = []
        common_cols = set(current_cols).intersection(set(target_cols))
        return common_cols

    def _choose_location(self, *args):
        raise NotImplemented

    def _on_target_db_changed(self, loc):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        # save a temporary copy of current match rules, will try to restore later if possible
        match_rules = self.rules_widget.get_rules_and_filters()
        try:
            self.reset_target_db()
            self.possible_cols = self.get_possible_cols()
            if self.target_db:
                self.rules_widget.setEnabled(True)
                self.srg.setEnabled(True)
                self.rules_widget.reset(self.possible_cols)
                # restore match rules from previous library if possible
                # if some elements of match rules cannot be restored, clear all match rules as if no restore took place.
                if DEBUG:
                    prints('Find Duplicates: restoring match rules from previous target library')
                if not self.rules_widget.restore_rules_and_filters(match_rules, show_error_msg=False):
                    self.rules_widget.reset(self.possible_cols)
        finally:
            QApplication.restoreOverrideCursor()

    def clean_loc_list(self, loc_list):
        '''
        remove invalid entries from location list
        '''
        for idx in reversed(range(len(loc_list))):
            loc = loc_list[idx]
            exists = self.db.exists_at(loc)
            if not exists:
                loc_list.pop(idx)
        return loc_list

    def save_settings(self):
        self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_LIBRARY_DUPLICATES][cfg.KEY_LIBRARIES_LOC_LIST] = self.location.file_list
        self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_LIBRARY_DUPLICATES][cfg.KEY_LAST_SETTINGS] = self.rules_widget.get_rules_and_filters()
        cfg.set_library_config(self.db, self.library_config)

    def restore_settings(self):
        loc_list = copy.copy(self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_LIBRARY_DUPLICATES][cfg.KEY_LIBRARIES_LOC_LIST])
        loc_list = self.clean_loc_list(loc_list)
        self.location.populate(loc_list)
        rules_and_filters = self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_LIBRARY_DUPLICATES][cfg.KEY_LAST_SETTINGS]
        if rules_and_filters and self.target_db:
            # if some elements of match rules cannot be restored, clear all match rules as if no restore took place.
            if not self.rules_widget.restore_rules_and_filters(rules_and_filters, show_error_msg=False):
                self.rules_widget.reset()

    def _on_match_rules_updated(self, isComplete):
        self.srg.label.setText('')
        self.srg.save_button.setEnabled(isComplete)

    def _accept_clicked(self):
        if not self.rules_widget.isComplete():
            error_dialog(
                self,
                _('Match rule(s) has empty values'),
                _('Match rule(s) missing field or algorithm. To proceed, complete the missing data, or delete the match rule(s).'),
                show=True
            )
            return
        self.match_rules = copy.deepcopy(self.rules_widget.get_match_rules())
        loc = str(self.location.text()).strip()
        if not loc:
            return error_dialog(self, _('No library specified'),
                    _('You must specify a library path'), show=True)
        exists = self.db.exists_at(loc)
        if patheq(loc, self.db.library_path):
            return error_dialog(self, _('Same as current'),
                    _('The location {0} contains the current calibre library').format(loc), show=True)
        if not exists:
            return error_dialog(self, _('No existing library found'),
                    _('There is no existing calibre library at {0}').format(loc),
                    show=True)

        self.library_path = loc
        self.save_settings()
        self.accept()

class AdvancedVariationsDialog(FindVariationsDialog):

    DEFAULT_ROW_HEIGHT = 24
    ICON_SIZE = 16
    
    def __init__(self, plugin_action):
        self.plugin_action = plugin_action
        self.gui = plugin_action.gui
        self.db = self.gui.current_db
        SizePersistedDialog.__init__(self, self.gui, 'Addvanced Metadata Variations Dialog')
        self.library_config = cfg.get_library_config(self.db)
        self.alg = AdvancedVariationAlgorithm(self.db, self.gui)
        self.item_map = {}
        self.count_map = {}
        self.variations_map = {}
        self.is_renamed = False
        self.combo_items = []
        self.item_type = self.item_icon = None
        self.possible_cols = self.get_possible_cols()
        self._init_controls()

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def _init_controls(self):
        self.setWindowTitle(_('Find metadata variations'))
        self.setWindowIcon(get_icon('images/find_duplicates.png'))
        l = QVBoxLayout()
        self.setLayout(l)
        self.title_layout = ImageTitleLayout(self, 'user_profile.png', _('Find Metadata Variations'))
        l.addLayout(self.title_layout)
        l.addSpacing(10)

        self.srg = SaveRestoreGroup(self, False)
        l.addWidget(self.srg)

        algorithms = self.plugin_action.algorithms 
        self.rules_widget = RulesWidget(self, self.gui, algorithms, self.possible_cols, mode='metadata_variations')
        l.addWidget(self.rules_widget)
        
        self.rules_widget.match_rules_updated.connect(self._on_match_rules_updated)

        self.refresh_button = QPushButton(_('Search'), self)
        self.refresh_button.setIcon(QIcon(I('search.png')))
        self.refresh_button.setToolTip(_('Search for results'))
        self.refresh_button.clicked.connect(self._refresh_results)
        self.refresh_button.setDisabled(True)
        
        hl = QHBoxLayout()
        hl.addStretch(1)
        hl.addWidget(self.refresh_button)
        l.addLayout(hl)
        
        rgb = QGroupBox(_('Search results:'), self)
        l.addWidget(rgb, 1)

        gl = QGridLayout()
        rgb.setLayout(gl)

        self.item_lbl = QLabel(_('Items:'), self)
        self.vlbl = QLabel(_('Variations:'), self)

        self.item_list = QListWidget(self)
        self.item_list.setAlternatingRowColors(True)
        self.item_list.setIconSize(QSize(self.ICON_SIZE, self.ICON_SIZE))
        self.item_list.currentItemChanged.connect(self._on_list_item_changed)
        self.item_list.doubleClicked.connect(self._on_list_item_double_clicked)

        self.variations_list = QListWidget(self)
        self.variations_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.variations_list.setIconSize(QSize(self.ICON_SIZE, self.ICON_SIZE))
        self.variations_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.variations_list.customContextMenuRequested.connect(self._on_context_menu_requested)

        self.show_books_chk = QCheckBox(_('&Show matching books'), self)
        self.show_books_chk.setToolTip(_('As a group is selected, show the search results in the library view'))
        self.show_books_chk.clicked.connect(self._on_show_books_checkbox_changed)

        self.rename_lbl = QLabel(_('Rename to:'), self)
        self.rename_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.rename_combo = ItemsComboBox(self)

        gl.addWidget(self.item_lbl, 0, 0, 1, 2)
        gl.addWidget(self.vlbl, 0, 2, 1, 1)
        gl.addWidget(self.item_list, 1, 0, 1, 2)
        gl.addWidget(self.variations_list, 1, 2, 1, 1)
        gl.addWidget(self.show_books_chk, 2, 0, 1, 1)
        gl.addWidget(self.rename_lbl, 2, 1, 1, 1)
        gl.addWidget(self.rename_combo, 2, 2, 1, 1)
        gl.setColumnStretch(1, 2)
        gl.setColumnStretch(2, 3)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self._close_clicked)
        self.rename_button = button_box.addButton(_('&Rename'), QDialogButtonBox.ActionRole)
        self.rename_button.setToolTip(_('Rename all of the selected items to this name'))
        self.rename_button.clicked.connect(self._rename_selected)

        self.ignore_button = button_box.addButton(_('&Ignore'), QDialogButtonBox.ActionRole)
        self.ignore_button.setToolTip(_('Ignore all selected items from consideration at this time'))
        self.ignore_button.clicked.connect(self._ignore_selected)
        l.addWidget(button_box)
        
        self.resize(600, 700)
        self.setSizePolicy(qSizePolicy_Preferred, qSizePolicy_Preferred)
        
        self.restore_settings()
        self._on_match_rules_updated(self.rules_widget.isComplete())

    def get_possible_cols(self):
        all_cols = get_cols(self.db)
        possible_cols = []
        for column in all_cols:
            datatype = column_metadata(self.db, column)['datatype']
            if datatype in ['text','series']:
                if column not in ['title','languages','formats']:
                    possible_cols.append(column)
        return possible_cols

    def _on_match_rules_updated(self, isComplete):
        if isComplete:
            self.refresh_button.setEnabled(True)
        else:
            self.refresh_button.setDisabled(True)
        try:
            control = self.rules_widget.controls_layout.itemAt(0).widget()
            field = control.col_combo_box.currentText()
            if field:
                self._on_field_change(field)
        except AttributeError:
            # rules_widget has no contorls on it
            pass
        self.srg.label.setText('')
        self.srg.save_button.setEnabled(isComplete)

    def _refresh_results(self):
        self.match_rules = copy.deepcopy(self.rules_widget.get_match_rules()) 
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.item_map, self.count_map, self.variations_map = \
                self.alg.run_variation_check(self.match_rules)
            self.combo_items = list(self.item_map.values())
            self._populate_rename_combo()
            self._populate_items_list()
        finally:
            QApplication.restoreOverrideCursor()
        if len(self.variations_map) == 0:
            info_dialog(self.gui, _('No matches'), _('You have no variations of {0} using this criteria').format(self.item_type),
                        show=True, show_copy_button=False)

    def _on_field_change(self, field):
        #self.item_type = self.control.col_combo_box.currentText()
        self.item_type = field
        icon_name = column_metadata(self.db, self.item_type)['icon_name']
        self.item_icon = QIcon(I(icon_name))
        self.search_pattern = '{}:"=%s"'.format(self.item_type)
        
        self.title_layout.update_title_icon(icon_name)

        self.item_lbl.setText(field + ':')
        self.item_list.clear()
        self.rename_combo.clear()
        self._on_list_item_changed()

    def _on_item_option_toggled(self, is_checked):
        # functionality replaced by _on_field_change
        raise NotImplemented

    def _perform_database_rename(self, old_id, text):
        self.is_renamed = True
        item_type = self.item_type.lower()
        if item_type == 'authors':
            self.db.rename_author(old_id, text)
        elif item_type == 'publisher':
            self.db.rename_publisher(old_id, text)
        elif item_type == 'series':
            self.db.rename_series(old_id, text, change_index=False)
        elif item_type == 'tags':
            self.db.rename_tag(old_id, text)
        # Update: add custom column to metadata variations {
        else:
            self.db.rename_custom_item(old_id, text, column_metadata(self.db, self.item_type)['label'], num=None)
        #}

    def save_settings(self):  
        self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_METADATA_VARIATIONS][cfg.KEY_SHOW_VARIATION_BOOKS] = self.show_books_chk.isChecked()
        self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_METADATA_VARIATIONS][cfg.KEY_LAST_SETTINGS] = self.rules_widget.get_rules_and_filters()
        cfg.set_library_config(self.db, self.library_config)

    def restore_settings(self):
        show_books = self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_METADATA_VARIATIONS][cfg.KEY_SHOW_VARIATION_BOOKS]
        self.show_books_chk.setChecked(show_books)
        rules_and_filters = self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_METADATA_VARIATIONS][cfg.KEY_LAST_SETTINGS]
#        is_restore = self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_RESTORE_LAST_SETTINGS]
        if rules_and_filters:
            # if some elements of match rules cannot be restored, clear all match rules as if no restore took place.
            if not self.rules_widget.restore_rules_and_filters(rules_and_filters, show_error_msg=False):
                self.rules_widget.reset()

    def _close_clicked(self):
        self.save_settings()
        self.reject()
