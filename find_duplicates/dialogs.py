from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import codecs
from collections import OrderedDict
from functools import partial

try:
    from qt.core import (QDialogButtonBox, QVBoxLayout, QHBoxLayout, QTabWidget,
                        QLabel, QTextEdit, Qt, QGroupBox, QWidget, QComboBox,
                        QRadioButton, QTableWidget, QAbstractItemView,
                        QGridLayout, QButtonGroup, QCheckBox, QSpinBox,
                        QListWidget, QListWidgetItem, QSize, QPushButton,
                        QApplication, QIcon, QToolButton, QMenu, QObject)
except ImportError:
    from PyQt5.Qt import (QDialogButtonBox, QVBoxLayout, QHBoxLayout, QTabWidget,
                        QLabel, QTextEdit, Qt, QGroupBox, QWidget, QComboBox,
                        QRadioButton, QTableWidget, QAbstractItemView,
                        QGridLayout, QButtonGroup, QCheckBox, QSpinBox,
                        QListWidget, QListWidgetItem, QSize, QPushButton,
                        QApplication, QIcon, QToolButton, QMenu, QObject)

from calibre import patheq
from calibre.ebooks.metadata import authors_to_string, fmt_sidx
from calibre.gui2 import info_dialog, choose_dir, error_dialog, choose_save_file
from calibre.gui2.complete2 import EditWithComplete
from calibre.gui2.dialogs.confirm_delete import confirm
from calibre.gui2.dialogs.message_box import MessageBox
from calibre.utils.date import format_date
from calibre.utils.titlecase import titlecase
from calibre.gui2.widgets import HistoryLineEdit

import calibre_plugins.find_duplicates.config as cfg
from calibre_plugins.find_duplicates.common_icons import get_icon
from calibre_plugins.find_duplicates.common_dialogs import SizePersistedDialog
from calibre_plugins.find_duplicates.common_widgets import (ImageTitleLayout, ReadOnlyTableWidgetItem, 
                                        CheckableTableWidgetItem)
from calibre_plugins.find_duplicates.matching import (set_author_soundex_length,
                    set_publisher_soundex_length, set_series_soundex_length, set_tags_soundex_length)
from calibre_plugins.find_duplicates.variation_algorithms import VariationAlgorithm

try:
    load_translations()
except NameError:
    pass

SEARCH_TYPES = ['titleauthor', 'binary', 'identifier']

IDENTIFIER_DESC = _('<b>Book duplicate search</b><br/>'
              '- Find groups of books which have an identical identifier '
              'such as an ISBN, amazon id, goodreads, uri etc.<br/>'
              '- Marking a group as exempt will prevent those specific books '
              'from appearing together in future duplicate book searches.')

BINARY_DESC = _('<b>Book duplicate search</b><br/>'
              '- Find groups of books which have a book format that is binary identical.<br/>'
              '- Compares the actual file size of every book format in your library, '
              'computing an SHA hash to compare contents where sizes match.<br/>'
              '- Books found using this search are guaranteed to be duplicates.<br/>'
              '- Marking a group as exempt will prevent those specific books '
              'from appearing together in future duplicate book searches.')

TITLE_DESCS = OrderedDict([
               ('identical',_('<b>Title duplicate search</b><br/>'
                             '- Find groups of books with an <b>identical title</b> and {0}<br/>'
                             '- Titles must match exactly excluding case.<br/>'
                             '- Marking a group as exempt will prevent those specific books '
                             'from appearing together in future duplicate book searches.')),
               ('similar',  _('<b>Title duplicate search</b><br/>'
                             '- Find groups of books with a <b>similar title</b> and {0}<br/>'
                             '- Similar title matches apply removal of common punctuation and '
                             'prefixes and applies the same title matching logic as Automerge.<br/>'
                             '- Marking a group as exempt will prevent those specific books '
                             'from appearing together in future duplicate book searches.')),
               ('soundex',  _('<b>Title duplicate search</b><br/>'
                             '- Find groups of books with a <b>soundex title</b> and {0}<br/>'
                             '- Soundex title matches are based on the same removal of punctuation '
                             'and common prefixes as a similar title search.<br/>'
                             '- Marking a group as exempt will prevent those specific books '
                             'from appearing together in future duplicate book searches.')),
               ('fuzzy',    _('<b>Title duplicate search</b><br/>'
                             '- Find groups of books with a <b>fuzzy title</b> and {0}<br/>'
                             '- Fuzzy title matches remove all punctuation, subtitles '
                             'and any words after \'and\', \'or\' or \'aka\' in the title.<br/>'
                             '- Marking a group as exempt will prevent those specific books '
                             'from appearing together in future duplicate book searches.')),
               ('ignore',   _('<b>Author duplicate search</b><br/>'
                             '- Find groups of books <b>ignoring title</b> with {0}<br/>'
                             '- Ignore title searches are best to find variations of author '
                             'names regardless of the books you have for each.<br/>'
                             '- Marking a group as exempt will prevent any books by those authors '
                             'from appearing together in future duplicate author searches.'))
               ])

AUTHOR_DESCS = OrderedDict([
                ('identical',_('an <b>identical author</b>.<br/>'
                              '- Authors must match exactly excluding case.')),
                ('similar',  _('a <b>similar author</b>.<br/>'
                              '- Similar authors differ only in '
                              'punctuation, initials or order of their names.')),
                ('soundex',  _('a <b>soundex author</b>.<br/>'
                              '- Soundex author matches start with the same removal '
                              'of punctuation and ordering as a similar author search.')),
                ('fuzzy',    _('a <b>fuzzy match author</b>.<br/>'
                              '- Fuzzy author matches compare using their '
                              'surnames and only the first initial.')),
                ('ignore',   _('<b>ignoring the author</b>.'))
               ])


class HistoryLineEditWithDelete(HistoryLineEdit):
    def __init__(self, *args):
        HistoryLineEdit.__init__(self, *args)
        self.view().installEventFilter(HistoryLineEditWithDeleteDropDownEventFilter(self))


class HistoryLineEditWithDeleteDropDownEventFilter(QObject):
    def __init__(self, parent):
        QObject.__init__(self, parent)
        self.parent = parent
        
    def eventFilter(self, obj, event):
        eventType = event.type()
        if eventType == event.KeyPress:
            if event.key() == Qt.Key_Delete:
                self.parent.removeItem(obj.selectedIndexes()[0].row())
                return True
        return False


class ListComboBox(QComboBox):

    def __init__(self, parent, values, selected_value=None):
        QComboBox.__init__(self, parent)
        self.values = values
        if selected_value is not None:
            self.populate_combo(selected_value)

    def populate_combo(self, selected_value):
        self.clear()
        selected_idx = idx = -1
        for value in self.values:
            idx = idx + 1
            self.addItem(value)
            if value == selected_value:
                selected_idx = idx
        self.setCurrentIndex(selected_idx)

    def selected_value(self):
        return str(self.currentText())


class FindBookDuplicatesDialog(SizePersistedDialog):
    '''
    Dialog to configure search options and perform the search
    '''
    def __init__(self, gui):
        SizePersistedDialog.__init__(self, gui, 'duplicate finder plugin:duplicate dialog')

        self.setWindowTitle(_('Find Duplicates'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'images/find_duplicates.png', _('Duplicate Search Options'))
        layout.addLayout(title_layout)
        layout.addSpacing(5)

        search_type_group_box = QGroupBox(_('Duplicate Search Type'), self)
        layout.addWidget(search_type_group_box)
        search_type_group_box_layout = QHBoxLayout()
        search_type_group_box.setLayout(search_type_group_box_layout)
        self.search_type_button_group = QButtonGroup(self)
        self.search_type_button_group.buttonClicked.connect(self._search_type_radio_clicked)
        for row, text in enumerate([_('Title/Author'), _('Binary Compare'), _('Identifier')]):
            rdo = QRadioButton(text, self)
            rdo.row = row
            self.search_type_button_group.addButton(rdo)
            self.search_type_button_group.setId(rdo, row)
            search_type_group_box_layout.addWidget(rdo)
        layout.addSpacing(5)

        self.identifier_types = gui.current_db.get_all_identifier_types()
        self.identifier_combo = ListComboBox(self, self.identifier_types)
        search_type_group_box_layout.insertWidget(3, self.identifier_combo)

        match_layout = QHBoxLayout()
        layout.addLayout(match_layout)

        self.title_match_group_box = QGroupBox(_('Title Matching'),self)
        match_layout.addWidget(self.title_match_group_box)
        title_match_group_box_layout = QGridLayout()
        self.title_match_group_box.setLayout(title_match_group_box_layout)
        self.title_button_group = QButtonGroup(self)
        self.title_button_group.buttonClicked.connect(self._title_radio_clicked)
        for row, key in enumerate(TITLE_DESCS.keys()):
            rdo = QRadioButton(titlecase(key), self)
            rdo.row = row
            self.title_button_group.addButton(rdo)
            self.title_button_group.setId(rdo, row)
            title_match_group_box_layout.addWidget(rdo, row, 0, 1, 1)
        self.title_soundex_label = QLabel(_('Length:'), self)
        self.title_soundex_label.setToolTip(_('The shorter the soundex length, the greater likelihood '
                                         'of false positives.\n'
                                         'Large soundex values reduce your chances of matches'))
        title_match_group_box_layout.addWidget(self.title_soundex_label, 2, 1, 1, 1, Qt.AlignRight)
        self.title_soundex_spin = QSpinBox()
        self.title_soundex_spin.setRange(1, 99)
        title_match_group_box_layout.addWidget(self.title_soundex_spin, 2, 2, 1, 1, Qt.AlignLeft)

        self.author_match_group_box = QGroupBox(_('Author Matching'), self)
        match_layout.addWidget(self.author_match_group_box)
        author_match_group_box_layout = QGridLayout()
        self.author_match_group_box.setLayout(author_match_group_box_layout)
        self.author_button_group = QButtonGroup(self)
        self.author_button_group.buttonClicked.connect(self._author_radio_clicked)
        for row, key in enumerate(AUTHOR_DESCS.keys()):
            rdo = QRadioButton(titlecase(key), self)
            rdo.row = row
            self.author_button_group.addButton(rdo)
            self.author_button_group.setId(rdo, row)
            author_match_group_box_layout.addWidget(rdo, row, 0, 1, 1)
        self.author_soundex_label = QLabel(_('Length:'), self)
        self.author_soundex_label.setToolTip(self.title_soundex_label.toolTip())
        author_match_group_box_layout.addWidget(self.author_soundex_label, 2, 1, 1, 1, Qt.AlignRight)
        self.author_soundex_spin = QSpinBox()
        self.author_soundex_spin.setRange(1, 99)
        author_match_group_box_layout.addWidget(self.author_soundex_spin, 2, 2, 1, 1, Qt.AlignLeft)

        self.description = QTextEdit(self)
        self.description.setReadOnly(True)
        layout.addSpacing(5)
        layout.addWidget(self.description)

        layout.addSpacing(5)
        display_group_box = QGroupBox(_('Result Options'), self)
        layout.addWidget(display_group_box)
        display_group_box_layout = QGridLayout()
        display_group_box.setLayout(display_group_box_layout)
        self.show_all_button = QRadioButton(_('Show all groups at once with highlighting'), self)
        self.show_one_button = QRadioButton(_('Show one group at a time'), self)
        display_group_box_layout.addWidget(self.show_all_button, 0, 0, 1, 1)
        display_group_box_layout.addWidget(self.show_one_button, 0, 1, 1, 1)
        self.show_tag_author_checkbox = QCheckBox(_('Highlight authors in the tag browser for ignore title searches'))
        self.show_tag_author_checkbox.setToolTip(_('When checked, will ensure that the authors for the current group\n'
                                                'are shown in the tag browser and highlighted if multiple groups shown.\n'
                                                'Only applies for author duplicate searches.'))
        display_group_box_layout.addWidget(self.show_tag_author_checkbox, 1, 0, 1, 2)
        self.sort_numdups_checkbox = QCheckBox(_('Sort groups by number of duplicates'))
        self.sort_numdups_checkbox.setToolTip(_('When unchecked, will sort by an approximation of the title\n'
                                                'or by author if title is being ignored'))
        display_group_box_layout.addWidget(self.sort_numdups_checkbox, 2, 0, 1, 2)
        self.include_languages_checkbox = QCheckBox(_('Include languages metadata when comparing titles'))
        self.include_languages_checkbox.setToolTip(_('When checked, books with identical titles but different\n'
                                                'languages metadata field values will not show as duplicates'))
        display_group_box_layout.addWidget(self.include_languages_checkbox, 3, 0, 1, 2)
        self.auto_delete_binary_dups_checkbox = QCheckBox(_('When doing a Binary Compare, automatically remove duplicate formats'))
        self.auto_delete_binary_dups_checkbox.setToolTip(
              _('When checked and the Binary duplicate search is run, if duplicate formats are found\n'
                'then all except one are deleted. The format on the oldest book record will be kept.\n'
                'This is a convenience function for where you have multiple formats associated with\n'
                'each book and hence it is not readily obvious which of these is the duplicate.\n'
                'Note that the book records themselves are not deleted, and will still appear in the\n'
                'results for merging even if they now have no formats.'))
        display_group_box_layout.addWidget(self.auto_delete_binary_dups_checkbox, 4, 0, 1, 2)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._ok_clicked)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.search_type = cfg.plugin_prefs.get(cfg.KEY_SEARCH_TYPE, SEARCH_TYPES[0])
        # For legacy plugin users
        if self.search_type == 'isbn':
            self.search_type = 'identifier'
        self.identifier_type = cfg.plugin_prefs.get(cfg.KEY_IDENTIFIER_TYPE, 'isbn')
        self.identifier_combo.populate_combo(self.identifier_type)
        self.title_match = cfg.plugin_prefs.get(cfg.KEY_TITLE_MATCH, 'identical')
        self.author_match  = cfg.plugin_prefs.get(cfg.KEY_AUTHOR_MATCH, 'identical')
        search_type_idx = SEARCH_TYPES.index(self.search_type)
        self.search_type_button_group.button(search_type_idx).setChecked(True)
        title_idx = list(TITLE_DESCS.keys()).index(self.title_match)
        self.title_button_group.button(title_idx).setChecked(True)
        author_idx = list(AUTHOR_DESCS.keys()).index(self.author_match)
        self.author_button_group.button(author_idx).setChecked(True)
        self._update_description()

        self.title_soundex_spin.setValue(cfg.plugin_prefs.get(cfg.KEY_TITLE_SOUNDEX, 6))
        self.author_soundex_spin.setValue(cfg.plugin_prefs.get(cfg.KEY_AUTHOR_SOUNDEX, 8))

        show_all_groups = cfg.plugin_prefs.get(cfg.KEY_SHOW_ALL_GROUPS, True)
        self.show_all_button.setChecked(show_all_groups)
        self.show_one_button.setChecked(not show_all_groups)
        sort_groups_by_title = cfg.plugin_prefs.get(cfg.KEY_SORT_GROUPS_TITLE, True)
        self.sort_numdups_checkbox.setChecked(not sort_groups_by_title)
        show_tag_author = cfg.plugin_prefs.get(cfg.KEY_SHOW_TAG_AUTHOR, True)
        self.show_tag_author_checkbox.setChecked(show_tag_author)
        include_languages = cfg.plugin_prefs.get(cfg.KEY_INCLUDE_LANGUAGES, False)
        self.include_languages_checkbox.setChecked(include_languages)
        auto_delete_binary_dups = cfg.plugin_prefs.get(cfg.KEY_AUTO_DELETE_BINARY_DUPS, False)
        self.auto_delete_binary_dups_checkbox.setChecked(auto_delete_binary_dups)

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def _search_type_radio_clicked(self, button):
        idx = button.row
        self.search_type = SEARCH_TYPES[idx]
        self._update_description()

    def _title_radio_clicked(self, button):
        idx = button.row
        self.title_match = list(TITLE_DESCS.keys())[idx]
        self._update_description()

    def _author_radio_clicked(self, button):
        idx = button.row
        self.author_match = list(AUTHOR_DESCS.keys())[idx]
        self._update_description()

    def _update_description(self):
        if self.search_type == 'titleauthor':
            self._enable_title_author_options(enabled=True)
            desc = TITLE_DESCS[self.title_match].format(AUTHOR_DESCS[self.author_match])
        else:
            self._enable_title_author_options(enabled=False)
            if self.search_type == 'identifier':
                desc = IDENTIFIER_DESC
            else: # self.search_type == 'binary':
                desc = BINARY_DESC
        self.description.setText(desc)

    def _enable_title_author_options(self, enabled):
        self.title_match_group_box.setVisible(enabled)
        self.author_match_group_box.setVisible(enabled)
        for btn in self.title_button_group.buttons():
            btn.setEnabled(enabled)
        for btn in self.author_button_group.buttons():
            btn.setEnabled(enabled)
        self.title_soundex_label.setEnabled(enabled)
        self.title_soundex_spin.setEnabled(enabled)
        self.author_soundex_label.setEnabled(enabled)
        self.author_soundex_spin.setEnabled(enabled)
        if enabled:
            self.title_button_group.button(4).setEnabled(self.author_match != 'ignore')
            self.author_button_group.button(4).setEnabled(self.title_match != 'ignore')
            # Do not allow a combination of Ignore Title, Identical Author
            ident_auth_btn = self.author_button_group.button(0)
            ident_auth_btn.setEnabled(self.title_match != 'ignore')
            if not ident_auth_btn.isEnabled() and ident_auth_btn.isChecked():
                # We have to move the author radio button selection to a valid one
                self.author_button_group.button(1).setChecked(True)
                self.author_match = list(AUTHOR_DESCS.keys())[1]

    def _ok_clicked(self):
        cfg.plugin_prefs[cfg.KEY_SEARCH_TYPE] = self.search_type
        cfg.plugin_prefs[cfg.KEY_IDENTIFIER_TYPE] = self.identifier_combo.selected_value()
        cfg.plugin_prefs[cfg.KEY_TITLE_MATCH] = self.title_match
        cfg.plugin_prefs[cfg.KEY_AUTHOR_MATCH] = self.author_match
        show_all_groups = self.show_all_button.isChecked()
        cfg.plugin_prefs[cfg.KEY_SHOW_ALL_GROUPS] = show_all_groups
        sort_groups_by_title = not self.sort_numdups_checkbox.isChecked()
        cfg.plugin_prefs[cfg.KEY_SORT_GROUPS_TITLE] = sort_groups_by_title
        show_tag_author = self.show_tag_author_checkbox.isChecked()
        cfg.plugin_prefs[cfg.KEY_SHOW_TAG_AUTHOR] = show_tag_author
        cfg.plugin_prefs[cfg.KEY_TITLE_SOUNDEX] = int(str(self.title_soundex_spin.value()))
        cfg.plugin_prefs[cfg.KEY_AUTHOR_SOUNDEX] = int(str(self.author_soundex_spin.value()))
        cfg.plugin_prefs[cfg.KEY_INCLUDE_LANGUAGES] = self.include_languages_checkbox.isChecked()
        cfg.plugin_prefs[cfg.KEY_AUTO_DELETE_BINARY_DUPS] = self.auto_delete_binary_dups_checkbox.isChecked()
        self.accept()


class BookExemptionsTableWidget(QTableWidget):

    def __init__(self, parent):
        QTableWidget.__init__(self, parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def populate(self, books):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(books))
        header_labels = ['Remove', 'Title', 'Author', 'Series', 'Tags', 'Date']
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(24)

        for row, book in enumerate(books):
            self._populate_table_row(row, book)

        self.setSortingEnabled(False)
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)
        self.resizeColumnToContents(3)
        self.resizeColumnToContents(5)
        if len(books) > 0:
            self.selectRow(0)

    def _populate_table_row(self, row, book):
        if row == 0:
            self.setItem(row, 0, ReadOnlyTableWidgetItem(''))
        else:
            self.setItem(row, 0, CheckableTableWidgetItem(False))

        title_widget = ReadOnlyTableWidgetItem(book.title)
        title_widget.setData(Qt.UserRole, book.id)
        self.setItem(row, 1, title_widget)

        display_authors = authors_to_string(book.authors)
        self.setItem(row, 2, ReadOnlyTableWidgetItem(display_authors))

        display_series = ''
        if book.series:
            display_series = '%s [%s]' % (book.series, fmt_sidx(book.series_index))
        self.setItem(row, 3, ReadOnlyTableWidgetItem(display_series))

        display_tags = ''
        if book.tags:
            display_tags = ', '.join(book.tags)
        self.setItem(row, 4, ReadOnlyTableWidgetItem(display_tags))

        display_timestamp = format_date(book.timestamp, format=None)
        self.setItem(row, 5, ReadOnlyTableWidgetItem(display_timestamp))

    def get_checked_book_ids(self):
        ids = []
        for row in list(range(1, self.rowCount())):
            if row:
                if self.item(row, 0).get_boolean_value():
                    ids.append(self.item(row, 1).data(Qt.UserRole))
        return ids


class AuthorExemptionsTableWidget(QTableWidget):

    def __init__(self, parent):
        QTableWidget.__init__(self, parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def populate(self, authors):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(authors))
        header_labels = ['Remove', 'Author']
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setDefaultSectionSize(24)

        for row, author in enumerate(authors):
            self._populate_table_row(row, author)

        self.setSortingEnabled(False)
        self.resizeColumnToContents(0)
        if len(authors) > 0:
            self.selectRow(0)

    def _populate_table_row(self, row, author):
        if row == 0:
            self.setItem(row, 0, ReadOnlyTableWidgetItem(''))
        else:
            self.setItem(row, 0, CheckableTableWidgetItem(False))
        self.setItem(row, 1, ReadOnlyTableWidgetItem(author))

    def get_checked_authors(self):
        authors = []
        for row in list(range(1, self.rowCount())):
            if row:
                if self.item(row, 0).get_boolean_value():
                    authors.append(str(self.item(row, 1).text()))
        return authors


class ManageExemptionsDialog(SizePersistedDialog):
    '''
    Dialog to configure search options and perform the search
    '''
    def __init__(self, parent, db, book_id, book_exemptions, author_exemptions_map):
        SizePersistedDialog.__init__(self, parent, 'duplicate finder plugin:exemptions dialog')

        self.setWindowTitle(_('Manage Duplicate Exemptions'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'images/find_duplicates.png', _('Manage Exemptions'))
        layout.addLayout(title_layout)

        self._exempt_books_table = None
        if book_exemptions:
            layout.addSpacing(10)
            help_label1 = QLabel(_('The first book below will never appear as a duplicate '
                                   'with the following books.<br/>'
                                   'To allow future duplicate consideration, tick the remove checkbox '
                                   'and click ok.'), self)
            layout.addWidget(help_label1)

            self._exempt_books_table = BookExemptionsTableWidget(self)
            layout.addWidget(self._exempt_books_table)
            # Populate the table with book exemptions
            books = self._get_books(db, book_id, book_exemptions)
            self._exempt_books_table.populate(books)

        self._exempt_authors_table_map = OrderedDict()
        if author_exemptions_map:
            layout.addSpacing(10)
            help_label2 = QLabel(_('The authors below will never appear as a duplicate '
                                   'with the following authors.<br/>'
                                   'To allow future duplicate consideration, tick the remove checkbox '
                                   'and click ok.'), self)
            layout.addWidget(help_label2)
            tab_widget = QTabWidget(self)
            layout.addWidget(tab_widget)
            for author, author_exemptions in list(author_exemptions_map.items()):
                tab_page = QWidget(self)
                tab_widget.addTab(tab_page, author)
                tab_page_layout = QVBoxLayout()
                tab_page.setLayout(tab_page_layout)
                exempt_authors_table = AuthorExemptionsTableWidget(self)
                tab_page_layout.addWidget(exempt_authors_table)
                self._exempt_authors_table_map[author] = exempt_authors_table
                # Populate the table with author exemptions
                authors = self._get_authors(db, author, author_exemptions)
                exempt_authors_table.populate(authors)
            layout.addSpacing(10)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def get_checked_book_ids(self):
        if self._exempt_books_table:
            return self._exempt_books_table.get_checked_book_ids()

    def get_checked_authors_map(self):
        author_exemptions_map = OrderedDict()
        for author, exempt_authors_table in list(self._exempt_authors_table_map.items()):
            checked_items = exempt_authors_table.get_checked_authors()
            if checked_items:
                author_exemptions_map[author] = checked_items
        return author_exemptions_map

    def _get_books(self, db, book_id, book_exemptions):
        book_ids = list([book_id])
        book_ids.extend(list(book_exemptions))
        try:
            books = [db.new_api.get_metadata(book_id)
                     for book_id in book_ids if db.data.has_id(book_id)]
        except:
            books = [db.get_metadata(book_id, index_is_id=True, get_user_categories=False)
                     for book_id in book_ids if db.data.has_id(book_id)]
        return books

    def _get_authors(self, db, author, author_exemptions):
        authors = list([author])
        authors.extend(sorted(list(author_exemptions)))
        return authors


# --------------------------------------------------------------
#           Variations Dialog and related controls
# --------------------------------------------------------------

class ItemsComboBox(EditWithComplete):

    def __init__(self, parent):
        EditWithComplete.__init__(self, parent)
        self.set_separator(None)
        self.setSizeAdjustPolicy(self.AdjustToMinimumContentsLengthWithIcon)
        self.setEditable(True)

    @property
    def current_val(self):
        return str(self.currentText()).strip()

    @current_val.setter
    def current_val(self, val):
        if not val:
            val = ''
        self.setEditText(val.strip())
        self.lineEdit().setCursorPosition(0)


    def initialize(self, items):
        self.books_to_refresh = set([])
        self.update_items_cache(items)
        self.clear()
        for name in items:
            self.addItem(name)
        self.lineEdit().setText('')


class FindVariationsDialog(SizePersistedDialog):

    DEFAULT_ROW_HEIGHT = 24
    ICON_SIZE = 16

    def __init__(self, gui):
        SizePersistedDialog.__init__(self, gui, 'find duplicates plugin:variations dialog')
        self.gui = gui
        self.db = gui.current_db
        self.alg = VariationAlgorithm(self.db)
        self.item_map = {}
        self.count_map = {}
        self.variations_map = {}
        self.is_renamed = False
        self.combo_items = []
        self.item_type = self.item_icon = None
        self.suppress_selection_change = False

        self._initialize_controls()

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()
        show_books = cfg.plugin_prefs.get(cfg.KEY_SHOW_VARIATION_BOOKS, True)
        self.show_books_chk.setChecked(show_books)
        self.opt_authors.setChecked(True)

    def _initialize_controls(self):
        self.setWindowTitle(_('Find Duplicates Plugin'))
        self.setWindowIcon(get_icon('images/find_duplicates.png'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.title_layout = ImageTitleLayout(self, 'user_profile.png', _('Find Metadata Variations'))
        layout.addLayout(self.title_layout)
        layout.addSpacing(10)

        igb = QGroupBox(_('Choose metadata column:'), self)
        layout.addWidget(igb)
        igbl = QHBoxLayout()
        igb.setLayout(igbl)
        self.opt_authors = QRadioButton(_('Authors'), self)
        self.opt_authors.toggled.connect(self._on_item_option_toggled)
        self.opt_authors.setMinimumWidth(80)
        self.opt_series = QRadioButton(_('Series'), self)
        self.opt_series.toggled.connect(self._on_item_option_toggled)
        self.opt_series.setMinimumWidth(80)
        self.opt_publishers = QRadioButton(_('Publisher'), self)
        self.opt_publishers.toggled.connect(self._on_item_option_toggled)
        self.opt_publishers.setMinimumWidth(80)
        self.opt_tags = QRadioButton(_('Tags'), self)
        self.opt_tags.toggled.connect(self._on_item_option_toggled)
        self.opt_tags.setMinimumWidth(80)
        igbl.addWidget(self.opt_authors)
        igbl.addWidget(self.opt_series)
        igbl.addWidget(self.opt_publishers)
        igbl.addWidget(self.opt_tags)
        igbl.addStretch(1)

        gb = QGroupBox(_('Choose similarity level:'), self)
        layout.addWidget(gb)
        gbl = QHBoxLayout()
        gb.setLayout(gbl)
        self.opt_similar = QRadioButton(_('Similar'), self)
        self.opt_similar.setChecked(True)
        self.opt_similar.setMinimumWidth(80)
        self.opt_soundex = QRadioButton(_('Soundex'), self)
        self.opt_soundex.setMinimumWidth(80)
        self.opt_fuzzy = QRadioButton(_('Fuzzy'), self)
        self.opt_fuzzy.setMinimumWidth(80)
        self.soundex_label = QLabel(_('Length:'), self)
        self.soundex_label.setToolTip(_('The shorter the soundex length, the greater likelihood of false positives.\n'
                                      'Large soundex values reduce your chances of matches'))
        self.soundex_spin = QSpinBox()
        self.soundex_spin.setRange(1, 99)
        refresh_button = QPushButton(_('Search'), self)
        refresh_button.setIcon(QIcon(I('search.png')))
        refresh_button.setToolTip(_('Search for results'))
        refresh_button.clicked.connect(self._refresh_results)
        refresh_button.setDefault(True)
        gbl.addWidget(self.opt_similar)
        gbl.addWidget(self.opt_soundex)
        gbl.addWidget(self.soundex_label)
        gbl.addWidget(self.soundex_spin)
        gbl.addWidget(self.opt_fuzzy)
        gbl.addStretch(1)
        gbl.addWidget(refresh_button)

        rgb = QGroupBox(_('Search results:'), self)
        layout.addWidget(rgb, 1)

        gl = QGridLayout()
        rgb.setLayout(gl)

        self.item_lbl = QLabel(_('Authors:'), self)
        self.vlbl = QLabel(_('Variations:'), self)

        self.item_list = QListWidget(self)
        self.item_list.setAlternatingRowColors(True)
        self.item_list.setIconSize(QSize(self.ICON_SIZE, self.ICON_SIZE))
        self.item_list.currentItemChanged.connect(self._on_list_item_changed)
        self.item_list.doubleClicked.connect(self._on_list_item_double_clicked)

        self.variations_list = QListWidget(self)
        self.variations_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.variations_list.setIconSize(QSize(self.ICON_SIZE, self.ICON_SIZE))
        self.variations_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.variations_list.customContextMenuRequested.connect(self._on_context_menu_requested)
        self.variations_list.itemSelectionChanged.connect(self._on_variation_list_item_changed)

        self.show_books_chk = QCheckBox(_('&Show matching books'), self)
        self.show_books_chk.setToolTip(_('As a group is selected, show the search results in the library view'))
        self.show_books_chk.clicked.connect(self._on_show_books_checkbox_changed)

        self.rename_lbl = QLabel(_('Rename to:'), self)
        self.rename_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.rename_combo = ItemsComboBox(self)

        gl.addWidget(self.item_lbl, 0, 0, 1, 2)
        gl.addWidget(self.vlbl, 0, 2, 1, 1)
        gl.addWidget(self.item_list, 1, 0, 1, 2)
        gl.addWidget(self.variations_list, 1, 2, 1, 1)
        gl.addWidget(self.show_books_chk, 2, 0, 1, 1)
        gl.addWidget(self.rename_lbl, 2, 1, 1, 1)
        gl.addWidget(self.rename_combo, 2, 2, 1, 1)
        gl.setColumnStretch(1, 2)
        gl.setColumnStretch(2, 3)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self._close_clicked)
        self.rename_button = button_box.addButton(_('&Rename'), QDialogButtonBox.ActionRole)
        self.rename_button.setToolTip(_('Rename all of the selected items to this name'))
        self.rename_button.clicked.connect(self._rename_selected)

        self.ignore_button = button_box.addButton(_('&Ignore'), QDialogButtonBox.ActionRole)
        self.ignore_button.setToolTip(_('Ignore all selected items from consideration at this time'))
        self.ignore_button.clicked.connect(self._ignore_selected)
        layout.addWidget(button_box)

    def _refresh_results(self):
        item_type = self.item_type.lower()
        match_type = 'similar'
        if self.opt_soundex.isChecked():
            match_type = 'soundex'
            soundex_len = int(str(self.soundex_spin.value()))
            if item_type == 'authors':
                cfg.plugin_prefs[cfg.KEY_AUTHOR_SOUNDEX] = soundex_len
                set_author_soundex_length(soundex_len)
            elif item_type == 'publisher':
                cfg.plugin_prefs[cfg.KEY_PUBLISHER_SOUNDEX] = soundex_len
                set_publisher_soundex_length(soundex_len)
            elif item_type == 'series':
                cfg.plugin_prefs[cfg.KEY_SERIES_SOUNDEX] = soundex_len
                set_series_soundex_length(soundex_len)
            elif item_type == 'tags':
                cfg.plugin_prefs[cfg.KEY_TAGS_SOUNDEX] = soundex_len
                set_tags_soundex_length(soundex_len)
        elif self.opt_fuzzy.isChecked():
            match_type = 'fuzzy'

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.item_map, self.count_map, self.variations_map = \
                self.alg.run_variation_check(match_type, item_type)
            combo_item_texts = []
            for item_id in self.item_map.keys():
                if item_id in self.count_map:
                    combo_item_texts.append(self.item_map[item_id])
            self.combo_items = combo_item_texts
            self._populate_rename_combo()
            self._populate_items_list()
        finally:
            QApplication.restoreOverrideCursor()
        if len(self.variations_map) == 0:
            info_dialog(self.gui, _('No matches'), _('You have no variations of {0} using this criteria').format(self.item_type),
                        show=True, show_copy_button=False)

    def _populate_rename_combo(self):
        self.rename_combo.initialize(sorted(self.combo_items))

    def _populate_items_list(self, select_next=''):
        self.item_list.blockSignals(True)
        self.item_list.clear()
        descs = []
        for item_id in list(self.variations_map.keys()):
            desc = self.item_map[item_id]
            descs.append(desc)
            lw = QListWidgetItem('%s (%d books)'%(desc,self.count_map[item_id]))
            lw.setData(Qt.UserRole, item_id)
            lw.setIcon(self.item_icon)
            lw.setSizeHint(QSize(0, self.DEFAULT_ROW_HEIGHT))
            self.item_list.addItem(lw)
        self.variations_list.sortItems()
        self.item_list.blockSignals(False)
        self.rename_combo.setText('')
        idx = 0
        if select_next:
            # We want to find the "next" item alphabetically after this text
            descs.append(select_next)
            snames = sorted(descs)
            idx = snames.index(select_next)
            if idx == len(snames)-1:
                idx -= 1
        if self.item_list.count() > 0 and idx >= 0:
            self.item_list.setCurrentRow(idx)

    def _populate_variations_list(self):
        self.suppress_selection_change = True
        self.variations_list.clear()
        ilw = self.item_list.currentItem()
        if ilw is None:
            return
        item_id, _text = self._decode_list_item(ilw)
        for variation_id in self.variations_map[item_id]:
            if variation_id in self.item_map:
                lw = QListWidgetItem('%s (%d books)'%(self.item_map[variation_id],self.count_map[variation_id]))
                lw.setData(Qt.UserRole, variation_id)
                lw.setIcon(self.item_icon)
                lw.setSizeHint(QSize(0, self.DEFAULT_ROW_HEIGHT))
                self.variations_list.addItem(lw)

        self.variations_list.sortItems()
        self.variations_list.selectAll()
        if self.show_books_chk.isChecked():
            self._search_in_gui()
        self.suppress_selection_change = False

    def _on_context_menu_requested(self, pos):
        ilw = self.variations_list.currentItem()
        if ilw is None:
            return
        _item_id, text = self._decode_list_item(ilw)

        self.variations_context_menu = QMenu(self)
        self.variations_context_menu.addAction(_('Use this variation name'),
                                               partial(self._on_use_variation_name, text))
        self.variations_context_menu.popup(self.variations_list.mapToGlobal(pos))

    def _on_use_variation_name(self, text):
        self.rename_combo.setText(text)

    def _search_in_gui(self):
        ilw = self.item_list.currentItem()
        if ilw is None:
            self.gui.search.clear()
            return
        item_id, text = self._decode_list_item(ilw)
        query = self.search_pattern % text
        for var_lw in self.variations_list.selectedItems():
            variation_id, variation_text = self._decode_list_item(var_lw)
            if variation_id in self.item_map:
                query = query + ' or ' + self.search_pattern % variation_text
        self.gui.search.set_search_string(query)

    def _on_show_books_checkbox_changed(self, is_checked):
        if is_checked:
            self._search_in_gui()

    def _on_item_option_toggled(self, is_checked):
        if self.opt_authors.isChecked():
            self.item_type = 'Authors'
            icon_name = 'user_profile.png'
            self.search_pattern='authors:"=%s"'
            self.soundex_spin.setValue(cfg.plugin_prefs.get(cfg.KEY_AUTHOR_SOUNDEX, 8))
        if self.opt_publishers.isChecked():
            self.item_type = 'Publisher'
            icon_name = 'publisher.png'
            self.search_pattern='publisher:"=%s"'
            self.soundex_spin.setValue(cfg.plugin_prefs.get(cfg.KEY_PUBLISHER_SOUNDEX, 6))
        elif self.opt_series.isChecked():
            self.item_type = 'Series'
            icon_name = 'series.png'
            self.search_pattern='series:"=%s"'
            self.soundex_spin.setValue(cfg.plugin_prefs.get(cfg.KEY_SERIES_SOUNDEX, 6))
        elif self.opt_tags.isChecked():
            self.item_type = 'Tags'
            icon_name = 'tags.png'
            self.search_pattern='tags:"=%s"'
            self.soundex_spin.setValue(cfg.plugin_prefs.get(cfg.KEY_TAGS_SOUNDEX, 4))
        self.item_icon = QIcon(I(icon_name))
        self.title_layout.update_title_icon(icon_name)

        self.item_lbl.setText(self.item_type + ':')
        self.item_list.clear()
        self.rename_combo.clear()
        self._on_list_item_changed()

    def _on_list_item_changed(self):
        has_items = self.item_list.count() > 0
        self.rename_button.setEnabled(has_items)
        self.ignore_button.setEnabled(has_items)
        if self.item_list.currentRow() == -1:
            self.rename_combo.setText('')
            self.vlbl.setText(_('Variations:'))
        else:
            _id, text = self._decode_list_item(self.item_list.currentItem())
            self.rename_combo.setText(text)
            self.vlbl.setText(_('Variations of: {0}').format(text))
        self._populate_variations_list()

    def _on_list_item_double_clicked(self, idx):
        if idx != None and idx.row() >= 0:
            self._rename_selected()

    def _on_variation_list_item_changed(self):
        if self.suppress_selection_change:
            return
        # Special feature, if user deselects variations then reduce the visible
        # books to reflect only the actual selected items.
        if self.show_books_chk.isChecked():
            self._search_in_gui()

    def _decode_list_item(self, lw):
        item_id = int(lw.data(Qt.UserRole))
        item_text = ''
        if item_id in self.item_map:
            item_text = self.item_map[item_id]
        return item_id, item_text

    def _rename_selected(self):
        # We will rename both the LHS and all selected items on the RHS where needed.
        new_name = str(self.rename_combo.text())
        if not new_name:
            return
        item_lw = self.item_list.currentItem()
        item_id, item_text = self._decode_list_item(item_lw)
        rename_items = [(item_id, item_text)]
        for var_lw in self.variations_list.selectedItems():
            rename_items.append(self._decode_list_item(var_lw))
        if len(rename_items) == 1:
            # The user has not selected anything on the right hand side.
            return

        message = '<p>'+_('Are you sure you want to rename the selected {0} items to "{1}"?').format(len(rename_items), new_name)+'</p>'
        if not confirm(message,'find_duplicates_confirm_rename', self):
            return
        # Do the database rename for each of these ids where necessary
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for rename_item_id, rename_item_text in rename_items:
                if rename_item_text != new_name:
                    self._perform_database_rename(rename_item_id, new_name)
                    self.item_map[rename_item_id] = new_name
                # Now update our maps
                var_ids_set = self.variations_map[rename_item_id]
                for other_item_id, _other_item_text in rename_items:
                    if other_item_id != rename_item_id:
                        var_ids_set.remove(other_item_id)
                if len(var_ids_set) == 0:
                    del self.variations_map[rename_item_id]
                    del self.item_map[rename_item_id]
                    del self.count_map[rename_item_id]
                    self.combo_items.remove(rename_item_text)
            # Make sure we remove the actual selected item even if it has unresolved matches
            if item_id in self.variations_map:
                del self.variations_map[item_id]
                del self.item_map[item_id]
                del self.count_map[item_id]
            if item_text in self.combo_items:
                self.combo_items.remove(item_text)
            if new_name not in self.combo_items:
                self.combo_items.append(new_name)
        finally:
            QApplication.restoreOverrideCursor()

        # Update our on-screen presentation with the new lists - selection will be lost!
        self.variations_list.clear()
        self._populate_rename_combo()
        self._populate_items_list(select_next=item_text)
        self._on_list_item_changed()

    def _ignore_selected(self):
        # We will remove all selected items from the RHS from the map.
        item_lw = self.item_list.currentItem()
        item_id, item_text = self._decode_list_item(item_lw)
        ignore_items = [(item_id, item_text)]
        for var_lw in self.variations_list.selectedItems():
            ignore_items.append(self._decode_list_item(var_lw))

        for ignore_item_id, ignore_item_text in ignore_items:
            var_ids_set = self.variations_map[ignore_item_id]
            for other_item_id, other_item_text in ignore_items:
                if other_item_id != ignore_item_id:
                    var_ids_set.remove(other_item_id)
            if len(var_ids_set) == 0:
                del self.variations_map[ignore_item_id]
                del self.item_map[ignore_item_id]
                del self.count_map[ignore_item_id]
            if ignore_item_text in self.combo_items:
                self.combo_items.remove(ignore_item_text)

        # Update our on-screen presentation with the new lists - selection will be lost!
        self.variations_list.clear()
        self._populate_rename_combo()
        self._populate_items_list(select_next=item_text)

    def _perform_database_rename(self, old_id, text):
        self.is_renamed = True
        item_type = self.item_type.lower()
        if item_type == 'authors':
            self.db.rename_author(old_id, text)
        elif item_type == 'publisher':
            self.db.rename_publisher(old_id, text)
        elif item_type == 'series':
            self.db.rename_series(old_id, text, change_index=False)
        elif item_type == 'tags':
            self.db.rename_tag(old_id, text)

    def is_changed(self):
        return self.is_renamed

    def is_showing_books(self):
        return self.show_books_chk.isChecked()

    def _close_clicked(self):
        cfg.plugin_prefs[cfg.KEY_SHOW_VARIATION_BOOKS] = self.show_books_chk.isChecked()
        self.reject()



LIBRARY_IDENTIFIER_DESC = _('<b>Book duplicate search</b><br/>'
              '- Report books in this library which have an identical identifier for books '
              'in the target library.<br/>')

LIBRARY_BINARY_DESC = _('<b>Book duplicate search</b><br/>'
              '- Report books in this library which are binary identical to books in your target library.<br/>'
              '- Compares the actual file size of every book format in your libraries, '
              'computing an SHA hash to compare contents where sizes match.<br/>'
              '- Books found using this search are guaranteed to be duplicates.')

LIBRARY_TITLE_DESCS = OrderedDict([
               ('identical',_('<b>Title duplicate search</b><br/>'
                             '- Report books in this library compared to your target library with an <b>identical title</b> and {0}<br/>'
                             '- Titles must match exactly excluding case.')),
               ('similar',  _('<b>Title duplicate search</b><br/>'
                             '- Report books in this library compared to your target library with a <b>similar title</b> and {0}<br/>'
                             '- Similar title matches apply removal of common punctuation and '
                             'prefixes and applies the same title matching logic as Automerge.')),
               ('soundex',  _('<b>Title duplicate search</b><br/>'
                             '- Report books in this library compared to your target library with a <b>soundex title</b> and {0}<br/>'
                             '- Soundex title matches are based on the same removal of punctuation '
                             'and common prefixes as a similar title search.')),
               ('fuzzy',    _('<b>Title duplicate search</b><br/>'
                             '- Report books in this library compared to your target library with a <b>fuzzy title</b> and {0}<br/>'
                             '- Fuzzy title matches remove all punctuation, subtitles '
                             'and any words after \'and\', \'or\' or \'aka\' in the title.')),
               ('ignore',   _('<b>Author duplicate search</b><br/>'
                             '- Report books in this library compared to your target library <b>ignoring title</b> with {0}<br/>'
                             '- Ignore title searches are best to find variations of author '
                             'names regardless of the books you have for each.'))
               ])


class FindLibraryDuplicatesDialog(SizePersistedDialog):
    '''
    Dialog to configure search options and perform the search
    '''
    def __init__(self, gui):
        SizePersistedDialog.__init__(self, gui, 'find_duplicates_plugin:library_duplicate_dialog')
        self.gui = gui
        self.setWindowTitle(_('Find Duplicates'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'library.png', _('Cross Library Search Options'))
        layout.addLayout(title_layout)
        layout.addSpacing(5)

        library_group_box = QGroupBox(_('Compare With Library:'), self)
        layout.addWidget(library_group_box)
        lgbl = QHBoxLayout()
        library_group_box.setLayout(lgbl)
        library_label = QLabel(_('Library:'), self)
        self.location = HistoryLineEditWithDelete(self)
        self.browse_button = QToolButton(self)
        self.browse_button.setIcon(get_icon('document_open.png'))
        self.browse_button.clicked.connect(self._choose_location)
        lgbl.addWidget(library_label)
        lgbl.addWidget(self.location, 1)
        lgbl.addWidget(self.browse_button)
        self.location.initialize('find_duplicates_plugin:library_duplicate_combo')

        search_type_group_box = QGroupBox(_('Duplicate Search Type:'), self)
        layout.addWidget(search_type_group_box)
        search_type_group_box_layout = QHBoxLayout()
        search_type_group_box.setLayout(search_type_group_box_layout)
        self.search_type_button_group = QButtonGroup(self)
        self.search_type_button_group.buttonClicked.connect(self._search_type_radio_clicked)
        for row, text in enumerate([_('Title/Author'), _('Binary Compare'), _('Identifier')]):
            rdo = QRadioButton(text, self)
            rdo.row = row
            self.search_type_button_group.addButton(rdo)
            self.search_type_button_group.setId(rdo, row)
            search_type_group_box_layout.addWidget(rdo)
        layout.addSpacing(5)

        self.identifier_types = gui.current_db.get_all_identifier_types()
        self.identifier_combo = ListComboBox(self, self.identifier_types)
        search_type_group_box_layout.insertWidget(3, self.identifier_combo)

        match_layout = QHBoxLayout()
        layout.addLayout(match_layout)

        self.title_match_group_box = QGroupBox(_('Title Matching:'),self)
        match_layout.addWidget(self.title_match_group_box)
        title_match_group_box_layout = QGridLayout()
        self.title_match_group_box.setLayout(title_match_group_box_layout)
        self.title_button_group = QButtonGroup(self)
        self.title_button_group.buttonClicked.connect(self._title_radio_clicked)
        for row, key in enumerate(LIBRARY_TITLE_DESCS.keys()):
            rdo = QRadioButton(titlecase(key), self)
            rdo.row = row
            self.title_button_group.addButton(rdo)
            self.title_button_group.setId(rdo, row)
            title_match_group_box_layout.addWidget(rdo, row, 0, 1, 1)
        self.title_soundex_label = QLabel(_('Length:'), self)
        self.title_soundex_label.setToolTip(_('The shorter the soundex length, the greater likelihood '
                                         'of false positives.\n'
                                         'Large soundex values reduce your chances of matches'))
        title_match_group_box_layout.addWidget(self.title_soundex_label, 2, 1, 1, 1, Qt.AlignRight)
        self.title_soundex_spin = QSpinBox()
        self.title_soundex_spin.setRange(1, 99)
        title_match_group_box_layout.addWidget(self.title_soundex_spin, 2, 2, 1, 1, Qt.AlignLeft)

        self.author_match_group_box = QGroupBox(_('Author Matching:'), self)
        match_layout.addWidget(self.author_match_group_box)
        author_match_group_box_layout = QGridLayout()
        self.author_match_group_box.setLayout(author_match_group_box_layout)
        self.author_button_group = QButtonGroup(self)
        self.author_button_group.buttonClicked.connect(self._author_radio_clicked)
        for row, key in enumerate(AUTHOR_DESCS.keys()):
            rdo = QRadioButton(titlecase(key), self)
            rdo.row = row
            self.author_button_group.addButton(rdo)
            self.author_button_group.setId(rdo, row)
            author_match_group_box_layout.addWidget(rdo, row, 0, 1, 1)
        self.author_soundex_label = QLabel(_('Length:'), self)
        self.author_soundex_label.setToolTip(self.title_soundex_label.toolTip())
        author_match_group_box_layout.addWidget(self.author_soundex_label, 2, 1, 1, 1, Qt.AlignRight)
        self.author_soundex_spin = QSpinBox()
        self.author_soundex_spin.setRange(1, 99)
        author_match_group_box_layout.addWidget(self.author_soundex_spin, 2, 2, 1, 1, Qt.AlignLeft)

        self.description = QTextEdit(self)
        self.description.setReadOnly(True)
        layout.addSpacing(5)
        layout.addWidget(self.description)

        layout.addSpacing(5)
        compare_group_box = QGroupBox(_('Compare Options:'), self)
        layout.addWidget(compare_group_box)
        compare_group_box_layout = QVBoxLayout()
        compare_group_box.setLayout(compare_group_box_layout)
        self.include_languages_checkbox = QCheckBox(_('Include languages metadata when comparing titles'))
        self.include_languages_checkbox.setToolTip(_('When checked, books with identical titles but different\n'
                                                'languages metadata field values will not show as duplicates'))
        compare_group_box_layout.addWidget(self.include_languages_checkbox)
        self.display_results_checkbox = QCheckBox(_('Display duplicate books when search completes.'))
        self.display_results_checkbox.setToolTip(_('Uncheck this option if you just want the output log.'))
        compare_group_box_layout.addWidget(self.display_results_checkbox)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._ok_clicked)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.search_type = cfg.plugin_prefs.get(cfg.KEY_SEARCH_TYPE, SEARCH_TYPES[0])
        # For legacy plugin users
        if self.search_type == 'isbn':
            self.search_type = 'identifier'
        self.identifier_type = cfg.plugin_prefs.get(cfg.KEY_IDENTIFIER_TYPE, 'isbn')
        self.identifier_combo.populate_combo(self.identifier_type)
        self.title_match = cfg.plugin_prefs.get(cfg.KEY_TITLE_MATCH, 'identical')
        self.author_match  = cfg.plugin_prefs.get(cfg.KEY_AUTHOR_MATCH, 'identical')
        search_type_idx = SEARCH_TYPES.index(self.search_type)
        self.search_type_button_group.button(search_type_idx).setChecked(True)
        title_idx = list(LIBRARY_TITLE_DESCS.keys()).index(self.title_match)
        self.title_button_group.button(title_idx).setChecked(True)
        author_idx = list(AUTHOR_DESCS.keys()).index(self.author_match)
        self.author_button_group.button(author_idx).setChecked(True)
        self._update_description()

        self.title_soundex_spin.setValue(cfg.plugin_prefs.get(cfg.KEY_TITLE_SOUNDEX, 6))
        self.author_soundex_spin.setValue(cfg.plugin_prefs.get(cfg.KEY_AUTHOR_SOUNDEX, 8))
        include_languages = cfg.plugin_prefs.get(cfg.KEY_INCLUDE_LANGUAGES, False)
        self.include_languages_checkbox.setChecked(include_languages)
        display_results = cfg.plugin_prefs.get(cfg.KEY_DISPLAY_LIBRARY_RESULTS, False)
        self.display_results_checkbox.setChecked(display_results)

        self.library_config = cfg.get_library_config(self.gui.current_db)
        self.location.setText(self.library_config.get(cfg.KEY_LAST_LIBRARY_COMPARE, ''))

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def _choose_location(self, *args):
        loc = choose_dir(self, 'choose duplicate library',
                _('Choose library location to compare against'))
        if loc is not None:
            self.location.setText(loc)

    def _search_type_radio_clicked(self, button):
        idx = button.row
        self.search_type = SEARCH_TYPES[idx]
        self._update_description()

    def _title_radio_clicked(self, button):
        idx = button.row
        self.title_match = list(LIBRARY_TITLE_DESCS.keys())[idx]
        self._update_description()

    def _author_radio_clicked(self, button):
        idx = button.row
        self.author_match = list(AUTHOR_DESCS.keys())[idx]
        self._update_description()

    def _update_description(self):
        if self.search_type == 'titleauthor':
            self._enable_title_author_options(enabled=True)
            desc = LIBRARY_TITLE_DESCS[self.title_match].format(AUTHOR_DESCS[self.author_match])
        else:
            self._enable_title_author_options(enabled=False)
            if self.search_type == 'identifier':
                desc = LIBRARY_IDENTIFIER_DESC
            else: # self.search_type == 'binary':
                desc = LIBRARY_BINARY_DESC
        self.description.setText(desc)

    def _enable_title_author_options(self, enabled):
        self.title_match_group_box.setVisible(enabled)
        self.author_match_group_box.setVisible(enabled)
        for btn in self.title_button_group.buttons():
            btn.setEnabled(enabled)
        for btn in self.author_button_group.buttons():
            btn.setEnabled(enabled)
        self.title_soundex_label.setEnabled(enabled)
        self.title_soundex_spin.setEnabled(enabled)
        self.author_soundex_label.setEnabled(enabled)
        self.author_soundex_spin.setEnabled(enabled)
        if enabled:
            self.title_button_group.button(4).setEnabled(self.author_match != 'ignore')
            self.author_button_group.button(4).setEnabled(self.title_match != 'ignore')
            # We WILL allow a combination of Ignore Title, Identical Author

    def _ok_clicked(self):
        db = self.gui.current_db
        loc = str(self.location.text()).strip()
        if not loc:
            return error_dialog(self, _('No library specified'),
                    _('You must specify a library path'), show=True)
        exists = db.exists_at(loc)
        if patheq(loc, db.library_path):
            return error_dialog(self, _('Same as current'),
                    _('The location {0} contains the current calibre library').format(loc), show=True)
        if not exists:
            return error_dialog(self, _('No existing library found'),
                    _('There is no existing calibre library at {0}').format(loc),
                    show=True)

        cfg.plugin_prefs[cfg.KEY_SEARCH_TYPE] = self.search_type
        cfg.plugin_prefs[cfg.KEY_IDENTIFIER_TYPE] = self.identifier_combo.selected_value()
        cfg.plugin_prefs[cfg.KEY_TITLE_MATCH] = self.title_match
        cfg.plugin_prefs[cfg.KEY_AUTHOR_MATCH] = self.author_match
        cfg.plugin_prefs[cfg.KEY_TITLE_SOUNDEX] = int(str(self.title_soundex_spin.value()))
        cfg.plugin_prefs[cfg.KEY_AUTHOR_SOUNDEX] = int(str(self.author_soundex_spin.value()))
        cfg.plugin_prefs[cfg.KEY_INCLUDE_LANGUAGES] = self.include_languages_checkbox.isChecked()
        cfg.plugin_prefs[cfg.KEY_DISPLAY_LIBRARY_RESULTS] = self.display_results_checkbox.isChecked()
        self.location.save_history()
        self.library_config[cfg.KEY_LAST_LIBRARY_COMPARE] = loc
        cfg.set_library_config(db, self.library_config)
        self.accept()


class SummaryMessageBox(MessageBox):
    def __init__(self, parent, title, msg, det_msg='', q_icon=None,
                 show_copy_button=True, default_yes=True):
        MessageBox.__init__(self, MessageBox.INFO, title, msg, det_msg, q_icon,
                            show_copy_button, parent, default_yes)
        if det_msg:
            b = self.bb.addButton(_('Save log')+'...', self.bb.AcceptRole)
            b.setIcon(QIcon(I('save.png')))
            b.clicked.connect(self._save_log)

    def _save_log(self):
        txt = str(self.det_msg.toPlainText())
        filename = choose_save_file(self, 'find_duplicates_plugin:save_log',
                _('Save Find Duplicates log'),
                filters=[(_('Duplicates log file'), ['txt'])])
        if filename:
            with codecs.open(filename, 'w', 'utf-8') as f:
                f.write(txt)
