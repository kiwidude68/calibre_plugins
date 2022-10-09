from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

import os, re, traceback, copy, shutil
from functools import partial
import six
from six import text_type as unicode

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (Qt, QVBoxLayout, QLabel, QAbstractItemView, QCheckBox,
                        QGroupBox, QIcon, QPixmap, QListWidget, QListWidgetItem,
                        QDialog, QHBoxLayout, QDialogButtonBox, QPushButton,
                        QLineEdit, QGridLayout, QColorDialog, QColor, QSpinBox,
                        pyqtSignal, QComboBox, QTabWidget, QWidget, QInputDialog,
                        QTimer, QTextEdit, QProgressDialog, QSize,
                        QToolButton, QMenu, QFileDialog, QPainter, QPen, QRect,
                        QAbstractListModel, QFont, QSpacerItem)
except ImportError:
    from PyQt5.Qt import (Qt, QVBoxLayout, QLabel, QAbstractItemView, QCheckBox,
                        QGroupBox, QIcon, QPixmap, QListWidget, QListWidgetItem,
                        QDialog, QHBoxLayout, QDialogButtonBox, QPushButton,
                        QLineEdit, QGridLayout, QColorDialog, QColor, QSpinBox,
                        pyqtSignal, QComboBox, QTabWidget, QWidget, QInputDialog,
                        QTimer, QTextEdit, QProgressDialog, QSize,
                        QToolButton, QMenu, QFileDialog, QPainter, QPen, QRect,
                        QAbstractListModel, QFont, QSpacerItem)

from calibre import fit_image
from calibre.constants import iswindows
from calibre.ebooks.metadata import string_to_authors
from calibre.gui2 import (choose_images, error_dialog, question_dialog,
                          FileDialog, choose_files, info_dialog)
from calibre.gui2.dnd import dnd_get_files, dnd_has_extension, IMAGE_EXTENSIONS
from calibre.utils.config import JSONConfig
from calibre.utils.zipfile import ZipFile

import calibre_plugins.generate_cover.config as cfg
from calibre_plugins.generate_cover.common_compatibility import qSizePolicy_Expanding, qSizePolicy_Minimum, qtDropActionCopyAction
from calibre_plugins.generate_cover.common_icons import get_icon
from calibre_plugins.generate_cover.common_dialogs import SizePersistedDialog
from calibre_plugins.generate_cover.common_widgets import ReadOnlyLineEdit, ImageTitleLayout
from calibre_plugins.generate_cover.draw import (
    generate_cover_for_book, get_image_size, get_title_author_series)

try:
    AnyFile = QFileDialog.FileMode.AnyFile
except:
    AnyFile = QFileDialog.AnyFile

class GenerateCoverProgressDialog(QProgressDialog):
    '''
    Progress dialog for generating multiple covers rather than displaying the status
    '''
    def __init__(self, gui, books, db):
        self.total_count = len(books)
        QProgressDialog.__init__(self, '', _('Cancel'), 0, self.total_count, gui)
        self.setWindowTitle(_('Generating %d covers')%self.total_count)
        self.setMinimumWidth(500)
        self.books, self.db = books, db
        self.gui = gui

        library_config = cfg.get_library_config(db)
        self.update_column = library_config.get(cfg.PREFS_KEY_UPDATE_COLUMN, '')
        self.update_value = library_config.get(cfg.PREFS_KEY_UPDATE_VALUE, '')
        custom_columns = db.field_metadata.custom_field_metadata()
        if self.update_column != 'tags':
            if self.update_column not in custom_columns:
                # Custom column does not exist
                self.update_column = ''
                library_config[cfg.PREFS_KEY_UPDATE_COLUMN] = ''
                library_config[cfg.PREFS_KEY_UPDATE_VALUE] = ''
                cfg.set_library_config(db, library_config)
            else:
                self.update_col = custom_columns[self.update_column]
                self.update_column_type = self.update_col['datatype']
                self.update_label = self.db.field_metadata.key_to_label(self.update_column)
        self.i = 0
        # QTimer workaround on Win 10 on first go for Win10/Qt6 users not displaying dialog properly.
        QTimer.singleShot(100, self.do_generate_cover)
        self.exec_()

    def do_generate_cover(self):
        if self.i >= self.total_count:
            return self.do_close()
        mi = self.books[self.i]

        self.setLabelText(_('Generating: ')+mi.title)
        cover_data = generate_cover_for_book(mi, db=self.db.new_api)
        self.db.set_cover(mi.id, cover_data)
        if self.update_column and self.update_value:
            if self.update_column == 'tags':
                print(('Setting tags for book to:',self.update_value))
                self.db.set_tags(mi.id, self.update_value.split(','), append=True)
            elif self.update_column_type == 'bool':
                new_value = self.update_value.lower() == 'y'
                self.db.set_custom(mi.id, new_value, label=self.update_label)
            elif self.update_column_type == 'text':
                if self.update_col['is_multiple']:
                    self.db.set_custom_bulk_multiple([mi.id], add=[self.update_value], label=self.update_label)
                else:
                    self.db.set_custom(mi.id, self.update_value, label=self.update_label)

        self.i += 1
        self.setValue(self.i)
        QTimer.singleShot(0, self.do_generate_cover)

    def do_close(self):
        self.hide()
        self.gui = None


class UnsavedSettingsDialog(QDialog):

    def __init__(self, parent, setting_name, allow_dont_save=False):
        QDialog.__init__(self, parent)
        self.setWindowTitle(_('Unsaved Changes'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        layout.addWidget(QLabel(_('You have unsaved changes to the <b>%s</b> setting.<br>') % setting_name +
                                _('What do you want to do?'), self))
        # Dialog buttons
        button_box = QDialogButtonBox()
        self.discard_changes_button = button_box.addButton( ' '+_('Discard Changes')+' ', QDialogButtonBox.RejectRole)
        self.discard_changes_button.setToolTip(_('Revert unsaved changes and generate cover using the original<br/>'
                                                 'setting values (not as shown)'))
        self.discard_changes_button.clicked.connect(self.reject)
        self.is_deferred_save = False
        if allow_dont_save:
            self.dont_save_setting_button = button_box.addButton( ' '+_('Don\'t Save Yet')+' ', QDialogButtonBox.ApplyRole)
            self.dont_save_setting_button.setToolTip(_('Generate cover using these settings.<br/>'
                                                       'You can revert or save the changes when you next enter dialog.'))
            self.dont_save_setting_button.clicked.connect(self.on_dont_save_clicked)
        self.save_setting_button = button_box.addButton( ' '+_('Save Changes')+' ', QDialogButtonBox.AcceptRole)
        self.save_setting_button.setToolTip(_('Generate cover using these settings and save for future usage'))
        self.save_setting_button.clicked.connect(self.accept)
        layout.addWidget(button_box)

        self.resize(self.sizeHint())

    def on_dont_save_clicked(self):
        self.is_deferred_save = True
        self.accept()


class ImageView(QWidget):

    BORDER_WIDTH = 1
    cover_changed = pyqtSignal(object)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self._pixmap = QPixmap()
        self.setMinimumSize(QSize(150, 200))
        self.draw_border = True

    def setPixmap(self, pixmap):
        if not isinstance(pixmap, QPixmap):
            raise TypeError('Must use a QPixmap')
        self._pixmap = pixmap
        self.updateGeometry()
        self.update()

    def pixmap(self):
        return self._pixmap

    def sizeHint(self):
        if self._pixmap.isNull():
            return self.minimumSize()
        return self._pixmap.size()

    def paintEvent(self, event):
        QWidget.paintEvent(self, event)
        pmap = self._pixmap
        if pmap.isNull():
            return
        w, h = pmap.width(), pmap.height()
        cw, ch = self.rect().width(), self.rect().height()
        scaled, nw, nh = fit_image(w, h, cw, ch)
        if scaled:
            pmap = pmap.scaled(nw, nh, Qt.IgnoreAspectRatio,
                    Qt.SmoothTransformation)
        w, h = pmap.width(), pmap.height()
        x = int(abs(cw - w)/2.)
        y = int(abs(ch - h)/2.)
        target = QRect(x, y, w, h)
        p = QPainter(self)
        try:
            try:
                # qt6
                p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
            except:
                # qt5
                p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
            p.drawPixmap(target, pmap)
            pen = QPen()
            pen.setWidth(self.BORDER_WIDTH)
            p.setPen(pen)
            if self.draw_border:
                p.drawRect(target)
            #p.drawRect(self.rect())
        finally:
            p.end()


class PickSavedSettingListWidget(QListWidget):

    def __init__(self, parent=None):
        QListWidget.__init__(self, parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def populate(self, settings, selected_setting=cfg.KEY_DEFAULT):
        self.blockSignals(True)
        self.clear()
        self.settings = settings
        # Sort the settings so that the default one always appears first in list
        sorted_keys = sorted(settings.keys())
        sorted_keys.remove(cfg.KEY_DEFAULT)
        sorted_keys.insert(0, cfg.KEY_DEFAULT)
        for key in sorted_keys:
            item = QListWidgetItem(key, self)
            self.addItem(item)
        self.select_value(selected_setting)
        self.blockSignals(False)

    def selected_setting(self):
        if self.currentRow() == -1:
            return self.settings[cfg.KEY_DEFAULT]
        return self.settings[unicode(self.currentItem().text()).strip()]

    def select_value(self, selected_setting):
        self.blockSignals(True)
        items = self.findItems(selected_setting, Qt.MatchExactly)
        if len(items) == 0:
            self.setCurrentRow(0)
        else:
            self.setCurrentItem(items[0])
        self.blockSignals(False)


class PickImageListWidget(QListWidget):

    files_dropped = pyqtSignal(object)

    def __init__(self, images_dir, parent=None):
        QListWidget.__init__(self, parent)
        self.images_dir = images_dir
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAcceptDrops(True)

    def populate(self, files):
        self.blockSignals(True)
        self.clear()
        self.files = list(cfg.TOKEN_COVERS) + [f for f in files if f not in cfg.TOKEN_COVERS]
        for image_name in self.files:
            if image_name in cfg.TOKEN_COVERS:
                file_path = image_name
            else:
                file_path = os.path.join(self.images_dir, image_name)
                if iswindows:
                    file_path = os.path.normpath(file_path)

            item = QListWidgetItem(image_name, self)
            item.setToolTip(file_path)
            self.addItem(item)
        self.blockSignals(False)

    def select_image_name(self, selected_file_path):
        self.blockSignals(True)
        selected_idx = 0
        if selected_file_path in self.files:
            selected_idx = self.files.index(selected_file_path)
        self.setCurrentRow(selected_idx)
        self.blockSignals(False)

    def selected_image_name(self):
        if self.currentRow() == -1:
            return None
        return self.files[self.currentRow()]

    def dragEnterEvent(self, event):
        md = event.mimeData()
        if dnd_has_extension(md, IMAGE_EXTENSIONS):
            event.acceptProposedAction()

    def dropEvent(self, event):
        event.setDropAction(qtDropActionCopyAction)
        md = event.mimeData()
        files, _y = dnd_get_files(md, IMAGE_EXTENSIONS)
        if files is not None:
            self.files_dropped.emit(files)
        event.accept()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()


class FieldOrderListWidget(QListWidget):

    itemChecked = pyqtSignal()
    itemMoved = pyqtSignal()

    def __init__(self, parent):
        QListWidget.__init__(self, parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.itemChanged.connect(self.handle_item_changed)

    def populate(self, field_list):
        self.blockSignals(True)
        self.clear()
        self.field_list = field_list
        for field in field_list:
            item = QListWidgetItem(field['name'], self)
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if field['display']:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.addItem(item)
        self.blockSignals(False)

    def handle_item_changed(self, item):
        checked = item.checkState() == Qt.Checked
        for field in self.field_list:
            if field['name'] == unicode(item.text()).strip():
                if checked != field['display']:
                    field['display'] = checked
                    self.itemChecked.emit()
                    break

    def move_field_up(self):
        row = self.currentRow()
        if row <= 0:
            return
        field = self.field_list.pop(row)
        self.field_list.insert(row-1, field)
        self.populate(self.field_list)
        self.setCurrentRow(row-1)
        self.itemMoved.emit()

    def move_field_down(self):
        row = self.currentRow()
        if row == -1 or row == len(self.field_list)-1:
            return
        field = self.field_list.pop(row)
        self.field_list.insert(row+1, field)
        self.populate(self.field_list)
        self.setCurrentRow(row+1)
        self.itemMoved.emit()


class FontFamilyModel(QAbstractListModel):

    def __init__(self, *args):
        QAbstractListModel.__init__(self, *args)
        from calibre.utils.fonts.scanner import font_scanner
        try:
            self.families = font_scanner.find_font_families()
        except:
            self.families = []
            print('WARNING: Could not load fonts')
            traceback.print_exc()
        # Restrict to Qt families as Qt tends to crash
        self.font = QFont('Arial' if iswindows else 'sansserif')

    def rowCount(self, *args):
        return len(self.families)

    def data(self, index, role):
        try:
            family = self.families[index.row()]
        except:
            traceback.print_exc()
            return None
        if role == Qt.DisplayRole:
            return family
        if role == Qt.FontRole:
            # If a user chooses some non standard font as the interface font,
            # rendering some font names causes Qt to crash, so return what is
            # hopefully a "safe" font
            return self.font
        return None

    def index_of(self, family):
        return self.families.index(family.strip())


class FontComboBox(QComboBox):
    def __init__(self, parent):
        QComboBox.__init__(self, parent)
        self.font_family_model = FontFamilyModel()
        self.setModel(self.font_family_model)

    def select_value(self, value):
        idx = self.findText(value) if value else -1
        self.setCurrentIndex(idx)

    def get_value(self):
        if self.currentIndex() < 0:
            return None
        return unicode(self.currentText()).strip()


class SavedSettingsTab(QWidget):

    settings_changed = pyqtSignal(object)
    changed = pyqtSignal()

    def __init__(self, parent_dialog):
        self.parent_dialog = parent_dialog
        QWidget.__init__(self)
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        self.is_saved = True

        self.saved_setting_groupbox = QGroupBox(_('Saved Settings:'))
        main_layout.addWidget(self.saved_setting_groupbox)
        saved_setting_layout = QHBoxLayout()
        self.saved_setting_groupbox.setLayout(saved_setting_layout)
        saved_setting_inner_layout = QVBoxLayout()
        saved_setting_layout.addLayout(saved_setting_inner_layout)
        self.saved_setting_list = PickSavedSettingListWidget()
        self.saved_setting_list.currentRowChanged.connect(self.saved_setting_changed)
        saved_setting_inner_layout.addWidget(self.saved_setting_list)

        self.autosave_checkbox = QCheckBox(_('Autosave settings'), self)
        self.autosave_checkbox.setToolTip(_('Do not prompt to save changes to a setting. Always save when\n'
                                            'switching to another setting, clicking OK or using Import/Export.'))
        saved_setting_inner_layout.addWidget(self.autosave_checkbox)

        saved_setting_button_layout = QVBoxLayout()
        saved_setting_layout.addLayout(saved_setting_button_layout)
        add_image_button = QToolButton()
        add_image_button.setToolTip(_('Add setting'))
        add_image_button.setIcon(get_icon('plus.png'))
        add_image_button.clicked.connect(self.add_setting)
        saved_setting_button_layout.addWidget(add_image_button)
        rename_setting_button = QToolButton()
        rename_setting_button.setToolTip(_('Rename setting'))
        rename_setting_button.setIcon(get_icon('images/rename.png'))
        rename_setting_button.clicked.connect(self.rename_setting)
        saved_setting_button_layout.addWidget(rename_setting_button)

        import_setting_button = QToolButton()
        import_setting_button.setToolTip(_('Import setting'))
        import_setting_button.setIcon(get_icon('images/import.png'))
        import_setting_button.clicked.connect(self.import_setting)
        saved_setting_button_layout.addWidget(import_setting_button)
        export_setting_button = QToolButton()
        export_setting_button.setToolTip(_('Export setting'))
        export_setting_button.setIcon(get_icon('images/export.png'))
        export_setting_button.clicked.connect(self.export_setting)
        saved_setting_button_layout.addWidget(export_setting_button)

        remove_image_button = QToolButton(self)
        remove_image_button.setToolTip(_('Delete setting from this list'))
        remove_image_button.setIcon(get_icon('list_remove.png'))
        remove_image_button.clicked.connect(self.remove_setting)
        saved_setting_button_layout.addWidget(remove_image_button)
        spacerItem1 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        saved_setting_button_layout.addItem(spacerItem1)

        main_layout.addSpacing(10)
        pick_image_groupbox = QGroupBox(_('Select Image:'))
        main_layout.addWidget(pick_image_groupbox)
        pick_image_layout = QHBoxLayout()
        pick_image_groupbox.setLayout(pick_image_layout)
        self.pick_image_list = PickImageListWidget(self.parent_dialog.images_dir)
        self.pick_image_list.currentRowChanged.connect(self.changed)
        self.pick_image_list.files_dropped.connect(self.image_files_dropped)
        pick_image_layout.addWidget(self.pick_image_list)
        pick_image_button_layout = QVBoxLayout()
        pick_image_layout.addLayout(pick_image_button_layout)
        add_image_button = QToolButton()
        add_image_button.setToolTip(_('Add image to this list'))
        add_image_button.setIcon(get_icon('plus.png'))
        add_image_button.clicked.connect(self.add_image)
        pick_image_button_layout.addWidget(add_image_button)
        rename_image_button = QToolButton()
        rename_image_button.setToolTip(_('Rename image'))
        rename_image_button.setIcon(get_icon('images/rename.png'))
        rename_image_button.clicked.connect(self.rename_image)
        pick_image_button_layout.addWidget(rename_image_button)
        remove_image_button = QToolButton(self)
        remove_image_button.setToolTip(_('Remove image from this list'))
        remove_image_button.setIcon(get_icon('list_remove.png'))
        remove_image_button.clicked.connect(self.remove_image)
        pick_image_button_layout.addWidget(remove_image_button)
        spacerItem2 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        pick_image_button_layout.addItem(spacerItem2)

    def update_saved_status(self, is_saved):
        if is_saved:
            self.saved_setting_groupbox.setTitle(_('Saved Settings:'))
        else:
            self.saved_setting_groupbox.setTitle(_('Saved Settings: (*unsaved changes)'))
        self.is_saved = is_saved

    def populate_settings_list(self, selected_setting):
        settings = cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]
        if selected_setting not in settings:
            selected_setting = cfg.KEY_DEFAULT
        self.saved_setting_list.populate(settings, selected_setting)

    def saved_setting_changed(self):
        selected_setting = self.saved_setting_list.selected_setting()
        self.check_for_setting_save()
        cfg.plugin_prefs[cfg.STORE_CURRENT] = selected_setting
        self.settings_changed.emit(selected_setting)

    def check_for_setting_save(self):
        if not self.is_saved:
            current_setting = self.parent_dialog.current
            current_setting_name = current_setting[cfg.KEY_NAME]
            save_changes = self.autosave_checkbox.isChecked()
            if not save_changes:
                d = UnsavedSettingsDialog(self.parent_dialog, current_setting_name)
                d.exec_()
                save_changes = d.result() == d.Accepted
            if save_changes:
                # Save the settings
                saved_settings = cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]
                saved_settings[current_setting_name] = copy.deepcopy(current_setting)
                cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS] = saved_settings

    def add_setting(self):
        new_setting_name = self.get_new_setting_name(_('Add new setting'))
        if not new_setting_name:
            return
        current_options = self.parent_dialog.current
        settings = cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]
        settings[new_setting_name] = copy.deepcopy(current_options)
        settings[new_setting_name][cfg.KEY_NAME] = new_setting_name
        cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS] = settings
        self.populate_settings_list(new_setting_name)
        self.saved_setting_changed()

    def get_new_setting_name(self, heading, default_name=''):
        new_setting_name, ok = QInputDialog.getText(self.parent_dialog, heading,
                            'Enter a unique name for this saved setting:', text=default_name)
        if not ok:
            # Operation cancelled
            return None
        new_setting_name = unicode(new_setting_name).strip()
        if len(new_setting_name) == 0:
            return None
        settings = cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]
        safe_setting_names = [name.lower() for name in settings.keys()]
        if new_setting_name.lower() in safe_setting_names:
            error_dialog(self.parent_dialog, _('Cannot add'),
                         _('The name you specified is not unique'), show=True)
            return None
        return new_setting_name

    def remove_setting(self):
        selected_setting = self.saved_setting_list.selected_setting()
        setting_name = selected_setting[cfg.KEY_NAME]
        if setting_name == cfg.KEY_DEFAULT:
            # Cannot delete the default setting
            return error_dialog(self.parent_dialog, _('Cannot remove'),
                                _('You cannot remove the default setting'), show=True)
        if not question_dialog(self.parent_dialog, _('Are you sure?'), '<p>'+
                _('Are you sure you want to remove the \'%s\' setting?')%setting_name,
                show_copy_button=False):
            return
        settings = cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]
        del settings[setting_name]
        cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS] = settings
        self.saved_setting_list.takeItem(self.saved_setting_list.currentRow())

    def rename_setting(self):
        selected_setting = self.saved_setting_list.selected_setting()
        setting_name = selected_setting[cfg.KEY_NAME]
        if setting_name == cfg.KEY_DEFAULT:
            # Cannot delete the default setting
            return error_dialog(self.parent_dialog, _('Cannot rename'),
                                _('You cannot rename the default setting'), show=True)
        new_setting_name, ok = QInputDialog.getText(self.parent_dialog, _('New setting name:'),
                                            _('New setting name:'), text=setting_name)
        new_setting_name = unicode(new_setting_name).strip()
        if not ok or new_setting_name.lower() == setting_name.lower():
            # Operation cancelled or user did not actually choose a new name
            return
        settings = cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]
        for setting in settings.keys():
            if setting.lower() == new_setting_name.lower():
                return error_dialog(self.parent_dialog, _('Setting exists'),
                        _('A saved setting already exists with this name.'), show=True)
        del settings[setting_name]
        selected_setting[cfg.KEY_NAME] = new_setting_name
        settings[new_setting_name] = selected_setting
        cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS] = settings
        if self.parent_dialog.current['name'] == setting_name:
            self.parent_dialog.current['name'] = new_setting_name
        self.populate_settings_list(new_setting_name)

    def import_setting(self):
        self.check_for_setting_save()
        archive_paths = self.pick_archive_names_to_import()
        if not archive_paths:
            return
        for archive_path in archive_paths:
            if iswindows:
                archive_path = os.path.normpath(archive_path)

            # Write the zip file contents into the plugin images directory
            images_dir = self.parent_dialog.images_dir
            if not os.path.exists(images_dir):
                os.makedirs(images_dir)
            with ZipFile(archive_path, 'r') as zf:
                contents = zf.namelist()
                if 'gc_setting.json' not in contents:
                    return error_dialog(self.parent_dialog, _('Import Failed'),
                                        _('This is not a valid Generate Cover export archive'), show=True)
                json_path = os.path.join(images_dir,'gc_setting.json')
                try:
                    # Write the json file out first so we can check the saved image settings
                    fs = os.path.join(images_dir, 'gc_setting.json')
                    with open(fs,'wb') as f:
                        f.write(zf.read('gc_setting.json'))

                    # Read the .JSON file to get the setting (migrating to latest schema if required)
                    archive_config = JSONConfig('resources/images/generate_cover/gc_setting')
                    setting_version = archive_config[cfg.STORE_SCHEMA_VERSION]
                    ## six.itervalues doesn't have a next() in Calibre's bundled version?
                    # setting = six.itervalues(archive_config[cfg.STORE_SAVED_SETTINGS]).next()
                    ## Whatever.  This is ugly, but it works for getting the 'first' value.
                    setting = [x for x in six.itervalues(archive_config[cfg.STORE_SAVED_SETTINGS])][0]
                    setting_name = setting[cfg.KEY_NAME]
                    setting = cfg.migrate_config_setting(setting_version, setting_name, setting)

                    # Ask the user for a unique setting name
                    new_setting_name = self.get_new_setting_name(_('Import setting'), setting_name)
                    if not new_setting_name:
                        return
                    setting[cfg.KEY_NAME] = new_setting_name

                    # Check whether we need to import an image (overwriting if necessary)
                    new_image_name = image_name = setting[cfg.KEY_IMAGE_FILE]
                    dest_file_path = None
                    if image_name not in cfg.TOKEN_COVERS:
                        # We have to import - only prompt the user if it won't conflict in naming
                        dest_file_path = self.confirm_add_image(image_name)
                        if not dest_file_path:
                            return None
                        new_image_name = os.path.basename(dest_file_path)
                        setting[cfg.KEY_IMAGE_FILE] = new_image_name
                        try:
                            with open(dest_file_path,'wb') as f:
                                f.write(zf.read(image_name))
                        except:
                            return error_dialog(self.parent_dialog, _('Cannot import'),
                                    _('Failed to copy image'), det_msg=traceback.format_exc(), show=True)

                    # No more user intervention required, go ahead with rest of the operation
                    settings = cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]
                    settings[new_setting_name] = copy.deepcopy(setting)
                    cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS] = settings
                    # Repopulate the list without changing the selected setting
                    selected_setting_name = self.saved_setting_list.selected_setting()[cfg.KEY_NAME]
                    selected_image_name = self.pick_image_list.selected_image_name()
                    self.populate_settings_list(selected_setting_name)
                    if new_image_name and new_image_name not in self.files:
                        self.files.append(new_image_name)
                        self.update_files(selected_image_name, emit_changed=False)
                finally:
                    if os.path.exists(json_path):
                        os.remove(json_path)

    def export_setting(self):
        self.check_for_setting_save()
        selected_setting = self.saved_setting_list.selected_setting()
        if selected_setting is None:
            return
        archive_path = self.pick_archive_name_to_export()
        if not archive_path:
            return
        if iswindows:
            archive_path = os.path.normpath(archive_path)

        images_dir = self.parent_dialog.images_dir
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)

        # Make a setting copy
        setting = copy.deepcopy(selected_setting)
        image_name = setting[cfg.KEY_IMAGE_FILE]
        image_path = None
        if image_name not in cfg.TOKEN_COVERS:
            image_path = os.path.join(images_dir, image_name)
            if iswindows:
                image_path = os.path.normpath(image_path)

        # Write our setting out to a json file, temporarily created in the images directory
        # before zipping and deleting afterwards
        export_settings = {}
        export_settings[setting[cfg.KEY_NAME]] = setting
        archive_config = JSONConfig('resources/images/generate_cover/gc_setting')
        archive_config.set(cfg.STORE_SAVED_SETTINGS, export_settings)
        archive_config.set(cfg.STORE_SCHEMA_VERSION, cfg.DEFAULT_SCHEMA_VERSION)

        json_path = os.path.join(images_dir, 'gc_setting.json')
        if iswindows:
            json_path = os.path.normpath(json_path)

        try:
            # Create the zip file archive
            with ZipFile(archive_path, 'w') as archive_zip:
                archive_zip.write(json_path, os.path.basename(json_path))
                if image_path is not None:
                    archive_zip.write(image_path, image_name)
            info_dialog(self.parent_dialog, _('Export completed'),
                        _('Cover setting exported to<br>%s') % archive_path,
                        show=True, show_copy_button=False)
        finally:
            if os.path.exists(json_path):
                os.remove(json_path)

    def pick_archive_names_to_import(self):
        archives = choose_files(self.parent_dialog, 'Generate Cover plugin:pick archive dialog',
                                _('Select setting file(s) to import'),
                             filters=[(_('GC Files'), ['zip'])], all_files=False, select_only_single_file=False)
        if not archives:
            return
        return archives

    def pick_archive_name_to_export(self):
        fd = FileDialog(name='gc archive dialog', title=_('Save setting as'), filters=[(_('GC Files'), ['zip'])],
                        parent=self, add_all_files_filter=False, mode=AnyFile)
        fd.setParent(None)
        if not fd.accepted:
            return None
        return fd.get_files()[0]

    def populate_image_files_list(self):
        files = cfg.plugin_prefs[cfg.STORE_FILES]
        valid_files = []
        for image_name in files:
            if image_name in cfg.TOKEN_COVERS:
                valid_files.append(image_name)
            else:
                file_path = os.path.join(self.parent_dialog.images_dir, image_name)
                if os.path.exists(file_path):
                    valid_files.append(image_name)
                else:
                    self.remove_file_from_saved_settings(image_name)
        self.files = valid_files
        cfg.plugin_prefs[cfg.STORE_FILES] = self.files
        self.pick_image_list.populate(valid_files)

    def rename_image(self):
        selected_name = self.pick_image_list.selected_image_name()
        if selected_name in cfg.TOKEN_COVERS:
            return error_dialog(self.parent_dialog, _('Cannot rename'),
                _('You cannot rename this image'), show=True)
        current_path = os.path.join(self.parent_dialog.images_dir, selected_name)
        new_name, ok = QInputDialog.getText(self.parent_dialog, _('New image name:'),
                                            _('New image name:'), text=selected_name)
        new_name = unicode(new_name).strip()
        # Add back the extension if the user omitted it
        ext = os.path.splitext(selected_name)[1]
        if not new_name.endswith(ext):
            new_name += ext
        if not ok or new_name == selected_name:
            # Operation cancelled or user did not actually choose a new name
            return
        dest_path = os.path.join(self.parent_dialog.images_dir, new_name)
        if iswindows:
            dest_path = os.path.normpath(dest_path)
        if os.path.exists(dest_path):
            if iswindows and (new_name.lower() == selected_name.lower()):
                # On windows we will get a false positive if only changing case
                pass
            else:
                return error_dialog(self.parent_dialog, _('File exists'),
                        _('An image already exists with this name.'), det_msg=dest_path, show=True)
        try:
            os.rename(current_path, dest_path)
        except:
            return error_dialog(self.parent_dialog, _('Cannot rename'),
                    _('Failed to rename image'), det_msg=traceback.format_exc(), show=True)

        self.remove_file_from_saved_settings(selected_name, new_name)
        self.files.remove(selected_name)
        self.files.append(new_name)
        self.update_files(new_name)

    def add_image(self):
        files = choose_images(self.parent_dialog, 'Generate Cover plugin:choose image dialog',
                              _('Add cover images'), select_only_single_file=False)
        if not files or not files[0]:
            return
        dest_names = []
        for image_path in files:
            file_path = os.path.abspath(image_path)
            dest_name = self.handle_add_image(file_path)
            dest_names.append(dest_name)
        if dest_names:
            self.update_files(dest_names[0])

    def remove_image(self):
        selected_name = self.pick_image_list.selected_image_name()
        if selected_name in cfg.TOKEN_COVERS:
            return error_dialog(self.parent_dialog, _('Cannot remove'),
                _('You cannot remove this image'), show=True)

        if not question_dialog(self.parent_dialog, _('Are you sure?'), '<p>'+
                _('Are you sure you want to delete the image: %s')%selected_name,
                show_copy_button=False):
            return

        self.files.remove(selected_name)
        cfg.plugin_prefs[cfg.STORE_FILES] = self.files

        image_path = os.path.join(self.parent_dialog.images_dir, selected_name)
        if iswindows:
            image_path = os.path.normpath(image_path)
        if not os.access(image_path, os.W_OK):
            error_dialog(self.parent_dialog, _('Cannot write'),
                   _('You do not have permission to delete the file'), det_msg=image_path, show=True)
        else:
            try:
                os.remove(image_path)
            except:
                traceback.print_exc()
        self.remove_file_from_saved_settings(selected_name)
        self.update_files(self.files[0])

    def handle_add_image(self, file_path):
        if iswindows:
            file_path = os.path.normpath(file_path)
        if not os.access(file_path, os.R_OK):
            error_dialog(self.parent_dialog, _('Cannot read'),
                   _('You do not have permission to read the file.'), det_msg=file_path, show=True)
            return None

        image_name = os.path.basename(file_path)
        dest_file_path = self.confirm_add_image(image_name)
        if not dest_file_path:
            return None

        try:
            shutil.copyfile(file_path, dest_file_path)
        except:
            return error_dialog(self.parent_dialog, _('Cannot copy'),
                    _('Failed to copy image'), det_msg=traceback.format_exc(), show=True)

        image_name = os.path.basename(dest_file_path)
        if image_name not in self.files:
            self.files.append(image_name)
        return image_name

    def confirm_add_image(self, image_name):
        dest_file_path = os.path.join(self.parent_dialog.images_dir, image_name)
        if iswindows:
            dest_file_path = os.path.normpath(dest_file_path)
        while True:
            if os.path.exists(dest_file_path):
                if not question_dialog(self.parent_dialog, _('Overwrite existing'), '<p>'+
                        _('An image file already exists with this name. Do you want to overwrite it?'),
                        show_copy_button=False):
                    # Since user is not overwriting, offer chance for a new name for the image
                    new_image_name, ok = QInputDialog.getText(self.parent_dialog, _('Enter image name'),
                                        _('Enter a unique name for this image:'), text=image_name)
                    if not ok:
                        # Operation cancelled
                        return None
                    new_image_name = unicode(new_image_name).strip()
                    if len(new_image_name) == 0:
                        return None
                    dest_file_path = os.path.join(self.parent_dialog.images_dir, new_image_name)
                    if iswindows:
                        dest_file_path = os.path.normpath(dest_file_path)
                    continue

                if not os.access(dest_file_path, os.W_OK):
                    error_dialog(self.parent_dialog, _('Cannot write'),
                           _('You do not have permission to overwrite the file'), det_msg=dest_file_path, show=True)
                    return None
            # If we got to here we are good to go
            return dest_file_path

    def update_files(self, selected_name, emit_changed=True):
        self.files = sorted(self.files, key=lambda k: k.lower())
        cfg.plugin_prefs[cfg.STORE_FILES] = self.files
        self.pick_image_list.populate(self.files)
        self.pick_image_list.select_image_name(selected_name)
        if emit_changed:
            self.changed.emit()

    def remove_file_from_saved_settings(self, removed_file, new_image_file=None):
        # Iterate through all the saved settings and any using this image need
        # to be updated to just use the library image.
        if not new_image_file:
            new_image_file = cfg.TOKEN_DEFAULT_COVER
        saved_settings = cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]
        for value in saved_settings.values():
            if value[cfg.KEY_IMAGE_FILE] == removed_file:
                value[cfg.KEY_IMAGE_FILE] = new_image_file
        cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS] = saved_settings

    def image_files_dropped(self, dropped_files):
        first_dropped_name = None
        for dropped_file in dropped_files:
            dest_name = self.handle_add_image(dropped_file)
            if dest_name and not first_dropped_name:
                first_dropped_name = dest_name
        if first_dropped_name:
            self.update_files(first_dropped_name)



DIC_name_font = [
    ('Title', _('Title')),
    ('Author', _('Author')),
    ('Series', _('Series')),
    ('Custom', _('Custom')),
]
DIC_name_color = [
    ('Background', _('Background')),
    ('Border', _('Border')),
    ('Fill', _('Fill')),
    ('Stroke', _('Stroke')),
]

class FontsTab(QWidget):

    changed = pyqtSignal()

    def __init__(self, parent_dialog):
        self.parent_dialog = parent_dialog
        QWidget.__init__(self)
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        fonts_groupbox = QGroupBox(_('Fonts:'))
        main_layout.addWidget(fonts_groupbox)
        fonts_layout = QVBoxLayout()
        fonts_groupbox.setLayout(fonts_layout)
        fonts_grid_layout = QGridLayout()
        fonts_layout.addLayout(fonts_grid_layout)
        row = 0
        for name, display_name in DIC_name_font:
            font_label = QLabel(display_name+':', self)
            font_label.setToolTip(_('Select a font and specify a size in pixels.\n'
                                    'If font set to \'Default\', uses the tweak value from\n'
                                    '\'generate_cover_title_font\' if present.'))
            fonts_grid_layout.addWidget(font_label, row, 0, 1, 1)
            font_combo = FontComboBox(self)
            setattr(self, '_font' + name, font_combo)
            fonts_grid_layout.addWidget(font_combo, row, 1, 1, 2)
            size_spin = QSpinBox(self)
            size_spin.setRange(10, 1000)
            size_spin.setSingleStep(2)
            setattr(self, '_fontSize' + name, size_spin)
            size_spin.valueChanged[int].connect(self.changed)
            fonts_grid_layout.addWidget(size_spin, row, 3, 1, 1)
            # Create the toolbutton menu for alignment
            align_btn = self._create_align_button(name)
            fonts_grid_layout.addWidget(align_btn, row, 4, 1, 1)
            row += 1

        self.fonts_linked_checkbox = QCheckBox(_('Use the same font family for all text'))
        self.fonts_linked_checkbox.setToolTip(_('When checked, the same font family is used for all text content on the cover'))
        self.fonts_linked_checkbox.stateChanged[int].connect(self.fonts_linked_changed)
        getattr(self, '_fontTitle').currentIndexChanged.connect(self.title_font_changed)
        getattr(self, '_fontAuthor').currentIndexChanged.connect(self.changed)
        getattr(self, '_fontSeries').currentIndexChanged.connect(self.changed)
        getattr(self, '_fontCustom').currentIndexChanged.connect(self.changed)
        fonts_layout.addWidget(self.fonts_linked_checkbox)
        self.fonts_reduced_checkbox = QCheckBox(_('Auto-reduce font size to fit on one line'))
        self.fonts_reduced_checkbox.setToolTip(_('When checked, the font size will be used as a maximum size.\n'
                                                 'A reduced size will be used where needed to fit text on one line.'))
        self.fonts_reduced_checkbox.stateChanged[int].connect(self.changed)
        fonts_layout.addWidget(self.fonts_reduced_checkbox)

        main_layout.addSpacing(10)
        colors_groupbox = QGroupBox(_('Colors:'))
        main_layout.addWidget(colors_groupbox)
        colors_layout = QVBoxLayout()
        colors_groupbox.setLayout(colors_layout)
        colors_grid_layout = QGridLayout()
        colors_layout.addLayout(colors_grid_layout)
        row = 0

        for name, display_name in DIC_name_color:
            setattr(self, '_tclabel' + name, QLabel(display_name+':', self))
            colors_grid_layout.addWidget(getattr(self, '_tclabel' + name), row, 0, 1, 1)
            color_ledit = ReadOnlyLineEdit('', self)
            setattr(self, '_color' + name, color_ledit)
            colors_grid_layout.addWidget(color_ledit, row, 1, 1, 1)
            clear_color_button = QToolButton(self)
            clear_color_button.setIcon(QIcon(I('trash.png')))
            clear_color_button.setToolTip(_('Reset %s color') % display_name.lower())
            clear_color_button.clicked.connect(partial(self.reset_color, color_ledit, name))
            setattr(self, '_clearColor' + name, clear_color_button)
            colors_grid_layout.addWidget(clear_color_button, row, 2, 1, 1)
            select_button = QPushButton('...', self)
            select_button.setToolTip(_('Select a %s color') % display_name.lower())
            select_button.clicked.connect(partial(self.pick_color, color_ledit))
            setattr(self, '_selectColor' + name, select_button)
            fm = select_button.fontMetrics()
            select_button.setFixedWidth(fm.width('...') + 10)
            colors_grid_layout.addWidget(select_button, row, 3, 1, 1)
            row += 1

        self.apply_stroke_checkbox = QCheckBox(_('Apply'))
        self.apply_stroke_checkbox.setToolTip(_('When checked, stroke color is drawn around text'))
        self.apply_stroke_checkbox.stateChanged[int].connect(self.changed)
        self.apply_stroke_checkbox.setVisible(False)
        for x in '_color _clearColor _selectColor _tclabel'.split():
            getattr(self, x + 'Stroke').setVisible(False)
        colors_grid_layout.addWidget(self.apply_stroke_checkbox, row-1, 4, 1, 1)
        main_layout.insertStretch(-1)

    def _create_align_button(self, display_name):
        button = QToolButton()
        button.setIcon(QIcon(I('format-justify-center.png')))
        menu = QMenu(button)
        ac = menu.addAction(QIcon(I('format-justify-left.png')), _('Left aligned'))
        ac.triggered.connect(partial(self.change_alignment, button, display_name, 'left'))
        ac = menu.addAction(QIcon(I('format-justify-center.png')), _('Centered'))
        ac.triggered.connect(partial(self.change_alignment, button, display_name, 'center'))
        ac = menu.addAction(QIcon(I('format-justify-right.png')), _('Right aligned'))
        ac.triggered.connect(partial(self.change_alignment, button, display_name, 'right'))
        button.setMenu(menu)
        button.setPopupMode(QToolButton.InstantPopup)
        setattr(self, '_fontAlign' + display_name, button)
        setattr(self, '_fontAlignValue' + display_name, 'center')
        return button

    def change_alignment(self, button, display_name, new_value):
        setattr(self, '_fontAlignValue' + display_name, new_value)
        if new_value == 'left':
            button.setIcon(QIcon(I('format-justify-left.png')))
        elif new_value == 'center':
            button.setIcon(QIcon(I('format-justify-center.png')))
        else:
            button.setIcon(QIcon(I('format-justify-right.png')))
        self.changed.emit()

    def reset_color(self, color_ledit, display_name):
        saved_setting = self.parent_dialog.get_saved_setting()
        colors = saved_setting[cfg.KEY_COLORS]
        default_color = colors[display_name.lower()]
        color_ledit.setText(default_color)
        self.changed.emit()

    def pick_color(self, color_ledit):
        color = QColor(unicode(color_ledit.text()))
        picked_color = QColorDialog.getColor(color, self)
        if picked_color.isValid():
            color_ledit.setText(picked_color.name())
            self.changed.emit()

    def title_font_changed(self):
        if self.fonts_linked_checkbox.isChecked():
            self.set_other_fonts_linked_to_title_font_combo()
        self.changed.emit()

    def fonts_linked_changed(self, state):
        getattr(self, '_fontAuthor').setEnabled(True)
        getattr(self, '_fontSeries').setEnabled(True)
        getattr(self, '_fontCustom').setEnabled(True)
        if state == Qt.Checked:
            self.set_other_fonts_linked_to_title_font_combo()
            getattr(self, '_fontAuthor').setEnabled(False)
            getattr(self, '_fontSeries').setEnabled(False)
            getattr(self, '_fontCustom').setEnabled(False)
        self.changed.emit()

    def set_other_fonts_linked_to_title_font_combo(self):
        title_font = getattr(self, '_fontTitle').get_value()
        getattr(self, '_fontAuthor').blockSignals(True)
        getattr(self, '_fontSeries').blockSignals(True)
        getattr(self, '_fontCustom').blockSignals(True)
        getattr(self, '_fontAuthor').select_value(title_font)
        getattr(self, '_fontSeries').select_value(title_font)
        getattr(self, '_fontCustom').select_value(title_font)
        getattr(self, '_fontAuthor').blockSignals(False)
        getattr(self, '_fontSeries').blockSignals(False)
        getattr(self, '_fontCustom').blockSignals(False)


class DimensionsTab(QWidget):

    changed = pyqtSignal()

    def __init__(self, parent_dialog):
        self.parent_dialog = parent_dialog
        QWidget.__init__(self)
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        size_groupbox = QGroupBox(_('Size:'), self)
        main_layout.addWidget(size_groupbox)
        size_layout = QGridLayout()
        size_groupbox.setLayout(size_layout)
        cover_width_label = QLabel(_('Cover width:'), self)
        cover_width_label.setToolTip(_('The width in pixels of the output .jpg file'))
        size_layout.addWidget(cover_width_label, 0, 0, 1, 1)
        self.width_spin = QSpinBox(self)
        self.width_spin.setRange(100, 5000)
        self.width_spin.valueChanged[int].connect(self.changed)
        size_layout.addWidget(self.width_spin, 0, 1, 1, 1)
        cover_height_label = QLabel(_('Cover height:'), self)
        cover_height_label.setToolTip(_('The height in pixels of the output .jpg file'))
        size_layout.addWidget(cover_height_label, 0, 2, 1, 1)
        self.height_spin = QSpinBox(self)
        self.height_spin.setRange(100, 5000)
        self.height_spin.valueChanged[int].connect(self.changed)
        size_layout.addWidget(self.height_spin, 0, 3, 1, 1)
        self.background_image_checkbox = QCheckBox(_('Stretch image to use as cover background'), self)
        self.background_image_checkbox.setToolTip(_('Check this to overlay text on the image background.\n'
                                                    'Uncheck this to place text around the image.'))
        self.background_image_checkbox.stateChanged.connect(self.image_resize_changed)
        size_layout.addWidget(self.background_image_checkbox, 1, 0, 1, 4)
        self.resize_to_image_checkbox = QCheckBox(_('Resize cover dimensions to match background image'), self)
        self.resize_to_image_checkbox.setToolTip(_('Check this to automatically resize the cover based on\n'
                                                   'the dimensions of the currently chosen background image'))
        self.resize_to_image_checkbox.stateChanged.connect(self.resize_dimensions_changed)
        size_layout.addWidget(self.resize_to_image_checkbox, 2, 0, 1, 4)
        self.resize_image_to_fit_checkbox = QCheckBox(_('Resize image to scale up if smaller than available area'), self)
        self.resize_image_to_fit_checkbox.setToolTip(_('Check this to automatically resize the cover image to fit the\n'
                                                       'the maximum area available if it is too small'))
        self.resize_image_to_fit_checkbox.stateChanged.connect(self.image_resize_changed)
        size_layout.addWidget(self.resize_image_to_fit_checkbox, 3, 0, 1, 4)

        main_layout.addSpacing(10)
        margins_groupbox = QGroupBox(_('Margins:'), self)
        main_layout.addWidget(margins_groupbox)
        margins_layout = QGridLayout()
        margins_groupbox.setLayout(margins_layout)

        top_margin_label = QLabel(_('Top margin:'), self)
        top_margin_label.setToolTip(_('The margin in pixels from the top of the cover\n'
                                      'to the first content'))
        margins_layout.addWidget(top_margin_label, 1, 0, 1, 1)
        self.top_margin_spin = QSpinBox(self)
        self.top_margin_spin.setRange(0, 5000)
        self.top_margin_spin.valueChanged[int].connect(self.changed)
        margins_layout.addWidget(self.top_margin_spin, 1, 1, 1, 1)

        bottom_margin_label = QLabel(_('Bottom margin:'), self)
        bottom_margin_label.setToolTip(_('The margin in pixels from the bottom of the cover\n'
                                         'to the last content'))
        margins_layout.addWidget(bottom_margin_label, 1, 2, 1, 1)
        self.bottom_margin_spin = QSpinBox(self)
        self.bottom_margin_spin.setRange(0, 5000)
        self.bottom_margin_spin.valueChanged[int].connect(self.changed)
        margins_layout.addWidget(self.bottom_margin_spin, 1, 3, 1, 1)

        left_margin_label = QLabel(_('Left margin:'), self)
        left_margin_label.setToolTip(_('The minimum margin in pixels from the left of the cover\n'
                                       'to the text content'))
        margins_layout.addWidget(left_margin_label, 2, 0, 1, 1)
        self.left_margin_spin = QSpinBox(self)
        self.left_margin_spin.setRange(0, 5000)
        self.left_margin_spin.valueChanged[int].connect(self.changed)
        margins_layout.addWidget(self.left_margin_spin, 2, 1, 1, 1)

        right_margin_label = QLabel(_('Right margin:'), self)
        right_margin_label.setToolTip(_('The minimum margin in pixels from the right of the cover\n'
                                        'to the text content'))
        margins_layout.addWidget(right_margin_label, 2, 2, 1, 1)
        self.right_margin_spin = QSpinBox(self)
        self.right_margin_spin.setRange(0, 5000)
        self.right_margin_spin.valueChanged[int].connect(self.changed)
        margins_layout.addWidget(self.right_margin_spin, 2, 3, 1, 1)

        text_padding_label = QLabel(_('Text padding:'), self)
        text_padding_label.setToolTip(_('The spacing in pixels between successive lines of text'))
        margins_layout.addWidget(text_padding_label, 3, 0, 1, 1)
        self.text_margin_spin = QSpinBox(self)
        self.text_margin_spin.setRange(0, 5000)
        self.text_margin_spin.valueChanged[int].connect(self.changed)
        margins_layout.addWidget(self.text_margin_spin, 3, 1, 1, 1)

        image_padding_label = QLabel(_('Image padding:'), self)
        image_padding_label.setToolTip(_('The spacing in pixels between the image and text\n'
                                         'placed above and below it'))
        margins_layout.addWidget(image_padding_label, 3, 2, 1, 1)

        self.image_margin_spin = QSpinBox(self)
        self.image_margin_spin.setRange(0, 5000)
        self.image_margin_spin.valueChanged[int].connect(self.changed)
        margins_layout.addWidget(self.image_margin_spin, 3, 3, 1, 1)

        main_layout.addSpacing(10)
        borders_groupbox = QGroupBox(_('Border Widths:'), self)
        main_layout.addWidget(borders_groupbox)
        borders_layout = QGridLayout()
        borders_groupbox.setLayout(borders_layout)
        cover_border_label = QLabel(_('Cover border:'), self)
        cover_border_label.setToolTip(_('The width in pixels of a border around the edge\n'
                                        'of the cover. Specify 0 for no border'))
        borders_layout.addWidget(cover_border_label, 4, 0, 1, 1)
        self.cover_border_width_spin = QSpinBox(self)
        self.cover_border_width_spin.setRange(0, 99)
        self.cover_border_width_spin.valueChanged[int].connect(self.changed)
        borders_layout.addWidget(self.cover_border_width_spin, 4, 1, 1, 1)
        image_border_label = QLabel(_('Image border:'), self)
        image_border_label.setToolTip(_('The width in pixels of a border around the edge\n'
                                        'of the image. Specify 0 for no border'))
        borders_layout.addWidget(image_border_label, 4, 2, 1, 1)
        self.image_border_width_spin = QSpinBox(self)
        self.image_border_width_spin.setRange(0, 99)
        self.image_border_width_spin.valueChanged[int].connect(self.changed)
        borders_layout.addWidget(self.image_border_width_spin, 4, 3, 1, 1)
        main_layout.insertStretch(-1)
        self.image_resize_changed()

    def image_resize_changed(self):
        self.background_image_checkbox.setEnabled(not self.resize_image_to_fit_checkbox.isChecked())
        if self.background_image_checkbox.isChecked() and not self.background_image_checkbox.isEnabled():
            self.background_image_checkbox.setChecked(False)
        self.resize_image_to_fit_checkbox.setEnabled(not self.background_image_checkbox.isChecked() and not self.resize_to_image_checkbox.isChecked())
        if self.resize_image_to_fit_checkbox.isChecked() and not self.resize_image_to_fit_checkbox.isEnabled():
            self.resize_image_to_fit_checkbox.setChecked(False)
        self.resize_to_image_checkbox.setEnabled(self.background_image_checkbox.isChecked() and not self.resize_image_to_fit_checkbox.isChecked())
        if self.resize_to_image_checkbox.isChecked() and not self.resize_to_image_checkbox.isEnabled():
            self.resize_image_to_fit_checkbox.setChecked(False)
        self.changed.emit()

    def resize_dimensions_changed(self):
        self.width_spin.setEnabled(not self.resize_to_image_checkbox.isChecked())
        self.height_spin.setEnabled(not self.resize_to_image_checkbox.isChecked())
        self.image_resize_changed()
        self.changed.emit()


class ContentsTab(QWidget):

    changed = pyqtSignal()

    def __init__(self, parent_dialog):
        self.parent_dialog = parent_dialog
        QWidget.__init__(self)
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        content_groupbox = QGroupBox(_('Field Order:'), self)
        content_groupbox.setToolTip(_('Alter the order of items on the cover and\n'
                                      'whether they are displayed using the checkbox'))
        main_layout.addWidget(content_groupbox)
        field_layout = QHBoxLayout()
        content_groupbox.setLayout(field_layout)
        self.field_order_list = FieldOrderListWidget(self)
        self.field_order_list.itemChecked.connect(self.changed)
        self.field_order_list.itemMoved.connect(self.changed)
        self.field_order_list.setMinimumHeight(90)
        self.field_order_list.setMaximumHeight(100)
        field_layout.addWidget(self.field_order_list)
        field_button_layout = QVBoxLayout()
        field_layout.addLayout(field_button_layout)
        move_up_button = QToolButton(self)
        move_up_button.setToolTip(_('Move field up'))
        move_up_button.setIcon(get_icon('arrow-up.png'))
        move_up_button.clicked.connect(self.field_order_list.move_field_up)
        field_button_layout.addWidget(move_up_button)
        spacerItem1 = QSpacerItem(20, 4, )
        field_button_layout.addItem(spacerItem1)
        move_down_button = QToolButton(self)
        move_down_button.setToolTip(_('Move field down'))
        move_down_button.setIcon(get_icon('arrow-down.png'))
        move_down_button.clicked.connect(self.field_order_list.move_field_down)
        field_button_layout.addWidget(move_down_button)

        main_layout.addSpacing(5)
        custom_groupbox = QGroupBox(_('Custom Text:'), self)
        main_layout.addWidget(custom_groupbox)
        custom_layout = QVBoxLayout()
        custom_groupbox.setLayout(custom_layout)
        self.custom_text_ledit = QTextEdit(self)
        self.custom_text_ledit.textChanged.connect(self.changed)
        custom_layout.addWidget(self.custom_text_ledit)

        main_layout.addSpacing(5)
        options_groupbox = QGroupBox(_('Other Options:'), self)
        main_layout.addWidget(options_groupbox)
        options_layout = QGridLayout()
        options_groupbox.setLayout(options_layout)
        self.swap_author_checkbox = QCheckBox(_('Swap author LN,FN to FN LN'), self)
        self.swap_author_checkbox.setToolTip(_('Use this option if your authors are stored as LN, FN\n'
                                               'but you prefer to see FN LN on the book cover'))
        self.swap_author_checkbox.stateChanged.connect(self.changed)
        options_layout.addWidget(self.swap_author_checkbox, 0, 0, 1, 2)
        self.series_label = QLabel(_('Series text:'), self)
        self.series_label.setToolTip(_('Change the way series information is displayed.\n'
                                       'Useful for non-English languages!'))
        options_layout.addWidget(self.series_label, 1, 0, 1, 1)
        self.series_text_ledit = QLineEdit(self)
        self.series_text_ledit.textChanged.connect(self.changed)
        options_layout.addWidget(self.series_text_ledit, 1, 1, 1, 1)

        main_layout.addSpacing(5)
        metadata_groupbox = QGroupBox(_('Metadata: (*not saved)'), self)
        metadata_groupbox.setToolTip(_('Optionally override the text in these fields for this book.\n'
                                       'These are not saved as part of the settings profile.\n'
                                       'This functionality is disabled if multiple books are selected.'))
        main_layout.addWidget(metadata_groupbox)
        metadata_layout = QGridLayout()
        metadata_groupbox.setLayout(metadata_layout)
        self.metadata_title_label = QLabel(_('Title:'), self)
        self.metadata_title_ledit = QLineEdit(self)
        self.metadata_title_ledit.textChanged.connect(self.changed)
        self.metadata_author_label = QLabel(_('Author:'), self)
        self.metadata_author_ledit = QLineEdit(self)
        self.metadata_author_ledit.textChanged.connect(self.changed)
        self.metadata_series_label = QLabel(_('Series:'), self)
        self.metadata_series_ledit = QLineEdit(self)
        self.metadata_series_ledit.textChanged.connect(self.changed)
        metadata_layout.addWidget(self.metadata_title_label, 0, 0, 1, 1)
        metadata_layout.addWidget(self.metadata_author_label, 1, 0, 1, 1)
        metadata_layout.addWidget(self.metadata_series_label, 2, 0, 1, 1)
        metadata_layout.addWidget(self.metadata_title_ledit, 0, 1, 1, 1)
        metadata_layout.addWidget(self.metadata_author_ledit, 1, 1, 1, 1)
        metadata_layout.addWidget(self.metadata_series_ledit, 2, 1, 1, 1)

        main_layout.insertStretch(-1)


class CoverOptionsDialog(SizePersistedDialog):

    def __init__(self, parent, images_dir, book, is_multiple_books):
        self.ia = parent
        self.gui = parent.gui
        SizePersistedDialog.__init__(self, self.gui, 'Generate Cover plugin:cover options dialog')
        self.book, self.images_dir = (book, images_dir)
        self.is_multiple_books = is_multiple_books
        self.current = cfg.plugin_prefs[cfg.STORE_CURRENT]

        self.block_updates = True
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(500)
        self._preview_timer.timeout.connect(self.display_preview)

        self.setWindowTitle(_('Cover Options'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'images/generate_cover.png', _('Generate Custom Cover'))
        layout.addLayout(title_layout)

        # Main content layout
        config_layout = QHBoxLayout()
        layout.addLayout(config_layout)

        tab_widget = QTabWidget(self)
        tab_widget.setMinimumWidth(350)
        config_layout.addWidget(tab_widget)

        # Tab page for choosing saved settings and image
        self.saved_settings_tab = SavedSettingsTab(self)
        self.saved_settings_tab.changed.connect(self.options_changed)
        self.saved_settings_tab.settings_changed.connect(self.saved_settings_changed)
        self.fonts_tab = FontsTab(self)
        self.fonts_tab.changed.connect(self.options_changed)
        self.dimensions_tab = DimensionsTab(self)
        self.dimensions_tab.changed.connect(self.options_changed)
        self.contents_tab = ContentsTab(self)
        self.contents_tab.changed.connect(self.options_changed)
        tab_widget.addTab(self.saved_settings_tab, _('Settings'))
        tab_widget.addTab(self.fonts_tab, _('Fonts'))
        tab_widget.addTab(self.dimensions_tab, _('Dimensions'))
        tab_widget.addTab(self.contents_tab, _('Contents'))

        config_layout.addSpacing(5)
        self.preview_cover = ImageView(self)
        config_layout.addWidget(self.preview_cover)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_clicked)
        button_box.rejected.connect(self.reject_clicked)
        self.reset_button = button_box.addButton(_(' Revert '), QDialogButtonBox.ResetRole)
        self.reset_button.setToolTip(_('Revert to your previous saved setting values'))
        self.reset_button.clicked.connect(self.revert_to_saved)
        self.save_setting_button = button_box.addButton(_(' Save '), QDialogButtonBox.ResetRole)
        self.save_setting_button.setToolTip(_('Overwrite your current saved setting'))
        self.save_setting_button.clicked.connect(self.persist_saved_setting)
        self.options_button = button_box.addButton(_(' Customize... '), QDialogButtonBox.ResetRole)
        self.options_button.setToolTip(_('Set general options for this plugin'))
        self.options_button.clicked.connect(self.show_configuration)
        self.help_button = button_box.addButton(' '+_('&Help'), QDialogButtonBox.ResetRole)
        self.help_button.setIcon(get_icon('help.png'))
        self.help_button.clicked.connect(cfg.show_help)
        layout.addWidget(button_box)

        self.saved_settings_tab.populate_image_files_list()
        self.saved_settings_tab.populate_settings_list(self.current.get(cfg.KEY_NAME, cfg.KEY_DEFAULT))
        if cfg.plugin_prefs[cfg.STORE_OTHER_OPTIONS].get(cfg.KEY_AUTOSAVE, False):
            self.saved_settings_tab.autosave_checkbox.setCheckState(Qt.Checked)
        else:
            self.saved_settings_tab.autosave_checkbox.setCheckState(Qt.Unchecked)

        self.apply_options_to_controls()
        self.block_updates = False
        self.display_preview()
        self.compare_current_with_saved()

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def __enter__(self, *args):
        return self

    def __exit__(self, *args):
        self.terminate()

    def save_preferences(self):
        other_options = copy.deepcopy(cfg.DEFAULT_OTHER_OPTIONS)
        other_options[cfg.KEY_AUTOSAVE] = self.saved_settings_tab.autosave_checkbox.isChecked()
        cfg.plugin_prefs[cfg.STORE_OTHER_OPTIONS] = other_options

    def accept_clicked(self):
        self.save_preferences()
        if not self.saved_settings_tab.is_saved:
            if self.saved_settings_tab.autosave_checkbox.isChecked():
                # With autosave turned on we will always save changes on OK clicked
                self.persist_saved_setting(prompt=False, update_display=False)
            else:
                # With autosave turned off we will ask user what to do with changes
                current_setting_name = self.current[cfg.KEY_NAME]
                d = UnsavedSettingsDialog(self, current_setting_name, allow_dont_save=True)
                d.exec_()
                if d.result() == d.Accepted:
                    if not d.is_deferred_save:
                        self.persist_saved_setting(prompt=False, update_display=False)
                elif d.result() == d.Rejected:
                    self.revert_to_saved(prompt=False, update_display=False)
        self.accept()

    def reject_clicked(self):
        self.save_preferences()
        if not self.saved_settings_tab.is_saved:
            # We will always automatically revert settings when Cancel is pressed
            # regardless of whether user has Autosave turned on or off.
            self.revert_to_saved(prompt=False, update_display=False)
        self.reject()

    def terminate(self):
        if hasattr(self, '_preview_timer') and self._preview_timer.isActive():
            self._preview_timer.stop()

    def saved_settings_changed(self, settings):
        if self.block_updates:
            return
        self.current = copy.deepcopy(settings)
        self.apply_options_to_controls()
        self.display_preview()
        self.update_display_for_saved_status(True)

    def revert_to_saved(self, prompt=True, update_display=True):
        setting_name = self.current[cfg.KEY_NAME]
        if prompt:
            if not question_dialog(self, _('Are you sure?'), '<p>'+
                    _('Revert to your previously saved values for \'%s\'?')%setting_name,
                    show_copy_button=False):
                return
        self.block_updates = True
        all_saved_settings = cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]
        saved_settings = all_saved_settings.get(setting_name, None)
        if saved_settings is None:
            saved_settings = all_saved_settings.get(cfg.KEY_DEFAULT)
        self.current = self.get_saved_setting()
        if update_display:
            self.apply_options_to_controls()
            self.options_changed()
        else:
            cfg.plugin_prefs[cfg.STORE_CURRENT] = self.current

    def persist_saved_setting(self, prompt=True, update_display=True):
        setting_name = self.current[cfg.KEY_NAME]
        if prompt:
            if not question_dialog(self, _('Are you sure?'), '<p>'+
                    _('Overwrite the \'%s\' setting with the current values?')%setting_name,
                    show_copy_button=False):
                return
        saved_settings = cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]
        saved_settings[setting_name] = copy.deepcopy(self.current)
        cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS] = saved_settings
        if update_display:
            self.update_display_for_saved_status(True)

    def get_saved_setting(self):
        # Get the saved setting version of whatever settings the current options are based on
        all_saved_settings = cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]
        saved_settings = all_saved_settings.get(self.current[cfg.KEY_NAME], None)
        if saved_settings is None:
            saved_settings = all_saved_settings.get(cfg.KEY_DEFAULT)
        return copy.deepcopy(saved_settings)

    def parse_series(self, val):
        if val:
            pat = re.compile(r'\[([.0-9]+)\]')
            match = pat.search(val)
            if match is not None:
                s_index = float(match.group(1))
                val = pat.sub('', val).strip()
            else:
                s_index = 1.0
            return val, s_index
        return None, None

    def apply_options_to_controls(self):
        self.block_updates = True

        selected_image_name = self.current.get(cfg.KEY_IMAGE_FILE, None)
        if selected_image_name is None:
            selected_image_name = cfg.TOKEN_DEFAULT_COVER
            self.current[cfg.KEY_IMAGE_FILE] = selected_image_name
        self.saved_settings_tab.pick_image_list.select_image_name(selected_image_name)

        self.contents_tab.field_order_list.populate(self.current[cfg.KEY_FIELD_ORDER])
        self.contents_tab.swap_author_checkbox.setChecked(self.current[cfg.KEY_SWAP_AUTHOR])
        self.contents_tab.custom_text_ledit.setText(self.current[cfg.KEY_CUSTOM_TEXT])
        self.contents_tab.series_text_ledit.setText(self.current.get(cfg.KEY_SERIES_TEXT, cfg.DEFAULT_SERIES_TEXT))

        self.contents_tab.metadata_title_label.setEnabled(not self.is_multiple_books)
        self.contents_tab.metadata_author_label.setEnabled(not self.is_multiple_books)
        self.contents_tab.metadata_series_label.setEnabled(not self.is_multiple_books)
        self.contents_tab.metadata_title_ledit.setEnabled(not self.is_multiple_books)
        self.contents_tab.metadata_author_ledit.setEnabled(not self.is_multiple_books)
        self.contents_tab.metadata_series_ledit.setEnabled(not self.is_multiple_books)
        if not self.is_multiple_books:
            options = {}
            options[cfg.KEY_SERIES_TEXT] = '{series} [{series_index}]'
            options[cfg.KEY_SWAP_AUTHOR] = False
            (title, author_string, series_string) = get_title_author_series(self.book, options)
            if title:
                self.contents_tab.metadata_title_ledit.setText(title)
            else:
                self.contents_tab.metadata_title_ledit.setText('')
            if author_string:
                self.contents_tab.metadata_author_ledit.setText(author_string)
            else:
                self.contents_tab.metadata_author_ledit.setText('')
            if series_string:
                self.contents_tab.metadata_series_ledit.setText(series_string)
            else:
                self.contents_tab.metadata_series_ledit.setText('')

        (width, height) = self.current[cfg.KEY_SIZE]
        self.dimensions_tab.width_spin.setValue(width)
        self.dimensions_tab.height_spin.setValue(height)
        self.dimensions_tab.background_image_checkbox.setChecked(self.current[cfg.KEY_BACKGROUND_IMAGE])
        self.dimensions_tab.resize_image_to_fit_checkbox.setChecked(self.current[cfg.KEY_RESIZE_IMAGE_TO_FIT])
        self.dimensions_tab.resize_to_image_checkbox.setChecked(self.current[cfg.KEY_RESIZE_TO_IMAGE])

        margins = self.current[cfg.KEY_MARGINS]
        self.dimensions_tab.top_margin_spin.setValue(margins['top'])
        self.dimensions_tab.bottom_margin_spin.setValue(margins['bottom'])
        self.dimensions_tab.left_margin_spin.setValue(margins['left'])
        self.dimensions_tab.right_margin_spin.setValue(margins['right'])
        self.dimensions_tab.image_margin_spin.setValue(margins['image'])
        self.dimensions_tab.text_margin_spin.setValue(margins['text'])

        borders = self.current[cfg.KEY_BORDERS]
        self.dimensions_tab.cover_border_width_spin.setValue(borders['coverBorder'])
        self.dimensions_tab.image_border_width_spin.setValue(borders['imageBorder'])

        fonts = self.current[cfg.KEY_FONTS]
        getattr(self.fonts_tab, '_fontAuthor').setEnabled(True)
        getattr(self.fonts_tab, '_fontSeries').setEnabled(True)
        for name, display_name in DIC_name_font:
            getattr(self.fonts_tab, '_font'+name).select_value(fonts[name.lower()]['name'])
            getattr(self.fonts_tab, '_fontSize'+name).setValue(fonts[name.lower()]['size'])
            button = getattr(self.fonts_tab, '_fontAlign'+name)
            self.fonts_tab.change_alignment(button, name, fonts[name.lower()]['align'])

        is_fonts_linked = self.current.get(cfg.KEY_FONTS_LINKED, False)
        self.fonts_tab.fonts_linked_checkbox.setChecked(is_fonts_linked)
        getattr(self.fonts_tab, '_fontAuthor').setEnabled(not is_fonts_linked)
        getattr(self.fonts_tab, '_fontSeries').setEnabled(not is_fonts_linked)
        self.fonts_tab.fonts_reduced_checkbox.setChecked(self.current.get(cfg.KEY_FONTS_AUTOREDUCED, False))

        colors = self.current[cfg.KEY_COLORS]
        for name, display_name in DIC_name_color:
            getattr(self.fonts_tab, '_color'+name).setText(colors[name.lower()])

        is_stroke_applied = self.current.get(cfg.KEY_COLOR_APPLY_STROKE, False)
        self.fonts_tab.apply_stroke_checkbox.setChecked(is_stroke_applied)

        self.block_updates = False

    def update_current_options(self):
        cfg.plugin_prefs[cfg.STORE_FILES] = self.saved_settings_tab.files
        self.current[cfg.KEY_IMAGE_FILE] = self.saved_settings_tab.pick_image_list.selected_image_name()

        self.current[cfg.KEY_SWAP_AUTHOR] = self.contents_tab.swap_author_checkbox.isChecked()
        self.current[cfg.KEY_CUSTOM_TEXT] = unicode(self.contents_tab.custom_text_ledit.toPlainText())
        self.current[cfg.KEY_SERIES_TEXT] = unicode(self.contents_tab.series_text_ledit.text()).strip()
        if not self.is_multiple_books:
            self.book.title = unicode(self.contents_tab.metadata_title_ledit.text())
            self.book.authors = string_to_authors(self.contents_tab.metadata_author_ledit.text())
            series_name, series_index = self.parse_series(unicode(self.contents_tab.metadata_series_ledit.text()))
            self.book.series = series_name
            self.book.series_index = series_index

        self.current[cfg.KEY_BACKGROUND_IMAGE] = self.dimensions_tab.background_image_checkbox.isChecked()
        self.current[cfg.KEY_RESIZE_IMAGE_TO_FIT] = self.dimensions_tab.resize_image_to_fit_checkbox.isChecked()
        self.current[cfg.KEY_RESIZE_TO_IMAGE] = self.dimensions_tab.resize_to_image_checkbox.isChecked()
        width = int(unicode(self.dimensions_tab.width_spin.value()).strip())
        height = int(unicode(self.dimensions_tab.height_spin.value()).strip())
        if self.current[cfg.KEY_BACKGROUND_IMAGE] and self.current[cfg.KEY_RESIZE_TO_IMAGE]:
            # We need to get the dimensions of this image and use those if they differ
            image_path = image_name = self.current[cfg.KEY_IMAGE_FILE]
            if image_name == cfg.TOKEN_CURRENT_COVER and hasattr(self.book, '_path_to_cover'):
                image_path = self.book._path_to_cover
            elif image_name == cfg.TOKEN_DEFAULT_COVER:
                image_path = I('library.png')
            else:
                image_path = os.path.join(self.images_dir, image_name)
                if iswindows:
                    image_path = os.path.normpath(image_path)
            new_width, new_height = get_image_size(image_path)
            if new_width != width or new_height != height:
                width = new_width
                height = new_height
                self.dimensions_tab.width_spin.setValue(width)
                self.dimensions_tab.height_spin.setValue(height)
        self.current[cfg.KEY_SIZE] = (width, height)

        top_mgn = int(unicode(self.dimensions_tab.top_margin_spin.value()).strip())
        bottom_mgn = int(unicode(self.dimensions_tab.bottom_margin_spin.value()).strip())
        left_mgn = int(unicode(self.dimensions_tab.left_margin_spin.value()).strip())
        right_mgn = int(unicode(self.dimensions_tab.right_margin_spin.value()).strip())
        image_mgn = int(unicode(self.dimensions_tab.image_margin_spin.value()).strip())
        text_mgn = int(unicode(self.dimensions_tab.text_margin_spin.value()).strip())
        self.current[cfg.KEY_MARGINS] = (top_mgn, bottom_mgn, left_mgn)
        self.current[cfg.KEY_MARGINS] = {'top':    top_mgn,
                                         'bottom': bottom_mgn,
                                         'left':   left_mgn,
                                         'right':  right_mgn,
                                         'image':  image_mgn,
                                         'text':   text_mgn}

        cover_border_width = int(unicode(self.dimensions_tab.cover_border_width_spin.value()).strip())
        image_border_width = int(unicode(self.dimensions_tab.image_border_width_spin.value()).strip())

        self.current[cfg.KEY_BORDERS] = {'coverBorder': cover_border_width,
                                         'imageBorder': image_border_width }

        border_color = unicode(getattr(self.fonts_tab, '_colorBorder').text()).strip()
        background_color = unicode(getattr(self.fonts_tab, '_colorBackground').text()).strip()
        is_stroke_applied = self.fonts_tab.apply_stroke_checkbox.isChecked()
        self.current[cfg.KEY_COLOR_APPLY_STROKE] = is_stroke_applied
        fill_color = unicode(getattr(self.fonts_tab, '_colorFill').text()).strip()
        stroke_color = unicode(getattr(self.fonts_tab, '_colorStroke').text()).strip()
        self.current[cfg.KEY_COLORS] = {'border':     border_color,
                                        'background': background_color,
                                        'fill':       fill_color,
                                        'stroke':     stroke_color }

        is_fonts_linked = self.fonts_tab.fonts_linked_checkbox.isChecked()
        self.current[cfg.KEY_FONTS_LINKED] = is_fonts_linked
        self.current[cfg.KEY_FONTS_AUTOREDUCED] = self.fonts_tab.fonts_reduced_checkbox.isChecked()
        title_font  = getattr(self.fonts_tab, '_fontTitle').get_value()
        author_font = getattr(self.fonts_tab, '_fontAuthor').get_value()
        series_font = getattr(self.fonts_tab, '_fontSeries').get_value()
        custom_font = getattr(self.fonts_tab, '_fontCustom').get_value()
        title_size  = int(unicode(getattr(self.fonts_tab, '_fontSizeTitle').text()).strip())
        author_size = int(unicode(getattr(self.fonts_tab, '_fontSizeAuthor').text()).strip())
        series_size = int(unicode(getattr(self.fonts_tab, '_fontSizeSeries').text()).strip())
        custom_size = int(unicode(getattr(self.fonts_tab, '_fontSizeCustom').text()).strip())
        title_align  = unicode(getattr(self.fonts_tab, '_fontAlignValueTitle')).strip()
        author_align = unicode(getattr(self.fonts_tab, '_fontAlignValueAuthor')).strip()
        series_align = unicode(getattr(self.fonts_tab, '_fontAlignValueSeries')).strip()
        custom_align = unicode(getattr(self.fonts_tab, '_fontAlignValueCustom')).strip()
        self.current[cfg.KEY_FONTS] = {
                    'title':  { 'name': title_font,  'size': title_size,  'align': title_align },
                    'author': { 'name': author_font, 'size': author_size, 'align': author_align },
                    'series': { 'name': series_font, 'size': series_size, 'align': series_align },
                    'custom': { 'name': custom_font, 'size': custom_size, 'align': custom_align } }
        cfg.plugin_prefs[cfg.STORE_CURRENT] = self.current

    def options_changed(self):
        if self.block_updates:
            return
        self.update_current_options()
        # Compare current with saved settings to see if changed.
        self.compare_current_with_saved()
        # Kick off a timer to refresh the preview image
        if self._preview_timer.isActive():
            self._preview_timer.stop()
        self._preview_timer.start()

    def display_preview(self):
        if self.saved_settings_tab.pick_image_list.selected_image_name():
            cover_data = generate_cover_for_book(self.book, db=self.gui.current_db.new_api)
            pix = QPixmap()
            pix.loadFromData(cover_data)
            self.preview_cover.setPixmap(pix)
        else:
            self.preview_cover.setPixmap(QPixmap(None))

    def compare_current_with_saved(self):
        saved_settings = cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]
        saved_setting = saved_settings.get(self.current[cfg.KEY_NAME], {})
        if saved_setting is None:
            return
        is_saved = self.compare_items(self.current, saved_setting)
        self.update_display_for_saved_status(is_saved)

    def update_display_for_saved_status(self, is_saved):
        self.saved_settings_tab.update_saved_status(is_saved)
        self.reset_button.setEnabled(not is_saved)
        self.save_setting_button.setEnabled(not is_saved)

    def compare_items(self, item1, item2):
        if item1 is None and item2 is None:
            return True
        elif item1 is None or item2 is None:
            return False
        typ = type(item1).__name__
        if typ == 'dict':
            diff = [key for key, val in six.iteritems(item1) if not self.compare_items(val, item2.get(key, None))]
            if len(diff) > 0:
                return False
        elif typ in ['tuple', 'list']:
            if typ == 'tuple':
                item1 = list(item1)
                item2 = list(item2)
            diff = [idx for idx, val in enumerate(item1) if not self.compare_items(val, item2[idx])]
            if len(diff) > 0:
                return False
        else: # bool, unicode, int
            if item1 != item2:
                return False
        return True

    def show_configuration(self):
        self.ia.interface_action_base_plugin.do_user_config(self.gui)
