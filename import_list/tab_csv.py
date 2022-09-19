from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import os, csv
from collections import OrderedDict, Counter

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (QApplication, Qt, QWidget, QGridLayout, QHBoxLayout,
                        QVBoxLayout, QLabel, QGroupBox, QPushButton, QTableWidget,
                        QAbstractItemView, QLineEdit, QToolButton, QRadioButton,
                        QCheckBox, QSpinBox, QScrollArea)
except ImportError:                        
    from PyQt5.Qt import (QApplication, Qt, QWidget, QGridLayout, QHBoxLayout,
                        QVBoxLayout, QLabel, QGroupBox, QPushButton, QTableWidget,
                        QAbstractItemView, QLineEdit, QToolButton, QRadioButton,
                        QCheckBox, QSpinBox, QScrollArea)

from calibre.debug import iswindows
from calibre.ebooks.metadata import fmt_sidx
from calibre.gui2 import error_dialog, choose_files

import calibre_plugins.import_list.config as cfg
from calibre_plugins.import_list.common_compatibility import qSizePolicy_Preferred, qSizePolicy_Expanding
from calibre_plugins.import_list.common_icons import get_icon
from calibre_plugins.import_list.common_widgets import ReadOnlyTableWidgetItem
from calibre_plugins.import_list.tab_common import (DragDropComboBox,
                                AddRemoveFieldDialog, MatchGroupBox, create_standard_columns)
from calibre_plugins.import_list.encodings import EncodingComboBox
from calibre_plugins.import_list.tab_common import tidy as tidy_function

try:
    load_translations()
except NameError:
    pass

def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [str(cell, 'utf-8', errors='replace') for cell in row]

def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        try:
            yield line.encode('utf-8', errors='replace')
        except:
            # Going to just assume it is already encoded
            yield line

class CSVRowsTableWidget(QTableWidget):

    def __init__(self, parent):
        QTableWidget.__init__(self, parent)
        self.setSortingEnabled(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().setDefaultSectionSize(self.verticalHeader().minimumSectionSize())

    def populate_table(self, csv_rows):
        self.clear()
        self.setRowCount(len(csv_rows))
        header_labels = [str(col) for col in range(1, len(csv_rows[0])+1)]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.horizontalHeader().setStretchLastSection(True)

        for row, csv_row in enumerate(csv_rows):
            self.populate_table_row(row, csv_row)

        self.resizeColumnsToContents()

    def populate_table_row(self, row, csv_row):
        for col, col_data in enumerate(csv_row):
            self.setItem(row, col, ReadOnlyTableWidgetItem(col_data))

    def clear_table(self):
        self.clear()
        self.setRowCount(0)
        self.setColumnCount(0)

class ImportCSVTab(QWidget):

    def __init__(self, parent_page):
        self.parent_page = parent_page
        QWidget.__init__(self)
        self.csv_row_controls = OrderedDict()
        self._init_controls()
        self.possible_columns = create_standard_columns(self.parent_page.db)

    def _init_controls(self):
        self.block_events=True

        l = self.l = QGridLayout()
        self.setLayout(l)

        import_lbl = QLabel(_('&Import from file:'))
        import_lbl.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self.setting_lbl = QLabel('', self)
        self.setting_lbl.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.file_combo = DragDropComboBox(self, drop_mode='file')
        import_lbl.setBuddy(self.file_combo)
        l.addWidget(import_lbl, 0, 0, 1, 1)
        l.addWidget(self.setting_lbl, 0, 1, 1, 1)
        cfl = QHBoxLayout()
        l.addLayout(cfl, 1, 0, 1, 2)
        cfl.addWidget(self.file_combo, 1)
        self.choose_file_button = QToolButton(self)
        self.choose_file_button.setToolTip(_('Choose the file to import'))
        self.choose_file_button.setIcon(get_icon('images/ellipses.png'))
        self.choose_file_button.clicked.connect(self._choose_file)
        cfl.addWidget(self.choose_file_button)

        wl = QHBoxLayout()
        l.addLayout(wl, 2, 0, 1, 2)
        contents_lbl = QLabel(_('&Contents:'), self)
        #l.addWidget(contents_lbl, 2, 0, 1, 2)
        wl.addWidget(contents_lbl, 1)

        # Update: add encodings support {
        encoding_label = QLabel(_('&Encoding:'), self)
        self.encoding_combo = EncodingComboBox(self)
        encoding_label.setBuddy(self.encoding_combo)
        wl.addWidget(encoding_label)
        wl.addWidget(self.encoding_combo)
        #}

        self.content = CSVRowsTableWidget(self)
        contents_lbl.setBuddy(self.content)
        l.addWidget(self.content, 3, 0, 1, 2)
        l.setColumnStretch(0, 1)
        l.setRowStretch(3, 2)

        ol1 = QHBoxLayout()
        l.addLayout(ol1, 4, 0, 1, 2)

        dgb = QGroupBox(' '+_('&Delimiter:')+' ', self)
        ol1.addWidget(dgb)
        dl = QGridLayout()
        dgb.setLayout(dl)
        self.delimiter_tab_opt = QRadioButton(_('&Tab'), self)
        self.delimiter_other_opt = QRadioButton(_('&Other:'), self)
        self.delimiter_other_ledit = QLineEdit(self)
        self.delimiter_other_ledit.setFixedWidth(30)
        self.delimiter_other_opt.setChecked(True)
        dl.addWidget(self.delimiter_tab_opt, 0, 0, 1, 1)
        dl.addWidget(self.delimiter_other_opt, 0, 1, 1, 1)
        dl.addWidget(self.delimiter_other_ledit, 0, 2, 1, 1)
        dl.setRowStretch(2, 1)

        pgb = QGroupBox(' '+_('Processing:')+' ', self)
        ol1.addWidget(pgb, 1)
        pl = QGridLayout()
        pgb.setLayout(pl)
        self.skip_first_row_chk = QCheckBox(_('S&kip first row'), self)
        self.skip_first_row_chk.setToolTip(_('Select this option to ignore the first row of column headings'))
        self.unquote_chk = QCheckBox(_('&Unquote'), self)
        self.unquote_chk.setToolTip(_('Remove any quotes around columns of data'))
        # Update: option to disable tidying fields for csv {
        self.tidy_chk = QCheckBox(_('Tidy'), self)
        self.tidy_chk.setToolTip(_('Clean title and authors before importing. This is intended for web imports but is optional for csv\n'
                                   'It includes removing leading and trailing periods and commas, removing some special characters\n'
                                   'and removing numbers indicating a position at the begining of the string.'))
        # }
        pl.addWidget(self.skip_first_row_chk, 0, 0, 1, 1)
        pl.addWidget(self.unquote_chk, 0, 1, 1, 1)
        # Update: option to disable tidying fields for csv {
        pl.addWidget(self.tidy_chk, 0, 2, 1, 1)
        # }
        pl.setColumnStretch(2, 1)

        # update: add match by identifier {
        self.mgb = MatchGroupBox(self)
        self.match_layout = QVBoxLayout()
        self.match_layout.addWidget(self.mgb)
        l.addLayout(self.match_layout, 5, 0, 1, 2)
        #}
        
        cgb = QGroupBox(_(' &Columns To Import: '), self)
        self.csv_layout = QGridLayout()
        self.csv_layout.setSizeConstraint(self.csv_layout.SetMinAndMaxSize)
        cgb.setLayout(self.csv_layout)
        self.csv_layout.setColumnStretch(8, 1)
        # Update: add scrollbar {
        scroll = QScrollArea()
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidgetResizable(True)
        scroll.setSizePolicy(qSizePolicy_Expanding, qSizePolicy_Preferred)
        scroll.setWidget(cgb)
        scroll.setMinimumHeight(80)
        l.addWidget(scroll, 6, 0, 1, 2)
        l.setRowStretch(6, 1)
        #}
        # Controls will be added dynamically when grid is populated
        # Laying them out in label/spin pairs, three across per row

        butl = QHBoxLayout()
        l.addLayout(butl, 7, 0, 1, 2)

        self.clear_button = QPushButton(get_icon('trash.png'), _('&Clear'), self)
        self.clear_button.setToolTip(_('Clear all settings back to the defaults on this tab'))
        self.clear_button.clicked.connect(self._clear_to_defaults)
        self.add_field_button = QPushButton(get_icon('column.png'), _('&Fields')+'...', self)
        self.add_field_button.setToolTip(_('Select field(s) to import'))
        self.add_field_button.clicked.connect(self._add_field)
        # Update: add option to auto-map columns from csv headers {
        self.from_headers_button = QPushButton(get_icon('column.png'), _('&From headers')+'...', self)
        self.from_headers_button.setToolTip(_('Guess field(s) from csv headers'))
        self.from_headers_button.clicked.connect(self._row_controls_from_headers)
        #}
        self.reverse_list_checkbox = QCheckBox(_('Reverse order'), self)
        self.reverse_list_checkbox.setToolTip(_('Display the books in the opposite order to the source'))
        self.preview_button = QPushButton(get_icon('wizard.png'), _('&Preview'), self)
        self.preview_button.setToolTip(_('Preview the results in the books grid'))
        self.preview_button.clicked.connect(self._preview_rows)
        butl.addWidget(self.clear_button)
        butl.addWidget(self.add_field_button)
        butl.addStretch(1)
        butl.addWidget(self.from_headers_button)
        butl.addStretch(1)
        butl.addWidget(self.reverse_list_checkbox)
        butl.addWidget(self.preview_button)

        self.file_combo.currentIndexChanged.connect(self._on_file_change)        
        self.block_events=False

    def _add_field(self):
        used_fields = list(self.csv_row_controls.keys())
        d = AddRemoveFieldDialog(self, self.possible_columns, used_fields)
        if d.exec_() == d.Accepted:
            for remove_field in d.removed_names:
                self._clear_csv_controls_for_field(remove_field)
            for new_field in d.added_names:
                self._append_csv_row_controls(new_field)
            self.mgb._refresh_match_opts()
            self.resize_controls()

    def _clear_csv_controls_for_field(self, key):
        if key not in self.csv_row_controls:
            return
        # Remove all items from the layout
        for ckey in list(self.csv_row_controls.keys()):
            row_controls = self.csv_row_controls[ckey]
            self.csv_layout.removeWidget(row_controls['label'])
            row_controls['label'].setParent(None)
            self.csv_layout.removeWidget(row_controls['spin'])
            row_controls['spin'].setParent(None)
        # Delete the csv control
        row_controls = self.csv_row_controls[key]
        del self.csv_row_controls[key]
        # Layout the remaining controls again
        for i, ckey in enumerate(self.csv_row_controls.keys()):
            row = int(i / 3)
            col = int(2 * (i % 3))
            row_controls = self.csv_row_controls[ckey]
            self.csv_layout.addWidget(row_controls['label'], row, col, 1, 1)
            self.csv_layout.addWidget(row_controls['spin'], row, col + 1, 1, 1)

    def _clear_csv_controls(self, add_default_fields=True):
        for key in list(self.csv_row_controls.keys()):
            row_controls = self.csv_row_controls[key]
            self.csv_layout.removeWidget(row_controls['label'])
            row_controls['label'].setParent(None)
            self.csv_layout.removeWidget(row_controls['spin'])
            row_controls['spin'].setParent(None)
        self.csv_row_controls.clear()
        if add_default_fields:
            self._append_csv_row_controls('title')
            self._append_csv_row_controls('authors')

    def _append_csv_row_controls(self, field_name, spin_value=0):
        display_name = self.possible_columns.get(field_name, '')

        lbl = QLabel(display_name + ':', self)
        spin = QSpinBox(self)
        spin.setMinimum(0)
        spin.setValue(spin_value)
        row_controls = {}
        row_controls['label'] = lbl
        row_controls['spin'] = spin
        # Layout the controls in rows of three label/spin pairs
        row = int(len(self.csv_row_controls) / 3)
        col = int(2 * (len(self.csv_row_controls) % 3))
        self.csv_row_controls[field_name] = row_controls
        self.csv_layout.addWidget(lbl, row, col, 1, 1)
        self.csv_layout.addWidget(spin, row, col + 1, 1, 1)

    def _clear_to_defaults(self, clear_last=True, add_default_fields=True):
        self.block_events = True
        self._clear_setting_name(clear_last)
        self.file_combo.clearEditText()
        self.delimiter_other_opt.setChecked(True)
        self.delimiter_other_ledit.setText(',')
        self.skip_first_row_chk.setChecked(True)
        self.unquote_chk.setChecked(True)
        self.tidy_chk.setChecked(True)
        self.reverse_list_checkbox.setChecked(False)
        self._clear_csv_controls(add_default_fields)
        self.block_events = False
        self.content.clear_table()
        self.parent_page.clear_preview_books()
        self.mgb._refresh_match_opts()
        self.resize_controls()

    def _clear_setting_name(self, clear_last=True):
        if clear_last:
            self.parent_page.library_config[cfg.KEY_LAST_WEB_SETTING] = ''
        self.setting_lbl.setText('')
        self.parent_page.info['current_setting'] = ''

    def _choose_file(self):
        files = choose_files(None, _('import CSV file dialog'), _('Select a CSV file to import'),
                             all_files=True, select_only_single_file=True)
        if not files:
            return
        csv_file = files[0]
        if iswindows:
            csv_file = os.path.normpath(csv_file)

        self.block_events = True
        existing_index = self.file_combo.findText(csv_file, Qt.MatchExactly)
        if existing_index >= 0:
            self.file_combo.setCurrentIndex(existing_index)
        else:
            self.file_combo.insertItem(0, csv_file)
            self.file_combo.setCurrentIndex(0)
        self.block_events = False
        self._clear_setting_name()
        self._on_file_change()

    def _on_file_change(self):
        self.parent_page.clear_preview_books()
        self._populate_csv_table()

    def _open_file(self):
        csv_file = str(self.file_combo.currentText()).strip()
        if not csv_file:
            error_dialog(self, _('File not specified'), _('You have not specified a path to a CSV file'),
                         show=True)
            self.file_combo.setFocus()
            return
        if not os.path.exists(csv_file):
            error_dialog(self, _('File not found'), _('No file found at this location'),
                         show=True)
            return
        # Update our combo dropdown history if needed
        self.file_combo.reorder_items()
        return csv_file

    def _csv_to_rows(self):
        if self.block_events:
            return

        if self.delimiter_tab_opt.isChecked():
            delim = str('\t')
        else:
            delim = str(self.delimiter_other_ledit.text())

        if not delim:
            error_dialog(self, _('Invalid options'), _('You have not specified a delimiter'), show=True)
            return
        csv_file = self._open_file()
        if not csv_file:
            self.content.clear()
            self.parent_page.clear_preview_books()
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            quoting = csv.QUOTE_MINIMAL
            if not self.unquote_chk.isChecked():
                quoting = csv.QUOTE_NONE

            rows = []
            # Update: add encodings support {
            encoding = self.encoding_combo.currentEncoding()
            if encoding == 'utf-8': encoding = 'utf-8-sig'
            #}
            # Fix: open in Universal line mode
            with open(csv_file, 'r', newline='', encoding=encoding) as f:
                reader = csv.reader(f, dialect=csv.excel, delimiter=delim, quoting=quoting)
                for row in reader:
                    rows.append(row)
            return rows
        finally:
            QApplication.restoreOverrideCursor()

    def _populate_csv_table(self):
        rows = self._csv_to_rows()
        if rows:
            self.content.populate_table(rows)

    def _preview_rows(self):
        if self.block_events:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            skip_first_row = self.skip_first_row_chk.isChecked()
            # Update: option to disable tidying fields for csv {
            is_tidy = self.tidy_chk.isChecked()
            if is_tidy:
                tidy = tidy_function
            else:
                tidy = lambda field_name, text: '' if text is None else text.strip()
            # }
            rows = self._csv_to_rows()
            books = []
            if rows:
                self.content.populate_table(rows)
                fields = {}
                for field_name, controls in self.csv_row_controls.items():
                    spin = int(str(controls['spin'].value()))
                    if spin > 0:
                        fields[field_name] = spin

                custom_columns = self.parent_page.db.field_metadata.custom_field_metadata()
                for r, row in enumerate(rows):
                    if skip_first_row and r == 0:
                        continue
                    cols = len(row)
                    row_name_values = {}
                    for field_name, field_index in fields.items():
                        if field_index <= cols:
                            row_name_values[field_name] = row[field_index - 1]
                        else:
                            row_name_values[field_name] = ''

                    book = {}
                    for field_name, field_value in row_name_values.items():
                        series_index = '0'
                        if field_name == 'series_index' or (field_name.startswith('#') and field_name.endswith('_index')):
                            continue
                        col = {}
                        if field_name.startswith('#') and field_name in custom_columns:
                            col = custom_columns[field_name]
                        if field_name == 'series' or col.get('datatype','') == 'series':
                            series_name = tidy(field_name, field_value)
                            if field_name+'_index' in row_name_values:
                                series_index = row_name_values[field_name+'_index']
                            if series_name:
                                try:
                                    book[field_name] = '%s [%s]'%(series_name, fmt_sidx(series_index))
                                except:
                                    book[field_name] = series_name + ' [0]'
                        elif col.get('datatype','') == 'bool':
                            if field_value.lower() in ['true','yes','y','1']:
                                field_value = 'Yes'
                            elif field_value.lower() in ['n/a','undefined','']:
                                field_value = 'n/a'
                            else:
                                field_value = 'No'
                            book[field_name] = tidy(field_name, field_value)
                        else:
                            book[field_name] = tidy(field_name, field_value)
                    # Check to make sure that at least one of the columns has a value.
                    has_value = False
                    for v in book.values():
                        if v:
                            has_value = True
                            break
                    if has_value:
                        books.append(book)

            if self.reverse_list_checkbox.isChecked():
                books.reverse()
            columns = self._get_current_columns()
            self.parent_page.refresh_preview_books(columns, books, cfg.KEY_IMPORT_TYPE_CSV)
        finally:
            QApplication.restoreOverrideCursor()

    def _get_current_columns(self):
        # Identify which columns the user has configured
        columns = ['title', 'authors']
        for field_name in self.csv_row_controls.keys():
            if field_name not in columns:
                columns.append(field_name)
        return columns

    def restore_settings(self, library_config):
        self._clear_to_defaults(clear_last=False, add_default_fields=False)
        context = library_config[cfg.KEY_CURRENT][cfg.KEY_IMPORT_TYPE_CSV]

        self.file_combo.populate_items(library_config[cfg.KEY_CSV_FILES],
                                       context[cfg.KEY_CSV_FILE])

        self.block_events = True
        delimiter = context[cfg.KEY_CSV_DELIMITER]
        if delimiter == '\t':
            self.delimiter_tab_opt.setChecked(True)
        else:
            self.delimiter_other_opt.setChecked(True)
            self.delimiter_other_ledit.setText(delimiter)
        self.skip_first_row_chk.setChecked(context[cfg.KEY_CSV_SKIP_FIRST])
        self.unquote_chk.setChecked(context[cfg.KEY_CSV_UNQUOTE])
        # Update: option to disable tidying fields for csv {
        self.tidy_chk.setChecked(context[cfg.KEY_CSV_TIDY])
        # }
        self.reverse_list_checkbox.setChecked(context.get(cfg.KEY_CSV_REVERSE_LIST, False))

        # When populating, have to cater for our "default" rows.
        for data in context[cfg.KEY_CSV_DATA]:
            field_name = data[cfg.KEY_CSV_FIELD]
            field_index = data[cfg.KEY_CSV_FIELD_INDEX]
            # Update: add restored id_types to possible columns even if not returned by db.get_all_identifier_types()
            if field_name.startswith('identifier:') and not self.possible_columns.get(field_name):
                self.possible_columns[field_name] = field_name.replace('identifier','ID')
            #}
            self._append_csv_row_controls(field_name, field_index)

        # Update: add match by identifier {
        # this must be done after restoring csv rows to be able to restore match_by_identifier option
        match_settings = context[cfg.KEY_MATCH_SETTINGS]
        self.mgb.set_match_opts(match_settings)
        self.resize_controls()
        #}
        # Update: add encodings support {
        self.encoding_combo.setEncodings(context[cfg.KEY_CSV_COMBO_ENCODINGS])
        self.encoding_combo.setCurrentEncoding(context[cfg.KEY_CSV_ENCODING])
        #}
            
        last_setting_name = library_config.get(cfg.KEY_LAST_CSV_SETTING, '')
        self.setting_lbl.setText('<b>%s</b>'%last_setting_name)
        self.block_events = False

    def save_settings(self, library_config):
        library_config[cfg.KEY_CSV_FILES] = self.file_combo.get_items_list()
        context = library_config[cfg.KEY_CURRENT][cfg.KEY_IMPORT_TYPE_CSV]
        context[cfg.KEY_CSV_FILE] = str(self.file_combo.currentText())
        if self.delimiter_tab_opt.isChecked():
            context[cfg.KEY_CSV_DELIMITER] = '\t'
        else:
            context[cfg.KEY_CSV_DELIMITER] = str(self.delimiter_other_ledit.text())
        context[cfg.KEY_CSV_SKIP_FIRST] = self.skip_first_row_chk.isChecked()
        context[cfg.KEY_CSV_UNQUOTE] = self.unquote_chk.isChecked()
        # Update: option to disable tidying fields for csv {
        context[cfg.KEY_CSV_TIDY] = self.tidy_chk.isChecked()
        # }
        context[cfg.KEY_CSV_REVERSE_LIST] = self.reverse_list_checkbox.isChecked()
        # Update: add match by identifier {
        context[cfg.KEY_MATCH_SETTINGS] = self.mgb.get_match_opts()
        #}
        # Update: add encodings support {
        context[cfg.KEY_CSV_ENCODING] = self.encoding_combo.currentEncoding()
        context[cfg.KEY_CSV_COMBO_ENCODINGS] = self.encoding_combo.getEncodings()
        #}
        data_items = []
        for field_name, controls in self.csv_row_controls.items():
            data = {}
            data[cfg.KEY_CSV_FIELD] = field_name
            data[cfg.KEY_CSV_FIELD_INDEX] = int(str(controls['spin'].value()))
            data_items.append(data)
        context[cfg.KEY_CSV_DATA] = data_items

    # Update: Control the stretch factor of scroll dynamically {
    def resize_controls(self):
        # FIXME: there must be a more simple way to this in pyqt5
        controls_count = len(self.csv_row_controls.keys())
        if controls_count < 4:
            self.l.setRowStretch(6, 0)
        elif controls_count < 7:
            self.l.setRowStretch(6, 2)
        else:
            self.l.setRowStretch(6, 3)
    #}
    # Update: add option to auto-map columns from csv headers {

    def _row_controls_from_headers(self, columns=[]):
        import codecs
        try:
            headers = self._csv_to_rows()[0]
        except:
            return
        if not headers: return
        headers = [header.lower() for header in headers]
        try:
            if headers[0].startswith(codecs.BOM_UTF8.decode(encoding='utf-8')):
                headers[0] = headers[0].lstrip(codecs.BOM_UTF8.decode(encoding='utf-8'))
        except:
            pass
        duplicate_headers = [k for k,v in Counter(headers).items() if v>1]
        if columns:
            columns_to_include = columns
        else:
            columns_to_include = self.possible_columns.keys()
        self._clear_csv_controls(add_default_fields=False)
        for field in ['title','authors']:
            try:
                spin_value = headers.index(field) + 1
            except ValueError:
                spin_value = 0
            self._append_csv_row_controls(field, spin_value)
        for spin_value, field in enumerate(headers, 1):
            if field in duplicate_headers: continue
            if field in ['title','authors']: continue
            if field in columns_to_include:
                self._append_csv_row_controls(field, spin_value)
            elif '#'+field in columns_to_include:
                if '#'+field not in headers:
                    self._append_csv_row_controls('#'+field, spin_value)
            elif 'identifier:'+field.lstrip('#') in columns_to_include:
                if 'identifier:'+field.lstrip('#') not in headers:
                    self._append_csv_row_controls('identifier:'+field.lstrip('#'), spin_value)
        self.mgb._refresh_match_opts()
    #}
