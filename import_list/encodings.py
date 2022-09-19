from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'
__copyright__ = '2020, Ahmed Zaki <azaki00.dev@gmail.com>'

from functools import partial

try:
    from qt.core import (Qt, QComboBox, QDialogButtonBox, QGridLayout, QVBoxLayout,
                        QToolButton, QLabel, QTableWidget, QAbstractItemView,
                        QToolButton)
except ImportError:                        
    from PyQt5.Qt import (Qt, QComboBox, QDialogButtonBox, QGridLayout, QVBoxLayout,
                        QToolButton, QLabel, QTableWidget, QAbstractItemView,
                        QToolButton)

from calibre_plugins.import_list.common_icons import get_icon
from calibre_plugins.import_list.common_dialogs import SizePersistedDialog
from calibre_plugins.import_list.common_widgets import ReadOnlyTableWidgetItem
import calibre_plugins.import_list.config as cfg
from calibre.gui2 import error_dialog


try:
    load_translations()
except NameError:
    pass

desc_map = {
    "big5": "Chinese Traditional",
    "big5hkscs": "Chinese Traditional",
    "IBM424": "Hebrew",
    "IBM437": "English",
    "IBM500": "Western",
    "IBM775": "Baltic",
    "IBM850": "Western",
    "IBM852": "Central European",
    "IBM855": "Cyrillic",
    "IBM857": "Turkish",
    "IBM858": "Western",
    "IBM860": "Portuguese",
    "IBM861": "Icelandic",
    "IBM862": "Hebrew",
    "IBM863": "Canadian",
    "IBM864": "Arabic",
    "IBM865": "Nordic",
    "IBM866": "Russian",
    "IBM869": "Greek",
    "cp932": "Japanese",
    "cp949": "Korean",
    "windows-1250": "Central European",
    "windows-1251": "Cyrillic",
    "windows-1252": "Western",
    "windows-1253": "Greek",
    "windows-1254": "Turkish",
    "windows-1255": "Hebrew",
    "windows-1256": "Arabic",
    "windows-1257": "Baltic",
    "windows-1258": "Vietnamese",
    "euc-jp": "Japanese",
    "euc-kr": "Korean",
    "gb2312": "Chinese Simplified",
    "gbk": "Chinese Unified",
    "iso-2022-jp": "Japanese",
    "iso-2022-kr": "Korean",
    "iso-8859-1": "Western",
    "iso-8859-2": "Central European",
    "iso-8859-3": "South European",
    "iso-8859-4": "Baltic",
    "iso-8859-5": "Cyrillic",
    "iso-8859-6": "Arabic",
    "iso-8859-7": "Greek",
    "iso-8859-8": "Hebrew",
    "iso-8859-9": "Turkish",
    "iso-8859-10": "Nordic",
    "iso-8859-11": "Thai",
    "iso-8859-13": "Baltic",
    "iso-8859-14": "Celtic",
    "iso-8859-15": "Western",
    "iso-8859-16": "Romanian",
    "johab": "Korean",
    "koi8-r": "Russian",
    "koi8-u": "Ukrainian",
    "shift_jis": "Japanese",
    "utf-32": "Unicode",
    "utf-16": "Unicode",
    "utf-16be": "Unicode",
    "utf-16le": "Unicode",
    "utf-7": "Unicode",
    "utf-8": "Unicode",
    "utf-8-sig": "Unicode"
}

class EncodingComboBox(QComboBox):
    def __init__(self, parent):
        QComboBox.__init__(self, parent)
        self.currentTextChanged.connect(self._encoding_changed)
        self.add_remove_text = _('Add or Remove')+'...'
        self.detect_encoding_text = _('detect encoding')
        self.last_idx = -1
        self.default_encoding = 'utf-8'

    def _add_remove_encodings(self, chosen_encodings):
        d = EncodingDialog(self, chosen_encodings)
        if d.exec_() == d.Accepted:
            self.setEncodings(d.chosen_encodings)
        else:
            self.setCurrentIndex(self.last_idx)

    def _encoding_changed(self):
        if self.currentText() == self.add_remove_text:
            self._add_remove_encodings(self.getEncodings())
        else:
            self.last_idx = self.currentIndex()

    def setEncodings(self, encodings, current=None):
        self.clear()
        self.addItems(encodings + [self.add_remove_text])
        self.insertSeparator(len(encodings))
        self.last_idx = self.currentIndex()

    def getEncodings(self):
        count = self.count()
        if count == 0:
            return []
        l = [ self.itemText(idx) for idx in range(count) ]
        # separator text == ''
        for text in [self.detect_encoding_text,self.add_remove_text,'']:
            try:
                l.remove(text)
            except ValueError:
                pass
        return l

    def currentEncoding(self):
        currentText = self.currentText()
        if currentText == '':
            return self.default_encoding
        elif currentText == self.detect_encoding_text:
            return 'auto'
        else:
            return currentText

    def setCurrentEncoding(self, encoding):
        idx = self.findText(encoding)
        if idx != -1:
            self.setCurrentIndex(idx)
        else:
            idx = len(self.getEncodings())
            self.insertItem(idx, encoding)
            self.setCurrentIndex(idx)

class EncodingTable(QTableWidget):

    def __init__(self, parent, sortable=True):
        QTableWidget.__init__(self, parent)
        self.setSortingEnabled(sortable)
        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().setDefaultSectionSize(self.verticalHeader().minimumSectionSize())

    def populate_table(self, all_rows, header_labels=None):
        self.clear()
        self.setRowCount(len(all_rows))
        if not header_labels:
            header_labels = [str(col) for col in range(1, len(all_rows[0])+1)]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.horizontalHeader().setStretchLastSection(True)

        for row, tbl_row in enumerate(all_rows):
            self.populate_table_row(row, tbl_row)

        self.resizeColumnsToContents()

    def populate_table_row(self, row, tbl_row):
        for col, col_data in enumerate(tbl_row):
            if isinstance(col_data, str):
                col_data = ReadOnlyTableWidgetItem(col_data)
            self.setItem(row, col, col_data)

    def remove_row(self):
        rows = sorted(self.selectionModel().selectedRows())
        for selrow in reversed(rows):
            self.removeRow(selrow.row())

    def take_rows(self):
        rows = sorted(self.selectionModel().selectedRows())
        for row in rows:
            yield [ self.takeItem(row.row(), column) for column in range(self.columnCount()) ]

    def add_row(self, tbl_row):
        sortable = self.isSortingEnabled()
        try:
            self.setSortingEnabled(False)
            row_idx = self.rowCount()
            self.insertRow(row_idx)
            self.populate_table_row(row_idx, tbl_row)
        finally:
            self.setSortingEnabled(sortable)

    def move_row_up(self):
        rows = sorted(self.selectionModel().selectedRows())
        for selrow in rows:
            old_idx = selrow.row()
            if old_idx > 0:
                new_idx = old_idx - 1
                tbl_row = [ self.takeItem(old_idx, column) for column in range(self.columnCount()) ]
                # delete before inserting to idx change
                self.removeRow(old_idx)
                self.insertRow(new_idx)
                self.populate_table_row(new_idx, tbl_row)
                self.setCurrentItem(self.item(new_idx,0))

    def move_row_down(self):
        rows = sorted(self.selectionModel().selectedRows())
        for selrow in rows:
            old_idx = selrow.row()
            if old_idx < (self.rowCount() - 1):
                new_idx = old_idx + 1
                tbl_row = [ self.takeItem(old_idx, column) for column in range(self.columnCount()) ]
                # delete before inserting to idx change
                self.removeRow(old_idx)
                self.insertRow(new_idx)
                self.populate_table_row(new_idx, tbl_row)
                self.setCurrentItem(self.item(new_idx,0))

class EncodingDialog(SizePersistedDialog):

    def __init__(self, parent, chosen_encodings=['utf-8','utf-16'], desc_map=desc_map):
        SizePersistedDialog.__init__(self, parent, 'import list plugin:encoding dialog')
        self._initialise_layout()
        self.resize_dialog()
        self.desc_map = desc_map
        self.header_labels = [_('Encoding'),_('Description')]
        self.encoding_col_idx = 0
        self.populate(chosen_encodings)

    def _initialise_layout(self):
        self.setWindowTitle(_('Choose Encodings'))
        l = QGridLayout()
        self.setLayout(l)

        avail_lbl = QLabel(_('Available Encodings:'), self)
        avail_lbl.setStyleSheet('QLabel { font-weight: bold; }')
        l.addWidget(avail_lbl, 0, 0, 1, 1)

        chosen_lbl = QLabel(_('Chosen Encodings:'), self)
        chosen_lbl.setStyleSheet('QLabel { font-weight: bold; }')
        l.addWidget(chosen_lbl, 0, 2, 1, 1)

        self.avail_tbl = EncodingTable(self)
        l.addWidget(self.avail_tbl, 1, 0, 1, 1)

        move_button_layout = QVBoxLayout()
        l.addLayout(move_button_layout, 1, 1, 1, 1)

        self.add_btn = QToolButton(self)
        self.add_btn.setIcon(get_icon('plus.png'))
        self.add_btn.setToolTip(_('Add the selected encoding'))
        self.remove_btn = QToolButton(self)
        self.remove_btn.setIcon(get_icon('minus.png'))
        self.remove_btn.setToolTip(_('Remove the selected encoding'))

        move_button_layout.addStretch(1)
        move_button_layout.addWidget(self.add_btn)
        move_button_layout.addWidget(self.remove_btn)
        move_button_layout.addStretch(1)
        
        self.chosen_tbl = EncodingTable(self, sortable=False)
        l.addWidget(self.chosen_tbl, 1, 2, 1, 1)

        self.add_btn.clicked.connect(partial(self._move_row, self.avail_tbl, self.chosen_tbl))
        self.remove_btn.clicked.connect(partial(self._move_row, self.chosen_tbl, self.avail_tbl))

        sort_button_layout = QVBoxLayout()
        l.addLayout(sort_button_layout, 1, 3, 1, 1)

        self.up_btn = QToolButton(self)
        self.up_btn.setIcon(get_icon('arrow-up.png'))
        self.up_btn.setToolTip(_('Move the selected item up'))
        self.up_btn.clicked.connect(self._move_row_up)
        self.down_btn = QToolButton(self)
        self.down_btn.setIcon(get_icon('arrow-down.png'))
        self.down_btn.setToolTip(_('Move the selected item down'))
        self.down_btn.clicked.connect(self._move_row_down)
        self.reset_btn = QToolButton(self)
        self.reset_btn.setIcon(get_icon('edit-undo.png'))
        self.reset_btn.setToolTip(_('Reset to defaults'))
        self.reset_btn.clicked.connect(self._reset)
        sort_button_layout.addWidget(self.up_btn)
        sort_button_layout.addStretch(1)
        sort_button_layout.addWidget(self.reset_btn)
        sort_button_layout.addStretch(1)
        sort_button_layout.addWidget(self.down_btn)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._accept_clicked)
        self.button_box.rejected.connect(self.reject)
        l.addWidget(self.button_box, 2, 2, 1, 4)

        for tbl in [self.avail_tbl, self.chosen_tbl]:
            tbl.itemPressed.connect(partial(self.table_item_pressed, tbl))
        
        for btn in [self.add_btn, self.remove_btn, self.up_btn, self.down_btn]:
            btn.clicked.connect(self._refresh_btns_state)

        self._refresh_btns_state()

    def _move_row_up(self):
        self.chosen_tbl.move_row_up()

    def _move_row_down(self):
        self.chosen_tbl.move_row_down()

    def _reset(self):
        for tbl in [self.avail_tbl,self.chosen_tbl]:
            for idx in range(tbl.rowCount(),-1,-1):
                tbl.removeRow(idx)
            for idx in range(tbl.columnCount(),-1,-1):
                tbl.removeColumn(idx)
        self.populate(cfg.DEFAULT_CSV_SETTING_VALUES[cfg.KEY_CSV_COMBO_ENCODINGS])

    def _move_row(self, from_tbl, to_tbl):
        rows = from_tbl.take_rows()
        for row in rows:
            from_tbl.remove_row()
            to_tbl.add_row(row)

    def _get_chosen_encodings(self):
        chosen_encodings = [ self.chosen_tbl.item(row, self.encoding_col_idx).text().strip() \
                                        for row in range(self.chosen_tbl.rowCount()) ]
        return chosen_encodings

    def table_item_pressed(self, tbl):
        if tbl == self.avail_tbl:
            self.chosen_tbl.clearSelection()
        else:
            self.avail_tbl.clearSelection()
        self._refresh_btns_state()

    def _refresh_btns_state(self):
        for btn in [self.add_btn, self.remove_btn, self.up_btn, self.down_btn]:
            btn.setDisabled(True)
        if self.avail_tbl.selectedItems() != []:
            self.add_btn.setEnabled(True)
        if self.chosen_tbl.selectedItems() != []:
            self.remove_btn.setEnabled(True)
            self.up_btn.setEnabled(self.chosen_tbl.currentRow() != 0)
            self.down_btn.setEnabled(self.chosen_tbl.currentRow() < self.chosen_tbl.rowCount() - 1)

    def _accept_clicked(self):
        self.chosen_encodings = self._get_chosen_encodings()
        if len(self.chosen_encodings) == 0:
            error_dialog(self, _('No encodings selected'), _('You must select one or more fields first.'), show=True)
            return
        self.accept()

    def populate(self, chosen_encodings):
        avail_encodings = set(self.desc_map.keys()) - set(chosen_encodings)
        avail_rows = [(encoding, self.desc_map[encoding]) for encoding in avail_encodings]
        chosen_rows = [(encoding, self.desc_map[encoding]) for encoding in chosen_encodings]
        self.avail_tbl.populate_table(avail_rows, self.header_labels)
        self.avail_tbl.sortItems(self.encoding_col_idx, Qt.AscendingOrder)
        self.chosen_tbl.populate_table(chosen_rows, self.header_labels)

