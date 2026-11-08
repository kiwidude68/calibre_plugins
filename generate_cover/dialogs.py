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
                        QTimer, QTextEdit, QProgressDialog, QSize, QPoint, QListView,
                        QToolButton, QFileDialog, QPainter, QPen, QRect, QScrollArea,
                        QAbstractListModel, QFont, QFontDatabase, QSpacerItem, QSizePolicy)
except ImportError:
    from PyQt5.Qt import (Qt, QVBoxLayout, QLabel, QAbstractItemView, QCheckBox,
                        QGroupBox, QIcon, QPixmap, QListWidget, QListWidgetItem,
                        QDialog, QHBoxLayout, QDialogButtonBox, QPushButton,
                        QLineEdit, QGridLayout, QColorDialog, QColor, QSpinBox,
                        pyqtSignal, QComboBox, QTabWidget, QWidget, QInputDialog,
                        QTimer, QTextEdit, QProgressDialog, QSize, QPoint, QListView,
                        QToolButton, QFileDialog, QPainter, QPen, QRect, QScrollArea,
                        QAbstractListModel, QFont, QFontDatabase, QSpacerItem, QSizePolicy)

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
from calibre_plugins.generate_cover.common_widgets import ImageTitleLayout
from calibre_plugins.generate_cover.draw import (
    generate_cover_for_book, get_image_size, get_title_author_series)

try:
    AnyFile = QFileDialog.FileMode.AnyFile
except:
    AnyFile = QFileDialog.AnyFile

def update_custom_columns_if_required(db, mi):
    library_config = cfg.get_library_config(db)
    update_column = library_config.get(cfg.PREFS_KEY_UPDATE_COLUMN, '')
    update_value = library_config.get(cfg.PREFS_KEY_UPDATE_VALUE, '')
    custom_columns = db.field_metadata.custom_field_metadata()
    if update_column:
        if update_column != 'tags':
            if update_column not in custom_columns:
                # Custom column does not exist
                update_column = ''
                library_config[cfg.PREFS_KEY_UPDATE_COLUMN] = ''
                library_config[cfg.PREFS_KEY_UPDATE_VALUE] = ''
                cfg.set_library_config(db, library_config)
            else:
                update_col = custom_columns[update_column]
                update_column_type = update_col['datatype']
                update_label = db.field_metadata.key_to_label(update_column)
    if update_column and update_value:
        if update_column == 'tags':
            db.set_tags(mi.id, update_value.split(','), append=True)
        elif update_column_type == 'bool':
            new_value = update_value.lower() == 'y'
            db.set_custom(mi.id, new_value, label=update_label)
        elif update_column_type == 'text':
            if update_col['is_multiple']:
                db.set_custom_bulk_multiple([mi.id], add=[update_value], label=update_label)
            else:
                db.set_custom(mi.id, update_value, label=update_label)


class GenerateCoverProgressDialog(QProgressDialog):
    '''
    Progress dialog for generating multiple covers rather than displaying the status
    '''
    def __init__(self, gui, books, db, options):
        self.total_count = len(books)
        QProgressDialog.__init__(self, '', _('Cancel'), 0, self.total_count, gui)
        self.setWindowTitle(_('Generating %d covers')%self.total_count)
        self.setMinimumWidth(500)
        self.books, self.db, self.options = books, db, options
        self.gui = gui
        self.i = 0
        # QTimer workaround on Win 10 on first go for Win10/Qt6 users not displaying dialog properly.
        QTimer.singleShot(100, self.do_generate_cover)
        self.exec_()

    def do_generate_cover(self):
        if self.i >= self.total_count:
            return self.do_close()
        mi = self.books[self.i]

        self.setLabelText(_('Generating: ')+mi.title)
        cover_data = generate_cover_for_book(mi, options=self.options, db=self.db.new_api)
        self.db.set_cover(mi.id, cover_data)
        update_custom_columns_if_required(self.db, mi)

        self.i += 1
        self.setValue(self.i)
        QTimer.singleShot(0, self.do_generate_cover)

    def do_close(self):
        self.hide()
        self.gui = None


class UnsavedSettingsDialog(QDialog):

    def __init__(self, parent, setting_name):
        QDialog.__init__(self, parent)
        self.setWindowTitle(_('Unsaved Changes'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        layout.addWidget(QLabel(_('You have unsaved changes to the <b>%s</b> setting.<br>') % setting_name +
                                _('What do you want to do?'), self))
        # Dialog buttons
        button_box = QDialogButtonBox()
        self.discard_changes_button = button_box.addButton( ' '+_('Discard Changes')+' ', QDialogButtonBox.RejectRole)
        self.discard_changes_button.setToolTip(_('Revert unsaved changes'))
        self.discard_changes_button.clicked.connect(self.reject)
        self.save_setting_button = button_box.addButton( ' '+_('Save Changes')+' ', QDialogButtonBox.AcceptRole)
        self.save_setting_button.setToolTip(_('Overwrite current profile with these changes'))
        self.save_setting_button.clicked.connect(self.accept)
        layout.addWidget(button_box)

        self.resize(self.sizeHint())


class UnsavedSettingsGenerateDialog(QDialog):

    def __init__(self, parent, setting_name):
        QDialog.__init__(self, parent)
        self.setWindowTitle(_('Unsaved Changes'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        layout.addWidget(QLabel(_('You have unsaved changes to the <b>%s</b> setting.<br>') % setting_name +
                                _('What do you want to do?'), self))
        # Dialog buttons
        button_box = QDialogButtonBox()
        self.save_setting_button = button_box.addButton( ' '+_('Generate && Save')+' ', QDialogButtonBox.ActionRole)
        self.save_setting_button.setToolTip(_('Generate cover using these settings and save for future usage'))
        self.save_setting_button.clicked.connect(self.accept)
        self.discard_changes_button = button_box.addButton( ' '+_('Generate && Revert')+' ', QDialogButtonBox.ActionRole)
        self.discard_changes_button.setToolTip(_('Generate cover using these settings then discard them'))
        self.discard_changes_button.clicked.connect(self.on_dont_save_clicked)
        self.is_deferred_revert = False
        self.cancel_button = button_box.addButton( ' '+_('Cancel')+' ', QDialogButtonBox.RejectRole)
        self.cancel_button.setToolTip(_('Cancel action'))
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(button_box)

        self.resize(self.sizeHint())

    def on_dont_save_clicked(self):
        self.is_deferred_revert = True
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
        try:
            self.families = QFontDatabase.families()
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
        font_list = QListView(self)
        font_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        font_list.setUniformItemSizes(True)
        self.setView(font_list)
        row_height = max(font_list.sizeHintForRow(0), font_list.fontMetrics().height())
        font_list.setMaximumHeight(row_height * 12 + 2 * font_list.frameWidth())
        self.setMaxVisibleItems(12)

    def showPopup(self):
        QComboBox.showPopup(self)
        popup = self.view().window()
        screen = self.screen()
        if screen is None:
            return

        view = self.view()
        row_height = max(view.sizeHintForRow(0), view.fontMetrics().height())
        visible_rows = min(12, max(1, self.count()))
        popup_height = row_height * visible_rows + 2 * view.frameWidth() + 8
        popup_width = self.width()
        screen_rect = screen.availableGeometry()
        combo_top = self.mapToGlobal(QPoint(0, 0))
        popup_x = min(max(combo_top.x(), screen_rect.left()),
                      screen_rect.right() + 1 - popup_width)
        popup_y = combo_top.y() + self.height()
        if popup_y + popup_height > screen_rect.bottom() + 1:
            popup_y = combo_top.y() - popup_height
        popup_y = min(max(popup_y, screen_rect.top()),
                      screen_rect.bottom() + 1 - popup_height)
        popup.setMaximumHeight(popup_height)
        popup.setGeometry(popup_x, popup_y, popup_width, popup_height)

    def select_value(self, value):
        idx = self.findText(value) if value else -1
        self.setCurrentIndex(idx)

    def get_value(self):
        if self.currentIndex() < 0:
            return None
        return unicode(self.currentText()).strip()


class QFontWeightComboBox(QComboBox):

    def __init__(self, parent):
        QComboBox.__init__(self, parent)
        self.addItem(_('Light'), 'Light')
        self.addItem(_('Normal'), 'Normal')
        self.addItem(_('Demi Bold'), 'Demi Bold')
        self.addItem(_('Bold'), 'Bold')
        self.addItem(_('Black'), 'Black')

    def select_value(self, value):
        idx = self.findData(value) if value else -1
        self.setCurrentIndex(idx)

    def get_value(self):
        if self.currentIndex() < 0:
            return None
        return self.itemData(self.currentIndex())


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
                    archive_config = JSONConfig('plugins/Generate Cover/gc_setting')
                    setting_version = archive_config.get(cfg.STORE_SCHEMA_VERSION, 0)
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
        archive_config = JSONConfig('plugins/Generate Cover/gc_setting')
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
    ('Custom2', _('Custom 2')),
    ('Custom3', _('Custom 3')),
]
DIC_name_text_fill_color = [
    ('Title', _('Title')),
    ('Author', _('Author')),
    ('Series', _('Series')),
    ('Custom', _('Custom')),
    ('Custom2', _('Custom 2')),
    ('Custom3', _('Custom 3')),
]

class ColorsPanel(QGroupBox):

    changed = pyqtSignal()

    def __init__(self, parent_dialog, parent=None):
        self.parent_dialog = parent_dialog
        QGroupBox.__init__(self, _('Color:'), parent)
        colors_grid_layout = QGridLayout(self)
        colors_grid_layout.setColumnMinimumWidth(0, 80)

        row = 0
        self.fill_color_label = QLabel(_('Fill Color:'), self)
        self.fill_color_button = QPushButton(self)
        self.fill_color_button.setToolTip(_('Choose selected field fill color'))
        self.fill_color_button.clicked.connect(partial(self.pick_color, self.fill_color_button))
        self.reset_fill_color_button = QToolButton(self)
        self.reset_fill_color_button.setIcon(QIcon(I('trash.png')))
        self.reset_fill_color_button.setToolTip(_('Reset selected field fill color'))
        self.reset_fill_color_button.clicked.connect(self.reset_selected_fill_color)

        self.use_this_fill_color_checkbox = QCheckBox(_('Use this fill color for all text'), self)
        self.use_this_fill_color_checkbox.setToolTip(_('When checked, the current fill color is used for all text.\n'
                                                       'When unchecked, you can set a different fill color for each field.'))
        self.use_this_fill_color_checkbox.stateChanged[int].connect(self.same_fill_color_changed)
        colors_grid_layout.addWidget(self.fill_color_label, row, 0, 1, 1)
        colors_grid_layout.addWidget(self.fill_color_button, row, 1, 1, 1)
        colors_grid_layout.addWidget(self.reset_fill_color_button, row, 2, 1, 1)
        colors_grid_layout.addWidget(self.use_this_fill_color_checkbox, row, 3, 1, 1)
        colors_grid_layout.setColumnStretch(3, 1)

        row = 1
        self.element_backdrop_checkbox = QCheckBox(_('Backdrop:'), self)
        self.element_backdrop_checkbox.setToolTip(_('Optionally render a color backdrop for this element'))
        self.element_backdrop_checkbox.setStyleSheet('padding-top: 1px')
        self.element_backdrop_checkbox.stateChanged.connect(self.parent_dialog.element_options_changed)
        self.element_backdrop_color_button = QPushButton(self)
        self.element_backdrop_color_button.setToolTip(_('Choose this element\'s backdrop color, if applied'))
        self.element_backdrop_color_button.clicked.connect(self.parent_dialog.pick_element_backdrop_color)
        self.reset_backdrop_color_button = QToolButton(self)
        self.reset_backdrop_color_button.setIcon(QIcon(I('trash.png')))
        self.reset_backdrop_color_button.setToolTip(_('Reset selected field backdrop color'))
        self.reset_backdrop_color_button.clicked.connect(self.parent_dialog.reset_element_backdrop_color)
        self.backdrops_linked_checkbox = QCheckBox(_('Use this backdrop for all text'), self)
        self.backdrops_linked_checkbox.stateChanged.connect(self.parent_dialog.element_options_changed)
        colors_grid_layout.addWidget(self.element_backdrop_checkbox, row, 0, 1, 1)
        colors_grid_layout.addWidget(self.element_backdrop_color_button, row, 1, 1, 1)
        colors_grid_layout.addWidget(self.reset_backdrop_color_button, row, 2, 1, 1)
        colors_grid_layout.addWidget(self.backdrops_linked_checkbox, row, 3, 1, 1)

        row = 2
        backdrop_opacity_label = QLabel(_('Opacity:'), self)
        self.element_backdrop_opacity_spin = QSpinBox(self)
        self.element_backdrop_opacity_spin.setRange(0, 100)
        self.element_backdrop_opacity_spin.setSuffix('%')
        self.element_backdrop_opacity_spin.valueChanged[int].connect(self.parent_dialog.element_options_changed)
        self.element_backdrop_full_width_checkbox = QCheckBox(_('Full width or height'), self)
        self.element_backdrop_full_width_checkbox.setToolTip(_('When checked, the backdrop will extend to the full width of the cover (height if rotated).\n'
                                                              'When unchecked, the backdrop will only extend to the width or height of the text.'))
        self.element_backdrop_full_width_checkbox.stateChanged.connect(
            self.parent_dialog.element_options_changed)
        colors_grid_layout.addWidget(backdrop_opacity_label, row, 0, 1, 1)
        colors_grid_layout.addWidget(self.element_backdrop_opacity_spin, row, 1, 1, 1)
        colors_grid_layout.addWidget(self.element_backdrop_full_width_checkbox, row, 3, 1, 1)

        row = 3
        backdrop_options_layout = QVBoxLayout()
        colors_grid_layout.addLayout(backdrop_options_layout, row, 0, 1, 4)
        self.element_padding_spins = add_padding_controls(
            self, backdrop_options_layout, 5000,
            self.parent_dialog.element_options_changed)
        self.element_backdrop_color_button.setFixedWidth(
            self.element_padding_spins['top'].minimumWidth())
        self.element_backdrop_opacity_spin.setFixedWidth(
            self.element_padding_spins['top'].minimumWidth())

        self.colors_grid_layout = colors_grid_layout

    def update_selected_field(self, field_name):
        font_key = self.parent_dialog.font_key_for_field(field_name)
        is_enabled = font_key is not None
        self.fill_color_button.setEnabled(font_key is not None)
        self.reset_fill_color_button.setEnabled(is_enabled)
        if font_key is None:
            return
        colors = self.parent_dialog.current[cfg.KEY_COLORS]
        color_key = font_key + '_fill'
        self.fill_color_button.setProperty('color_key', color_key)
        self.set_color_swatch(self.fill_color_button, colors.get(color_key, '#000000'))

    def set_color_swatch(self, color_button, color):
        color_button.setProperty('color', color)
        color_button.setStyleSheet('background-color: %s;' % color)

    def reset_color(self, color_button, display_name):
        saved_setting = self.parent_dialog.get_saved_setting()
        self.set_color_swatch(color_button, saved_setting[cfg.KEY_COLORS].get(display_name.lower(), '#000000'))
        self.changed.emit()

    def reset_selected_fill_color(self):
        field_name = getattr(self.parent_dialog, '_selected_text_field', None)
        font_key = self.parent_dialog.font_key_for_field(field_name or '')
        if font_key is None:
            return
        colors = self.parent_dialog.get_saved_setting()[cfg.KEY_COLORS]
        self.set_color_swatch(
            self.fill_color_button, colors.get(font_key + '_fill', '#000000'))
        self.changed.emit()

    def pick_color(self, color_button):
        color = QColor(unicode(color_button.property('color') or '#000000'))
        picked_color = QColorDialog.getColor(color, self)
        if picked_color.isValid():
            self.set_color_swatch(color_button, picked_color.name())
            self.changed.emit()

    def same_fill_color_changed(self):
        is_checked = self.use_this_fill_color_checkbox.isChecked()
        if is_checked:
            field_name = self.parent_dialog._selected_text_field or ''
            font_key = self.parent_dialog.font_key_for_field(field_name)
            source_key = (font_key + '_fill') if font_key else 'title_fill'
            common_fill = self.parent_dialog.current[cfg.KEY_COLORS].get(source_key, '#000000')
            for name, _ in DIC_name_text_fill_color:
                self.parent_dialog.current[cfg.KEY_COLORS][name.lower() + '_fill'] = common_fill
            self.set_color_swatch(self.fill_color_button, common_fill)
        self.update_selected_field(self.parent_dialog._selected_text_field or '')
        self.changed.emit()

    def set_element_backdrop_color(self, color):
        self.element_backdrop_color = color
        self.element_backdrop_color_button.setStyleSheet('background-color: %s;' % color)

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
        size_layout.setColumnMinimumWidth(0, 80)
        size_layout.setColumnMinimumWidth(2, 60)
        size_groupbox.setLayout(size_layout)
        cover_width_label = QLabel(_('Cover width:'), self)
        cover_width_label.setToolTip(_('The width in pixels of the output .jpg file'))
        size_layout.addWidget(cover_width_label, 0, 0, 1, 1)
        self.width_spin = QSpinBox(self)
        self.width_spin.setRange(100, 5000)
        self.width_spin.valueChanged[int].connect(self.changed)
        size_layout.addWidget(self.width_spin, 0, 1, 1, 1)
        cover_height_label = QLabel(_('Height:'), self)
        cover_height_label.setToolTip(_('The height in pixels of the output .jpg file'))
        size_layout.addWidget(cover_height_label, 0, 2, 1, 1)
        self.height_spin = QSpinBox(self)
        self.height_spin.setRange(100, 5000)
        self.height_spin.valueChanged[int].connect(self.changed)
        size_layout.addWidget(self.height_spin, 0, 3, 1, 1)
        size_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        size_layout.addItem(size_spacer, 1, 4, 1, 1)

        background_color_label = QLabel(_('Background:'), self)
        size_layout.addWidget(background_color_label, 1, 0, 1, 1)
        self.background_color_button = QPushButton(self)
        self.background_color_button.setToolTip(_('Choose the background color'))
        self.background_color_button.clicked.connect(self.parent_dialog.pick_background_color)
        size_layout.addWidget(self.background_color_button, 1, 1, 1, 1)
        self.reset_background_color_button = QToolButton(self)
        self.reset_background_color_button.setIcon(QIcon(I('trash.png')))
        self.reset_background_color_button.setToolTip(_('Reset background color'))
        self.reset_background_color_button.clicked.connect(self.parent_dialog.reset_background_color)
        size_layout.addWidget(self.reset_background_color_button, 1, 2, 1, 1)
        self.resize_to_image_checkbox = QCheckBox(_('Resize cover dimensions to match background image'), self)
        self.resize_to_image_checkbox.setToolTip(_('Check this to automatically resize the cover based on\n'
                                                   'the dimensions of the currently chosen background image'))
        self.resize_to_image_checkbox.stateChanged.connect(self.resize_dimensions_changed)
        size_layout.addWidget(self.resize_to_image_checkbox, 2, 0, 1, 5)
        self.resize_image_to_fit_checkbox = QCheckBox(_('Resize image to scale up if smaller than available area'), self)
        self.resize_image_to_fit_checkbox.setToolTip(_('Check this to automatically resize the cover image to fit the\n'
                                                       'the maximum area available if it is too small'))
        self.resize_image_to_fit_checkbox.stateChanged.connect(self.image_resize_changed)
        size_layout.addWidget(self.resize_image_to_fit_checkbox, 3, 0, 1, 5)

        main_layout.addSpacing(10)
        margins_groupbox = QGroupBox(_('Margins:'), self)
        main_layout.addWidget(margins_groupbox)
        margins_layout = QGridLayout()
        margins_layout.setColumnMinimumWidth(0, 80)
        margins_layout.setColumnMinimumWidth(2, 60)
        margins_groupbox.setLayout(margins_layout)

        top_margin_label = QLabel(_('Top:'), self)
        top_margin_label.setToolTip(_('The margin in pixels from the top of the cover\n'
                                      'to the first content'))
        margins_layout.addWidget(top_margin_label, 1, 0, 1, 1)
        self.top_margin_spin = QSpinBox(self)
        self.top_margin_spin.setRange(0, 5000)
        self.top_margin_spin.valueChanged[int].connect(self.changed)
        margins_layout.addWidget(self.top_margin_spin, 1, 1, 1, 1)

        bottom_margin_label = QLabel(_('Bottom:'), self)
        bottom_margin_label.setToolTip(_('The margin in pixels from the bottom of the cover\n'
                                         'to the last content'))
        margins_layout.addWidget(bottom_margin_label, 1, 2, 1, 1)
        self.bottom_margin_spin = QSpinBox(self)
        self.bottom_margin_spin.setRange(0, 5000)
        self.bottom_margin_spin.valueChanged[int].connect(self.changed)
        margins_layout.addWidget(self.bottom_margin_spin, 1, 3, 1, 1)
        margins_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        margins_layout.addItem(margins_spacer, 1, 4, 1, 1)

        left_margin_label = QLabel(_('Left:'), self)
        left_margin_label.setToolTip(_('The minimum margin in pixels from the left of the cover\n'
                                       'to the text content'))
        margins_layout.addWidget(left_margin_label, 2, 0, 1, 1)
        self.left_margin_spin = QSpinBox(self)
        self.left_margin_spin.setRange(0, 5000)
        self.left_margin_spin.valueChanged[int].connect(self.changed)
        margins_layout.addWidget(self.left_margin_spin, 2, 1, 1, 1)

        right_margin_label = QLabel(_('Right:'), self)
        right_margin_label.setToolTip(_('The minimum margin in pixels from the right of the cover\n'
                                        'to the text content'))
        margins_layout.addWidget(right_margin_label, 2, 2, 1, 1)
        self.right_margin_spin = QSpinBox(self)
        self.right_margin_spin.setRange(0, 5000)
        self.right_margin_spin.valueChanged[int].connect(self.changed)
        margins_layout.addWidget(self.right_margin_spin, 2, 3, 1, 1)

        main_layout.addSpacing(10)
        borders_groupbox = QGroupBox(_('Border:'), self)
        main_layout.addWidget(borders_groupbox)
        borders_layout = QGridLayout()
        borders_layout.setColumnMinimumWidth(0, 80)
        borders_groupbox.setLayout(borders_layout)

        cover_border_label = QLabel(_('Border width:'), self)
        cover_border_label.setToolTip(_('The width in pixels of a border around the edge\n'
                                        'of the cover. Specify 0 for no border'))
        borders_layout.addWidget(cover_border_label, 0, 0, 1, 1)
        self.cover_border_width_spin = QSpinBox(self)
        self.cover_border_width_spin.setRange(0, 99)
        self.cover_border_width_spin.valueChanged[int].connect(self.changed)
        borders_layout.addWidget(self.cover_border_width_spin, 0, 1, 1, 1)

        border_color_label = QLabel(_('Color:'), self)
        borders_layout.addWidget(border_color_label, 1, 0, 1, 1)
        self.border_color_button = QPushButton(self)
        self.border_color_button.setToolTip(_('Choose the border color'))
        self.border_color_button.clicked.connect(self.parent_dialog.pick_border_color)
        borders_layout.addWidget(self.border_color_button, 1, 1, 1, 1)
        self.reset_border_color_button = QToolButton(self)
        self.reset_border_color_button.setIcon(QIcon(I('trash.png')))
        self.reset_border_color_button.setToolTip(_('Reset border color'))
        self.reset_border_color_button.clicked.connect(self.parent_dialog.reset_border_color)
        borders_layout.addWidget(self.reset_border_color_button, 1, 2, 1, 1)
        borders_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        borders_layout.addItem(borders_spacer, 1, 3, 2, 1)

        dimension_spins = (self.width_spin, self.height_spin,
                           self.top_margin_spin, self.bottom_margin_spin,
                           self.left_margin_spin, self.right_margin_spin,
                           self.cover_border_width_spin)
        for spin in dimension_spins:
            spin.setSuffix(' px')
        control_width = max(spin.sizeHint().width() for spin in dimension_spins)
        for spin in dimension_spins:
            spin.setFixedWidth(control_width)
        self.background_color_button.setFixedWidth(control_width)
        self.border_color_button.setFixedWidth(control_width)
        main_layout.insertStretch(-1)
        self.image_resize_changed()

    def set_border_color(self, color):
        self.border_color = color
        self.border_color_button.setProperty('color', color)
        self.border_color_button.setStyleSheet('background-color: %s;' % color)

    def set_background_color(self, color):
        self.background_color = color
        self.background_color_button.setProperty('color', color)
        self.background_color_button.setStyleSheet('background-color: %s;' % color)

    def image_resize_changed(self):
        background_image_checkbox = self.parent_dialog.contents_tab.background_image_checkbox
        background_image_checkbox.setEnabled(not self.resize_image_to_fit_checkbox.isChecked())
        if background_image_checkbox.isChecked() and not background_image_checkbox.isEnabled():
            background_image_checkbox.setChecked(False)
        self.resize_image_to_fit_checkbox.setEnabled(not background_image_checkbox.isChecked() and not self.resize_to_image_checkbox.isChecked())
        if self.resize_image_to_fit_checkbox.isChecked() and not self.resize_image_to_fit_checkbox.isEnabled():
            self.resize_image_to_fit_checkbox.setChecked(False)
        self.resize_to_image_checkbox.setEnabled(background_image_checkbox.isChecked() and not self.resize_image_to_fit_checkbox.isChecked())
        if self.resize_to_image_checkbox.isChecked() and not self.resize_to_image_checkbox.isEnabled():
            self.resize_image_to_fit_checkbox.setChecked(False)
        self.changed.emit()

    def resize_dimensions_changed(self):
        self.width_spin.setEnabled(not self.resize_to_image_checkbox.isChecked())
        self.height_spin.setEnabled(not self.resize_to_image_checkbox.isChecked())
        self.image_resize_changed()
        self.changed.emit()


def add_padding_controls(parent, layout, max_value, on_change, grid_position=None):
    padding_container = QVBoxLayout()
    if grid_position is None:
        layout.addLayout(padding_container)
    else:
        layout.addLayout(padding_container, *grid_position)
    padding_layout = QGridLayout()
    padding_layout.setColumnMinimumWidth(0, 80)
    padding_layout.setColumnMinimumWidth(2, 80)
    padding_container.addLayout(padding_layout)
    controls = {}
    side_labels = {
        'top': _('Padding Top:'), 'bottom': _('Bottom:'),
        'left': _('Padding Left:'), 'right': _('Right:'),
    }
    for row, sides in enumerate((('top', 'bottom'), ('left', 'right'))):
        for pair, side in enumerate(sides):
            label_column = pair * 2
            padding_layout.addWidget(
                QLabel(side_labels[side], parent), row, label_column)
            spin = QSpinBox(parent)
            spin.setRange(0, max_value)
            spin.setSuffix(' px')
            spin.setMinimumWidth(75)
            spin.valueChanged[int].connect(on_change)
            padding_layout.addWidget(spin, row, label_column + 1)
            controls[side] = spin
    padding_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
    padding_layout.addItem(padding_spacer, 0, 4, 1, 1)
    return controls


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
        self.field_order_list.currentRowChanged.connect(self.parent_dialog.element_selection_changed)
        self.field_order_list.setFixedHeight(84)
        field_layout.addWidget(self.field_order_list)
        field_button_layout = QVBoxLayout()
        field_layout.addLayout(field_button_layout)
        move_up_button = QToolButton(self)
        move_up_button.setToolTip(_('Move field up'))
        move_up_button.setIcon(get_icon('arrow-up.png'))
        move_up_button.clicked.connect(self.field_order_list.move_field_up)
        field_button_layout.addWidget(move_up_button, 0, Qt.AlignTop)
        field_button_layout.addStretch(1)
        move_down_button = QToolButton(self)
        move_down_button.setToolTip(_('Move field down'))
        move_down_button.setIcon(get_icon('arrow-down.png'))
        move_down_button.clicked.connect(self.field_order_list.move_field_down)
        field_button_layout.addWidget(move_down_button, 0, Qt.AlignBottom)

        # Image options are only displayed when the Image field is selected in the field order list
        self.image_options_groupbox = QGroupBox(_('Image:'), self)
        main_layout.addWidget(self.image_options_groupbox)
        image_options_layout = QVBoxLayout()
        self.image_options_groupbox.setLayout(image_options_layout)
        self.background_image_checkbox = QCheckBox(_('Stretch image to use as cover background'), self)
        self.background_image_checkbox.setToolTip(_('Check this to overlay text on the image background.\n'
                                'Uncheck this to place text around the image.'))
        image_options_layout.addWidget(self.background_image_checkbox)
        self.image_padding_spins = add_padding_controls(
            self, image_options_layout, 5000, self.parent_dialog.element_options_changed)
        self.image_options_groupbox.setVisible(False)

        image_border_groupbox = QGroupBox(_('Border:'), self)
        self.image_border_groupbox = image_border_groupbox
        main_layout.addWidget(image_border_groupbox)
        image_border_layout = QGridLayout()
        image_border_layout.setColumnMinimumWidth(0, 80)
        image_border_groupbox.setLayout(image_border_layout)
        image_border_label = QLabel(_('Image border:'), self)
        image_border_label.setToolTip(
            _('The width in pixels of a border around the edge of the image'))
        image_border_layout.addWidget(image_border_label, 0, 0, 1, 1)
        self.image_border_width_spin = QSpinBox(self)
        self.image_border_width_spin.setRange(0, 99)
        self.image_border_width_spin.setMinimumWidth(75)
        self.image_border_width_spin.setSuffix(' px')
        self.image_border_width_spin.valueChanged[int].connect(self.changed)
        image_border_layout.addWidget(self.image_border_width_spin, 0, 1, 1, 1)
        image_border_color_label = QLabel(_('Color:'), self)
        image_border_layout.addWidget(image_border_color_label, 1, 0, 1, 1)
        self.image_border_color_button = QPushButton(self)
        self.image_border_color_button.setMinimumWidth(75)
        self.image_border_color_button.setToolTip(_('Choose the image border color (if it is not stretched to the cover edge)'))
        self.image_border_color_button.clicked.connect(
            self.parent_dialog.pick_image_border_color)
        image_border_layout.addWidget(self.image_border_color_button, 1, 1, 1, 1)
        self.reset_image_border_color_button = QToolButton(self)
        self.reset_image_border_color_button.setIcon(QIcon(I('trash.png')))
        self.reset_image_border_color_button.setToolTip(_('Reset image border color'))
        self.reset_image_border_color_button.clicked.connect(
            self.parent_dialog.reset_image_border_color)
        image_border_layout.addWidget(self.reset_image_border_color_button, 1, 2, 1, 1)
        image_borders_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        image_border_layout.addItem(image_borders_spacer, 1, 3, 1, 1)
        self.image_border_groupbox.setVisible(False)

        self.image_mode_spacer = QWidget(self)
        self.image_mode_spacer.setVisible(False)
        main_layout.addWidget(self.image_mode_spacer)

        # All these options are only displayed when a text field is selected in the field order list
        fonts_groupbox = QGroupBox(_('Font:'), self)
        self.fonts_groupbox = fonts_groupbox
        main_layout.addWidget(fonts_groupbox)
        fonts_layout = QVBoxLayout()
        fonts_groupbox.setLayout(fonts_layout)
        font_row_layout = QHBoxLayout()
        fonts_layout.addLayout(font_row_layout)
        self.font_field_label = QLabel(_('Font:'), self)
        self.font_field_label.setMinimumWidth(80)
        font_row_layout.addWidget(self.font_field_label)
        self.font_family_combo = FontComboBox(self)
        self.font_family_combo.setToolTip(_('Choose the font family for the selected field'))
        self.font_family_combo.currentIndexChanged.connect(self.parent_dialog.font_options_changed)
        font_row_layout.addWidget(self.font_family_combo, 1)
        self.font_size_spin = QSpinBox(self)
        self.font_size_spin.setRange(10, 1000)
        self.font_size_spin.setSingleStep(2)
        self.font_size_spin.setSuffix(' px')
        self.font_size_spin.setMinimumWidth(40)
        self.font_size_spin.setToolTip(_('Font size in pixels'))
        self.font_size_spin.valueChanged[int].connect(self.parent_dialog.font_options_changed)
        font_row_layout.addWidget(self.font_size_spin)

        font_options_layout = QGridLayout()
        font_options_layout.setColumnMinimumWidth(0, 90)
        fonts_layout.addLayout(font_options_layout)
        self.fonts_linked_checkbox = QCheckBox(_('Use this font family for all text'), self)
        self.fonts_linked_checkbox.setToolTip(_('When checked, this font family is used for all text content on the cover'))
        self.fonts_linked_checkbox.stateChanged.connect(self.parent_dialog.fonts_linked_changed)
        font_options_layout.addWidget(self.fonts_linked_checkbox, 0, 1, 1, 2)
        self.fonts_reduced_checkbox = QCheckBox(_('Auto-reduce font size to fit on one line'), self)
        self.fonts_reduced_checkbox.setToolTip(_('When checked, this font size will be used as a maximum size.\n'
                             'A reduced size will be used where needed to fit text on one line.'))
        self.fonts_reduced_checkbox.stateChanged.connect(self.changed)
        font_options_layout.addWidget(self.fonts_reduced_checkbox, 1, 1, 1, 2)

        font_style_layout = QHBoxLayout()
        font_style_label = QLabel(_('Style:'), self)
        font_style_label.setMinimumWidth(80)
        font_style_layout.addWidget(font_style_label)
        self.font_alignment_combo = QComboBox(self)
        self.font_alignment_combo.setMinimumWidth(75)
        self.font_alignment_combo.addItem(_('Left'), 'left')
        self.font_alignment_combo.addItem(_('Centre'), 'center')
        self.font_alignment_combo.addItem(_('Right'), 'right')
        self.font_alignment_combo.currentIndexChanged.connect(self.parent_dialog.font_options_changed)

        font_style_layout.addWidget(self.font_alignment_combo)
        self.font_weight_combo = QFontWeightComboBox(self)
        self.font_weight_combo.setMinimumWidth(75)
        font_style_layout.addWidget(self.font_weight_combo)
        self.font_weight_combo.currentIndexChanged.connect(self.parent_dialog.font_options_changed)
        self.font_italic_checkbox = QCheckBox(_('Italic'), self)
        self.font_italic_checkbox.stateChanged.connect(self.parent_dialog.font_options_changed)
        font_style_layout.addWidget(self.font_italic_checkbox)
        self.font_underline_checkbox = QCheckBox(_('Underline'), self)
        self.font_underline_checkbox.stateChanged.connect(self.parent_dialog.font_options_changed)
        font_style_layout.addWidget(self.font_underline_checkbox)
        font_style_layout.addStretch(1)
        fonts_layout.addLayout(font_style_layout)

        font_rotation_layout = QHBoxLayout()
        font_rotation_label = QLabel(_('Rotation:'), self)
        font_rotation_label.setMinimumWidth(80)
        font_rotation_layout.addWidget(font_rotation_label)
        self.font_rotation_combo = QComboBox(self)
        self.font_rotation_combo.setMinimumWidth(75)
        for angle in (0, 90, 270):
            # TRANSLATORS: Text rotation angle in degrees (0, 90, or 270), not temperature.
            # Keep %d; use a suitable local degree symbol or abbreviation.
            self.font_rotation_combo.addItem(_(u'%d\u00b0') % angle, angle)
        self.font_rotation_combo.setToolTip(_('Rotate the selected text field'))
        self.font_rotation_combo.currentIndexChanged.connect(
            self.parent_dialog.font_options_changed)
        font_rotation_layout.addWidget(self.font_rotation_combo)
        placement_label = QLabel(_('Placement:'), self)
        placement_label.setMinimumWidth(80)
        font_rotation_layout.addWidget(placement_label)
        self.font_rotation_side_combo = QComboBox(self)
        self.font_rotation_side_combo.setMinimumWidth(75)
        self.font_rotation_side_combo.addItem(_('Left'), 'left')
        self.font_rotation_side_combo.addItem(_('Right'), 'right')
        self.font_rotation_side_combo.setToolTip(_('Place vertical text along the left or right edge'))
        self.font_rotation_side_combo.currentIndexChanged.connect(
            self.parent_dialog.font_options_changed)
        font_rotation_layout.addWidget(self.font_rotation_side_combo)
        font_rotation_layout.addStretch(1)
        fonts_layout.addLayout(font_rotation_layout)
        self.font_text_padding_spins = add_padding_controls(
            self, fonts_layout, 5000, self.parent_dialog.font_options_changed)

        self.colors_panel = ColorsPanel(self.parent_dialog, self)
        self.colors_panel.changed.connect(self.changed)
        main_layout.addWidget(self.colors_panel)

        main_layout.addSpacing(5)
        options_groupbox = QGroupBox(_('Data:'), self)
        self.other_options_groupbox = options_groupbox
        main_layout.addWidget(options_groupbox)
        options_layout = QGridLayout()
        options_groupbox.setLayout(options_layout)
        self.field_text_label = QLabel(_('Text:'), self)
        self.field_text_label.setFixedWidth(
            self.field_text_label.fontMetrics().width('Custom Text 3:') + 8)
        self.field_text_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.field_text_label.setIndent(0)
        self.field_text_label.setStyleSheet("""padding-top:4px""")
        options_layout.addWidget(self.field_text_label, 0, 0, 1, 1)
        self.field_text_edit = QTextEdit(self)
        self.field_text_edit.textChanged.connect(self.changed)
        self.field_text_edit.setMinimumHeight(25)
        options_layout.addWidget(self.field_text_edit, 0, 1, 1, 1)
        options_layout.setRowStretch(0, 10)
        self.swap_author_checkbox = QCheckBox(_('Swap author LN,FN to FN LN'), self)
        self.swap_author_checkbox.setToolTip(_('Use this option if your authors are stored as LN, FN\n'
                                               'but you prefer to see FN LN on the book cover'))
        self.swap_author_checkbox.stateChanged.connect(self.changed)
        options_layout.addWidget(self.swap_author_checkbox, 1, 0, 1, 2)
        self.series_label = QLabel(_('Series text:'), self)
        self.series_label.setToolTip(_('Change the way series information is displayed.\n'
                                       'Useful for non-English languages!'))
        options_layout.addWidget(self.series_label, 2, 0, 1, 1)
        self.series_text_ledit = QLineEdit(self)
        self.series_text_ledit.textChanged.connect(self.changed)
        options_layout.addWidget(self.series_text_ledit, 2, 1, 1, 1)

        text_groups = (
            self.fonts_groupbox,
            self.colors_panel,
            self.other_options_groupbox,
        )
        self.image_mode_spacer.setFixedWidth(
            max(group.sizeHint().width() for group in text_groups))

        main_layout.insertStretch(-1)

    def set_image_mode(self, enabled):
        text_groups = (
            self.fonts_groupbox,
            self.colors_panel,
            self.other_options_groupbox,
        )
        if enabled:
            text_height = sum(group.sizeHint().height() for group in text_groups)
            image_height = (self.image_options_groupbox.sizeHint().height() +
                            self.image_border_groupbox.sizeHint().height())
            spacer_height = text_height - image_height
            spacer_height = text_height - image_height + max(0, self.layout().spacing())
            self.image_mode_spacer.setFixedHeight(max(0, spacer_height))
        else:
            self.image_mode_spacer.setFixedHeight(0)
        self.image_options_groupbox.setVisible(enabled)
        self.image_border_groupbox.setVisible(enabled)
        self.image_mode_spacer.setVisible(enabled)
        for group in text_groups:
            group.setVisible(not enabled)

    def set_image_border_color(self, color):
        self.image_border_color = color
        self.image_border_color_button.setProperty('color', color)
        self.image_border_color_button.setStyleSheet('background-color: %s;' % color)

class CoverOptionsDialog(SizePersistedDialog):

    def __init__(self, parent, images_dir, book, is_multiple_books):
        self.ia = parent
        self.gui = parent.gui
        SizePersistedDialog.__init__(self, self.gui, 'Generate Cover plugin:cover options dialog')
        self.book, self.images_dir = (book, images_dir)
        self.is_multiple_books = is_multiple_books
        self.current = cfg.plugin_prefs[cfg.STORE_CURRENT]
        self.is_deferred_revert = False
        self.setMinimumHeight(500)
        self.setMinimumWidth(650)

        self.block_updates = True
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(500)
        self._preview_timer.timeout.connect(self.display_preview)

        self.setWindowTitle(_('Cover Options'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        layout.setSizeConstraint(layout.SetNoConstraint)
        title_layout = ImageTitleLayout(self, 'images/generate_cover.png', _('Generate Custom Cover'))
        layout.addLayout(title_layout)

        # Main content layout
        config_layout = QHBoxLayout()
        layout.addLayout(config_layout)

        tab_widget = QTabWidget(self)
        tab_widget.setMinimumWidth(250)

        # Tab page for choosing saved settings and image
        self.saved_settings_tab = SavedSettingsTab(self)
        self.saved_settings_tab.changed.connect(self.options_changed)
        self.saved_settings_tab.settings_changed.connect(self.saved_settings_changed)

        self.contents_tab = ContentsTab(self)
        self.contents_tab.changed.connect(self.options_changed)
        self.dimensions_tab = DimensionsTab(self)
        self.dimensions_tab.changed.connect(self.options_changed)

        # The contents tab is very tall vertically, so we will make it scrollable to avoid the dialog being too tall for the screen.
        contents_scroll_area = QScrollArea(self)
        contents_scroll_area.setWidgetResizable(True)
        try:
            contents_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # Qt6 compatibility
        except AttributeError:
            contents_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Qt5 compatibility
        self.contents_tab.background_image_checkbox.stateChanged.connect(
            self.dimensions_tab.image_resize_changed)
        contents_scroll_area.setWidget(self.contents_tab)

        tab_widget.addTab(self.saved_settings_tab, _('Settings'))
        tab_widget.addTab(self.dimensions_tab, _('Dimensions'))
        tab_widget.addTab(contents_scroll_area, _('Contents'))
        tab_widget.setFixedWidth(max(250, tab_widget.sizeHint().width()))
        config_layout.addWidget(tab_widget, 0)

        config_layout.addSpacing(5)
        self.preview_cover = ImageView(self)
        config_layout.addWidget(self.preview_cover, 1)

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
                d = UnsavedSettingsGenerateDialog(self, current_setting_name)
                d.exec_()
                if d.result() == d.Accepted:
                    # Either "Generate + Save" or "Generate + Revert"
                    self.is_deferred_revert = d.is_deferred_revert
                    if not d.is_deferred_revert:
                        self.persist_saved_setting(prompt=False, update_display=False)
                elif d.result() == d.Rejected:
                    # User clicked cancel - do not exit this dialog.
                    return
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
        self._selected_text_field = None

        selected_image_name = self.current.get(cfg.KEY_IMAGE_FILE, None)
        if selected_image_name is None:
            selected_image_name = cfg.TOKEN_DEFAULT_COVER
            self.current[cfg.KEY_IMAGE_FILE] = selected_image_name
        self.saved_settings_tab.pick_image_list.select_image_name(selected_image_name)

        self.contents_tab.field_order_list.populate(self.current[cfg.KEY_FIELD_ORDER])
        if self.contents_tab.field_order_list.count():
            self.contents_tab.field_order_list.setCurrentRow(0)
        self.contents_tab.colors_panel.backdrops_linked_checkbox.setChecked(self.current.get(cfg.KEY_BACKDROPS_LINKED, False))
        self.contents_tab.swap_author_checkbox.setChecked(self.current[cfg.KEY_SWAP_AUTHOR])
        self.contents_tab.series_text_ledit.setText(self.current.get(cfg.KEY_SERIES_TEXT, cfg.DEFAULT_SERIES_TEXT))

        (width, height) = self.current[cfg.KEY_SIZE]
        self.dimensions_tab.width_spin.setValue(width)
        self.dimensions_tab.height_spin.setValue(height)
        self.contents_tab.background_image_checkbox.setChecked(self.current[cfg.KEY_BACKGROUND_IMAGE])
        self.dimensions_tab.resize_image_to_fit_checkbox.setChecked(self.current[cfg.KEY_RESIZE_IMAGE_TO_FIT])
        self.dimensions_tab.resize_to_image_checkbox.setChecked(self.current[cfg.KEY_RESIZE_TO_IMAGE])

        margins = self.current[cfg.KEY_MARGINS]
        self.dimensions_tab.top_margin_spin.setValue(margins['top'])
        self.dimensions_tab.bottom_margin_spin.setValue(margins['bottom'])
        self.dimensions_tab.left_margin_spin.setValue(margins['left'])
        self.dimensions_tab.right_margin_spin.setValue(margins['right'])

        borders = self.current[cfg.KEY_BORDERS]
        self.dimensions_tab.cover_border_width_spin.setValue(borders['coverBorder'])
        self.contents_tab.image_border_width_spin.setValue(borders['imageBorder'])

        is_fonts_linked = self.current.get(cfg.KEY_FONTS_LINKED, False)
        self.contents_tab.fonts_linked_checkbox.setChecked(is_fonts_linked)
        self.contents_tab.fonts_reduced_checkbox.setChecked(self.current.get(cfg.KEY_FONTS_AUTOREDUCED, False))

        colors = self.current[cfg.KEY_COLORS]
        self.dimensions_tab.set_border_color(colors['border'])
        self.dimensions_tab.set_background_color(colors['background'])
        self.contents_tab.set_image_border_color(
            colors.get(cfg.KEY_IMAGE_BORDER_COLOR, colors['border']))

        is_same_fill = self.current.get(cfg.KEY_FILL_COLORS_LINKED, True)
        self.contents_tab.colors_panel.use_this_fill_color_checkbox.setChecked(is_same_fill)

        self.block_updates = False
        self.element_selection_changed(self.contents_tab.field_order_list.currentRow())

    def update_current_options(self):
        cfg.plugin_prefs[cfg.STORE_FILES] = self.saved_settings_tab.files
        self.current[cfg.KEY_IMAGE_FILE] = self.saved_settings_tab.pick_image_list.selected_image_name()

        self.current[cfg.KEY_SWAP_AUTHOR] = self.contents_tab.swap_author_checkbox.isChecked()
        self.save_selected_text_value()
        self.current[cfg.KEY_SERIES_TEXT] = unicode(self.contents_tab.series_text_ledit.text()).strip()
        self.current[cfg.KEY_BACKDROPS_LINKED] = self.contents_tab.colors_panel.backdrops_linked_checkbox.isChecked()
        self.current[cfg.KEY_BACKGROUND_IMAGE] = self.contents_tab.background_image_checkbox.isChecked()
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
        self.current[cfg.KEY_MARGINS] = (top_mgn, bottom_mgn, left_mgn)
        self.current[cfg.KEY_MARGINS] = {'top':    top_mgn,
                                         'bottom': bottom_mgn,
                                         'left':   left_mgn,
                                         'right':  right_mgn}

        cover_border_width = int(unicode(self.dimensions_tab.cover_border_width_spin.value()).strip())
        image_border_width = int(unicode(self.contents_tab.image_border_width_spin.value()).strip())

        self.current[cfg.KEY_BORDERS] = {'coverBorder': cover_border_width,
                                         'imageBorder': image_border_width }

        colors = self.current[cfg.KEY_COLORS]
        colors['border'] = unicode(self.dimensions_tab.border_color)
        colors[cfg.KEY_IMAGE_BORDER_COLOR] = unicode(
            self.contents_tab.image_border_color)
        colors['background'] = unicode(self.dimensions_tab.background_color)
        selected_font_key = self.font_key_for_field(self._selected_text_field or '')
        selected_fill_key = 'title_fill'
        if selected_font_key:
            selected_fill_key = selected_font_key + '_fill'
            colors[selected_fill_key] = unicode(
                self.contents_tab.colors_panel.fill_color_button.property('color') or '#000000')
        is_same_fill_color = self.contents_tab.colors_panel.use_this_fill_color_checkbox.isChecked()
        if is_same_fill_color:
            common_fill = colors.get(selected_fill_key, colors.get('title_fill', '#000000'))
            for name, _ in DIC_name_text_fill_color:
                colors[name.lower() + '_fill'] = common_fill
        self.current[cfg.KEY_COLORS] = colors
        self.current[cfg.KEY_FILL_COLORS_LINKED] = is_same_fill_color

        self.current[cfg.KEY_FONTS_LINKED] = self.contents_tab.fonts_linked_checkbox.isChecked()
        self.current[cfg.KEY_FONTS_AUTOREDUCED] = self.contents_tab.fonts_reduced_checkbox.isChecked()
        cfg.plugin_prefs[cfg.STORE_CURRENT] = self.current

    def element_selection_changed(self, row):
        if self.block_updates or row < 0:
            return
        self.save_selected_text_value()
        field = self.contents_tab.field_order_list.field_list[row]
        is_text_element = field['name'] != 'Image'
        is_image_element = field['name'] == 'Image'
        self.block_updates = True
        self._selected_text_field = field['name']
        self.contents_tab.fonts_groupbox.setTitle(field['name'] + ':')
        self.contents_tab.field_text_label.setText(field['name'] + ':')
        self.contents_tab.field_text_edit.setPlainText(self.get_selected_text_value(field['name']))
        is_metadata_field = field['name'] in ('Title', 'Author', 'Series')
        self.contents_tab.field_text_edit.setEnabled(
            is_text_element and (not is_metadata_field or not self.is_multiple_books))
        font_key = self.font_key_for_field(field['name'])
        self.contents_tab.font_family_combo.setEnabled(font_key is not None)
        self.contents_tab.font_size_spin.setEnabled(font_key is not None)
        self.contents_tab.font_alignment_combo.setEnabled(font_key is not None)
        self.contents_tab.font_weight_combo.setEnabled(font_key is not None)
        self.contents_tab.font_italic_checkbox.setEnabled(font_key is not None)
        self.contents_tab.font_underline_checkbox.setEnabled(font_key is not None)
        self.contents_tab.font_rotation_combo.setEnabled(font_key is not None)
        self.contents_tab.font_rotation_side_combo.setEnabled(False)

        for spin in self.contents_tab.font_text_padding_spins.values():
            spin.setEnabled(font_key is not None)
        if font_key is not None:
            font = self.current[cfg.KEY_FONTS][font_key]
            self.contents_tab.font_family_combo.select_value(font['name'])
            self.contents_tab.font_size_spin.setValue(font['size'])
            self.contents_tab.font_weight_combo.select_value(font.get('weight', 'Normal'))
            self.contents_tab.font_italic_checkbox.setChecked(font.get('italic', False))
            self.contents_tab.font_underline_checkbox.setChecked(font.get('underline', False))
            alignment_index = self.contents_tab.font_alignment_combo.findData(font['align'])
            self.contents_tab.font_alignment_combo.setCurrentIndex(max(0, alignment_index))
            angle = field.get(cfg.KEY_FIELD_ROTATION, 0)
            rotation_index = self.contents_tab.font_rotation_combo.findData(angle)
            self.contents_tab.font_rotation_combo.setCurrentIndex(max(0, rotation_index))
            side = field.get(cfg.KEY_FIELD_ROTATION_SIDE, 'left')
            side_index = self.contents_tab.font_rotation_side_combo.findData(side)
            self.contents_tab.font_rotation_side_combo.setCurrentIndex(max(0, side_index))
            self.contents_tab.font_rotation_side_combo.setEnabled(angle in (90, 270))
            text_padding = field.get(cfg.KEY_FIELD_TEXT_PADDING, cfg.DEFAULT_ELEMENT_OPTIONS[cfg.KEY_FIELD_TEXT_PADDING])
            for side, spin in self.contents_tab.font_text_padding_spins.items():
                spin.setValue(text_padding[side])
            self.contents_tab.colors_panel.update_selected_field(field['name'])

        show_author_option = field['name'] == 'Author'
        show_series_option = field['name'] == 'Series'
        self.contents_tab.swap_author_checkbox.setVisible(show_author_option)
        self.contents_tab.series_label.setVisible(show_series_option)
        self.contents_tab.series_text_ledit.setVisible(show_series_option)
        if is_image_element:
            image_padding = field.get(cfg.KEY_FIELD_IMAGE_PADDING, cfg.DEFAULT_ELEMENT_OPTIONS[cfg.KEY_FIELD_IMAGE_PADDING])
            for side, spin in self.contents_tab.image_padding_spins.items():
                spin.setValue(image_padding[side])
        self.contents_tab.set_image_mode(is_image_element)
        backdrop_padding = field.get(cfg.KEY_FIELD_BACKDROP_PADDING, cfg.DEFAULT_ELEMENT_OPTIONS[cfg.KEY_FIELD_BACKDROP_PADDING])
        for side, spin in self.contents_tab.colors_panel.element_padding_spins.items():
            spin.setValue(backdrop_padding[side])
        self.contents_tab.colors_panel.element_backdrop_checkbox.setChecked(field.get(cfg.KEY_FIELD_BACKDROP, False))
        self.contents_tab.colors_panel.element_backdrop_full_width_checkbox.setChecked(
            field.get(cfg.KEY_FIELD_BACKDROP_FULL_WIDTH, False))
        self.contents_tab.colors_panel.set_element_backdrop_color(field.get(cfg.KEY_FIELD_BACKDROP_COLOR, '#000000'))
        self.contents_tab.colors_panel.element_backdrop_opacity_spin.setValue(field.get(cfg.KEY_FIELD_BACKDROP_OPACITY, 70))
        for spin in self.contents_tab.colors_panel.element_padding_spins.values():
            spin.setEnabled(is_text_element)
        self.contents_tab.colors_panel.element_backdrop_checkbox.setEnabled(is_text_element)
        self.contents_tab.colors_panel.element_backdrop_full_width_checkbox.setEnabled(is_text_element)
        self.contents_tab.colors_panel.backdrops_linked_checkbox.setEnabled(is_text_element)
        self.contents_tab.colors_panel.element_backdrop_color_button.setEnabled(is_text_element)
        self.contents_tab.colors_panel.element_backdrop_opacity_spin.setEnabled(is_text_element)
        self.block_updates = False

    def font_key_for_field(self, field_name):
        field_font_keys = {'Title': 'title', 'Author': 'author', 'Series': 'series'}
        if field_name in field_font_keys:
            return field_font_keys[field_name]
        if field_name.startswith('Custom Text '):
            custom_index = int(field_name.rsplit(' ', 1)[1])
            return 'custom' if custom_index == 1 else 'custom%d' % custom_index
        return None

    def font_options_changed(self, *args):
        if self.block_updates:
            return
        row = self.contents_tab.field_order_list.currentRow()
        if row < 0:
            return
        field_name = self.contents_tab.field_order_list.field_list[row]['name']
        font_key = self.font_key_for_field(field_name)
        if font_key is None:
            return
        font = self.current[cfg.KEY_FONTS][font_key]
        font['name'] = self.contents_tab.font_family_combo.get_value()
        font['size'] = self.contents_tab.font_size_spin.value()
        font['weight'] = self.contents_tab.font_weight_combo.get_value()
        font['italic'] = self.contents_tab.font_italic_checkbox.isChecked()
        font['underline'] = self.contents_tab.font_underline_checkbox.isChecked()
        font['align'] = self.contents_tab.font_alignment_combo.itemData(
            self.contents_tab.font_alignment_combo.currentIndex())
        field = self.contents_tab.field_order_list.field_list[row]
        field[cfg.KEY_FIELD_ROTATION] = self.contents_tab.font_rotation_combo.itemData(
            self.contents_tab.font_rotation_combo.currentIndex())
        field[cfg.KEY_FIELD_ROTATION_SIDE] = self.contents_tab.font_rotation_side_combo.itemData(
            self.contents_tab.font_rotation_side_combo.currentIndex())
        self.contents_tab.font_rotation_side_combo.setEnabled(
            field[cfg.KEY_FIELD_ROTATION] in (90, 270))
        field[cfg.KEY_FIELD_TEXT_PADDING] = {
            side: spin.value()
            for side, spin in self.contents_tab.font_text_padding_spins.items()
        }
        if self.contents_tab.fonts_linked_checkbox.isChecked():
            for name, _ in DIC_name_font:
                self.current[cfg.KEY_FONTS][name.lower()]['name'] = font['name']
                self.current[cfg.KEY_FONTS][name.lower()]['weight'] = font['weight']
        self.options_changed()

    def fonts_linked_changed(self, *args):
        if self.block_updates:
            return
        linked = self.contents_tab.fonts_linked_checkbox.isChecked()
        self.current[cfg.KEY_FONTS_LINKED] = linked
        if linked:
            font_key = self.font_key_for_field(self._selected_text_field or '')
            if font_key is not None:
                selected_font = self.current[cfg.KEY_FONTS][font_key]['name']
                for name, _ in DIC_name_font:
                    self.current[cfg.KEY_FONTS][name.lower()]['name'] = selected_font
        row = self.contents_tab.field_order_list.currentRow()
        if row >= 0:
            font_key = self.font_key_for_field(self.contents_tab.field_order_list.field_list[row]['name'])
            self.contents_tab.font_family_combo.setEnabled(font_key is not None)
        self.options_changed()

    def get_selected_text_value(self, field_name):
        if field_name == 'Title':
            return unicode(self.book.title or '')
        if field_name == 'Author':
            options = {cfg.KEY_SERIES_TEXT: '', cfg.KEY_SWAP_AUTHOR: False}
            return get_title_author_series(self.book, options)[1]
        if field_name == 'Series':
            options = {cfg.KEY_SERIES_TEXT: '{series} [{series_index}]', cfg.KEY_SWAP_AUTHOR: False}
            return get_title_author_series(self.book, options)[2] or ''
        if field_name.startswith('Custom Text '):
            custom_index = int(field_name.rsplit(' ', 1)[1]) - 1
            custom_key = cfg.KEY_CUSTOM_TEXT_FIELDS[custom_index]
            return self.current.get(custom_key, '')
        return ''

    def save_selected_text_value(self):
        field_name = getattr(self, '_selected_text_field', None)
        if not field_name:
            return
        text = unicode(self.contents_tab.field_text_edit.toPlainText())
        if field_name == 'Title':
            self.book.title = text
        elif field_name == 'Author':
            self.book.authors = string_to_authors(text)
        elif field_name == 'Series':
            series_name, series_index = self.parse_series(text)
            self.book.series = series_name
            self.book.series_index = series_index
        elif field_name.startswith('Custom Text '):
            custom_index = int(field_name.rsplit(' ', 1)[1]) - 1
            custom_key = cfg.KEY_CUSTOM_TEXT_FIELDS[custom_index]
            self.current[custom_key] = text

    def element_options_changed(self, *args):
        if self.block_updates:
            return
        row = self.contents_tab.field_order_list.currentRow()
        if row < 0:
            return
        field = self.contents_tab.field_order_list.field_list[row]
        if field['name'] != 'Image':
            field[cfg.KEY_FIELD_BACKDROP_PADDING] = {
                side: spin.value()
                for side, spin in self.contents_tab.colors_panel.element_padding_spins.items()
            }
            field[cfg.KEY_FIELD_BACKDROP] = self.contents_tab.colors_panel.element_backdrop_checkbox.isChecked()
            field[cfg.KEY_FIELD_BACKDROP_FULL_WIDTH] = (
                self.contents_tab.colors_panel.element_backdrop_full_width_checkbox.isChecked())
            field[cfg.KEY_FIELD_BACKDROP_COLOR] = self.contents_tab.colors_panel.element_backdrop_color
            field[cfg.KEY_FIELD_BACKDROP_OPACITY] = self.contents_tab.colors_panel.element_backdrop_opacity_spin.value()
            if self.contents_tab.colors_panel.backdrops_linked_checkbox.isChecked():
                backdrop_keys = (cfg.KEY_FIELD_BACKDROP,
                                 cfg.KEY_FIELD_BACKDROP_FULL_WIDTH,
                                 cfg.KEY_FIELD_BACKDROP_PADDING,
                                 cfg.KEY_FIELD_BACKDROP_COLOR, cfg.KEY_FIELD_BACKDROP_OPACITY)
                selected_backdrop = {key: field[key] for key in backdrop_keys}
                for other_field in self.contents_tab.field_order_list.field_list:
                    if other_field['name'] != 'Image':
                        other_field.update(selected_backdrop)
            self.current[cfg.KEY_BACKDROPS_LINKED] = self.contents_tab.colors_panel.backdrops_linked_checkbox.isChecked()
        else:
            image_padding = {
                side: spin.value()
                for side, spin in self.contents_tab.image_padding_spins.items()
            }
            field[cfg.KEY_FIELD_IMAGE_PADDING] = image_padding
        self.options_changed()

    def pick_element_backdrop_color(self):
        row = self.contents_tab.field_order_list.currentRow()
        if row < 0:
            return
        field = self.contents_tab.field_order_list.field_list[row]
        color = QColor(field.get(cfg.KEY_FIELD_BACKDROP_COLOR, '#000000'))
        picked_color = QColorDialog.getColor(color, self)
        if picked_color.isValid():
            self.contents_tab.colors_panel.set_element_backdrop_color(picked_color.name())
            self.element_options_changed()

    def reset_element_backdrop_color(self):
        row = self.contents_tab.field_order_list.currentRow()
        if row < 0:
            return
        field = self.contents_tab.field_order_list.field_list[row]
        color = QColor(field.get(cfg.KEY_FIELD_BACKDROP_COLOR, '#000000'))
        self.contents_tab.colors_panel.set_element_backdrop_color(color.name())
        self.element_options_changed()

    def pick_border_color(self):
        color = QColor(self.dimensions_tab.border_color)
        picked_color = QColorDialog.getColor(color, self)
        if picked_color.isValid():
            self.dimensions_tab.set_border_color(picked_color.name())
            self.options_changed()

    def reset_border_color(self):
        color = self.get_saved_setting()[cfg.KEY_COLORS].get('border', '#000000')
        self.dimensions_tab.set_border_color(color)
        self.options_changed()

    def pick_image_border_color(self):
        color = QColor(self.contents_tab.image_border_color)
        picked_color = QColorDialog.getColor(color, self)
        if picked_color.isValid():
            self.contents_tab.set_image_border_color(picked_color.name())
            self.options_changed()

    def reset_image_border_color(self):
        saved_colors = self.get_saved_setting()[cfg.KEY_COLORS]
        color = saved_colors.get(
            cfg.KEY_IMAGE_BORDER_COLOR, saved_colors.get('border', '#000000'))
        self.contents_tab.set_image_border_color(color)
        self.options_changed()

    def pick_background_color(self):
        color = QColor(self.dimensions_tab.background_color)
        picked_color = QColorDialog.getColor(color, self)
        if picked_color.isValid():
            self.dimensions_tab.set_background_color(picked_color.name())
            self.options_changed()

    def reset_background_color(self):
        color = self.get_saved_setting()[cfg.KEY_COLORS].get('background', '#ffffff')
        self.dimensions_tab.set_background_color(color)
        self.options_changed()

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
