from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import six
from six import text_type as unicode
from six.moves import range
from six.moves.urllib.parse import quote_plus

from functools import partial

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (Qt, QHBoxLayout, QVBoxLayout, QLabel, QApplication,
                        QDialogButtonBox, QAbstractItemView, QTableWidget, QAction,
                        QTableWidgetItem, QComboBox, QUrl, QCheckBox, QDoubleSpinBox,
                        QToolButton, QSpacerItem, QSpinBox)
except ImportError:
    from PyQt5.Qt import (Qt, QHBoxLayout, QVBoxLayout, QLabel, QApplication,
                        QDialogButtonBox, QAbstractItemView, QTableWidget, QAction,
                        QTableWidgetItem, QComboBox, QUrl, QCheckBox, QDoubleSpinBox,
                        QToolButton, QSpacerItem, QSpinBox)

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.ebooks.metadata import fmt_sidx
from calibre.ebooks.metadata.book.base import Metadata
from calibre.gui2 import question_dialog, open_url
from calibre.gui2.complete2 import EditWithComplete
from calibre.gui2.dialogs.add_empty_book import AddEmptyBookDialog
from calibre.utils.config import tweaks
from calibre.utils.date import qt_to_dt
from calibre.utils.icu import sort_key

import calibre_plugins.manage_series.config as cfg
from calibre_plugins.manage_series.common_compatibility import qSizePolicy_Minimum, qSizePolicy_Expanding, qtDropActionCopyAction
from calibre_plugins.manage_series.common_icons import get_icon
from calibre_plugins.manage_series.common_dialogs import SizePersistedDialog
from calibre_plugins.manage_series.common_widgets import (ReadOnlyTableWidgetItem, ImageTitleLayout,
                                                          DateDelegate, DateTableWidgetItem)
from calibre_plugins.manage_series.book import SeriesBook

class LockSeriesDialog(SizePersistedDialog):

    def __init__(self, parent, title, initial_value):
        SizePersistedDialog.__init__(self, parent, 'Manage Series plugin:lock series dialog')
        self.initialize_controls(title, initial_value)

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def initialize_controls(self, title, initial_value):
        self.setWindowTitle(_('Lock Series Index'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'images/lock32.png', _('Lock Series Index'))
        layout.addLayout(title_layout)

        layout.addSpacing(10)
        self.title_label = QLabel(_('Series index for book:')+' \'%s\''%title, self)
        layout.addWidget(self.title_label)

        hlayout = QHBoxLayout()
        layout.addLayout(hlayout)

        self.value_spinbox = QDoubleSpinBox(self)
        self.value_spinbox.setRange(0, 99000000)
        self.value_spinbox.setDecimals(2)
        if initial_value is not None:
            self.value_spinbox.setValue(initial_value)
        self.value_spinbox.selectAll()
        hlayout.addWidget(self.value_spinbox, 0)
        hlayout.addStretch(1)

        self.assign_same_checkbox = QCheckBox(_('&Assign this index value to all remaining books'), self)
        layout.addWidget(self.assign_same_checkbox)
        layout.addStretch(1)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_value(self):
        return float(unicode(self.value_spinbox.value()))

    def assign_same_value(self):
        return self.assign_same_checkbox.isChecked()

class TitleWidgetItem(QTableWidgetItem):

    def __init__(self, book):
        QTableWidgetItem.__init__(self, book.title())
        if not book.is_valid():
            self.setIcon(get_icon('dialog_warning.png'))
            self.setToolTip(_('You have conflicting or out of sequence series indexes'))
        elif book.id() is None:
            self.setIcon(get_icon('add_book.png'))
            self.setToolTip(_('Empty book added to series'))
        elif book.is_title_changed() or book.is_pubdate_changed() or book.is_series_changed():
            self.setIcon(get_icon('format-list-ordered.png'))
            self.setToolTip(_('The book data has been changed'))
        else:
            self.setIcon(get_icon('ok.png'))
            self.setToolTip(_('The series data is unchanged'))


class AuthorsTableWidgetItem(ReadOnlyTableWidgetItem):

    def __init__(self, authors):
        text = ' & '.join(authors)
        ReadOnlyTableWidgetItem.__init__(self, text)
        self.setForeground(Qt.darkGray)


class SeriesTableWidgetItem(ReadOnlyTableWidgetItem):

    def __init__(self, series_name, series_index, is_original=False, assigned_index=None):
        if series_name:
            text = '%s [%s]' % (series_name, fmt_sidx(series_index))
        else:
            text = ''
        ReadOnlyTableWidgetItem.__init__(self, text)
        if assigned_index is not None:
            self.setIcon(get_icon('images/lock.png'))
            self.setToolTip(_('Value assigned by user'))
        if is_original:
            #self.foreground().setColor(Qt.darkGray)
            self.setForeground(Qt.darkGray)


class SeriesColumnComboBox(QComboBox):

    def __init__(self, parent, series_columns):
        QComboBox.__init__(self, parent)
        self.series_columns = series_columns
        for key, column in six.iteritems(series_columns):
            self.addItem('%s (%s)'% (key, column['name']))
        self.insertItem(0, 'Series')

    def select_text(self, selected_key):
        if selected_key == 'Series':
            self.setCurrentIndex(0)
        else:
            for idx, key in enumerate(self.seriesColumns.keys()):
                if key == selected_key:
                    self.setCurrentIndex(idx)
                    return

    def selected_value(self):
        if self.currentIndex() == 0:
            return 'Series'
        return list(self.series_columns.keys())[self.currentIndex() - 1]


class SeriesTableWidget(QTableWidget):

    def __init__(self, parent):
        QTableWidget.__init__(self, parent)
        self.create_context_menu()
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDropIndicatorShown(True)
        self.fmt = tweaks['gui_pubdate_display_format']
        if self.fmt is None:
            self.fmt = 'MMM yyyy'
        self.pin_view = None

    def create_context_menu(self):
        self.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.assign_original_index_action = QAction(_('Lock old series index'), self)
        self.assign_original_index_action.setIcon(get_icon('images/lock.png'))
        self.assign_original_index_action.triggered.connect(self.parent().assign_original_index)
        self.addAction(self.assign_original_index_action)
        self.assign_index_action = QAction(_('Lock series index')+'...', self)
        self.assign_index_action.setIcon(get_icon('images/lock.png'))
        self.assign_index_action.triggered.connect(self.parent().assign_index)
        self.addAction(self.assign_index_action)
        self.clear_index_action = QAction(_('Unlock series index'), self)
        self.clear_index_action.setIcon(get_icon('images/lock_delete.png'))
        self.clear_index_action.triggered.connect(partial(self.parent().clear_index, all_rows=False))
        self.addAction(self.clear_index_action)
        self.clear_all_index_action = QAction(_('Unlock all series index'), self)
        self.clear_all_index_action.setIcon(get_icon('images/lock_open.png'))
        self.clear_all_index_action.triggered.connect(partial(self.parent().clear_index, all_rows=True))
        self.addAction(self.clear_all_index_action)
        sep1 = QAction(self)
        sep1.setSeparator(True)
        self.addAction(sep1)
        self.add_empty_action = QAction(_('Add empty books')+'...', self)
        self.add_empty_action.setIcon(get_icon('add_book.png'))
        self.add_empty_action.triggered.connect(self.parent().add_empty_book)
        self.addAction(self.add_empty_action)
        sep2 = QAction(self)
        sep2.setSeparator(True)
        self.addAction(sep2)
        for name in [_('PubDate'), _('Original Series Index'), _('Original Series Name')]:
            sort_action = QAction(_('Sort by')+' '+name, self)
            sort_action.setIcon(get_icon('images/sort.png'))
            sort_action.triggered.connect(partial(self.parent().sort_by, name))
            self.addAction(sort_action)
        sep3 = QAction(self)
        sep3.setSeparator(True)
        self.addAction(sep3)
        for name, icon in [('FantasticFiction', 'images/ms_ff.png'),
                           ('Goodreads', 'images/ms_goodreads.png'),
                           ('Google', 'images/ms_google.png'),
                           ('Wikipedia', 'images/ms_wikipedia.png')]:
            menu_action = QAction('Search %s' % name, self)
            menu_action.setIcon(get_icon(icon))
            menu_action.triggered.connect(partial(self.parent().search_web, name))
            self.addAction(menu_action)

    def populate_table(self, books):
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(books))
        header_labels = [_('Title'), _('Author(s)'), _('PubDate'), _('Series'), _('New Series')]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(24)
        self.horizontalHeader().setStretchLastSection(True)

        for row, book in enumerate(books):
            self.populate_table_row(row, book)

        self.resizeColumnToContents(0)
        self.setMinimumColumnWidth(0, 150)
        self.setColumnWidth(1, 100)
        self.resizeColumnToContents(2)
        self.setMinimumColumnWidth(2, 60)
        self.resizeColumnToContents(3)
        self.setMinimumColumnWidth(3, 120)
        self.setSortingEnabled(False)
        self.setMinimumSize(550, 0)
        self.selectRow(0)
        delegate = DateDelegate(self, self.fmt, default_to_today=False)
        self.setItemDelegateForColumn(2, delegate)

    def setMinimumColumnWidth(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def populate_table_row(self, row, book):
        self.blockSignals(True)
        self.setItem(row, 0, TitleWidgetItem(book))
        self.setItem(row, 1, AuthorsTableWidgetItem(book.authors()))
        self.setItem(row, 2, DateTableWidgetItem(book.pubdate(), is_read_only=False,
                                                 default_to_today=False, fmt=self.fmt))
        self.setItem(row, 3, SeriesTableWidgetItem(book.orig_series_name(),
                                                   book.orig_series_index(),
                                                   is_original=True))
        self.setItem(row, 4, SeriesTableWidgetItem(book.series_name(),
                                                   book.series_index(),
                                                   assigned_index=book.assigned_index()))
        self.blockSignals(False)

    def swap_row_widgets(self, src_row, dest_row):
        self.blockSignals(True)
        self.insertRow(dest_row)
        for col in range(self.columnCount()):
            self.setItem(dest_row, col, self.takeItem(src_row, col))
        self.removeRow(src_row)
        self.blockSignals(False)

    def select_and_scroll_to_row(self, row):
        self.selectRow(row)
        self.scrollToItem(self.currentItem())

    def event_has_mods(self, event=None):
        mods = event.modifiers() if event is not None else \
                QApplication.keyboardModifiers()
        return mods & Qt.ControlModifier or mods & Qt.ShiftModifier

    def mousePressEvent(self, event):
        ep = event.pos()
        if self.indexAt(ep) not in self.selectionModel().selectedIndexes() and \
                event.button() == Qt.LeftButton and not self.event_has_mods():
            self.setDragEnabled(False)
        else:
            self.setDragEnabled(True)
        return QTableWidget.mousePressEvent(self, event)

    def dropEvent(self, event):
        rows = self.selectionModel().selectedRows()
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        drop_row = self.rowAt(event.pos().y())
        if drop_row == -1:
            drop_row = self.rowCount() - 1
        rows_before_drop = [idx for idx in selrows if idx < drop_row]
        rows_after_drop = [idx for idx in selrows if idx >= drop_row]

        dest_row = drop_row
        for selrow in rows_after_drop:
            dest_row += 1
            self.swap_row_widgets(selrow + 1, dest_row)
            book = self.parent().books.pop(selrow)
            self.parent().books.insert(dest_row, book)

        dest_row = drop_row + 1
        for selrow in reversed(rows_before_drop):
            self.swap_row_widgets(selrow, dest_row)
            book = self.parent().books.pop(selrow)
            self.parent().books.insert(dest_row - 1, book)
            dest_row = dest_row - 1

        event.setDropAction(qtDropActionCopyAction)
        # Determine the new row selection
        self.selectRow(drop_row)
        self.parent().renumber_series()

    def set_series_column_headers(self, text):
        item = self.horizontalHeaderItem(3)
        if item is not None:
            item.setText(_('Old')+' '+text)
        item = self.horizontalHeaderItem(4)
        if item is not None:
            item.setText(_('New')+' '+text)


class SeriesDialog(SizePersistedDialog):

    def __init__(self, parent, books, all_series, series_columns):
        SizePersistedDialog.__init__(self, parent, 'Manage Series plugin:series dialog')
        self.db = self.parent().library_view.model().db
        self.books = books
        self.all_series = all_series
        self.series_columns = series_columns
        self.block_events = True

        self.initialize_controls()

        # Books will have been sorted by the Calibre series column
        # Choose the appropriate series column to be editing
        initial_series_column = 'Series'
        self.series_column_combo.select_text(initial_series_column)
        if len(series_columns) == 0:
            # Will not have fired the series_column_changed event
            self.series_column_changed()
        # Renumber the books using the assigned series name/index in combos/spinbox
        self.renumber_series(display_in_table=False)

        # Display the books in the table
        self.block_events = False
        self.series_table.populate_table(books)
        if len(unicode(self.series_combo.text()).strip()) > 0:
            self.series_table.setFocus()
        else:
            self.series_combo.setFocus()
        self.update_series_headers(initial_series_column)

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def initialize_controls(self):
        self.setWindowTitle('Manage Series')
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'images/manage_series.png', _('Create or Modify Series'))
        layout.addLayout(title_layout)

        # Series name and start index layout
        series_name_layout = QHBoxLayout()
        layout.addLayout(series_name_layout)

        series_column_label = QLabel(_('Series &Column:'), self)
        series_name_layout.addWidget(series_column_label)
        self.series_column_combo = SeriesColumnComboBox(self, self.series_columns)
        self.series_column_combo.currentIndexChanged[int].connect(self.series_column_changed)
        series_name_layout.addWidget(self.series_column_combo)
        series_column_label.setBuddy(self.series_column_combo)
        series_name_layout.addSpacing(20)

        series_label = QLabel(_('Series &Name:'), self)
        series_name_layout.addWidget(series_label)
        self.series_combo = EditWithComplete(self)
        self.series_combo.setEditable(True)
        self.series_combo.setInsertPolicy(QComboBox.InsertAlphabetically)
        self.series_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.series_combo.setMinimumContentsLength(25)
        self.series_combo.currentIndexChanged[int].connect(self.series_changed)
        self.series_combo.editTextChanged.connect(self.series_changed)
        self.series_combo.set_separator(None)
        series_label.setBuddy(self.series_combo)
        series_name_layout.addWidget(self.series_combo)
        series_name_layout.addSpacing(20)
        series_start_label = QLabel(_('&Start At:'), self)
        series_name_layout.addWidget(series_start_label)
        self.series_start_number = QSpinBox(self)
        self.series_start_number.setRange(0, 99000000)
        self.series_start_number.valueChanged[int].connect(self.series_start_changed)
        series_name_layout.addWidget(self.series_start_number)
        series_start_label.setBuddy(self.series_start_number)
        series_name_layout.insertStretch(-1)

        # Main series table layout
        table_layout = QHBoxLayout()
        layout.addLayout(table_layout)

        self.series_table = SeriesTableWidget(self)
        self.series_table.itemSelectionChanged.connect(self.item_selection_changed)
        self.series_table.cellChanged[int,int].connect(self.cell_changed)

        table_layout.addWidget(self.series_table)
        table_button_layout = QVBoxLayout()
        table_layout.addLayout(table_button_layout)
        move_up_button = QToolButton(self)
        move_up_button.setToolTip(_('Move book up in series (Alt+Up)'))
        move_up_button.setIcon(get_icon('arrow-up.png'))
        move_up_button.setShortcut(_('Alt+Up'))
        move_up_button.clicked.connect(self.move_rows_up)
        table_button_layout.addWidget(move_up_button)
        move_down_button = QToolButton(self)
        move_down_button.setToolTip(_('Move book down in series (Alt+Down)'))
        move_down_button.setIcon(get_icon('arrow-down.png'))
        move_down_button.setShortcut(_('Alt+Down'))
        move_down_button.clicked.connect(self.move_rows_down)
        table_button_layout.addWidget(move_down_button)
        spacerItem1 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        table_button_layout.addItem(spacerItem1)
        assign_index_button = QToolButton(self)
        assign_index_button.setToolTip(_('Lock to index value')+'...')
        assign_index_button.setIcon(get_icon('images/lock.png'))
        assign_index_button.clicked.connect(self.assign_index)
        table_button_layout.addWidget(assign_index_button)
        clear_index_button = QToolButton(self)
        clear_index_button.setToolTip(_('Unlock series index'))
        clear_index_button.setIcon(get_icon('images/lock_delete.png'))
        clear_index_button.clicked.connect(self.clear_index)
        table_button_layout.addWidget(clear_index_button)
        spacerItem2 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        table_button_layout.addItem(spacerItem2)
        add_empty_button = QToolButton(self)
        add_empty_button.setToolTip(_('Add empty book to the series list'))
        add_empty_button.setIcon(get_icon('add_book.png'))
        add_empty_button.setShortcut(_('Ctrl+Shift+E'))
        add_empty_button.clicked.connect(self.add_empty_book)
        table_button_layout.addWidget(add_empty_button)
        delete_button = QToolButton(self)
        delete_button.setToolTip(_('Remove book from the series list'))
        delete_button.setIcon(get_icon('trash.png'))
        delete_button.clicked.connect(self.remove_book)
        table_button_layout.addWidget(delete_button)
        spacerItem3 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        table_button_layout.addItem(spacerItem3)
        move_left_button = QToolButton(self)
        move_left_button.setToolTip(_('Move series index to left of decimal point (Alt+Left)'))
        move_left_button.setIcon(get_icon('back.png'))
        move_left_button.setShortcut(_('Alt+Left'))
        move_left_button.clicked.connect(partial(self.series_indent_change, -1))
        table_button_layout.addWidget(move_left_button)
        move_right_button = QToolButton(self)
        move_right_button.setToolTip(_('Move series index to right of decimal point (Alt+Right)'))
        move_right_button.setIcon(get_icon('forward.png'))
        move_right_button.setShortcut(_('Alt+Right'))
        move_right_button.clicked.connect(partial(self.series_indent_change, 1))
        table_button_layout.addWidget(move_right_button)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        keep_button = button_box.addButton(' '+_('&Restore Original Series')+' ', QDialogButtonBox.ResetRole)
        keep_button.clicked.connect(self.restore_original_series)
        help_button = button_box.addButton(' '+_('&Help')+' ', QDialogButtonBox.ResetRole)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(cfg.show_help)

    def series_column_changed(self):
        series_column = self.series_column_combo.selected_value()
        SeriesBook.series_column = series_column
        # Choose a series name and series index from the first book in the list
        initial_series_name = ''
        initial_series_index = 1
        if len(self.books) > 0:
            first_book = self.books[0]
            initial_series_name = first_book.series_name()
            if initial_series_name:
                initial_series_index = int(first_book.series_index())
        # Populate the series name combo as appropriate for that column
        self.initialize_series_name_combo(series_column, initial_series_name)
        # Populate the series index spinbox with the initial value
        self.series_start_number.setProperty('value', initial_series_index)
        self.update_series_headers(series_column)
        if self.block_events:
            return
        self.renumber_series()

    def update_series_headers(self, series_column):
        if series_column == 'Series':
            self.series_table.set_series_column_headers(series_column)
        else:
            header_text = self.series_columns[series_column]['name']
            self.series_table.set_series_column_headers(header_text)

    def initialize_series_name_combo(self, series_column, series_name):
        self.series_combo.clear()
        if series_name is None:
            series_name = ''
        values = self.all_series
        if series_column == 'Series':
            self.series_combo.update_items_cache([x[1] for x in values])
            for i in values:
                _id, name = i
                self.series_combo.addItem(name)
        else:
            label = self.db.field_metadata.key_to_label(series_column)
            values = list(self.db.all_custom(label=label))
            values.sort(key=sort_key)
            self.series_combo.update_items_cache(values)
            for name in values:
                self.series_combo.addItem(name)
        self.series_combo.setEditText(series_name)

    def series_changed(self):
        if self.block_events:
            return
        self.renumber_series()

    def series_start_changed(self):
        if self.block_events:
            return
        self.renumber_series()

    def restore_original_series(self):
        # Go through the books and overwrite the indexes with the originals, fixing in place
        for book in self.books:
            if book.orig_series_index():
                book.set_assigned_index(book.orig_series_index())
                book.set_series_index(book.orig_series_index())
        # Now renumber the whole series so that anything in between gets changed
        self.renumber_series()

    def renumber_series(self, display_in_table=True):
        if len(self.books) == 0:
            return
        series_name = unicode(self.series_combo.currentText()).strip()
        series_index = float(unicode(self.series_start_number.value()))
        last_series_indent = 0
        for row, book in enumerate(self.books):
            book.set_series_name(series_name)
            series_indent = book.series_indent()
            if book.assigned_index() is not None:
                series_index = book.assigned_index()
            else:
                if series_indent >= last_series_indent:
                    if series_indent == 0:
                        if row > 0:
                            series_index += 1.
                    elif series_indent == 1:
                        series_index += 0.1
                    else:
                        series_index += 0.01
                else:
                    # When series indent decreases, need to round to next
                    if series_indent == 1:
                        series_index = round(series_index + 0.05, 1)
                    else: # series_indent == 0:
                        series_index = round(series_index + 0.5, 0)
            book.set_series_index(series_index)
            last_series_indent = series_indent
        # Now determine whether books have a valid index or not
        self.books[0].set_is_valid(True)
        for row in range(len(self.books)-1, 0, -1):
            book = self.books[row]
            previous_book = self.books[row-1]
            if book.series_index() <= previous_book.series_index():
                book.set_is_valid(False)
            else:
                book.set_is_valid(True)
        if display_in_table:
            for row, book in enumerate(self.books):
                self.series_table.populate_table_row(row, book)

    def assign_original_index(self):
        if len(self.books) == 0:
            return
        for row in self.series_table.selectionModel().selectedRows():
            book = self.books[row.row()]
            book.set_assigned_index(book.orig_series_index())
        self.renumber_series()
        self.item_selection_changed()

    def assign_index(self):
        if len(self.books) == 0:
            return
        auto_assign_value = None
        for row in self.series_table.selectionModel().selectedRows():
            book = self.books[row.row()]
            if auto_assign_value is not None:
                book.set_assigned_index(auto_assign_value)
                continue

            d = LockSeriesDialog(self, book.title(), book.series_index())
            d.exec_()
            if d.result() != d.Accepted:
                break
            if d.assign_same_value():
                auto_assign_value = d.get_value()
                book.set_assigned_index(auto_assign_value)
            else:
                book.set_assigned_index(d.get_value())

        self.renumber_series()
        self.item_selection_changed()

    def clear_index(self, all_rows=False):
        if len(self.books) == 0:
            return
        if all_rows:
            for book in self.books:
                book.set_assigned_index(None)
        else:
            for row in self.series_table.selectionModel().selectedRows():
                book = self.books[row.row()]
                book.set_assigned_index(None)
        self.renumber_series()

    def add_empty_book(self):

        def create_empty_book(authors):
            mi = Metadata(_('Unknown'), dlg.selected_authors)
            for key in self.series_columns.keys():
                meta = self.db.metadata_for_field(key)
                mi.set_user_metadata(key, meta)
                mi.set(key, val=None, extra=None)
            return SeriesBook(mi, self.series_columns)

        idx = self.series_table.currentRow()
        if idx == -1:
            author = None
        else:
            author = self.books[idx].authors()[0]

        dlg = AddEmptyBookDialog(self, self.db, author)
        if dlg.exec_() != dlg.Accepted:
            return
        num = dlg.qty_to_add
        for _x in range(num):
            idx += 1
            book = create_empty_book(dlg.selected_authors)
            self.books.insert(idx, book)
        self.series_table.setRowCount(len(self.books))
        self.renumber_series()

    def remove_book(self):
        if not question_dialog(self, _('Are you sure?'), '<p>'+
                _('Remove the selected book(s) from the series list?'), show_copy_button=False):
            return
        rows = self.series_table.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        first_sel_row = self.series_table.currentRow()
        for row in reversed(selrows):
            self.books.pop(row)
            self.series_table.removeRow(row)
        if first_sel_row < self.series_table.rowCount():
            self.series_table.select_and_scroll_to_row(first_sel_row)
        elif self.series_table.rowCount() > 0:
            self.series_table.select_and_scroll_to_row(first_sel_row - 1)
        self.renumber_series()

    def move_rows_up(self):
        self.series_table.setFocus()
        rows = self.series_table.selectionModel().selectedRows()
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
            self.series_table.swap_row_widgets(selrow - 1, selrow + 1)
            self.books[selrow-1], self.books[selrow] = self.books[selrow], self.books[selrow-1]

        scroll_to_row = first_sel_row - 1
        if scroll_to_row > 0:
            scroll_to_row = scroll_to_row - 1
        self.series_table.scrollToItem(self.series_table.item(scroll_to_row, 0))
        self.renumber_series()

    def move_rows_down(self):
        self.series_table.setFocus()
        rows = self.series_table.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        last_sel_row = selrows[-1]
        if last_sel_row == self.series_table.rowCount() - 1:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        for selrow in reversed(selrows):
            self.series_table.swap_row_widgets(selrow + 2, selrow)
            self.books[selrow+1], self.books[selrow] = self.books[selrow], self.books[selrow+1]

        scroll_to_row = last_sel_row + 1
        if scroll_to_row < self.series_table.rowCount() - 1:
            scroll_to_row = scroll_to_row + 1
        self.series_table.scrollToItem(self.series_table.item(scroll_to_row, 0))
        self.renumber_series()

    def series_indent_change(self, delta):
        for row in self.series_table.selectionModel().selectedRows():
            book = self.books[row.row()]
            series_indent = book.series_indent()
            if delta > 0:
                if series_indent < 2:
                    book.set_series_indent(series_indent+1)
            else:
                if series_indent > 0:
                    book.set_series_indent(series_indent-1)
            book.set_assigned_index(None)
        self.renumber_series()

    def sort_by(self, name):
        if name == 'PubDate':
            self.books = sorted(self.books, key=lambda k: k.sort_key(sort_by_pubdate=True))
        elif name == 'Original Series Name':
            self.books = sorted(self.books, key=lambda k: k.sort_key(sort_by_name=True))
        else:
            self.books = sorted(self.books, key=lambda k: k.sort_key())
        self.renumber_series()

    def search_web(self, name):
        URLS =  {
                'FantasticFiction': 'http://www.fantasticfiction.co.uk/search/?searchfor=author&keywords={author}',
                'Goodreads': 'http://www.goodreads.com/search/search?q={author}&search_type=books',
                'Google': 'http://www.google.com/#sclient=psy&q=%22{author}%22+%22{title}%22',
                'Wikipedia': 'http://en.wikipedia.org/w/index.php?title=Special%3ASearch&search={author}'
                }
        for row in self.series_table.selectionModel().selectedRows():
            book = self.books[row.row()]
            safe_title = self.convert_to_search_text(book.title())
            safe_author = self.convert_author_to_search_text(book.authors()[0])
            url = URLS[name].replace('{title}', safe_title).replace('{author}', safe_author)
            if not isinstance(url, bytes):
                url = url.encode('utf-8')
            open_url(QUrl.fromEncoded(url))

    def convert_to_search_text(self, text, encoding='utf-8'):
        # First we strip characters we will definitely not want to pass through.
        # Periods from author initials etc do not need to be supplied
        text = text.replace('.', '')
        # Now encode the text using Python function with chosen encoding
        text = quote_plus(text.encode(encoding, 'ignore'))
        # If we ended up with double spaces as plus signs (++) replace them
        text = text.replace('++','+')
        return text

    def convert_author_to_search_text(self, author, encoding='utf-8'):
        # We want to convert the author name to FN LN format if it is stored LN, FN
        # We do this because some websites (Kobo) have crappy search engines that
        # will not match Adams+Douglas but will match Douglas+Adams
        # Not really sure of the best way of determining if the user is using LN, FN
        # Approach will be to check the tweak and see if a comma is in the name

        # Comma separated author will be pipe delimited in Calibre database
        fn_ln_author = author
        if author.find(',') > -1:
            # This might be because of a FN LN,Jr - check the tweak
            sort_copy_method = tweaks['author_sort_copy_method']
            if sort_copy_method == 'invert':
                # Calibre default. Hence "probably" using FN LN format.
                fn_ln_author = author
            else:
                # We will assume that we need to switch the names from LN,FN to FN LN
                parts = author.split(',')
                surname = parts.pop(0)
                parts.append(surname)
                fn_ln_author = ' '.join(parts).strip()
        return self.convert_to_search_text(fn_ln_author, encoding)

    def cell_changed(self, row, column):
        book = self.books[row]
        if column == 0:
            book.set_title(unicode(self.series_table.item(row, column).text()).strip())
        elif column == 2:
            qtdate = self.series_table.item(row, column).data(Qt.DisplayRole)
            book.set_pubdate(qt_to_dt(qtdate, as_utc=False))

    def item_selection_changed(self):
        row = self.series_table.currentRow()
        if row == -1:
            return
        has_assigned_index = False
        for row in self.series_table.selectionModel().selectedRows():
            book = self.books[row.row()]
            if book.assigned_index():
                has_assigned_index = True
        self.series_table.clear_index_action.setEnabled(has_assigned_index)
        if not has_assigned_index:
            for book in self.books:
                if book.assigned_index():
                    has_assigned_index = True
        self.series_table.clear_all_index_action.setEnabled(has_assigned_index)
