from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import re, collections, copy
from functools import partial

# calibre Python 3 compatibility.
from six import text_type as unicode
try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (Qt, QVBoxLayout, QLabel, QLineEdit, QApplication,
                          QGroupBox, QHBoxLayout, QToolButton, QTableWidgetItem,
                          QIcon, QTableWidget, QPushButton, QCheckBox,
                          QAbstractItemView, QDialogButtonBox, QAction,
                          QGridLayout, pyqtSignal, QUrl, QListWidget, QListWidgetItem,
                          QTextEdit, QSplitter, QWidget)
except ImportError:
    from PyQt5.Qt import (Qt, QVBoxLayout, QLabel, QLineEdit, QApplication,
                          QGroupBox, QHBoxLayout, QToolButton, QTableWidgetItem,
                          QIcon, QTableWidget, QPushButton, QCheckBox,
                          QAbstractItemView, QDialogButtonBox, QAction,
                          QGridLayout, pyqtSignal, QUrl, QListWidget, QListWidgetItem,
                          QTextEdit, QSplitter, QWidget)

from calibre.ebooks.metadata import MetaInformation
from calibre.gui2 import error_dialog, question_dialog, gprefs, open_url
from calibre.gui2.library.delegates import RatingDelegate, TextDelegate
from calibre.utils.date import qt_to_dt, UNDEFINED_DATE
from calibre.devices.usbms.driver import debug_print

import calibre_plugins.goodreads_sync.config as cfg
from calibre_plugins.goodreads_sync.common_compatibility import qSizePolicy_Minimum, qtDropActionCopyAction, qtDropActionMoveAction
from calibre_plugins.goodreads_sync.common_icons import get_icon, get_pixmap
from calibre_plugins.goodreads_sync.common_dialogs import SizePersistedDialog
from calibre_plugins.goodreads_sync.common_widgets import (DateDelegate, DateTableWidgetItem,
                            ImageTitleLayout, ReadOnlyTableWidgetItem, ReadOnlyLineEdit, get_date_format)
from calibre_plugins.goodreads_sync.core import update_calibre_isbn_if_required, get_searchable_author, CalibreDbHelper

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

READ_SHELF = 'read'
CURRENTLY_READING_SHELF = 'currently-reading'

KEY_DISPLAY_ACTIVE_SHELVES = 'display_active_shelves'
KEY_LAST_SELECTED_SHELVES = 'last_selected_shelves'

SHOW_BOOK_URL_PREFIX = '%s/book/show/' % cfg.URL
SHOW_BOOK_URL_PREFIX2 = '%s/book/show/' % cfg.URL_HTTPS

def get_urls_from_event(event):
    '''
    Accept a drop event and return a list of urls that can be read from
    and represent urls on the goodreads site.
    '''
    if event.mimeData().hasFormat('text/uri-list'):
        urls = [unicode(u.toString()).strip() for u in event.mimeData().urls()]
        return [u for u in urls if u.startswith(SHOW_BOOK_URL_PREFIX) or u.startswith(SHOW_BOOK_URL_PREFIX2)]


class TextWithLengthDelegate(TextDelegate):
    '''
    Override the calibre TextDelegate to set a maximum length.
    '''
    def __init__(self, parent, text_length=None):
        super(TextWithLengthDelegate, self).__init__(parent)
        self.text_length = text_length

    def createEditor(self, parent, option, index):
        editor = super(TextWithLengthDelegate, self).createEditor(parent, option, index)
        if self.text_length:
            editor.setMaxLength(self.text_length)
        return editor


class ImageLabel(QLabel):

    def __init__(self, parent, icon_name, size=16):
        super(ImageLabel,self).__init__(parent)
        pixmap = get_pixmap(icon_name)
        self.setPixmap(pixmap)
        self.setMaximumSize(size, size)
        self.setScaledContents(True)


class NumericTableWidgetItem(QTableWidgetItem):

    def __init__(self, number, is_read_only=False):
        super(NumericTableWidgetItem, self).__init__('')
        self.setData(Qt.DisplayRole, number)
        if is_read_only:
            self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)

    def value(self):
        return self.data(Qt.DisplayRole)


class RatingTableWidgetItem(QTableWidgetItem):

    def __init__(self, rating, is_read_only=False):
        super(RatingTableWidgetItem, self).__init__('')
        self.setData(Qt.DisplayRole, rating)
        if is_read_only:
            self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)


class SwitchEditionTableWidget(QTableWidget):

    book_selection_changed = pyqtSignal(object)

    def __init__(self, parent, id_caches, calibre_id):
        QTableWidget.__init__(self, parent)
        self.id_caches, self.calibre_id = (id_caches, calibre_id)
        self.create_context_menu()
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.itemSelectionChanged.connect(self.item_selection_changed)
        self.setAcceptDrops(True)

    def create_context_menu(self):
        self.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.view_book_action = QAction(_('View &book on Goodreads.com'), self)
        self.view_book_action.setIcon(get_icon('images/view_book.png'))
        self.view_book_action.triggered.connect(self.view_book_on_goodreads)
        self.addAction(self.view_book_action)
        sep1 = QAction(self)
        sep1.setSeparator(True)
        self.addAction(sep1)
        self.paste_url_action = QAction(_('Paste Goodreads.com url'), self)
        self.paste_url_action.setShortcut(_('Ctrl+V'))
        self.paste_url_action.triggered.connect(self.paste_url)
        self.addAction(self.paste_url_action)

    def populate_table(self, goodreads_edition_books):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(goodreads_edition_books))
        header_labels = [_('Title'), _('Cover'), _('Edition')]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(24)
        self.horizontalHeader().setStretchLastSection(True)

        self.goodreads_edition_books = goodreads_edition_books
        for row, book in enumerate(goodreads_edition_books):
            self.populate_table_row(row, book)

        self.resizeColumnsToContents()
        self.setMinimumColumnWidth(0, 150)
        self.setMinimumColumnWidth(1, 50)
        self.setMinimumColumnWidth(2, 100)
        self.setRangeColumnWidth(0, 150, 300) # Title
        self.setSortingEnabled(True)
        self.setMinimumSize(500, 0)
        if len(goodreads_edition_books) > 0:
            self.selectRow(0)

    def setMinimumColumnWidth(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def setRangeColumnWidth(self, col, minimum, maximum):
        self.setMinimumColumnWidth(col, minimum)
        if self.columnWidth(col) > maximum:
            self.setColumnWidth(col, maximum)

    def populate_table_row(self, row, goodreads_edition_book):
        # Check to see whether we have one or more calibre_ids matching this
        # goodreads id in our cache
        existing_calibre_ids = self.id_caches.get_calibre_ids_linked(
                                        goodreads_edition_book['goodreads_id'])
        title_item = GoodreadsTitleWidgetItem(goodreads_edition_book['goodreads_title'],
                                              existing_calibre_ids, self.calibre_id)
        title_item.setData(Qt.UserRole, row)
        self.setItem(row, 0, title_item)
        self.setItem(row, 1, ReadOnlyTableWidgetItem(goodreads_edition_book['goodreads_cover']))
        self.setItem(row, 2, ReadOnlyTableWidgetItem(goodreads_edition_book['goodreads_edition']))

    def item_selection_changed(self):
        has_selected_book = self.selectionModel().hasSelection()
        self.view_book_action.setEnabled(has_selected_book)
        self.book_selection_changed.emit(has_selected_book)

    def paste_url(self):
        cb = QApplication.instance().clipboard()
        txt = unicode(cb.text()).strip()
        if txt:
            self.add_url_to_grid(txt)

    def selected_goodreads_book(self):
        row = self.selectionModel().selectedRows()[0]
        return self.goodreads_edition_books[self.item(row.row(), 0).data(Qt.UserRole)]

    def view_book_on_goodreads(self):
        url = '%s/book/show/%s' % (cfg.URL, self.selected_goodreads_book()['goodreads_id'])
        open_url(QUrl(url))

    def dragEnterEvent(self, event):
        if not event.possibleActions() & (qtDropActionCopyAction | qtDropActionMoveAction):
            return
        urls = get_urls_from_event(event)
        if urls:
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = get_urls_from_event(event)
        event.setDropAction(qtDropActionCopyAction)
        # User has dropped a valid Goodreads url onto our dialog.
        # Insert it as a fake row at the top
        url = urls[0]
        self.add_url_to_grid(url)

    def add_url_to_grid(self, url):
        match = re.search(r'/show/(\d+)', url)
        if not match:
            return
        goodreads_id = match.group(1)
        goodreads_edition_book = {}
        goodreads_edition_book['goodreads_id'] = goodreads_id
        goodreads_edition_book['goodreads_title'] = url
        goodreads_edition_book['goodreads_cover'] = ''
        goodreads_edition_book['goodreads_edition'] = ''
        goodreads_edition_book['goodreads_isbn'] = ''
        self.goodreads_edition_books.insert(0, goodreads_edition_book)
        self.populate_table(self.goodreads_edition_books)
        self.selectRow(0)

    def dragMoveEvent(self, event):
        event.acceptProposedAction()


class SwitchEditionDialog(SizePersistedDialog):
    '''
    This dialog allows the user to pick a book from search results from Goodreads
    '''
    def __init__(self, parent, id_caches, calibre_book, goodreads_books,
                 next_book, enable_search=True):
        SizePersistedDialog.__init__(self, parent, 'goodreads sync plugin:switch edition dialog')
        self.calibre_book = calibre_book
        self.skip = False
        self.setWindowTitle(_('Switch Goodreads Edition'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        window_title = _('Goodreads.com Editions')
        title_layout = ImageTitleLayout(self, 'images/link_add_lg.png', window_title)
        layout.addLayout(title_layout)

        match_groupbox = QGroupBox(_('Calibre book:'))
        layout.addWidget(match_groupbox)
        match_layout = QGridLayout()
        match_groupbox.setLayout(match_layout)
        match_layout.addWidget(QLabel(_('Title:'), self), 0, 0, 1, 1)
        match_layout.addWidget(ReadOnlyLineEdit(calibre_book['calibre_title'], self), 0, 1, 1, 3)
        match_layout.addWidget(QLabel(_('Author:'), self), 1, 0, 1, 1)
        match_layout.addWidget(ReadOnlyLineEdit(calibre_book['calibre_author'], self), 1, 1, 1, 3)
        match_layout.addWidget(QLabel(_('Series:'), self), 2, 0, 1, 1)
        match_layout.addWidget(ReadOnlyLineEdit(calibre_book['calibre_series'], self), 2, 1, 1, 1)
        match_layout.addWidget(QLabel(_('ISBN:'), self), 2, 2, 1, 1)
        match_layout.addWidget(ReadOnlyLineEdit(calibre_book['calibre_isbn'], self), 2, 3, 1, 1)

        layout.addSpacing(5)
        layout.addWidget(QLabel(_('Select the Goodreads edition to link to this calibre book:'), self))
        self.pick_book_table = SwitchEditionTableWidget(self, id_caches,
                                                        calibre_book['calibre_id'])
        layout.addWidget(self.pick_book_table)
        self.pick_book_table.doubleClicked.connect(self.accept)
        self.pick_book_table.book_selection_changed.connect(self.handle_book_selection_changed)

        message = _('You can drag/drop a Goodreads website link to add it to the results.')
        layout.addWidget(QLabel(message, self))

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        if enable_search:
            search_button = self.button_box.addButton(_('Search Goodreads.com'), QDialogButtonBox.ResetRole)
            search_button.clicked.connect(self.search_on_goodreads)
        if next_book:
            self.skip_button = QPushButton(QIcon(I('forward.png')), _('Skip'), self)
            self.button_box.addButton(self.skip_button, QDialogButtonBox.ActionRole)
            tip = _("Skip this book and move to the next:\n'{0}'").format(next_book)
            self.skip_button.setToolTip(tip)
            self.skip_button.clicked.connect(self.skip_triggered)

        # Populate with data
        self.pick_book_table.populate_table(goodreads_books)
        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def search_on_goodreads(self):
        # Perform a URL search
        title = self.calibre_book['calibre_title']
        author = self.calibre_book['calibre_author']
        if title == _('Unknown'):
            title = ''
        if author == _('Unknown'):
            author = ''
        query = title
        if author:
            query = query + ' ' + get_searchable_author(author)
        query = quote_plus(query.strip().encode('utf-8')).replace('++', '+')
        url = '%s/search?search_type=books&search[query]=%s' % (cfg.URL, query)
        if not isinstance(url, bytes):
            url = url.encode('utf-8')
        open_url(QUrl.fromEncoded(url))

    def handle_book_selection_changed(self, selection_is_not_valid):
        ok_button = self.button_box.button(QDialogButtonBox.Ok)
        ok_button.setEnabled(selection_is_not_valid)

    def selected_goodreads_book(self):
        book = self.pick_book_table.selected_goodreads_book()
        return book

    def skip_triggered(self):
        self.skip = True
        self.accept()


class ActionStatus(object):
    '''
    Used as constants to define the possible status values for books when displayed
    in the add/remove from shelf and sync from shelf dialogs.
    The numeric values are used for sorting purposes
    '''
    NO_LINK = 0
    ADD_EMPTY = 1
    VALID = 5
    WARNING = 9


class ChooseShelvesToSyncDialog(SizePersistedDialog):

    def __init__(self, parent=None, plugin_action=None, grhttp=None, user_name=None, shelves=[]):
        SizePersistedDialog.__init__(self, parent, 'goodreads sync plugin:shelves sync dialog')
        self.setWindowTitle(_('Select shelves to sync from:'))
        self.grhttp, self.user_name, self.shelves = (grhttp, user_name, shelves)
        self.gui = parent
        self.plugin_action = plugin_action

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.default_prefs = { KEY_DISPLAY_ACTIVE_SHELVES: True, KEY_LAST_SELECTED_SHELVES:[] }
        other_prefs = gprefs.get(self.unique_pref_name+':other_prefs', self.default_prefs)

        self.values_list = QListWidget(self)
        self.values_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.values_list)

        self.display_active_shelves = QCheckBox(_('Show Active shelves only'))
        layout.addWidget(self.display_active_shelves)
        self.display_active_shelves.setChecked(other_prefs.get(KEY_DISPLAY_ACTIVE_SHELVES,True))
        self.display_active_shelves.stateChanged[int].connect(self._display_active_shelves_changed)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._accept_clicked)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._display_shelves(other_prefs[KEY_LAST_SELECTED_SHELVES])

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def _display_shelves(self, selected_shelves):
        is_active_only = self.display_active_shelves.isChecked()
        self.values_list.clear()
        for shelf in self.shelves:
            shelf_name = shelf['name']
            if is_active_only and not shelf['active']:
                continue
            icon = 'images/shelf.png'
            if shelf['exclusive']:
                icon = 'images/shelf_exclusive.png'
            item = QListWidgetItem(get_icon(icon), shelf_name, self.values_list)
            self.values_list.addItem(item)
            item.setSelected(shelf['name'] in selected_shelves)

    def _display_active_shelves_changed(self):
        selected_shelves = self._get_selected_shelf_names()
        self._display_shelves(selected_shelves)

    def _save_preferences(self):
        other_prefs = copy.deepcopy(self.default_prefs)
        other_prefs[KEY_DISPLAY_ACTIVE_SHELVES] = self.display_active_shelves.isChecked()
        other_prefs[KEY_LAST_SELECTED_SHELVES] = self._get_selected_shelf_names()
        gprefs[self.unique_pref_name+':other_prefs'] = other_prefs

    def _get_selected_shelf_names(self):
        values = []
        for item in self.values_list.selectedItems():
            values.append(unicode(item.text()))
        return values

    def _accept_clicked(self):
        self._save_preferences()
        self.selected_shelf_names = self._get_selected_shelf_names()
        if len(self.selected_shelf_names) == 0:
            error_dialog(self.gui, _('No shelves selected'), _('You must select one or more shelves first.'), show=True)
            return

        self.selected_shelves = []
        for shelf in self.shelves:
            if shelf['name'] in self.selected_shelf_names:
                self.selected_shelves.append(shelf)
        
        self.plugin_action.progressbar_show(1)
        self.goodreads_shelf_books = self.grhttp.get_goodreads_books_on_shelves(self.user_name, self.selected_shelves)
        self.plugin_action.progressbar_hide()
        self.accept()


class UpdateReadingProgressTableWidget(QTableWidget):

    search_for_goodreads_books = pyqtSignal(object, object)
    view_book = pyqtSignal(object)
    book_selection_changed = pyqtSignal(object)

    def __init__(self, parent, reading_progress_column, rating_column=None, date_read_column=None, review_text_column=None):
        QTableWidget.__init__(self, parent)
        self.pin_view = None
        self.reading_progress_column = reading_progress_column
        self.rating_column = rating_column
        self.date_read_column = date_read_column
        self.review_text_column = review_text_column
        self.create_context_menu()
        self.itemSelectionChanged.connect(self.item_selection_changed)
        self.doubleClicked.connect(self.search_for_goodreads_books_click)
        self.header_labels = [_('Status'), _('Title'), _('Author'), _('Series'), _('Progress'), _('Comment'), _('Rating'), _('Date Read'), _('Review')]
        self.format = get_date_format()

    def setMinimumColumnWidth(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def create_context_menu(self):
        self.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.search_action = QAction(get_icon('images/link_add.png'), _('Search for book in Goodreads')+'...', self)
        self.search_action.triggered.connect(self.search_for_goodreads_books_click)
        self.addAction(self.search_action)
        sep1 = QAction(self)
        sep1.setSeparator(True)
        self.addAction(sep1)
        self.view_book_action = QAction(get_icon('images/view_book.png'), _('&View book on Goodreads.com'), self)
        self.view_book_action.triggered.connect(self.view_book_on_goodreads_click)
        self.addAction(self.view_book_action)

    def populate_table(self, calibre_books):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(calibre_books))

        self.setColumnCount(len(self.header_labels))
        self.setHorizontalHeaderLabels(self.header_labels)
        self.verticalHeader().setDefaultSectionSize(24)

        # We need to resort the supplied data using the status attribute in the dictionary
        self.calibre_books = sorted(calibre_books, key=lambda k: k['status'])
        for row, book in enumerate(self.calibre_books):
            self.populate_table_row(row, book)

        self.resizeColumnsToContents()
        self.setMinimumColumnWidth(1, 120)
        self.setMinimumColumnWidth(2, 120)

        self.setMinimumColumnWidth(4, 40)
        self.setMinimumColumnWidth(5, 220)
        delegate = TextWithLengthDelegate(self, 420) # The status comment is limited to 420 characters. 
        self.setItemDelegateForColumn(5, delegate)
        delegate = RatingDelegate(self)
        self.setItemDelegateForColumn(6, delegate)
        self.setMinimumColumnWidth(6, 80)
        delegate = DateDelegate(self)
        self.setItemDelegateForColumn(7, delegate)

        self.setColumnHidden(6, True)
        self.setColumnHidden(7, True)
        self.setColumnHidden(8, True)

        self.setSortingEnabled(True)
        self.setMinimumSize(500, 0)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def populate_table_row(self, row, calibre_book):
        self.blockSignals(True)
        self.setSortingEnabled(False)

        self.setItem(row, 0, StatusDataWidgetItem(calibre_book['status_msg'], calibre_book['status']))
        item = SortableReadOnlyTableWidgetItem(calibre_book['calibre_title'], sort_key=calibre_book['calibre_title_sort'])
        item.setData(Qt.UserRole, calibre_book['calibre_id'])
        self.setItem(row, 1, item)
        item = SortableReadOnlyTableWidgetItem(calibre_book['calibre_author'], calibre_book['calibre_author_sort'])
        item.setData(Qt.UserRole, row)
        self.setItem(row, 2, item)
        self.setItem(row, 3, ReadOnlyTableWidgetItem(calibre_book['calibre_series']))
        progress = calibre_book['calibre_reading_progress'] if calibre_book['calibre_reading_progress'] >= 0 else -1
        self.setItem(row, 4, NumericTableWidgetItem(progress, is_read_only=False))
        self.setItem(row, 5, QTableWidgetItem(''))
        if progress >= 100:
            self.setItem(row, 6, RatingTableWidgetItem(calibre_book['calibre_rating'], is_read_only=False))
            self.setItem(row, 7, DateTableWidgetItem(calibre_book['calibre_date_read'],
                                                     is_read_only=False, default_to_today=True))
            self.setItem(row, 8, QTableWidgetItem(calibre_book['calibre_review_text']))
        else:
            self.setItem(row, 6, RatingTableWidgetItem(0, is_read_only=True))
            self.setItem(row, 7, DateTableWidgetItem(None, is_read_only=True, fmt=self.format))
            self.setItem(row, 8, NumericTableWidgetItem(''))
        
        self.setSortingEnabled(True)
        self.blockSignals(False)

    def update_books(self, calibre_books):
        if self.isColumnHidden(4) and self.isColumnHidden(5):
            return
        for row in range(self.rowCount()):
            calibre_id = self.item(row, 1).data(Qt.UserRole)
            for calibre_book in calibre_books:
                if calibre_book['calibre_id'] == calibre_id:
                    calibre_book['calibre_reading_progress'] = self.item(row, 4).data(Qt.DisplayRole)
                    calibre_book['status_comment_text'] = self.item(row, 5).data(Qt.DisplayRole)
                    if not self.isColumnHidden(6):
                        calibre_book['calibre_rating'] = self.item(row, 6).data(Qt.DisplayRole)
                    if not self.isColumnHidden(7):
                        qtdate = self.item(row, 7).data(Qt.DisplayRole)
                        debug_print("update_books - qtdate='%s'" % qtdate)
                        if not qtdate == '':
                            calibre_book['calibre_date_read'] = qt_to_dt(qtdate, as_utc=False)
                    if not self.isColumnHidden(8):
                        calibre_book['calibre_review_text'] = self.item(row, 8).data(Qt.DisplayRole)
                    break

    def item_selection_changed(self):
        selection_has_no_goodreads_id = True
        selection_is_not_valid = True
        if not self.selectionModel().hasSelection():
            selection_has_no_goodreads_id = False
            selection_is_not_valid = False
        else:
            for row in self.selectionModel().selectedRows():
                calibre_book_id = self.item(row.row(), 2).data(Qt.UserRole)
                calibre_book = self.calibre_books[calibre_book_id]
                if calibre_book['status'] == ActionStatus.VALID:
                    selection_is_not_valid = False
                if calibre_book['goodreads_id']:
                    selection_has_no_goodreads_id = False
        self.book_selection_changed.emit(selection_is_not_valid)
        self.search_action.setEnabled(selection_is_not_valid)
        self.view_book_action.setEnabled(not selection_has_no_goodreads_id)

    def view_book_on_goodreads_click(self):
        for row in self.selectionModel().selectedRows():
            calibre_book_id = self.item(row.row(), 2).data(Qt.UserRole)
            calibre_book = self.calibre_books[calibre_book_id]
            self.view_book.emit(calibre_book['goodreads_id'])

    def search_for_goodreads_books_click(self):
        rows = []
        calibre_books_to_search = []
        for row in self.selectionModel().selectedRows():
            calibre_book_id = self.item(row.row(), 2).data(Qt.UserRole)
            calibre_book = self.calibre_books[calibre_book_id]
            if calibre_book['status'] != ActionStatus.VALID:
                rows.append(row.row())
                calibre_books_to_search.append(calibre_book)
        if len(calibre_books_to_search) == 0:
            return
        self.search_for_goodreads_books.emit(rows, calibre_books_to_search)

    def show_columns(self, is_rating_visible, is_dateread_visible, is_reviewtext_visible):
        if self.rating_column:
            self.setColumnHidden(6, not is_rating_visible)
        if self.date_read_column:
            self.setColumnHidden(7, not is_dateread_visible)
        if self.review_text_column:
            self.setColumnHidden(8, not is_reviewtext_visible)


class UpdateReadingProgressDialog(SizePersistedDialog):
    '''
    This dialog previews and handles activity for updating the reading progress
    '''
    def __init__(self, parent, plugin_action, grhttp, id_caches, user_name, action, calibre_books):
        SizePersistedDialog.__init__(self, parent, 'goodreads sync plugin:update reading progress dialog')
        self.gui = parent
        self.grhttp, self.id_caches, self.user_name, self.action, self.calibre_books = \
            (grhttp, id_caches, user_name, action, calibre_books)
        self.update_isbn = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_UPDATE_ISBN, 'NEVER')
        self.default_prefs = { KEY_DISPLAY_ACTIVE_SHELVES: True, KEY_LAST_SELECTED_SHELVES:[] }
        self.reading_progress_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_READING_PROGRESS_COLUMN, '')
        self.rating_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_RATING_COLUMN, '')
        self.date_read_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_DATE_READ_COLUMN, '')
        self.review_text_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_REVIEW_TEXT_COLUMN, '')
        self.progress_is_percent = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_PROGRESS_IS_PERCENT, True)
        self.is_rating_visible = False
        self.is_dateread_visible = False
        self.is_review_text_visible = False
        self.plugin_action = plugin_action

        user_info = cfg.plugin_prefs[cfg.STORE_USERS].get(user_name)
        self.shelves = user_info[cfg.KEY_SHELVES]
        self.shelves_map = dict([(shelf['name'], shelf) for shelf in self.shelves])

        # Create all the widgets etc for our controls
        self.init_gui_layout()

        # Now update our books to set the status indicating errors, warnings or valid:
        for calibre_book in calibre_books:
            self.update_book_status(calibre_book)

        self.summary_table.populate_table(calibre_books)
        self.update_error_counts()        
        self.put_finished_on_read_shelf_clicked(self.put_finished_on_read_shelf_checked)
        
        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def init_gui_layout(self):
        self.setWindowTitle(_('Update Reading Progress'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        other_prefs = gprefs.get(self.unique_pref_name+':other_prefs', self.default_prefs)

        title_icon = 'images/add_to_shelf_lg.png'
        title_text = _('Update Reading Progress')
        title_layout = ImageTitleLayout(self, title_icon, title_text)
        layout.addLayout(title_layout)

        grid_layout = QGridLayout()
        layout.addLayout(grid_layout)

        message = _('To fix missing links, double click to search for a matching book in Goodreads')
        grid_layout.addWidget(QLabel(message, self), 0, 0, 1, 2)
        self.error_label = QLabel('', self)
        grid_layout.addWidget(self.error_label, 0, 1, Qt.AlignRight)

        self.summary_table = UpdateReadingProgressTableWidget(self, self.reading_progress_column, 
                                                              self.rating_column, self.date_read_column,
                                                              self.review_text_column)
        self.summary_table.view_book.connect(self.grhttp.view_book_on_goodreads)
        self.summary_table.search_for_goodreads_books.connect(self.handle_search_for_goodreads_books)
        self.summary_table.book_selection_changed.connect(self.handle_book_selection_changed)
        grid_layout.addWidget(self.summary_table, 1, 0, 1, 2)

        check_box_layout = QHBoxLayout()
        layout.addLayout(check_box_layout)
        self.put_reading_on_currently_reading_shelf = QCheckBox(_('Put books on currently-reading shelf'))
        self.put_reading_on_currently_reading_shelf.setToolTip(_("If the reading progress is being updated, but the books are not finished, put the books onto the 'currently-reading' shelf."))
        check_box_layout.addWidget(self.put_reading_on_currently_reading_shelf)
        self.put_reading_on_currently_reading_shelf.setChecked(other_prefs.get('put_reading_on_currently_reading_shelf',True))

        self.put_finished_on_read_shelf = QCheckBox(_('Put finished books on read shelf'))
        self.put_finished_on_read_shelf.setToolTip(_("If the reading progress is 100%, put the books onto the 'read' shelf."))
        check_box_layout.addWidget(self.put_finished_on_read_shelf)
        self.put_finished_on_read_shelf.setChecked(other_prefs.get('put_finished_on_read_shelf',True))
        self.put_finished_on_read_shelf.clicked.connect(self.put_finished_on_read_shelf_clicked)
        self.put_finished_on_read_shelf_clicked(other_prefs.get('put_finished_on_read_shelf',True))
        check_box_layout.addStretch()

        button_box = QDialogButtonBox()
        self.search_button = button_box.addButton( _('Search Goodreads')+'...', QDialogButtonBox.ResetRole)
        self.search_button.clicked.connect(self.summary_table.search_for_goodreads_books_click)
        self.search_button.setEnabled(False)
        action_button_name = _('Update Progress')
        self.action_button = button_box.addButton(action_button_name, QDialogButtonBox.AcceptRole)
        self.action_button.setAutoDefault(True)
        self.action_button.clicked.connect(self.action_button_clicked)
        self.cancel_button = button_box.addButton(_('Cancel'), QDialogButtonBox.RejectRole)
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(button_box)

        self.resize(self.sizeHint())

    def update_book_status(self, calibre_book):
        # Based on data in the book and the shelf set a status
        goodreads_id = calibre_book['goodreads_id']
        isbn = calibre_book['calibre_isbn']
        if not goodreads_id and not isbn:
            calibre_book['status_msg'] = _('No Goodreads book linked!')
            calibre_book['status'] = ActionStatus.NO_LINK
            return
        if not goodreads_id and isbn:
            # Now see if we can find it by an API call to Goodreads for this ISBN
            goodreads_id = self.grhttp.get_goodreads_id_for_isbn(isbn)
            if goodreads_id:
                calibre_book['goodreads_id'] = goodreads_id
            else:
                calibre_book['status'] = ActionStatus.NO_LINK
                calibre_book['status_msg'] = _('No Goodreads book linked!')
                return
        calibre_book['status'] = ActionStatus.VALID
        calibre_book['status_msg'] = _('Ready')

    def find_goodreads_id_on_shelf_contents(self, goodreads_shelf_books, isbn):
        # Currently we will only match on ISBN. Maybe in future will do title/author too
        if not isbn:
            return None
        for goodreads_id, goodreads_book in goodreads_shelf_books.items():
            if goodreads_book['goodreads_isbn'] == isbn:
                return goodreads_id

    def update_error_counts(self):
        self.error_count = 0
        self.warning_count = 0
        self.valid_count = 0
        for calibre_book in self.calibre_books:
            status = calibre_book['status']
            if status == ActionStatus.NO_LINK:
                self.error_count = self.error_count + 1
            elif status == ActionStatus.WARNING:
                self.warning_count = self.warning_count + 1
            else:
                self.valid_count = self.valid_count + 1
        text = _('{0} missing links').format(self.error_count)
        if self.warning_count > 0:
            text = _('{0}, {1} warnings').format(text, self.warning_count)
        self.error_label.setText(text)

    @property
    def put_reading_on_currently_reading_shelf_checked(self):
        return self.put_reading_on_currently_reading_shelf.checkState() == Qt.Checked

    @property
    def put_finished_on_read_shelf_checked(self):
        return self.put_finished_on_read_shelf.checkState() == Qt.Checked

    def put_finished_on_read_shelf_clicked(self, checked):
        self.is_rating_visible = self.shelves_map[READ_SHELF].get(cfg.KEY_ADD_RATING, False) and checked
        self.is_dateread_visible = self.shelves_map[READ_SHELF].get(cfg.KEY_ADD_DATE_READ, False) and checked
        self.is_review_text_visible = self.shelves_map[READ_SHELF].get(cfg.KEY_ADD_REVIEW_TEXT, False) and checked

        self.summary_table.show_columns(self.is_rating_visible, self.is_dateread_visible, self.is_review_text_visible)
        
    def action_button_clicked(self):
        self.save_preferences()
        self.action_button.setEnabled(False)

        # Grab latest values for rating and date read columns
        self.summary_table.update_books(self.calibre_books)

        client = self.grhttp.create_oauth_client(self.user_name)
        upload_progress = self.action == 'progress' and len(self.reading_progress_column) > 0
        upload_rating = self.is_rating_visible and len(self.rating_column) > 0
        upload_date_read = self.is_dateread_visible and len(self.date_read_column) > 0
        upload_review_text = self.is_review_text_visible and len(self.review_text_column) > 0
        currently_reading_books = []
        read_books = []
        self.plugin_action.progressbar_label(_('Updating Goodreads progress')+'...')
        self.plugin_action.progressbar_show(len(self.calibre_books))
        # Add/remove each linked book to the selected shelf
        for calibre_book in self.calibre_books:
            self.plugin_action.progressbar_increment()
            if calibre_book['status'] == ActionStatus.VALID:
                goodreads_id = calibre_book['goodreads_id']
                progress = int(calibre_book['calibre_reading_progress']) if calibre_book['calibre_reading_progress'] else None
                progress = progress if progress >=0 else None
                review_text = None
                calibre_book['status_comment_text'] if len(calibre_book.get('status_comment_text','')) > 0 else None 
                self.grhttp.update_status(client, goodreads_id, progress, self.progress_is_percent, review_text)
                if (upload_progress and progress):
                    calibre_book['goodreads_reading_progress'] = progress

                    if self.put_reading_on_currently_reading_shelf_checked and progress < 100:
                        currently_reading_books.append(calibre_book)
                        review_id = self.grhttp.add_remove_book_to_shelf(client, CURRENTLY_READING_SHELF, goodreads_id, 'add')

                    if self.put_finished_on_read_shelf_checked and progress >= 100:
                        read_books.append(calibre_book)
                        review_id = self.grhttp.add_remove_book_to_shelf(client, READ_SHELF, goodreads_id, 'add')
                        # If adding books and rating/date read columns update the Goodreads review
                        if review_id:
                            if review_id and (upload_rating or upload_date_read or upload_review_text):
                                rating = None
                                date_read = None
                                review_text = None
                                if upload_rating:
                                    rating = int(calibre_book['calibre_rating']) / 2
                                    if rating:
                                        calibre_book['goodreads_rating'] = rating
                                if upload_date_read:
                                    date_read = calibre_book['calibre_date_read']
                                    if date_read:
                                        calibre_book['goodreads_read_at'] = date_read
                                if upload_review_text:
                                    review_text = calibre_book['calibre_review_text']
                                    if review_text:
                                        calibre_book['goodreads_review_text'] = review_text
                                self.grhttp.update_review(client, READ_SHELF, review_id, goodreads_id, rating, date_read, review_text)
        # Finally, apply any "add" actions to books that were added to shelves
        if len(currently_reading_books) > 0:
            self._apply_add_actions_for_books(currently_reading_books, CURRENTLY_READING_SHELF, upload_progress)
        if len(read_books) > 0:
            self._apply_add_actions_for_books(read_books, READ_SHELF, upload_progress, upload_rating, upload_date_read, upload_review_text)

        self.accept()
        self.plugin_action.progressbar_hide()
    
    def _apply_add_actions_for_books(self, added_books, shelf_name, upload_progress, upload_rating=None, upload_date_read=None, upload_review_text=None):
        add_actions = []
        # Include some actions for setting our rating/date read/review text if appropriate
        if upload_progress:
            update_progress_action = {'action':'ADD', 'column':self.reading_progress_column, 'value':'goodreads_reading_progress'}
            add_actions.append(update_progress_action)
            if self.put_finished_on_read_shelf_checked:
                if upload_rating:
                    update_rating_action = {'action':'ADD', 'column':self.rating_column, 'value':'goodreads_rating'}
                    add_actions.append(update_rating_action)
                if upload_date_read:
                    upload_date_read_action = {'action':'ADD', 'column':self.date_read_column, 'value':'read_at'}
                    add_actions.append(upload_date_read_action)
                if upload_review_text:
                    upload_review_text_action = {'special':'review_text', 'action':'ADD', 'column':self.review_text_column, 'value':''}
                    add_actions.append(upload_review_text_action)
                add_actions.extend(self.shelves_map[shelf_name].get(cfg.KEY_ADD_ACTIONS,[]))
        if len(add_actions) > 0:
            self.plugin_action.progressbar_label(_("Updating books in calibre..."))
            CalibreDbHelper().apply_actions_to_calibre(self.gui, added_books, add_actions)

    def save_preferences(self):
        other_prefs = copy.deepcopy(self.default_prefs)
        other_prefs['put_finished_on_read_shelf'] = self.put_finished_on_read_shelf_checked
        other_prefs['put_reading_on_currently_reading_shelf'] = self.put_reading_on_currently_reading_shelf_checked
        gprefs[self.unique_pref_name+':other_prefs'] = other_prefs

    def handle_search_for_goodreads_books(self, rows, calibre_books):
        for index, row in enumerate(rows):
            calibre_book = calibre_books[index]
            title = calibre_book['calibre_title']
            author = calibre_book['calibre_author']
            next_book = None
            if index < len(calibre_books) - 1:
                next_book = calibre_books[index + 1]['calibre_title']
            goodreads_books = self.grhttp.search_for_goodreads_books(title, author)
            d = PickGoodreadsBookDialog(self, self.grhttp, self.id_caches, calibre_book,
                                        goodreads_books, next_book)
            d.exec_()
            if d.skip:
                continue
            if d.result() != d.Accepted:
                return
            goodreads_book = d.selected_goodreads_book()
            if goodreads_book is None:
                continue
            goodreads_id = goodreads_book['goodreads_id']
            calibre_book['goodreads_id'] = goodreads_id
            missing_isbn = not calibre_book['calibre_isbn'] and self.update_isbn == 'MISSING'
            if self.update_isbn == 'ALWAYS' or missing_isbn:
                # We will do an additional API call to get the ISBN value for this book
                # Necessary because ISBN is not returned by the Goodreads search API
                goodreads_book = self.grhttp.get_goodreads_book_for_id(goodreads_id)
                if goodreads_book:
                    update_calibre_isbn_if_required(calibre_book, goodreads_book['goodreads_isbn'],
                                                    self.update_isbn)
            # Update the status to reflect whether it is on the shelf or valid to be tried
            self.update_book_status(calibre_book)
            self.summary_table.populate_table_row(row, calibre_book)
            self.update_error_counts()

    def handle_book_selection_changed(self, selection_is_not_valid):
        self.search_button.setEnabled(selection_is_not_valid)

    def view_book_on_goodreads(self):
        url = '%s/book/show/%s' % (cfg.URL, self.selected_goodreads_book()['goodreads_id'])
        open_url(QUrl(url))


class SortableReadOnlyTableWidgetItem(ReadOnlyTableWidgetItem):
    def __init__(self, text, sort_key=None):
        super(SortableReadOnlyTableWidgetItem, self).__init__(text)
        self.sort_key = text if not sort_key or sort_key == '' else sort_key

    #Qt uses a simple < check for sorting items, override this to use the sortKey
    def __lt__(self, other):
        return self.sort_key < other.sort_key


class CalibreTitleWidgetItem(SortableReadOnlyTableWidgetItem):

    def __init__(self, title, existing_goodreads_id, match_goodreads_id, sort_key=None):
        super(CalibreTitleWidgetItem, self).__init__(title, sort_key)
        if existing_goodreads_id:
            if match_goodreads_id == existing_goodreads_id:
                self.setIcon(get_icon('metadata.png'))
                self.setToolTip(_('You are already linked to this calibre book'))
            else:
                self.setIcon(get_icon('dialog_warning.png'))
                self.setToolTip(_('This calibre book is linked to a different Goodreads book.'))


class GoodreadsTitleWidgetItem(ReadOnlyTableWidgetItem):

    def __init__(self, title, existing_calibre_ids, match_calibre_id):
        ReadOnlyTableWidgetItem.__init__(self, title)
        if existing_calibre_ids and len(existing_calibre_ids) > 0:
            if match_calibre_id in (existing_calibre_ids):
                self.setIcon(get_icon('metadata.png'))
                self.setToolTip(_('You have already linked to this Goodreads book'))
            else:
                self.setIcon(get_icon('dialog_warning.png'))
                self.setToolTip(_('This Goodreads book is linked to a different calibre book.'))


class StatusDataWidgetItem(ReadOnlyTableWidgetItem):
    ICON_MAP = { ActionStatus.NO_LINK: 'images/link_add.png',
                 ActionStatus.WARNING: 'dialog_warning.png',
                 ActionStatus.VALID: 'ok.png' }

    TOOLTIP_MAP = { ActionStatus.NO_LINK: _('You must link this calibre book to a matching book in Goodreads'),
                    ActionStatus.WARNING: _('No changes will be made to your shelf in Goodreads for this book'),
                    ActionStatus.VALID: '' }

    def __init__(self, status_msg, status):
        ReadOnlyTableWidgetItem.__init__(self, status_msg)
        self.setIcon(get_icon(self.ICON_MAP[status]))
        self.setToolTip(self.TOOLTIP_MAP[status])
        self.setData(20, status)

    def get_status(self):
        return self.data(20)


class SyncStatusDataWidgetItem(StatusDataWidgetItem):
    ICON_MAP = { ActionStatus.NO_LINK: 'images/link_add.png',
                 ActionStatus.WARNING: 'dialog_warning.png',
                 ActionStatus.VALID: 'ok.png',
                 ActionStatus.ADD_EMPTY: 'add_book.png' }

    TOOLTIP_MAP = { ActionStatus.NO_LINK: _("You must link this Goodreads book to a matching book in calibre \n"
                                        "in order for any sync actions to be applied"),
                    ActionStatus.WARNING: _("No actions have been set for this shelf.\n"
                                          "Use 'Customize plugin' to specify the actions"),
                    ActionStatus.VALID: _('Actions will be applied when you click Sync Now'),
                    ActionStatus.ADD_EMPTY: _("An empty book will be created in calibre for this book \n"
                                            "using the Goodreads metadata") }


class PickGoodreadsBookTableWidget(QTableWidget):

    book_selection_changed = pyqtSignal(object)

    def __init__(self, parent, id_caches, calibre_id):
        QTableWidget.__init__(self, parent)
        self.id_caches, self.calibre_id = (id_caches, calibre_id)
        self.create_context_menu()
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.itemSelectionChanged.connect(self.item_selection_changed)
        self.setAcceptDrops(True)

    def create_context_menu(self):
        self.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.view_book_action = QAction(_('View &book on Goodreads.com'), self)
        self.view_book_action.setIcon(get_icon('images/view_book.png'))
        self.view_book_action.triggered.connect(self.view_book_on_goodreads)
        self.addAction(self.view_book_action)
        sep1 = QAction(self)
        sep1.setSeparator(True)
        self.addAction(sep1)
        self.paste_url_action = QAction(_('Paste Goodreads.com url'), self)
        self.paste_url_action.setShortcut(_('Ctrl+V'))
        self.paste_url_action.triggered.connect(self.paste_url)
        self.addAction(self.paste_url_action)

    def populate_table(self, goodreads_search_books):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(goodreads_search_books))
        header_labels = [_('Title'), _('Author'), _('Series')]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(24)
        self.horizontalHeader().setStretchLastSection(True)

        self.goodreads_search_books = goodreads_search_books
        for row, book in enumerate(goodreads_search_books):
            self.populate_table_row(row, book)

        self.resizeColumnsToContents()
        self.setMinimumColumnWidth(0, 150)
        self.setMinimumColumnWidth(1, 150)
        self.setMinimumColumnWidth(2, 70)
        self.setRangeColumnWidth(0, 150, 300) # Title
        self.setRangeColumnWidth(1, 150, 300) # Author
        self.setSortingEnabled(True)
        self.setMinimumSize(500, 0)
        if len(goodreads_search_books) > 0:
            self.selectRow(0)

    def setMinimumColumnWidth(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def setRangeColumnWidth(self, col, minimum, maximum):
        self.setMinimumColumnWidth(col, minimum)
        if self.columnWidth(col) > maximum:
            self.setColumnWidth(col, maximum)

    def populate_table_row(self, row, goodreads_search_book):
        # Check to see whether we have one or more calibre_ids matching this
        # goodreads id in our cache
        existing_calibre_ids = self.id_caches.get_calibre_ids_linked(
                                        goodreads_search_book['goodreads_id'])
        title_item = GoodreadsTitleWidgetItem(goodreads_search_book['goodreads_title'],
                                              existing_calibre_ids, self.calibre_id)
        title_item.setData(Qt.UserRole, row)
        self.setItem(row, 0, title_item)
        self.setItem(row, 1, ReadOnlyTableWidgetItem(goodreads_search_book['goodreads_author']))
        self.setItem(row, 2, ReadOnlyTableWidgetItem(goodreads_search_book['goodreads_series']))

    def item_selection_changed(self):
        has_selected_book = self.selectionModel().hasSelection()
        self.view_book_action.setEnabled(has_selected_book)
        self.book_selection_changed.emit(has_selected_book)

    def paste_url(self):
        cb = QApplication.instance().clipboard()
        txt = unicode(cb.text()).strip()
        if txt:
            self.add_url_to_grid(txt)

    def selected_goodreads_book(self):
        if not self.selectionModel().hasSelection():
            return
        row = self.selectionModel().selectedRows()[0]
        row = self.item(row.row(), 0).data(Qt.UserRole)
        if row >= 0:
            return self.goodreads_search_books[row]

    def view_book_on_goodreads(self):
        url = '%s/book/show/%s' % (cfg.URL, self.selected_goodreads_book()['goodreads_id'])
        open_url(QUrl(url))

    def dragEnterEvent(self, event):
        if not event.possibleActions() & (qtDropActionCopyAction | qtDropActionMoveAction):
            return
        urls = get_urls_from_event(event)
        if urls:
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = get_urls_from_event(event)
        event.setDropAction(qtDropActionCopyAction)
        # User has dropped a valid Goodreads url onto our dialog.
        # Insert it as a fake row at the top
        url = urls[0]
        self.add_url_to_grid(url)

    def add_url_to_grid(self, url):
        match = re.search(r'/show/(\d+)', url)
        if not match:
            return
        goodreads_id = match.group(1)
        goodreads_search_book = {}
        goodreads_search_book['goodreads_id'] = goodreads_id
        goodreads_search_book['goodreads_title'] = url
        goodreads_search_book['goodreads_author'] = ''
        goodreads_search_book['goodreads_series'] = ''
        self.goodreads_search_books.insert(0, goodreads_search_book)
        self.populate_table(self.goodreads_search_books)
        self.selectRow(0)

    def dragMoveEvent(self, event):
        event.acceptProposedAction()


class PickGoodreadsBookDialog(SizePersistedDialog):
    '''
    This dialog allows the user to pick a book from search results from Goodreads
    '''
    def __init__(self, parent, grhttp, id_caches, calibre_book, goodreads_books,
                 next_book, is_isbn_match=False):
        SizePersistedDialog.__init__(self, parent, 'goodreads sync plugin:pick goodreads book dialog')
        self.calibre_book = calibre_book
        self.grhttp, self.id_caches = grhttp, id_caches
        self.skip = False
        self.setWindowTitle(_('Search for Goodreads book'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        window_title = _('Goodreads.com matches for Title/Author')
        if is_isbn_match:
            window_title = _('Goodreads.com matches for ISBN')
        title_layout = ImageTitleLayout(self, 'images/link_add_lg.png', window_title)
        layout.addLayout(title_layout)

        match_groupbox = QGroupBox(_('Calibre book:'))
        layout.addWidget(match_groupbox)
        match_layout = QGridLayout()
        match_groupbox.setLayout(match_layout)
        match_layout.addWidget(QLabel(_('Title:'), self), 0, 0, 1, 1)
        match_layout.addWidget(ReadOnlyLineEdit(calibre_book['calibre_title'], self), 0, 1, 1, 3)
        match_layout.addWidget(QLabel(_('Author:'), self), 1, 0, 1, 1)
        match_layout.addWidget(ReadOnlyLineEdit(calibre_book['calibre_author'], self), 1, 1, 1, 3)
        match_layout.addWidget(QLabel(_('Series:'), self), 2, 0, 1, 1)
        match_layout.addWidget(ReadOnlyLineEdit(calibre_book['calibre_series'], self), 2, 1, 1, 1)
        match_layout.addWidget(QLabel(_('ISBN:'), self), 2, 2, 1, 1)
        match_layout.addWidget(ReadOnlyLineEdit(calibre_book['calibre_isbn'], self), 2, 3, 1, 1)

        layout.addSpacing(5)
        layout.addWidget(QLabel(_('Select the Goodreads book to link to this calibre book:'), self))
        self.pick_book_table = PickGoodreadsBookTableWidget(self, id_caches,
                                                            calibre_book['calibre_id'])
        layout.addWidget(self.pick_book_table)
        self.pick_book_table.doubleClicked.connect(self.accept)
        self.pick_book_table.book_selection_changed.connect(self.handle_book_selection_changed)

        message = _('You can drag/drop a Goodreads website link to add it to the results.')
        layout.addWidget(QLabel(message, self))

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.editions_button = self.button_box.addButton(_('Switch Edition'), QDialogButtonBox.ResetRole)
        self.editions_button.clicked.connect(self.switch_editions)

        search_button = self.button_box.addButton(_('Search Goodreads.com'), QDialogButtonBox.ResetRole)
        search_button.clicked.connect(self.search_on_goodreads)
        if next_book:
            self.skip_button = QPushButton(QIcon(I('forward.png')), _('Skip'), self)
            self.button_box.addButton(self.skip_button, QDialogButtonBox.ActionRole)
            tip = _("Skip this book and move to the next:\n'{0}'").format(next_book)
            self.skip_button.setToolTip(tip)
            self.skip_button.clicked.connect(self.skip_triggered)

        # Populate with data
        self.pick_book_table.populate_table(goodreads_books)
        self.handle_book_selection_changed(len(goodreads_books) > 0)
        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def search_on_goodreads(self):
        # Perform a URL search
        title = self.calibre_book['calibre_title']
        author = self.calibre_book['calibre_author']
        if title == _('Unknown'):
            title = ''
        if author == _('Unknown'):
            author = ''
        query = title
        if author:
            query = query + ' ' + get_searchable_author(author)
        query = quote_plus(query.strip().encode('utf-8')).replace('++', '+')
        url = '%s/search?search_type=books&search[query]=%s' % (cfg.URL, query)
        if not isinstance(url, bytes):
            url = url.encode('utf-8')
        open_url(QUrl.fromEncoded(url))

    def handle_book_selection_changed(self, selection_is_not_valid):
        ok_button = self.button_box.button(QDialogButtonBox.Ok)
        ok_button.setEnabled(selection_is_not_valid)
        self.editions_button.setEnabled(selection_is_not_valid)

    def selected_goodreads_book(self):
        return self.pick_book_table.selected_goodreads_book()

    def skip_triggered(self):
        self.skip = True
        self.accept()

    def switch_editions(self):
        # Display dialog allowing user to switch editions
        goodreads_book = self.pick_book_table.selected_goodreads_book()
        if not goodreads_book:
            error_dialog(self, _('No book selected'), _('You must select a book to switch edition'), show=True)
            return
        work_id = goodreads_book.get('goodreads_work_id', None)
        if not work_id:
            # Determine
            work_goodreads_book = self.grhttp.get_goodreads_book_with_work_id(goodreads_book['goodreads_id'])
            if not work_goodreads_book:
                error_dialog(self, _('Invalid book'), _('No goodreads work id found for this book'), show=True)
                return
            work_id = work_goodreads_book['goodreads_work_id']

        edition_books = self.grhttp.get_edition_books_for_work_id(work_id)
        d = SwitchEditionDialog(self, self.id_caches, self.calibre_book,
                                    edition_books, next_book=None, enable_search=False)
        d.exec_()
        if d.result() != d.Accepted:
            return
        new_goodreads_book = d.selected_goodreads_book()
        # Replace id and title
        goodreads_book['goodreads_id'] = new_goodreads_book['goodreads_id']
        goodreads_book['goodreads_title'] = new_goodreads_book['goodreads_title']
        row = self.pick_book_table.currentRow()
        self.pick_book_table.populate_table_row(row, goodreads_book)


class PickCalibreBookTableWidget(QTableWidget):

    def __init__(self, parent, goodreads_id):
        QTableWidget.__init__(self, parent)
        self.goodreads_id = goodreads_id
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def populate_table(self, calibre_books):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(calibre_books))
        header_labels = [_('Title'), _('Author'), _('Series'), _('ISBN')]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(24)

        # We need to re-sort the supplied data using the status attribute in the dictionary
        self.calibre_books = sorted(calibre_books, key=lambda k: '%s%s%s' % \
                                    (k['calibre_author_sort'], k['calibre_series'], k['calibre_title']))
        for row, book in enumerate(self.calibre_books):
            self.populate_table_row(row, book)

        self.resizeColumnsToContents()
        self.setMinimumColumnWidth(0, 150)
        self.setMinimumColumnWidth(1, 150)
        self.setMinimumColumnWidth(2, 70)
        self.setMinimumColumnWidth(3, 90)
        self.setRangeColumnWidth(0, 150, 300) # Title
        self.setRangeColumnWidth(1, 150, 300) # Author
        self.setSortingEnabled(True)
        self.setMinimumSize(500, 0)
        if len(calibre_books) > 0:
            self.selectRow(0)

    def setMinimumColumnWidth(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def setRangeColumnWidth(self, col, minimum, maximum):
        self.setMinimumColumnWidth(col, minimum)
        if self.columnWidth(col) > maximum:
            self.setColumnWidth(col, maximum)

    def populate_table_row(self, row, calibre_book):
        existing_goodreads_id = calibre_book.get('goodreads_id', None)
        item = CalibreTitleWidgetItem(calibre_book['calibre_title'],
                                            existing_goodreads_id, self.goodreads_id,
                                            calibre_book['calibre_title_sort']
                                            )
        item.setData(Qt.UserRole, row)
        self.setItem(row, 0, item)
        self.setItem(row, 1, SortableReadOnlyTableWidgetItem(calibre_book['calibre_author'], calibre_book['calibre_author_sort']))
        self.setItem(row, 2, ReadOnlyTableWidgetItem(calibre_book['calibre_series']))
        self.setItem(row, 3, ReadOnlyTableWidgetItem(calibre_book['calibre_isbn']))

    def selected_calibre_books(self):
        selected_books = []
        for row in self.selectionModel().selectedRows():
            row = self.selectionModel().selectedRows()[0]
            book_id = self.item(row.row(), 0).data(Qt.UserRole)
            selected_books.append(self.calibre_books[book_id])
        return selected_books


class PickCalibreBookDialog(SizePersistedDialog):
    '''
    This dialog allows the user to pick a book from search results from calibre
    that can then be linked to a particular Goodreads book
    '''
    def __init__(self, parent, id_caches, goodreads_book, calibre_books, search_calibre_fn, next_book):
        SizePersistedDialog.__init__(self, parent, 'goodreads sync plugin:pick calibre book dialog')
        self.id_caches, self.goodreads_book, self.search_calibre_fn = \
            (id_caches, goodreads_book, search_calibre_fn)
        self.skip = False

        self.setWindowTitle(_('Search for calibre Book'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'images/link_add_lg.png', _('calibre Search Results'))
        layout.addLayout(title_layout)

        match_groupbox = QGroupBox(_('Goodreads book:'))
        layout.addWidget(match_groupbox)
        match_layout = QGridLayout()
        match_groupbox.setLayout(match_layout)
        match_layout.addWidget(QLabel(_('Title:'), self), 0, 0, 1, 1)
        match_layout.addWidget(ReadOnlyLineEdit(goodreads_book['goodreads_title'], self), 0, 1, 1, 3)
        match_layout.addWidget(QLabel(_('Author:'), self), 1, 0, 1, 1)
        match_layout.addWidget(ReadOnlyLineEdit(goodreads_book['goodreads_author'], self), 1, 1, 1, 3)
        match_layout.addWidget(QLabel(_('Series:'), self), 2, 0, 1, 1)
        match_layout.addWidget(ReadOnlyLineEdit(goodreads_book['goodreads_series'], self), 2, 1, 1, 1)
        match_layout.addWidget(QLabel(_('ISBN:'), self), 2, 2, 1, 1)
        match_layout.addWidget(ReadOnlyLineEdit(goodreads_book['goodreads_isbn'], self), 2, 3, 1, 1)

        layout.addSpacing(5)
        layout.addWidget(QLabel(_('Select a calibre book to link to this Goodreads book:'), self))
        self.pick_book_table = PickCalibreBookTableWidget(self, goodreads_book['goodreads_id'])
        layout.addWidget(self.pick_book_table)
        self.pick_book_table.doubleClicked.connect(self.accept)

        layout.addSpacing(5)
        search_groupbox = QGroupBox(_('Or, try a different calibre search:'))
        layout.addWidget(search_groupbox)
        search_layout = QGridLayout()
        search_groupbox.setLayout(search_layout)

        title_label = QLabel(_('&Title:'), self)
        words = goodreads_book['goodreads_title'].strip().split()
        for i, word in enumerate(words):
            if word.endswith('.') or word.endswith(','):
                words[i] = word[:-1]
        self.title_ledit = QLineEdit(' '.join(words), self)
        title_label.setBuddy(self.title_ledit)

        author_label = QLabel(_('&Author:'), self)
        author = goodreads_book['goodreads_author'].replace('.', '. ').replace(',', ' ').replace('  ', ' ')
        words = author.strip().split()
        for i, word in enumerate(words):
            if word.endswith('.') or word.endswith(','):
                words[i] = word[:-1]
        self.author_ledit = QLineEdit(' '.join(words), self)
        author_label.setBuddy(self.author_ledit)

        self.search_button = QPushButton(_('&Go!'), self)
        self.search_button.setSizePolicy(qSizePolicy_Minimum, qSizePolicy_Minimum)
        self.search_button.clicked.connect(self.search_click)
        self.search_button.setToolTip(_('Search again using this title/author'))
        self.clear_title_button = QToolButton(self)
        self.clear_title_button.setIcon(QIcon(I('trash.png')))
        self.clear_title_button.setToolTip(_('Clear the title field'))
        self.clear_title_button.clicked.connect(partial(self.reset_textbox, self.title_ledit))
        self.clear_author_button = QToolButton(self)
        self.clear_author_button.setIcon(QIcon(I('trash.png')))
        self.clear_author_button.setToolTip(_('Clear the author field'))
        self.clear_author_button.clicked.connect(partial(self.reset_textbox, self.author_ledit))
        search_layout.addWidget(title_label, 0, 0, 1, 1)
        search_layout.addWidget(self.title_ledit, 0, 1, 1, 1)
        search_layout.addWidget(self.clear_title_button, 0, 2, 1, 1)
        search_layout.addWidget(author_label, 1, 0, 1, 1)
        search_layout.addWidget(self.author_ledit, 1, 1, 1, 1)
        search_layout.addWidget(self.clear_author_button, 1, 2, 1, 1)
        search_layout.addWidget(self.search_button, 1, 3, 1, 1)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.ok_clicked)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        if next_book:
            self.skip_button = QPushButton(QIcon(I('forward.png')), _('Skip'), self)
            button_box.addButton(self.skip_button, QDialogButtonBox.ActionRole)
            tip = _("Skip this book and move to the next:\n'{0}'").format(next_book)
            self.skip_button.setToolTip(tip)
            self.skip_button.clicked.connect(self.skip_triggered)

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()
        # Populate with the initial results
        self.pick_book_table.populate_table(calibre_books)

    def search_click(self):
        self.search_button.setEnabled(False)
        try:
            title = unicode(self.title_ledit.text()).strip()
            author = unicode(self.author_ledit.text()).strip()
            calibre_books = self.search_calibre_fn(title, author)
            self.pick_book_table.populate_table(calibre_books)
        finally:
            self.search_button.setEnabled(True)

    def reset_textbox(self, textbox):
        textbox.clear()

    def selected_results(self):
        return self.pick_book_table.selected_calibre_books()

    def ok_clicked(self):
        # We need to validate whether the user has chosen a search result that
        # is already linked to another Goodreads book. We will prompt the user
        # if this is the case giving them the option to overwrite it.
        results = self.selected_results()
        if len(results) == 0:
            self.reject()
            return
        # TODO: Change this when supporting multiple calibre books for a goodreads one
        calibre_id = results[0]['calibre_id']
        goodreads_id = self.id_caches.calibre_to_goodreads_ids().get(calibre_id, '')
        if not goodreads_id or goodreads_id == self.goodreads_book['goodreads_id']:
            self.accept()
            return
        if not question_dialog(self, _('Overwrite Goodreads Link'), \
                _('This calibre book is already linked to a different Goodreads book.')+'<p>'+ \
                _('Only one Goodreads book can be linked to a calibre book at a time.')+'<p><p>'+ \
                _('Click Yes to overwrite the link to this book, No to Cancel'), show_copy_button=False):
            return
        self.accept()

    def skip_triggered(self):
        self.skip = True
        self.accept()


class DoAddRemoveTableWidget(QTableWidget):

    search_for_goodreads_books = pyqtSignal(object, object)
    view_book = pyqtSignal(object)
    book_selection_changed = pyqtSignal(object)

    def __init__(self, parent, rating_column, date_read_column, review_text_column):
        QTableWidget.__init__(self, parent)
        self.rating_column, self.date_read_column, self.review_text_column = (rating_column, date_read_column, review_text_column)
        self.create_context_menu()
        self.itemSelectionChanged.connect(self.item_selection_changed)
        self.doubleClicked.connect(self.search_for_goodreads_books_click)
        self.header_labels = [_('Status'), _('Title'), _('Author'), _('Series'), _('Rating'), _('Date Read'), _('Review')]
        self.pin_view = None

    def setMinimumColumnWidth(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def create_context_menu(self):
        self.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.search_action = QAction(get_icon('images/link_add.png'), _('Search for book in Goodreads')+'...', self)
        self.search_action.triggered.connect(self.search_for_goodreads_books_click)
        self.addAction(self.search_action)
        sep1 = QAction(self)
        sep1.setSeparator(True)
        self.addAction(sep1)
        self.view_book_action = QAction(get_icon('images/view_book.png'), _('&View book on Goodreads.com'), self)
        self.view_book_action.triggered.connect(self.view_book_on_goodreads_click)
        self.addAction(self.view_book_action)

    def populate_table(self, calibre_books):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(calibre_books))

        self.setColumnCount(len(self.header_labels))
        self.setHorizontalHeaderLabels(self.header_labels)
        self.verticalHeader().setDefaultSectionSize(24)

        # We need to re-sort the supplied data using the status attribute in the dictionary
        self.calibre_books = sorted(calibre_books, key=lambda k: k['status'])
        for row, book in enumerate(self.calibre_books):
            self.populate_table_row(row, book)

        self.resizeColumnsToContents()
        self.setMinimumColumnWidth(1, 120)
        self.setMinimumColumnWidth(2, 120)

        delegate = RatingDelegate(self)
        self.setItemDelegateForColumn(4, delegate)
        self.setMinimumColumnWidth(4, 90)
        delegate = DateDelegate(self)
        self.setItemDelegateForColumn(5, delegate)
        self.setColumnHidden(4, True)
        self.setColumnHidden(5, True)
        self.setColumnHidden(6, True)

        self.setSortingEnabled(True)
        self.setMinimumSize(500, 0)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def populate_table_row(self, row, calibre_book):
        self.blockSignals(True)
        self.setSortingEnabled(False)

        self.setItem(row, 0, StatusDataWidgetItem(calibre_book['status_msg'], calibre_book['status']))
        item = SortableReadOnlyTableWidgetItem(calibre_book['calibre_title'],calibre_book['calibre_title_sort'])
        item.setData(Qt.UserRole, calibre_book['calibre_id'])
        self.setItem(row, 1, item)
        item = SortableReadOnlyTableWidgetItem(calibre_book['calibre_author'], calibre_book['calibre_author_sort'])
        item.setData(Qt.UserRole, row)
        self.setItem(row, 2, item)
        self.setItem(row, 3, ReadOnlyTableWidgetItem(calibre_book['calibre_series']))
        self.setItem(row, 4, RatingTableWidgetItem(calibre_book['calibre_rating'], is_read_only=False))
        self.setItem(row, 5, DateTableWidgetItem(calibre_book['calibre_date_read'],
                                                 is_read_only=False, default_to_today=True))
        self.setItem(row, 6, QTableWidgetItem(calibre_book['calibre_review_text']))

        self.setSortingEnabled(True)
        self.blockSignals(False)

    def update_books(self, calibre_books):
        if self.isColumnHidden(4) and self.isColumnHidden(5):
            return
        for row in range(self.rowCount()):
            calibre_id = self.item(row, 1).data(Qt.UserRole)
            for calibre_book in calibre_books:
                if calibre_book['calibre_id'] == calibre_id:
                    if not self.isColumnHidden(4):
                        calibre_book['calibre_rating'] = self.item(row, 4).data(Qt.DisplayRole)
                    if not self.isColumnHidden(5):
                        qtdate = self.item(row, 5).data(Qt.DisplayRole)
                        debug_print("update_books - qtdate='%s'" % qtdate)
                        calibre_book['calibre_date_read'] = qt_to_dt(qtdate, as_utc=False)
                    if not self.isColumnHidden(6):
                        calibre_book['calibre_review_text'] = unicode(self.item(row, 6).data(Qt.DisplayRole))
                    break

    def show_columns(self, is_rating_visible, is_dateread_visible, is_reviewtext_visible):
        if self.rating_column:
            self.setColumnHidden(4, not is_rating_visible)
        if self.date_read_column:
            self.setColumnHidden(5, not is_dateread_visible)
        if self.review_text_column:
            self.setColumnHidden(6, not is_reviewtext_visible)

    def item_selection_changed(self):
        selection_has_no_goodreads_id = True
        selection_is_not_valid = True
        if not self.selectionModel().hasSelection():
            selection_has_no_goodreads_id = False
            selection_is_not_valid = False
        else:
            for row in self.selectionModel().selectedRows():
                calibre_book_id = self.item(row.row(), 2).data(Qt.UserRole)
                calibre_book = self.calibre_books[calibre_book_id]
                if calibre_book['status'] == ActionStatus.VALID:
                    selection_is_not_valid = False
                if calibre_book['goodreads_id']:
                    selection_has_no_goodreads_id = False
        self.book_selection_changed.emit(selection_is_not_valid)
        self.search_action.setEnabled(selection_is_not_valid)
        self.view_book_action.setEnabled(not selection_has_no_goodreads_id)

    def view_book_on_goodreads_click(self):
        for row in self.selectionModel().selectedRows():
            calibre_book = self.calibre_books[row.row()]
            self.view_book.emit(calibre_book['goodreads_id'])

    def search_for_goodreads_books_click(self):
        rows = []
        calibre_books_to_search = []
        for row in self.selectionModel().selectedRows():
            calibre_book_id = self.item(row.row(), 2).data(Qt.UserRole)
            calibre_book = self.calibre_books[calibre_book_id]
            if calibre_book['status'] != ActionStatus.VALID:
                rows.append(row.row())
                calibre_books_to_search.append(calibre_book)
        if len(calibre_books_to_search) == 0:
            return
        self.search_for_goodreads_books.emit(rows, calibre_books_to_search)


class DoAddRemoveDialog(SizePersistedDialog):
    '''
    This dialog previews and handles activity for an add/remove to shelf action
    '''
    def __init__(self, parent, grhttp, id_caches, user_name, action, calibre_books):
        SizePersistedDialog.__init__(self, parent, 'goodreads sync plugin:add remove dialog')
        self.gui = parent
        self.grhttp, self.id_caches, self.user_name, self.action, self.calibre_books = \
            (grhttp, id_caches, user_name, action, calibre_books)
        self.update_isbn = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_UPDATE_ISBN, 'NEVER')
        self.default_prefs = { KEY_DISPLAY_ACTIVE_SHELVES: True, KEY_LAST_SELECTED_SHELVES:[] }
        self.rating_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_RATING_COLUMN, '')
        self.date_read_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_DATE_READ_COLUMN, '')
        self.review_text_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_REVIEW_TEXT_COLUMN, '')
        self.is_rating_visible = False
        self.is_dateread_visible = False
        self.is_review_text_visible = False

        user_info = cfg.plugin_prefs[cfg.STORE_USERS].get(user_name)
        self.shelves = user_info[cfg.KEY_SHELVES]
        self.shelves_map = dict([(shelf['name'], shelf) for shelf in self.shelves])

        # Create all the widgets etc for our controls
        self.init_gui_layout()

        # Now update our books to set the status indicating errors, warnings or valid:
        for calibre_book in calibre_books:
            self.update_book_status(calibre_book)

        self.summary_table.populate_table(calibre_books)
        self.update_error_counts()

        if self.action == 'add':
            # Change visibility of rating/dateread columns based on selection
            # Not relevant for remove from shelve, only add to shelf
            self.values_list.itemSelectionChanged.connect(self.shelf_selection_changed)
            self.shelf_selection_changed() # Fire first-time initialisation

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def init_gui_layout(self):
        self.setWindowTitle('Modify Goodreads Shelf')
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        other_prefs = gprefs.get(self.unique_pref_name+':other_prefs', self.default_prefs)

        title_icon = 'images/add_to_shelf_lg.png' if self.action == 'add' else 'images/remove_from_shelf.png'
        title_text = _('Add to shelf') if self.action == 'add' else _('Remove from shelf')
        title_layout = ImageTitleLayout(self, title_icon, title_text)
        layout.addLayout(title_layout)

        grid_layout = QGridLayout()
        layout.addLayout(grid_layout)

        message = _('To fix missing links, double click to search for a matching book in Goodreads')
        grid_layout.addWidget(QLabel(message, self), 0, 1, 1, 2)
        self.error_label = QLabel('', self)
        grid_layout.addWidget(self.error_label, 0, 2, Qt.AlignRight)

        select_label = QLabel(_('Select shelf:'),self)
        select_label.setToolTip(_('Select one or more shelves to add or remove from'))
        grid_layout.addWidget(select_label, 0, 0)

        self.values_list = QListWidget(self)
        self.values_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        grid_layout.addWidget(self.values_list, 1, 0)
        self.display_active_shelves = QCheckBox(_('Show Active shelves only'))
        grid_layout.addWidget(self.display_active_shelves, 2, 0)
        self.display_active_shelves.setChecked(other_prefs.get(KEY_DISPLAY_ACTIVE_SHELVES,True))
        self.display_active_shelves.stateChanged[int].connect(self.display_active_shelves_changed)

        self.summary_table = DoAddRemoveTableWidget(self, self.rating_column, self.date_read_column, self.review_text_column)
        self.summary_table.view_book.connect(self.grhttp.view_book_on_goodreads)
        self.summary_table.search_for_goodreads_books.connect(self.handle_search_for_goodreads_books)
        self.summary_table.book_selection_changed.connect(self.handle_book_selection_changed)
        grid_layout.addWidget(self.summary_table, 1, 1, 1, 2)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 4)

        upload_layout = QHBoxLayout()
        grid_layout.addLayout(upload_layout, 2, 1, 1, 2)
        upload_layout.addStretch()
        self.rating_image_label = ImageLabel(self, 'images/rating_add.png')
        self.rating_image_label.setVisible(False)
        upload_layout.addWidget(self.rating_image_label)
        self.rating_label = QLabel(_('Add calibre Rating to Goodreads'), self)
        self.rating_label.setVisible(False)
        upload_layout.addWidget(self.rating_label)
        self.date_read_image_label = ImageLabel(self, 'images/dateread_add.png')
        self.date_read_image_label.setVisible(False)
        upload_layout.addWidget(self.date_read_image_label)
        self.date_read_label = QLabel(_('Add calibre Date Read to Goodreads'), self)
        self.date_read_label.setVisible(False)
        upload_layout.addWidget(self.date_read_label)
        self.review_text_image_label = ImageLabel(self, 'images/review_add.png')
        self.review_text_image_label.setVisible(False)
        upload_layout.addWidget(self.review_text_image_label)
        self.review_text_label = QLabel(_('Add calibre Review Text to Goodreads'), self)
        self.review_text_label.setVisible(False)
        upload_layout.addWidget(self.review_text_label)

        button_box = QDialogButtonBox()
        self.search_button = button_box.addButton( _('Search Goodreads')+'...', QDialogButtonBox.ResetRole)
        self.search_button.clicked.connect(self.summary_table.search_for_goodreads_books_click)
        self.search_button.setEnabled(False)
        action_button_name = _('Add to Shelf') if self.action == 'add' else _('Remove from Shelf')
        self.action_button = button_box.addButton(action_button_name, QDialogButtonBox.AcceptRole)
        self.action_button.setAutoDefault(True)
        self.action_button.clicked.connect(self.action_button_clicked)
        self.cancel_button = button_box.addButton(_('Cancel'), QDialogButtonBox.RejectRole)
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(button_box)

        self.display_shelves(other_prefs[KEY_LAST_SELECTED_SHELVES])

        self.resize(self.sizeHint())

    def shelf_selection_changed(self):
        selected_shelves = self._get_selected_shelf_names()
        self.is_rating_visible = False
        self.is_dateread_visible = False
        self.is_review_text_visible = False
        for shelf_name in selected_shelves:
            if self.shelves_map[shelf_name].get(cfg.KEY_ADD_RATING, False):
                self.is_rating_visible = True
            if self.shelves_map[shelf_name].get(cfg.KEY_ADD_DATE_READ, False):
                self.is_dateread_visible = True
            if self.shelves_map[shelf_name].get(cfg.KEY_ADD_REVIEW_TEXT, False):
                self.is_review_text_visible = True
        self.summary_table.show_columns(self.is_rating_visible, self.is_dateread_visible, self.is_review_text_visible)
        self.rating_image_label.setVisible(self.is_rating_visible)
        self.rating_label.setVisible(self.is_rating_visible)
        self.date_read_image_label.setVisible(self.is_dateread_visible)
        self.date_read_label.setVisible(self.is_dateread_visible)
        self.review_text_image_label.setVisible(self.is_review_text_visible)
        self.review_text_label.setVisible(self.is_review_text_visible)

    def display_active_shelves_changed(self):
        selected_shelves = self._get_selected_shelf_names()
        self.display_shelves(selected_shelves)

    def display_shelves(self, selected_shelves):
        is_active_only = self.display_active_shelves.isChecked()
        self.values_list.clear()
        for shelf in self.shelves:
            shelf_name = shelf['name']
            if is_active_only and not shelf['active']:
                continue
            icon = 'images/shelf.png'
            if shelf['exclusive']:
                icon = 'images/shelf_exclusive.png'
            item = QListWidgetItem(get_icon(icon), shelf_name, self.values_list)
            self.values_list.addItem(item)
            item.setSelected(shelf['name'] in selected_shelves)

    def _get_selected_shelf_names(self):
        values = []
        for item in self.values_list.selectedItems():
            values.append(unicode(item.text()))
        return values

    def update_book_status(self, calibre_book):
        # Based on data in the book and the shelf set a status
        goodreads_id = calibre_book['goodreads_id']
        isbn = calibre_book['calibre_isbn']
        if not goodreads_id and not isbn:
            calibre_book['status_msg'] = _('No Goodreads book linked!')
            calibre_book['status'] = ActionStatus.NO_LINK
            return
        if not goodreads_id and isbn:
            # Now see if we can find it by an API call to Goodreads for this ISBN
            goodreads_id = self.grhttp.get_goodreads_id_for_isbn(isbn)
            if goodreads_id:
                calibre_book['goodreads_id'] = goodreads_id
            else:
                calibre_book['status'] = ActionStatus.NO_LINK
                calibre_book['status_msg'] = _('No Goodreads book linked!')
                return
        calibre_book['status'] = ActionStatus.VALID
        calibre_book['status_msg'] = _('Ready')

    def find_goodreads_id_on_shelf_contents(self, goodreads_shelf_books, isbn):
        # Currently we will only match on ISBN. Maybe in future will do title/author too
        if not isbn:
            return None
        for goodreads_id, goodreads_book in goodreads_shelf_books.items():
            if goodreads_book['goodreads_isbn'] == isbn:
                return goodreads_id

    def update_error_counts(self):
        self.error_count = 0
        self.warning_count = 0
        self.valid_count = 0
        for calibre_book in self.calibre_books:
            status = calibre_book['status']
            if status == ActionStatus.NO_LINK:
                self.error_count = self.error_count + 1
            elif status == ActionStatus.WARNING:
                self.warning_count = self.warning_count + 1
            else:
                self.valid_count = self.valid_count + 1
        text = _('{0} missing links').format(self.error_count)
        if self.warning_count > 0:
            text = _('{0}, {1} warnings').format(text, self.warning_count)
        self.error_label.setText(text)

    def action_button_clicked(self):
        selected_shelves = self._get_selected_shelf_names()
        if not selected_shelves:
            return error_dialog(self, _('No shelves selected'), _('You must select one or more shelves first.'),
                                show=True)
        exclusive_count = 0
        for shelf_name in selected_shelves:
            for shelf in self.shelves:
                if shelf['name'] == shelf_name:
                    if shelf['exclusive']:
                        exclusive_count += 1
                    break
        if exclusive_count > 1:
            return error_dialog(self, _('Too many shelves'), _('You cannot add to more than one exclusive shelf.'),
                                show=True)

        if exclusive_count > 0 and self.action == 'remove':
            if not question_dialog(self.gui, _('Exclusive Shelf Warning'), '<p>' +
                _('You are about to remove from a shelf marked as exclusive.')+'<p>'+
                _("This will result in these books being <b>moved</b> to one of your other "
                "shelves rather than being deleted from all shelves.")+'<p>' +
                _('Do you want to continue?'), show_copy_button=False):
                return False

        if self.error_count > 0:
            if not question_dialog(self, _('Are you sure?'), '<p>'+
                    _('There are books in this list not yet linked to calibre which will be ignored.')+'<p><p>'+
                    _('Do you want to continue?'),
                    show_copy_button=False):
                return

        self.save_preferences()
        self.action_button.setEnabled(False)

        # Grab latest values for rating and date read columns
        self.summary_table.update_books(self.calibre_books)

        client = self.grhttp.create_oauth_client(self.user_name)
        upload_rating = self.action == 'add' and self.is_rating_visible and len(self.rating_column) > 0
        upload_date_read = self.action == 'add' and self.is_dateread_visible and len(self.date_read_column) > 0
        upload_review_text = self.action == 'add' and self.is_review_text_visible and len(self.review_text_column) > 0
        added_books = []
        # Add/remove each linked book to the selected shelf
        for calibre_book in self.calibre_books:
            if calibre_book['status'] == ActionStatus.VALID:
                goodreads_id = calibre_book['goodreads_id']
                for shelf_name in selected_shelves:
                    review_id = self.grhttp.add_remove_book_to_shelf(client, shelf_name, goodreads_id, self.action)
                    if not review_id:
                        # Could have had a Goodreads failure, stop immediately.
                        break
                # If adding books and rating/date read columns update the Goodreads review
                if review_id and self.action == 'add':
                    added_books.append(calibre_book)
                    if review_id and (upload_rating or upload_date_read or upload_review_text):
                        rating = None
                        date_read = None
                        review_text = None
                        if upload_rating:
                            rating = int(calibre_book['calibre_rating'] / 2)
                            calibre_book['goodreads_rating'] = rating
                        if upload_date_read:
                            date_read = calibre_book['calibre_date_read']
                            calibre_book['goodreads_read_at'] = date_read
                        if upload_review_text:
                            review_text = calibre_book['calibre_review_text']
                            calibre_book['goodreads_review_text'] = review_text
                        self.grhttp.update_review(client, shelf_name, review_id, goodreads_id, rating, date_read, review_text)
                if not review_id:
                    # Don't keep trying to add books
                    break

        # Finally, apply any "add" actions to books that were added to shelf
        if len(added_books) > 0:
            add_actions = []
            # Include some actions for setting our rating/date read/review text if appropriate
            if upload_rating:
                update_rating_action = {'action':'ADD', 'column':self.rating_column, 'value':'goodreads_rating'}
                add_actions.append(update_rating_action)
            if upload_date_read:
                upload_date_read_action = {'action':'ADD', 'column':self.date_read_column, 'value':'read_at'}
                add_actions.append(upload_date_read_action)
            if upload_review_text:
                upload_review_text_action = {'special':'review_text', 'action':'ADD', 'column':self.review_text_column, 'value':''}
                add_actions.append(upload_review_text_action)
            for shelf_name in selected_shelves:
                add_actions.extend(self.shelves_map[shelf_name].get(cfg.KEY_ADD_ACTIONS,[]))
            if len(add_actions) > 0:
                CalibreDbHelper().apply_actions_to_calibre(self.gui, added_books, add_actions)

        self.accept()

    def save_preferences(self):
        other_prefs = copy.deepcopy(self.default_prefs)
        other_prefs[KEY_DISPLAY_ACTIVE_SHELVES] = self.display_active_shelves.isChecked()
        other_prefs[KEY_LAST_SELECTED_SHELVES] = self._get_selected_shelf_names()
        gprefs[self.unique_pref_name+':other_prefs'] = other_prefs

    def handle_search_for_goodreads_books(self, rows, calibre_books):
        for index, row in enumerate(rows):
            calibre_book = calibre_books[index]
            title = calibre_book['calibre_title']
            author = calibre_book['calibre_author']
            next_book = None
            if index < len(calibre_books) - 1:
                next_book = calibre_books[index + 1]['calibre_title']
            goodreads_books = self.grhttp.search_for_goodreads_books(title, author)
            d = PickGoodreadsBookDialog(self, self.grhttp, self.id_caches, calibre_book,
                                        goodreads_books, next_book)
            d.exec_()
            if d.skip:
                continue
            if d.result() != d.Accepted:
                return
            goodreads_book = d.selected_goodreads_book()
            if goodreads_book is None:
                continue
            goodreads_id = goodreads_book['goodreads_id']
            calibre_book['goodreads_id'] = goodreads_id
            missing_isbn = not calibre_book['calibre_isbn'] and self.update_isbn == 'MISSING'
            if self.update_isbn == 'ALWAYS' or missing_isbn:
                # We will do an additional API call to get the ISBN value for this book
                # Necessary because ISBN is not returned by the Goodreads search API
                goodreads_book = self.grhttp.get_goodreads_book_for_id(goodreads_id)
                if goodreads_book:
                    update_calibre_isbn_if_required(calibre_book, goodreads_book['goodreads_isbn'],
                                                    self.update_isbn)
            # Update the status to reflect whether it is on the shelf or valid to be tried
            self.update_book_status(calibre_book)
            self.summary_table.populate_table_row(row, calibre_book)
            self.update_error_counts()

    def handle_book_selection_changed(self, selection_is_not_valid):
        self.search_button.setEnabled(selection_is_not_valid)

    def view_book_on_goodreads(self):
        url = '%s/book/show/%s' % (cfg.URL, self.selected_goodreads_book()['goodreads_id'])
        open_url(QUrl(url))


class DoShelfSyncTableWidget(QTableWidget):

    search_for_goodreads_books = pyqtSignal(object, object)
    add_empty_books = pyqtSignal(object, object)
    view_book = pyqtSignal(object)
    book_selection_changed = pyqtSignal(object)

    def __init__(self, parent):
        QTableWidget.__init__(self, parent)
        self.create_context_menu()
        self.itemSelectionChanged.connect(self.item_selection_changed)
        self.doubleClicked.connect(self.search_for_calibre_books_click)
        self.format = get_date_format()

    def create_context_menu(self):
        self.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.search_action = QAction(get_icon('images/link_add.png'), _('Search calibre'), self)
        self.search_action.triggered.connect(self.search_for_calibre_books_click)
        self.addAction(self.search_action)
        sep1 = QAction(self)
        sep1.setSeparator(True)
        self.addAction(sep1)
        self.empty_book_action = QAction(get_icon('add_book.png'), _('Add empty book to calibre'), self)
        self.empty_book_action.triggered.connect(self.add_empty_book_click)
        self.addAction(self.empty_book_action)
        sep2 = QAction(self)
        sep2.setSeparator(True)
        self.addAction(sep2)
        self.view_book_action = QAction(get_icon('images/view_book.png'), _('&View book on Goodreads.com'), self)
        self.view_book_action.triggered.connect(self.view_book_on_goodreads_click)
        self.addAction(self.view_book_action)

    def populate_table(self, goodreads_books):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(goodreads_books))
        header_labels = [_('Status'), _('GR Title'), _('GR Author'),
                         _('GR Series'), _('GR Rating'), _('GR Date Read'), _('GR ISBN'), _('Shelves'), _('Linked to calibre Title'),
                         _('calibre Author'), _('calibre Series'), _('calibre Rating'), _('Date Read'), _('calibre ISBN'), 'book_no']
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(24)

        self.goodreads_books = goodreads_books
        for row, book in enumerate(self.goodreads_books):
            self.populate_table_row(row, book, book_index=row)

        delegate = RatingDelegate(self)
        self.setItemDelegateForColumn(4, delegate)
        self.setItemDelegateForColumn(11, delegate)

        delegate = DateDelegate(self)
        self.setItemDelegateForColumn(5, delegate)
        self.setItemDelegateForColumn(12, delegate)
        
        self.resizeColumnsToContents()
        self.setRangeColumnWidth(1, 120, 200) # GR Title
        self.setRangeColumnWidth(2, 120, 200) # GR Author
        self.setMinimumColumnWidth(3, 90)
        self.setMinimumColumnWidth(5, 90) # Ensure space for date read to be updated
        self.setRangeColumnWidth(8, 120, 200) # calibre Title
        self.setRangeColumnWidth(9, 120, 200) # calibre Author
        self.setSortingEnabled(True)
        self.setMinimumSize(700, 0)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        if len(goodreads_books) > 0:
            self.selectRow(0)
            
        self.setColumnHidden(14, True)

    def setMinimumColumnWidth(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def setRangeColumnWidth(self, col, minimum, maximum):
        self.setMinimumColumnWidth(col, minimum)
        if self.columnWidth(col) > maximum:
            self.setColumnWidth(col, maximum)

    def populate_table_row(self, row, goodreads_book, book_index=-1):
        self.blockSignals(True)
        self.setSortingEnabled(False)
        self.setItem(row,  0, SyncStatusDataWidgetItem(goodreads_book['status_msg'], goodreads_book['status']))
        item = ReadOnlyTableWidgetItem(goodreads_book['goodreads_title'])
        if book_index >= 0:
            item.setData(Qt.UserRole, book_index)
        self.setItem(row,  1, item)
        self.setItem(row,  2, ReadOnlyTableWidgetItem(goodreads_book['goodreads_author']))
        self.setItem(row,  3, ReadOnlyTableWidgetItem(goodreads_book['goodreads_series']))
        self.setItem(row,  4, RatingTableWidgetItem(goodreads_book['goodreads_rating'] *2 , is_read_only=True))
        self.setItem(row,  5, DateTableWidgetItem(goodreads_book['goodreads_read_at'], is_read_only=True, fmt=self.format))
        self.setItem(row,  6, ReadOnlyTableWidgetItem(goodreads_book['goodreads_isbn']))
        self.setItem(row,  7, ReadOnlyTableWidgetItem(goodreads_book['goodreads_shelves']))
        self.setItem(row,  8, SortableReadOnlyTableWidgetItem(goodreads_book['calibre_title'], sort_key=goodreads_book['calibre_title_sort']))
        self.setItem(row,  9, SortableReadOnlyTableWidgetItem(goodreads_book['calibre_author'], sort_key=goodreads_book['calibre_author_sort']))
        self.setItem(row, 10, ReadOnlyTableWidgetItem(goodreads_book['calibre_series']))
        self.setItem(row, 11, RatingTableWidgetItem(goodreads_book['calibre_rating'], is_read_only=True))
        self.setItem(row, 12, DateTableWidgetItem(goodreads_book['calibre_date_read'], is_read_only=True, fmt=self.format))
        self.setItem(row, 13, ReadOnlyTableWidgetItem(goodreads_book['calibre_isbn']))
        if book_index >= 0:
            self.setItem(row, 14, NumericTableWidgetItem(book_index, is_read_only=True))
        self.setSortingEnabled(True)
        self.blockSignals(False)

    def find_and_populate_table_row(self, book_index, book_to_update):
        for row in range(self.rowCount()):
            if book_index == self.item(row, 1).data(Qt.UserRole):
                self.populate_table_row(row, book_to_update, book_index=self.item(row, 1).data(Qt.UserRole))
                break

    def item_selection_changed(self):
        selection_has_no_goodreads_id = True
        selection_is_not_valid = True
        add_empty_is_valid = True

        if not self.selectionModel().hasSelection():
            selection_has_no_goodreads_id = False
            selection_is_not_valid = False
            add_empty_is_valid = False
        else:
            for row in self.selectionModel().selectedRows():
                book = self.goodreads_books[self.item(row.row(), 1).data(Qt.UserRole)]
                if book['status'] == ActionStatus.WARNING:
                    add_empty_is_valid = False
                if book['status'] == ActionStatus.VALID:
                    add_empty_is_valid = False
                    selection_is_not_valid = False
                if len(book['goodreads_id']) > 0:
                    selection_has_no_goodreads_id = False
        self.search_action.setEnabled(selection_is_not_valid)
        self.book_selection_changed.emit(selection_is_not_valid)
        self.empty_book_action.setEnabled(add_empty_is_valid)
        self.view_book_action.setEnabled(not selection_has_no_goodreads_id)

    def view_book_on_goodreads_click(self):
        for row in self.selectionModel().selectedRows():
            book = self.goodreads_books[self.item(row.row(), 1).data(Qt.UserRole)]
            self.view_book.emit(book['goodreads_id'])

    def get_selected_books(self, status=[]):
        rows = []
        books = []
        for row in self.selectionModel().selectedRows():
            book = self.goodreads_books[self.item(row.row(), 1).data(Qt.UserRole)]
            if book['status'] in status:
                rows.append(self.item(row.row(), 1).data(Qt.UserRole))
                books.append(book)
        return (rows, books)

    def search_for_calibre_books_click(self):
        (rows, books) = self.get_selected_books(status=[ActionStatus.NO_LINK])
        if len(rows) == 0:
            return
        self.search_for_goodreads_books.emit(rows, books)

    def add_empty_book_click(self):
        (rows, books) = self.get_selected_books(status=[ActionStatus.NO_LINK, ActionStatus.ADD_EMPTY])
        if len(rows) == 0:
            return
        self.add_empty_books.emit(rows, books)


class DoShelfSyncDialog(SizePersistedDialog):
    '''
    This dialog summarises the activity from a sync from shelf action
    '''
    def __init__(self, parent, plugin_action, grhttp, user_name, selected_shelves, goodreads_books, calibre_searcher):
        SizePersistedDialog.__init__(self, parent, 'goodreads sync plugin:do shelf sync dialog')
        self.grhttp, self.user_name, self.shelves = (grhttp, user_name, selected_shelves)
        self.shelf_names = [shelf['name'] for shelf in selected_shelves]
        self.gui = parent
        self.db = parent.library_view.model().db
        self.plugin_action = plugin_action

        self.user_info = cfg.plugin_prefs[cfg.STORE_USERS][user_name]

        # Create all the controls etc on this dialog
        self.init_gui_layout()

        # Display the shelves on the dialog
        self.calibre_searcher = calibre_searcher
        self.goodreads_books = self.flatten_book_shelf(goodreads_books)
        for book in self.goodreads_books:
            self.update_book_status(book)
        self.summary_table.populate_table(self.goodreads_books)
        self.update_error_counts()

    def init_gui_layout(self):
        window_text = _('Sync from Goodreads Shelf')
        self.setWindowTitle(window_text)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.splitter = QSplitter(self)
        self.splitter.setOrientation(Qt.Vertical)
        layout.addWidget(self.splitter)
        splitter_top = QWidget(self)
        self.splitter.addWidget(splitter_top)
        top_layout = QVBoxLayout()
        splitter_top.setLayout(top_layout)

        if len(self.shelf_names) == 1:
            title = _("Sync from '{0}' shelf").format(self.shelf_names[0])
        else:
            title = _("Sync from {0} shelves").format(len(self.shelf_names))
        title_layout = ImageTitleLayout(self, 'images/sync_from_shelf_lg.png', title)
        top_layout.addLayout(title_layout)

        heading_layout = QHBoxLayout()
        top_layout.addLayout(heading_layout)
        message_text = _('To fix missing links, double click to search for a matching book in calibre.')
        heading_layout.addWidget(QLabel(message_text, self))
        self.error_label = QLabel('', self)
        self.error_label.setAlignment(Qt.AlignRight)
        heading_layout.addWidget(self.error_label)

        self.summary_table = DoShelfSyncTableWidget(self)
        self.summary_table.view_book.connect(self.grhttp.view_book_on_goodreads)
        self.summary_table.search_for_goodreads_books.connect(self.handle_search_calibre_for_goodreads_books)
        self.summary_table.add_empty_books.connect(self.handle_add_empty_books)
        self.summary_table.book_selection_changed.connect(self.handle_book_selection_changed)
        top_layout.addWidget(self.summary_table)

        splitter_bottom = QWidget(self)
        self.splitter.addWidget(splitter_bottom)
        actions_layout = QGridLayout()
        splitter_bottom.setLayout(actions_layout)

        self.description = QTextEdit(self)
        self.description.setReadOnly(True)
        actions_layout.addWidget(QLabel(_('The following actions will be performed for books that are synced:'), self), 0, 0)
        actions_layout.addWidget(self.description, 1, 0, 4, 1)
        actions_layout.setRowStretch(4, 2)
        self._display_sync_actions()

        if self.update_rating:
            rating_image_label = ImageLabel(self, 'images/rating_sync.png')
            actions_layout.addWidget(rating_image_label, 1, 1)
            rating_label = QLabel(_('Add Goodreads Rating to calibre'), self)
            actions_layout.addWidget(rating_label, 1, 2)
        if self.update_date_read:
            date_read_image_label = ImageLabel(self, 'images/dateread_sync.png')
            actions_layout.addWidget(date_read_image_label, 2, 1)
            date_read_label = QLabel(_('Add Goodreads Date Read to calibre'), self)
            actions_layout.addWidget(date_read_label, 2, 2)
        if self.update_review_text:
            review_text_image_label = ImageLabel(self, 'images/review_sync.png')
            actions_layout.addWidget(review_text_image_label, 3, 1)
            review_text_label = QLabel(_('Add Goodreads Review Text to calibre'), self)
            actions_layout.addWidget(review_text_label, 3, 2)

        self.auto_match_checkbox = QCheckBox(_('When searching calibre, if only one result is found then automatically link to it without prompting'))
        layout.addWidget(self.auto_match_checkbox)
        auto_match_result = gprefs.get(self.unique_pref_name+':auto match', False)
        self.auto_match_checkbox.setChecked(auto_match_result)
        self.auto_match_checkbox.stateChanged.connect(self.auto_match_state_changed)
        
        button_box = QDialogButtonBox()
        self.sync_button = button_box.addButton(_('Sync Now'), QDialogButtonBox.AcceptRole)
        self.sync_button.setDefault(True)
        self.sync_button.clicked.connect(self.sync_button_clicked)
        self.cancel_button = button_box.addButton(_('Cancel'), QDialogButtonBox.RejectRole)
        self.cancel_button.clicked.connect(self.reject)
        self.search_button = button_box.addButton(_('Search calibre'), QDialogButtonBox.ResetRole)
        self.search_button.clicked.connect(self.summary_table.search_for_calibre_books_click)
        self.search_button.setEnabled(False)
        layout.addWidget(button_box)
        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def _display_sync_actions(self):
        text = ''
        self.rating_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_RATING_COLUMN, None)
        self.date_read_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_DATE_READ_COLUMN, None)
        self.review_text_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_REVIEW_TEXT_COLUMN, None)
        self.update_rating = False
        self.update_date_read = False
        self.update_review_text = False
        for shelf in self.shelves:
            sync_actions = shelf[cfg.KEY_SYNC_ACTIONS]
            if len(sync_actions) > 0:
                text += _('For books on the <b>{0}</b> shelf:<br>').format(shelf['name'])
                for sync_action in sync_actions:
                    sync_action_type = sync_action['action']
                    if sync_action_type == 'ADD':
                        text += _("+ Add '{0}' to column '{1}'<br>").format(sync_action['value'], sync_action['column'])
                    elif sync_action_type == 'REMOVE':
                        text += _("- Remove '{0}' from column '{1}'<br>").format(sync_action['value'], sync_action['column'])
                text += '<br>'
            if shelf.get(cfg.KEY_SYNC_RATING, False):
                self.update_rating = True
            if shelf.get(cfg.KEY_SYNC_DATE_READ, False):
                self.update_date_read = True
            if shelf.get(cfg.KEY_SYNC_REVIEW_TEXT, False):
                self.update_review_text = True
        while text.endswith('<br>'):
            text = text[:-4]
        self.description.setText(text)
        # Can only update rating/date read if columns are configured
        if self.update_rating and not self.rating_column:
            self.update_rating = False
        if self.update_date_read and not self.date_read_column:
            self.update_date_read = False
        if self.update_review_text and not self.review_text_column:
            self.update_review_text = False

    def auto_match_state_changed(self):
        auto_match_result = self.auto_match_checkbox.isChecked()
        gprefs[self.unique_pref_name+':auto match'] = auto_match_result

    def update_error_counts(self):
        self.error_count = 0
        self.warning_count = 0
        self.valid_count = 0
        self.add_count = 0
        for book in self.goodreads_books:
            status = book['status']
            if status == ActionStatus.NO_LINK:
                self.error_count = self.error_count + 1
            elif status == ActionStatus.WARNING:
                self.warning_count = self.warning_count + 1
            elif status == ActionStatus.ADD_EMPTY:
                self.add_count = self.add_count + 1
            else:
                self.valid_count = self.valid_count + 1
        text = _('{0} missing links').format(self.error_count)
        if self.warning_count > 0:
            text = _("{0}, {1} warnings").format(text, self.warning_count)
        if self.add_count > 0:
            text = _("{0}, {1} books to add").format(text, self.add_count)
        self.error_label.setText(text)

    def flatten_book_shelf(self, goodreads_books):
        # Build a mapping of calibre ISBNs to calibre IDs
        isbn_map = collections.defaultdict(list)
        for id_ in self.db.all_ids():
            isbn = self.db.isbn(id_, index_is_id=True)
            if isbn:
                sub_map = isbn_map.get(isbn, [])
                sub_map.append(id_)
                isbn_map[isbn] = sub_map
        gr_cache = self.calibre_searcher.id_caches.goodreads_to_calibre_ids()
        cb_cache = self.calibre_searcher.id_caches.calibre_to_goodreads_ids()
        # Flatten out the structure, from its 1:M to a 1:1
        flattened_books = []
        autolinked_calibre_ids = []
        for goodreads_id, goodreads_book in goodreads_books.items():
            calibre_ids = gr_cache.get(goodreads_id, [])
            is_auto_link_by_isbn = False
            if len(calibre_ids) == 0 and goodreads_book['goodreads_isbn']:
                # We have not yet mapped this Goodreads id to a calibre book
                # Attempt a mapping ourselves by doing a calibre isbn map lookup
                calibre_ids = isbn_map.get(goodreads_book['goodreads_isbn'], [])
                if len(calibre_ids) > 0:
                    # We found at least one calibre book matching the Goodreads ISBN
                    # However we can only automap where the calibre book is not mapped
                    # to a different goodreads book already, so filter this list
                    calibre_ids = [i for i in calibre_ids if i not in cb_cache]
                    # Also filter out any that we may have autolinked so far in memory
                    calibre_ids = [i for i in calibre_ids if i not in autolinked_calibre_ids]
                if len(calibre_ids) > 0:
                    is_auto_link_by_isbn = True
                    autolinked_calibre_ids.extend(calibre_ids)
            if len(calibre_ids) > 0:
                # We have at least one calibre match - flatten into a book for each match
                for calibre_id in calibre_ids:
                    book = goodreads_book.copy()
                    self.calibre_searcher.get_calibre_data_for_book(book, calibre_id)
                    book['orig_calibre_id'] = book['calibre_id']
                    book['orig_calibre_isbn'] = book['calibre_isbn']
                    if is_auto_link_by_isbn:
                        # As we autolinked we need to record this as changed so that
                        # after the sync takes place we can update the calibre database
                        book['orig_calibre_id'] = ''
                        update_calibre_isbn_if_required(book, book['goodreads_isbn'])
                    flattened_books.append(book)
            else:
                book = goodreads_book.copy()
                book['calibre_id'] = ''
                book['orig_calibre_id'] = ''
                book['calibre_isbn'] = ''
                book['orig_calibre_isbn'] = ''
                book['calibre_title'] = ''
                book['calibre_title_sort'] = ''
                book['calibre_author'] = ''
                book['calibre_author_sort'] = ''
                book['calibre_series'] = ''
                book['calibre_rating'] = 0
                book['calibre_date_read'] = UNDEFINED_DATE
                book['calibre_review_text'] = ''
                flattened_books.append(book)
        return flattened_books

    def update_book_status(self, book):
        # Based on data in the book and the shelf set a status
        if book['calibre_id']:
            book['status'] = ActionStatus.VALID
            book['status_msg'] = _('Ready')
        else:
            book['status'] = ActionStatus.NO_LINK
            book['status_msg'] = _('No calibre book linked!')

    def handle_add_empty_books(self, rows, goodreads_books):
        # Treat it as a toggle - if the book has been added already clear the calibre entries
        toggled_ids = []
        for index, row in enumerate(rows):
            goodreads_book = goodreads_books[index]
            if goodreads_book['status'] == ActionStatus.ADD_EMPTY:
                goodreads_book['calibre_id'] = ''
                goodreads_book['calibre_isbn'] = ''
                goodreads_book['calibre_title'] = ''
                goodreads_book['calibre_title_sort'] = ''
                goodreads_book['calibre_author'] = ''
                goodreads_book['calibre_author_sort'] = ''
                goodreads_book['calibre_series'] = ''
                goodreads_book['calibre_rating'] = 0
                goodreads_book['calibre_date_read'] = UNDEFINED_DATE
                goodreads_book['calibre_review_text'] = ''
                self.update_book_status(goodreads_book)
                self.summary_table.populate_table_row(row, goodreads_book, book_index=index)
                toggled_ids.append(goodreads_book['goodreads_id'])

        # Get our setting to know whether to convert Goodreads author FN LN to LN, FN
        c = cfg.plugin_prefs[cfg.STORE_PLUGIN]
        swap_author_names = c.get(cfg.KEY_AUTHOR_SWAP, False)
        # Copy the Goodreads info into the calibre columns for later usage when we create
        # the actual rows in database
        for index, row in enumerate(rows):
            goodreads_book = goodreads_books[index]
            if goodreads_book['goodreads_id'] in toggled_ids:
                continue
            if goodreads_book['status'] != ActionStatus.NO_LINK:
                continue
            goodreads_book['calibre_isbn'] = goodreads_book['goodreads_isbn']
            goodreads_book['calibre_title'] = goodreads_book['goodreads_title']
            goodreads_book['calibre_author'] = goodreads_book['goodreads_author']
            if swap_author_names:
                authors = goodreads_book['goodreads_author'].split('&')
                swapped_authors = []
                for author in authors:
                    name_parts = author.strip().rpartition(' ')
                    if name_parts[2]:
                        swapped_authors.append(name_parts[2] + ', ' + name_parts[0])
                    else:
                        swapped_authors.append(author)
                goodreads_book['calibre_author'] = ' & '.join(swapped_authors)
            goodreads_book['calibre_series'] = goodreads_book['goodreads_series']
            goodreads_book['status'] = ActionStatus.ADD_EMPTY
            goodreads_book['status_msg'] = _('Add to calibre')
            self.summary_table.populate_table_row(row, goodreads_book, book_index=index)
        # Ensure our error counts reflect the latest info
        self.update_error_counts()

    def handle_search_calibre_for_goodreads_books(self, rows, goodreads_books):
        for index, row in enumerate(rows):
            goodreads_book = goodreads_books[index]
            title = goodreads_book['goodreads_title']
            authors = goodreads_book['goodreads_author'].split('&')
            author = authors[0].strip()
            calibre_books = self.calibre_searcher.search_calibre_fuzzy_map(title, author)
            if self.auto_match_checkbox.isChecked() and len(calibre_books) == 1:
                # We are auto-linking, but need to be sure that we don't autolink to a
                # calibre book that is already linked to a different goodreads book
                if not calibre_books[0]['goodreads_id']:
                    self.link_to_calibre_books(row, goodreads_book, calibre_books)
                    continue

            next_book = None
            if index < len(goodreads_books) - 1:
                next_book = goodreads_books[index + 1]['goodreads_title']
            d = PickCalibreBookDialog(self, self.calibre_searcher.id_caches, goodreads_book,
                                      calibre_books, self.search_calibre_using_query, next_book)
            d.exec_()
            if d.skip:
                continue
            if d.result() != d.Accepted:
                break
            selected_books = d.selected_results()
            if len(selected_books) == 0:
                continue
            self.link_to_calibre_books(row, goodreads_book, selected_books)
        self.update_error_counts()

    def search_calibre(self, title, author):
        self.search_button.setEnabled(False)
        try:
            calibre_books = self.calibre_searcher.search_calibre_fuzzy_map(title, author)
            self.update_search_results_with_current_links(calibre_books)
            return calibre_books
        finally:
            self.search_button.setEnabled(True)

    def update_search_results_with_current_links(self, calibre_books):
        # We may need to override the mapped goodreads id on the search results if
        # the user has duplicate goodreads on their shelf and overwrote a link
        # As we have not committed to a database yet the in memory cache is out of date
        for calibre_book in calibre_books:
            calibre_id = calibre_book['calibre_id']
            for goodreads_book in self.goodreads_books:
                is_book_changed = goodreads_book['calibre_id'] != goodreads_book['orig_calibre_id']
                if is_book_changed and calibre_id == goodreads_book['calibre_id']:
                    calibre_book['goodreads_id'] = goodreads_book['calibre_id']
                    break

    def link_to_calibre_books(self, row, goodreads_book, calibre_books):
        # If the user selected more than one book, we need to create
        # additional row(s) in our grid representing those additional books
        # TODO: Support this (for now only have a single result from dialog)
        calibre_id = calibre_books[0]['calibre_id']
        goodreads_book['calibre_id'] = calibre_id
        goodreads_book['calibre_isbn'] = calibre_books[0]['calibre_isbn']
        goodreads_book['calibre_title'] = calibre_books[0]['calibre_title']
        goodreads_book['calibre_author'] = calibre_books[0]['calibre_author']
        goodreads_book['calibre_series'] = calibre_books[0]['calibre_series']
        goodreads_book['calibre_rating'] = calibre_books[0]['calibre_rating']
        goodreads_book['calibre_date_read'] = calibre_books[0]['calibre_date_read']
        goodreads_book['calibre_review_text'] = calibre_books[0]['calibre_review_text']
        update_calibre_isbn_if_required(goodreads_book, goodreads_book['goodreads_isbn'])
        self.update_book_status(goodreads_book)
        self.summary_table.find_and_populate_table_row(row, goodreads_book)
        # We also need to check whether we now have a duplicate link situation
        # where another Goodreads book is also linked to this Goodreads id.
        # for other_book in self.goodreads_books:
        for index, other_book in enumerate(self.goodreads_books):
            if other_book['goodreads_id'] == goodreads_book['goodreads_id']:
                # Don't compare with ourselves
                continue
            if other_book['calibre_id'] == calibre_id:
                # Found a duplicate. We must unlink it!
                other_book['calibre_id'] = ''
                other_book['calibre_isbn'] = ''
                other_book['calibre_title'] = ''
                other_book['calibre_author'] = ''
                other_book['calibre_series'] = ''
                other_book['calibre_rating'] = 0
                other_book['calibre_date_read'] = UNDEFINED_DATE
                other_book['calibre_review_text'] = ''
                self.update_book_status(other_book)
                self.summary_table.find_and_populate_table_row(index, other_book)

    def search_calibre_using_query(self, title, author):
        self.search_button.setEnabled(False)
        try:
            return self.calibre_searcher.search_calibre_using_query(title, author)
        finally:
            self.search_button.setEnabled(True)

    def handle_book_selection_changed(self, selection_is_not_valid):
        self.search_button.setEnabled(selection_is_not_valid)

    def _create_empty_books(self, goodreads_books):
        # Iterate through these Goodreads books creating equivalent books in calibre
        for book in goodreads_books:
            mi = MetaInformation(book['calibre_title'], book['calibre_author'].split('&'))
            # Now set the other metadata values we have available for this book
            # ISBN will automatically be saved by the calling code to this dialog.
            if len(book['calibre_series']) > 0:
                # Series will be in two parts
                series_parts = book['calibre_series'].rpartition('[')
                mi.series = series_parts[0].strip()
                try:
                    mi.series_index = float(series_parts[2].rpartition(']')[0])
                except:
                    pass
            book['calibre_id'] = self.db.import_book(mi, [])

    def _get_sync_actions_for_user_shelf(self, user_name, shelf_name):
        shelves = self.user_info[cfg.KEY_SHELVES]
        for shelf in shelves:
            if shelf['name'] == shelf_name:
                return shelf.get(cfg.KEY_SYNC_ACTIONS, [])

    def sync_button_clicked(self):
        if self.error_count > 0:
            if not question_dialog(self, _('Are you sure?'), '<p>'+
                    _('There are books in this list not yet linked to calibre which will be ignored.<p><p>Are you sure you want to continue?'),
                    show_copy_button=False):
                return
        # Create empty books if any were marked as needed by the user.
        add_empty_books = [b for b in self.goodreads_books if b['status'] == ActionStatus.ADD_EMPTY ]
        self.num_added_books = len(add_empty_books)
        if self.num_added_books > 0:
            self._create_empty_books(add_empty_books)

        # Apply sync actions to our valid books and any empty ones just created
        all_sync_books = [b for b in self.goodreads_books if b['status'] in \
                                [ActionStatus.ADD_EMPTY, ActionStatus.VALID] ]
        for shelf in self.shelves:
            sync_actions = []
            # Find the subset of valid books that are on this shelf
            sync_books = [b for b in all_sync_books if shelf['name'] in b['goodreads_shelves_list']]
            if len(sync_books) > 0:
                # Now apply rating/date read/review text to calibre book entries if relevant
                if self.update_rating and shelf.get(cfg.KEY_SYNC_RATING):
                    added_action = False
                    for book in sync_books:
                        if book['calibre_rating'] != book['goodreads_rating'] * 2:
                            book['calibre_rating'] = book['goodreads_rating'] * 2
                            book['rating_changed'] = True
                            if not added_action:
                                added_action = True
                                sync_rating_action = {'action':'ADD', 'column':self.rating_column, 'value':'goodreads_rating'}
                                sync_actions.append(sync_rating_action)
                if self.update_date_read and shelf.get(cfg.KEY_SYNC_DATE_READ):
                    added_action = False
                    for book in sync_books:
                        if book['calibre_date_read'] != book['goodreads_read_at']:
                            book['calibre_date_read'] = book['goodreads_read_at']
                            book['date_read_changed'] = True
                            if not added_action:
                                added_action = True
                                sync_date_read_action = {'action':'ADD', 'column':self.date_read_column, 'value':'read_at'}
                                sync_actions.append(sync_date_read_action)
                if self.update_review_text and shelf.get(cfg.KEY_SYNC_REVIEW_TEXT):
                    added_action = False
                    for book in sync_books:
                        if book['calibre_review_text'] != book['goodreads_review_text']:
                            book['calibre_review_text'] = book['goodreads_review_text']
                            book['review_text_changed'] = True
                            if not added_action:
                                added_action = True
                                sync_review_text_action = {'special':'review_text', 'action':'ADD', 'column':self.review_text_column, 'value':''}
                                sync_actions.append(sync_review_text_action)
                sync_actions.extend(shelf.get(cfg.KEY_SYNC_ACTIONS, []))
                if len(sync_actions) > 0:
                    CalibreDbHelper().apply_actions_to_calibre(self.gui, sync_books, sync_actions)
        self.accept()

