from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import re, sys, traceback
from functools import partial

try:
    from qt.core import (Qt, QWidget, QGridLayout, QHBoxLayout,
                        QLabel, QGroupBox, QVBoxLayout, QPushButton,
                        QToolButton, QMenu, QCheckBox)
except ImportError:                        
    from PyQt5.Qt import (Qt, QWidget, QGridLayout, QHBoxLayout,
                        QLabel, QGroupBox, QVBoxLayout, QPushButton,
                        QToolButton, QMenu, QCheckBox)

from calibre.ebooks.metadata import fmt_sidx
from calibre.gui2 import error_dialog

import calibre_plugins.import_list.config as cfg
from calibre_plugins.import_list.common_compatibility import qTextEdit_NoWrap
from calibre_plugins.import_list.common_icons import get_icon
from calibre_plugins.import_list.tab_common import (StrippedTextEdit, ReorderedComboBox,
                                tidy, AddColumnDialog, create_standard_columns)

try:
    load_translations()
except NameError:
    pass

DEFAULT_CLIP_PATTERNS = [('Title - Author', r'(?P<title>.*?) \- (?P<authors>.*)'),
                         ('Title by Author', r'(?P<title>.*?) by (?P<authors>.*)'),
                         ('Title / Author', r'(?P<title>.*?) / (?P<authors>.*)'),
                         ('Title (Author)', r'(?P<title>.*?) \((?P<authors>.*)\)')]
    
class ImportClipboardTab(QWidget):

    def __init__(self, parent_page):
        self.parent_page = parent_page
        QWidget.__init__(self)
        self.init_controls()
        self.possible_columns = create_standard_columns(self.parent_page.db)

    def init_controls(self):
        self.block_events=False
        l = QGridLayout()
        self.setLayout(l)

        paste_lbl = QLabel(_('&Paste your book list here:'))
        paste_lbl.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self.setting_lbl = QLabel('', self)
        self.setting_lbl.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        l.addWidget(paste_lbl, 0, 0, 1, 1)
        l.addWidget(self.setting_lbl, 0, 1, 1, 1)
        self.paste_button = QPushButton(get_icon('edit-paste.png'), _('&Paste'), self)
        self.paste_button.setToolTip(_('Replace all text above with the contents of your clipboard'))
        self.paste_button.clicked.connect(self._paste_text)
        l.addWidget(self.paste_button, 0, 2, 1, 1)

        self.clip_textedit = StrippedTextEdit(self)
        self.clip_textedit.setLineWrapMode(qTextEdit_NoWrap)
        paste_lbl.setBuddy(self.clip_textedit)
        l.addWidget(self.clip_textedit, 1, 0, 1, 3)
        l.setColumnStretch(0,1)
        l.setRowStretch(1,1)

        gb = QGroupBox(' '+_('Conversion expression:')+' ', self)
        l.addWidget(gb, 2, 0, 1, 3)

        gbl = QVBoxLayout()
        gb.setLayout(gbl)
        re_lbl = QLabel(_('Set a <a href="http://manual.calibre-ebook.com/regexp.html">regular expression</a> to use for titles and other metadata. '
                        'The group names you can use include')+': (?P&lt;title&gt;), (?P&lt;authors&gt;), (?P&lt;series&gt;), (?P&lt;series_index&gt;), '
                        '(?P&lt;identifier:isbn&gt;)', self)
        re_lbl.linkActivated.connect(self.parent_page.open_external_link)
        re_lbl.setWordWrap(True)
        gbl.addWidget(re_lbl)

        rel = QHBoxLayout()
        gbl.addLayout(rel)

        self.pat_combo = ReorderedComboBox(self, strip_items=False)
        rel.addWidget(self.pat_combo, 1)

        self.standard_pat_button = QToolButton(self)
        self.standard_pat_button.setToolTip(_('Choose a predefined named pattern'))
        self.standard_pat_button.setMenu(self._create_standard_pat_menu())
        self.standard_pat_button.setIcon(get_icon('images/script.png'))
        self.standard_pat_button.setPopupMode(QToolButton.InstantPopup)
        rel.addWidget(self.standard_pat_button)

        butl = QHBoxLayout()
        l.addLayout(butl, 4, 0, 1, 3)

        self.clear_button = QPushButton(get_icon('trash.png'), _('&Clear'), self)
        self.clear_button.setToolTip(_('Clear all settings back to the defaults on this tab'))
        self.clear_button.clicked.connect(self._clear_to_defaults)
        self.add_field_button = QPushButton(get_icon('column.png'), _('&Fields')+'...', self)
        self.add_field_button.setToolTip(_('Add expression for field to import'))
        self.add_field_button.clicked.connect(self._add_field)
        self.reverse_list_checkbox = QCheckBox(_('Reverse order'), self)
        self.reverse_list_checkbox.setToolTip(_('Display the books in the opposite order to the source'))
        self.preview_button = QPushButton(get_icon('wizard.png'), _('&Preview'), self)
        self.preview_button.setToolTip(_('Preview the results in the books grid'))
        self.preview_button.clicked.connect(self._preview_rows)
        butl.addWidget(self.clear_button)
        butl.addWidget(self.add_field_button)
        butl.addStretch(1)
        butl.addWidget(self.reverse_list_checkbox)
        butl.addWidget(self.preview_button)

        # Wire up our signals at the end to prevent premature raising
        self.clip_textedit.textChanged.connect(self._preview_rows)

    def _clear_to_defaults(self, clear_last=True):
        self.block_events = True
        self._clear_setting_name(clear_last)
        self.clip_textedit.clear()
        self.pat_combo.clearEditText()
        self.reverse_list_checkbox.setChecked(False)
        self.block_events = False
        self.parent_page.clear_preview_books()

    def _clear_setting_name(self, clear_last=True):
        if clear_last:
            self.parent_page.library_config[cfg.KEY_LAST_WEB_SETTING] = ''
        self.setting_lbl.setText('')
        self.parent_page.info['current_setting'] = ''
        
    def _add_field(self):
        # Interested in all columns (can't be bothered filtering it)
        d = AddColumnDialog(self, self.possible_columns)
        if d.exec_() == d.Accepted:
            expression = str(self.pat_combo.currentText())
            for new_field in d.selected_names:
                expression += '(?P<' + new_field + '>.*)'
            self.pat_combo.setEditText(expression)
            self.pat_combo.setFocus()

    def _paste_text(self):
        self._clear_setting_name()
        self.clip_textedit.clear()
        self.clip_textedit.paste()

    def _create_standard_pat_menu(self):
        menu = QMenu(self)
        for name, regex in DEFAULT_CLIP_PATTERNS:
            action = menu.addAction(name)
            action.triggered.connect(partial(self._assign_standard_pattern, regex))
        return menu

    def _assign_standard_pattern(self, regex):
        self.pat_combo.setEditText(regex)
        self._preview_rows()

    def _preview_rows(self):
        if self.block_events:
            return
        expression = str(self.pat_combo.currentText())
        if '?P<author>' in expression:
            # Play nice to legacy users and substitute ?P<authors> for ?P<author>
            expression = expression.replace('?P<author>', '?P<authors>')
            self.pat_combo.setEditText(expression)
        regex = None
        defined_columns = []
        if expression:
            defined_columns = re.findall(r'\?P<([^>]+)>', expression)
            expression = re.sub(r'(?i)\?P<identifier:', '?P<', expression)
            try:
                regex = re.compile(expression, re.UNICODE)
            except:
                msg = _('Failed to parse page:\n') + str(sys.exc_info()[1])
                error_dialog(self.parent_page, _('Invalid regular expression'), msg, show=True,
                             det_msg=traceback.format_exc())
            else:
                # Update our combo dropdown history if needed
                self.pat_combo.reorder_items()

        books = []
        text = str(self.clip_textedit.toPlainText())
        lines = text.split('\n')
        num_lines = 0
        custom_columns = self.parent_page.db.field_metadata.custom_field_metadata()
        for line in lines:
            if len(line) == 0:
                continue
            num_lines += 1
            title = line
            author = series_name = ''
            book = {'title':title, 'authors':author}
            if regex is not None:
                m = regex.match(line)
                if m is not None:
                    for defined_column in defined_columns:
                        series_index = '0'
                        if defined_column.lower().startswith('identifier:'):
                            book[defined_column] = tidy(defined_column, m.group(defined_column[11:]))
                            continue
                        if defined_column not in m.groupdict():
                            continue
                        if defined_column == 'series_index' or (defined_column.startswith('#') and defined_column.endswith('_index')):
                            continue
                        col = {}
                        if defined_column.startswith('#') and defined_column in custom_columns:
                            col = custom_columns[defined_column]
                        if defined_column == 'series' or col.get('datatype','') == 'series':
                            series_name = tidy(defined_column, m.group(defined_column))
                            if defined_column+'_index' in m.groupdict():
                                series_index = m.group(defined_column+'_index')
                            if series_name and series_index:
                                try:
                                    book[defined_column] = '%s [%s]'%(series_name, fmt_sidx(series_index))
                                except:
                                    book[defined_column] = series_name + ' [0]'
                        elif col.get('datatype','') == 'bool':
                            value_text = tidy(defined_column, m.group(defined_column))
                            if value_text.lower() in ['true','yes','y','1']:
                                value_text = 'Yes'
                            if value_text.lower() in ['n/a','undefined','']:
                                value_text = 'n/a'
                            else:
                                value_text = 'No'
                            book[defined_column] = value_text
                        else:
                            book[defined_column] = tidy(defined_column, m.group(defined_column))
            books.append(book)

        if self.reverse_list_checkbox.isChecked():
            books.reverse()
        columns = self._get_current_columns()
        self.parent_page.refresh_preview_books(columns, books, cfg.KEY_IMPORT_TYPE_CLIPBOARD)

    def _get_current_columns(self):
        # Identify which columns the user has configured
        columns = ['title', 'authors']
        text = str(self.pat_combo.currentText())
        defined_columns = re.findall(r'\?P<([^>]+)>', text)
        for column in defined_columns:
            if column not in columns:
                columns.append(column)
        return columns

    def restore_settings(self, library_config):
        self._clear_to_defaults(clear_last=False)
        context = library_config[cfg.KEY_CURRENT][cfg.KEY_IMPORT_TYPE_CLIPBOARD]
        self.pat_combo.populate_items(library_config[cfg.KEY_CLIPBOARD_REGEXES],
                                      context[cfg.KEY_CLIPBOARD_REGEX])
        self.reverse_list_checkbox.setChecked(context.get(cfg.KEY_CLIPBOARD_REVERSE_LIST, False))
        self.block_events = True
        self.clip_textedit.setPlainText(context[cfg.KEY_CLIPBOARD_TEXT])
        last_setting_name = library_config.get(cfg.KEY_LAST_CLIPBOARD_SETTING, '')
        self.setting_lbl.setText('<b>%s</b>'%last_setting_name)
        self.block_events = False

    def save_settings(self, library_config):
        library_config[cfg.KEY_CLIPBOARD_REGEXES] = self.pat_combo.get_items_list()
        context = library_config[cfg.KEY_CURRENT][cfg.KEY_IMPORT_TYPE_CLIPBOARD]
        context[cfg.KEY_CLIPBOARD_REGEX] = str(self.pat_combo.currentText())
        context[cfg.KEY_CLIPBOARD_TEXT] = str(self.clip_textedit.toPlainText())
        context[cfg.KEY_CLIPBOARD_REVERSE_LIST] = self.reverse_list_checkbox.isChecked()
