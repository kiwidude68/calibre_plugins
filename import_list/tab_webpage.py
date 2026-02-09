from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import re, copy, sys, traceback
from collections import OrderedDict
from functools import partial
from uuid import uuid4
from six import text_type as unicode

from lxml.html import fromstring, tostring
from lxml.html.clean import Cleaner

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (QApplication, Qt, QWidget, QTextEdit, QGridLayout,
                        QLabel, QGroupBox, QVBoxLayout, QPushButton, QHBoxLayout,
                        QVBoxLayout, QLineEdit, QToolButton, QMenu, QCheckBox, QSpinBox,
                        QTextCursor, QBrush, QUrl, QDialogButtonBox,
                        QRadioButton, QScrollArea, QComboBox)
except ImportError:                        
    from PyQt5.Qt import (QApplication, Qt, QWidget, QTextEdit, QGridLayout,
                        QLabel, QGroupBox, QVBoxLayout, QPushButton, QHBoxLayout,
                        QVBoxLayout, QLineEdit, QToolButton, QMenu, QCheckBox, QSpinBox,
                        QTextCursor, QBrush, QUrl, QDialogButtonBox,
                        QRadioButton, QScrollArea, QComboBox)

try:
    qTextCursor_KeepAnchor = QTextCursor.MoveMode.KeepAnchor
    qTextCursor_MoveAnchor = QTextCursor.MoveMode.MoveAnchor
    qTextCursor_Right = QTextCursor.MoveOperation.Right
except:
    qTextCursor_KeepAnchor = QTextCursor.KeepAnchor
    qTextCursor_MoveAnchor = QTextCursor.MoveAnchor
    qTextCursor_Right = QTextCursor.Right

from calibre import browser, random_user_agent, prints
from calibre.ebooks.metadata import fmt_sidx
from calibre.ebooks.BeautifulSoup import BeautifulSoup
from calibre.gui2 import error_dialog, open_url
from calibre.utils.cleantext import clean_ascii_chars
from calibre.utils.ipc.simple_worker import fork_job, WorkerError

import calibre_plugins.import_list.config as cfg
from calibre_plugins.import_list.common_compatibility import qSizePolicy_Preferred, qSizePolicy_Expanding
from calibre_plugins.import_list.common_icons import get_icon
from calibre_plugins.import_list.common_dialogs import SizePersistedDialog
from calibre_plugins.import_list.page_common import AUTHOR_SEPARATOR, TAGS_SEPARATOR
from calibre_plugins.import_list.tab_common import (DragDropComboBox, get_templated_url,
                                tidy_title, tidy_author, tidy_pubdate, tidy_field,
                                DEFAULT_STRIP_PATTERNS, create_standard_columns,
                                AddRemoveFieldDialog, MatchGroupBox)

try:
    load_translations()
except NameError:
    pass

WEB_ENCODINGS = ['utf-8','iso-8859-1','iso-8859-2','latin-1','ascii']

def load_page_in_browser(url, delay):
    raw = None
    try:
        br = browser(random_user_agent())
        raw = br.open_novisit(url).read()
    except:
        pass
    return raw


class RexexStripDialog(SizePersistedDialog):

    def __init__(self, parent, field_name, regex, regex_is_strip):
        SizePersistedDialog.__init__(self, parent, 'import list plugin:regex strip dialog')

        self.setWindowTitle(field_name)
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        hrl = QHBoxLayout()
        layout.addLayout(hrl)
        self.regxex_is_strip_radio = QRadioButton(_('Strip matching text'), self)
        self.regex_is_inclusive_radio = QRadioButton(_('Include matching text'), self)
        hrl.addWidget(self.regxex_is_strip_radio)
        hrl.addWidget(self.regex_is_inclusive_radio)
        hrl.addStretch(1)
        if regex_is_strip:
            self.regxex_is_strip_radio.setChecked(True)
        else:
            self.regex_is_inclusive_radio.setChecked(True)

        hl = QHBoxLayout()
        layout.addLayout(hl)

        self.strip_regex_ledit = QLineEdit(regex, self)
        self.strip_regex_ledit.setMinimumWidth(150)
        self.standard_pat_button = QToolButton(self)
        self.standard_pat_button.setToolTip(_('Choose a predefined pattern'))
        self.standard_pat_button.setMenu(self._create_standard_pat_menu())
        self.standard_pat_button.setIcon(get_icon('images/script.png'))
        self.standard_pat_button.setPopupMode(QToolButton.InstantPopup)
        self.clear_button = QToolButton(self)
        self.clear_button.setToolTip(_('Clear the regular expression'))
        self.clear_button.setIcon(get_icon('trash.png'))
        self.clear_button.clicked.connect(self._clear_regex)
        hl.addWidget(self.strip_regex_ledit, 1)
        hl.addWidget(self.standard_pat_button)
        hl.addWidget(self.clear_button)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def _create_standard_pat_menu(self):
        menu = QMenu(self)
        for name, regex in DEFAULT_STRIP_PATTERNS:
            action = menu.addAction(name)
            action.triggered.connect(partial(self._assign_standard_pattern, regex))
        return menu

    def _assign_standard_pattern(self, regex):
        self.strip_regex_ledit.setText(regex)

    def _clear_regex(self):
        self.strip_regex_ledit.clear()
        self.raw_list = []

    def regex_text(self):
        return unicode(self.strip_regex_ledit.text())

    def regex_is_strip(self):
        return self.regxex_is_strip_radio.isChecked()


class ListComboBox(QComboBox):

    def __init__(self, parent, values, selected_value=None):
        QComboBox.__init__(self, parent)
        self.values = values
        if selected_value is not None:
            self.populate_combo(selected_value)

    def populate_combo(self, selected_value):
        self.blockSignals(True)
        self.clear()
        selected_idx = idx = -1
        for value in self.values:
            idx = idx + 1
            self.addItem(value)
            if value == selected_value:
                selected_idx = idx
        self.setCurrentIndex(selected_idx)
        self.blockSignals(False)

    def selected_value(self):
        return unicode(self.currentText())


class ImportWebPageTab(QWidget):

    def __init__(self, parent_page):
        self.parent_page = parent_page
        QWidget.__init__(self)
        self.is_changed_text = False
        self.xpath_row_controls = OrderedDict()
        self._init_controls()
        self._load_column_metadata()
        self.raw_list = []

    def _init_controls(self):
        self.block_events = False

        vl = QVBoxLayout()
        self.setLayout(vl)

        l = self.l = QGridLayout()
        vl.addLayout(l)

        url_lbl = QLabel(_('&Download from url:'), self)
        url_lbl.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self.setting_lbl = QLabel('', self)
        self.setting_lbl.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.url_combo = DragDropComboBox(self, drop_mode='url')
        self.url_combo.editTextChanged.connect(self._on_url_changed)
        url_lbl.setBuddy(self.url_combo)
        l.addWidget(url_lbl, 0, 0, 1, 1)
        l.addWidget(self.setting_lbl, 0, 1, 1, 1)
        cul = QHBoxLayout()
        l.addLayout(cul, 1, 0, 1, 2)
        cul.addWidget(self.url_combo, 1)
        self.paste_button = QToolButton(self)
        self.paste_button.setToolTip(_('Paste a URL from your clipboard'))
        self.paste_button.setIcon(get_icon('edit-paste.png'))
        self.paste_button.clicked.connect(self._paste_url)
        cul.addWidget(self.paste_button)
        self.open_browser_button = QToolButton(self)
        self.open_browser_button.setToolTip(_('Open this url in your web browser'))
        self.open_browser_button.setIcon(get_icon('images/browser.png'))
        self.open_browser_button.clicked.connect(self._open_in_browser)
        cul.addWidget(self.open_browser_button)

        wl = QHBoxLayout()
        l.addLayout(wl, 2, 0, 1, 2)
        source_lbl = QLabel(_('&Source html:'), self)
        encoding_lbl = QLabel(_('&Encoding:'), self)
        encoding_lbl.setToolTip(_('Specify the web page encoding if not utf-8'))
        self.encoding_combo = ListComboBox(self, WEB_ENCODINGS, WEB_ENCODINGS[0])
        encoding_lbl.setBuddy(self.encoding_combo)
        self.javascript_checkbox = QCheckBox(_('Load javascript'), self)
        self.javascript_checkbox.setToolTip(_('Enable this option if the web page renders its content using javascript'))
        delay_lbl = QLabel(_('&Delay:'), self)
        delay_lbl.setToolTip(_('Additional delay in seconds to wait for web page javascript to execute'))
        self.delay_spin = QSpinBox(self)
        self.delay_spin.setRange(0, 60)
        delay_lbl.setBuddy(self.delay_spin)
        wl.addWidget(source_lbl, 1)
        wl.addWidget(encoding_lbl)
        wl.addWidget(self.encoding_combo)
        wl.addWidget(self.javascript_checkbox)
        wl.addWidget(delay_lbl)
        wl.addWidget(self.delay_spin)

        self.source_tedit = QTextEdit(self)
        if hasattr(self.source_tedit, 'setTabStopDistance'):
            self.source_tedit.setTabStopDistance(24)
        else:
            self.source_tedit.setTabStopWidth(24)
        self.source_tedit.textChanged.connect(self._source_text_changed)
        source_lbl.setBuddy(self.source_tedit)
        l.addWidget(self.source_tedit, 3, 0, 1, 2)
        l.setRowStretch(3, 1)

        fgb = QGroupBox(' '+_('Find:')+' ', self)
        fgb.setStyleSheet('QGroupBox { font-weight: bold; }')
        l.addWidget(fgb, 4, 0, 1, 2)
        fgbl = QHBoxLayout()
        fgb.setLayout(fgbl)
        find_lbl = QLabel(_('&Text:'), self)
        find_lbl.setToolTip(_('Search for text to help locate the region of interest such as\n'
                            'a book name when designing your xpath expressions'))
        self.find_ledit = QLineEdit('', self)
        self.find_ledit.setPlaceholderText(_('Search for specific text'))
        find_lbl.setBuddy(self.find_ledit)
        self.find_button = QPushButton(get_icon('search.png'), _('&Find'), self)
        self.find_button.clicked.connect(self._find_text)
        fgbl.addWidget(find_lbl)
        fgbl.addWidget(self.find_ledit, 1)
        fgbl.addWidget(self.find_button)

        self.mgb = MatchGroupBox(self)
        self.match_layout = QVBoxLayout()
        self.match_layout.addWidget(self.mgb)
        l.addLayout(self.match_layout, 5, 0, 1, 2)

        gb = QGroupBox(' '+_('XPath:')+' ', self)
        gb.setStyleSheet('QGroupBox { font-weight: bold; }')

        gbl = QVBoxLayout()
        gb.setLayout(gbl)
        xpath_lbl = QLabel(_('Specify XPath expressions to identify the parent '
                           'rows and title / authors within each row in the source html.'), self)
        xpath_lbl.setWordWrap(True)
        xpath_lbl.linkActivated.connect(self.parent_page.open_external_link)
        gbl.addWidget(xpath_lbl)

        self.xpath_layout = QGridLayout()
        gbl.addLayout(self.xpath_layout)

        scroll = QScrollArea()
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidgetResizable(True)
        scroll.setSizePolicy(qSizePolicy_Expanding, qSizePolicy_Preferred)
        scroll.setWidget(gb)
        l.addWidget(scroll, 6, 0, 1, 2)
        l.setRowStretch(6, 1)
        # Controls will be added dynamically when grid is populated

        xpbl = QHBoxLayout()
        l.addLayout(xpbl, 7, 0, 1, 2)
        self.row_count_lbl = QLabel(_('0 occurrences'), self)
        self.row_count_lbl.setToolTip(_('Number of matches using Test'))
        self.test_previous_button = QToolButton(self)
        self.test_previous_button.setToolTip(_('Previous test result'))
        self.test_previous_button.setIcon(get_icon('arrow-up.png'))
        self.test_previous_button.setEnabled(False)
        self.test_previous_button.clicked.connect(self._goto_previous)
        self.test_next_button = QToolButton(self)
        self.test_next_button.setToolTip(_('Next test result'))
        self.test_next_button.setIcon(get_icon('arrow-down.png'))
        self.test_next_button.setEnabled(False)
        self.test_next_button.clicked.connect(self._goto_next)
        xpbl.addStretch(1)
        xpbl.addWidget(self.row_count_lbl)
        xpbl.addWidget(self.test_previous_button)
        xpbl.addWidget(self.test_next_button)

        butl = QHBoxLayout()
        vl.addLayout(butl)

        self.clear_button = QPushButton(get_icon('trash.png'), _('&Clear'), self)
        self.clear_button.setToolTip(_('Clear all settings back to the defaults on this tab'))
        self.clear_button.clicked.connect(self._clear_to_defaults)
        self.add_field_button = QPushButton(get_icon('column.png'), _('&Fields')+'...', self)
        self.add_field_button.setToolTip(_('Select field(s) to import'))
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

        self.block_events = False

    def _load_column_metadata(self):
        self.possible_columns = OrderedDict()
        self.possible_columns['rows'] ='Rows'
        for k,v in create_standard_columns(self.parent_page.db).items():
            self.possible_columns[k] = v

    def _add_field(self):
        used_fields = list(self.xpath_row_controls.keys())
        d = AddRemoveFieldDialog(self, self.possible_columns, used_fields)
        if d.exec_() == d.Accepted:
            for remove_field in d.removed_names:
                self._clear_xpath_controls_for_row(remove_field)
            for new_field in d.added_names:
                self._append_xpath_row_controls(new_field)
        self.mgb._refresh_match_opts()

    def _source_text_changed(self):
        if self.block_events:
            return
        self.is_changed_text = True

    def _find_text(self):
        find_text = unicode(self.find_ledit.text()).lower()
        txt = unicode(self.source_tedit.toPlainText()).lower()
        if not txt or not find_text:
            return
        cursor_idx = self.source_tedit.textCursor().position() + 1
        next_match_idx = -1
        if cursor_idx + len(find_text) < len(txt):
            next_match_idx = txt.find(find_text, cursor_idx + 1)
        if next_match_idx < 0:
            next_match_idx = txt.find(find_text)
        if next_match_idx < 0:
            return error_dialog(self, _('No matches'), _('No matches for:') + ' ' + find_text, show=True, show_copy_button=False)
        self._goto_loc(next_match_idx, n=len(find_text))
        self.source_tedit.setFocus()

    def _clear_xpath_controls_for_row(self, key):
        if key not in self.xpath_row_controls:
            return
        row_controls = self.xpath_row_controls[key]
        self.xpath_layout.removeWidget(row_controls['label'])
        row_controls['label'].setParent(None)
        self.xpath_layout.removeWidget(row_controls['ledit'])
        row_controls['ledit'].setParent(None)
        self.xpath_layout.removeWidget(row_controls['test_xpath_button'])
        row_controls['test_xpath_button'].clicked.disconnect()
        row_controls['test_xpath_button'].setParent(None)
        if 'regex_button' in row_controls:
            self.xpath_layout.removeWidget(row_controls['regex_button'])
            row_controls['regex_button'].clicked.disconnect()
            row_controls['regex_button'].setParent(None)
        del self.xpath_row_controls[key]

    def _clear_xpath_controls(self, add_default_fields=True):
        for key in list(self.xpath_row_controls.keys()):
            self._clear_xpath_controls_for_row(key)
        if add_default_fields:
            self._append_xpath_row_controls('rows')
            self._append_xpath_row_controls('title')
            self._append_xpath_row_controls('authors')

    def _append_xpath_row_controls(self, field_name, xpath_text='', regex_text='', is_strip_regex=True):
        row_controls = {}
        row = self.xpath_layout.rowCount()
        # It should be possible to load a saved setting for an identifier column
        # even if that column is not one of our "known" ones.
        if field_name not in self.possible_columns:
            if field_name.startswith('identifier:'):
                self.possible_columns[field_name] = field_name.replace('identifier:', 'ID:')
        display_name = self.possible_columns.get(field_name, '')

        lbl = QLabel(display_name + ':', self)
        ledit = QLineEdit(xpath_text, self)
        test_xpath_button = QToolButton(self)
        test_xpath_button.setIcon(get_icon('images/color.png'))
        test_xpath_button.clicked.connect(partial(self._test_xpath, field_name))
        self.xpath_layout.addWidget(lbl, row, 0, 1, 1)
        self.xpath_layout.addWidget(ledit, row, 1, 1, 1)
        self.xpath_layout.addWidget(test_xpath_button, row, 2, 1, 1)
        row_controls['label'] = lbl
        row_controls['ledit'] = ledit
        row_controls['test_xpath_button'] = test_xpath_button
        # Special cases hard-coded
        if field_name == 'rows':
            lbl.setToolTip(_('Identify the parent node in the html source that contains a single book'))
        else:
            regex_button = QToolButton(self)
            self._set_regex_button_visual(regex_button, regex_text, is_strip_regex)
            regex_button.clicked.connect(partial(self._modify_regex, regex_button, field_name))
            self.xpath_layout.addWidget(regex_button, row, 3, 1, 1)
            row_controls['regex_button'] = regex_button
            row_controls['regex'] = regex_text
            row_controls['regex_is_strip'] = is_strip_regex
        self.xpath_row_controls[field_name] = row_controls

    def _clear_to_defaults(self, clear_last=True, add_default_fields=True):
        self.block_events = True
        self._clear_setting_name(clear_last)
        self.url_combo.clearEditText()
        self.encoding_combo.setCurrentIndex(0)
        self.javascript_checkbox.setChecked(False)
        self.source_tedit.clear()
        self.raw_list = []
        self.find_ledit.setText('')
        self._clear_xpath_controls(add_default_fields)
        self.is_changed_text = False
        self.match_locs = []
        self.test_previous_button.setEnabled(False)
        self.test_next_button.setEnabled(False)
        self.reverse_list_checkbox.setChecked(False)
        self.block_events = False
        self.parent_page.clear_preview_books()
        self.mgb._refresh_match_opts()

    def _modify_regex(self, regex_button, field_name):
        regex = self.xpath_row_controls[field_name]['regex']
        regex_is_strip = self.xpath_row_controls[field_name]['regex_is_strip']
        d = RexexStripDialog(self, field_name, regex, regex_is_strip)
        if d.exec_() == d.Accepted:
            self.xpath_row_controls[field_name]['regex'] = d.regex_text()
            self.xpath_row_controls[field_name]['regex_is_strip'] = d.regex_is_strip()
            self._set_regex_button_visual(regex_button, d.regex_text(), d.regex_is_strip())

    def _set_regex_button_visual(self, regex_button, regex, is_strip_regex):
        if regex:
            regex_button.setIcon(get_icon('images/regex_specified.png'))
            if is_strip_regex:
                regex_button.setToolTip(_('Strip: %s')% regex)
            else:
                regex_button.setToolTip(_('Include: %s')% regex)
        else:
            regex_button.setIcon(get_icon('images/regex.png'))
            regex_button.setToolTip(_('No expression'))

    def _clear_setting_name(self, clear_last=True):
        if clear_last:
            self.parent_page.library_config[cfg.KEY_LAST_WEB_SETTING] = ''
        self.setting_lbl.setText('')
        self.parent_page.info['current_setting'] = ''

    def _paste_url(self):
        cb = QApplication.instance().clipboard()
        self._clear_setting_name()
        txt = unicode(cb.text()).strip()
        self.url_combo.setEditText(txt)

    def _on_url_changed(self):
        self.block_events = True
        self.source_tedit.clear()
        self.raw_list = []
        self.block_events = False

    def _open_in_browser(self):
        url = get_templated_url(unicode(self.url_combo.currentText()).strip())
        if url:
            open_url(QUrl(url))

    def _load_html(self, url, encoding, render_javascript):
        if url.lower().startswith('file://'):
            fname = QUrl(url).toLocalFile()
            with open(fname, 'rb') as f:
                raw = f.read()
        else:
            if render_javascript:
                try:
                    res = fork_job('calibre_plugins.import_list.tab_webpage', 'load_page_in_browser',
                            (url, int(unicode(self.delay_spin.value()))))
                except WorkerError as e:
                    prints(e.orig_tb)
                    raise RuntimeError('Failed to run load_page_in_browser')
                raw = res['result']
            else:
                br = browser(url, user_agent=random_user_agent())
                raw = br.open_novisit(url).read()
        if raw:
            raw = raw.decode(encoding, errors='replace').encode('utf-8')
            raw = clean_ascii_chars(raw).replace(b'\r', b'')
            #open('''D:\\import-list-raw.html''','wb').write(raw)
        return raw

    def get_page_range(self, url):
        page_range = re.sub(r'.*\{(\d+)\-(\d+)\}.*', r'\1,\2', url)
        try:
            page_range = [ int(x) for x in page_range.split(',') ]
            first, last = page_range
            return first, last
        except:
            return None

    def url_with_page_no(self, url, page_no):
        url = re.sub(r'(.*)\{\d+\-\d+\}(.*)', r'\1__page_no__\2'.format(page_no), url)
        url = url.replace('__page_no__', unicode(page_no))
        return url

    def _download_source(self):
        url = unicode(self.url_combo.currentText()).strip()
        if not url:
            self.block_events = True
            self.source_tedit.clear()
            self.raw_list = []
            self.block_events = False
            self.parent_page.clear_preview_books()
            return None

        page_range = self.get_page_range(url)
        if page_range:
            first, last = page_range
            urls = [self.url_with_page_no(url, x) for x in range(first, last+1)]
        else:
            urls = [ get_templated_url(unicode(self.url_combo.currentText()).strip()) ]

        self.url_combo.reorder_items()
        encoding = self.encoding_combo.selected_value()
        render_javascript = self.javascript_checkbox.isChecked()

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for idx, url in enumerate(urls):
                try:
                    raw = self._load_html(url, encoding, render_javascript)

                    # Now prettify the html
                    soup = BeautifulSoup(raw)
                    raw = soup.prettify()#.decode('utf-8')
                    #open('''D:\\raw_prettified.html''','wb').write(raw)
                    root = fromstring(raw)
                    # Strip out loads of nonsense like Javascript and CSS which won't be used to parse
                    cleaner = Cleaner(style=True, page_structure=False)
                    root = cleaner.clean_html(root)
                    raw = tostring(root, method='html')
                    #open('D:\\raw_cleaned.html','wb').write(raw)
                    # We convert another time between root and raw to be 100% sure we can highlight correctly
                    # It's a pain from a performance perspective but only way to be sure due to issues found
                    # with Fantastic Fiction not showing the right results
                    root = fromstring(raw)
                    raw = tostring(root, method='html')
                    #open('D:\\raw_reconverted.html','wb').write(raw)
                    self.raw_list.append(raw)

                    if idx == 0:
                        self.block_events = True
                        self.source_tedit.setPlainText(unicode(raw, 'utf-8'))
                        self.block_events = False

                        self.test_next_button.setEnabled(False)
                        self.test_previous_button.setEnabled(False)
                except:
                    traceback.print_exc()
                    msg = _('Failed to download page')+':\n' + unicode(sys.exc_info()[1])
                    error_dialog(self.parent_page, _('Failed to download page'), msg, show=True)
                    #return None
            return self.raw_list
        finally:
            QApplication.restoreOverrideCursor()

    def _get_matching_elements(self, root, row_xpath, field_name, xpath):
        elements = []

        def iterate_matches(parent):
            # Any special cases up the top
            if field_name == 'series_index':
                series_indexes = parent.xpath(xpath)
                for series_index in series_indexes:
                    try:
                        _si = float(series_index)
                        elements.append(series_index)
                    except:
                        pass
            else:
                values = parent.xpath(xpath)
                for value_name in values:
                    if value_name is not None and len(value_name):
                        elements.append(value_name)

        if row_xpath:
            rows = root.xpath(row_xpath)
            for row in rows:
                if field_name == 'rows':
                    elements.append(row)
                else:
                    iterate_matches(row)
        else:
            iterate_matches(root)
        return elements

    def _test_xpath(self, field_name='rows'):
        self.test_next_button.setEnabled(False)
        self.test_previous_button.setEnabled(False)

        rows_xpath = unicode(self.xpath_row_controls['rows']['ledit'].text()).strip()
        xpath = unicode(self.xpath_row_controls[field_name]['ledit'].text()).strip()
        if not xpath:
            return error_dialog(self, _('Test failed'), _('You must specify an xpath'), show=True)

        raw = unicode(self.source_tedit.toPlainText())
        if not self.raw_list:
            raw_list = self._download_source()
            raw = raw_list[0]
        if not raw:
            return error_dialog(self, _('Test failed'), _('No html source available to match against'), show=True)

        QApplication.setOverrideCursor(Qt.WaitCursor)
        root = fromstring(raw)
        if self.is_changed_text:
            # Have to replace the text in case the tostring/fromstring changed nodes
            new_raw = tostring(root, method='html')
            self.source_tedit.setPlainText(new_raw)
            self.is_changed_text = False
        #Remove any previous selections
        self.source_tedit.setExtraSelections([])
        # Find all our matching elements
        try:
            elements = self._get_matching_elements(root, rows_xpath, field_name, xpath)
        except:
            QApplication.restoreOverrideCursor()
            error_dialog(self, _('Invalid xpath'),
                         _('Your xpath expression is invalid')+':\n'+unicode(sys.exc_info()[1]),
                         show=True, det_msg=traceback.format_exc())
            return
        finally:
            QApplication.restoreOverrideCursor()

        color = Qt.yellow
        matches, uuid_raw = self._search_for_matches(root, elements)
        self.row_count_lbl.setText(unicode(len(matches)) + ' '+_('occurrences'))
        if matches:
            self._highlight_matches(matches, uuid_raw, color)

    def _search_for_matches(self, root, matching_elements):
        matches = []
        prefix = ''
        # Insert a uuid before and after the opening/closing of the matching tag
        # We do this so able to find this text again afterwards
        for elem in matching_elements:
            open_id = unicode(uuid4())
            close_id = unicode(uuid4())
            if hasattr(elem, 'tag'):
                #print(open_id, close_id, 'has a tag')
                prev = elem.getprevious()
                if prev is not None:
                    #print('Prev=', prev.tag)
                    if prev.tail is None:
                        prev.tail = open_id
                    else:
                        prev.tail = prev.tail + open_id
                else:
                    prev = elem.getparent()
                    if prev is not None:
                        #print('Parent=', prev.tag)
                        if prev.text is None:
                            prev.text = open_id
                        else:
                            prev.text = prev.text + open_id
                    else:
                        # Special case of the first element
                        prefix += open_id

                if elem.tail is None:
                    elem.tail = close_id
                else:
                    elem.tail = close_id + elem.tail
            else:
                #print(open_id, close_id, 'has no tag')
                parent_elem = elem.getparent()
                if parent_elem.text is None:
                    # Assume this is a self-closing element
                    parent_elem.tail = open_id + parent_elem.tail + close_id
                else:
                    parent_elem.text = open_id + parent_elem.text + close_id
            matches.append((open_id, close_id))
        uuid_raw = prefix + tostring(root, method='html').decode(encoding='utf-8')
        return matches, uuid_raw

    def _highlight_matches(self, matches, uuid_raw, color=Qt.yellow):
        selections = []
        self.match_locs = []
        cursor = QTextCursor(self.source_tedit.document())
        extsel = QTextEdit.ExtraSelection()
        extsel.cursor = cursor
        extsel.format.setBackground(QBrush(color))
        #open('d:\\uuid_raw.html','wb').write(uuid_raw)
        try:
            offset = 0
            for open_id, close_id in matches:
                start_pos = uuid_raw.find(open_id, offset) - offset
                offset += len(open_id)
                end_pos = uuid_raw.find(close_id, start_pos) - offset
                offset += len(close_id)
                #print('Open', open_id,'Close',close_id,'Start=',start_pos,'End=',end_pos,'Offset=',offset)
                es = QTextEdit.ExtraSelection(extsel)
                es.cursor.setPosition(start_pos, qTextCursor_MoveAnchor)
                es.cursor.setPosition(end_pos, qTextCursor_KeepAnchor)
                selections.append(es)
                self.match_locs.append((start_pos, end_pos))
        except Exception as e:
            pass
        self.source_tedit.setExtraSelections(selections)
        if self.match_locs:
            self.test_next_button.setEnabled(True)
            self.test_previous_button.setEnabled(True)
            self._goto_loc(0)
            self._goto_next()
        else:
            self.test_next_button.setEnabled(False)
            self.test_previous_button.setEnabled(False)

    def _goto_previous(self):
        pos = self.source_tedit.textCursor().position()
        if self.match_locs:
            match_loc = len(self.match_locs) - 1
            for i in range(len(self.match_locs) - 1, -1, -1):
                loc = self.match_locs[i][1]
                if pos > loc:
                    match_loc = i
                    break
            self._goto_loc(self.match_locs[match_loc][0])

    def _goto_next(self):
        pos = self.source_tedit.textCursor().position()
        if self.match_locs:
            match_loc = 0
            for i in range(len(self.match_locs)):
                loc = self.match_locs[i][0]
                if pos < loc:
                    match_loc = i
                    break
            self._goto_loc(self.match_locs[match_loc][0])

    def _goto_loc(self, loc, operation=qTextCursor_Right, mode=qTextCursor_KeepAnchor, n=0):
        doc = self.source_tedit.document()
        cursor = QTextCursor(doc)
        if n:
            cursor.setPosition(loc)
            cursor.movePosition(operation, mode, n)
            self.source_tedit.setTextCursor(cursor)
        else:
            cursor.setPosition(doc.characterCount() - 1)
            self.source_tedit.setTextCursor(cursor)
            cursor.setPosition(loc)
            self.source_tedit.setTextCursor(cursor)

    def _preview_rows(self):
        if self.block_events:
            return

        raw = unicode(self.source_tedit.toPlainText()).strip()
        raw_list = self.raw_list
        if not raw_list:
            raw_list = self._download_source()
        if not raw_list:
            self.parent_page.clear_preview_books()
            return

        xpaths = {}
        has_xpath = False
        for field_name, controls in self.xpath_row_controls.items():
            xpath = unicode(controls['ledit'].text()).strip()
            if xpath:
                has_xpath = True
            xpaths[field_name] = xpath
        if not has_xpath:
            return error_dialog(self, _('Invalid xpath'), _('You have not specified any xpath expressions'), show=True)
        if not xpaths['title']:
            return error_dialog(self, _('Invalid xpath'), _('You have not specified a title xpath expression'), show=True)
        if 'series' in xpaths and 'series_index' not in xpaths:
            return error_dialog(self, _('Invalid xpath'), _('You must add a series_index xpath field if using series'), show=True)
        if 'series_index' in xpaths and 'series' not in xpaths:
            return error_dialog(self, _('Invalid xpath'), _('You must add a series xpath field if using series index'), show=True)
        rows_xpath = xpaths['rows']
        del xpaths['rows']

        field_regexes = {}
        for field_name, controls in self.xpath_row_controls.items():
            if 'regex' in controls:
                regex_text = controls['regex'].strip()
                if regex_text:
                    regex = re.compile(regex_text)
                    field_regexes[field_name] = (regex, controls['regex_is_strip'])

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            #root = fromstring(raw)
            books = []
            custom_columns = self.parent_page.db.field_metadata.custom_field_metadata()

            def append_matches(row_name_values):
                max_values = 0
                for values in row_name_values.values():
                    if len(values) > max_values:
                        max_values = len(values)
                for i in range(0, max_values):
                    book = {}
                    for field_name, values in row_name_values.items():
                        # Special case for series/series_index which are paired together
                        if field_name == 'series_index' or (field_name.startswith('#') and field_name.endswith('_index')):
                            continue
                        if i >= len(values) and field_name not in ['authors', 'series']:
                            # Special cases for assume same series/author on each row
                            book[field_name] = ''
                            continue
                        regex, regex_is_strip = field_regexes.get(field_name, (None, True))
                        value_text = ''
                        col = {}
                        if field_name.startswith('#') and field_name in custom_columns:
                            col = custom_columns[field_name]
                        # Special cases for some fields
                        if field_name == 'authors':
                            if len(values) == 1:
                                value_text = tidy_author(values[0], regex, regex_is_strip)
                            elif i < len(values):
                                value_text = tidy_author(values[i], regex, regex_is_strip)
                        elif field_name == 'series' or col.get('datatype','') == 'series':
                            series_name = ''
                            series_index = ''
                            if len(values) == 1:
                                series_name = tidy_field(values[0], regex, regex_is_strip)
                            elif i < len(values):
                                series_name = tidy_field(values[i], regex, regex_is_strip)
                            si_regex, si_regex_is_strip = field_regexes.get(field_name+'_index', (None, True))
                            if i >= len(row_name_values[field_name+'_index']):
                                series_index = '0'
                            else:
                                series_index = tidy_field(row_name_values[field_name+'_index'][i], si_regex, si_regex_is_strip)
                            if series_name and series_index:
                                try:
                                    value_text = '%s [%s]'%(series_name, fmt_sidx(series_index))
                                except:
                                    value_text = series_name + ' [0]'
                        elif field_name == 'title':
                            value_text = tidy_title(values[i], regex, regex_is_strip)
                        elif field_name == 'pubdate':
                            # May be able to remove this special case if put a regex
                            value_text = tidy_pubdate(values[i], regex, regex_is_strip)
                        elif col.get('datatype','') == 'bool':
                            value_text = tidy_field(values[i], regex, regex_is_strip)
                            if value_text.lower() in ['true','yes','y','1']:
                                value_text = 'Yes'
                            elif value_text.lower() in ['n/a','undefined','']:
                                value_text = 'n/a'
                            else:
                                value_text = 'No'
                        else:
                            value_text = tidy_field(values[i], regex, regex_is_strip)
                        book[field_name] = value_text
                    # Only append book if has a title
                    if len(book.get('title','')):
                        books.append(book)

            for raw in raw_list:
                root = fromstring(raw)
                if rows_xpath:
                    rows = root.xpath(rows_xpath)
                    for row in rows:
                        row_name_values = {}
                        for field_name, xpath in xpaths.items():
                            field_values = []
                            if xpath:
                                matches = row.xpath(xpath)
                                for match in matches:
                                    field_value = match.strip()
                                    if field_value:
                                        field_values.append(field_value)
                            # If multiple values for a field, append them into a single value for this row.
                            if len(field_values) > 1 and field_name == 'authors':
                                row_name_values[field_name] = [AUTHOR_SEPARATOR.join(field_values)]
                            elif len(field_values) > 1 and field_name == 'tags':
                                row_name_values[field_name] = [TAGS_SEPARATOR.join(field_values)]
                            elif len(field_values) > 1 and field_name in custom_columns and custom_columns[field_name]['is_multiple']:
                                if 'is_names' in custom_columns[field_name]['display'] and custom_columns[field_name]['display']['is_names']:
                                    row_name_values[field_name] = [AUTHOR_SEPARATOR.join(field_values)]
                                else:
                                    row_name_values[field_name] = [TAGS_SEPARATOR.join(field_values)]
                            else:
                                row_name_values[field_name] = field_values
                        append_matches(row_name_values)
                else:
                    row_name_values = {}
                    for field_name, xpath in xpaths.items():
                        if xpath:
                            row_name_values[field_name] = root.xpath(xpath)
                        else:
                            row_name_values[field_name] = []
                    append_matches(row_name_values)

            if self.reverse_list_checkbox.isChecked():
                books.reverse()
            columns = self._get_current_columns()
            self.parent_page.refresh_preview_books(columns, books, cfg.KEY_IMPORT_TYPE_WEB)
        except:
            QApplication.restoreOverrideCursor()
            msg = _('Failed to process page')+':\n' + unicode(sys.exc_info()[1])
            return error_dialog(self.parent_page, _('Failed to process page'), msg, show=True,
                         det_msg=traceback.format_exc())
        else:
            QApplication.restoreOverrideCursor()

    def _get_current_columns(self):
        # Identify which columns the user has configured
        columns = ['title', 'authors']
        for field_name in self.xpath_row_controls.keys():
            if field_name not in columns and field_name != 'rows':
                columns.append(field_name)
        return columns

    def restore_settings(self, library_config):
        self._clear_to_defaults(clear_last=False, add_default_fields=False)
        context = library_config[cfg.KEY_CURRENT].get(cfg.KEY_IMPORT_TYPE_WEB, None)
        if context is None:
            context = copy.deepcopy(cfg.DEFAULT_WEB_SETTING_VALUES)
        self.url_combo.populate_items(library_config[cfg.KEY_WEB_URLS],
                                      context[cfg.KEY_WEB_URL])
        # When populating, have to cater for our "default" rows.
        for data in context[cfg.KEY_WEB_XPATH_DATA]:
            field_name = data[cfg.KEY_WEB_FIELD]
            field_xpath = data[cfg.KEY_WEB_XPATH]
            strip_regex = data.get(cfg.KEY_WEB_REGEX, '')
            is_strip_regex = data.get(cfg.KEY_WEB_REGEX_IS_STRIP, True)
            self._append_xpath_row_controls(field_name, field_xpath, strip_regex, is_strip_regex)
        # Update: add match by identifier {
        # this must be done after restoring csv rows to be able to restore match_by_identifier option
        match_settings = context[cfg.KEY_MATCH_SETTINGS]
        self.mgb.set_match_opts(match_settings)
        #}
        self.reverse_list_checkbox.setChecked(context.get(cfg.KEY_WEB_REVERSE_LIST, False))
        self.encoding_combo.populate_combo(context.get(cfg.KEY_WEB_ENCODING, 'utf-8'))
        self.javascript_checkbox.setChecked(context.get(cfg.KEY_WEB_JAVASCRIPT, False))
        self.delay_spin.setValue(library_config.get(cfg.KEY_JAVASCRIPT_DELAY, cfg.DEFAULT_DELAY))
        last_setting_name = library_config.get(cfg.KEY_LAST_WEB_SETTING, '')
        self.setting_lbl.setText('<b>%s</b>'%last_setting_name)

    def save_settings(self, library_config):
        library_config[cfg.KEY_WEB_URLS] = self.url_combo.get_items_list()
        library_config[cfg.KEY_JAVASCRIPT_DELAY] = int(unicode(self.delay_spin.value()))
        context = library_config[cfg.KEY_CURRENT].get(cfg.KEY_IMPORT_TYPE_WEB, None)
        if context is None:
            context = copy.deepcopy(cfg.DEFAULT_WEB_SETTING_VALUES)
        context[cfg.KEY_WEB_URL] = unicode(self.url_combo.currentText())
        # Update: add match by identifier {
        context[cfg.KEY_MATCH_SETTINGS] = self.mgb.get_match_opts()
        #}
        data_items = []
        for field_name, controls in self.xpath_row_controls.items():
            data = {}
            data[cfg.KEY_WEB_FIELD] = field_name
            data[cfg.KEY_WEB_XPATH] = unicode(controls['ledit'].text()).strip()
            if 'regex' in controls:
                data[cfg.KEY_WEB_REGEX] = controls['regex']
                data[cfg.KEY_WEB_REGEX_IS_STRIP] = controls['regex_is_strip']
            data_items.append(data)
        context[cfg.KEY_WEB_XPATH_DATA] = data_items
        context[cfg.KEY_WEB_REVERSE_LIST] = self.reverse_list_checkbox.isChecked()
        context[cfg.KEY_WEB_JAVASCRIPT] = self.javascript_checkbox.isChecked()
        context[cfg.KEY_WEB_ENCODING] = self.encoding_combo.selected_value()
