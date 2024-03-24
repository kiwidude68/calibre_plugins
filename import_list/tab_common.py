from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import re, datetime

try:
    from qt.core import (Qt, QTextEdit, QComboBox, QLineEdit, QVBoxLayout,
                        QListWidget, QListWidgetItem, QAbstractItemView,
                        QDialogButtonBox, QGroupBox, QRadioButton, QHBoxLayout)
except ImportError:                        
    from PyQt5.Qt import (Qt, QTextEdit, QComboBox, QLineEdit, QVBoxLayout,
                        QListWidget, QListWidgetItem, QAbstractItemView,
                        QDialogButtonBox, QGroupBox, QRadioButton, QHBoxLayout)

from calibre.gui2 import error_dialog
from calibre.gui2.dnd import dnd_get_files
from calibre.utils.formatter import EvalFormatter

from calibre_plugins.import_list.algorithms import get_title_tokens
from calibre_plugins.import_list.common_compatibility import qTextEdit_NoWrap, qtDropActionCopyAction, qtDropActionMoveAction
from calibre_plugins.import_list.common_dialogs import SizePersistedDialog
from calibre_plugins.import_list.page_common import AUTHOR_SEPARATOR

try:
    load_translations()
except NameError:
    pass

DEFAULT_STRIP_PATTERNS = [('[...] or (...)', r'[\[\(].*[\]\)]'),
                         ('[...]', r'\[.*\]'),
                         ('(...)', r'\(.*\)')]

ICON_SIZE = 24


template_formatter = EvalFormatter()
def get_templated_url(tokenised_url):
    d = {'date':datetime.date.today().isoformat()}
    url = template_formatter.safe_format(tokenised_url, d, 'Template error', None)
    return url

def tidy_title(title_text, regex=None, regex_is_strip=True):
    if regex is not None:
        if regex_is_strip:
            title_text = regex.sub('', title_text)
        else:
            match = regex.search(title_text)
            if match:
                title_text = match.group(1)
            else:
                return ''
    # When scraping from web in particular, remove newlines and extra space
    title_text = re.sub(r'\s+', ' ', title_text).strip()
    # Remove some characters which aren't generally in real title names
    title_text = re.sub(r'[\*"“”]', '', title_text)
    # Remove a trailing " by" since is more frequently a "Title by Author" usage
    # If a book genuinely ends with that word, hopefully it is capitalised as " By"
    if title_text.endswith(' by'):
        title_text = title_text[:-3].strip()
    # If the text starts with a leading number indicating a position, strip that too.
    title_text = re.sub(r'^(\d+\.)', '', title_text)
    # Remove trailing periods or commas.
    while title_text and title_text[-1:] in (',', '.'):
        title_text = title_text[:-1]
    # Remove leading periods or commas.
    while title_text and title_text[:1] in (',', '.'):
        title_text = title_text[1:]
    return title_text.strip()

def tidy_author(author_text, regex=None, regex_is_strip=True):
    from calibre.ebooks.metadata import string_to_authors, authors_to_string
    if regex is not None:
        if regex_is_strip:
            author_text = regex.sub('', author_text)
        else:
            match = regex.search(author_text)
            if match:
                author_text = match.group(1)
            else:
                return ''
#     print("tidy_author: before - author_text='%s'" % author_text)
    # When scraping from web in particular, remove newlines and extra space
    author_text = re.sub(r'\s+', ' ', author_text).strip()
    # If it starts with a leading comma strip that.
    if author_text.startswith(','):
        author_text = author_text[1:].strip()
    # Remove a starting "by " or "By " since highly unlikely to be author name!
    if author_text.lower().startswith('by '):
        author_text = author_text[3:].strip()
    # If the text starts with a leading number indicating a position, strip that too.
    author_text = re.sub(r'^(\d+\.)', '', author_text)
    # If any semi-colons, treat them as a multiple author separator
    if ';' in author_text:
        authors = [a.strip() for a in author_text.split(';')]
        author_text = AUTHOR_SEPARATOR.join(authors)
    author_text = authors_to_string(string_to_authors(author_text))
#     print("tidy_author: after - author_text='%s'" % author_text)
    return author_text.strip()

def tidy_pubdate(pubdate_text, regex=None, regex_is_strip=True):
    if regex is not None:
        if regex_is_strip:
            pubdate_text = regex.sub('', pubdate_text)
        else:
            match = regex.search(pubdate_text)
            if match:
                pubdate_text = match.group(1)
            else:
                return ''
    pubdate_text = pubdate_text.replace('(', '').replace(')', '').strip()
    return pubdate_text

def tidy_field(text, regex=None, regex_is_strip=True):
    if regex is not None:
        if regex_is_strip:
            text = regex.sub('', text)
        else:
            match = regex.search(text)
            if match:
                text = match.group(1)
            else:
                return ''
    if text is None:
        return ''
    return text.strip()

def tidy(field_name, text, regex=None, regex_is_strip=True):
    if field_name == 'title':
        return tidy_title(text, regex, regex_is_strip)
    if field_name == 'authors':
        return tidy_author(text, regex, regex_is_strip)
    if field_name == 'pubdate':
        return tidy_pubdate(text, regex, regex_is_strip)
    return tidy_field(text, regex, regex_is_strip)

def create_standard_columns(db):
    columns = {}
    columns['title'] = _('Title')
    columns['authors'] = _('Authors')
    columns['series'] = _('Series')
    columns['series_index'] = _('Series Index')
    columns['pubdate'] = _('Published')
    columns['publisher'] = _('Publisher')
    columns['rating'] = _('Rating')
    columns['tags'] = _('Tags')
    columns['comments'] = _('Comments')
    columns['languages'] = _('Languages')

    id_types = db.get_all_identifier_types()
    for id_type in sorted(id_types):
        columns['identifier:'+id_type] = 'ID:'+id_type
    # Update: add match by uuid {
    # add uuid to identifiers provided the user does not have a custom uuid identifier
    if 'uuid' not in id_types:
        columns['identifier:uuid'] = 'ID:uuid'
    #}

    custom_columns = db.field_metadata.custom_field_metadata()
    for key, column in custom_columns.items():
        typ = column['datatype']
        if typ == 'series':
            # Add an extra column for the custom series index.
            columns[key+'_index'] = column['name'] + ' Index'
#         if typ not in ['enumeration', 'composite']:
        if typ not in ['composite']:
            columns[key] = column['name']
    return columns

class ReorderedComboBox(QComboBox):

    def __init__(self, parent, strip_items=True):
        QComboBox.__init__(self, parent)
        self.strip_items = strip_items
        self.setEditable(True)
        self.setMaxCount(10)
        self.setInsertPolicy(QComboBox.InsertAtTop)

    def populate_items(self, items, sel_item):
        self.blockSignals(True)
        self.clear()
        self.clearEditText()
        for text in items:
            if text != sel_item:
                self.addItem(text)
        if sel_item:
            self.insertItem(0, sel_item)
            self.setCurrentIndex(0)
        else:
            self.setEditText('')
        self.blockSignals(False)

    def reorder_items(self):
        self.blockSignals(True)
        text = str(self.currentText())
        if self.strip_items:
            text = text.strip()
        if not text.strip():
            return
        existing_index = self.findText(text, Qt.MatchExactly)
        if existing_index:
            self.removeItem(existing_index)
            self.insertItem(0, text)
            self.setCurrentIndex(0)
        self.blockSignals(False)

    def get_items_list(self):
        if self.strip_items:
            return [str(self.itemText(i)).strip() for i in range(0, self.count())]
        else:
            return [str(self.itemText(i)) for i in range(0, self.count())]


class DragDropLineEdit(QLineEdit):
    '''
    Unfortunately there is a flaw in the Qt implementation which means that
    when the QComboBox is in editable mode that dropEvent is not fired
    if you drag into the editable text area. Working around this by having
    a custom LineEdit() set for the parent combobox.
    '''
    def __init__(self, parent, drop_mode):
        QLineEdit.__init__(self, parent)
        self.drop_mode = drop_mode
        self.setAcceptDrops(True)

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dragEnterEvent(self, event):
        if int(event.possibleActions() & qtDropActionCopyAction) + \
           int(event.possibleActions() & qtDropActionMoveAction) == 0:
            return
        data = self._get_data_from_event(event)
        if data:
            event.acceptProposedAction()

    def dropEvent(self, event):
        data = self._get_data_from_event(event)
        event.setDropAction(qtDropActionCopyAction)
        self.setText(data[0])

    def _get_data_from_event(self, event):
        md = event.mimeData()
        if self.drop_mode == 'file':
            urls, filenames = dnd_get_files(md, ['csv', 'txt'])
            if not urls:
                # Nothing found
                return
            if not filenames:
                # Local files
                return urls
            else:
                # Remote files
                return filenames
        if event.mimeData().hasFormat('text/uri-list'):
            urls = [str(u.toString()).strip() for u in md.urls()]
            return urls


class DragDropComboBox(ReorderedComboBox):
    '''
    Unfortunately there is a flaw in the Qt implementation which means that
    when the QComboBox is in editable mode that dropEvent is not fired
    if you drag into the editable text area. Working around this by having
    a custom LineEdit() set for the parent combobox.
    '''
    def __init__(self, parent, drop_mode='url'):
        ReorderedComboBox.__init__(self, parent)
        self.drop_line_edit = DragDropLineEdit(parent, drop_mode)
        self.setLineEdit(self.drop_line_edit)
        self.setAcceptDrops(True)
        self.setEditable(True)
        self.setMaxCount(10)
        self.setInsertPolicy(QComboBox.InsertAtTop)

    def dragMoveEvent(self, event):
        self.lineEdit().dragMoveEvent(event)

    def dragEnterEvent(self, event):
        self.lineEdit().dragEnterEvent(event)

    def dropEvent(self, event):
        self.lineEdit().dropEvent(event)


class StrippedTextEdit(QTextEdit):
    '''
    Override the pasting of data to strip leading and trailing spaces off every line
    '''

    def __init__(self, parent):
        QTextEdit.__init__(self, parent)
        self.setLineWrapMode(qTextEdit_NoWrap)

    def insertFromMimeData(self, source):
        if not source.hasText():
            return
        lines = str(source.text()).split('\n')
        new_lines = []
        for line in lines:
            ln = line.strip()
            if ln:
                new_lines.append(ln)
        txt = '\n'.join(new_lines)
        cursor = self.textCursor()
        cursor.insertText(txt)


class AddColumnDialog(SizePersistedDialog):
    '''
    Used by the Clipboard tab to add a field to the parse list.
    '''

    def __init__(self, parent, columns):
        SizePersistedDialog.__init__(self, parent, 'import list plugin:add field dialog')
        self.setWindowTitle(_('Select field(s) to add:'))
        self.avail_columns = columns

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.values_list = QListWidget(self)
        self.values_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.values_list.doubleClicked.connect(self._accept_clicked)
        layout.addWidget(self.values_list)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._accept_clicked)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._populate_fields_list()

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def _populate_fields_list(self):
        self.values_list.clear()
        sorted_keys = sorted(list(self.avail_columns.keys()), key=lambda k: self.avail_columns[k])
        for field_name in sorted_keys:
            display_name = self.avail_columns[field_name]
            if field_name.startswith('#'):
                display_name = '%s (%s)' % (display_name, field_name)
            item = QListWidgetItem(display_name, self.values_list)
            item.setData(Qt.UserRole, field_name)
            item.setToolTip(field_name)
            self.values_list.addItem(item)

    def _get_selected_field_names(self):
        values = []
        for item in self.values_list.selectedItems():
            field_name = str(item.data(Qt.UserRole))
            values.append(field_name)
        return values

    def _accept_clicked(self):
        self.selected_names = self._get_selected_field_names()
        if len(self.selected_names) == 0:
            error_dialog(self, _('No fields selected'), _('You must select one or more fields first.'), show=True)
            return
        self.accept()


class AddRemoveFieldDialog(SizePersistedDialog):

    def __init__(self, parent, avail_columns_map, used_fields):
        SizePersistedDialog.__init__(self, parent, 'import list plugin:addremove field dialog')
        self.setWindowTitle(_('Select fields to import:'))
        self.avail_columns_map = avail_columns_map
        self.used_fields = used_fields

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.values_list = QListWidget(self)
        self.values_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.values_list.doubleClicked.connect(self._accept_clicked)
        layout.addWidget(self.values_list)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._accept_clicked)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._populate_fields_list()

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def _populate_fields_list(self):
        self.values_list.clear()
        sorted_keys = sorted(list(self.avail_columns_map.keys()), key=lambda k: self.avail_columns_map[k])
        for field_name in sorted_keys:
            display_name = self.avail_columns_map[field_name]
            if field_name.startswith('#'):
                display_name = '%s (%s)' % (display_name, field_name)
            item = QListWidgetItem(display_name, self.values_list)
            item.setData(Qt.UserRole, field_name)
            if field_name in ['title','authors','rows']:
                item.setFlags(Qt.ItemIsUserCheckable)
            else:
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            if field_name in self.used_fields:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            item.setToolTip(field_name)
            self.values_list.addItem(item)

    def _get_checked_field_names(self):
        self.added_names = []
        self.removed_names = []
        for row in range(0, self.values_list.count()):
            item = self.values_list.item(row)
            field_name = str(item.data(Qt.UserRole))
            if item.checkState() == Qt.Checked:
                if field_name not in self.used_fields:
                    self.added_names.append(field_name)
            elif field_name in self.used_fields:
                self.removed_names.append(field_name)

    def _accept_clicked(self):
        self._get_checked_field_names()
        self.accept()

# Update: add match by identifier {
class MatchGroupBox(QGroupBox):
    def __init__(self, parent_tab):
        QGroupBox.__init__(self)
        self.parent_tab = parent_tab
        self.gui = parent_tab.parent_page.gui
        self.init_controls()

    def init_controls(self):
        self.setTitle(' '+_('&Match Method:')+' ')
        ml = self.ml = QHBoxLayout()
        self.setLayout(ml)
        self.titleauthor_opt = QRadioButton(_('&Title/Author'), self)
        self.titleauthor_opt.setChecked(True)
        self.titleauthor_opt.toggled.connect(self._match_btn_toggled)
        id_box = QHBoxLayout()
        self.identifier_opt = QRadioButton(_('&Identifier:'), self)
        self.identifier_opt.toggled.connect(self._match_btn_toggled)
        self.identifier_combo = QComboBox()
        self.identifier_combo.setMaximumWidth(300)
        self.identifier_opt.setEnabled(False)
        id_box.addWidget(self.identifier_opt)
        id_box.addWidget(self.identifier_combo)
        id_box.setContentsMargins(0, 0, 0, 0)
        ml.addWidget(self.titleauthor_opt)
        ml.addStretch(1)
        ml.addLayout(id_box)

    def _match_btn_toggled(self):
        self.identifier_combo.clear()
        if self.identifier_opt.isChecked():
            self.identifier_combo.addItems(self.get_id_types())

    def _refresh_match_opts(self):
        current_id_types = self.get_id_types()
        currentText = self.identifier_combo.currentText()
        self.identifier_combo.clear()
        self.identifier_opt.setEnabled(True)
        if len(current_id_types) == 0:
            self.titleauthor_opt.setChecked(True)
            self.identifier_opt.setEnabled(False)
        else:
            if currentText in current_id_types:
                self.identifier_combo.addItems(current_id_types)
                idx = self.identifier_combo.findText(currentText)
                self.identifier_combo.setCurrentIndex(idx)
                self.identifier_opt.setChecked(True)
            else:
                # Previoysly chosen identifier no more available, switch to titleauthor matching
                if self.identifier_opt.isChecked():
                    self.titleauthor_opt.setChecked(True)

    def get_id_types(self):
        return [ key.split(':')[-1] for key in self.parent_tab._get_current_columns() if key.find('identifier:') != -1 ]

    def get_match_opts(self):
        match_settings = {}
        if self.titleauthor_opt.isChecked():
            match_settings['match_method'] = 'title/author'
        elif self.identifier_opt.isChecked():
            match_settings['match_method'] = 'identifier'
            match_settings['id_type'] = self.identifier_combo.currentText()
        return match_settings
        
    def set_match_opts(self, match_settings):
        if match_settings['match_method'] == 'title/author':
            self.titleauthor_opt.setChecked(True)
        elif match_settings['match_method'] == 'identifier':
            id_type = match_settings['id_type']
            self.identifier_opt.setEnabled(True)
            self.identifier_opt.setChecked(True)
            self.identifier_combo.clear()
            self.identifier_combo.addItems([id_type])
            self.identifier_combo.setCurrentText(id_type)
        self._refresh_match_opts()

#}

# Test Wizard {{{
# calibre-debug -e tab_common.py
if __name__ == '__main__':

    def test_tokens():
        title = 'Young Samurai: The Way of the Sword (Young Samurai, #1)'
        print((list(get_title_tokens(title, strip_subtitle=False))))

    def test_assert_equal(expected, value):
        if value != expected:
            print(('Expected: \'%s\' but was \'%s\'' % (expected, value)))

    def test_tidy_title_author():
        test_assert_equal('The Magicians', tidy_title('  \n1. "The Magicians"  '))
        test_assert_equal('The Magicians', tidy_title('  The  \nMagicians.'))
        test_assert_equal('1942', tidy_title('  1942  '))
        test_assert_equal('1942', tidy_title(' \n1. 1942  '))
        test_assert_equal('Joe Bloggs', tidy_author('  \n by Joe Bloggs '))
        test_assert_equal('Bloggs, Joe', tidy_author(' Bloggs, Joe. '))
        test_assert_equal('Bloggs, S.', tidy_author(' Bloggs, S. '))
        test_assert_equal('S. Bloggs & Mr. Foo', tidy_author('by S.  Bloggs with Mr. Foo'))
        test_assert_equal('S. Bloggs & Mr. Foo', tidy_author('S. Bloggs and Mr. Foo'))
        print('Tests completed')

    #test_tokens()
    test_tidy_title_author()
    r = re.compile(r'\((\d+)\)')
    print((tidy_field('Hugo Award for Best Short Story (2012)', r, False)))
# }}}
