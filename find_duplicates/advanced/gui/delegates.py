#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~

__license__ = 'GPL v3'
__copyright__ = '2020, Ahmed Zaki <azaki00.dev@gmail.com>'

try:
    from qt.core import (QApplication, Qt, QComboBox, QIcon,
                        QStyledItemDelegate, QModelIndex, QEvent,
                        pyqtSignal, QStyle, QStyleOptionButton, QSize)
except ImportError:
    from PyQt5.Qt import (QApplication, Qt, QComboBox, QIcon,
                        QStyledItemDelegate, QModelIndex, QEvent,
                        pyqtSignal, QStyle, QStyleOptionButton, QSize)

from calibre_plugins.find_duplicates.common_icons import get_icon
from calibre_plugins.find_duplicates.advanced.gui import TreeComboBox


class ComboDelegate(QStyledItemDelegate):

    def __init__(self, parent, items_list):
        QStyledItemDelegate.__init__(self, parent)
        self.table_widget = parent
        self.longest_text = ''
        self.items_list = items_list

    def createEditor(self, parent, option, index):
        m = index.model()
        col_name = m.headers[index.column()]
        editor = QComboBox(parent)
        max_len = 0
        self.longest_text = ''
        for v in self.items_list:
            editor.addItem(v)
            if len(v) > max_len:
                self.longest_text = v
        return editor

    def setModelData(self, editor, model, index):
        val = str(editor.currentText())
        if not val:
            val = ''
        model.setData(index, val, Qt.EditRole)

    def setEditorData(self, editor, index):
        m = index.model()
        val = m.data(index, Qt.DisplayRole)
        idx = editor.findText(val)
        editor.setCurrentIndex(idx)


class ButtonDelegate(QStyledItemDelegate):

    clicked = pyqtSignal(QModelIndex)

    def __init__(self, parent):
        super(ButtonDelegate, self).__init__(parent)
        self._pressed = None
        self._hover = None

    def button_state(self, index):
        model = index.model()
        if hasattr(model, 'button_state'):
            return model.button_state(index)
        else:
            visible = True
            enabled = True
            return visible, enabled

    def paint(self, painter, option, index):
        state = QStyle.StateFlag.State_None
        m = index.model()
        visible, enabled = self.button_state(index)
        if not visible:
            super(ButtonDelegate, self).paint(painter, option, index)
            return
        if enabled:
            state |= QStyle.StateFlag.State_Enabled
        if self._pressed and self._pressed == (index.row(), index.column()):
            state |= QStyle.StateFlag.State_Sunken
        else:
            state |= QStyle.StateFlag.State_Raised
        if option.state & QStyle.StateFlag.State_MouseOver:
            state |= QStyle.StateFlag.State_MouseOver
        painter.save()
        opt = QStyleOptionButton()
        opt.text = ''
        # default iconsize is (-1,-1) so the icon is invisible, set to (16, 16)
        opt.iconSize = QSize(16,16)
        opt.icon = QIcon(get_icon('gear.png'))
        opt.rect = option.rect
        opt.palette = option.palette
        opt.state = state
        QApplication.style().drawControl(QStyle.ControlElement.CE_PushButton, opt, painter)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        visible, enabled = self.button_state(index)
        # ignore clicks on cells with absent or disabled buttons
        if not visible or not enabled:
            return super(ButtonDelegate, self).editorEvent(event, model, option, index)
        if event.type() == QEvent.MouseButtonPress:
            # store the position that is clicked
            self._pressed = (index.row(), index.column())
            return True
        elif event.type() == QEvent.MouseButtonRelease:
            if self._pressed == (index.row(), index.column()):
                # we are at the same place, so emit
                self.clicked.emit(index)
            elif self._pressed:
                # different place.
                # force a repaint on the pressed cell by emitting a dataChanged
                # Note: This is probably not the best idea
                # but I've yet to find a better solution.
                oldIndex = index.model().index(*self._pressed)
                self._pressed = None
                index.model().dataChanged.emit(oldIndex, oldIndex)
            self._pressed = None
            return True
        else:
            # for all other cases, default action will be fine
            return super(ButtonDelegate, self).editorEvent(event, model, option, index)


class TreeComboDelegate(QStyledItemDelegate):

    def __init__(self, parent, data):
        QStyledItemDelegate.__init__(self, parent)
        self.table_widget = parent
        self.data = data

    def createEditor(self, parent, option, index):
        editor = TreeComboBox(parent)
        editor.build_tree(self.data)
        return editor

    def setModelData(self, editor, model, index):
        val = str(editor.currentText())
        if not val:
            val = ''
        model.setData(index, val, Qt.EditRole)

    def setEditorData(self, editor, index):
        m = index.model()
        val = m.data(index, Qt.DisplayRole)
        matches = editor.tree_model.findItems(val, Qt.MatchRecursive)
        # exclude parent items as they are not actions
        matches = [ x for x in matches if x.isSelectable()]
        if len(matches) == 0:
            editor.setCurrentIndex(-1)
        else:
            item = matches[0]
            editor.selectIndex(item.index())

