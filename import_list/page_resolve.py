from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import copy
from collections import OrderedDict, defaultdict
from functools import partial

try:
    from qt.core import (QApplication, Qt, QGridLayout, QLabel, QGroupBox, QWidget,
                        QVBoxLayout, QPushButton, QTableWidget, QDialogButtonBox,
                        QHBoxLayout, QAbstractItemView, QLineEdit, QToolButton,
                        QAction, QSplitter, QListWidget, QComboBox,
                        QListWidgetItem, QRadioButton, QModelIndex)
except ImportError:                        
    from PyQt5.Qt import (QApplication, Qt, QGridLayout, QLabel, QGroupBox, QWidget,
                        QVBoxLayout, QPushButton, QTableWidget, QDialogButtonBox,
                        QHBoxLayout, QAbstractItemView, QLineEdit, QToolButton,
                        QAction, QSplitter, QListWidget, QComboBox,
                        QListWidgetItem, QRadioButton, QModelIndex)

from calibre.ebooks.metadata import fmt_sidx, string_to_authors
from calibre.gui2 import error_dialog
from calibre.gui2.dialogs.confirm_delete import confirm
from calibre.utils.config import prefs
from calibre.utils.titlecase import titlecase

from calibre_plugins.import_list.algorithms import (get_title_algorithm_fn, get_author_algorithm_fn,
                                TITLE_AUTHOR_ALGORITHMS, TITLE_ONLY_ALGORITHMS,
                                get_title_tokens, get_author_tokens)
from calibre_plugins.import_list.common_icons import get_icon
from calibre_plugins.import_list.common_dialogs import SizePersistedDialog
from calibre_plugins.import_list.common_widgets import ReadOnlyTableWidgetItem
from calibre_plugins.import_list.models import (BookModel, BookSortFilterModel, FILTER_ALL,
                                                FILTER_MATCHED, FILTER_UNMATCHED)
from calibre_plugins.import_list.page_common import WizardPage, AUTHOR_SEPARATOR
from calibre_plugins.import_list.views import ListBookView, MatchedBookView

try:
    load_translations()
except NameError:
    pass


def title_author_tier_name(title_alg, author_alg):
    tier_name = '{} title'.format(title_alg)
    if author_alg:
        tier_name += ' / {} author'.format(author_alg)
    return tier_name.title()

class MetadataColumnsDialog(SizePersistedDialog):

    def __init__(self, parent, columns):
        SizePersistedDialog.__init__(self, parent, 'import list plugin:metadata column dialog')
        self.setWindowTitle(_('Update metadata fields'))
        self.avail_columns = columns
        self.selected_names = []

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.values_list = QListWidget(self)
        self.values_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.values_list.doubleClicked.connect(self._accept_clicked)
        layout.addWidget(self.values_list)

        hl = QHBoxLayout()
        layout.addLayout(hl)
        self.select_all_button = QPushButton(_('Select all'), self)
        self.select_all_button.clicked.connect(self._on_select_all_click)
        self.clear_all_button = QPushButton(_('Clear all'), self)
        self.clear_all_button.clicked.connect(self._on_clear_all_click)
        hl.addWidget(self.select_all_button)
        hl.addWidget(self.clear_all_button)

        layout.addSpacing(10)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._accept_clicked)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._populate_fields_list()

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def _on_select_all_click(self):
        for row in range(0, self.values_list.count()):
            item = self.values_list.item(row)
            item.setCheckState(Qt.Checked)

    def _on_clear_all_click(self):
        for row in range(0, self.values_list.count()):
            item = self.values_list.item(row)
            item.setCheckState(Qt.Unchecked)

    def _populate_fields_list(self):
        self.values_list.clear()
        last_selected = self.load_custom_pref('last_selected', [])
        sorted_keys = sorted(list(self.avail_columns.keys()), key=lambda k: self.avail_columns[k])
        for field_name in sorted_keys:
            display_name = self.avail_columns[field_name]
            if field_name.startswith('#'):
                display_name = '%s (%s)' % (display_name, field_name)
            item = QListWidgetItem(display_name, self.values_list)
            item.setData(Qt.UserRole, field_name)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            if field_name in last_selected:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.values_list.addItem(item)

    def _get_checked_field_names(self):
        values = []
        for row in range(0, self.values_list.count()):
            item = self.values_list.item(row)
            if item.checkState() == Qt.Checked:
                field_name = str(item.data(Qt.UserRole))
                values.append(field_name)
        return values

    def _accept_clicked(self):
        self.selected_names = self._get_checked_field_names()
        if len(self.selected_names) == 0:
            error_dialog(self, _('No fields selected'), _('You must select one or more fields first.'), show=True)
            return
        self.accept()

    def persist_custom_prefs(self):
        '''
        Invoked when the dialog is closing. Override this function to call
        save_custom_pref() if you have a setting you want persisted that you can
        retrieve in your __init__() using load_custom_pref() when next opened
        '''
        if len(self.selected_names) > 0:
            self.save_custom_pref('last_selected', self.selected_names)


def get_user_available_columns_map(db, cols):
    avail_cols = db.field_metadata.displayable_field_keys()
    valid_cols_map = OrderedDict()
    for col in cols:
        if col in avail_cols:
            valid_cols_map[col] = db.field_metadata[col]['name']
        elif col.lower().startswith('identifier:'):
            valid_cols_map[col] = 'ID:'+col[11:]
    return valid_cols_map


class SearchMatchesTableWidget(QTableWidget):

    def __init__(self, parent):
        QTableWidget.__init__(self, parent)
        self.setSortingEnabled(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().setDefaultSectionSize(24)

    def initialise(self, column_widths, display_cols_map):
        self.display_cols_map = display_cols_map
        self.setColumnCount(len(self.display_cols_map))
        self.setHorizontalHeaderLabels(list(self.display_cols_map.values()))
        self.populate_table([])

        if column_widths is None:
            for i, key in enumerate(self.display_cols_map.keys()):
                if key == 'title':
                    self._set_minimum_column_width(i, 150)
                else:
                    self._set_minimum_column_width(i, 100)
        else:
            for c,w in enumerate(column_widths):
                self.setColumnWidth(c, w)

    def populate_table(self, books):
        self.books = books
        self.setRowCount(0)
        self.setRowCount(len(books))
        for row, book in enumerate(books):
            self.populate_table_row(row, book)

    def _set_minimum_column_width(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def populate_table_row(self, row, book):
        for i, key in enumerate(self.display_cols_map.keys()):
            data = book['!calibre_'+key]
            self.setItem(row, i, ReadOnlyTableWidgetItem(data))


class ResolvePage(WizardPage):

    ID = 2

    def init_controls(self):
        self.block_events = True
        self.setTitle(_('Step 2: Match list of books against your library'))
        l = QVBoxLayout(self)
        self.setLayout(l)

        self.vert_splitter = QSplitter(self)
        self.vert_splitter.setOrientation(Qt.Vertical)
        self.vert_splitter.setChildrenCollapsible(False)

        list_gb = QGroupBox('', self)
        list_gb.setStyleSheet('QGroupBox { font-weight: bold; }')
        self.vert_splitter.addWidget(list_gb)
        book_list_box = QHBoxLayout()
        book_list_box.setContentsMargins(0, 0, 0, 0)
        list_gb.setLayout(book_list_box)

        self.horiz_splitter = QSplitter(self)
        self.horiz_splitter.setChildrenCollapsible(False)
        book_list_box.addWidget(self.horiz_splitter)

        # Books in list in top left section within the books grouping box, left side of splitter
        books_list_widget = QWidget(self)
        books_list_layout = QVBoxLayout()
        books_list_widget.setLayout(books_list_layout)
        self.horiz_splitter.addWidget(books_list_widget)
        list_books_label = QLabel(_('Books in list:'), self)
        list_books_label.setStyleSheet('QLabel { font-weight: bold; }')
        list_books_label.setMinimumHeight(24)
        books_list_layout.addWidget(list_books_label)
        self.list_book_view = ListBookView(self)
        books_list_layout.addWidget(self.list_book_view)

        # Matches in library top right section, right side of splitter
        matches_library_widget = QWidget(self)
        matches_library_layout = QGridLayout()
        matches_library_widget.setLayout(matches_library_layout)
        self.horiz_splitter.addWidget(matches_library_widget)
        self.horiz_splitter.setStretchFactor(0, 2)
        self.horiz_splitter.setStretchFactor(1, 3)

        filter_layout = QHBoxLayout()
        self.filter_all = QRadioButton(_('Show All'), self)
        self.filter_all.setChecked(True)
        self.filter_matched = QRadioButton(_('Matched'), self)
        self.filter_unmatched = QRadioButton(_('Unmatched'), self)
        for btn in [self.filter_all, self.filter_matched, self.filter_unmatched]:
            btn.clicked.connect(self._refresh_filter)
        filter_layout.addStretch(1)
        filter_layout.addWidget(self.filter_all)
        filter_layout.addWidget(self.filter_matched)
        tier_filter_combo = self.tier_filter_combo = QComboBox()
        tier_filter_combo.setCurrentIndex(-1)
        tier_filter_combo.activated.connect(self._refresh_filter)
        filter_layout.addWidget(self.tier_filter_combo)
        filter_layout.addWidget(self.filter_unmatched)

        self.matched_books_label = QLabel(_('Matches in library:'), self)
        self.matched_books_label.setStyleSheet('QLabel { font-weight: bold; }')
        matches_library_layout.addWidget(self.matched_books_label, 0, 0, 1, 1)
        matches_library_layout.addLayout(filter_layout, 0, 1, 1, 1)
        self.matched_book_view = MatchedBookView(self, self.db)
        matches_library_layout.addWidget(self.matched_book_view, 1, 0, 1, 2)
        matches_library_layout.setColumnStretch(0, 1)
        matches_library_layout.setColumnStretch(1, 2)
        matches_library_layout.setColumnStretch(2, 1)

        matches_buttons_layout = QVBoxLayout()
        matches_library_layout.addLayout(matches_buttons_layout, 1, 2, 1, 1)
        self.clear_match_button = QToolButton(self)
        self.clear_match_button.setIcon(get_icon('list_remove.png'))
        self.clear_match_button.setToolTip(_('Clear the match associated with the selected books in the list'))
        self.clear_match_button.clicked.connect(self._clear_match)
        self.remove_book_button = QToolButton(self)
        self.remove_book_button.setIcon(get_icon('minus.png'))
        self.remove_book_button.setToolTip(_('Remove the selected books from the list'))
        self.remove_book_button.clicked.connect(self._remove_book)
        self.empty_book_button = QToolButton(self)
        self.empty_book_button.setIcon(get_icon('add_book.png'))
        self.empty_book_button.setToolTip(_('Create an empty book for the selected books in the list'))
        self.empty_book_button.clicked.connect(self._match_empty_book)
        self.update_metadata_button = QToolButton(self)
        self.update_metadata_button.setIcon(get_icon('metadata.png'))
        self.update_metadata_button.setToolTip(_('Update metadata for the selected books in the list'))
        self.update_metadata_button.clicked.connect(self._update_metadata_for_book)
        self.revert_metadata_button = QToolButton(self)
        self.revert_metadata_button.setIcon(get_icon('edit-undo.png'))
        self.revert_metadata_button.setToolTip(_('Revert metadata for the selected books back to existing values'))
        self.revert_metadata_button.clicked.connect(self._revert_metadata_for_book)
        matches_buttons_layout.addWidget(self.clear_match_button)
        matches_buttons_layout.addWidget(self.empty_book_button)
        matches_buttons_layout.addWidget(self.update_metadata_button)
        matches_buttons_layout.addWidget(self.revert_metadata_button)
        matches_buttons_layout.addWidget(self.remove_book_button)
        matches_buttons_layout.addStretch(1)

        possible_matches_box = QGroupBox(_('Possible matches for selected book:'), self)
        possible_matches_box.setStyleSheet('QGroupBox { font-weight: bold; }')
        self.vert_splitter.addWidget(possible_matches_box)
        possible_matches_layout = QVBoxLayout()
        possible_matches_box.setLayout(possible_matches_layout)

        search_layout = QHBoxLayout()
        possible_matches_layout.addLayout(search_layout)
        search_label = QLabel(_('Search:'), self)
        self.search_ledit = QLineEdit(self)
        self.go_button = QPushButton(_('&Go!'), self)
        self.go_button.clicked.connect(partial(self._on_search_click))
        self.clear_button = QToolButton(self)
        self.clear_button.setIcon(get_icon('clear_left'))
        self.clear_button.clicked.connect(partial(self._on_clear_search_text))
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_ledit, 1)
        search_layout.addWidget(self.go_button)
        search_layout.addWidget(self.clear_button)

        search_matches_layout = QHBoxLayout()
        possible_matches_layout.addLayout(search_matches_layout)
        self.search_matches_table = SearchMatchesTableWidget(self)
        search_matches_layout.addWidget(self.search_matches_table, 1)

        search_buttons_layout = QVBoxLayout()
        search_matches_layout.addLayout(search_buttons_layout)
        search_buttons_layout.addStretch(1)
        self.select_book_button = QToolButton(self)
        self.select_book_button.setIcon(get_icon('ok.png'))
        self.select_book_button.setToolTip(_('Select this book as the match for this list title'))
        self.select_book_button.clicked.connect(self._on_search_matches_select)
        self.append_book_button = QToolButton(self)
        self.append_book_button.setIcon(get_icon('plus.png'))
        self.append_book_button.setToolTip(_('Append this book as a new item on the list'))
        self.append_book_button.clicked.connect(self._append_book)
        search_buttons_layout.addWidget(self.select_book_button)
        search_buttons_layout.addWidget(self.append_book_button)

        self.vert_splitter.setStretchFactor(0, 3)
        self.vert_splitter.setStretchFactor(1, 2)
        l.addWidget(self.vert_splitter, 1)

        self.list_book_view.doubleClicked.connect(self._on_book_list_double_clicked)
        self.search_matches_table.doubleClicked.connect(self._on_search_matches_double_clicked)
        self.list_book_view.verticalScrollBar().valueChanged[int].connect(self._sync_to_list_scrollbar)
        self.matched_book_view.verticalScrollBar().valueChanged[int].connect(self._sync_to_matched_scrollbar)
        self.is_scrolling = False

        self.block_events = False

        self._create_context_menu_actions()
        self._create_context_menus(self.list_book_view)
        self._create_context_menus(self.matched_book_view)
        self._create_search_matches_context_menus()

    def initializePage(self):
        if 'hash_maps' not in self.info:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.info['hash_maps'] = self.info['hash_maps_queue'].get()
            QApplication.restoreOverrideCursor()

        import_columns = self.info['book_columns']
        # Update: Add match by uuid {
        # delete uuid identifier (added only for matching) unless the user has a custom identifier named uuid
        if not 'uuid' in self.db.get_all_identifier_types():
            try:
                import_columns.remove('identifier:uuid')
            except Exception as e:
                pass
        #}
        # The display columns (used in search and the right-hand grid) must
        # always include series and tags, which will be placed after our two
        # other mandatory columns of title and author.
        display_columns = list(import_columns)
        if 'series' in display_columns:
            display_columns.remove('series')
        if 'tags' in display_columns:
            display_columns.remove('tags')
        display_columns.insert(2,'series')
        display_columns.insert(3,'tags')
        self.import_cols_map = get_user_available_columns_map(self.db, import_columns)
        self.display_cols_map = get_user_available_columns_map(self.db, display_columns)
        #print('Import columns map:', self.import_cols_map)
        #print('Display columns map:', self.display_cols_map)

        books = copy.deepcopy(self.info['books'])
        # Our books dict will only have the title and author from the first page
        # of the wizard. We want to attempt to match each book against your
        # calibre library.

        for book in books:
            self._apply_best_calibre_book_match(book)

        self.book_model = BookModel(self.db, books, self.import_cols_map, self.display_cols_map)
        self.proxy_model = BookSortFilterModel(self)
        self.proxy_model.setSourceModel(self.book_model)
        self.list_book_view.set_model(self.proxy_model, self.import_cols_map, self.book_model.headers)
        self.matched_book_view.set_model(self.proxy_model, self.import_cols_map, self.display_cols_map, self.book_model.editable_columns)
        self.list_book_view.selectRow(0)
        self.matched_book_view.setSelectionModel(self.list_book_view.selectionModel())
        self.list_book_view.selectionModel().currentChanged.connect(self._on_book_list_current_changed)
        self.list_book_view.selectionModel().selectionChanged.connect(self._on_book_list_selection_changed)

        column_widths = self.info['state'].get('resolve_search_column_widths', None)
        self.search_matches_table.initialise(column_widths, self.display_cols_map)

        self._update_book_counts()
        # If our first page needs a search, fire it off now
        if len(str(self.search_ledit.text())):
            self._on_search_click()
        # Precompute any tags to be added to empty books if user has them configured
        self.add_empty_tags = []
        empty_tags = prefs['new_book_tags']
        for tag in [t.strip() for t in empty_tags]:
            if tag:
                self.add_empty_tags.append(tag)

        horiz_splitter_state = self.info['state'].get('resolve_splitter_state_horiz', None)
        if horiz_splitter_state is not None:
            self.horiz_splitter.restoreState(horiz_splitter_state)
        vert_splitter_state = self.info['state'].get('resolve_splitter_state_vert', None)
        if vert_splitter_state is not None:
            self.vert_splitter.restoreState(vert_splitter_state)
        # Make sure the buttons are set correctly for the opening state
        self._update_book_list_buttons_state()
        self._update_match_buttons_state()
        self._on_book_list_current_changed(self.list_book_view.model().index(0,0,QModelIndex()), None)

        match_tiers = self.get_match_tiers()
        # clear combo in case the user presses previous and then next
        self.tier_filter_combo.clear()
        self.tier_filter_combo.addItems([''] + match_tiers)

        self._refresh_filter()

    def _create_context_menu_actions(self):
        self.clear_match_action = QAction(get_icon('list_remove.png'), _('&Clear match'), self)
        self.clear_match_action.setToolTip(self.clear_match_button.toolTip())
        self.clear_match_action.triggered.connect(self._clear_match)
        self.remove_book_action = QAction(get_icon('minus.png'), _('&Remove book'), self)
        self.remove_book_action.setToolTip(self.remove_book_button.toolTip())
        self.remove_book_action.triggered.connect(self._remove_book)
        self.sep1 = QAction(self)
        self.sep1.setSeparator(True)
        self.empty_book_action = QAction(get_icon('add_book.png'), _('Match &empty book'), self)
        self.empty_book_action.setToolTip(self.empty_book_button.toolTip())
        self.empty_book_action.triggered.connect(self._match_empty_book)
        self.update_metadata_action = QAction(get_icon('metadata.png'), _('&Update metadata'), self)
        self.update_metadata_action.setToolTip(self.update_metadata_button.toolTip())
        self.update_metadata_action.triggered.connect(self._update_metadata_for_book)
        self.revert_metadata_action = QAction(get_icon('edit-undo.png'), _('&Revert metadata'), self)
        self.revert_metadata_action.setToolTip(self.revert_metadata_button.toolTip())
        self.revert_metadata_action.triggered.connect(self._revert_metadata_for_book)
        self.swap_author_names_action = QAction(get_icon('swap.png'), _('S&wap Author Names'), self)
        self.swap_author_names_action.setToolTip(_('Swap selected author names between FN LN and LN,FN'))
        self.swap_author_names_action.triggered.connect(self._swap_author_names)
        self.sep2 = QAction(self)
        self.sep2.setSeparator(True)
        self.search_title_author_action = QAction(get_icon('search.png'), _('&Search for title/author'), self)
        self.search_title_author_action.setToolTip(_('&Search your library using a simplified title/author of this book'))
        self.search_title_author_action.triggered.connect(partial(self._force_search_book, True, True))
        self.search_title_action = QAction(get_icon('book.png'), _('Search for &title'), self)
        self.search_title_action.setToolTip(_('&Search your library using a simplified title of this book'))
        self.search_title_action.triggered.connect(partial(self._force_search_book, True, False))
        self.search_author_action = QAction(get_icon('user_profile.png'), _('Search for &author'), self)
        self.search_author_action.setToolTip(_('&Search your library using a simplified author of this book'))
        self.search_author_action.triggered.connect(partial(self._force_search_book, False, True))

    def _create_context_menus(self, table):
        table.setContextMenuPolicy(Qt.ActionsContextMenu)
        table.addAction(self.search_title_author_action)
        table.addAction(self.search_title_action)
        table.addAction(self.search_author_action)
        table.addAction(self.sep1)
        table.addAction(self.clear_match_action)
        table.addAction(self.empty_book_action)
        table.addAction(self.update_metadata_action)
        table.addAction(self.revert_metadata_action)
        table.addAction(self.swap_author_names_action)
        table.addAction(self.sep2)
        table.addAction(self.remove_book_action)

    def _create_search_matches_context_menus(self):
        table = self.search_matches_table
        table.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.select_book_action = QAction(get_icon('ok.png'), _('&Select Book'), table)
        self.select_book_action.setToolTip(self.select_book_button.toolTip())
        self.select_book_action.triggered.connect(self._on_search_matches_select)
        sep5 = QAction(table)
        sep5.setSeparator(True)
        self.append_book_action = QAction(get_icon('plus.png'), _('&Append to list'), table)
        self.append_book_action.setToolTip(self.append_book_button.toolTip())
        self.append_book_action.triggered.connect(self._append_book)

        table.addAction(self.select_book_action)
        table.addAction(sep5)
        table.addAction(self.append_book_action)

    def _sync_to_list_scrollbar(self, value):
        if self.is_scrolling:
            return
        self.is_scrolling = True
        self.matched_book_view.verticalScrollBar().setValue(value)
        self.is_scrolling = False

    def _sync_to_matched_scrollbar(self, value):
        if self.is_scrolling:
            return
        self.is_scrolling = True
        self.list_book_view.verticalScrollBar().setValue(value)
        self.is_scrolling = False

    def _update_book_list_buttons_state(self):
        is_row_selected = self.list_book_view.currentIndex().isValid()

        can_clear = can_add_empty = is_row_selected
        can_update_metadata = can_revert_metadata = can_swap_authors = is_row_selected
        book = None
        if is_row_selected:
            rows = self.list_book_view.selectionModel().selectedRows()
            for selrow in rows:
                actual_idx = self.proxy_model.mapToSource(selrow)
                book = self.book_model.books[actual_idx.row()]
                book_status = book['!status']
                if book_status in ['unmatched','multiple','added']:
                    can_clear = False
                if book_status in ['unmatched','multiple']:
                    can_swap_authors = False
                if book_status in ['added','matched','empty']:
                    can_add_empty = False
                if book_status != 'matched':
                    can_update_metadata = False
                if book['!overwrite_metadata'] == False:
                    can_revert_metadata = False
                else:
                    # Check if all the metadata fields are identical currently
                    all_same = True
                    for col in self.import_cols_map.keys():
                        if '$!calibre_'+col in book and book['!calibre_'+col] != book['$!calibre_'+col]:
                            all_same = False
                            break
                    if all_same:
                        can_revert_metadata = False

        self.clear_match_button.setEnabled(is_row_selected and can_clear)
        self.clear_match_action.setEnabled(self.clear_match_button.isEnabled())
        self.remove_book_button.setEnabled(is_row_selected and len(self.book_model.books) > 0)
        self.remove_book_action.setEnabled(self.remove_book_button.isEnabled())
        self.empty_book_button.setEnabled(is_row_selected and can_add_empty)
        self.empty_book_action.setEnabled(self.empty_book_button.isEnabled())
        self.update_metadata_button.setEnabled(is_row_selected and can_update_metadata)
        self.update_metadata_action.setEnabled(self.update_metadata_button.isEnabled())
        self.revert_metadata_button.setEnabled(is_row_selected and can_revert_metadata)
        self.revert_metadata_action.setEnabled(self.revert_metadata_button.isEnabled())
        self.swap_author_names_action.setEnabled(can_swap_authors)
        self.search_title_author_action.setEnabled(is_row_selected)
        self.search_title_action.setEnabled(is_row_selected)
        self.search_author_action.setEnabled(is_row_selected)

    def _update_match_buttons_state(self):
        have_books = len(self.search_matches_table.books) > 0
        is_row_selected = self.search_matches_table.currentRow() != -1
        self.select_book_button.setEnabled(have_books)
        self.select_book_action.setEnabled(is_row_selected and have_books)
        self.append_book_button.setEnabled(have_books)
        self.append_book_action.setEnabled(is_row_selected and have_books)

    def _clear_match(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            rows = self.list_book_view.selectionModel().selectedRows()
            for selrow in rows:
                actual_idx = self.proxy_model.mapToSource(selrow)
                book = self.book_model.books[actual_idx.row()]
                book['!status'] = 'unmatched'
                book['!id'] = ''
                book['!mi'] = None
                book['!overwrite_metadata'] = False
                book['!authors_sort'] = ''
                for col in self.display_cols_map.keys():
                    if col == 'title':
                        book['!calibre_title'] = _('*** No Match ***')
                    else:
                        book['!calibre_'+col] = ''
                        book['$!calibre_'+col] = ''
                idx = self.book_model.index(actual_idx.row(), actual_idx.row())
                self.book_model.dataChanged.emit(idx, idx)
            self._update_book_counts()
            self._update_book_list_buttons_state()
        finally:
            QApplication.restoreOverrideCursor()

    def _remove_book(self):
        message = '<p>'+_('Are you sure you want to remove the selected books from the list?')+'<p>'
        if not confirm(message,'import_list_delete_from_list', self):
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            rows = sorted(self.list_book_view.selectionModel().selectedRows())
            actual_idx = self.proxy_model.mapToSource(rows[0])
            sel_row = actual_idx.row()
            for selrow in reversed(rows):
                actual_idx = self.proxy_model.mapToSource(selrow)
                self.book_model.removeRow(actual_idx.row())

            cnt = len(self.book_model.books)
            if sel_row == cnt:
                sel_row = cnt - 1
            if cnt == 0:
                sel_row = -1
            else:
                self.list_book_view.selectRow(sel_row)
                self._refresh_selected_book(sel_row)
            self._update_book_counts()
            self._update_book_list_buttons_state()
        finally:
            QApplication.restoreOverrideCursor()

    def _match_empty_book(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            rows = self.list_book_view.selectionModel().selectedRows()
            for selrow in reversed(rows):
                actual_idx = self.proxy_model.mapToSource(selrow)
                book = self.book_model.books[actual_idx.row()]
                book['!status'] = 'empty'
                book['!id'] = ''
                book['mi'] = None
                book['!overwrite_metadata'] = False
                book['!authors_sort'] = ''
                book['!calibre_title'] = titlecase(book['title'])
                if book['authors']:
                    book['!calibre_authors'] = book['authors']
                else:
                    book['!calibre_authors'] = _('Unknown')
                book['!calibre_tags'] = ','.join(self.add_empty_tags)
                book['!calibre_series'] = ''
                # Now update all the other columns
                for col in self.import_cols_map.keys():
                    if col in ['title','authors']:
                        continue
                    if col == 'tags':
                        new_tags = [t.strip() for t in book['tags'].split(',') if len(t.strip()) > 0]
                        existing_tags = [t.strip() for t in book['!calibre_tags'].split(',') if len(t.strip()) > 0]
                        combined_tags = sorted(list(set(new_tags).union(set(existing_tags))))
                        book['!calibre_tags'] = ', '.join(combined_tags)
                    else:
                        book['!calibre_'+col] = book[col]
                # Show every column as having changed by setting original values to blank
                for col in self.import_cols_map.keys():
                    book['$!calibre_'+col] = ''
                idx = self.book_model.index(actual_idx.row(), actual_idx.row())
                self.book_model.dataChanged.emit(idx, idx)
            self._update_book_counts()
            self._update_book_list_buttons_state()
        finally:
            QApplication.restoreOverrideCursor()

    def update_metadata(self, fields_to_update):
        rows = self.list_book_view.selectionModel().selectedRows()
        for selrow in rows:
            actual_idx = self.proxy_model.mapToSource(selrow)
            book = self.book_model.books[actual_idx.row()]
            book['!overwrite_metadata'] = True
            for field in fields_to_update:
                # Handle special cases where we do not want to overwrite
                val = book[field]
                # use get method as 'identifier:idtype' has no cmeta
                cmeta = self.db.field_metadata.all_metadata().get(field, {})
                ism = cmeta.get('is_multiple', {}) and field not in ['authors','languages']
                if ism:
                    new = [t.strip() for t in val.split(',') if len(t.strip()) > 0]
                    existing = [t.strip() for t in book['!calibre_'+field].split(cmeta['is_multiple']['ui_to_list']) if len(t.strip()) > 0]
                    combined = sorted(list(set(new).union(set(existing))))
                    book['!calibre_'+field] = cmeta['is_multiple']['list_to_ui'].join(combined)
                else:
                    book['!calibre_'+field] = val

            idx = self.book_model.index(actual_idx.row(), actual_idx.row())
            self.book_model.dataChanged.emit(idx, idx)
        self._update_book_list_buttons_state()

    def _update_metadata_for_book(self):
        d = MetadataColumnsDialog(self, self.import_cols_map)
        if d.exec_() != d.Accepted:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.update_metadata(d.selected_names)
        finally:
            QApplication.restoreOverrideCursor()

    def _revert_metadata_for_book(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            rows = self.list_book_view.selectionModel().selectedRows()
            for selrow in rows:
                actual_idx = self.proxy_model.mapToSource(selrow)
                book = self.book_model.books[actual_idx.row()]
                book['!overwrite_metadata'] = False
                for col in self.import_cols_map.keys():
                    book['!calibre_'+col] = book['$!calibre_'+col]
                idx = self.book_model.index(actual_idx.row(), actual_idx.row())
                self.book_model.dataChanged.emit(idx, idx)
            self._update_book_list_buttons_state()
        finally:
            QApplication.restoreOverrideCursor()

    def _swap_author_names(self):
        rows = self.list_book_view.selectionModel().selectedRows()
        for selrow in rows:
            actual_idx = self.proxy_model.mapToSource(selrow)
            book = self.book_model.books[actual_idx.row()]
            if not book['!calibre_authors']:
                continue
            if book['!status'] == 'matched':
                book['!overwrite_metadata'] = True
            authors = [a.strip() for a in book['!calibre_authors'].split('&') if len(a.strip()) > 0]

            def swap_to_fn_ln(a):
                parts = a.split(',')
                if len(parts) <= 1:
                    return a
                surname = parts[0]
                return '%s %s' % (' '.join(parts[1:]), surname)

            def swap_to_ln_fn(a):
                parts = a.split(None)
                if len(parts) <= 1:
                    return a
                surname = parts[-1]
                return '%s, %s' % (surname, ' '.join(parts[:-1]))

            if ',' in authors[0]:
                authors = [swap_to_fn_ln(a) for a in authors]
            else:
                authors = [swap_to_ln_fn(a) for a in authors]

            book['!calibre_authors'] = AUTHOR_SEPARATOR.join(authors)
            idx = self.book_model.index(actual_idx.row(), actual_idx.row())
            self.book_model.dataChanged.emit(idx, idx)
        self._update_book_list_buttons_state()

    def _append_book(self):
        message = '<p>'+_('Are you sure you want to add the selected book to the list?')+'<p>'
        if not confirm(message,'reading_list_import_append_to_list', self):
            return
        match_book = self.search_matches_table.books[self.search_matches_table.currentRow()]
        # Going to assume we will insert just after the currently selected row.
        actual_idx = self.proxy_model.mapToSource(self.list_book_view.selectionModel().selectedRows()[0])
        row = actual_idx.row() + 1
        self.book_model.insertRow(row)
        book = self.book_model.books[row]
        for k,v in match_book.items():
            if k not in book:
                book[k] = v
        idx = self.book_model.index(row, row)
        self.book_model.dataChanged.emit(idx, idx)
        self._update_book_counts()

    def _force_search_book(self, include_title, include_author):
        actual_idx = self.proxy_model.mapToSource(self.list_book_view.selectionModel().selectedRows()[0])
        book = self.book_model.books[actual_idx.row()]
        self._on_clear_search_text()
        self._prepare_search_text(book, include_title, include_author)
        self._on_search_click()

    def _apply_best_calibre_book_match(self, book):
        book['!status'] = 'unmatched'
        book['!id'] = ''
        book['!mi'] = None
        book['!overwrite_metadata'] = False
        book['!match_tier'] = ''
        for col in self.import_cols_map.keys():
            if col == 'title':
                book['!calibre_title'] = '*** ' + _('No Match') + ' ***'
            else:
                book['!calibre_'+col] = ''

        # Update: add match by identifier {
        match_settings = self.get_match_settings()
        match_type = match_settings['match_method']
        method_name = '_apply_best_calibre_book_match_'+str(match_type).replace('/', '_')
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            try:
                method(book)
            except Exception as e:
                import traceback
                print(traceback.format_exc())
        #}

    def _apply_best_calibre_book_match_title_author(self, book):
        title = book['title']
        authors = book['authors']
        authors = string_to_authors(authors)
              
        def get_hashes_for_algorithm(title_alg, author_alg, title, authors):
            thash = ''
            ahashes = []
            rev_ahashes = []
            title_fn = get_title_algorithm_fn(title_alg)
            if title_fn is not None:
                thash = title_fn(title)
            author_fn = get_author_algorithm_fn(author_alg)
            if author_fn is not None:
                for author in authors:
                    ahash, rev_ahash = author_fn(author)
                    ahashes.append(ahash)
                    rev_ahashes.append(rev_ahash)

            ta_hashes = []
            if len(authors) > 0:
                for ahash in ahashes:
                    ta_hash = thash + ahash
                    ta_hashes.append(ta_hash)
            else:
                ta_hashes = [thash]
            rev_ta_hashes = []
            if len(authors) > 0:
                for rev_ahash in rev_ahashes:
                    if rev_ahash is not None and ( rev_ahash not in ahashes ):
                        rev_ta_hash = thash + rev_ahash
                        rev_ta_hashes.append(rev_ta_hash)
            else:
                rev_ta_hashes = []
            return ta_hashes, rev_ta_hashes

        # Determine a progression of which (title, author) algorithms to try
        algs = TITLE_AUTHOR_ALGORITHMS
        if not authors:
            # Rather than the full set just run the subset that only use title
            algs = TITLE_ONLY_ALGORITHMS

        #print('HASH MAPS:', self.info['hash_maps'])
        for title_alg, author_alg in algs:
            alg_hashes, rev_alg_hashes = get_hashes_for_algorithm(title_alg, author_alg, title, authors)
            #print('Alg_hash', alg_hash, 'Rev alg hash', rev_alg_hash)
            hash_map = self.info['hash_maps'][(title_alg, author_alg)]
            tier_name = title_author_tier_name(title_alg, author_alg)
            #print('Hash Map=', hash_map)
            matching_book_ids = set()
            #print(title, author, 'alg_hash:"%s"'%alg_hash)
            for alg_hash in alg_hashes:
                if alg_hash in hash_map:
                    matching_book_ids.update(hash_map[alg_hash])
            for rev_alg_hash in rev_alg_hashes:
                if rev_alg_hash is not None and rev_alg_hash in hash_map:
                    matching_book_ids.update(hash_map[rev_alg_hash])
            if len(matching_book_ids) == 1:
                book['!status'] = 'matched'
                book['!id'] = next(iter(matching_book_ids))
                book['!match_tier'] = tier_name
                self._populate_calibre_info_for_book(book)
                break
            elif len(matching_book_ids) > 1:
                book['!status'] = 'multiple'
                book['!id'] = matching_book_ids
                book['!match_tier'] = tier_name
                book['!calibre_title'] = _('*** Multiple Matches ***')
                break

    # Update: add match by identifier {
    def _apply_best_calibre_book_match_identifier(self, book):
        match_settings = self.get_match_settings()
        id_type = match_settings['id_type']
        # if id_type is not present in library but remaining as option because of a previous or
        # saved setting, reinsert an empty dict into hash_maps to avoid errors. no matching will occur.
        if not id_type in self.db.get_all_identifier_types():
            if not self.info['hash_maps'].get(id_type):
                self.info['hash_maps'][id_type] = defaultdict(set)
        #
        hash_map = self.info['hash_maps'][id_type]
        identifier = book.get('identifier:'+id_type)
        matching_book_ids = []
        if identifier:
            matching_book_ids = hash_map.get(identifier, [])
        if len(matching_book_ids) == 1:
            book['!status'] = 'matched'
            book['!id'] = next(iter(matching_book_ids))
            self._populate_calibre_info_for_book(book)
        elif len(matching_book_ids) > 1:
            book['!status'] = 'multiple'
            book['!id'] = matching_book_ids
            book['!calibre_title'] = '*** '+_('Multiple Matches')+' ***'

    def get_match_settings(self):
        return self.info['match_settings']
    #}

    def get_match_tiers(self):
        tier_names = []
        match_settings = self.get_match_settings()
        if match_settings.get('match_method') == 'title/author':
            from calibre_plugins.import_list.algorithms import CACHED_ALGORITHMS
            for title_alg, author_alg in CACHED_ALGORITHMS:
                tier_name = title_author_tier_name(title_alg, author_alg)
                tier_names.append(tier_name)
        return tier_names

    def _populate_calibre_info_for_book(self, book):
        book_id = book['!id']
        mi = self.db.get_metadata(book_id, index_is_id=True, get_user_categories=False)
        book['!mi'] = mi
        book['!calibre_title'] = mi.title
        book['!authors_sort'] = mi.author_sort
        book['!calibre_authors'] = AUTHOR_SEPARATOR.join(mi.authors)
        book['!calibre_series'] = ''
        series = mi.series
        if series is not None:
            series_index = mi.series_index
            book['!calibre_series'] = '%s [%s]'%(series, fmt_sidx(series_index))
        book['!calibre_tags'] = ''
        tags = mi.tags
        if tags is not None:
            book['!calibre_tags'] = ', '.join(tags)
        from calibre.utils.localization import calibre_langcode_to_name
        languages = map(calibre_langcode_to_name, mi.languages)
        if languages is not None:
            book['!calibre_languages'] = ', '.join(languages)

        for col in self.display_cols_map.keys():
            if col in ('title', 'authors', 'series', 'tags', 'languages'):
                continue
            book['!calibre_'+col] = mi.format_field(col, series_with_index=True)[1]
        # Show every column as being unchanged
        for col in self.import_cols_map.keys():
            book['$!calibre_'+col] = book['!calibre_'+col]

    def _on_book_list_current_changed(self, row, old_row):
        if self.block_events:
            return
        actual_idx = self.proxy_model.mapToSource(row)
        self._refresh_selected_book(actual_idx.row())

    def _refresh_selected_book(self, row):
        self.search_ledit.setText('')
        self._clear_match_list()
        if row < 0:
            return
        book = self.book_model.books[row]
        book_status = book['!status']
        if book_status == 'multiple':
            self.search_ledit.setPlaceholderText(_('Displaying all similar matches for this book'))
            self._display_multiple_matches(book['!id'])
        else:
            self._on_clear_search_text()
            self._prepare_search_text(book)

    def _on_book_list_selection_changed(self, sel, desel):
        if self.block_events:
            return
        self._update_book_list_buttons_state()

    def _on_book_list_double_clicked(self, row):
        actual_idx = self.proxy_model.mapToSource(row)
        book = self.book_model.books[actual_idx.row()]
        if book['!status'] == 'unmatched' or book['!status'] == 'matched':
            self._on_search_click()

    def _on_clear_search_text(self):
        self.search_ledit.setPlaceholderText(_('Search for a book in your library'))
        self.search_ledit.clear()

    def _prepare_search_text(self, book, include_title=True, include_author=True):
        query = ''
        if include_title:
            title = book.get('title','')
            query = ' '.join(get_title_tokens(title, strip_subtitle=False))
        if include_author:
            author = book.get('authors','')
            if author:
                author = author.partition('&')[0].strip()
            author_tokens = [t for t in get_author_tokens(author) if len(t) > 1]
            query += ' ' +  ' '.join(author_tokens)
        query = query.replace('  ', ' ')
        self.search_ledit.setText(query.strip())
        self.go_button.setAutoDefault(True)
        self.go_button.setDefault(True)

    def _on_search_click(self):
        query = str(self.search_ledit.text())
        QApplication.setOverrideCursor(Qt.WaitCursor)
        matches = self.db.search_getting_ids(query.strip(), None)
        QApplication.restoreOverrideCursor()
        self._display_multiple_matches(matches)

    def _on_search_matches_select(self):
        self._on_search_matches_double_clicked(self.search_matches_table.currentIndex())

    def _on_search_matches_double_clicked(self, row):
        match_book = self.search_matches_table.books[row.row()]
        actual_idx = self.proxy_model.mapToSource(self.list_book_view.selectionModel().selectedRows()[0])
        list_row = actual_idx.row()
        book = self.book_model.books[list_row]
        if book['!status'] in ['unmatched', 'multiple']:
            book['!status'] = 'matched'
            for k in match_book.keys():
                book[k] = match_book[k]
            idx = self.book_model.index(list_row, list_row)
            self.book_model.dataChanged.emit(idx, idx)
            self._update_book_counts()
            self._clear_match_list()
            self._update_match_buttons_state()
            self._update_book_list_buttons_state()

    def _display_multiple_matches(self, book_ids):
        match_books = {}
        for book_id in book_ids:
            match_book = { '!id': book_id }
            self._populate_calibre_info_for_book(match_book)
            match_books[book_id] = match_book
        # Sort by title and author
        skeys = sorted(list(match_books.keys()),
           key=lambda ckey: '%s%s' % (match_books[ckey]['!calibre_title'],
                                      match_books[ckey]['!authors_sort']))
        sorted_books = [match_books[key] for key in skeys]
        self.search_matches_table.populate_table(sorted_books)
        if sorted_books:
            self.search_matches_table.selectRow(0)
        self._update_match_buttons_state()

    def _clear_match_list(self):
        self.search_matches_table.populate_table([])
        self._update_match_buttons_state()

    def _refresh_filter(self):
        if self.filter_all.isChecked():
            filter_criteria = FILTER_ALL
        elif self.filter_matched.isChecked():
            filter_criteria = FILTER_MATCHED
        elif self.filter_unmatched.isChecked():
            filter_criteria = FILTER_UNMATCHED
        match_tier = self.tier_filter_combo.currentText()
        self.block_events = True
        self.proxy_model.set_filter_criteria(filter_criteria, match_tier)
        self.block_events = False
        actual_idx = self.proxy_model.mapToSource(self.list_book_view.model().index(0,0,QModelIndex()))
        self._refresh_selected_book(actual_idx.row())

    def _update_book_counts(self):
        matches_cnt = 0
        total = len(self.book_model.books)
        for book in self.book_model.books:
            if book['!status'] not in ['unmatched', 'multiple']:
                matches_cnt += 1
        if total == 0:
            self.matched_books_label.setText(_('Matches in library:'))
        elif total == 1 and matches_cnt == 1:
            self.matched_books_label.setText(_('Matches in library:(1 match)'))
        else:
            self.matched_books_label.setText(_('Matches in library:')+' (%(count)d of %(total)d)'%{'count': matches_cnt, 'total': total})
        self.completeChanged.emit()

    def get_search_matches_table_column_widths(self):
        table_column_widths = []
        for c in range(0, self.search_matches_table.columnCount()):
            table_column_widths.append(self.search_matches_table.columnWidth(c))
        return table_column_widths

    def isComplete(self):
        '''
        Don't allow the user onto the next wizard page if no matched/added/empty books
        '''
        books = [book for book in self.book_model.books if book['!status'] in ['matched','empty','added']]
        if not books:
            return False
        return True

    def validatePage(self):
        books = [book for book in self.book_model.books if book['!status'] in ['matched','empty','added']]
        self.info['save_books'] = books
        self.info['resolve_splitter_state_vert'] = bytearray(self.vert_splitter.saveState())
        self.info['resolve_splitter_state_horiz'] = bytearray(self.horiz_splitter.saveState())
        return True

