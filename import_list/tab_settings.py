from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import copy, os, json
from collections import defaultdict

try:
    from qt.core import (Qt, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, 
                        QAbstractItemView, QRadioButton, QUrl, QTreeWidget, 
                        QSize, QTreeWidgetItem, QListWidget, QListWidgetItem,
                        QInputDialog, QFileDialog)
except ImportError:                        
    from PyQt5.Qt import (Qt, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, 
                        QAbstractItemView, QRadioButton, QUrl, QTreeWidget, 
                        QSize, QTreeWidgetItem, QListWidget, QListWidgetItem,
                        QInputDialog, QFileDialog)

try:
    AnyFile = QFileDialog.FileMode.AnyFile
except:
    AnyFile = QFileDialog.AnyFile

from calibre.debug import iswindows
from calibre.gui2 import (error_dialog, choose_files, open_url,
                          info_dialog, FileDialog)
from calibre.gui2.dialogs.confirm_delete import confirm
from calibre.utils.config import config_dir, JSONConfig
from calibre.utils.zipfile import ZipFile

import calibre_plugins.import_list.config as cfg
from calibre_plugins.import_list.common_icons import get_icon
from calibre_plugins.import_list.tab_common import get_templated_url, ICON_SIZE

try:
    load_translations()
except NameError:
    pass

class SettingsTab(QWidget):

    def __init__(self, parent_page):
        self.parent_page = parent_page
        QWidget.__init__(self, parent_page)
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        self.bl = QHBoxLayout()
        self.layout.addLayout(self.bl)

        self.browser_button = QPushButton(get_icon('images/browser.png'), _('Browser'), self)
        self.browser_button.setToolTip(_('View related website page in your web browser'))
        self.browser_button.clicked.connect(self.view_web_page)
        self.edit_button = QPushButton(get_icon('edit_input.png'), _('Edit'), self)
        self.edit_button.setToolTip(_('Edit this saved setting'))
        self.edit_button.clicked.connect(self.edit_setting)
        self.preview_button = QPushButton(get_icon('wizard.png'), _('&Preview'), self)
        self.preview_button.setToolTip(_('Preview the results in the books grid'))
        self.preview_button.clicked.connect(self.load_setting)
        self.bl.addWidget(self.browser_button)
        self.bl.addStretch(1)
        self.bl.addWidget(self.edit_button)
        self.bl.addWidget(self.preview_button)

    def get_setting_name(self):
        pass

    def get_setting_url(self, name):
        pass

    def is_predefined(self):
        pass

    def view_web_page(self):
        name = self.get_setting_name()
        tokenised_url = self.get_setting_url(name)
        url = get_templated_url(tokenised_url)
        open_url(QUrl(url))

    def edit_setting(self):
        self.parent_page.request_load_settings(self.get_setting_name(),
                                self.is_predefined(), edit_mode=True)

    def load_setting(self):
        self.parent_page.request_load_settings(self.get_setting_name(),
                                self.is_predefined(), edit_mode=False)


class UserSettingsTab(SettingsTab):

    def __init__(self, parent_page, saved_settings):
        SettingsTab.__init__(self, parent_page)
        self.saved_settings = saved_settings
        
        self.browser_button.setVisible(False)

        sl = QHBoxLayout()
        self.layout.insertLayout(0, sl, 1)
        self.settings_list = QListWidget(self)
        self.settings_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.settings_list.setAlternatingRowColors(True)
        self.settings_list.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.settings_list.itemDoubleClicked.connect(self.load_setting)
        sl.addWidget(self.settings_list, 1)

        actl = QVBoxLayout()
        sl.addLayout(actl)

        self.delete_button = QPushButton(get_icon('trash.png'), _('Delete'), self)
        self.delete_button.clicked.connect(self._delete_setting)
        self.rename_button = QPushButton(get_icon('edit-undo.png'), _('Rename'), self)
        self.rename_button.clicked.connect(self._rename_setting)
        self.export_button = QPushButton(get_icon('arrow-up.png'), _('Export')+'...', self)
        self.export_button.clicked.connect(self._export_setting)
        self.import_button = QPushButton(get_icon('arrow-down.png'), _('Import.')+'...', self)
        self.import_button.clicked.connect(self._import_setting)
        actl.addWidget(self.delete_button)
        actl.addWidget(self.rename_button)
        actl.addWidget(self.import_button)
        actl.addWidget(self.export_button)
        actl.addStretch(1)

        self._populate_list(saved_settings, select_first=True)
        self.settings_list.currentRowChanged[int].connect(self._current_row_changed)

        self.plugins_dir = os.path.join(config_dir, 'plugins')

    def _delete_setting(self):
        setting_name = self.get_setting_name()
        message = '<p>'+_('Are you sure you want to remove the setting "%s"?')%setting_name
        if not confirm(message+'<p>',_('import_list_delete_setting'), self):
            return
        idx = self.settings_list.currentRow()
        del self.saved_settings[setting_name]
        self.settings_list.takeItem(idx)
        cnt = self.settings_list.count()
        if cnt > 0:
            if idx >= cnt:
                idx = cnt - 1
            self.settings_list.setCurrentRow(idx)

    def _rename_setting(self):
        setting_name = self.get_setting_name()
        new_setting_name, ok = QInputDialog.getText(self.parent_page, _('New setting name:'),
                                            _('New setting name:'), text=setting_name)
        new_setting_name = str(new_setting_name).strip()
        if not ok or new_setting_name.lower() == setting_name.lower():
            # Operation cancelled or user did not actually choose a new name
            return
        for setting in self.saved_settings.keys():
            if setting.lower() == new_setting_name.lower():
                return error_dialog(self.parent_page, _('Setting exists'),
                        _('A saved setting already exists with this name.'), show=True)

        self.saved_settings[new_setting_name] = self.saved_settings[setting_name]
        del self.saved_settings[setting_name]
        self._populate_list(self.saved_settings)
        item = self.settings_list.findItems(new_setting_name, Qt.MatchExactly)[0]
        self.settings_list.setCurrentItem(item)

    def _import_setting(self):
        archive_paths = self._pick_archive_names_to_import()
        if not archive_paths:
            return
        for archive_path in archive_paths:
            if iswindows:
                archive_path = os.path.normpath(archive_path)

            with ZipFile(archive_path, 'r') as zf:
                contents = zf.namelist()
                if 'saved_setting.json' not in contents:
                    return error_dialog(self.parent_page, _('Import Failed'),
                                        _('This is not a valid Import List export archive'), show=True)
                json_text = zf.read('saved_setting.json')
                json_config = json.loads(json_text, encoding='utf-8')

            # Ask the user for a unique setting name
            settings = json_config[cfg.KEY_SAVED_SETTINGS]
            setting_name = list(settings.keys())[0]
            new_setting_name = self._get_new_setting_name(_('Import setting'), setting_name)
            if not new_setting_name:
                return
            # No more user intervention required, go ahead with rest of the operation
            self.saved_settings[new_setting_name] = copy.deepcopy(settings[setting_name])

        # Repopulate the list without changing the selected setting
        selected_setting_name = self.get_setting_name()
        self._populate_list(self.saved_settings)
        if selected_setting_name:
            item = self.settings_list.findItems(selected_setting_name, Qt.MatchExactly)[0]
            self.settings_list.setCurrentItem(item)
        else:
            self.settings_list.setCurrentRow(0)

    def _export_setting(self):
        setting_name = self.get_setting_name()
        archive_path = self._pick_archive_name_to_export()
        if not archive_path:
            return
        if iswindows:
            archive_path = os.path.normpath(archive_path)

        setting = self.saved_settings[setting_name]
        # Write our setting out to a json file, temporarily created in the plugins directory
        # before zipping and deleting afterwards
        export_settings = {}
        export_settings[setting_name] = copy.deepcopy(setting)
        # We don't want to export the "readingList" section as not relevant to other machines
        export_settings[setting_name][cfg.KEY_READING_LIST] = cfg.DEFAULT_READING_LIST_VALUES
        archive_config = JSONConfig('plugins/saved_setting')
        archive_config.set(cfg.KEY_SAVED_SETTINGS, export_settings)
        archive_config.set(cfg.KEY_SCHEMA_VERSION, cfg.DEFAULT_SCHEMA_VERSION)

        json_path = os.path.join(self.plugins_dir, 'saved_setting.json')
        if iswindows:
            json_path = os.path.normpath(json_path)
        try:
            # Create the zip file archive
            with ZipFile(archive_path, 'w') as archive_zip:
                archive_zip.write(json_path, os.path.basename(json_path))
            info_dialog(self.parent_page, _('Export completed'),
                        _('Cover setting exported to')+'<br>%s' % archive_path,
                        show=True, show_copy_button=False)
        finally:
            if os.path.exists(json_path):
                os.remove(json_path)

    def _get_new_setting_name(self, heading, default_name=''):
        new_setting_name, ok = QInputDialog.getText(self.parent_page, heading,
                            _('Enter a unique name for this saved setting:'), text=default_name)
        if not ok:
            # Operation cancelled
            return None
        new_setting_name = str(new_setting_name).strip()
        if len(new_setting_name) == 0:
            return None
        safe_setting_names = [name.lower() for name in self.saved_settings.keys()]
        if new_setting_name.lower() in safe_setting_names:
            error_dialog(self.parent_page, _('Cannot add'),
                                _('The name you specified is not unique'), show=True)
            return None
        return new_setting_name

    def _pick_archive_names_to_import(self):
        archives = choose_files(self.parent_page, 'Import List plugin:pick archive dialog',
                                _('Select setting file(s) to import'), all_files=False,
                                filters=[('Setting Files', ['zip'])], select_only_single_file=False)
        if not archives:
            return
        return archives

    def _pick_archive_name_to_export(self):
        fd = FileDialog(name='Import List plugin:pick archive dialog', title=_('Save setting as'),
                        parent=self.parent_page, filters=[('Setting Files', ['zip'])],
                        add_all_files_filter=False, mode=AnyFile)
        fd.setParent(None)
        if not fd.accepted:
            return None
        return fd.get_files()[0]

    def _current_row_changed(self, new_row):
        is_item_selected = new_row >= 0
        self.delete_button.setEnabled(is_item_selected)
        self.rename_button.setEnabled(is_item_selected)
        self.export_button.setEnabled(is_item_selected)
        self.edit_button.setEnabled(is_item_selected)
        self.preview_button.setEnabled(is_item_selected)
        self.browser_button.setEnabled(False)
        if is_item_selected:
            setting = self.saved_settings[self.get_setting_name()]
            if setting[cfg.KEY_IMPORT_TYPE] == cfg.KEY_IMPORT_TYPE_WEB:
                self.browser_button.setEnabled(True)

    def select_setting(self, setting_name):
        if setting_name is None:
            return
        matches = self.settings_list.findItems(setting_name, Qt.MatchExactly)
        if matches:
            self.settings_list.setCurrentItem(matches[0])

    def get_setting_name(self):
        item = self.settings_list.currentItem()
        if item is not None:
            return str(item.text())

    def get_setting_url(self, name):
        return self.settings_list[name][cfg.KEY_IMPORT_TYPE_WEB][cfg.KEY_WEB_URL]

    def is_predefined(self):
        return False

    def _populate_list(self, settings, select_first=False):
        self.settings_list.clear()
        # Sort the keys by saved setting import type
        skeys = sorted(list(settings.keys()),
                   key=lambda setting_name: '%s:%s'%(settings[setting_name][cfg.KEY_IMPORT_TYPE],
                                                     setting_name.lower()))
        for setting_name in skeys:
            item = QListWidgetItem(setting_name, self.settings_list)
            import_type = settings[setting_name][cfg.KEY_IMPORT_TYPE]
            if import_type == 'clipboard':
                item.setIcon(get_icon('edit-paste.png'))
            elif import_type == 'csv':
                item.setIcon(get_icon('drawer.png'))
            else:
                item.setIcon(get_icon('images/web.png'))
        if select_first and len(settings):
            self.settings_list.setCurrentRow(0)


class PredefinedSettingsTab(SettingsTab):

    def __init__(self, parent_page):
        SettingsTab.__init__(self, parent_page)
        self.last_tree_setting_name = None
        self._init_controls()

    def _init_controls(self):
        sl = QHBoxLayout()
        self.layout.insertLayout(0, sl, 1)
        self.settings_list = QListWidget(self)
        self.settings_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.settings_list.setAlternatingRowColors(True)
        self.settings_list.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.settings_list.itemDoubleClicked.connect(self.load_setting)
        sl.addWidget(self.settings_list, 1)

        self.settings_tv = QTreeWidget(self)
        self.settings_tv.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.settings_tv.header().hide()
        self.settings_tv.setSelectionMode(QAbstractItemView.SingleSelection)
        self.settings_tv.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        sl.addWidget(self.settings_tv, 1)

        actl = QVBoxLayout()
        sl.addLayout(actl)

        self.view_list_opt = QRadioButton(_('View as List'), self)
        self.view_list_opt.toggled.connect(self._view_type_toggled)
        self.view_category_opt = QRadioButton(_('View by Category'), self)
        self.view_category_opt.toggled.connect(self._view_type_toggled)
        actl.addWidget(self.view_list_opt)
        actl.addWidget(self.view_category_opt)
        actl.addStretch(1)

        self._populate_list(cfg.PREDEFINED_WEB_SETTINGS)
        self._populate_settings_tree()
        self.settings_list.currentRowChanged[int].connect(self._current_row_changed)
        self.settings_tv.currentItemChanged.connect(self._current_tree_item_changed)

    def _current_row_changed(self, new_row):
        is_enabled = new_row >= 0
        self.browser_button.setEnabled(is_enabled)
        self.edit_button.setEnabled(is_enabled)
        self.preview_button.setEnabled(is_enabled)

    def _current_tree_item_changed(self, current_item, previous_item):
        is_enabled = current_item is not None and current_item.childCount() == 0
        self.browser_button.setEnabled(is_enabled)
        self.edit_button.setEnabled(is_enabled)
        self.preview_button.setEnabled(is_enabled)
        if is_enabled:
            self.last_tree_setting_name = str(current_item.text(0))

    def _on_tree_item_double_clicked(self, item, col):
        if item is not None and item.childCount() == 0:
            self.load_setting()

    def get_setting_name(self):
        if self.view_list_opt.isChecked():
            return str(self.settings_list.currentItem().text())
        return self.last_tree_setting_name

    def get_setting_url(self, name):
        return cfg.PREDEFINED_WEB_SETTINGS[name][cfg.KEY_WEB_URL]

    def is_predefined(self):
        return True

    def select_setting(self, setting_name):
        if setting_name is None or setting_name not in cfg.PREDEFINED_WEB_SETTINGS:
            return
        if self.view_list_opt.isChecked():
            self._select_list_setting(setting_name)
        else:
            self.settings_tv.collapseAll()
            self._select_tree_setting(setting_name)

    def _view_type_toggled(self, is_checked):
        if not is_checked:
            return
        if self.view_list_opt.isChecked():
            self.settings_list.setVisible(True)
            self.settings_tv.setVisible(False)
        elif self.view_category_opt.isChecked():
            self.settings_list.setVisible(False)
            self.settings_tv.setVisible(True)

    def _select_list_setting(self, setting_name):
        matches = self.settings_list.findItems(setting_name, Qt.MatchExactly)
        if matches:
            self.settings_list.setCurrentItem(matches[0])

    def _select_tree_setting(self, setting_name):
        matches = self.settings_tv.findItems(setting_name, Qt.MatchExactly | Qt.MatchRecursive)
        if matches:
            matches[0].setSelected(True)
            matches[0].parent().setExpanded(True)
            self.settings_tv.setCurrentItem(matches[0])

    def _populate_list(self, settings):
        self.settings_list.clear()
        # Sort the keys by saved setting import type
        for setting_name in sorted(settings.keys()):
            item = QListWidgetItem(setting_name, self.settings_list)
            item.setIcon(get_icon('images/web.png'))
        self.settings_list.setCurrentRow(0)

    def _populate_settings_tree(self):
        cat_map = defaultdict(set)
        for setting_name, setting in cfg.PREDEFINED_WEB_SETTINGS.items():
            for cat_name in setting[cfg.KEY_WEB_CATEGORIES]:
                cat_map[cat_name].add(setting_name)

        first_child = None
        genre_tree_map = {}
        for cat_name in sorted(cat_map.keys()):
            parent = None
            if cat_name in genre_tree_map:
                parent = genre_tree_map[cat_name]
            else:
                # Not currently in our map so create the relevant nodes
                cat_parts = cat_name.split(':')
                parent = None
                for i in range(0, len(cat_parts)):
                    partial_cat_name = ':'.join(cat_parts[0:i+1])
                    if partial_cat_name in genre_tree_map:
                        parent = genre_tree_map[partial_cat_name]
                        continue
                    if parent is None:
                        parent = QTreeWidgetItem()
                        self.settings_tv.addTopLevelItem(parent)
                    else:
                        parent = QTreeWidgetItem(parent)
                    parent.setText(0, cat_parts[i])
                    parent.setFlags(Qt.ItemIsEnabled)
                    parent.setIcon(0, get_icon('images/category.png'))
                    genre_tree_map[partial_cat_name] = parent

            for setting_name in sorted(cat_map[cat_name],key=lambda c: c.lower()):
                it = QTreeWidgetItem(parent)
                it.setText(0, setting_name)
                it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                it.setIcon(0, get_icon('images/web.png'))
                if first_child is None:
                    first_child = it
