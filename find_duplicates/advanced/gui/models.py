#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~

__license__ = 'GPL v3'
__copyright__ = '2020, Ahmed Zaki <azaki00.dev@gmail.com>'

try:
    from qt.core import Qt, QAbstractTableModel, QModelIndex, QIcon, QBrush
except ImportError:
    from PyQt5.Qt import Qt, QAbstractTableModel, QModelIndex, QIcon, QBrush

from calibre_plugins.find_duplicates.common_icons import get_icon

try:
    load_translations()
except NameError:
    pass

DOWN    = 1
UP      = -1

class AlgorithmsModel(QAbstractTableModel):

    def __init__(self, algorithms, algorithms_config):
        QAbstractTableModel.__init__(self)
        self.algorithms_config = algorithms_config
        self.algorithms = algorithms
        self.col_map = ['name','settings','comment','errors']
        self.editable_columns = ['name','comment']
        self.optional_cols = ['comment']
        self.hidden_cols = []
        self.col_min_width = {
            'name': 300,
            'settings': 50,
            'comment': 200,
            'errors': 250
        }
        all_headers = [('Algorithm'),_('Settings'),_('Comment'),_('Errors')]
        self.headers = all_headers

    def rowCount(self, parent):
        if parent and parent.isValid():
            return 0
        return len(self.algorithms_config)

    def columnCount(self, parent):
        if parent and parent.isValid():
            return 0
        return len(self.headers)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        elif role == Qt.DisplayRole and orientation == Qt.Vertical:
            return section + 1
        return None

    def data(self, index, role):
        if not index.isValid():
            return None;
        row, col = index.row(), index.column()
        if row < 0 or row >= len(self.algorithms_config):
            return None
        algorithm_config = self.algorithms_config[row]
        col_name = self.col_map[col]
        value = algorithm_config.get(col_name, '')
        error = algorithm_config.get('errors', '')
        
        if role in [Qt.DisplayRole, Qt.UserRole, Qt.EditRole]:
            if col_name in ['settings']:
                pass
            elif col_name == 'errors':
                if error:
                    return _('Validation Error. Double click for details')
            else:
                return value

        elif role == Qt.DecorationRole:
            if col_name == 'errors':
                if error:
                    return QIcon(get_icon('dialog_error.png'))
                
        elif role == Qt.ToolTipRole:
            if col_name == 'errors':
                if error:
                    return error

            elif col_name == 'comment':
                tooltip = algorithm_config.get('comment', '')
                return tooltip
                        
            elif col_name == 'name':
                tooltip = algorithm_config.get('description', '')
                return tooltip

        elif role == Qt.ForegroundRole:
            color = None
            if error:
                color = Qt.red
            if color is not None:
                return QBrush(color)

        return None

    def setData(self, index, value, role):
        done = False

        row, col = index.row(), index.column()
        algorithm_config = self.algorithms_config[row]
        val = str(value).strip()
        col_name = self.col_map[col]
        
        if role == Qt.EditRole:
            if col_name == 'name':
                old_name = algorithm_config.get('name', '')
                algorithm_config['name'] = val
                if val != old_name:
                    # reset settings as they are not valid for this new algorithm
                    algorithm_config['settings'] = {}
                    # reset any previous errors
                    algorithm_config['errors'] = ''
            elif col_name == 'settings':
                pass
            elif col_name in ['comment']:
                algorithm_config[col_name] = val
            done = True
            
        return done

    def flags(self, index):
        flags = QAbstractTableModel.flags(self, index)
        if index.isValid():
            algorithm_config = self.algorithms_config[index.row()]
            col_name = self.col_map[index.column()]
            if col_name in self.editable_columns:
                flags |= Qt.ItemIsEditable
        return flags

    def button_state(self, index):
        visible = False
        enabled = False
        row, col = index.row(), index.column()
        algorithm_config = self.algorithms_config[row]
        name = algorithm_config.get('name')
        if name:
            visible = True
            algorithm = self.algorithms.get(name)
            config_widget = None
            if algorithm:
                config_widget = algorithm.config_widget()
            if config_widget:
                enabled = True
        return visible, enabled
        

    def insertRows(self, row, count, idx):
        self.beginInsertRows(QModelIndex(), row, row + count - 1)
        for i in range(0, count):
            algorithm_config = {}
            algorithm_config['name'] = ''
            algorithm_config['settings'] = {}
            algorithm_config['comment'] = ''
            self.algorithms_config.insert(row + i, algorithm_config)
        self.endInsertRows()
        return True

    def removeRows(self, row, count, idx):
        self.beginRemoveRows(QModelIndex(), row, row + count - 1)
        for i in range(0, count):
            self.algorithms_config.pop(row + i)
        self.endRemoveRows()
        return True

    def move_rows(self, rows, direction=DOWN):
        srows = sorted(rows, reverse=direction == DOWN)
        for row in srows:
            pop = self.algorithms_config.pop(row)
            self.algorithms_config.insert(row+direction, pop)
        self.layoutChanged.emit()

    def validate_algorithm(self, row, algorithm_config):
        col = self.col_map.index('errors')
        name = algorithm_config['name']
        if name in self.algorithms.keys():
            algorithm = self.algorithms[name]
            settings = algorithm_config.get('settings')
            if not settings:
                settings = algorithm.default_settings()
            is_algorithm_valid = algorithm.validate(settings)
            if is_algorithm_valid is not True:
                msg, details = is_algorithm_valid
                algorithm_config['errors'] = details
                index = self.index(row, col, QModelIndex())
                self.dataChanged.emit(index, index)
                return is_algorithm_valid
        else:
            details = _('Algorithm ({}) is not currently available').format(name)
            algorithm_config['errors'] = details
            index = self.index(row, col, QModelIndex())
            self.dataChanged.emit(index, index)
            return (_('Algorithm unavailable'), details)
        return True

    def validate(self):
        all_algorithms_valid = True
        for row, algorithm_config in enumerate(self.algorithms_config):
            is_algorithm_valid = self.validate_algorithm(row, algorithm_config)
            if is_algorithm_valid is not True:
                all_algorithms_valid = False
        return all_algorithms_valid
