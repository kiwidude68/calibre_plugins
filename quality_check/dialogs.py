from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import six
from six.moves import range
from six import text_type as unicode

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

try:
    from qt.core import (QVBoxLayout, QLabel, QRadioButton, QDialogButtonBox,
                          QGroupBox, QGridLayout, QComboBox, QProgressDialog,
                          QTimer, QIcon, QTableWidget, QHBoxLayout,
                          QAbstractItemView, Qt, QCheckBox, QSpinBox, QToolButton)
except:
    from PyQt5.Qt import (QVBoxLayout, QLabel, QRadioButton, QDialogButtonBox,
                          QGroupBox, QGridLayout, QComboBox, QProgressDialog,
                          QTimer, QIcon, QTableWidget, QHBoxLayout,
                          QAbstractItemView, Qt, QCheckBox, QSpinBox, QToolButton)

from calibre.ebooks.metadata import authors_to_string, fmt_sidx
from calibre.gui2 import gprefs, error_dialog
from calibre.gui2.dialogs.message_box import MessageBox

import calibre_plugins.quality_check.config as cfg
from calibre_plugins.quality_check.common_dialogs import SizePersistedDialog, ViewLogDialog
from calibre_plugins.quality_check.common_icons import get_icon
from calibre_plugins.quality_check.common_widgets import ImageTitleLayout, ReadOnlyTableWidgetItem


class QualityProgressDialog(QProgressDialog):

    def __init__(self, gui, book_ids, callback_fn, db, status_msg_type='books', action_type=_('Checking')):
        self.total_count = len(book_ids)
        QProgressDialog.__init__(self, '', _('Cancel'), 0, self.total_count, gui)
        self.setMinimumWidth(500)
        self.book_ids, self.callback_fn, self.db = book_ids, callback_fn, db
        self.action_type, self.status_msg_type = action_type, status_msg_type
        self.gui = gui
        self.setWindowTitle('%s %d %s...' % (self.action_type, self.total_count, self.status_msg_type))
        self.i, self.result_ids = 0, []
        # QTimer workaround on Win 10 on first go for Win10/Qt6 users not displaying dialog properly.
        QTimer.singleShot(100, self.do_book_action)
        self.exec_()

    def do_book_action(self):
        if self.wasCanceled():
            return self.do_close()
        if self.i >= self.total_count:
            return self.do_close()
        book_id = self.book_ids[self.i]
        self.i += 1

        dtitle = self.db.title(book_id, index_is_id=True)
        self.setWindowTitle(_('%s %d %s  (%d matches)...') % (self.action_type, self.total_count, self.status_msg_type, len(self.result_ids)))
        self.setLabelText('%s: %s'%(self.action_type, dtitle))
        if self.callback_fn(book_id, self.db):
            self.result_ids.append(book_id)
        self.setValue(self.i)

        QTimer.singleShot(0, self.do_book_action)

    def do_close(self):
        self.hide()
        self.gui = None


class CompareTypeComboBox(QComboBox):

    def __init__(self, parent, allow_equality=True):
        QComboBox.__init__(self, parent)
        self.addItems([_('less than'), _('greater than')])
        if allow_equality:
            self.addItems([_('equal to'), _('not equal to')])

    def select_text(self, selected_text):
        idx = self.findText(selected_text)
        if idx != -1:
            self.setCurrentIndex(idx)
        else:
            self.setCurrentIndex(0)


class CoverOptionsDialog(SizePersistedDialog):

    def __init__(self, parent):
        SizePersistedDialog.__init__(self, parent, 'quality check plugin:cover options dialog')

        self.initialize_controls()

        # Set some default values from last time dialog was used.
        last_opt = gprefs.get(self.unique_pref_name+':last_opt', 0)
        if last_opt == 0:
            self.opt_no_cover.setChecked(True)
        elif last_opt == 1:
            self.opt_file_size.setChecked(True)
        else:
            self.opt_dimensions.setChecked(True)
        size_check_type = gprefs.get(self.unique_pref_name+':last_size_check_type', 'less than')
        self.file_size_check_type.select_text(size_check_type)
        dimensions_check_type = gprefs.get(self.unique_pref_name+':last_dimensions_check_type', 'less than')
        self.dimensions_check_type.select_text(dimensions_check_type)
        last_size = gprefs.get(self.unique_pref_name+':last_size', 20)
        self.file_size_spin.setProperty('value', last_size)
        last_width = gprefs.get(self.unique_pref_name+':last_width', 300)
        self.image_width_spin.setProperty('value', last_width)
        last_height = gprefs.get(self.unique_pref_name+':last_height', 400)
        self.image_height_spin.setProperty('value', last_height)

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def initialize_controls(self):
        self.setWindowTitle('Quality Check')
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'images/quality_check.png', _('Cover Search Options'))
        layout.addLayout(title_layout)

        options_group = QGroupBox(_('Search library for books where'), self)
        layout.addWidget(options_group)
        options_layout = QGridLayout()
        options_group.setLayout(options_layout)
        self.opt_file_size = QRadioButton(_('Cover file size is'), self)
        options_layout.addWidget(self.opt_file_size, 0, 0, 1, 1)
        self.file_size_check_type = CompareTypeComboBox(self, allow_equality=False)
        options_layout.addWidget(self.file_size_check_type, 0, 1, 1, 1)
        self.file_size_spin = QSpinBox(self)
        self.file_size_spin.setMinimum(1)
        self.file_size_spin.setMaximum(99000000)
        options_layout.addWidget(self.file_size_spin, 0, 2, 1, 1)
        options_layout.addWidget(QLabel('kb'), 0, 3, 1, 1)

        self.opt_dimensions = QRadioButton(_('Cover dimensions are'), self)
        options_layout.addWidget(self.opt_dimensions, 1, 0, 1, 1)
        self.dimensions_check_type = CompareTypeComboBox(self)
        options_layout.addWidget(self.dimensions_check_type, 1, 1, 1, 1)
        self.image_width_spin = QSpinBox(self)
        self.image_width_spin.setMinimum(0)
        self.image_width_spin.setMaximum(99000000)
        options_layout.addWidget(self.image_width_spin, 1, 2, 1, 1)
        options_layout.addWidget(QLabel(_('width')), 1, 3, 1, 1)
        self.image_height_spin = QSpinBox(self)
        self.image_height_spin.setMinimum(0)
        self.image_height_spin.setMaximum(99000000)
        options_layout.addWidget(self.image_height_spin, 2, 2, 1, 1)
        options_layout.addWidget(QLabel(_('height')), 2, 3, 1, 1)

        self.opt_no_cover = QRadioButton(_('No cover'), self)
        options_layout.addWidget(self.opt_no_cover, 3, 0, 1, 1)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.ok_clicked)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def ok_clicked(self):
        if self.opt_no_cover.isChecked():
            gprefs[self.unique_pref_name+':last_opt'] = 0
        elif self.opt_file_size.isChecked():
            gprefs[self.unique_pref_name+':last_opt'] = 1
        else:
            gprefs[self.unique_pref_name+':last_opt'] = 2
        gprefs[self.unique_pref_name+':last_size_check_type'] = \
                            unicode(self.file_size_check_type.currentText()).strip()
        gprefs[self.unique_pref_name+':last_dimensions_check_type'] = \
                            unicode(self.dimensions_check_type.currentText()).strip()
        gprefs[self.unique_pref_name+':last_size'] = self.file_size
        gprefs[self.unique_pref_name+':last_width'] = self.image_width
        gprefs[self.unique_pref_name+':last_height'] = self.image_height
        self.accept()

    @property
    def check_type(self):
        if self.opt_file_size.isChecked():
            return unicode(self.file_size_check_type.currentText()).strip()
        elif self.opt_dimensions.isChecked():
            return unicode(self.dimensions_check_type.currentText()).strip()

    @property
    def file_size(self):
        return int(unicode(self.file_size_spin.value()))

    @property
    def image_width(self):
        return int(unicode(self.image_width_spin.value()))

    @property
    def image_height(self):
        return int(unicode(self.image_height_spin.value()))


class ResultsSummaryDialog(MessageBox): # {{{

    def __init__(self, parent, title, msg, log=None, det_msg=''):
        '''
        A modal popup that summarises the result of Quality Check with
        opportunity to review the log.

        :param log: An HTML or plain text log
        :param title: The title for this popup
        :param msg: The msg to display
        :param det_msg: Detailed message
        '''
        MessageBox.__init__(self, MessageBox.INFO, title, msg,
                det_msg=det_msg, show_copy_button=False,
                parent=parent)
        self.log = log
        self.vlb = self.bb.addButton(_('View log'), self.bb.ActionRole)
        self.vlb.setIcon(QIcon(I('debug.png')))
        self.vlb.clicked.connect(self.show_log)
        self.det_msg_toggle.setVisible(bool(det_msg))
        self.vlb.setVisible(bool(log.plain_text))

    def show_log(self):
        self.log_viewer = ViewLogDialog(_('Quality Check log'), self.log.html,
                parent=self)


class ExcludableMenusComboBox(QComboBox):

    def __init__(self, parent, last_menu_key):
        QComboBox.__init__(self, parent)
        self.populate_combo(last_menu_key)

    def populate_combo(self, last_menu_key):
        self.clear()
        selected_idx = 0
        self.menu_keys = []
        idx = -1
        hidden_menus = cfg.plugin_prefs[cfg.STORE_OPTIONS].get(cfg.KEY_HIDDEN_MENUS, [])
        for menu_key, value in cfg.PLUGIN_MENUS.items():
            if not value['excludable']:
                continue
            # Will also exclude menus that the user is not showing
            if menu_key in hidden_menus:
                continue
            idx += 1
            self.menu_keys.append(menu_key)
            if menu_key == last_menu_key:
                selected_idx = idx
            name = value['name']
            sub_menu = value['sub_menu']
            img = get_icon(value['image'])
            if sub_menu:
                name = sub_menu + ' -> ' + name
            self.addItem(img, name)
        self.setCurrentIndex(selected_idx)

    def get_selected_menu(self):
        return self.menu_keys[self.currentIndex()]



class ExcludeAddDialog(SizePersistedDialog):

    def __init__(self, parent, last_menu_key):
        SizePersistedDialog.__init__(self, parent, _('quality check plugin:exclude add dialog'))
        self.last_menu_key = last_menu_key

        self.initialize_controls()

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def initialize_controls(self):
        self.setWindowTitle(_('Quality Check Add Exclusions'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'images/quality_check.png', _('Exclude Books'))
        layout.addLayout(title_layout)

        layout.addSpacing(10)
        layout.addWidget(QLabel(_('Exclude selected books(s) from the following Quality Check:')))
        self.menus_combo = ExcludableMenusComboBox(self, self.last_menu_key)
        layout.addWidget(self.menus_combo)
        layout.addSpacing(10)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    @property
    def menu_key(self):
        return self.menus_combo.get_selected_menu()


class AuthorTableWidgetItem(ReadOnlyTableWidgetItem):
    def __init__(self, text, sort_key):
        ReadOnlyTableWidgetItem.__init__(self, text)
        self.sort_key = sort_key

    #Qt uses a simple < check for sorting items, override this to use the sortKey
    def __lt__(self, other):
        return self.sort_key < other.sort_key


class SeriesTableWidgetItem(ReadOnlyTableWidgetItem):
    def __init__(self, series, series_index):
        display = ''
        if series:
            display = '%s [%s]' % (series, fmt_sidx(series_index))
        ReadOnlyTableWidgetItem.__init__(self, display)
        self.sortKey = '%s%04d' % (series, series_index)

    #Qt uses a simple < check for sorting items, override this to use the sortKey
    def __lt__(self, other):
        return self.sortKey < other.sortKey


class ExcludeViewTableWidget(QTableWidget):

    def __init__(self, parent):
        QTableWidget.__init__(self, parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def populate_table(self, books):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(books))
        header_labels = ['Title', 'Author', 'Series']
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(24)
        self.horizontalHeader().setStretchLastSection(True)

        for row, book in enumerate(books):
            self.populate_table_row(row, book)

        self.setSortingEnabled(True)
        self.resizeColumnsToContents()
        self.setMinimumColumnWidth(0, 100)
        self.setMinimumColumnWidth(1, 100)
        self.setMinimumSize(400, 0)
        if len(books) > 0:
            self.selectRow(0)

    def setMinimumColumnWidth(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def populate_table_row(self, row, book):
        title_cell = ReadOnlyTableWidgetItem(book['title'])
        title_cell.setData(Qt.UserRole, book['calibre_id'])
        self.setItem(row, 0, title_cell)
        self.setItem(row, 1, AuthorTableWidgetItem(book['author'], book['author_sort']))
        self.setItem(row, 2, SeriesTableWidgetItem(book['series'], book['series_index']))

    def get_calibre_ids(self):
        ids = []
        for row in range(self.rowCount()):
            ids.append(self.item(row, 0).data(Qt.UserRole))
        return ids

    def remove_selected_rows(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        first_sel_row = self.currentRow()
        for selrow in reversed(rows):
            self.removeRow(selrow.row())
        if first_sel_row < self.rowCount():
            self.select_and_scroll_to_row(first_sel_row)
        elif self.rowCount() > 0:
            self.select_and_scroll_to_row(first_sel_row - 1)

    def select_and_scroll_to_row(self, row):
        self.selectRow(row)
        self.scrollToItem(self.currentItem())


class ExcludeViewDialog(SizePersistedDialog):

    def __init__(self, parent, db, last_menu_key):
        SizePersistedDialog.__init__(self, parent, _('quality check plugin:exclude view dialog'))
        self.db = db

        self.setWindowTitle(_('Quality Check View Exclusions'))

        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'images/quality_check.png', _('View Excluded Books'))
        layout.addLayout(title_layout)

        menus_layout = QHBoxLayout()
        layout.addLayout(menus_layout)
        menus_layout.addWidget(QLabel('Quality check:'))
        self.menus_combo = ExcludableMenusComboBox(self, last_menu_key)
        menus_layout.addWidget(self.menus_combo)
        menus_layout.addStretch(-1)

        books_layout = QHBoxLayout()
        layout.addLayout(books_layout)

        self.books_table = ExcludeViewTableWidget(self)
        books_layout.addWidget(self.books_table)

        button_layout = QVBoxLayout()
        books_layout.addLayout(button_layout)
        self.remove_button = QToolButton(self)
        self.remove_button.setToolTip(_('Remove selected books from the exclusions'))
        self.remove_button.setIcon(get_icon('list_remove.png'))
        self.remove_button.clicked.connect(self.remove_from_list)
        button_layout.addWidget(self.remove_button)
        button_layout.addStretch(-1)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

        self.menus_combo.currentIndexChanged.connect(self._on_menu_combo_changed)
        self._populate_books(last_menu_key)

    def remove_from_list(self):
        self.books_table.remove_selected_rows()

    @property
    def menu_key(self):
        return self.menus_combo.get_selected_menu()

    def get_calibre_ids(self):
        return self.books_table.get_calibre_ids()

    def _on_menu_combo_changed(self):
        menu_key = self.menus_combo.get_selected_menu()
        self._populate_books(menu_key)

    def _populate_books(self, menu_key):
        book_ids = cfg.get_valid_excluded_books(self.db, menu_key)
        books = self._convert_calibre_ids_to_books(book_ids)
        self.books_table.populate_table(books)

    def _convert_calibre_ids_to_books(self, ids):
        books = []
        for calibre_id in ids:
            if not self.db.data.has_id(calibre_id):
                continue
            mi = self.db.get_metadata(calibre_id, index_is_id=True)
            book = {}
            book['calibre_id'] = mi.id
            book['title'] = mi.title
            book['author'] = authors_to_string(mi.authors)
            book['author_sort'] = mi.author_sort
            book['series'] = mi.series
            if mi.series:
                book['series_index'] = mi.series_index
            else:
                book['series_index'] = 0
            books.append(book)
        return books


class SearchEpubDialog(SizePersistedDialog):

    def __init__(self, parent):
        SizePersistedDialog.__init__(self, parent, _('quality check plugin:search epub dialog'))

        self.initialize_controls()

        # Set some default values from last time dialog was used.
        search_opts = gprefs.get(self.unique_pref_name+':search_opts', {})

        self.previous_finds = search_opts.get('previous_finds', [])
        if self.previous_finds:
            self.search_combo.addItems(self.previous_finds)
            self.search_combo.setEditText(self.previous_finds[0])

        self.ignore_case_checkbox.setChecked(search_opts.get('ignore_case', True))
        self.show_all_matches_checkbox.setChecked(search_opts.get('show_all_matches', False))
        self.scope_html_checkbox.setChecked(search_opts.get('scope_html', True))
        self.scope_css_checkbox.setChecked(search_opts.get('scope_css', False))
        self.scope_plaintext_checkbox.setChecked(search_opts.get('scope_plaintext', False))
        self.scope_opf_checkbox.setChecked(search_opts.get('scope_opf', False))
        self.scope_ncx_checkbox.setChecked(search_opts.get('scope_ncx', False))
        self.scope_zip_checkbox.setChecked(search_opts.get('scope_zip', False))

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def initialize_controls(self):
        self.setWindowTitle('Quality Check')
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'search.png', _('Search ePubs'))
        layout.addLayout(title_layout)

        find_group = QGroupBox(_('Find expression'), self)
        layout.addWidget(find_group)
        find_layout = QGridLayout()
        find_group.setLayout(find_layout)

        self.search_combo = QComboBox(self)
        self.search_combo.setEditable(True)
        self.search_combo.setCompleter(None)
        find_layout.addWidget(self.search_combo, 0, 0, 1, 2)

        self.ignore_case_checkbox = QCheckBox(_('&Ignore case'), self)
        find_layout.addWidget(self.ignore_case_checkbox, 1, 0, 1, 1)
        self.show_all_matches_checkbox = QCheckBox(_('&Show all occurrences'), self)
        self.show_all_matches_checkbox.setToolTip(_('If unchecked, the search of each ePub is stopped as soon as the first match is found.\n'
                                                  'If checked, all occurrences will be displayed in the log but it will run much slower.'))
        find_layout.addWidget(self.show_all_matches_checkbox, 2, 0, 1, 2)

        layout.addSpacing(5)
        scope_group = QGroupBox(_('Scope'), self)
        layout.addWidget(scope_group)
        scope_layout = QGridLayout()
        scope_group.setLayout(scope_layout)

        self.scope_html_checkbox = QCheckBox(_('&HTML content'), self)
        self.scope_html_checkbox.setToolTip(_('Search all html content files, including any html tags.\n'
                                            'If you also ticked the Plain text content option, this option is ignored.'))
        self.scope_css_checkbox = QCheckBox(_('&CSS/xpgt stylesheets'), self)
        self.scope_css_checkbox.setToolTip(_('Search all css or Adobe .xpgt stylesheets'))
        self.scope_plaintext_checkbox = QCheckBox(_('&Plain text content'), self)
        self.scope_plaintext_checkbox.setToolTip(_('Search body text of html files with all html tags stripped.\n'
                                                 'If you also ticked the HTML content option, that is ignored in favour of this.'))
        self.scope_opf_checkbox = QCheckBox(_('&OPF manifest'), self)
        self.scope_opf_checkbox.setToolTip(_('Search the .opf manifest file'))
        self.scope_ncx_checkbox = QCheckBox(_('&NCX TOC'), self)
        self.scope_ncx_checkbox.setToolTip(_('Search the NCX table of contents file'))
        self.scope_zip_checkbox = QCheckBox(_('&Zip filenames'), self)
        self.scope_zip_checkbox.setToolTip(_('Search the filenames inside the ePub (zip) file'))
        scope_layout.addWidget(self.scope_html_checkbox, 3, 0, 1, 1)
        scope_layout.addWidget(self.scope_css_checkbox, 3, 1, 1, 1)
        scope_layout.addWidget(self.scope_plaintext_checkbox, 4, 0, 1, 1)
        scope_layout.addWidget(self.scope_opf_checkbox, 4, 1, 1, 1)
        scope_layout.addWidget(self.scope_ncx_checkbox, 5, 1, 1, 1)
        scope_layout.addWidget(self.scope_zip_checkbox, 5, 0, 1, 1)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.ok_clicked)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def ok_clicked(self):
        search_text = unicode(self.search_combo.currentText()).strip()
        if not search_text:
            return error_dialog(self, _('No find text'),
                _('You must specify a regular expression to search for.'), show=True)
        search_opts = {}
        self.previous_finds = [f for f in self.previous_finds if f != search_text]
        self.previous_finds.insert(0, search_text)
        # Keep last 10 items
        search_opts['previous_finds'] = self.previous_finds[:10]
        search_opts['ignore_case'] = self.ignore_case_checkbox.isChecked()
        search_opts['show_all_matches'] = self.show_all_matches_checkbox.isChecked()
        search_opts['scope_html'] = self.scope_html_checkbox.isChecked()
        search_opts['scope_css'] = self.scope_css_checkbox.isChecked()
        search_opts['scope_plaintext'] = self.scope_plaintext_checkbox.isChecked()
        search_opts['scope_opf'] = self.scope_opf_checkbox.isChecked()
        search_opts['scope_ncx'] = self.scope_ncx_checkbox.isChecked()
        search_opts['scope_zip'] = self.scope_zip_checkbox.isChecked()
        any_scope_checked = False
        for k,v in search_opts.items():
            if k.startswith('scope') and v:
                any_scope_checked = True
                break
        if not any_scope_checked:
            return error_dialog(self, _('No search scope'),
                _('You must specify a scope for the ePub search.'), show=True)
        gprefs[self.unique_pref_name+':search_opts'] = search_opts
        self.search_opts = search_opts
        self.accept()

    @property
    def search_options(self):
        return self.search_opts


class ApplyFixProgressDialog(QProgressDialog):

    def __init__(self, gui, title, book_ids, tdir, apply_fix_callback):
        self.total_count = len(book_ids)
        QProgressDialog.__init__(self, '', '', 0, self.total_count, gui)
        self.setWindowTitle(title % self.total_count)
        self.setMinimumWidth(500)
        self.book_ids = book_ids
        self.tdir = tdir
        self.gui = gui
        self.db = self.gui.current_db
        self.i = 0
        self.updated_ids = []
        self.apply_fix_callback = apply_fix_callback
        # QTimer workaround on Win 10 on first go for Win10/Qt6 users not displaying dialog properly.
        QTimer.singleShot(100, self.do_book_check)
        self.closed = False

    def do_book_check(self):
        if self.i >= self.total_count:
            return self.do_close()
        book_id = self.book_ids[self.i]
        self.i += 1

        title = self.db.title(book_id, index_is_id=True)
        self.setLabelText(_('Fixing')+': '+title)

        # Call our callback FIX function to perform the work.
        if self.apply_fix_callback(book_id):
            self.updated_ids.append(book_id)

        self.setValue(self.i)
        QTimer.singleShot(0, self.do_book_check)

    def do_close(self):
        self.hide()
        if self.updated_ids:
            self.db.update_last_modified(self.updated_ids)
        self.gui.status_bar.show_message(_('Fix completed'), 3000)
        self.gui = None
        self.db = None
        self.closed = True
