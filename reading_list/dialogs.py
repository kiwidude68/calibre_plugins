from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from six import text_type as unicode
from six.moves import range

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (QVBoxLayout, QTableWidget, QHBoxLayout, QDialogButtonBox,
                        QAbstractItemView, Qt, QGridLayout,
                        QListWidget, QListWidgetItem, QLabel, QPushButton,
                        QToolButton, QSpacerItem)
except ImportError:
    from PyQt5.Qt import (QVBoxLayout, QTableWidget, QHBoxLayout, QDialogButtonBox,
                        QAbstractItemView, Qt, QGridLayout,
                        QListWidget, QListWidgetItem, QLabel, QPushButton,
                        QToolButton, QSpacerItem)

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.ebooks.metadata import fmt_sidx
from calibre.gui2.dialogs.confirm_delete import confirm

from calibre_plugins.reading_list.common_compatibility import qSizePolicy_Minimum, qSizePolicy_Expanding
from calibre_plugins.reading_list.common_icons import get_icon
from calibre_plugins.reading_list.common_dialogs import SizePersistedDialog
from calibre_plugins.reading_list.common_widgets import ReadOnlyTableWidgetItem, ImageTitleLayout

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


class EditListTableWidget(QTableWidget):

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

        self.setSortingEnabled(False)
        self.resizeColumnsToContents()
        self.setMinimumColumnWidth(0, 100)
        self.setMaximumColumnWidth(0, 300)
        self.setMinimumColumnWidth(1, 100)
        self.setMaximumColumnWidth(1, 300)
        self.setMinimumSize(300, 0)
        if len(books) > 0:
            self.selectRow(0)

    def setMinimumColumnWidth(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def setMaximumColumnWidth(self, col, maximum):
        if self.columnWidth(col) > maximum:
            self.setColumnWidth(col, maximum)

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
        selrows = self.selectionModel().selectedRows()
        rows = sorted(selrows, key=lambda x: x.row(), reverse=True)
        if len(rows) == 0:
            return
        message = _('<p>Are you sure you want to remove this book from the list?')
        if len(rows) > 1:
            message = _('<p>Are you sure you want to remove the selected %d books from the list?')%len(rows)
        if not confirm(message,'reading_list_delete_item', self):
            return
        first_sel_row = self.currentRow()
        for selrow in rows:
            self.removeRow(selrow.row())
        if first_sel_row < self.rowCount():
            self.select_and_scroll_to_row(first_sel_row)
        elif self.rowCount() > 0:
            self.select_and_scroll_to_row(first_sel_row - 1)

    def select_and_scroll_to_row(self, row):
        self.selectRow(row)
        self.scrollToItem(self.currentItem())

    def move_rows_up(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        first_sel_row = selrows[0]
        if first_sel_row <= 0:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        for selrow in selrows:
            self.swap_row_widgets(selrow - 1, selrow + 1)
        scroll_to_row = first_sel_row - 1
        if scroll_to_row > 0:
            scroll_to_row = scroll_to_row - 1
        self.scrollToItem(self.item(scroll_to_row, 0))

    def move_10_rows_up(self):
        for row in range(0, 10):
            self.move_rows_up()

    def move_to_top(self):
        for row in range(0, self.rowCount()):
            self.move_rows_up()

    def move_rows_down(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        last_sel_row = selrows[-1]
        if last_sel_row == self.rowCount() - 1:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        for selrow in reversed(selrows):
            self.swap_row_widgets(selrow + 2, selrow)
        scroll_to_row = last_sel_row + 1
        if scroll_to_row < self.rowCount() - 1:
            scroll_to_row = scroll_to_row + 1
        self.scrollToItem(self.item(scroll_to_row, 0))

    def move_10_rows_down(self):
        for row in range(0, 10):
            self.move_rows_down()

    def move_to_bottom(self):
        for row in range(0, self.rowCount()):
            self.move_rows_down()

    def swap_row_widgets(self, src_row, dest_row):
        self.blockSignals(True)
        self.insertRow(dest_row)
        for col in range(0, self.columnCount()):
            self.setItem(dest_row, col, self.takeItem(src_row, col))
        self.removeRow(src_row)
        self.blockSignals(False)


class EditListDialog(SizePersistedDialog):
    def __init__(self, parent, books, list_name):
        SizePersistedDialog.__init__(self, parent, _('reading list plugin:edit list dialog'))
        self.setWindowTitle(_('Edit List'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'images/reading_list.png',
                                        _('\'%s\' list books')%list_name)
        layout.addLayout(title_layout)
        books_layout = QHBoxLayout()
        layout.addLayout(books_layout)

        self.books_table = EditListTableWidget(self)
        books_layout.addWidget(self.books_table)

        button_layout = QVBoxLayout()
        books_layout.addLayout(button_layout)

        # move to top button
        self.move_top_button = QToolButton(self)
        self.move_top_button.setToolTip(_('Move selected books to the top of the list'))
        self.move_top_button.setIcon(get_icon('images/arrow_up_double_bar.png'))
        self.move_top_button.clicked.connect(self.books_table.move_to_top)
        button_layout.addWidget(self.move_top_button)
        # move up 10 rows button
        self.move_10_up_button = QToolButton(self)
        self.move_10_up_button.setToolTip(_('Move selected books 10 rows up the list'))
        self.move_10_up_button.setIcon(get_icon('images/arrow_up_double.png'))
        self.move_10_up_button.clicked.connect(self.books_table.move_10_rows_up)
        button_layout.addWidget(self.move_10_up_button)
        # move up one row button
        self.move_up_button = QToolButton(self)
        self.move_up_button.setToolTip(_('Move selected books up the list'))
        self.move_up_button.setIcon(get_icon('images/arrow_up_single.png'))
        self.move_up_button.clicked.connect(self.books_table.move_rows_up)
        button_layout.addWidget(self.move_up_button)

        spacerItem = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem)

	# remove from list button
        self.remove_button = QToolButton(self)
        self.remove_button.setToolTip(_('Remove selected books from the list'))
        self.remove_button.setIcon(get_icon('list_remove.png'))
        self.remove_button.clicked.connect(self.remove_from_list)
        button_layout.addWidget(self.remove_button)
        spacerItem1 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)

        # move down one row button
        button_layout.addItem(spacerItem1)
        self.move_down_button = QToolButton(self)
        self.move_down_button.setToolTip(_('Move selected books down the list'))
        self.move_down_button.setIcon(get_icon('images/arrow_down_single.png'))
        self.move_down_button.clicked.connect(self.books_table.move_rows_down)
        button_layout.addWidget(self.move_down_button)
        # move down 10 rows button
        self.move_10_down_button = QToolButton(self)
        self.move_10_down_button.setToolTip(_('Move selected books 10 rows down the list'))
        #self.move_10_down_button.setIcon(QIcon(I('arrow-down.png')))
        self.move_10_down_button.setIcon(get_icon('images/arrow_down_double.png'))
        self.move_10_down_button.clicked.connect(self.books_table.move_10_rows_down)
        button_layout.addWidget(self.move_10_down_button)
        # move to bottom button
        self.move_bottom_button = QToolButton(self)
        self.move_bottom_button.setToolTip(_('Move selected books to the bottom of the list'))
        #self.move_bottom_button.setIcon(QIcon(I('arrow-down.png')))
        self.move_bottom_button.setIcon(get_icon('images/arrow_down_double_bar.png'))
        self.move_bottom_button.clicked.connect(self.books_table.move_to_bottom)
        button_layout.addWidget(self.move_bottom_button)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()
        self.books_table.populate_table(books)

    def remove_from_list(self):
        self.books_table.remove_selected_rows()

    def get_calibre_ids(self):
        return self.books_table.get_calibre_ids()


class MoveBooksDialog(SizePersistedDialog):
    def __init__(self, parent, lists_in_use, list_names):
        SizePersistedDialog.__init__(self, parent, _('reading list plugin:move books dialog'))
        self.setWindowTitle(_('Move Books'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'images/reading_list.png',
                                        _('Move books between lists'))
        layout.addLayout(title_layout)
        main_layout = QGridLayout()
        layout.addLayout(main_layout)

        self.remove_from_label = QLabel(_('Select list(s) to remove from'), self)
        main_layout.addWidget(self.remove_from_label, 0, 0, 1, 2)
        self.remove_from_list = QListWidget(self)
        self.remove_from_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        main_layout.addWidget(self.remove_from_list, 1, 0, 1, 2)

        self.select_all_button = QPushButton(_('Select &All'), self)
        self.select_all_button.clicked.connect(self.remove_from_list.selectAll)
        main_layout.addWidget(self.select_all_button, 2, 0, 1, 1)

        self.select_none_button = QPushButton(_('Select &None'), self)
        self.select_none_button.clicked.connect(self.remove_from_list.clearSelection)
        main_layout.addWidget(self.select_none_button, 2, 1, 1, 1)

        self.dest_list_label = QLabel(_('Select list to add to'), self)
        main_layout.addWidget(self.dest_list_label, 0, 2, 1, 1)
        self.dest_list = QListWidget(self)
        self.dest_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        main_layout.addWidget(self.dest_list, 1, 2, 1, 1)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()
        self._populate_list(self.remove_from_list, lists_in_use)
        self._populate_list(self.dest_list, list_names, set_selected=False)
        self.dest_list.item(0).setSelected(True)

    def _populate_list(self, list_widget, list_names, set_selected=True):
        list_widget.clear()
        for list_name in list_names:
            item = QListWidgetItem(list_name, list_widget)
            list_widget.addItem(item)
            item.setSelected(set_selected)

    def select_no_items(self):
        for item in self.remove_from_list.items():
            item.setSelected(False)

    def get_source_list_names(self):
        values = []
        for item in self.remove_from_list.selectedItems():
            values.append(unicode(item.text()))
        return values

    def get_dest_list_names(self):
        values = []
        for item in self.dest_list.selectedItems():
            values.append(unicode(item.text()))
        return values

