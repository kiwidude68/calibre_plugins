from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import copy

try:
    from qt.core import (QWidget, QVBoxLayout, QPushButton, QUrl)
except ImportError:
    from PyQt5.Qt import (QWidget, QVBoxLayout, QPushButton, QUrl)

from calibre.gui2 import dynamic, info_dialog, open_url
from calibre.constants import numeric_version as calibre_version

from calibre_plugins.import_list.common_icons import get_icon
from calibre_plugins.import_list.common_dialogs import KeyboardConfigDialog, PrefsViewerDialog

try:
    load_translations()
except NameError:
    pass

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/Import-List'

KEY_SCHEMA_VERSION = 'schemaVersion'
# Modified: add identifier by match: pump DEFAULT_SCHEMA_VERSION to accomodate new option {
DEFAULT_SCHEMA_VERSION = 1.4
#}

# Per library settings are persisted in the calibre library database.
# For performance reasons I am just using a single parent key of 'Settings'
# so as to minimise the number of writes to the database. The reading of
# settings is done at the time the database is opened so reads are cached.
PREFS_NAMESPACE = 'ImportListPlugin'

PREFS_KEY_SETTINGS = 'settings'
# 'settings': { 'current': { 'importType': 'clipboard',
#                            'clipboard': {...},
#                            'csv': {...},
#                            'web': {...},
#                            'readingList': {...}
#                           },
#               'lastTab':              0,
#               'lastViewType':         '',
#               'lastUserSetting':      '',
#               'lastPredefinedSetting':'',
#               'lastClipboardSetting': '',
#               'lastCSVSetting':       '',
#               'lastWebSetting':       '',
#               'clipboardRegexes':     [],
#               'csvFiles':             [],
#               'webUrls':              [],
#               'lastReadingList':      '',
#               'clearReadingList':     True,
#               'javascriptDelay':      3,
#               'savedSettings': { 'name': { 'importType': 'clipboard',
#                                            'readingList': {} },
#                                            clipboard/csv/web fields },
#                                  ...
#                                },
#               'schemaVersion': x.x
#             }
#
# Settings are stored in a sub dictionary by type

KEY_LAST_TAB = 'lastTab'
KEY_LAST_VIEW_TYPE = 'lastViewType'
KEY_LAST_USER_SETTING = 'lastUserSetting'
KEY_LAST_PREDEFINED_SETTING = 'lastPredefinedSetting'
KEY_CURRENT = 'current'
KEY_CLIPBOARD_REGEXES = 'clipboardRegexes'
KEY_CSV_FILES = 'csvFiles'
KEY_WEB_URLS = 'webUrls'
KEY_SAVED_SETTINGS = 'savedSettings'
KEY_JAVASCRIPT_DELAY = 'javascriptDelay'
KEY_LAST_CLIPBOARD_SETTING = 'lastClipboardSetting'
KEY_LAST_CSV_SETTING = 'lastCSVSetting'
KEY_LAST_WEB_SETTING = 'lastWebSetting'

KEY_IMPORT_TYPE = 'importType'
KEY_MATCH_SETTINGS = 'matchSettings'

KEY_IMPORT_TYPE_CLIPBOARD = 'clipboard'
KEY_CLIPBOARD_REGEX = 'regex'
KEY_CLIPBOARD_TEXT = 'text'
KEY_CLIPBOARD_REVERSE_LIST = 'reverseList'

KEY_IMPORT_TYPE_CSV = 'csv'
KEY_CSV_FILE = 'file'
KEY_CSV_DELIMITER = 'delimiter'
KEY_CSV_SKIP_FIRST = 'skipFirst'
KEY_CSV_UNQUOTE = 'unquote'
KEY_CSV_TIDY = 'tidy'
KEY_CSV_REVERSE_LIST = 'reverseList'
KEY_CSV_DATA = 'columnData'
KEY_CSV_FIELD = 'field'
KEY_CSV_FIELD_INDEX = 'index'
KEY_CSV_ENCODING = 'encoding'
KEY_CSV_COMBO_ENCODINGS = 'comboEncodings'

KEY_IMPORT_TYPE_WEB = 'web'
KEY_WEB_URL = 'url'
KEY_WEB_CATEGORIES = 'categories'
KEY_WEB_XPATH_DATA = 'xpathData'
KEY_WEB_FIELD = 'field'
KEY_WEB_XPATH = 'xpath'
KEY_WEB_REGEX = 'regex'
KEY_WEB_REGEX_IS_STRIP = 'isRegexStrip'
KEY_WEB_REVERSE_LIST = 'reverseList'
KEY_WEB_JAVASCRIPT = 'javascript'
KEY_WEB_ENCODING = 'encoding'

KEY_READING_LIST = 'readingList'
KEY_READING_LIST_NAME = 'name'
KEY_READING_LIST_CLEAR = 'clearList'

DEFAULT_DELAY = 3

DEFAULT_CLIPBOARD_SETTING_VALUES = {
                        KEY_CLIPBOARD_REGEX: '',
                        KEY_CLIPBOARD_TEXT: '',
                        KEY_MATCH_SETTINGS: {'match_method': 'title/author'},
                        KEY_CLIPBOARD_REVERSE_LIST: False
                      }

DEFAULT_CSV_SETTING_VALUES = {
                        KEY_CSV_FILE: '',
                        KEY_CSV_DELIMITER: ',',
                        KEY_CSV_SKIP_FIRST: True,
                        KEY_CSV_UNQUOTE: True,
                        KEY_CSV_TIDY: True,
                        KEY_CSV_REVERSE_LIST: False,
                        KEY_MATCH_SETTINGS: {'match_method': 'title/author'},
                        KEY_CSV_ENCODING: 'utf-8',
                        KEY_CSV_COMBO_ENCODINGS: ['utf-8','utf-16','iso-8859-1'],
                        KEY_CSV_DATA: [
                             { KEY_CSV_FIELD: 'title',   KEY_CSV_FIELD_INDEX: 1 },
                             { KEY_CSV_FIELD: 'authors', KEY_CSV_FIELD_INDEX: 2 } ]
                      }

DEFAULT_WEB_SETTING_VALUES = {
                        KEY_WEB_URL: '',
                        KEY_MATCH_SETTINGS: {'match_method': 'title/author'},
                        KEY_WEB_XPATH_DATA: [
                             { KEY_WEB_FIELD: 'rows',    KEY_WEB_XPATH: '' },
                             { KEY_WEB_FIELD: 'title',   KEY_WEB_XPATH: '', KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: '' },
                             { KEY_WEB_FIELD: 'authors', KEY_WEB_XPATH: '', KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: '' } ],
                        KEY_WEB_REVERSE_LIST: False,
                        KEY_WEB_JAVASCRIPT: False,
                        KEY_WEB_ENCODING: 'utf-8'
                      }

DEFAULT_READING_LIST_VALUES = {
                        KEY_READING_LIST_NAME:  '',
                        KEY_READING_LIST_CLEAR: True
                      }

DEFAULT_LIBRARY_VALUES = {
                          KEY_CURRENT: { KEY_IMPORT_TYPE: KEY_IMPORT_TYPE_CLIPBOARD,
                                         KEY_IMPORT_TYPE_CLIPBOARD: copy.deepcopy(DEFAULT_CLIPBOARD_SETTING_VALUES),
                                         KEY_IMPORT_TYPE_CSV: copy.deepcopy(DEFAULT_CSV_SETTING_VALUES),
                                         KEY_IMPORT_TYPE_WEB: copy.deepcopy(DEFAULT_WEB_SETTING_VALUES),
                                         KEY_READING_LIST: copy.deepcopy(DEFAULT_READING_LIST_VALUES) },
                          KEY_LAST_TAB: 0,
                          KEY_LAST_VIEW_TYPE: 'list',
                          KEY_LAST_USER_SETTING: None,
                          KEY_LAST_PREDEFINED_SETTING: None,
                          KEY_LAST_CLIPBOARD_SETTING: '',
                          KEY_LAST_CSV_SETTING: '',
                          KEY_LAST_WEB_SETTING: '',
                          KEY_CLIPBOARD_REGEXES: [],
                          KEY_CSV_FILES: [],
                          KEY_WEB_URLS: [],
                          KEY_SAVED_SETTINGS: {},
                          KEY_JAVASCRIPT_DELAY: DEFAULT_DELAY,
                          KEY_SCHEMA_VERSION: DEFAULT_SCHEMA_VERSION
                         }

# These are not correct for direct usage and "copying" into a user setting.
# But it makes for more concise reading and maintenance.

# Here I attempt to "normalise" the website configurations, for any configurations that are used
# across more than one setting
if calibre_version < (3,41,0):
    tbody_in_xpath = ''
else:
    tbody_in_xpath = '/tbody'
PREDEFINED_WEB_CONFIGS = {
   'Amazon Best UK': {
            KEY_WEB_XPATH_DATA: [
                { KEY_WEB_FIELD: 'rows',    KEY_WEB_XPATH: '//div[@class="p13n-desktop-grid"]//div[@id="gridItemRoot"]' },
                { KEY_WEB_FIELD: 'title',   KEY_WEB_XPATH: './/a[@class="a-link-normal"]//div[@class="_cDEzb_p13n-sc-css-line-clamp-1_1Fn1y"]/text()',       KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: r':.*|\(.*\)' },
                { KEY_WEB_FIELD: 'authors', KEY_WEB_XPATH: './/div[@class="a-row a-size-small"][1]//text()[normalize-space()]',   KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: '' } ],
            KEY_WEB_REVERSE_LIST: False,
            KEY_WEB_JAVASCRIPT: True,
            KEY_WEB_ENCODING: 'utf-8',
            KEY_MATCH_SETTINGS: {'match_method': 'title/author'}
        },
   'Amazon Best US': {
            KEY_WEB_XPATH_DATA: [
                { KEY_WEB_FIELD: 'rows',    KEY_WEB_XPATH: '//div[@class="p13n-desktop-grid"]//div[@id="gridItemRoot"]' },
                { KEY_WEB_FIELD: 'title',   KEY_WEB_XPATH: './/a[@class="a-link-normal"]//div[@class="_cDEzb_p13n-sc-css-line-clamp-1_1Fn1y"]/text()',       KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: r':.*|\(.*\)' },
                { KEY_WEB_FIELD: 'authors', KEY_WEB_XPATH: './/div[@class="a-row a-size-small"][1]//text()[normalize-space()]',   KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: '' } ],
            KEY_WEB_REVERSE_LIST: False,
            KEY_WEB_JAVASCRIPT: True,
            KEY_WEB_ENCODING: 'utf-8',
            KEY_MATCH_SETTINGS: {'match_method': 'title/author'}
        },
   'Goodreads': {
            KEY_WEB_XPATH_DATA: [
                { KEY_WEB_FIELD: 'rows',         KEY_WEB_XPATH: '//table' + tbody_in_xpath + '/tr/td[3]' },
                { KEY_WEB_FIELD: 'title',        KEY_WEB_XPATH: 'a[@class="bookTitle"]/span/text()',          KEY_WEB_REGEX_IS_STRIP: True,  KEY_WEB_REGEX: r'\\([^\\)]+\\)' },
                { KEY_WEB_FIELD: 'authors',      KEY_WEB_XPATH: 'span/div/a[@class="authorName"]/span/text()',KEY_WEB_REGEX_IS_STRIP: True,  KEY_WEB_REGEX: '' },
                { KEY_WEB_FIELD: 'series',       KEY_WEB_XPATH: 'a[@class="bookTitle"]/span/text()',          KEY_WEB_REGEX_IS_STRIP: False, KEY_WEB_REGEX: r'\\(([^,\\.]+)' },
                { KEY_WEB_FIELD: 'series_index', KEY_WEB_XPATH: 'a[@class="bookTitle"]/span/text()',          KEY_WEB_REGEX_IS_STRIP: False, KEY_WEB_REGEX: r'#([\\d\\.]+)' },
                { KEY_WEB_FIELD: 'identifier:goodreads',   KEY_WEB_XPATH: 'a[@class="bookTitle"]/@href',      KEY_WEB_REGEX_IS_STRIP: False, KEY_WEB_REGEX: r'/book/show/(\\d+)' } ],
            KEY_WEB_REVERSE_LIST: False,
            KEY_WEB_JAVASCRIPT: False,
            KEY_WEB_ENCODING: 'utf-8',
            KEY_MATCH_SETTINGS: {'match_method': 'title/author'}
        },
   'Goodreads Award': {
            KEY_WEB_XPATH_DATA: [
                { KEY_WEB_FIELD: 'rows',         KEY_WEB_XPATH: '//table[@class="tableList"]' + tbody_in_xpath + '/tr/td[2]' },
                { KEY_WEB_FIELD: 'title',        KEY_WEB_XPATH: 'a[@class="bookTitle"]/span/text()',       KEY_WEB_REGEX_IS_STRIP: True,  KEY_WEB_REGEX: r'\\([^\\)]+\\)' },
                { KEY_WEB_FIELD: 'authors',      KEY_WEB_XPATH: 'span/div/a[@class="authorName"]/span/text()', KEY_WEB_REGEX_IS_STRIP: True,  KEY_WEB_REGEX: '' },
                { KEY_WEB_FIELD: 'series',       KEY_WEB_XPATH: 'a[@class="bookTitle"]/span/text()',       KEY_WEB_REGEX_IS_STRIP: False, KEY_WEB_REGEX: r'\\(([^,\\.]+)' },
                { KEY_WEB_FIELD: 'series_index', KEY_WEB_XPATH: 'a[@class="bookTitle"]/span/text()',       KEY_WEB_REGEX_IS_STRIP: False, KEY_WEB_REGEX: r'#([\\d\\.]+)' },
                { KEY_WEB_FIELD: 'identifier:goodreads',   KEY_WEB_XPATH: 'a[@class="bookTitle"]/@href',   KEY_WEB_REGEX_IS_STRIP: False, KEY_WEB_REGEX: r'/book/show/(\\d+)' } ],
            KEY_WEB_REVERSE_LIST: False,
            KEY_WEB_JAVASCRIPT: False,
            KEY_WEB_ENCODING: 'utf-8',
            KEY_MATCH_SETTINGS: {'match_method': 'title/author'}
        },
   'Goodreads Search': {
            KEY_WEB_XPATH_DATA: [
                { KEY_WEB_FIELD: 'rows',         KEY_WEB_XPATH: '//table[@class="tableList"]' + tbody_in_xpath + '/tr/td[2]' },
                { KEY_WEB_FIELD: 'title',        KEY_WEB_XPATH: 'a[@class="bookTitle"]/span/text()',          KEY_WEB_REGEX_IS_STRIP: True,  KEY_WEB_REGEX: r'\\([^\\)]+\\)' },
                { KEY_WEB_FIELD: 'authors',      KEY_WEB_XPATH: 'span/div/a[@class="authorName"]/span/text()',KEY_WEB_REGEX_IS_STRIP: True,  KEY_WEB_REGEX: '' },
                { KEY_WEB_FIELD: 'series',       KEY_WEB_XPATH: 'a[@class="bookTitle"]/span/text()',          KEY_WEB_REGEX_IS_STRIP: False, KEY_WEB_REGEX: r'\\(([^,\\.]+)' },
                { KEY_WEB_FIELD: 'series_index', KEY_WEB_XPATH: 'a[@class="bookTitle"]/span/text()',          KEY_WEB_REGEX_IS_STRIP: False, KEY_WEB_REGEX: r'#([\\d\\.]+)' },
                { KEY_WEB_FIELD: 'identifier:goodreads',   KEY_WEB_XPATH: 'a[@class="bookTitle"]/@href',      KEY_WEB_REGEX_IS_STRIP: False, KEY_WEB_REGEX: r'/book/show/(\\d+)' } ],
            KEY_WEB_REVERSE_LIST: False,
            KEY_WEB_JAVASCRIPT: False,
            KEY_WEB_ENCODING: 'utf-8',
            KEY_MATCH_SETTINGS: {'match_method': 'title/author'}
        },
   'Goodreads Shelf': {
            KEY_WEB_XPATH_DATA: [
                { KEY_WEB_FIELD: 'rows',                KEY_WEB_XPATH: '//div[@class="left"]' },
                { KEY_WEB_FIELD: 'title',               KEY_WEB_XPATH: 'a[@class="bookTitle"]/text()',            KEY_WEB_REGEX_IS_STRIP: True,  KEY_WEB_REGEX: r'\\([^\\)]+\\)' },
                { KEY_WEB_FIELD: 'authors',             KEY_WEB_XPATH: 'span/div/a[@class="authorName"]/span/text()', KEY_WEB_REGEX_IS_STRIP: True,  KEY_WEB_REGEX: '' },
                { KEY_WEB_FIELD: 'series',              KEY_WEB_XPATH: 'a[@class="bookTitle"]/text()',            KEY_WEB_REGEX_IS_STRIP: False, KEY_WEB_REGEX: r'\\(([^,\\.]+)' },
                { KEY_WEB_FIELD: 'series_index',        KEY_WEB_XPATH: 'a[@class="bookTitle"]/text()',            KEY_WEB_REGEX_IS_STRIP: False, KEY_WEB_REGEX: r'#([\\d\\.]+)' },
                { KEY_WEB_FIELD: 'identifier:goodreads',KEY_WEB_XPATH: 'a[@class="bookTitle"]/@href',             KEY_WEB_REGEX_IS_STRIP: False, KEY_WEB_REGEX: r'/book/show/(\\d+)' } ],
            KEY_WEB_REVERSE_LIST: False,
            KEY_WEB_JAVASCRIPT: False,
            KEY_WEB_ENCODING: 'utf-8',
            KEY_MATCH_SETTINGS: {'match_method': 'title/author'}
        },
   'NY Times': {
            KEY_WEB_XPATH_DATA: [
                { KEY_WEB_FIELD: 'rows',    KEY_WEB_XPATH: '//ol/li' },
                { KEY_WEB_FIELD: 'title',   KEY_WEB_XPATH: './/h3/text()',                  KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: r'\(.*' },
                { KEY_WEB_FIELD: 'authors', KEY_WEB_XPATH: './/article/div/a/p[2]/text()',  KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: '' } ],
            KEY_WEB_REVERSE_LIST: False,
            KEY_WEB_JAVASCRIPT: False,
            KEY_WEB_ENCODING: 'utf-8',
            KEY_MATCH_SETTINGS: {'match_method': 'title/author'}
        },
    }

# In the settings below, if a setting requires a configuration that is common to other settings, then
# it will contain a 'webConfig' key indicating the setting details above. We will build this true
# dictionary at run-time, I have just normalised this out as an optimisation for future maintenance
# purposes to reduce the amount of copy/pasting should a website change its appearance.
# If a website is only used once, there is no point in normalising it out so its settings are contained
# inline below and it will not have a 'webConfig' key.
KEY_WEB_CONFIG_NAME = 'webConfig'

CAT_AUTHORS = 'Authors'
CAT_AWARDS = 'Awards'
CAT_BESTSELLERS = 'BestSellers'
CAT_GENRE_FICTION = 'Genre:Fiction'
CAT_GENRE_NONFICTION = 'Genre:NonFiction'
CAT_GENRE_ACTION = 'Genre:Action & Adventure'
CAT_GENRE_CHILDREN = 'Genre:Children & YA'
CAT_GENRE_CONTEMPORARY = 'Genre:Contemporary'
CAT_GENRE_CRIME = 'Genre:Crime & Thrillers'
CAT_GENRE_FANTASY = 'Genre:Fantasy'
CAT_GENRE_HISTORICAL = 'Genre:Historical'
CAT_GENRE_HORROR = 'Genre:Horror'
CAT_GENRE_HUMOUR = 'Genre:Humour'
CAT_GENRE_ROMANCE = 'Genre:Romance'
CAT_GENRE_SCIENCE_FICTION = 'Genre:Science Fiction'
CAT_GENRE_WESTERNS = 'Genre:Westerns'
CAT_GENRE_WOMEN = 'Genre:Women'
CAT_NEW_RELEASES = 'New Releases'
CAT_SOCIAL = 'Social Websites'

PREDEFINED_WEB_SETTINGS_TEMPLATE = {
   'Amazon UK: Bestsellers: Action': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_ACTION],
            KEY_WEB_URL: 'http://www.amazon.co.uk/Bestsellers-Books-Adventure-Stories-Action/zgbs/books/275035/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: Bestsellers: Children': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_CHILDREN],
            KEY_WEB_URL: 'http://www.amazon.co.uk/Bestsellers-Books-Childrens/zgbs/books/69/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: Bestsellers: Contemporary': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_CONTEMPORARY],
            KEY_WEB_URL: 'http://www.amazon.co.uk/Bestsellers-Books-Contemporary-Fiction/zgbs/books/590756/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: Bestsellers: Crime': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_CRIME],
            KEY_WEB_URL: 'http://www.amazon.co.uk/Bestsellers-Books-Crime-Thrillers-Mystery/zgbs/books/72/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: Bestsellers: Fantasy': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_FANTASY],
            KEY_WEB_URL: 'http://www.amazon.co.uk/Bestsellers-Books-Fantasy/zgbs/books/279254/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: Bestsellers: Fiction': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_FICTION],
            KEY_WEB_URL: 'http://www.amazon.co.uk/Bestsellers-Books-Fiction/zgbs/books/62/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: Bestsellers: Historical': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_HISTORICAL],
            KEY_WEB_URL: 'http://www.amazon.co.uk/Bestsellers-Books-Historical-Fiction/zgbs/books/10790401/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: Bestsellers: Horror': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_HORROR],
            KEY_WEB_URL: 'http://www.amazon.co.uk/Bestsellers-Books-Horror/zgbs/books/63/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: Bestsellers: Humour': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_HUMOUR],
            KEY_WEB_URL: 'http://www.amazon.co.uk/Bestsellers-Books-Humorous-Fiction/zgbs/books/426359031/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: Bestsellers: Romance': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_ROMANCE],
            KEY_WEB_URL: 'http://www.amazon.co.uk/Bestsellers-Books-Romance/zgbs/books/88/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: Bestsellers: Science Fiction': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_SCIENCE_FICTION],
            KEY_WEB_URL: 'http://www.amazon.co.uk/Bestsellers-Books-Science-Fiction/zgbs/books/279292/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: Bestsellers: Westerns': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_WESTERNS],
            KEY_WEB_URL: 'http://www.amazon.co.uk/Bestsellers-Books-Westerns/zgbs/books/275065/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: Bestsellers: Women': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_WOMEN],
            KEY_WEB_URL: 'http://www.amazon.co.uk/Bestsellers-Books-Women-Writers-Fiction/zgbs/books/590760/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },

   'Amazon UK: New Releases: Action': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_ACTION],
            KEY_WEB_URL: 'http://www.amazon.co.uk/gp/new-releases/books/275035/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: New Releases: Children': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_CHILDREN],
            KEY_WEB_URL: 'http://www.amazon.co.uk/gp/new-releases/books/69/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: New Releases: Contemporary': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_CONTEMPORARY],
            KEY_WEB_URL: 'http://www.amazon.co.uk/gp/new-releases/books/590756/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: New Releases: Crime': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_CRIME],
            KEY_WEB_URL: 'http://www.amazon.co.uk/gp/new-releases/books/72/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: New Releases: Fantasy': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_FANTASY],
            KEY_WEB_URL: 'http://www.amazon.co.uk/gp/new-releases/books/279254/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: New Releases: Fiction': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_FICTION],
            KEY_WEB_URL: 'http://www.amazon.co.uk/gp/new-releases/books/62/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: New Releases: Historical': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_HISTORICAL],
            KEY_WEB_URL: 'http://www.amazon.co.uk/gp/new-releases/books/10790401/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: New Releases: Horror': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_HORROR],
            KEY_WEB_URL: 'http://www.amazon.co.uk/gp/new-releases/books/63/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: New Releases: Humour': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_HUMOUR],
            KEY_WEB_URL: 'http://www.amazon.co.uk/gp/new-releases/books/426359031/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: New Releases: Romance': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_ROMANCE],
            KEY_WEB_URL: 'http://www.amazon.co.uk/gp/new-releases/books/88/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: New Releases: Science Fiction': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_SCIENCE_FICTION],
            KEY_WEB_URL: 'http://www.amazon.co.uk/gp/new-releases/books/279292/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: New Releases: Westerns': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_WESTERNS],
            KEY_WEB_URL: 'http://www.amazon.co.uk/gp/new-releases/books/275065/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },
   'Amazon UK: New Releases: Women': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_WOMEN],
            KEY_WEB_URL: 'http://www.amazon.co.uk/gp/new-releases/books/590760/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best UK'
        },

   'Amazon USA: Bestsellers: Action': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_ACTION],
            KEY_WEB_URL: 'http://www.amazon.com/Best-Sellers-Books-Action-Adventure-Fiction/zgbs/books/720360/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: Bestsellers: Children': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_CHILDREN],
            KEY_WEB_URL: 'http://www.amazon.com/Best-Sellers-Books-Childrens/zgbs/books/4/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: Bestsellers: Contemporary': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_CONTEMPORARY],
            KEY_WEB_URL: 'http://www.amazon.com/Best-Sellers-Books-Contemporary-Literature-Fiction/zgbs/books/10129/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: Bestsellers: Crime': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_CRIME],
            KEY_WEB_URL: 'http://www.amazon.com/Best-Sellers-Books-Mystery-Thriller-Suspense/zgbs/books/18/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: Bestsellers: Fantasy': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_FANTASY],
            KEY_WEB_URL: 'http://www.amazon.com/Best-Sellers-Books-Fantasy/zgbs/books/16190/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: Bestsellers: Fiction': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_FICTION],
            KEY_WEB_URL: 'http://www.amazon.com/Best-Sellers-Books-Literature-Fiction/zgbs/books/17/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: Bestsellers: Historical': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_HISTORICAL],
            KEY_WEB_URL: 'http://www.amazon.com/Best-Sellers-Books-Historical-Fiction/zgbs/books/10177/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: Bestsellers: Horror': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_HORROR],
            KEY_WEB_URL: 'http://www.amazon.com/Best-Sellers-Books-Horror-Literature-Fiction/zgbs/books/49/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: Bestsellers: Humour': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_HUMOUR],
            KEY_WEB_URL: 'http://www.amazon.com/Best-Sellers-Books-Humorous-Fiction/zgbs/books/4465/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: Bestsellers: Romance': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_ROMANCE],
            KEY_WEB_URL: 'http://www.amazon.com/Best-Sellers-Books-Romance/zgbs/books/23/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: Bestsellers: Science Fiction': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_SCIENCE_FICTION],
            KEY_WEB_URL: 'http://www.amazon.com/Best-Sellers-Books-Science-Fiction/zgbs/books/16272/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: Bestsellers: Westerns': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_WESTERNS],
            KEY_WEB_URL: 'http://www.amazon.com/Best-Sellers-Books-Western-Fiction/zgbs/books/10197/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: Bestsellers: Women': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_WOMEN],
            KEY_WEB_URL: 'http://www.amazon.com/Best-Sellers-Books-Womens-Literature-Fiction/zgbs/books/542654/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: Bestsellers: Young Adult': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_CHILDREN],
            KEY_WEB_URL: 'http://www.amazon.com/Best-Sellers-Books-Teen/zgbs/books/28/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },

   'Amazon USA: New Releases: Action': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_ACTION],
            KEY_WEB_URL: 'http://www.amazon.com/gp/new-releases/books/720360/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: New Releases: Children': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_CHILDREN],
            KEY_WEB_URL: 'http://www.amazon.com/gp/new-releases/books/4/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: New Releases: Contemporary': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_CONTEMPORARY],
            KEY_WEB_URL: 'http://www.amazon.com/gp/new-releases/books/16272/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: New Releases: Crime': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_CRIME],
            KEY_WEB_URL: 'http://www.amazon.com/gp/new-releases/books/18/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: New Releases: Fantasy': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_FANTASY],
            KEY_WEB_URL: 'http://www.amazon.com/gp/new-releases/books/16190/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: New Releases: Fiction': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_FICTION],
            KEY_WEB_URL: 'http://www.amazon.com/gp/new-releases/books/10129/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: New Releases: Historical': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_HISTORICAL],
            KEY_WEB_URL: 'http://www.amazon.com/gp/new-releases/books/10177/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: New Releases: Humour': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_HORROR],
            KEY_WEB_URL: 'http://www.amazon.com/gp/new-releases/books/49/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: New Releases: Humour': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_HUMOUR],
            KEY_WEB_URL: 'http://www.amazon.com/gp/new-releases/books/4465/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: New Releases: Romance': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_ROMANCE],
            KEY_WEB_URL: 'http://www.amazon.com/gp/new-releases/books/23/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: New Releases: Science Fiction': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_SCIENCE_FICTION],
            KEY_WEB_URL: 'http://www.amazon.com/gp/new-releases/books/16272/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: New Releases: Westerns': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_WESTERNS],
            KEY_WEB_URL: 'http://www.amazon.com/gp/new-releases/books/10197/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: New Releases: Women': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_WOMEN],
            KEY_WEB_URL: 'http://www.amazon.com/gp/new-releases/books/542654/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Amazon USA: New Releases: Young Adult': {
            KEY_WEB_CATEGORIES: [CAT_NEW_RELEASES, CAT_GENRE_CHILDREN],
            KEY_WEB_URL: 'http://www.amazon.com/gp/new-releases/books/28/',
            KEY_WEB_CONFIG_NAME: 'Amazon Best US'
        },
   'Fantastic Fiction': {
            KEY_WEB_CATEGORIES: [CAT_AUTHORS],
            KEY_WEB_URL: 'http://www.fantasticfiction.co.uk/a/joe-abercrombie/',
            KEY_WEB_XPATH_DATA: [
                { KEY_WEB_FIELD: 'rows',         KEY_WEB_XPATH: '//div[@class="sectionleft"]' },
                { KEY_WEB_FIELD: 'title',        KEY_WEB_XPATH: 'a[contains(@href,".htm")]/text()',  KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: '' },
                { KEY_WEB_FIELD: 'authors',      KEY_WEB_XPATH: '//h1/text()',     KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: '' },
                { KEY_WEB_FIELD: 'series',       KEY_WEB_XPATH: 'strong/text()',   KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: '' },
                { KEY_WEB_FIELD: 'series_index', KEY_WEB_XPATH: 'text()',          KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: '' },
                { KEY_WEB_FIELD: 'pubdate',      KEY_WEB_XPATH: '''span[@class="year"]//text()[translate(translate(normalize-space(),'(',''),')','')]''',  KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: '' },
                { KEY_WEB_FIELD: 'identifier:ff',KEY_WEB_XPATH: 'a/@href',         KEY_WEB_REGEX_IS_STRIP: False, KEY_WEB_REGEX: '/(.*)\\.htm' } ],
            KEY_WEB_REVERSE_LIST: False,
            KEY_WEB_JAVASCRIPT: False,
            KEY_WEB_ENCODING: 'utf-8',
            KEY_MATCH_SETTINGS: {'match_method': 'title/author'}
        },

   'Goodreads: Awards: Hugo Award': {
            KEY_WEB_CATEGORIES: [CAT_AWARDS],
            KEY_WEB_URL: 'http://www.goodreads.com/award/show/9-hugo-award',
            KEY_WEB_CONFIG_NAME: 'Goodreads Award'
        },
   'Goodreads: Listopia: Best Books Ever': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_SOCIAL],
            KEY_WEB_URL: 'http://www.goodreads.com/list/show/1.Best_Books_Ever',
            KEY_WEB_CONFIG_NAME: 'Goodreads'
        },
   'Goodreads: Most Read': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS],
            KEY_WEB_URL: 'http://www.goodreads.com/book/most_read',
            KEY_WEB_CONFIG_NAME: 'Goodreads'
        },
   'Goodreads: Popular: This Month': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS],
            KEY_WEB_URL: 'http://www.goodreads.com/book/popular_by_date/{date:format_date(yyyy/M)}',
            KEY_WEB_CONFIG_NAME: 'Goodreads'
        },
   'Goodreads: Popular: This Year': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS],
            KEY_WEB_URL: 'http://www.goodreads.com/book/popular_by_date/{date:format_date(yyyy)}/',
            KEY_WEB_CONFIG_NAME: 'Goodreads'
        },
   'Goodreads: Search Result': {
            KEY_WEB_CATEGORIES: [CAT_AUTHORS],
            KEY_WEB_URL: 'http://www.goodreads.com/search?q=',
            KEY_WEB_CONFIG_NAME: 'Goodreads Search'
        },

   'Goodreads: Shelves: Adventure': {
            KEY_WEB_CATEGORIES: [CAT_SOCIAL, CAT_GENRE_ACTION],
            KEY_WEB_URL: 'http://www.goodreads.com/shelf/show/adventure',
            KEY_WEB_CONFIG_NAME: 'Goodreads Shelf'
        },
   'Goodreads: Shelves: Chick-Lit': {
            KEY_WEB_CATEGORIES: [CAT_SOCIAL, CAT_GENRE_WOMEN],
            KEY_WEB_URL: 'http://www.goodreads.com/shelf/show/chick-lit',
            KEY_WEB_CONFIG_NAME: 'Goodreads Shelf'
        },
   'Goodreads: Shelves: Childrens': {
            KEY_WEB_CATEGORIES: [CAT_SOCIAL, CAT_GENRE_CHILDREN],
            KEY_WEB_URL: 'http://www.goodreads.com/shelf/show/childrens',
            KEY_WEB_CONFIG_NAME: 'Goodreads Shelf'
        },
   'Goodreads: Shelves: Contemporary': {
            KEY_WEB_CATEGORIES: [CAT_SOCIAL, CAT_GENRE_CONTEMPORARY],
            KEY_WEB_URL: 'http://www.goodreads.com/shelf/show/contemporary',
            KEY_WEB_CONFIG_NAME: 'Goodreads Shelf'
        },
   'Goodreads: Shelves: Currently Reading': {
            KEY_WEB_CATEGORIES: [CAT_SOCIAL],
            KEY_WEB_URL: 'http://www.goodreads.com/shelf/show/currently-reading',
            KEY_WEB_CONFIG_NAME: 'Goodreads Shelf'
        },
   'Goodreads: Shelves: Fantasy': {
            KEY_WEB_CATEGORIES: [CAT_SOCIAL, CAT_GENRE_FANTASY],
            KEY_WEB_URL: 'http://www.goodreads.com/shelf/show/fantasy',
            KEY_WEB_CONFIG_NAME: 'Goodreads Shelf'
        },
   'Goodreads: Shelves: Historical': {
            KEY_WEB_CATEGORIES: [CAT_SOCIAL, CAT_GENRE_HISTORICAL],
            KEY_WEB_URL: 'http://www.goodreads.com/shelf/show/historical-fiction',
            KEY_WEB_CONFIG_NAME: 'Goodreads Shelf'
        },
   'Goodreads: Shelves: Humor': {
            KEY_WEB_CATEGORIES: [CAT_SOCIAL, CAT_GENRE_FANTASY],
            KEY_WEB_URL: 'http://www.goodreads.com/shelf/show/humor',
            KEY_WEB_CONFIG_NAME: 'Goodreads Shelf'
        },
   'Goodreads: Shelves: Horror': {
            KEY_WEB_CATEGORIES: [CAT_SOCIAL, CAT_GENRE_HORROR],
            KEY_WEB_URL: 'http://www.goodreads.com/shelf/show/horror',
            KEY_WEB_CONFIG_NAME: 'Goodreads Shelf'
        },
   'Goodreads: Shelves: Non-Fiction': {
            KEY_WEB_CATEGORIES: [CAT_SOCIAL, CAT_GENRE_NONFICTION],
            KEY_WEB_URL: 'http://www.goodreads.com/shelf/show/non-fiction',
            KEY_WEB_CONFIG_NAME: 'Goodreads Shelf'
        },
   'Goodreads: Shelves: Romance': {
            KEY_WEB_CATEGORIES: [CAT_SOCIAL, CAT_GENRE_ROMANCE],
            KEY_WEB_URL: 'http://www.goodreads.com/shelf/show/romance',
            KEY_WEB_CONFIG_NAME: 'Goodreads Shelf'
        },
   'Goodreads: Shelves: Science-Fiction': {
            KEY_WEB_CATEGORIES: [CAT_SOCIAL, CAT_GENRE_SCIENCE_FICTION],
            KEY_WEB_URL: 'http://www.goodreads.com/shelf/show/science-fiction',
            KEY_WEB_CONFIG_NAME: 'Goodreads Shelf'
        },
   'Goodreads: Shelves: Thriller': {
            KEY_WEB_CATEGORIES: [CAT_SOCIAL, CAT_GENRE_CRIME],
            KEY_WEB_URL: 'http://www.goodreads.com/shelf/show/thriller',
            KEY_WEB_CONFIG_NAME: 'Goodreads Shelf'
        },
   'Goodreads: Shelves: To Read': {
            KEY_WEB_CATEGORIES: [CAT_SOCIAL],
            KEY_WEB_URL: 'http://www.goodreads.com/shelf/show/to-read',
            KEY_WEB_CONFIG_NAME: 'Goodreads Shelf'
        },
   'Goodreads: Shelves: Western': {
            KEY_WEB_CATEGORIES: [CAT_SOCIAL, CAT_GENRE_WESTERNS],
            KEY_WEB_URL: 'http://www.goodreads.com/shelf/show/western',
            KEY_WEB_CONFIG_NAME: 'Goodreads Shelf'
        },
   'Goodreads: Shelves: Young-Adult': {
            KEY_WEB_CATEGORIES: [CAT_SOCIAL, CAT_GENRE_CHILDREN],
            KEY_WEB_URL: 'http://www.goodreads.com/shelf/show/young-adult',
            KEY_WEB_CONFIG_NAME: 'Goodreads Shelf'
        },

   'NY Times Bestsellers: Fiction eBooks': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_FICTION],
            KEY_WEB_URL: 'http://www.nytimes.com/best-sellers-books/e-book-fiction/list.html',
            KEY_WEB_CONFIG_NAME: 'NY Times'
        },
   'NY Times Bestsellers: NonFiction eBooks': {
            KEY_WEB_CATEGORIES: [CAT_BESTSELLERS, CAT_GENRE_NONFICTION],
            KEY_WEB_URL: 'http://www.nytimes.com/best-sellers-books/e-book-nonfiction/list.html',
            KEY_WEB_CONFIG_NAME: 'NY Times'
        },

   'Wikipedia: Nebula Best Novel': {
            KEY_WEB_CATEGORIES: [CAT_AWARDS],
            KEY_WEB_URL: 'http://en.wikipedia.org/wiki/Nebula_Award_for_Best_Novel',
            KEY_WEB_XPATH_DATA: [
                { KEY_WEB_FIELD: 'rows',    KEY_WEB_XPATH: '//table[@class="sortable wikitable"]/tbody/tr' },
                { KEY_WEB_FIELD: 'title',   KEY_WEB_XPATH: 'td[2]//i//text()[normalize-space()]', KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: '' },
                { KEY_WEB_FIELD: 'authors', KEY_WEB_XPATH: 'td[1]/span[1]/span/span/a/text()',    KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: '' } ],
            KEY_WEB_REVERSE_LIST: False,
            KEY_WEB_JAVASCRIPT: False,
            KEY_WEB_ENCODING: 'utf-8',
            KEY_MATCH_SETTINGS: {'match_method': 'title/author'}
        },
   'Wikipedia: Hugo Best Novel': {
            KEY_WEB_CATEGORIES: [CAT_AWARDS],
            KEY_WEB_URL: 'http://en.wikipedia.org/wiki/Hugo_Award_for_Best_Novel',
            KEY_WEB_XPATH_DATA: [
                { KEY_WEB_FIELD: 'rows',    KEY_WEB_XPATH: '//table[@class="sortable wikitable"]/tbody/tr' },
                { KEY_WEB_FIELD: 'title',   KEY_WEB_XPATH: 'td[2]//i//text()[normalize-space()]', KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: '' },
                { KEY_WEB_FIELD: 'authors', KEY_WEB_XPATH: 'td[1]/span[1]/span/span/a/text()',    KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: '' } ],
            KEY_WEB_REVERSE_LIST: False,
            KEY_WEB_JAVASCRIPT: False,
            KEY_WEB_ENCODING: 'utf-8',
            KEY_MATCH_SETTINGS: {'match_method': 'title/author'}
        },
   }

# Now actually create our real dictionary of settings
PREDEFINED_WEB_SETTINGS = {}

def create_predefined_web_settings():
    for k,v in PREDEFINED_WEB_SETTINGS_TEMPLATE.items():
        PREDEFINED_WEB_SETTINGS[k] = v
        if KEY_WEB_CONFIG_NAME in v:
            for sk, sv in PREDEFINED_WEB_CONFIGS[v[KEY_WEB_CONFIG_NAME]].items():
                PREDEFINED_WEB_SETTINGS[k][sk] = sv
            del v[KEY_WEB_CONFIG_NAME]

create_predefined_web_settings()

KEY_CSV_TITLE_COL = 'titleCol'
KEY_CSV_AUTHOR_COL = 'authorCol'
KEY_CSV_PUBDATE_COL = 'pubdateCol'
KEY_CSV_SERIES_COL = 'seriesCol'
KEY_CSV_SERIES_INDEX_COL = 'seriesIndexCol'

def migrate_library_config_if_required(db, library_config):
    schema_version = library_config.get(KEY_SCHEMA_VERSION, 0)
    if schema_version == DEFAULT_SCHEMA_VERSION:
        return
    # We have changes to be made - mark schema as updated
    library_config[KEY_SCHEMA_VERSION] = DEFAULT_SCHEMA_VERSION

    # Any migration code in future will exist in here.
    if schema_version < 1.1:
        if 'rowXPaths' in library_config:
            del library_config['rowXPaths']
        if 'titleXPaths' in library_config:
            del library_config['titleXPaths']
        if 'authorXPaths' in library_config:
            del library_config['authorXPaths']
        if 'pubdateXPaths' in library_config:
            del library_config['pubdateXPaths']
        if 'seriesXPaths' in library_config:
            del library_config['seriesXPaths']
        if 'seriesIndexXPaths' in library_config:
            del library_config['seriesIndexXPaths']
        if 'stripRegexes' in library_config:
            del library_config['stripRegexes']
        if 'displayColumns' in library_config:
            del library_config['displayColumns']

        def migrate_csv_setting_data(setting):
            data = []
            if 'titleCol' in setting:
                data.append({KEY_CSV_FIELD: 'title', KEY_CSV_FIELD_INDEX: setting['titleCol']})
                del setting['titleCol']
            if 'authorCol' in setting:
                data.append({KEY_CSV_FIELD: 'authors', KEY_CSV_FIELD_INDEX: setting['authorCol']})
                del setting['authorCol']
            if 'pubdateCol' in setting:
                data.append({KEY_CSV_FIELD: 'pubdate', KEY_CSV_FIELD_INDEX: setting['pubdateCol']})
                del setting['pubdateCol']
            if 'seriesCol' in setting:
                data.append({KEY_CSV_FIELD: 'series', KEY_CSV_FIELD_INDEX: setting['seriesCol']})
                del setting['seriesCol']
            if 'seriesIndexCol' in setting:
                data.append({KEY_CSV_FIELD: 'series_index', KEY_CSV_FIELD_INDEX: setting['seriesIndexCol']})
                del setting['seriesIndexCol']
            setting[KEY_CSV_DATA] = data

        def migrate_xpath_setting_data(setting):
            if 'xpathRow' not in setting:
                return
            data = [{KEY_WEB_FIELD: 'rows', KEY_WEB_XPATH: setting['xpathRow']}]
            del setting['xpathRow']
            if 'xpathTitle' in setting:
                data.append({KEY_WEB_FIELD: 'title', KEY_WEB_XPATH: setting['xpathTitle'], KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX: setting['stripRegex']})
                del setting['xpathTitle']
                del setting['stripRegex']
            if 'xpathAuthor' in setting:
                data.append({KEY_WEB_FIELD: 'authors', KEY_WEB_XPATH: setting['xpathAuthor'], KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX:''})
                del setting['xpathAuthor']
            if 'xpathPubdate' in setting:
                data.append({KEY_WEB_FIELD: 'pubdate', KEY_WEB_XPATH: setting['xpathPubdate'], KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX:''})
                del setting['xpathPubdate']
            if 'xpathSeries' in setting:
                data.append({KEY_WEB_FIELD: 'series', KEY_WEB_XPATH: setting['xpathSeries'], KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX:''})
                del setting['xpathSeries']
            if 'xpathSeriesIndex' in setting:
                data.append({KEY_WEB_FIELD: 'series_index', KEY_WEB_XPATH: setting['xpathSeriesIndex'], KEY_WEB_REGEX_IS_STRIP: True, KEY_WEB_REGEX:''})
                del setting['xpathSeriesIndex']
            setting[KEY_WEB_XPATH_DATA] = data

        # Look for any saved web configurations, and migrate them too.
        saved_settings = library_config[KEY_SAVED_SETTINGS]
        for key, saved_setting in saved_settings.items():
            if saved_setting[KEY_IMPORT_TYPE] == KEY_IMPORT_TYPE_CSV:
                migrate_csv_setting_data(saved_setting)
                saved_settings[key] = saved_setting
            elif saved_setting[KEY_IMPORT_TYPE] == KEY_IMPORT_TYPE_WEB:
                migrate_xpath_setting_data(saved_setting)
                saved_settings[key] = saved_setting
        library_config[KEY_SAVED_SETTINGS] = saved_settings

        # Musn't forget the current web setting as well
        current_settings = library_config[KEY_CURRENT]
        current_csv_setting = current_settings[KEY_IMPORT_TYPE_CSV]
        migrate_csv_setting_data(current_csv_setting)
        current_settings[KEY_IMPORT_TYPE_CSV] = current_csv_setting
        current_web_setting = current_settings[KEY_IMPORT_TYPE_WEB]
        migrate_xpath_setting_data(current_web_setting)
        current_settings[KEY_IMPORT_TYPE_WEB] = current_web_setting

    elif schema_version < 1.4:
        contexts = [ library_config[KEY_CURRENT][KEY_IMPORT_TYPE_CSV], library_config[KEY_CURRENT][KEY_IMPORT_TYPE_WEB] ] + \
            [ x for x in library_config[KEY_SAVED_SETTINGS].values() if x[KEY_IMPORT_TYPE] == KEY_IMPORT_TYPE_CSV ]
        for context in contexts:
            old_match_setting = context.get('match_by_identifier', '')
            if old_match_setting != '':
                del context['match_by_identifier']
            if old_match_setting:
                context[KEY_MATCH_SETTINGS] = {
                    'match_method': 'identifier',
                    'id_type': old_match_setting
                }
            else:
                context[KEY_MATCH_SETTINGS] = {
                    'match_method': 'title/author'
                }           

    # Update: add defaults for new keys {
    def get_missing_values_from_defaults(default_settings, settings):
        '''add keys present in default_settings and absent in setting'''
        for k, default_value in default_settings.items():
            try:
                setting_value = settings[k]
                if isinstance(default_value, dict):
                    get_missing_values_from_defaults(default_value, setting_value)
            except KeyError:
                settings[k] = copy.deepcopy(default_value)

    get_missing_values_from_defaults(DEFAULT_LIBRARY_VALUES, library_config)

    for saved_setting in library_config[KEY_SAVED_SETTINGS].values():
        import_type = saved_setting[KEY_IMPORT_TYPE]
        get_missing_values_from_defaults(DEFAULT_LIBRARY_VALUES[KEY_CURRENT][import_type], saved_setting)

    #}        
    set_library_config(db, library_config)


def get_library_config(db):
    library_config = db.prefs.get_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS, copy.deepcopy(DEFAULT_LIBRARY_VALUES))
    migrate_library_config_if_required(db, library_config)
    return library_config

def set_library_config(db, library_config):
    db.prefs.set_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS, library_config)

def get_saved_setting(db, setting_name):
    library_config = get_library_config(db)
    settings = library_config[KEY_SAVED_SETTINGS]
    return settings.get(setting_name, {})

def set_saved_setting(db, setting_name, setting):
    library_config = get_library_config(db)
    settings = library_config[KEY_SAVED_SETTINGS]
    settings[setting_name] = setting
    set_library_config(db, library_config)

def get_setting_names(db):
    library_config = get_library_config(db)
    lists = library_config[KEY_SAVED_SETTINGS]
    return sorted(list(lists.keys()))

def show_help():
    open_url(QUrl(HELP_URL))


class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        self.column_keys = self.plugin_action.gui.current_db.field_metadata.displayable_field_keys()
        self._initialise_controls()

        self.library_config = get_library_config(plugin_action.gui.current_db)

    def _initialise_controls(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        keyboard_shortcuts_button = QPushButton(_('Keyboard shortcuts')+'...', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self._edit_shortcuts)
        layout.addWidget(keyboard_shortcuts_button)

        reset_confirmation_button = QPushButton(_('Reset &confirmation dialogs'), self)
        reset_confirmation_button.setToolTip(_('Reset all show me again dialogs for the Import list plugin'))
        reset_confirmation_button.clicked.connect(self._reset_dialogs)
        layout.addWidget(reset_confirmation_button)

        view_prefs_button = QPushButton(_('&View library preferences')+'...', self)
        view_prefs_button.setToolTip(_('View data stored in the library database for this plugin'))
        view_prefs_button.clicked.connect(self._view_prefs)
        layout.addWidget(view_prefs_button)

        help_button = QPushButton(' '+_('&Help'), self)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(show_help)
        layout.addWidget(help_button)

    def _reset_dialogs(self):
        for key in dynamic.keys():
            if key.startswith('import_list_') and key.endswith('_again') \
                                              and dynamic[key] is False:
                dynamic[key] = True
        info_dialog(self, _('Done'),
                _('Confirmation dialogs have all been reset'), show=True)

    def _edit_shortcuts(self):
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()

    def _view_prefs(self):
        d = PrefsViewerDialog(self.plugin_action.gui, PREFS_NAMESPACE)
        d.exec_()

    def save_settings(self):
        pass
