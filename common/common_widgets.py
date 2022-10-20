#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2022, Grant Drake'

from six import text_type as unicode

try:
    from qt.core import (Qt, QTableWidgetItem, QComboBox, QHBoxLayout, QLabel, QFont, 
                        QDateTime, QStyledItemDelegate, QLineEdit)
except ImportError:
    from PyQt5.Qt import (Qt, QTableWidgetItem, QComboBox, QHBoxLayout, QLabel, QFont, 
                        QDateTime, QStyledItemDelegate, QLineEdit)

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.gui2 import error_dialog, UNDEFINED_QDATETIME
from calibre.utils.date import now, format_date, UNDEFINED_DATE

from common_icons import get_pixmap

# get_date_format
#
# CheckableTableWidgetItem
# DateDelegate
# DateTableWidgetItem
# ImageTitleLayout
# ReadOnlyTableWidgetItem
# ReadOnlyTextIconWidgetItem
# ReadOnlyCheckableTableWidgetItem
# TextIconWidgetItem
#
# CustomColumnComboBox
# KeyValueComboBox
# NoWheelComboBox
# ReadOnlyLineEdit

# ----------------------------------------------
#               Functions
# ----------------------------------------------

def get_date_format(tweak_name='gui_timestamp_display_format', default_fmt='dd MMM yyyy'):
    from calibre.utils.config import tweaks
    format = tweaks[tweak_name]
    if format is None:
        format = default_fmt
    return format 

# ----------------------------------------------
#               Widgets
# ----------------------------------------------

class CheckableTableWidgetItem(QTableWidgetItem):
    '''
    For use in a table cell, displays a checkbox that can potentially be tristate
    '''
    def __init__(self, checked=False, is_tristate=False):
        super(CheckableTableWidgetItem, self).__init__('')
        try:
            self.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled )
        except:
            self.setFlags(Qt.ItemFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled ))
        if is_tristate:
            self.setFlags(self.flags() | Qt.ItemFlag.ItemIsUserTristate)
        if checked:
            self.setCheckState(Qt.Checked)
        else:
            if is_tristate and checked is None:
                self.setCheckState(Qt.PartiallyChecked)
            else:
                self.setCheckState(Qt.Unchecked)

    def get_boolean_value(self):
        '''
        Return a boolean value indicating whether checkbox is checked
        If this is a tristate checkbox, a partially checked value is returned as None
        '''
        if self.checkState() == Qt.PartiallyChecked:
            return None
        else:
            return self.checkState() == Qt.Checked

from calibre.gui2.library.delegates import DateDelegate as _DateDelegate
class DateDelegate(_DateDelegate):
    '''
    Delegate for dates. Because this delegate stores the
    format as an instance variable, a new instance must be created for each
    column. This differs from all the other delegates.
    '''
    def __init__(self, parent, fmt='dd MMM yyyy', default_to_today=True):
        super(DateDelegate, self).__init__(parent)
        self.default_to_today = default_to_today
        self.format = get_date_format(default_fmt=fmt)

    def createEditor(self, parent, option, index):
        qde = QStyledItemDelegate.createEditor(self, parent, option, index)
        qde.setDisplayFormat(self.format)
        qde.setMinimumDateTime(UNDEFINED_QDATETIME)
        qde.setSpecialValueText(_('Undefined'))
        qde.setCalendarPopup(True)
        return qde

    def setEditorData(self, editor, index):
        val = index.model().data(index, Qt.DisplayRole)
        if val is None or val == UNDEFINED_QDATETIME:
            if self.default_to_today:
                val = self.default_date
            else:
                val = UNDEFINED_QDATETIME
        editor.setDateTime(val)

    def setModelData(self, editor, model, index):
        val = editor.dateTime()
        if val <= UNDEFINED_QDATETIME:
            model.setData(index, UNDEFINED_QDATETIME, Qt.EditRole)
        else:
            model.setData(index, QDateTime(val), Qt.EditRole)


class DateTableWidgetItem(QTableWidgetItem):

    def __init__(self, date_read, is_read_only=False, default_to_today=False, fmt=None):
        if date_read is None or date_read == UNDEFINED_DATE and default_to_today:
            date_read = now()
        if is_read_only:
            super(DateTableWidgetItem, self).__init__(format_date(date_read, fmt))
            self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
            self.setData(Qt.DisplayRole, QDateTime(date_read))
        else:
            super(DateTableWidgetItem, self).__init__('')
            self.setData(Qt.DisplayRole, QDateTime(date_read))


class ImageTitleLayout(QHBoxLayout):
    '''
    A reusable layout widget displaying an image followed by a title
    '''
    def __init__(self, parent, icon_name, title):
        super(ImageTitleLayout, self).__init__()
        self.title_image_label = QLabel(parent)
        self.update_title_icon(icon_name)
        self.addWidget(self.title_image_label)

        title_font = QFont()
        title_font.setPointSize(16)
        shelf_label = QLabel(title, parent)
        shelf_label.setFont(title_font)
        self.addWidget(shelf_label)
        self.insertStretch(-1)

    def update_title_icon(self, icon_name):
        pixmap = get_pixmap(icon_name)
        if pixmap is None:
            error_dialog(self.parent(), _('Restart required'),
                         _('Title image not found - you must restart Calibre before using this plugin!'), show=True)
        else:
            self.title_image_label.setPixmap(pixmap)
        self.title_image_label.setMaximumSize(32, 32)
        self.title_image_label.setScaledContents(True)


class ReadOnlyTableWidgetItem(QTableWidgetItem):
    '''
    For use in a table cell, displays text the user cannot select or modify.
    '''
    def __init__(self, text):
        if text is None:
            text = ''
        super(ReadOnlyTableWidgetItem, self).__init__(text)
        self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)


class ReadOnlyTextIconWidgetItem(ReadOnlyTableWidgetItem):
    '''
    For use in a table cell, displays an icon the user cannot select or modify.
    '''
    def __init__(self, text, icon):
        super(ReadOnlyTextIconWidgetItem, self).__init__(text)
        if icon:
            self.setIcon(icon)

class ReadOnlyCheckableTableWidgetItem(ReadOnlyTableWidgetItem):
    '''
    For use in a table cell, displays a checkbox next to some text the user cannot select or modify.
    '''
    def __init__(self, text, checked=False, is_tristate=False):
        super(ReadOnlyCheckableTableWidgetItem, self).__init__(text)
        try: # For Qt Backwards compatibility.
            self.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled )
        except:
            self.setFlags(Qt.ItemFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled ))
        if is_tristate:
            self.setFlags(self.flags() | Qt.ItemIsTristate)
        if checked:
            self.setCheckState(Qt.Checked)
        else:
            if is_tristate and checked is None:
                self.setCheckState(Qt.PartiallyChecked)
            else:
                self.setCheckState(Qt.Unchecked)

    def get_boolean_value(self):
        '''
        Return a boolean value indicating whether checkbox is checked
        If this is a tristate checkbox, a partially checked value is returned as None
        '''
        if self.checkState() == Qt.PartiallyChecked:
            return None
        else:
            return self.checkState() == Qt.Checked


class TextIconWidgetItem(QTableWidgetItem):
    '''
    For use in a table cell, displays text with an icon next to it.
    '''
    def __init__(self, text, icon):
        super(TextIconWidgetItem, self).__init__(text)
        self.setIcon(icon)


# ----------------------------------------------
#               Controls
# ----------------------------------------------


class CustomColumnComboBox(QComboBox):
    CREATE_NEW_COLUMN_ITEM = _("Create new column")

    def __init__(self, parent, custom_columns={}, selected_column='', initial_items=[''], create_column_callback=None):
        super(CustomColumnComboBox, self).__init__(parent)
        self.create_column_callback = create_column_callback
        self.current_index = 0
        if create_column_callback is not None:
            self.currentTextChanged.connect(self.current_text_changed)
        self.populate_combo(custom_columns, selected_column, initial_items)

    def populate_combo(self, custom_columns, selected_column, initial_items=[''], show_lookup_name=True):
        self.clear()
        self.column_names = []
        selected_idx = 0

        if isinstance(initial_items, dict):
            for key in sorted(initial_items.keys()):
                self.column_names.append(key)
                display_name = initial_items[key]
                self.addItem(display_name)
                if key == selected_column:
                    selected_idx = len(self.column_names) - 1
        else:
            for display_name in initial_items:
                self.column_names.append(display_name)
                self.addItem(display_name)
                if display_name == selected_column:
                    selected_idx = len(self.column_names) - 1

        for key in sorted(custom_columns.keys()):
            self.column_names.append(key)
            display_name = '%s (%s)'%(key, custom_columns[key]['name']) if show_lookup_name else custom_columns[key]['name']
            self.addItem(display_name)
            if key == selected_column:
                selected_idx = len(self.column_names) - 1
        
        if self.create_column_callback is not None:
            self.addItem(self.CREATE_NEW_COLUMN_ITEM)
            self.column_names.append(self.CREATE_NEW_COLUMN_ITEM)

        self.setCurrentIndex(selected_idx)

    def get_selected_column(self):
        selected_column = self.column_names[self.currentIndex()]
        if selected_column == self.CREATE_NEW_COLUMN_ITEM:
            selected_column = None
        return selected_column
    
    def current_text_changed(self, new_text):
        if new_text == self.CREATE_NEW_COLUMN_ITEM:
            result = self.create_column_callback()
            if not result:
                self.setCurrentIndex(self.current_index)
        else:
            self.current_index = self.currentIndex()


class KeyValueComboBox(QComboBox):

    def __init__(self, parent, values, selected_key):
        QComboBox.__init__(self, parent)
        self.values = values
        self.populate_combo(selected_key)

    def populate_combo(self, selected_key):
        self.clear()
        selected_idx = idx = -1
        for key, value in self.values.items():
            idx = idx + 1
            self.addItem(value)
            if key == selected_key:
                selected_idx = idx
        self.setCurrentIndex(selected_idx)

    def selected_key(self):
        for key, value in self.values.items():
            if value == unicode(self.currentText()).strip():
                return key


class NoWheelComboBox(QComboBox):
    '''
    For combobox displayed in a table cell using the mouse wheel has nasty interactions
    due to the conflict between scrolling the table vs scrolling the combobox item.
    Inherit from this class to disable the combobox changing value with mouse wheel.
    '''
    def wheelEvent(self, event):
        event.ignore()


class ReadOnlyLineEdit(QLineEdit):

    def __init__(self, text, parent):
        if text is None:
            text = ''
        super(ReadOnlyLineEdit, self).__init__(text, parent)
        self.setEnabled(False)
