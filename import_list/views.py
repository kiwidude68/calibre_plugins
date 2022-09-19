from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

try:
    from qt.core import (Qt, QTableView, QAbstractItemView)
except ImportError:    
    from PyQt5.Qt import (Qt, QTableView, QAbstractItemView)

from calibre.gui2.library.delegates import TextDelegate, CompleteDelegate


class ListBookView(QTableView):
    '''
    View for displaying the books showing their list import data
    '''
    def __init__(self, parent):
        QTableView.__init__(self, parent)
        self.setSortingEnabled(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.verticalHeader().setDefaultSectionSize(24)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

    def set_model(self, books_model, import_cols_map, headers):
        self.setModel(books_model)
        # Hide all calibre matches columns
        for i in range(len(import_cols_map), len(headers)):
            self.setColumnHidden(i, True)
        self.resizeColumnsToContents()
        # Specify a minimum width for title and author
        self._set_minimum_column_width(0, 150)
        self._set_minimum_column_width(1, 100)
        # Make sure every other column has a minimum width
        for i in range(2, len(import_cols_map)):
            self.setColumnHidden(i, False)
            self._set_minimum_column_width(i, 50)

    def _set_minimum_column_width(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)


class MatchedBookView(QTableView):
    '''
    View for displaying the books showing their matched calibre data
    '''
    def __init__(self, parent, db):
        QTableView.__init__(self, parent)
        self.setSortingEnabled(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.verticalHeader().setDefaultSectionSize(24)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.db = db
        self.import_cols_map = None
        self.display_cols_map = None
        self.editable_columns = None

    def set_model(self, books_model, import_cols_map, display_cols_map, editable_columns):
        self.setModel(books_model)
        self.import_cols_map = import_cols_map
        self.display_cols_map = display_cols_map
        self.editable_columns = editable_columns

        # Hide all import list columns
        for i in range(0, len(self.import_cols_map)):
            self.setColumnHidden(i, True)

        self.title_delegate = TextDelegate(self)
        self.authors_delegate = CompleteDelegate(self, '&', 'all_author_names', True)
        self.authors_delegate.set_database(self.db)
        self.series_delegate = TextDelegate(self)
        self.series_delegate.set_auto_complete_function(self.db.all_series)
        self.tags_delegate = CompleteDelegate(self, '&', 'all_tags', True)
        self.tags_delegate.set_database(self.db)

        self._set_delegates_for_columns()
        self.resizeColumnsToContents()
        # Specify a minimum width for title, author and series
        offset = len(self.import_cols_map)
        self._set_minimum_column_width(offset, 150)
        self._set_minimum_column_width(offset + 1, 100)
        self._set_minimum_column_width(offset + 2, 50)
        # Make sure every other column has a minimum width
        for i in range(3, len(self.display_cols_map)):
            self.setColumnHidden(offset + i, False)
            self._set_minimum_column_width(offset + i, 50)

    def _set_delegates_for_columns(self):
        for i, col in enumerate(self.display_cols_map.keys()):
            idx = i + len(self.import_cols_map)
            if '!calibre_'+col in self.editable_columns:
                self.setItemDelegateForColumn(idx, getattr(self, col+'_delegate'))

    def _set_minimum_column_width(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)
