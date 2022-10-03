#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~

__license__ = 'GPL v3'
__copyright__ = '2020, Ahmed Zaki <azaki00.dev@gmail.com>'

import os
import copy
import json
from functools import partial

try:
    from qt.core import (Qt, QGridLayout, QHBoxLayout, QVBoxLayout, QComboBox,
                        QLabel, QGroupBox, QToolButton, QPushButton, QDialogButtonBox,
                        QAbstractItemView, QListWidget, QListWidgetItem,
                        QInputDialog, QMenu)
except ImportError:
    from PyQt5.Qt import (Qt, QGridLayout, QHBoxLayout, QVBoxLayout, QComboBox,
                        QLabel, QGroupBox, QToolButton, QPushButton, QDialogButtonBox,
                        QAbstractItemView, QListWidget, QListWidgetItem,
                        QInputDialog, QMenu)

from calibre.constants import DEBUG
from calibre.debug import iswindows
from calibre.gui2 import info_dialog, error_dialog, choose_save_file, choose_files
from calibre.gui2.complete2 import EditWithComplete
from calibre.gui2.dialogs.confirm_delete import confirm

import calibre_plugins.find_duplicates.config as cfg
from calibre_plugins.find_duplicates.common_icons import get_icon
from calibre_plugins.find_duplicates.common_dialogs import SizePersistedDialog
from calibre_plugins.find_duplicates.advanced.common import truncate, confirm_with_details

try:
    load_translations()
except NameError:
    pass


class ManageRulesDialog(SizePersistedDialog): 
    def __init__(
            self,
            parent,
            saved_settings,
            db, library_config,
            debug_prefix='Find Duplicates',
            unique_pref_name='Find Duplicates plugin:manage saved settings dialog'
        ):
        SizePersistedDialog.__init__(self, parent, unique_pref_name)
        self.setWindowTitle(_('Manage saved settings'))
        self.saved_settings = saved_settings
        self.db = db
        self.library_config = library_config
        self.debug_prefix = debug_prefix

        layout = QGridLayout()
        self.setLayout(layout)
        
        self.settings_list = QListWidget(self)
        self.settings_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.settings_list.setAlternatingRowColors(True)
        layout.addWidget(self.settings_list, 0, 0, 1, 1)

        actl = QVBoxLayout()
        layout.addLayout(actl, 0, 1, 1, 1)

        self.delete_button = QPushButton(get_icon('trash.png'), _('Delete'), self)
        self.delete_button.clicked.connect(self._delete_setting)
        self.rename_button = QPushButton(get_icon('edit-undo.png'), _('Rename'), self)
        self.rename_button.clicked.connect(self._rename_setting)
        self.export_button = QPushButton(get_icon('arrow-up.png'), _('Export')+'...', self)
        self.export_button.clicked.connect(self._export_setting)
        self.import_button = QPushButton(get_icon('arrow-down.png'), _('Import')+'...', self)
        self.import_button.clicked.connect(self._import_setting)
        actl.addWidget(self.delete_button)
        actl.addWidget(self.rename_button)
        actl.addWidget(self.import_button)
        actl.addWidget(self.export_button)
        actl.addStretch(1)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box, 1, 0, 1, 2)

        self.resize_dialog()
        self._populate_list(saved_settings, select_first=True)
        self.settings_list.itemSelectionChanged.connect(self._selection_changed)
        
        self._selection_changed()

    def _selection_changed(self):
        items_count = len(self.settings_list.selectedItems())
        self.delete_button.setEnabled(items_count > 0)
        self.rename_button.setEnabled(items_count == 1)
        self.export_button.setEnabled(items_count > 0)

    def _populate_list(self, settings, select_first=False):
        self.settings_list.clear()
        skeys = sorted(list(settings.keys()))
        
        for setting_name in skeys:
            item = QListWidgetItem(setting_name, self.settings_list)
            item.setIcon(get_icon('edit-paste.png'))

        if select_first and len(settings):
            self.settings_list.setCurrentRow(0)

    def _delete_setting(self):        
        selected_items = self.settings_list.selectedItems()
        message = _('<p>Are you sure you want to delete the {} selected setting(s)?</p>').format(len(selected_items))
        if not confirm(message, 'confirm_delete_settings', self):
            return
        for item in reversed(selected_items):
            setting_name = item.text()
            row = self.settings_list.row(item)
            self.settings_list.takeItem(row)
            del self.saved_settings[setting_name]
        cfg.set_library_config(self.db, self.library_config)

    def _rename_setting(self):
        selected_item = self.settings_list.selectedItems()[0]
        setting_name = selected_item.text()
        new_setting_name, ok = QInputDialog.getText(self, _('New name:'),
                                            _('New name:'), text=setting_name)
        new_setting_name = str(new_setting_name).strip()
        if not ok or new_setting_name.lower() == setting_name.lower():
            # Operation cancelled or user did not actually choose a new name
            return
        for setting in self.saved_settings.keys():
            if setting.lower() == new_setting_name.lower():
                return error_dialog(self, _('Saved settings exists'),
                        _('Saved settings exists with this name.'), show=True)

        self.saved_settings[new_setting_name] = self.saved_settings[setting_name]
        del self.saved_settings[setting_name]
        self._populate_list(self.saved_settings)
        cfg.set_library_config(self.db, self.library_config)
        item = self.settings_list.findItems(new_setting_name, Qt.MatchExactly)[0]
        self.settings_list.setCurrentItem(item)

    def _export_setting(self):
        selected_items = self.settings_list.selectedItems()
        
        json_path = choose_save_file(self, 'export-saved-settings', _('Choose file'), filters=[
            (_('Saved settings'), ['json'])], all_files=False)
        if json_path:
            if not json_path.lower().endswith('.json'):
                json_path += '.json'
        if not json_path:
            return
            
        if iswindows:
            json_path = os.path.normpath(json_path)
            
        exported_settings = {
            cfg.KEY_ADVANCED_MODE: {
                cfg.KEY_SAVED_SETTINGS: {},
                cfg.KEY_SCHEMA_VERSION: cfg.DEFAULT_SCHEMA_VERSION
            }
        }
        
        for item in selected_items:
            setting_name = item.text()
            exported_settings[cfg.KEY_ADVANCED_MODE][cfg.KEY_SAVED_SETTINGS][setting_name] = self.saved_settings[setting_name]
            
        with open(json_path, 'w') as f:
            json.dump(exported_settings, f, indent=4)
        
        info_dialog(self, _('Export completed'),
                    _('Exported to: {}').format(json_path),
                    show=True, show_copy_button=False)

    def _import_setting(self):
        path = choose_files(self, 'import_saved_settings', _('Choose file'), filters=[
            (_('Saved settings'), ['json'])], all_files=False, select_only_single_file=True)
        if not path:
            return
        else:
            json_path = path[0]
        if iswindows:
            json_path = os.path.normpath(json_path)

        with open(json_path, 'r') as f:
            imported_settings = json.load(f)
        
        try:
            if imported_settings.get('findDuplicatesSavedSettingsSchema'):
                imported_settings = cfg.migrate_imported_settings_from_old_schema(imported_settings)

            # Before calling cfg.migrate_advanced_settings_if_necessary make sure imported settings
            # have all missing keys to avoid errors
            cfg.get_missing_values_from_defaults(cfg.DEFAULT_LIBRARY_VALUES, imported_settings)
        except Exception as e:
            error_dialog(
                self,
                _('Import error'),
                _('This is not a valid settings file'),
                show=True
            )
            if DEBUG:
                print('{}: importing settings file failed with error: {}'.format(self.debug_prefix, e))
                import traceback
                print(traceback.format_exc())
            return

        all_settings_names = imported_settings[cfg.KEY_ADVANCED_MODE][cfg.KEY_SAVED_SETTINGS].keys()
        already_exist = set(self.saved_settings).intersection(set(all_settings_names))
        
        if already_exist:
            sep = '\n • '
            det_msg = _('The following settings already exit:') + sep
            det_msg += sep.join(list(already_exist))
            if not confirm_with_details(self,
                _('Overwrite settings?'),
                '<p>'+_('{} of the imported settings already exists. Do you want to overwrite them?').format(len(already_exist))+'</p>',
                det_msg=det_msg,
                show_copy_button=False):
                return

        for setting_name, setting_value in imported_settings[cfg.KEY_ADVANCED_MODE][cfg.KEY_SAVED_SETTINGS].items():
            self.saved_settings[setting_name] = setting_value
            if DEBUG:
                print('{}: imported settings: {}'.format(self.debug_prefix, setting_name))

        cfg.set_library_config(self.db, self.library_config)
        self._populate_list(self.saved_settings, select_first=True)

class SaveRestoreGroup(QGroupBox):
    def __init__(self, parent, opt_append=True):
        QGroupBox.__init__(self, _('Save/Restore settings'))
        self.parent = parent
        self.db = parent.db
        self.library_config = parent.library_config
        self.saved_settings = self.library_config[cfg.KEY_ADVANCED_MODE][cfg.KEY_SAVED_SETTINGS]
        self.opt_append = opt_append
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.rules_box = EditWithComplete(self)
        self.rules_box.set_separator(None)
        self.rules_box.setEditable(True)
        self.rules_box.setInsertPolicy(QComboBox.InsertAlphabetically)
        self.rules_box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)

        self.restore_button = QToolButton()
        self.restore_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.restore_button.setText(_('Restore'))
        self.restore_button.setToolTip(_('Restore saved settings'))
        
        self.save_button = QPushButton(_('Save'))
        self.save_button.setToolTip(_('Save current settings'))

        self.manage_button = QPushButton(_('Manage'))
        self.manage_button.setToolTip(_('Manage saved settings'))

        self.label = QLabel('', self)
        self.label.setAlignment(Qt.AlignCenter)

        h_layout = QHBoxLayout()
        h_layout.addWidget(self.rules_box, 1)
        h_layout.addWidget(self.restore_button)
        if opt_append:            
            self.restore_button.setPopupMode(QToolButton.MenuButtonPopup)
            rm = QMenu()
            rm.addAction(_('Add to existing'), partial(self._restore_settings, True))
            self.restore_button.setMenu(rm)

        h_layout.addWidget(self.save_button)
        h_layout.addWidget(self.manage_button)
        
        layout.addLayout(h_layout)
        layout.addWidget(self.label)
        
        self.restore_button.clicked.connect(self._restore_settings)
        self.save_button.clicked.connect(self._save_settings)
        self.manage_button.clicked.connect(self._manage_rules)
        self.rules_box.currentTextChanged.connect(self._update_restore_button)
        self.rules_box.editTextChanged.connect(self._update_restore_button)
        
        self.save_button.clicked.connect(self.refresh)
        
        self.refresh()
        self._update_restore_button('')

    def refresh(self):
        self.rules_box.update_items_cache(set(self.saved_settings.keys()))

    def _restore_settings(self, add_to_existing=False):
        setting_name = self.rules_box.text()
        if setting_name not in self.saved_settings.keys():
            error_dialog(
                self,
                _('Name error'),
                _('No settings with the name "{}" found').format(setting_name),
                show=True
            )
            return
            
        saved_setting = copy.deepcopy(self.saved_settings[setting_name])
        if self.parent.rules_widget.restore_rules_and_filters(saved_setting, add_to_existing):
            if not add_to_existing:
                self.label.setText('<b>{}</b>'.format(truncate(setting_name, 50)))
        else:
            self.label.setText('')
        
    def _save_settings(self):        
        setting_name = self._get_new_setting_name(_('Save settings'), '', unique=False)
        if not setting_name:
            return
        if setting_name in self.saved_settings.keys():
            message = _('There is already a saved setting with the name <b>"{}"</b>. Are you sure you want to replace it?').format(setting_name)
            if not confirm('<p>'+message+'</p>','replace_saved_settings', self):
                return

        saved_setting = copy.deepcopy(self.parent.rules_widget.get_rules_and_filters())
        self.saved_settings[setting_name] = saved_setting
        cfg.set_library_config(self.db, self.library_config)
        self.label.setText('<b>{}</b>'.format(truncate(setting_name, 50)))

    def _get_new_setting_name(self, heading, default_name='', unique=True):
        msg = _('Enter a name:')
        if unique: msg = _('Enter a unique name:')
        new_setting_name, ok = QInputDialog.getText(self, heading,
                            msg, text=default_name)
        if not ok:
            # Operation cancelled
            return None
        new_setting_name = str(new_setting_name).strip()
        if len(new_setting_name) == 0:
            return None
        if not unique:
            return new_setting_name
        safe_setting_names = [name.lower() for name in self.saved_settings.keys()]
        if new_setting_name.lower() in safe_setting_names:
            error_dialog(
                self,
                _('Cannot add'),
                _('The name you specified is not unique'), show=True
            )
            return None
        return new_setting_name

    def _update_restore_button(self, text):
        self.restore_button.setEnabled(text in self.saved_settings.keys())

    def _manage_rules(self):
        last_text = self.rules_box.text()
        last_label = self.label.text()
        d = ManageRulesDialog(self, self.saved_settings, self.db, self.library_config)
        d.exec_()
        self.refresh()
        if last_text not in self.saved_settings.keys():
            self.rules_box.clear()
        if last_label not in self.saved_settings.keys():
            self.label.setText('')
        else:
            self.label.setText(last_label)
