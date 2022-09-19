#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~

__license__ = 'GPL v3'
__copyright__ = '2020, Ahmed Zaki <azaki00.dev@gmail.com>'

try:
    from qt.core import (QVBoxLayout, QComboBox,
                        QTreeView, QStandardItem, QStandardItemModel,
                        QFrame, QModelIndex, QEvent, QDialogButtonBox)
except ImportError:
    from PyQt5.Qt import (QVBoxLayout, QComboBox,
                        QTreeView, QStandardItem, QStandardItemModel,
                        QFrame, QModelIndex, QEvent, QDialogButtonBox)

from calibre.gui2 import error_dialog

from calibre_plugins.find_duplicates.common_dialogs import SizePersistedDialog

try:
    load_translations()
except NameError:
    pass

class SettingsWidgetDialog(SizePersistedDialog):

    def __init__(self, name, parent, gui, widget_cls, algorithm, title=_('Settings')):
        self.gui = gui
        self.widget_cls = widget_cls
        self.algorithm = algorithm
        SizePersistedDialog.__init__(self, parent, name)
        self.setup_ui()
        self.setWindowTitle(title)
        self.resize_dialog()

    def setup_ui(self):
        self.widget = self.widget_cls(self.gui)
        l = QVBoxLayout()
        self.setLayout(l)
        l.addWidget(self.widget)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        l.addWidget(self.button_box)

    def load_settings(self, settings):
        self.widget.load_settings(settings)

    def save_settings(self):
        return self.widget.save_settings()

    def validate(self, settings):
        if hasattr(self.widget, 'validate'):
            return self.widget.validate(settings)
        else:
            return self.algorithm.validate(settings)
    
    def accept(self):
        self.settings = self.save_settings()
        # Validate settings
        is_valid = self.validate(self.settings)
        if is_valid is not True:
            msg, details = is_valid
            error_dialog(self, msg, details, show=True)
            return
        SizePersistedDialog.accept(self)


class TreeComboBox(QComboBox):
    def __init__(self, *args):
        super().__init__(*args)

        self.__skip_next_hide = False

        self.tree_view = tree_view = QTreeView(self)
        tree_view.setFrameShape(QFrame.NoFrame)
        tree_view.setEditTriggers(tree_view.NoEditTriggers)
        tree_view.setAlternatingRowColors(True)
        tree_view.setSelectionBehavior(tree_view.SelectRows)
        tree_view.setWordWrap(True)
        tree_view.setAllColumnsShowFocus(True)
        tree_view.setHeaderHidden(True)
        self.setView(tree_view)

        self.view().viewport().installEventFilter(self)

    def build_tree(self, data):
        
        self.tree_model = tree_model = QStandardItemModel()
        root_node = tree_model.invisibleRootItem()

        self.setModel(tree_model)

        self.populate_items(data, root_node, 1)

    def populate_items(self, data, parent_node, level, parent_non_selectable=True):
        for k, v in data.items():
            node = QStandardItem(k)
            parent_node.appendRow([node])
            if v:
                if parent_non_selectable:
                    node.setSelectable(False)
                self.populate_items(v, node, level+1)

    def showPopup(self):
        self.setRootModelIndex(QModelIndex())
        super().showPopup()

    def hidePopup(self):
        self.setRootModelIndex(self.view().currentIndex().parent())
        self.setCurrentIndex(self.view().currentIndex().row())
        if self.__skip_next_hide:
            self.__skip_next_hide = False
        else:
            super().hidePopup()

    def selectIndex(self, index):
        self.setRootModelIndex(index.parent())
        self.setCurrentIndex(index.row())

    def eventFilter(self, object, event):
        if event.type() == QEvent.MouseButtonPress and object is self.view().viewport():
            index = self.view().indexAt(event.pos())
            self.__skip_next_hide = not self.view().visualRect(index).contains(event.pos())
        return False
