from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'


import copy, traceback, os
from threading import Thread
try:
    from queue import Queue
except ImportError:
    from Queue import Queue

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (Qt, QWidget, QTabWidget, QVBoxLayout, QTableWidget, QAbstractItemView,
                        QAction, QTableWidgetItem, QSplitter, QLabel, QHBoxLayout, QFont,
                        QCheckBox, QApplication)
except ImportError:                        
    from PyQt5.Qt import (Qt, QWidget, QTabWidget, QVBoxLayout, QTableWidget, QAbstractItemView,
                        QAction, QTableWidgetItem, QSplitter, QLabel, QHBoxLayout, QFont,
                        QCheckBox, QApplication)

from calibre.gui2.dialogs.confirm_delete import confirm
from calibre.constants import DEBUG

import calibre_plugins.import_list.config as cfg
from calibre_plugins.import_list.algorithms import LibraryHashBuilder
from calibre_plugins.import_list.common_compatibility import qSizePolicy_Ignored, qSizePolicy_Minimum
from calibre_plugins.import_list.common_icons import get_icon, get_pixmap
from calibre_plugins.import_list.common_dialogs import ViewLogDialog
from calibre_plugins.import_list.page_common import WizardPage
from calibre_plugins.import_list.tab_clipboard import ImportClipboardTab
from calibre_plugins.import_list.tab_csv import ImportCSVTab
from calibre_plugins.import_list.tab_settings import UserSettingsTab, PredefinedSettingsTab
from calibre_plugins.import_list.tab_webpage import ImportWebPageTab

try:
    load_translations()
except NameError:
    pass

def get_field_datatype(db, field):
    try:
        return db.field_metadata.all_metadata()[field]['datatype']
    except KeyError as e:
        pass
        # for non calibre fieldnames like 'identifier:isbn'
        return 'text'

def validation_error_message(exception):
    if isinstance(exception, ValueError):
        try:
            return exception.args[0]['message']
        except Exception as e:
            pass

def to_int(val, strict_int=True):
    '''
    calibre templates return numbers in text float form (e.g. 5.0)
    which fails when python try to convert using int('5.0')
    this function converts to float first
    '''
    try:
        val = float(val)
    except:
        raise ValueError
    if strict_int:
        if not val.is_integer():
            raise ValueError
    return int(val)

# Update: add validation {
class ValidationWidget(QWidget):
    def __init__(
        self,
        parent,
        icon_name='dialog_error.png',
        title='Validation Error(s) <a href="view_details">view details</a>'
    ):
        self.errors = {}
        self.parent = parent
        self._show_only_errors = False
        QWidget.__init__(self, parent)
        vl = QVBoxLayout()
        self.setLayout(vl)
        
        hl = QHBoxLayout()
        self.title_image_label = QLabel(self)
        self.update_title_icon(icon_name)
        hl.addWidget(self.title_image_label, 0, Qt.AlignVCenter)

        title_font = QFont()
        title_font.setPointSize(12)
        self.validation_label = QLabel(title, self)
        self.validation_label.setFont(title_font)
        self.validation_label.setSizePolicy(qSizePolicy_Minimum, qSizePolicy_Ignored)
        self.validation_label.linkActivated.connect(self._view_details)
        hl.addWidget(self.validation_label, 0, Qt.AlignVCenter)
        
        self.check_box = QCheckBox(_('Show only rows with errors'), self.parent)
        label = QLabel(
            _('<p style="font-style:italic;margin-left:30px;">(errors highlighted in <span style="color:red;">red</span>)</p>')
        )

        self.check_box.toggled.connect(self._check_button_state_changed)
        
        vl.addLayout(hl)
        vl.addWidget(self.check_box, 0, Qt.AlignTop)
        vl.addWidget(label)

    def update_title_icon(self, icon_name):
        pixmap = get_pixmap(icon_name)
        if pixmap:
            self.title_image_label.setPixmap(pixmap)
            self.title_image_label.setMaximumSize(24, 24)
            self.title_image_label.setScaledContents(True)

    def reset(self, errors):
        self.errors = errors
        self._parse_errors()
        self.check_box.setChecked(self._show_only_errors)
        self._check_button_state_changed()

    def _parse_errors(self):
        self.rows_with_errors = set()
        self.log = _('Some cells contain data that does not match calibre datatypes.\n'
                '\t\tErrors are detailed below:\n')
        for colname, v in self.errors.items():
            rows = [row for row in v.keys()]
            rows.sort()
            self.rows_with_errors.update(rows)
            if colname == 'title':
                details = ['{}'.format(row+1) for row in rows]
                self.log += _('\nTitle field is mandatory. The following rows contain empty titles:\n{}\n').format(', '.join(details))
            else:
                d = {
                    'colname': colname,
                    'datatype': get_field_datatype(self.parent.db, colname)
                }
                details = ['\t\t\trow ({}) => {}\n'.format(row+1, val) for row, val in v.items()]
                self.log += _('\nColumn "{colname}" must contain only data of type "{datatype}".\n'
                         '\t\tThe following rows have invalid type for column {colname}:\n').format(**d)
                self.log += '{}'.format(os.linesep).join(details)  

    def _view_details(self):
        ViewLogDialog(_('Validation errors details'), self.log, self.parent)

    def _hide_rows(self):
        rows_to_hide = set(range(self.parent.preview_table.rowCount())).difference(self.rows_with_errors)
        for row in rows_to_hide:
            self.parent.preview_table.hideRow(row)

    def _unhide_rows(self):
        for row in range(self.parent.preview_table.rowCount()):
            self.parent.preview_table.showRow(row)
    
    def _check_button_state_changed(self):
        if self.check_box.isChecked():
            self._show_only_errors = True
            self._hide_rows()
        else:
            self._show_only_errors = False
            self._unhide_rows()

    def _validate_preview_table(self, title_is_mandatory=True):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            # remove any validation errors from previous runs
            self._unhide_rows()
            self.hide()
            
            from calibre.utils.date import parse_date
            
            preview_table = self.parent.preview_table
            headers = preview_table.columns
            
            if preview_table.rowCount() == 0:
                return False

            errors = {}
            for column in range(0, len(headers)):
                colname = headers[column]
                check = {
                    'int': to_int,
                    'float': float,
                    'rating': float,
                    'datetime': parse_date
                }
                typ = get_field_datatype(self.parent.db, colname)
                if colname == 'title' and title_is_mandatory:
                    errors[colname] = {}
                    for row in range(preview_table.rowCount()):
                        val = preview_table.item(row, column).text().strip()
                        if val == '':
                            preview_table.item(row, column).setBackground(Qt.red)
                            preview_table.item(row, column).setToolTip(_('Title field is mandatory and cannot be empty'))
                            errors[colname][row] = val
                elif typ in check.keys():
                    errors[colname] = {}
                    for row in range(preview_table.rowCount()):
                        val = preview_table.item(row, column).text().strip()
                        if val == '': continue
                        try:
                            check[typ](val)
                        except Exception as e:
                            preview_table.item(row, column).setBackground(Qt.red)
                            msg = validation_error_message(e) or _('Data must be of type: {}').format(typ)
                            preview_table.item(row, column).setToolTip(msg)
                            errors[colname][row] = val
                            if DEBUG:
                                if not isinstance(e, ValueError):
                                    print(e)
            # use deepcopy to avoid RuntimeError: dictionary changed size during iteration
            for k, v in copy.deepcopy(errors).items():
                if v == {}:
                    errors.pop(k)
            if errors != {}:
                self.reset(errors)
                self.show()
                return False
            return True
        finally:
            QApplication.restoreOverrideCursor()
#}

class LoadHashMapsWorker(Thread):
    '''
    Worker thread to populate our hash maps, done on a background thread
    to keep the initial dialog display responsive
    '''
    def __init__(self, db, hash_maps_queue):
        Thread.__init__(self)
        self.db = db
        self.hash_maps_queue = hash_maps_queue

    def run(self):
        try:
            builder = LibraryHashBuilder(self.db)
            self.hash_maps_queue.put(builder.hash_maps)
        except:
            traceback.print_exc()


class PreviewBookTableWidget(QTableWidget):

    def __init__(self, parent, db, columns, column_widths):
        QTableWidget.__init__(self, parent)
        self.db = db
        self.setSortingEnabled(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.verticalHeader().setDefaultSectionSize(24)

        self.populate_table(columns, [])
        if column_widths is not None:
            for c,w in enumerate(column_widths):
                self.setColumnWidth(c, w)
                
    def create_headers(self, columns):
        # Remove any columns which won't be valid as composite munging into field
        if 'series_index' in columns:
            columns.remove('series_index')
        # Fix: remove custom series indices headers as well {
        series_idxs = [col for col in columns if col[-6:] == '_index' and self.db.field_metadata.custom_field_metadata().keys()]
        for col in series_idxs:
            columns.remove(col)
        #}
        self.columns = columns
        header_labels = []
        for column in self.columns:
            title = column
            if column in self.db.field_metadata.standard_field_keys():
                title = self.db.field_metadata[column]['name']
            elif column.lower().startswith('identifier:'):
                title = 'ID:'+column[11:]
            else:
                # TODO: Is a custom column - not currently supported
                pass
            header_labels.append(title)
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)

    def populate_table(self, columns, books):
        self.create_headers(columns)
        self.books = books
        self.setRowCount(0)
        self.setRowCount(len(books))

        for row, book in enumerate(books):
            self.populate_table_row(row, book)

    def populate_table_row(self, row, book):
        for i in range(0, len(self.columns)):
            self.setItem(row, i, QTableWidgetItem(book.get(self.columns[i], '')))

    def get_preview_books(self):
        for row in range(0, self.rowCount()):
            for i in range(0, len(self.columns)):
                column = self.columns[i]
                self.books[row][column] = str(self.item(row, i).text()).strip()
        return self.books

class ImportPage(WizardPage):

    ID = 1

    def init_controls(self):
        self.block_events = True
        self.setTitle(_('Step 1: Configure a list source'))
        l = QVBoxLayout(self)
        self.setLayout(l)

        self.splitter = QSplitter(self)

        self.tw = QTabWidget(self)
        self.splitter.addWidget(self.tw)

        self.user_settings_tab = UserSettingsTab(self, self.library_config[cfg.KEY_SAVED_SETTINGS])
        self.predefined_settings_tab = PredefinedSettingsTab(self)
        self.clipboard_tab = ImportClipboardTab(self)
        self.csv_tab = ImportCSVTab(self)
        self.web_page_tab = ImportWebPageTab(self)
        self.tw.addTab(self.user_settings_tab, _('User Settings'))
        self.tw.addTab(self.predefined_settings_tab, _('Predefined'))
        self.tw.addTab(self.clipboard_tab, _('Clipboard'))
        self.tw.addTab(self.csv_tab, _('CSV File'))
        self.tw.addTab(self.web_page_tab, _('Web Page'))
        self.tw.currentChanged[int].connect(self._current_tab_changed)

        columns = self.info['state'].get('import_preview_columns', ['title','authors','series','pubdate'])
        column_widths = self.info['state'].get('import_preview_column_widths', None)
        self.preview_table = PreviewBookTableWidget(self, self.db, columns, column_widths)
        # Update: add validation
        # put the preview table in VBox, to accomodate for validation errors above it
        rw = QWidget(self)
        self.vl = QVBoxLayout()
        rw.setLayout(self.vl)
        self.vw = ValidationWidget(self)
        self.vl.addWidget(self.vw)
        self.vw.hide()
        self.vl.addWidget(self.preview_table)
        self.vl.setContentsMargins(0, 0, 0, 0)
        self.splitter.addWidget(rw)
        #}
        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setChildrenCollapsible(False)
        l.addWidget(self.splitter, 1)

        view_as_type = self.library_config.get(cfg.KEY_LAST_VIEW_TYPE, 'list')
        if view_as_type == 'list':
            self.predefined_settings_tab.view_list_opt.setChecked(True)
        else:
            self.predefined_settings_tab.view_category_opt.setChecked(True)
        last_user = self.library_config.get(cfg.KEY_LAST_USER_SETTING, None)
        self.user_settings_tab.select_setting(last_user)
        last_predefined = self.library_config.get(cfg.KEY_LAST_PREDEFINED_SETTING, None)
        self.predefined_settings_tab.select_setting(last_predefined)

        self.block_events = False
        self._create_context_menu()
        self._rebuild_db_hash_maps()

    def _rebuild_db_hash_maps(self):
        if 'hash_maps' in self.info:
            del self.info['hash_maps']
        self.info['hash_maps_queue'] = Queue()
        worker = LoadHashMapsWorker(self.db, self.info['hash_maps_queue'])
        worker.start()

    def _create_context_menu(self):
        table = self.preview_table
        table.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.remove_book_action = QAction(get_icon('minus.png'), _('&Remove book'), table)
        self.remove_book_action.setToolTip(_('Remove selected books from the list'))
        self.remove_book_action.triggered.connect(self._remove_book)
        table.addAction(self.remove_book_action)
        # Update: export to csv {
        self.csv_book_action = QAction(get_icon('add_book.png'), _('&Export to csv'), table)
        self.csv_book_action.setToolTip(_('Export selected books to csv file'))
        self.csv_book_action.triggered.connect(self._export_to_csv)
        table.addAction(self.csv_book_action)
        #}

    def _current_tab_changed(self, idx):
        if hasattr(self.tw.widget(idx), 'preview_button'):
            pb = self.tw.widget(idx).preview_button
            pb.setAutoDefault(True)
            pb.setDefault(True)

    def _remove_book(self):
        message = '<p>'+_('Are you sure you want to remove the selected books from the list?')+'<p>'
        if not confirm(message,'import_list_delete_from_list', self):
            return
        rows = sorted(self.preview_table.selectionModel().selectedRows())
        for selrow in reversed(rows):
            #FIXME: hack to choose only visible rows. Select all (ctrl+a) selects visible and hidden rows
            if self.preview_table.isRowHidden(selrow.row()): continue
            #}
            self.preview_table.removeRow(selrow.row())
            self.preview_table.books.pop(selrow.row())
        self.completeChanged.emit()

    # Update: export to csv {
    def _export_to_csv(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            import csv
            from calibre.gui2 import choose_save_file
            
            rows = sorted(self.preview_table.selectionModel().selectedRows())
            fname = choose_save_file(self, 'export to csv', _('Choose file for exported csv'), initial_filename='ImportList.csv')
            if not fname:
                return
            
            #add an _index header for every series column
            headers = copy.copy(self.preview_table.columns)
            series_cols = [col for col in headers if get_field_datatype(self.db, col) == 'series']
            series_idxs = [headers.index(col) for col in series_cols]
            
            for col in reversed(series_cols):
                pos = self.preview_table.columns.index(col) + 1
                headers.insert(pos, col+'_index')
                
            with open(fname, 'w') as f:
                csv_writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                #FIXME: This is inexplicably working in py2 even though fields are in unicode
                csv_writer.writerow(headers)
                
                for selrow in reversed(rows):
                    #FIXME: hack to choose only visible rows. Select all (ctrl+a) selects visible and hidden rows
                    if self.preview_table.isRowHidden(selrow.row()): continue
                    #}
                    book = [ self.preview_table.item(selrow.row(), column).text().strip() for column in range(len(self.preview_table.columns)) ]
                    #replace series[idx] series and series_index
                    for idx in reversed(series_idxs):
                        series, sep, series_index = book[idx].rpartition('[')
                        series_index = series_index.strip().rstrip(']').strip()
                        series = series.strip()
                        book[idx] = series
                        book.insert(idx+1, series_index)
                    #
                    #FIXME: This is inexplicably working in py2 even though fields are in unicode
                    csv_writer.writerow(book)
        finally:
            QApplication.restoreOverrideCursor()
    #}

    def clear_preview_books(self):
        self.refresh_preview_books(columns=['title','authors'], books=[])

    def refresh_preview_books(self, columns, books, import_type=None):
        if not self.block_events:
            self.preview_table.populate_table(columns, books)
        if books:
            self.library_config[cfg.KEY_CURRENT][cfg.KEY_IMPORT_TYPE] = import_type
        self.completeChanged.emit()

    def request_load_settings(self, setting_name, is_predefined, edit_mode):
        if setting_name is not None:
            # Before we do anything further, call save_settings on tabs so that
            # the historical combos have their history stored for when repopulated
            for idx in range(0, self.tw.count()):
                if hasattr(self.tw.widget(idx), 'save_settings'):
                    self.tw.widget(idx).save_settings(self.library_config)

            if is_predefined:
                setting = copy.deepcopy(cfg.PREDEFINED_WEB_SETTINGS[setting_name])
                setting[cfg.KEY_IMPORT_TYPE] = cfg.KEY_IMPORT_TYPE_WEB
                setting[cfg.KEY_READING_LIST] = copy.deepcopy(cfg.DEFAULT_READING_LIST_VALUES)
            else:
                setting = self.library_config[cfg.KEY_SAVED_SETTINGS][setting_name]

            import_type = setting[cfg.KEY_IMPORT_TYPE]
            current = self.library_config[cfg.KEY_CURRENT]
            current[cfg.KEY_IMPORT_TYPE] = import_type
            current[import_type] = copy.deepcopy(setting)
            del current[import_type][cfg.KEY_IMPORT_TYPE]
            del current[import_type][cfg.KEY_READING_LIST]
            current[cfg.KEY_READING_LIST] = copy.deepcopy(setting[cfg.KEY_READING_LIST])

            related_tab_page = None
            if import_type == cfg.KEY_IMPORT_TYPE_CLIPBOARD:
                self.library_config[cfg.KEY_LAST_CLIPBOARD_SETTING] = setting_name
                related_tab_page = self.clipboard_tab
            elif import_type == cfg.KEY_IMPORT_TYPE_CSV:
                self.library_config[cfg.KEY_LAST_CSV_SETTING] = setting_name
                related_tab_page = self.csv_tab
            elif import_type == cfg.KEY_IMPORT_TYPE_WEB:
                self.library_config[cfg.KEY_LAST_WEB_SETTING] = setting_name
                related_tab_page = self.web_page_tab

            related_tab_page.restore_settings(self.library_config)

            if edit_mode:
                self.clear_preview_books()
                self.tw.setCurrentWidget(related_tab_page)
            else:
                related_tab_page._preview_rows()
            self.info['current_setting'] = '' if is_predefined else setting_name

    def get_preview_columns(self):
        return self.preview_table.columns

    def get_preview_table_column_widths(self):
        table_column_widths = []
        for c in range(0, self.preview_table.columnCount() - 1):
            table_column_widths.append(self.preview_table.columnWidth(c))
        return table_column_widths

    def isComplete(self):
        '''
        Don't allow the user onto the next wizard page without any rows of data
        or with a row that has no title
        '''
        # Update: add validation {
        # old title not empty validation is included here.
        if not self.vw._validate_preview_table():
            return False
        #}
        return True

    def initializePage(self):
        self.clipboard_tab.restore_settings(self.library_config)
        self.csv_tab.restore_settings(self.library_config)
        self.web_page_tab.restore_settings(self.library_config)

        tab_idx = self.library_config.get(cfg.KEY_LAST_TAB, 1)
        self.tw.setCurrentIndex(tab_idx)
        self._current_tab_changed(tab_idx)
        splitter_state = self.info['state'].get('import_splitter_state', None)
        if splitter_state is not None:
            self.splitter.restoreState(splitter_state)

    def validatePage(self):
        self.clipboard_tab.save_settings(self.library_config)
        self.csv_tab.save_settings(self.library_config)
        self.web_page_tab.save_settings(self.library_config)
        self.info['books'] = self.preview_table.get_preview_books()
        self.info['book_columns'] = self.get_preview_columns()
        self.info['import_splitter_state'] = bytearray(self.splitter.saveState())
        self.info['match_settings'] = None
        self.library_config[cfg.KEY_LAST_TAB] = self.tw.currentIndex()
        if self.tw.currentIndex() == 3:
            self.info['match_settings'] = self.csv_tab.mgb.get_match_opts()
        elif self.tw.currentIndex() == 4:
            self.info['match_settings'] = self.web_page_tab.mgb.get_match_opts()
        else:
            self.info['match_settings'] = {'match_method': 'title/author'}
        if self.predefined_settings_tab.view_list_opt.isChecked():
            self.library_config[cfg.KEY_LAST_VIEW_TYPE] = 'list'
        else:
            self.library_config[cfg.KEY_LAST_VIEW_TYPE] = 'category'
        self.library_config[cfg.KEY_LAST_USER_SETTING] = self.user_settings_tab.get_setting_name()
        self.library_config[cfg.KEY_LAST_PREDEFINED_SETTING] = self.predefined_settings_tab.get_setting_name()
        return True
