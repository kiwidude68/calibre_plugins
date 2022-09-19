#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~

__license__ = 'GPL v3'
__copyright__ = '2020, Ahmed Zaki <azaki00.dev@gmail.com>'


try:
    from qt.core import (QGridLayout, QLabel, QDialogButtonBox, QPlainTextEdit, QCheckBox,
                        QWidget, QPainter, QSize, QSizePolicy)
except ImportError:
    from PyQt5.Qt import (QGridLayout, QLabel, QDialogButtonBox, QPlainTextEdit, QCheckBox,
                        QWidget, QPainter, QSize, QSizePolicy)

try:
    qSizePolicy_Fixed = QSizePolicy.Policy.Fixed
except:
    qSizePolicy_Fixed = QSizePolicy.Fixed

import copy

from calibre.gui2.dialogs.message_box import MessageBox

TEMPLATE_PREFIX = 'TEMPLATE: '
TEMPLATE_ERROR = 'FD template error'

def truncate(string, length=22):
    return (string[:length] + '...') if len(string) > length else string

def to_list(string, sep=','):
    if string:
        return [a.strip().replace('|',',') for a in string.split(sep)]
    return []

STANDARD_FIELD_KEYS = [
    'title',
    'authors',
    'tags',
    'series',
    'languages',
    'publisher',
    'pubdate',
    'rating',
    'timestamp',
    'formats'
]

def get_cols(db):
    custom_fields = sorted([k for k,v in db.field_metadata.custom_field_metadata().items() if v['datatype'] not in ['comments']])
    return STANDARD_FIELD_KEYS + custom_fields

def column_metadata(db, column):
    fm = copy.deepcopy(db.field_metadata.all_metadata())
    meta = fm[column]
    if column == 'publisher':
        meta['icon_name'] = 'publisher.png'
        meta['delegate'] = 'publisher'
        meta['soundex_length'] = 6
    elif meta['datatype'] == 'series':
        meta['icon_name'] = 'series.png'
        meta['delegate'] = 'series'
        meta['soundex_length'] = 6
    elif meta['is_multiple'] != {}:
        if column == 'authors' or meta['display'].get('is_names'):
            meta['icon_name'] = 'user_profile.png'
            meta['delegate'] = 'authors'
            meta['soundex_length'] = 8
        else:
            meta['icon_name'] = 'tags.png'
            meta['delegate'] = 'tags'
            meta['soundex_length'] = 4
    else:
        meta['icon_name'] = 'column.png'
        meta['delegate'] = 'title'
        meta['soundex_length'] = 6
    return meta

def get_field_value(book_id, db, field_name, mi):
    if field_name.startswith('identifier:'):
        identifier_type = field_name.split(':')[-1]
        identifiers = db.get_identifiers(book_id, index_is_id=True)
        field_value = identifiers.get(identifier_type)
    else:
        field_value = db.new_api.field_for(field_name, book_id)

    return field_value

def composite_to_list(field_name, field_value, mi, composite_has_names):

    #{ composite fields with multiple items are currently returned as string, convert to list with items
    if mi.metadata_for_field(field_name)['datatype'] == 'composite':
        # test first, maybe it will change in future calibre releases
        if isinstance(field_value, str):
            if composite_has_names:
                SEP = '&'
            else:
                SEP = mi.metadata_for_field(field_name)['is_multiple']['list_to_ui']
            field_value = to_list(field_value, sep=SEP)
    #}
    return field_value


class Icon(QWidget):

    def __init__(self, parent=None, size=None):
        QWidget.__init__(self, parent)
        self.pixmap = None
        self.setSizePolicy(qSizePolicy_Fixed, qSizePolicy_Fixed)
        self.size = size or 64

    def set_icon(self, qicon):
        self.pixmap = qicon.pixmap(self.size, self.size)
        self.update()

    def sizeHint(self):
        return QSize(self.size, self.size)

    def paintEvent(self, ev):
        if self.pixmap is not None:
            x = (self.width() - self.size) // 2
            y = (self.height() - self.size) // 2
            p = QPainter(self)
            p.drawPixmap(x, y, self.size, self.size, self.pixmap)

class MessageBox2(MessageBox):
    def setup_ui(self):
        self.setObjectName("Dialog")
        self.resize(497, 235)
        self.gridLayout = l = QGridLayout(self)
        l.setObjectName("gridLayout")
        self.icon_widget = Icon(self)
        l.addWidget(self.icon_widget)
        self.msg = la = QLabel(self)
        la.setWordWrap(True), la.setMinimumWidth(400)
        la.setOpenExternalLinks(True)
        la.setObjectName("msg")
        l.addWidget(la, 0, 1, 1, 1)
        self.det_msg = dm = QPlainTextEdit(self)
        dm.setReadOnly(True)
        dm.setObjectName("det_msg")
        l.addWidget(dm, 1, 0, 1, 2)
        self.bb = bb = QDialogButtonBox(self)
        bb.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.setObjectName("bb")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        l.addWidget(bb, 3, 0, 1, 2)
        self.toggle_checkbox = tc = QCheckBox(self)
        tc.setObjectName("toggle_checkbox")
        l.addWidget(tc, 2, 0, 1, 2)

def confirm_with_details(parent, title, msg, det_msg='',
        show_copy_button=True):
    d = MessageBox2(MessageBox.INFO, title, msg, det_msg, parent=parent,
                    show_copy_button=show_copy_button)

    return d.exec_() == d.Accepted
