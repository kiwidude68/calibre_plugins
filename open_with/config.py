from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from functools import partial
import os, shutil

try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (Qt, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                        QLineEdit, QTableWidget, QTableWidgetItem, QFileDialog,
                        QAbstractItemView, QRadioButton, QAction, QIcon, QToolButton,
                        QDialog, QDialogButtonBox, QGridLayout, QGroupBox,
                        QInputDialog, QSpacerItem, QModelIndex)
except ImportError:
    from PyQt5.Qt import (Qt, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                        QLineEdit, QTableWidget, QTableWidgetItem, QFileDialog,
                        QAbstractItemView, QRadioButton, QAction, QIcon, QToolButton,
                        QDialog, QDialogButtonBox, QGridLayout, QGroupBox,
                        QInputDialog, QSpacerItem, QModelIndex)

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.constants import iswindows, isosx
from calibre.gui2 import (choose_files, choose_osx_app, error_dialog, FileDialog, info_dialog,
                          open_local_file, question_dialog)
from calibre.gui2.actions import menu_action_unique_name
from calibre.utils.config import config_dir, JSONConfig
from calibre.utils.zipfile import ZipFile

from calibre_plugins.open_with.common_compatibility import qSizePolicy_Minimum, qSizePolicy_Expanding
from calibre_plugins.open_with.common_icons import get_icon
from calibre_plugins.open_with.common_dialogs import KeyboardConfigDialog
from calibre_plugins.open_with.common_widgets import NoWheelComboBox, CheckableTableWidgetItem, TextIconWidgetItem


PLUGIN_ICONS = ['open_with.png', 'image_add.png', 'import.png', 'export.png']

COL_NAMES = ['active', 'menuText', 'subMenu', 'format', 'image', 'appPath', 'appArgs']

DEFAULT_MENU_SET_WINDOWS = [
        (True,  'Sigil (EPUB)',             '', 'EPUB',    'owp_sigil.png',    'C:\\Program Files\\Sigil\\Sigil.exe', ''),
        (False, 'Adobe Digital Ed (EPUB)',  '', 'EPUB',    'owp_ade.png',      'C:\\Program Files\\Adobe\\Adobe Digital Editions\\digitaleditions.exe', ''),
        (False, 'Adobe Digital x64 (EPUB)', '', 'EPUB',    'owp_ade.png',      'C:\\Program Files (x86)\\Adobe\\Adobe Digital Editions\\digitaleditions.exe', ''),
        (False, 'EPUBReader (EPUB)',        '', 'EPUB',    'owp_firefox.png',  'C:\\Program Files\\Mozilla Firefox\\firefox.exe', ''),
        (False, '', '', '', '', '', '', ''),
        (False, 'MS Paint (Cover)',         '', 'COVER',   'owp_mspaint.png',  'C:\\Windows\\System32\\mspaint.exe', ''),
        (False, 'PSP 7 (Cover)',            '', 'COVER',   'owp_psp.png',      'C:\\Program Files\\Jasc Software Inc\\Paint Shop Pro 7\\psp.exe', ''),
        (False, 'PSP 7 x64 (Cover)',        '', 'COVER',   'owp_psp.png',      'C:\\Program Files (x86)\\Jasc Software Inc\\Paint Shop Pro 7\\psp.exe', ''),
        (False, 'Paint.NET (Cover)',        '', 'COVER',   'owp_paintnet.png', 'C:\\Program Files\\Paint.NET\\PaintDotNet.exe', ''),
        (False, 'Photoshop CS5 (Cover)',    '', 'COVER',   'owp_pshop.png',    'C:\\Program Files\\Adobe\Adobe Photoshop CS5\\Photoshop.exe', ''),
        (False, 'Photoshop CS5 x64 (Cover)','', 'COVER',   'owp_pshop.png',    'C:\\Program Files (x86)\\Adobe\Adobe Photoshop CS5\\Photoshop.exe', ''),
        (False, '', '', '', '', '', '', ''),
        (False, 'Calibre (EPUB)',           '', 'EPUB',    'owp_calibre.png',  'C:\\Program Files\\Calibre2\\ebook-viewer.exe', ''),
        (False, 'Calibre x64 (EPUB)',       '', 'EPUB',    'owp_calibre.png',  'C:\\Program Files (x86)\\Calibre2\\ebook-viewer.exe', ''),
        (False, 'Calibre (MOBI)',           '', 'MOBI',    'owp_calibre.png',  'C:\\Program Files\\Calibre2\\ebook-viewer.exe', ''),
        (False, 'Calibre x64 (MOBI)',       '', 'MOBI',    'owp_calibre.png',  'C:\\Program Files (x86)\\Calibre2\\ebook-viewer.exe', ''),
        (False, '', '', '', '', '', '', ''),
        (False, 'Adobe Acrobat (PDF)',      '', 'PDF',     'owp_acrobat.png',  'C:\\Program Files\\Adobe\\Acrobat 10.0\\Acrobat\\Acrobat.exe', ''),
        (False, 'Adobe Acrobat x64 (PDF)',  '', 'PDF',     'owp_acrobat.png',  'C:\\Program Files (x86)\\Adobe\\Acrobat 10.0\\Acrobat\\Acrobat.exe', ''),
        (False, 'Adobe Digital Ed (PDF)',   '', 'PDF',     'owp_ade.png',      'C:\\Program Files\\Adobe\\Adobe Digital Editions\\digitaleditions.exe', ''),
        (False, 'Adobe Digital x64 (PDF)',  '', 'PDF',     'owp_ade.png',      'C:\\Program Files (x86)\\Adobe\\Adobe Digital Editions\\digitaleditions.exe', ''),
        (False, 'Briss (PDF)',              '', 'PDF',     'owp_briss.png',    'C:\\Program Files\\briss\\briss.exe', '')]
DEFAULT_MENU_SET_OSX = [
        (True,  'Sigil (EPUB)',             '', 'EPUB',    'owp_sigil.png',    '/Applications/Sigil.app', ''),
        (False, 'Adobe Digital Ed (EPUB)',  '', 'EPUB',    'owp_ade.png',      '/Applications/Adobe Digital Editions.app', ''),
        (False, 'EPUBReader (EPUB)',        '', 'EPUB',    'owp_firefox.png',  '/Applications/Firefox.app', ''),
        (True,  '', '', '', '', '', '', ''),
        (False, 'Photoshop CS5 (Cover)',    '', 'COVER',   'owp_pshop.png',    '/Applications/Adobe Photoshop CS5/Adobe Photoshop CS5.app', ''),
        (False, 'Pixelmator (Cover)',       '', 'COVER',   'owp_pixelm.png',   '/Applications/Pixelmator.app', ''),
        (True,  'Preview (Cover)',          '', 'COVER',   'owp_preview.png',  '/Applications/Preview.app', ''),
        (False, '', '', '', '', '', '', ''),
        (False, 'Adobe Acrobat (PDF)',      '', 'PDF',     'owp_acrobat.png',  '/Applications/Adobe Acrobat 9 Pro/Adobe Acrobat Pro.app', ''),
        (False, 'Adobe Digital Ed (PDF)',   '', 'PDF',     'owp_ade.png',      '/Applications/Adobe Digital Editions.app', ''),
        (False, 'Adobe Reader 9 (PDF)',     '', 'PDF',     'owp_reader.png',   '/Applications/Adobe Reader 9/Adobe Reader.app', ''),
        (False, 'Skim (PDF)',               '', 'PDF',     'owp_skim.png',     '/Applications/Skim.app', '')]
DEFAULT_MENU_SET_LINUX = [
        (True,  'Sigil (EPUB)',             '', 'EPUB',    'owp_sigil.png',    '/opt/sigil/sigil.sh', ''),
        (False, 'EPUBReader (EPUB)',        '', 'EPUB',    'owp_firefox.png',  'firefox', ''),
        (True,  '', '', '', '', '', '', ''),
        (True,  'Gimp (Cover)',             '', 'COVER',   'owp_gimp.png',     'gimp', '')]

STORE_MENUS_NAME = 'OpenWithMenus'
KEY_MENUS = 'Menus'
KEY_COL_WIDTH = 'UrlColWidth'
DEFAULT_STORE_VALUES = {
    KEY_MENUS: None,
    KEY_COL_WIDTH: -1
}

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Open With')

# Set defaults
plugin_prefs.defaults[STORE_MENUS_NAME] = DEFAULT_STORE_VALUES

def get_default_menu_set():
    if iswindows:
        return DEFAULT_MENU_SET_WINDOWS
    elif isosx:
        return DEFAULT_MENU_SET_OSX
    else:
        return DEFAULT_MENU_SET_LINUX

def get_default_icon_names():
    # Build a distinct set of icon names to pass to load_resources, including our top level icon
    icon_names = PLUGIN_ICONS
    for id, val in enumerate(get_default_menu_set()):
        icon = val[4]
        if icon is not None and icon not in icon_names:
            icon_names.append(icon)
    return icon_names

def get_menus_as_dictionary(config_menus=None):
    # Menu items will be stored in a config dictionary in the JSON configuration file
    # However if no menus defined (like first time user) we build a default dictionary set.
    if config_menus is None:
        # No menu items are defines so populate with the default set of menu items
        config_menus = [dict(list(zip(COL_NAMES, tup))) for tup in get_default_menu_set()]
    return config_menus

def get_pathed_icon(icon_name):
    '''
    We prefix our icons for two reasons:
    
    1. If they really are built-in icons from this zip file, then they sit in the zip subfolder 'images'
    2. If they were instead user-added images, they will sit in the folder: resources\images\Open With\
        however the logic in get_pixmap() would not look for them there due to the if statement that says
        anything not prefixed with 'images/' is assumed to be a calibre built-in icon.
    
    Note that this is only a problem for calibre < 6.2.0 get_icon_old)), the new get_icon_6_2_plus() is fine.
    but does no harm to still include the prefix as it tries without images/ first anyway.
    '''
    return 'images/'+icon_name


class ImageComboBox(NoWheelComboBox):

    def __init__(self, parent, image_names, images, selected_text):
        NoWheelComboBox.__init__(self, parent)
        self.populate_combo(image_names, images, selected_text)

    def populate_combo(self, image_names, images, selected_text):
        self.clear()
        for i, image in enumerate(image_names):
            self.insertItem(i, images[i], image)
        idx = self.findText(selected_text)
        self.setCurrentIndex(idx)
        self.setItemData(0, idx)


class FormatComboBox(NoWheelComboBox):

    def __init__(self, parent, format_names, selected_text):
        NoWheelComboBox.__init__(self, parent)
        self.populate_combo(format_names, selected_text)

    def populate_combo(self, format_names, selected_text):
        self.addItems(format_names)
        if selected_text:
            idx = self.findText(selected_text)
            self.setCurrentIndex(idx)
        else:
            self.setCurrentIndex(0)


class MenuTableWidget(QTableWidget):
    COMBO_IMAGE_ADD = 'Add New Image...'

    def __init__(self, all_formats, data_items, *args):
        QTableWidget.__init__(self, *args)
        self.all_formats = all_formats
        self.populate_table(data_items)
        self.cellChanged.connect(self.cell_changed)
        self.cellDoubleClicked.connect(self.cell_double_clicked)

    def app_path_column_width(self):
        if self.columnCount() > 4:
            return self.columnWidth(5)
        else:
            c = plugin_prefs[STORE_MENUS_NAME]
            return c.get(KEY_COL_WIDTH, -1)

    def populate_table(self, data_items):
        self.read_image_combo_names()
        self.format_names = self.read_format_combo_names()
        last_app_path_column_width = self.app_path_column_width()
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(data_items))
        header_labels = ['', _('Title'), _('Submenu'), _('Format'), _('Image'),
                         _('Application Path'), _('Args')]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(24)

        for row, data in enumerate(data_items):
            self.populate_table_row(row, data)

        self.resizeColumnsToContents()
        # Special sizing for the app path column as it tends to dominate the dialog
        if last_app_path_column_width != -1:
            self.setColumnWidth(5, last_app_path_column_width)
        self.setSortingEnabled(False)
        self.setMinimumSize(800, 0)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.selectRow(0)

    def populate_table_row(self, row, data):
        self.blockSignals(True)
        icon_name = data['image']
        menu_text = data['menuText']
        self.setItem(row, 0, CheckableTableWidgetItem(data['active']))
        self.setItem(row, 1, TextIconWidgetItem(menu_text, get_icon(get_pathed_icon(icon_name))))
        self.setItem(row, 2, QTableWidgetItem(data['subMenu']))
        if menu_text:
            self.set_editable_cells_in_row(row, format=data['format'],
                        image=icon_name, app_path=data['appPath'], app_args=data['appArgs'])
        else:
            # Make all the later column cells non-editable
            self.set_noneditable_cells_in_row(row)
        self.blockSignals(False)

    def append_data(self, data_items):
        for data in reversed(data_items):
            row = self.currentRow() + 1
            self.insertRow(row)
            self.populate_table_row(row, data)

    def get_data(self):
        data_items = []
        for row in range(self.rowCount()):
            data_items.append(self.convert_row_to_data(row))
        # Remove any blank separator row items from the end as unneeded.
        while len(data_items) > 0 and len(data_items[-1]['menuText']) == 0:
            data_items.pop()
        return data_items

    def get_selected_data(self):
        data_items = []
        for row in self.selectionModel().selectedRows():
            data_items.append(self.convert_row_to_data(row.row()))
        return data_items

    def convert_row_to_data(self, row):
        data = self.create_blank_row_data()
        data['active'] = self.item(row, 0).checkState() == Qt.Checked
        data['menuText'] = str(self.item(row, 1).text()).strip()
        data['subMenu'] = str(self.item(row, 2).text()).strip()
        if data['menuText']:
            data['format'] = str(self.cellWidget(row, 3).currentText()).strip()
            data['image'] = str(self.cellWidget(row, 4).currentText()).strip()
            data['appPath'] = str(self.item(row, 5).text()).strip()
            data['appArgs'] = str(self.item(row, 6).text()).strip()
        return data

    def cell_changed(self, row, col):
        if col == 1:
            menu_text = str(self.item(row, col).text()).strip()
            self.blockSignals(True)
            if menu_text:
                # Make sure that the other columns in this row are enabled if not already.
                if not self.item(row, 6).flags() & Qt.ItemIsEditable:
                    # We need to make later columns in this row editable
                    self.set_editable_cells_in_row(row)
            else:
                # Blank menu text so treat it as a separator row
                self.set_noneditable_cells_in_row(row)
            self.blockSignals(False)

    def cell_double_clicked(self, row, col):
        if col == 5:
            # User is double clicking the application path column. invoke the file open dialog.
            # But only do this if they are on a "valid" editable row.
            if not self.item(row, 6).flags() & Qt.ItemIsEditable:
                return
            app_path = None
            if isosx:
                apps = choose_osx_app(None, 'open with dialog',
                                     _('Select the application to execute for this format'))
                if not apps:
                    return
                app_path = apps[0]
            else: #windows/linux
                apps = choose_files(None, 'open with dialog', _('Select the application to execute for this format'),
                                 all_files=True, select_only_single_file=True)
                if not apps:
                    return
                app_path = apps[0]
                if iswindows:
                    app_path = os.path.normpath(app_path)
            self.item(row, col).setText(app_path)

    def image_combo_index_changed(self, combo, row):
        if combo.currentText() == self.COMBO_IMAGE_ADD:
            # Special item in the combo for choosing a new image to add to Calibre
            self.display_add_new_image_dialog(select_in_combo=True, combo=combo)
        # Regardless of new or existing item, update image on the title column
        title_item = self.item(row, 1)
        title_item.setIcon(combo.itemIcon(combo.currentIndex()))
        # Store the current index as item data in index 0 in case user cancels dialog in future
        combo.setItemData(0, combo.currentIndex())

    def set_editable_cells_in_row(self, row, format='', image='', app_path='', app_args=''):
        self.setCellWidget(row, 3, FormatComboBox(self, self.format_names, format))
        image_combo = ImageComboBox(self, self.image_names, self.images, image)
        image_combo.currentIndexChanged.connect(partial(self.image_combo_index_changed, image_combo, row))
        self.setCellWidget(row, 4, image_combo)
        # Make the app path widget only changeable by double-clicking which will invoke the open file dialog.
        path_widget = QTableWidgetItem(app_path)
        path_widget.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        self.setItem(row, 5, path_widget)
        self.setItem(row, 6, QTableWidgetItem(app_args))

    def set_noneditable_cells_in_row(self, row):
        for col in range(3,7):
            if self.cellWidget(row, col):
                self.removeCellWidget(row, col)
            item = QTableWidgetItem()
            item.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
            self.setItem(row, col, item)
        self.item(row, 1).setIcon(QIcon())

    def create_blank_row_data(self):
        data = {}
        data['active'] = True
        data['menuText'] = ''
        data['subMenu'] = ''
        data['format'] = ''
        data['image'] = ''
        data['appPath'] = ''
        data['appArgs'] = ''
        return data

    def edit_path(self):
        row = self.currentRow()
        if not self.item(row, 6).flags() & Qt.ItemIsEditable:
            return
        oldpath = str(self.item(row, 5).text()).strip()
        newpath, ok = QInputDialog.getText(self, _('Edit Path'),
                '<p>'+_('Choose a new path for this application:'),
                text=oldpath)
        newpath = str(newpath)
        if not ok or not newpath or newpath == oldpath:
            return
        self.item(row, 5).setText(newpath)

    def display_add_new_image_dialog(self, select_in_combo=False, combo=None):
        add_image_dialog = PickImageDialog(self, self.resources_dir, self.image_names)
        add_image_dialog.exec_()
        if add_image_dialog.result() == QDialog.Rejected:
            # User cancelled the add operation or an error - set to previous value
            if select_in_combo and combo:
                prevIndex = combo.itemData(0)
                combo.blockSignals(True)
                combo.setCurrentIndex(prevIndex)
                combo.blockSignals(False)
            return
        # User has added a new image so we need to repopulate every combo with new sorted list
        self.read_image_combo_names()
        for update_row in range(self.rowCount()):
            cellCombo = self.cellWidget(update_row, 4)
            if cellCombo:
                cellCombo.blockSignals(True)
                cellCombo.populate_combo(self.image_names, self.images, cellCombo.currentText())
                cellCombo.blockSignals(False)
        # Now select the newly added item in this row if required
        if select_in_combo and combo:
            idx = combo.findText(add_image_dialog.image_name)
            combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)

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
        for selrow in rows:
            self.swap_row_widgets(selrow.row() - 1, selrow.row() + 1)
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
        for selrow in reversed(rows):
            self.swap_row_widgets(selrow.row() + 2, selrow.row())
        scroll_to_row = last_sel_row + 1
        if scroll_to_row < self.rowCount() - 1:
            scroll_to_row = scroll_to_row + 1
        self.scrollToItem(self.item(scroll_to_row, 0))

    def swap_row_widgets(self, src_row, dest_row):
        self.blockSignals(True)
        self.insertRow(dest_row)
        for col in range(0,3):
            self.setItem(dest_row, col, self.takeItem(src_row, col))
        menu_text = str(self.item(dest_row, 1).text()).strip()
        if menu_text:
            for col in range(3,7):
                if col == 3:
                    # Format column has a combo box we also have to recreate
                    format = self.cellWidget(src_row, col).currentText()
                    self.setCellWidget(dest_row, col, FormatComboBox(self, self.format_names, format))
                elif col == 4:
                    # Image column has a combobox we have to recreate as cannot move widget (Qt crap)
                    icon_name = self.cellWidget(src_row, col).currentText()
                    image_combo = ImageComboBox(self, self.image_names, self.images, icon_name)
                    image_combo.currentIndexChanged.connect(partial(self.image_combo_index_changed, image_combo, dest_row))
                    self.setCellWidget(dest_row, col, image_combo)
                else:
                    # Any other column we transfer the TableWidgetItem
                    self.setItem(dest_row, col, self.takeItem(src_row, col))
        else:
            # This is a separator row
            self.set_noneditable_cells_in_row(dest_row)
        self.removeRow(src_row)
        self.blockSignals(False)

    def select_and_scroll_to_row(self, row):
        self.selectRow(row)
        self.scrollToItem(self.currentItem())

    def read_format_combo_names(self):
        formats = list(sorted(self.all_formats))
        formats.insert(0, 'TEMPLATE')
        formats.insert(0, 'COVER')
        return formats

    def read_image_combo_names(self):
        # Read all of the images that are contained in the zip file
        image_names = get_default_icon_names()
        # Remove all the images that do not have the owp_ prefix
        image_names = [x for x in image_names if x.startswith('owp_')]
        # Now read any images from the config\resources\images\Open With directory if any
        self.resources_dir = os.path.join(config_dir, 'resources/images/Open With')
        if iswindows:
            self.resources_dir = os.path.normpath(self.resources_dir)

        if os.path.exists(self.resources_dir):
            # Get the names of any .png images in this directory
            for f in os.listdir(self.resources_dir):
                if f.lower().endswith('.png'):
                    image_names.append(os.path.basename(f))

        image_names.sort()
        # Add a blank item at the beginning of the list, and a blank then special 'Add" item at end
        image_names.insert(0, '')
        image_names.append('')
        image_names.append(self.COMBO_IMAGE_ADD)
        self.image_names = image_names
        self.images = [get_icon(get_pathed_icon(x)) for x in image_names]


class PickImageDialog(QDialog):

    def __init__(self, parent=None, resources_dir='', image_names=[]):
        QDialog.__init__(self, parent)
        self.resources_dir = resources_dir
        self.image_names = image_names
        self.setWindowTitle(_('Add New Image'))
        v = QVBoxLayout(self)

        group_box = QGroupBox(_('&Select image source'), self)
        v.addWidget(group_box)
        grid = QGridLayout()
        self._radio_web = QRadioButton(_('From &web domain favicon'), self)
        self._radio_web.setChecked(True)
        self._web_domain_edit = QLineEdit(self)
        self._radio_web.setFocusProxy(self._web_domain_edit)
        grid.addWidget(self._radio_web, 0, 0)
        grid.addWidget(self._web_domain_edit, 0, 1)
        grid.addWidget(QLabel('e.g. www.amazon.com'), 0, 2)
        self._radio_file = QRadioButton(_('From .png &file'), self)
        self._input_file_edit = QLineEdit(self)
        self._input_file_edit.setMinimumSize(200, 0)
        self._radio_file.setFocusProxy(self._input_file_edit)
        pick_button = QPushButton('...', self)
        pick_button.setMaximumSize(24, 20)
        pick_button.clicked.connect(self.pick_file_to_import)
        grid.addWidget(self._radio_file, 1, 0)
        grid.addWidget(self._input_file_edit, 1, 1)
        grid.addWidget(pick_button, 1, 2)
        group_box.setLayout(grid)

        save_layout = QHBoxLayout()
        lbl_filename = QLabel(_('&Save as filename:'), self)
        lbl_filename.setMinimumSize(155, 0)
        self._save_as_edit = QLineEdit('', self)
        self._save_as_edit.setMinimumSize(200, 0)
        lbl_filename.setBuddy(self._save_as_edit)
        lbl_ext = QLabel('.png', self)
        save_layout.addWidget(lbl_filename, 0, Qt.AlignLeft)
        save_layout.addWidget(self._save_as_edit, 0, Qt.AlignLeft)
        save_layout.addWidget(lbl_ext, 1, Qt.AlignLeft)
        v.addLayout(save_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.ok_clicked)
        button_box.rejected.connect(self.reject)
        v.addWidget(button_box)
        self.resize(self.sizeHint())
        self._web_domain_edit.setFocus()
        self.new_image_name = None

    @property
    def image_name(self):
        return self.new_image_name

    def pick_file_to_import(self):
        images = choose_files(None, 'menu icon dialog', _('Select a .png file for the menu icon'),
                             filters=[('PNG Image Files', ['png'])], all_files=False, select_only_single_file=True)
        if not images:
            return
        f = images[0]
        if not f.lower().endswith('.png'):
            return error_dialog(self, _('Cannot select image'),
                    _('Source image must be a .png file.'), show=True)
        self._input_file_edit.setText(f)
        self._save_as_edit.setText(os.path.splitext(os.path.basename(f))[0])

    def ok_clicked(self):
        # Validate all the inputs
        save_name = str(self._save_as_edit.text()).strip()
        if not save_name:
            return error_dialog(self, _('Cannot import image'),
                    _('You must specify a filename to save as.'), show=True)
        self.new_image_name = os.path.splitext(save_name)[0] + '.png'
        if save_name.find('\\') > -1 or save_name.find('/') > -1:
            return error_dialog(self, _('Cannot import image'),
                    _('The save as filename should consist of a filename only.'), show=True)
        if not os.path.exists(self.resources_dir):
            os.makedirs(self.resources_dir)
        dest_path = os.path.join(self.resources_dir, self.new_image_name)
        if save_name in self.image_names or os.path.exists(dest_path):
            if not question_dialog(self, _('Are you sure?'), '<p>'+
                    _('An image with this name already exists - overwrite it?'),
                    show_copy_button=False):
                return

        if self._radio_web.isChecked():
            domain = str(self._web_domain_edit.text()).strip()
            if not domain:
                return error_dialog(self, _('Cannot import image'),
                        _('You must specify a web domain url'), show=True)
            url = 'http://www.google.com/s2/favicons?domain=' + domain
            urlretrieve(url, dest_path)
            return self.accept()
        else:
            source_file_path = str(self._input_file_edit.text()).strip()
            if not source_file_path:
                return error_dialog(self, _('Cannot import image'),
                        _('You must specify a source file.'), show=True)
            if not source_file_path.lower().endswith('.png'):
                return error_dialog(self, _('Cannot import image'),
                        _('Source image must be a .png file.'), show=True)
            if not os.path.exists(source_file_path):
                return error_dialog(self, _('Cannot import image'),
                        _('Source image does not exist!'), show=True)
            shutil.copyfile(source_file_path, dest_path)
            return self.accept()


class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        all_formats = plugin_action.gui.library_view.model().db.all_formats()

        c = plugin_prefs[STORE_MENUS_NAME]
        data_items = get_menus_as_dictionary(c[KEY_MENUS])

        heading_layout = QHBoxLayout()
        layout.addLayout(heading_layout)
        heading_label = QLabel(_('&Select and configure the menu items to display:'), self)
        heading_layout.addWidget(heading_label)
        # Add hyperlink to a help file at the right. We will replace the correct name when it is clicked.
        help_label = QLabel('<a href="http://www.foo.com/">Help</a>', self)
        help_label.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
        help_label.setAlignment(Qt.AlignRight)
        help_label.linkActivated.connect(self.help_link_activated)
        heading_layout.addWidget(help_label)

        # Add a horizontal layout containing the table and the buttons next to it
        table_layout = QHBoxLayout()
        layout.addLayout(table_layout)

        # Create a table the user can edit the data values in
        self._table = MenuTableWidget(all_formats, data_items, self)
        heading_label.setBuddy(self._table)
        table_layout.addWidget(self._table)

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

        move_up_button.clicked.connect(self._table.move_rows_up)
        move_down_button.clicked.connect(self._table.move_rows_down)
        add_button.clicked.connect(self._table.add_row)
        delete_button.clicked.connect(self._table.delete_rows)
        reset_button.clicked.connect(self.reset_to_defaults)

        keyboard_layout = QHBoxLayout()
        layout.addLayout(keyboard_layout)
        keyboard_shortcuts_button = QPushButton(' '+_('Keyboard shortcuts')+'... ', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        keyboard_layout.addWidget(keyboard_shortcuts_button)
        keyboard_layout.insertStretch(-1)

        # Define a context menu for the table widget
        self.create_context_menu(self._table)
        # Build a list of all the active unique names
        self.orig_unique_active_menus = self.get_active_unique_names(data_items)

    def save_settings(self):
        open_menus = {}
        open_menus[KEY_MENUS] = self._table.get_data()
        open_menus[KEY_COL_WIDTH] = self._table.app_path_column_width()
        plugin_prefs[STORE_MENUS_NAME] = open_menus

        # For each menu that was visible but now is not, we need to unregister any
        # keyboard shortcut associated with that action.
        menus_changed = False
        kb = self.plugin_action.gui.keyboard
        new_unique_active_menus = self.get_active_unique_names(open_menus[KEY_MENUS])
        for raw_unique_name in list(self.orig_unique_active_menus.keys()):
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
                unique_name = data['format']+data['menuText']
                active_unique_names[unique_name] = data['menuText']
        return active_unique_names

    def create_context_menu(self, table):
        table.setContextMenuPolicy(Qt.ActionsContextMenu)
        act_edit = QAction(get_icon('console.png'), _('&Edit Path')+'...', table)
        act_edit.triggered.connect(table.edit_path)
        table.addAction(act_edit)
        sep1 = QAction(table)
        sep1.setSeparator(True)
        table.addAction(sep1)
        act_add_image = QAction(get_icon('images/image_add.png'), _('&Add image')+'...', table)
        act_add_image.triggered.connect(table.display_add_new_image_dialog)
        table.addAction(act_add_image)
        act_open = QAction(get_icon('document_open.png'), _('&Open images folder'), table)
        act_open.triggered.connect(partial(self.open_images_folder, table.resources_dir))
        table.addAction(act_open)
        sep2 = QAction(table)
        sep2.setSeparator(True)
        table.addAction(sep2)
        act_import = QAction(get_icon('images/import.png'), _('&Import')+'...', table)
        act_import.triggered.connect(self.import_menus)
        table.addAction(act_import)
        act_export = QAction(get_icon('images/export.png'), _('&Export')+'...', table)
        act_export.triggered.connect(self.export_menus)
        table.addAction(act_export)

    def help_link_activated(self, url):
        self.plugin_action.show_help()

    def reset_to_defaults(self):
        if not question_dialog(self, _('Are you sure?'), '<p>'+
                _('Are you sure you want to reset to the plugin default menu?')+'<br>' +
                _('Any modified configuration and custom menu items will be discarded.'),
                show_copy_button=False):
            return
        self._table.populate_table(get_menus_as_dictionary())

    def open_images_folder(self, path):
        if not os.path.exists(path):
            if not question_dialog(self, _('Are you sure?'), '<p>'+
                    _('Folder does not yet exist. Do you want to create it?')+'<br>%s' % path,
                    show_copy_button=False):
                return
            os.makedirs(path)
        open_local_file(path)

    def import_menus(self):
        table = self._table
        archive_path = self.pick_archive_to_import()
        if not archive_path:
            return
        # Write the whole file contents into the resources\images directory
        if not os.path.exists(table.resources_dir):
            os.makedirs(table.resources_dir)
        with ZipFile(archive_path, 'r') as zf:
            contents = zf.namelist()
            if 'owip_menus.json' not in contents:
                return error_dialog(self, _('Import Failed'),
                                    _('This is not a valid OWIP export archive'), show=True)
            for resource in contents:
                fs = os.path.join(table.resources_dir,resource)
                with open(fs,'wb') as f:
                    f.write(zf.read(resource))
        json_path = os.path.join(table.resources_dir,'owip_menus.json')
        try:
            # Read the .JSON file to add to the menus then delete it.
            archive_config = JSONConfig('resources/images/owip_menus')
            menus_config = archive_config.get(STORE_MENUS_NAME).get(KEY_MENUS)
            # Now insert the menus into the table
            table.append_data(menus_config)
            info_dialog(self, _('Import completed'), _('%d menu items added') % len(menus_config),
                        show=True, show_copy_button=False)
        finally:
            if os.path.exists(json_path):
                os.remove(json_path)

    def export_menus(self):
        table = self._table
        data_items = table.get_selected_data()
        if len(data_items) == 0:
            return error_dialog(self, _('Cannot export'),
                                _('No menu items selected to export.'), show=True)
        archive_path = self.pick_archive_name_to_export()
        if not archive_path:
            return
        # Build our unique list of images that need to be exported
        image_names = {}
        for data in data_items:
            image_name = data['image']
            if image_name and image_name not in image_names:
                image_path = os.path.join(table.resources_dir, image_name)
                if os.path.exists(image_path):
                    image_names[image_name] = image_path
        # Write our menu items out to a json file
        if not os.path.exists(table.resources_dir):
            os.makedirs(table.resources_dir)
        archive_config = JSONConfig('resources/images/owip_menus')
        export_menus = {}
        export_menus[KEY_MENUS] = data_items
        archive_config.set(STORE_MENUS_NAME, export_menus)
        json_path = os.path.join(table.resources_dir,'owip_menus.json')

        try:
            # Create the zip file archive
            with ZipFile(archive_path, 'w') as archive_zip:
                archive_zip.write(json_path, os.path.basename(json_path))
                # Add any images referred to in those menu items that are local resources
                for image_name, image_path in list(image_names.items()):
                    archive_zip.write(image_path, os.path.basename(image_path))
            info_dialog(self, _('Export completed'), _('%d menu items exported to<br>%s') % (len(data_items), archive_path),
                        show=True, show_copy_button=False)
        finally:
            if os.path.exists(json_path):
                os.remove(json_path)

    def pick_archive_to_import(self):
        archives = choose_files(self, 'owp archive dialog', _('Select a menu file archive to import'),
                             filters=[('OWIP Files', ['owip','zip'])], all_files=False, select_only_single_file=True)
        if not archives:
            return
        f = archives[0]
        return f

    def pick_archive_name_to_export(self):
        fd = FileDialog(name='owp archive dialog', title=_('Save archive as'), filters=[('OWIP Files', ['zip'])],
                        parent=self, add_all_files_filter=False, mode=QFileDialog.FileMode.AnyFile)
        fd.setParent(None)
        if not fd.accepted:
            return None
        return fd.get_files()[0]

    def edit_shortcuts(self):
        self.save_settings()
        # Force the menus to be rebuilt immediately, so we have all our actions registered
        self.plugin_action.rebuild_menus()
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()
