from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'
__copyright__ = '2011, Grant Drake'

try:
    from qt.core import (Qt, QAbstractTableModel, QIcon, QBrush, QSortFilterProxyModel,
                        QModelIndex)
except ImportError:
    from PyQt5.Qt import (Qt, QAbstractTableModel, QIcon, QBrush, QSortFilterProxyModel,
                        QModelIndex)

from calibre.ebooks.metadata import fmt_sidx

from calibre_plugins.import_list.common_icons import get_icon
from calibre_plugins.import_list.page_common import parse_series, AUTHOR_SEPARATOR

try:
    load_translations()
except NameError:
    pass

FILTER_ALL = 0
FILTER_MATCHED = 1
FILTER_UNMATCHED = 2

class BookModel(QAbstractTableModel):
    '''
    Our data will consist in book of a dictionary which will have:
      'title', 'authors', [ + other columns ]
      '!calibre_title', '!calibre_authors', [ + other columns ]
      '!id', '!status', '!authors_sort'
    '''

    def __init__(self, db, books, import_cols_map, display_cols_map):
        QAbstractTableModel.__init__(self)
        self.db = db
        self.books = books
        self.import_cols_map = import_cols_map
        self.display_cols_map = display_cols_map
        self.editable_columns = ['!calibre_title', '!calibre_authors',
                                 '!calibre_series', '!calibre_tags']
        self.custom_columns = self.db.field_metadata.custom_field_metadata()

        all_headers = list(self.import_cols_map.values()) + \
                      list(self.display_cols_map.values())
        self.headers = all_headers

        # Now setup our list of names to lookup in our book dictionary
        self.column_map = []
        for col in self.import_cols_map.keys():
            self.column_map.append(col)
        for col in self.display_cols_map.keys():
            self.column_map.append('!calibre_' + col)

    def rowCount(self, parent):
        if parent and parent.isValid():
            return 0
        return len(self.books)

    def columnCount(self, parent):
        if parent and parent.isValid():
            return 0
        return len(self.headers)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return None

    def data(self, index, role):
        if not index.isValid():
            return None;
        row, col = index.row(), index.column()
        if row < 0 or row >= len(self.books):
            return None
        #print('Getting data for row: ', row, ' col:', col, ' role:', role)
        book = self.books[row]
        column_name = self.column_map[col]
        value = book.get(column_name, '')
        status = book['!status']

        if role in [Qt.DisplayRole, Qt.UserRole]:
            return value

        elif role == Qt.DecorationRole:
            if col == 0:
                icon_name = 'ok.png'
                if status == 'multiple':
                    icon_name = 'edit_input.png'
                elif status == 'unmatched':
                    icon_name = 'list_remove.png'
                elif status == 'empty':
                    icon_name = 'add_book.png'
                elif status == 'added':
                    icon_name = 'plus.png'
                return QIcon(get_icon(icon_name))

        elif role == Qt.ToolTipRole:
            if col == 0:
                tooltip = _('A matching book was found in your calibre library')
                if status == 'multiple':
                    tooltip = _('Multiple matches found for this title/author.\n' \
                              'Resolve this by selecting your match below.')
                elif status == 'unmatched':
                    tooltip = _('No matching book found in your library.\n' \
                              'Add an empty book or search for a match below.')
                elif status == 'empty':
                    tooltip = _('An empty book will be added if you save this list')
                elif status == 'added':
                    tooltip = _('This book was added to your list manually')
                return tooltip

        elif role == Qt.ForegroundRole:
            color = None
            if status == 'multiple':
                color = Qt.magenta
            elif status == 'unmatched':
                color = Qt.red
            elif column_name.startswith('!calibre_'):
                #print('Getting foreground for:',column_name, book)
                # Detect whether this column has a value changed from original
                # We also have stored in the book dictionary the original values
                # stored as $ + column name - .e.g !calibre_tags and $!calibre_tags
                orig_column_name = '$' + column_name
                if orig_column_name in book:
                    #print('Orig value:',book[orig_column_name], 'current value:',value)
                    if value != book[orig_column_name]:
                        color = Qt.blue
            if color is not None:
                return QBrush(color)
        return None

    def setData(self, index, value, role):
        done = False
        if role == Qt.EditRole:
            row, col = index.row(), index.column()
            book = self.books[row]
            val = str(value.toString()).strip()
            col_name = self.column_map[col]

            if col_name == '!calibre_title':
                book[col_name] = val
            elif col_name == '!calibre_authors':
                author = val
                if not author:
                    author = _('Unknown')
                authors = [a.strip() for a in author.split('&')]
                book[col_name] = AUTHOR_SEPARATOR.join(authors)
            elif col_name == '!calibre_series':
                series_name, series_index = parse_series(val)
                if series_name:
                    book[col_name] = '%s [%s]' % (series_name, fmt_sidx(series_index))
                else:
                    book[col_name] = ''
            elif col_name == '!calibre_tags':
                tags = [t.strip() for t in val.split(',')]
                book[col_name] = ', '.join(tags)

            self.dataChanged.emit(index, index)
            done = True
        return done

    def flags(self, index):
        flags = QAbstractTableModel.flags(self, index)
        if index.isValid():
            book = self.books[index.row()]
            col_name = self.column_map[index.column()]
            if book['!status'] == 'empty' and col_name in self.editable_columns:
                #print('Flags for:', col_name, 'are now empty')
                flags |= Qt.ItemIsEditable
        return flags

    def insertRows(self, row, count, idx):
        self.beginInsertRows(QModelIndex(), row, row + count - 1)
        for i in range(0, count):
            book = {}
            book['!id'] = -1
            book['!status'] = 'added'
            book['!authors_sort'] = ''
            book['!mi'] = None
            book['!overwrite_metadata'] = False
            self.books.insert(row + i, book)
        self.endInsertRows()
        return True

    def removeRows(self, row, count, idx):
        self.beginRemoveRows(QModelIndex(), row, row + count - 1)
        for i in range(0, count):
            self.books.pop(row + i)
        self.endRemoveRows()
        return True

    def is_custom_column(self, cc_label):
        return cc_label in self.custom_columns


class BookSortFilterModel(QSortFilterProxyModel):

    def __init__(self, parent):
        QSortFilterProxyModel.__init__(self, parent)
        self.setSortRole(Qt.UserRole)
        self.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.filter_criteria = FILTER_ALL
        self.match_tier = None

    def filterAcceptsRow(self, sourceRow, sourceParent):
        index = self.sourceModel().index(sourceRow, 0, sourceParent)
        book = self.sourceModel().books[index.row()]
        if self.filter_criteria == FILTER_ALL:
            return True
        if self.filter_criteria == FILTER_MATCHED:
            is_matched = book['!status'] in ['matched','empty']
            if self.match_tier:
                return is_matched and (book['!match_tier'] == self.match_tier)
            else:
                return is_matched
        if self.filter_criteria == FILTER_UNMATCHED:
            return book['!status'] in ['unmatched','multiple']
        return False

    def set_filter_criteria(self, filter_value, match_tier):
        self.filter_criteria = filter_value
        self.match_tier = match_tier
        self.invalidateFilter()
