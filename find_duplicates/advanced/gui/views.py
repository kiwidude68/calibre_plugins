#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~

__license__ = 'GPL v3'
__copyright__ = '2021, Ahmed Zaki <azaki00.dev@gmail.com>'

from collections import OrderedDict
from functools import partial
import itertools, operator
import copy

try:
    from qt.core import (Qt, QTableView, QAbstractItemView, QModelIndex,
                            QItemSelection, QMenu, QDialog)
except ImportError:
    from PyQt5.Qt import (Qt, QTableView, QAbstractItemView, QModelIndex,
                            QItemSelection, QMenu, QDialog)

from calibre.gui2 import question_dialog, error_dialog

from calibre_plugins.find_duplicates.advanced.gui.delegates import ButtonDelegate, TreeComboDelegate
from calibre_plugins.find_duplicates.advanced.gui.models import UP, DOWN
from calibre_plugins.find_duplicates.advanced.gui import SettingsWidgetDialog
from calibre_plugins.find_duplicates.common_dialogs import ViewLogDialog

try:
    load_translations()
except NameError:
    pass

class TableView(QTableView):

    def __init__(self, parent):
        QTableView.__init__(self, parent)
        self.setSortingEnabled(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setMouseTracking(True)
        self.verticalHeader().setDefaultSectionSize(30)
        self.verticalHeader().setVisible(True)
        self.verticalHeader().setSectionsMovable(True)
        self.horizontalHeader().setSectionsMovable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.horizontalHeader().setStretchLastSection(True)
        self.column_header = self.horizontalHeader()

    def _set_minimum_column_width(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def set_current_row(self, row=0, select=True, for_sync=False):
        if row > -1 and row < self.model().rowCount(QModelIndex()):
            h = self.horizontalHeader()
            logical_indices = list(range(h.count()))
            logical_indices = [x for x in logical_indices if not
                    h.isSectionHidden(x)]
            pairs = [(x, h.visualIndex(x)) for x in logical_indices if
                    h.visualIndex(x) > -1]
            if not pairs:
                pairs = [(0, 0)]
            pairs.sort(key=lambda x: x[1])
            i = pairs[0][0]
            index = self.model().index(row, i)
            if for_sync:
                sm = self.selectionModel()
                sm.setCurrentIndex(index, sm.NoUpdate)
            else:
                self.setCurrentIndex(index)
                if select:
                    sm = self.selectionModel()
                    sm.select(index, sm.SelectionFlag.ClearAndSelect|sm.Rows)

    def select_rows(self, rows, change_current=True, scroll=True):
        rows = {x.row() if hasattr(x, 'row') else x for x in
            rows}
        rows = list(sorted(rows))
        if rows:
            row = rows[0]
            if change_current:
                self.set_current_row(row, select=False)
            if scroll:
                self.scroll_to_row(row)
        sm = self.selectionModel()
        sel = QItemSelection()
        m = self.model()
        max_col = m.columnCount(QModelIndex()) - 1
        # Create a range based selector for each set of contiguous rows
        # as supplying selectors for each individual row causes very poor
        # performance if a large number of rows has to be selected.
        for k, g in itertools.groupby(enumerate(rows), lambda i_x:i_x[0]-i_x[1]):
            group = list(map(operator.itemgetter(1), g))
            sel.merge(QItemSelection(m.index(min(group), 0),
                m.index(max(group), max_col)), sm.SelectionFlag.Select)
        sm.select(sel, sm.SelectionFlag.ClearAndSelect)
        return rows

    def scroll_to_row(self, row):
        if row > -1:
            h = self.horizontalHeader()
            for i in range(h.count()):
                if not h.isSectionHidden(i) and h.sectionViewportPosition(i) >= 0:
                    self.scrollTo(self.model().index(row, i), self.PositionAtCenter)
                    break

    def add_row(self):
        self.setFocus()
        # We will insert a blank row below the currently selected row
        row = self.selectionModel().currentIndex().row() + 1
        self.model().insertRow(row)
        self.scroll_to_row(row)

    def delete_rows(self):
        self.setFocus()
        selrows = self.selectionModel().selectedRows()
        selrows = sorted(selrows, key=lambda x: x.row())
        if len(selrows) == 0:
            return
        message = _('Are you sure you want to delete this action?')
        if len(selrows) > 1:
            message = _('Are you sure you want to delete the selected %d actions?')%len(selrows)
        if not question_dialog(self, _('Are you sure?'), '<p>'+message, show_copy_button=False):
            return
        first_sel_row = selrows[0].row()
        for selrow in reversed(selrows):
            self.model().removeRow(selrow.row())
        if first_sel_row < self.model().rowCount(QModelIndex()):
            self.setCurrentIndex(self.model().index(first_sel_row, 0))
            self.scroll_to_row(first_sel_row)
        elif self.model().rowCount(QModelIndex()) > 0:
            self.setCurrentIndex(self.model().index(first_sel_row - 1, 0))
            self.scroll_to_row(first_sel_row - 1)

    def move_rows(self, direction=DOWN):
        self.setFocus()
        sm = self.selectionModel()
        selrows = sm.selectedRows()
        if len(selrows) == 0:
            return
        m = self.model()
        # make sure there is room to move UP/DOWN
        if direction == DOWN:
            boundary_selrow = selrows[-1].row()
            if boundary_selrow >= m.rowCount(QModelIndex()) - 1:
                return
        elif direction == UP:
            boundary_selrow = selrows[0].row()
            if boundary_selrow <= 0:
                return
        
        rows = [row.row() for row in selrows]
        m.move_rows(rows, direction=direction)
        
        # reset selections and scroll
        rows = [row+direction for row in rows]
        scroll_to_row = boundary_selrow + direction
        self.select_rows(rows)
        self.scroll_to_row(scroll_to_row)

    def show_column_header_context_menu(self, pos):
        model = self.model()
        idx = self.column_header.logicalIndexAt(pos)
        col = None
        if idx > -1 and idx < len(model.col_map):
            col = model.col_map[idx]
            name = str(model.headerData(idx, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) or '')
            self.column_header_context_menu = self.create_header_context_menu(col, name)
            self.column_header_context_menu.popup(self.column_header.mapToGlobal(pos))

    def create_header_context_menu(self, col, name):
        ans = QMenu(self)
        model = self.model()
        handler = partial(self.column_header_context_handler, column=col)
        if col in model.optional_cols:
            ans.addAction(_('Hide column %s') % name, partial(handler, action='hide'))

        hidden_cols = {model.col_map[i]: i for i in range(self.column_header.count())
                       if self.column_header.isSectionHidden(i)}

        hidden_cols = {k:v for k,v in hidden_cols.items() if k in model.optional_cols}

        ans.addSeparator()
        if hidden_cols:
            m = ans.addMenu(_('Show column'))
            hcols = [(hcol, str(self.model().headerData(hidx, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) or ''))
                     for hcol, hidx in hidden_cols.items()]
            hcols.sort()
            for hcol, hname in hcols:
                m.addAction(hname, partial(handler, action='show', column=hcol))
        return ans


    def column_header_context_handler(self, action=None, column=None):
        if not action or not column:
            return
        try:
            idx = self.col_map.index(column)
        except:
            return
        h = self.column_header

        if action == 'hide':
            if h.hiddenSectionCount() >= h.count():
                return error_dialog(self, _('Cannot hide all columns'), _(
                    'You must not hide all columns'), show=True)
            h.setSectionHidden(idx, True)
        elif action == 'show':
            h.setSectionHidden(idx, False)
            if h.sectionSize(idx) < 3:
                sz = h.sectionSizeHint(idx)
                h.resizeSection(idx, sz)

    def get_state(self):
        h = self.column_header
        cm = self.model().col_map
        state = {}
        state['hidden_columns'] = [cm[i] for i in range(h.count())
                if h.isSectionHidden(i)]
        state['column_positions'] = {}
        state['column_sizes'] = {}
        for i in range(h.count()):
            name = cm[i]
            state['column_positions'][name] = h.visualIndex(i)
            state['column_sizes'][name] = h.sectionSize(i)
        return state

    def apply_state(self, state):
        h = self.column_header
        cmap = {}
        hidden = state.get('hidden_columns', [])
        for i, c in enumerate(self.model().col_map):
            cmap[c] = i
            h.setSectionHidden(i, c in hidden)

        positions = state.get('column_positions', {})
        pmap = {}
        for col, pos in positions.items():
            if col in cmap:
                pmap[pos] = col
        for pos in sorted(pmap.keys()):
            col = pmap[pos]
            idx = cmap[col]
            current_pos = h.visualIndex(idx)
            if current_pos != pos:
                h.moveSection(current_pos, pos)

        sizes = state.get('column_sizes', {})
        for col, size in sizes.items():
            if col in cmap:
                sz = sizes[col]
                if sz < 3:
                    sz = h.sectionSizeHint(cmap[col])
                h.resizeSection(cmap[col], sz)

        for i in range(h.count()):
            if not h.isSectionHidden(i) and h.sectionSize(i) < 3:
                sz = h.sectionSizeHint(i)
                h.resizeSection(i, sz)


class AlgorithmsTable(TableView):

    def __init__(self, parent, gui, algorithms):
        TableView.__init__(self, parent)
        self.gui = gui
        self.algorithms = algorithms
        self.doubleClicked.connect(self._on_double_clicked)
        self.column_header.setSectionsClickable(True)
        self.column_header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.column_header.customContextMenuRequested.connect(partial(self.show_column_header_context_menu))

    def set_model(self, _model):
        self.setModel(_model)
        self.col_map = _model.col_map

        # Hide columns
        for col_name in _model.hidden_cols:
            col = self.col_map.index(col_name)
            self.setColumnHidden(col, True)

        self.algorithms_delegate = TreeComboDelegate(self, self.algorithm_tree())
        self.setItemDelegateForColumn(self.col_map.index('name'), self.algorithms_delegate)

        self.button_delegate = ButtonDelegate(self)
        self.setItemDelegateForColumn(self.col_map.index('settings'), self.button_delegate)
        self.button_delegate.clicked.connect(self._on_button_clicked)

        self.resizeColumnsToContents()
        # Make sure every other column has a minimum width
        for col_name, width in _model.col_min_width.items():
            col = self.col_map.index(col_name)
            self._set_minimum_column_width(col, width)

    def algorithm_tree(self):
        '''
        Build dictionary containing algorithm tree where:
        1. Builtin algorithms are top level nodes
        2. User Algorithms are inside a node called User Algorithms
        This is a dictionary of nested dictionaries. Even algorithms
        are nested dictionaries in the form of 'algorithm_name': {}
        '''
        for name, algorithm in self.algorithms.items():
            if getattr(algorithm, 'is_user_algorithm', False):
                setattr(algorithm, '_display_tree', ['User Algorithms'] + getattr(algorithm, 'display_tree', []))

        d = OrderedDict()
        for name, algorithm in self.algorithms.items():
            parent = d
            tree_path = getattr(algorithm, '_display_tree', []) + [name]
            for node in tree_path:
                if not parent.get(node):
                    parent[node] = {}
                parent = parent[node]
        return d            

    def copy_row(self):
        self.setFocus()
        m = self.model()
        sm = self.selectionModel()
        index = sm.currentIndex()
        new_row = copy.deepcopy(m.algorithms_config[index.row()])
        # We will insert the new row below the currently selected row
        m.algorithms_config.insert(index.row()+1, new_row)
        m.layoutChanged.emit()
        self.select_rows([index.row()+1])

    def _on_button_clicked(self, index):
        m = self.model()
        col_name = m.col_map[index.column()]
        if col_name == 'settings':
            algorithm_config = m.algorithms_config[index.row()]
            name = algorithm_config['name']
            if not name:
                # user clicking on setting before choosing algorithm
                error_dialog(
                    self,
                    _('No Algorithm Selected'),
                    _('You must choose an algorithm first'),
                    show=True
                )
                return
            algorithm = self.algorithms[name]
            settings = algorithm_config.get('settings')
            if not settings:
                settings = algorithm.default_settings()
            config_widget = algorithm.config_widget()
            if config_widget:
                name = 'FindDuplicates::{}'.format(name)
                title = '{}'.format(name)
                if issubclass(config_widget, QDialog):
                    # config_widget is a dialog
                    d = config_widget(self, self.gui, algorithm, name, title)
                else:
                    # config_widget is a qwidget
                    d = SettingsWidgetDialog(name, self, self.gui, config_widget, algorithm, title)
                # inject copy of algorithm_config into the settings dialog, for internal use only
                d._algorithm_config = copy.deepcopy(algorithm_config)
                if settings:
                    d.load_settings(settings)
                if d.exec_() == d.Accepted:
                    algorithm_config['settings'] = d.settings
                    # reset any previous error if present
                    algorithm_config['errors'] = ''
                    m.dataChanged.emit(index, index)

    def _on_double_clicked(self, index):
        m = self.model()
        col_name = m.col_map[index.column()]
        if col_name == 'errors':
            algorithm_config = m.algorithms_config[index.row()]
            details = algorithm_config.get('errors', '')
            self._view_error_details(details)
            

    def _view_error_details(self, details):
        ViewLogDialog(_('Errors details'), details, self)
