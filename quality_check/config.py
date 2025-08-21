from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from six import text_type as unicode
from six.moves import range

import copy
from collections import OrderedDict

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

try:
    from qt.core import (QWidget, QVBoxLayout, QLabel, QUrl, QCheckBox, QSize,
                          QGroupBox, QGridLayout, QListWidget, QListWidgetItem,
                          QAbstractItemView, Qt, QPushButton, QSpinBox)
except:
    from PyQt5.Qt import (QWidget, QVBoxLayout, QLabel, QUrl, QCheckBox, QSize,
                          QGroupBox, QGridLayout, QListWidget, QListWidgetItem,
                          QAbstractItemView, Qt, QPushButton, QSpinBox)

from calibre.gui2 import open_url
from calibre.gui2.actions import menu_action_unique_name
from calibre.gui2.complete2 import EditWithComplete
from calibre.utils.config import JSONConfig

from calibre_plugins.quality_check.common_icons import get_icon
from calibre_plugins.quality_check.common_dialogs import KeyboardConfigDialog, PrefsViewerDialog
from calibre_plugins.quality_check.common_widgets import KeyValueComboBox

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/Quality-Check'

KEY_SCHEMA_VERSION = STORE_SCHEMA_VERSION = 'SchemaVersion'
DEFAULT_SCHEMA_VERSION = 1.9

STORE_OPTIONS = 'options'
KEY_MAX_TAGS = 'maxTags'
KEY_MAX_TAG_EXCLUSIONS = 'maxTagExclusions'
KEY_HIDDEN_MENUS = 'hiddenMenus'
KEY_SEARCH_SCOPE = 'searchScope'

SCOPE_LIBRARY = 'Library'
SCOPE_SELECTION = 'Selection'

DEFAULT_STORE_VALUES = {
                           KEY_MAX_TAGS: 5,
                           KEY_MAX_TAG_EXCLUSIONS: [],
                           KEY_HIDDEN_MENUS: [],
                       }

# Per library we store an exclusions map
# 'settings': { 'exclusionsByCheck':  { 'check_epub_jacket':[1,2,3], ... } } }
# Exclusions map is a dictionary keyed by quality check menu of lists of book ids excluded from check
# e.g. { 'check_epub_jacket': [1,2,3] }
PREFS_NAMESPACE = 'QualityCheckPlugin'
PREFS_KEY_SETTINGS = 'settings'
KEY_EXCLUSIONS_BY_CHECK = 'exclusionsByCheck'
KEY_AUTHOR_INITIALS_MODE = 'authorInitialsMode'
AUTHOR_INITIALS_MODES = ['A.B.', 'A. B.', 'A B', 'AB']
KEY_SUPPRESS_FIX_DIALOG = 'suppressFixDialog'

DEFAULT_LIBRARY_VALUES = {
                          KEY_EXCLUSIONS_BY_CHECK: {  },
                         }

PLUGIN_MENUS = OrderedDict([
       ('check_covers',             {'name': _('Check covers')+'...',             'cat':'covers',   'sub_menu': '',                         'group': 0, 'excludable': True,  'image': 'images/check_cover.png',                'tooltip':_('Find books with book covers matching your criteria')}),

       ('check_epub_jacket',        {'name': _('Check having any jacket'),        'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 0, 'excludable': True,  'image': 'images/check_epub_jacket.png',          'tooltip':_('Check for ePub formats which have any calibre jacket')}),
       ('check_epub_legacy_jacket', {'name': _('Check having legacy jacket'),     'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 0, 'excludable': True,  'image': 'images/check_epub_jacket_legacy.png',   'tooltip':_('Check for ePub formats which have a calibre jacket from versions prior to 0.6.51')}),
       ('check_epub_multi_jacket',  {'name': _('Check having multiple jackets'),  'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 0, 'excludable': True,  'image': 'images/check_epub_jacket_multi.png',    'tooltip':_('Check for ePub formats which have multiple jackets')}),
       ('check_epub_no_jacket',     {'name': _('Check missing jacket'),           'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 0, 'excludable': True,  'image': 'images/check_epub_jacket_missing.png',  'tooltip':_('Check for ePub formats which do not have a jacket')}),
       ('check_epub_no_container',  {'name': _('Check missing container.xml'),    'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 1, 'excludable': True,  'image': 'images/check_epub_no_container.png',    'tooltip':_('Check for ePub formats with a missing container.xml indicating an invalid ePub')}),
       ('check_epub_namespaces',    {'name': _('Check invalid namespaces'),       'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 1, 'excludable': True,  'image': 'images/check_epub_namespaces.png',      'tooltip':_('Check for ePub formats with invalid namespaces in the container xml or opf manifest')}),
       ('check_epub_non_dc_meta',   {'name': _('Check non-dc: metadata'),         'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 1, 'excludable': True,  'image': 'images/check_epub_non_dc.png',          'tooltip':_('Check for ePub formats with metadata elements in the opf manifest that are not in the dc: namespace')}),
       ('check_epub_files_missing', {'name': _('Check manifest files missing'),   'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 1, 'excludable': True,  'image': 'images/check_epub_files_missing.png',   'tooltip':_('Check for ePub formats with files missing that are listed in their opf manifest')}),
       ('check_epub_unman_files',   {'name': _('Check unmanifested files'),       'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 1, 'excludable': True,  'image': 'images/check_epub_unmanifested.png',    'tooltip':_('Check for ePub formats with files that are not listed in their opf manifest excluding iTunes/bookmarks')}),
       ('check_epub_unused_css',    {'name': _('Check unused CSS files'),         'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 1, 'excludable': True,  'image': 'images/check_epub_unused_css.png',      'tooltip':_('Check for ePub formats with CSS files that are not referenced from any html pages')}),
       ('check_epub_unused_images', {'name': _('Check unused image files'),       'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 2, 'excludable': True,  'image': 'images/check_epub_unused_image.png',    'tooltip':_('Check for ePub formats with image files that are not referenced from the xhtml pages')}),
       ('check_epub_broken_images', {'name': _('Check broken image links'),       'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 2, 'excludable': True,  'image': 'images/check_epub_unused_image.png',    'tooltip':_('Check for ePub formats with html pages that contain broken links to images')}),
       ('check_epub_itunes',        {'name': _('Check iTunes files'),             'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 3, 'excludable': True,  'image': 'images/check_epub_itunes.png',          'tooltip':_('Check for ePub formats with an iTunesMetadata.plist or iTunesArtwork file')}),
       ('check_epub_bookmark',      {'name': _('Check calibre bookmark files'),   'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 3, 'excludable': True,  'image': 'images/check_epub_bookmarks.png',       'tooltip':_('Check for ePub formats with a calibre bookmarks file')}),
       ('check_epub_os_artifacts',  {'name': _('Check OS artifacts'),             'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 3, 'excludable': True,  'image': 'images/check_epub_os_files.png',        'tooltip':_('Check for ePub formats with OS artifacts of .DS_Store or Thumbs.db')}),
       ('check_epub_inside_epub',   {'name': _('Check ePub inside ePub'),         'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 3, 'excludable': True,  'image': 'images/check_book.png',                 'tooltip':_('Check for ePub formats containing a ePub inside')}),
       ('check_epub_toc_hierarchy', {'name': _('Check NCX TOC hierarchical'),     'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 4, 'excludable': True,  'image': 'images/check_epub_toc_hierarchical.png','tooltip':_('Check for ePub formats with a NCX file TOC which is not flat (i.e. hierarchical)')}),
       ('check_epub_toc_size',      {'name': _('Check NCX TOC with < 3 entries'), 'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 4, 'excludable': True,  'image': 'images/check_epub_toc_size.png',        'tooltip':_('Check for ePub formats with a NCX file TOC with less than 3 entries')}),
       ('check_epub_toc_broken',    {'name': _('Check NCX TOC with broken links'),'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 4, 'excludable': True,  'image': 'images/check_epub_toc_broken.png',      'tooltip':_('Check for ePub formats with a NCX file TOC that contains broken html links')}),
       ('check_epub_guide_broken',  {'name': _('Check <guide> broken links'),     'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 5, 'excludable': True,  'image': 'images/check_epub_guide_broken.png',    'tooltip':_('Check for ePub formats with broken links in the <guide> section of the manifest')}),
       ('check_epub_html_size',     {'name': _('Check oversize html files'),      'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 6, 'excludable': True,  'image': 'images/check_epub_html_size.png',       'tooltip':_('Check for ePub formats with an individual html file size that requires splitting on some devices')}),
       ('check_epub_drm',           {'name': _('Check DRM'),                      'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 7, 'excludable': True,  'image': 'images/check_epub_drm.png',             'tooltip':_('Check for ePub formats with DRM encryption xml files')}),
       ('check_epub_drm_meta',      {'name': _('Check Adobe DRM meta tag'),       'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 7, 'excludable': True,  'image': 'images/check_epub_drm.png',             'tooltip':_('Check for ePub formats that contain html pages with an Adobe DRM meta identifier tag')}),
       ('check_epub_repl_cover',    {'name': _('Check replaceable cover'),        'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 8, 'excludable': True,  'image': 'images/check_epub_cover.png',           'tooltip':_('Check for ePub formats with a cover that can be replaced when exporting or updating metadata with Modify ePub')}),
       ('check_epub_no_repl_cover', {'name': _('Check non-replaceable cover'),    'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 8, 'excludable': True,  'image': 'images/check_epub_no_cover.png',        'tooltip':_('Check for ePub formats with no cover or a cover that cannot be replaced without a calibre conversion')}),
       ('check_epub_svg_cover',     {'name': _('Check calibre SVG cover'),        'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 8, 'excludable': True,  'image': 'images/check_epub_cover.png',           'tooltip':_('Check for ePub formats with a cover that has been inserted by a calibre conversion or Modify ePub and that is SVG')}),
       ('check_epub_no_svg_cover',  {'name': _('Check no calibre SVG cover'),     'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group': 8, 'excludable': True,  'image': 'images/check_epub_no_cover.png',        'tooltip':_('Check for ePub formats that have no calibre cover inserted by a calibre conversion or Modify ePub that is SVG')}),
       ('check_epub_converted',     {'name': _('Check calibre conversion'),       'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group':12, 'excludable': True,  'image': 'images/check_epub_converted.png',       'tooltip':_('Check for ePub formats that have been converted by calibre')}),
       ('check_epub_not_converted', {'name': _('Check not calibre conversion'),   'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group':12, 'excludable': True,  'image': 'images/check_epub_not_converted.png',   'tooltip':_('Check for ePub formats that have not been converted by calibre')}),
       ('check_epub_corrupt_zip',   {'name': _('Check corrupt zip'),              'cat':'epub',     'sub_menu': _('Check ePub Structure'),     'group':12, 'excludable': True,  'image': 'images/check_epub_corrupt_zip.png',     'tooltip':_('Check for ePub zip that is corrupted, may need conversion to fix')}),

       ('check_epub_address',       {'name': _('Check <address> smart-tags'),     'cat':'epub',     'sub_menu': _('Check ePub Style'),     'group': 0, 'excludable': True,  'image': 'images/check_epub_address.png',        'tooltip':_('Check for ePub formats that have <address> elements from a poor conversion with Word smart tags')}),
       ('check_epub_fonts',         {'name': _('Check embedded fonts'),           'cat':'epub',     'sub_menu': _('Check ePub Style'),     'group': 1, 'excludable': True,  'image': 'images/check_epub_fonts.png',          'tooltip':_('Check for ePub formats with embedded fonts')}),
       ('check_epub_font_faces',    {'name': _('Check @font-face'),               'cat':'epub',     'sub_menu': _('Check ePub Style'),     'group': 1, 'excludable': True,  'image': 'images/check_epub_fonts.png',          'tooltip':_('Check for ePub formats with CSS or html files that contain @font-face declarations')}),
       ('check_epub_xpgt',          {'name': _('Check Adobe .xpgt margins'),      'cat':'epub',     'sub_menu': _('Check ePub Style'),     'group': 2, 'excludable': True,  'image': 'images/check_epub_adobe.png',          'tooltip':_('Check for ePub formats with an xpgt file with non-zero margins')}),
       ('check_epub_inline_xpgt',   {'name': _('Check Adobe inline .xpgt links'), 'cat':'epub',     'sub_menu': _('Check ePub Style'),     'group': 2, 'excludable': True,  'image': 'images/check_epub_adobe.png',          'tooltip':_('Check for ePub formats that contain html pages with links to an xpgt file')}),
       ('check_epub_css_justify',   {'name': _('Check CSS non-justified'),        'cat':'epub',     'sub_menu': _('Check ePub Style'),     'group': 3, 'excludable': True,  'image': 'images/check_epub_css_justify.png',    'tooltip':_('Check for ePub formats with CSS files that do not contain a text-align: justify style')}),
       ('check_epub_css_margins',   {'name': _('Check CSS book margins'),         'cat':'epub',     'sub_menu': _('Check ePub Style'),     'group': 3, 'excludable': True,  'image': 'images/check_epub_css_bmargins.png',   'tooltip':_('Check for ePub formats with book level CSS margins conflicting with calibre Preferences')}),
       ('check_epub_css_no_margins',{'name': _('Check CSS no book margins'),      'cat':'epub',     'sub_menu': _('Check ePub Style'),     'group': 3, 'excludable': True,  'image': 'images/check_epub_css_nbmargins.png',  'tooltip':_('Check for ePub formats that do not contain CSS book level margins')}),
       ('check_epub_inline_margins',{'name': _('Check inline @page margins'),     'cat':'epub',     'sub_menu': _('Check ePub Style'),     'group': 3, 'excludable': True,  'image': 'images/check_epub_css_pmargins.png',   'tooltip':_('Check for ePub formats that contain @page CSS margins in each flow')}),
       ('check_epub_javascript',    {'name': _('Check javascript <script>'),      'cat':'epub',     'sub_menu': _('Check ePub Style'),     'group': 4, 'excludable': True,  'image': 'images/check_epub_javascript.png',     'tooltip':_('Check for ePub formats that contain inline javascript <script> blocks')}),
       ('check_epub_smarten_punc',  {'name': _('Check smarten punctuation'),      'cat':'epub',     'sub_menu': _('Check ePub Style'),     'group': 4, 'excludable': True,  'image': 'images/check_epub_smarten_punc.png',   'tooltip':_('Check for ePub formats that contain unsmartened punctuation')}),

       ('check_mobi_missing_ebok',  {'name': _('Check missing EBOK cdetype'),     'cat':'mobi',     'sub_menu': _('Check Mobi'),     'group': 0, 'excludable': True,  'image': 'images/check_mobi_asin.png',           'tooltip':_('Check for MOBI/AZW/AZW3 formats missing the cdetype of EBOK required for a Kindle Fire')}),
       ('check_mobi_missing_asin',  {'name': _('Check missing ASIN identifier'),  'cat':'mobi',     'sub_menu': _('Check Mobi'),     'group': 0, 'excludable': True,  'image': 'images/check_mobi_asin.png',           'tooltip':_('Check for MOBI/AZW/AZW3 formats missing an ASIN in EXTH 113 required for reading on a Kindle Fire')}),
       ('check_mobi_share_disabled',{'name': _('Check Twitter/Facebook disabled'),'cat':'mobi',     'sub_menu': _('Check Mobi'),     'group': 0, 'excludable': True,  'image': 'images/check_mobi_asin.png',           'tooltip':_('Check for MOBI/AZW/AZW3 formats missing an ASIN in both EXTH 113 and EXTH 504 to enable "share" features on Facebook or Twitter')}),
       ('check_mobi_clipping_limit',{'name': _('Check clipping limit'),           'cat':'mobi',     'sub_menu': _('Check Mobi'),     'group': 1, 'excludable': True,  'image': 'images/check_mobi_clipping.png',       'tooltip':_('Check for MOBI/AZW/AZW3 formats that have a clipping limit specified by the publisher in EXTH header 401')}),

       ('check_title_sort',         {'name': _('Check title sort'),               'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 1, 'excludable': True,  'image': 'images/check_book.png',                'tooltip':_('Find books with an invalid title sort value')}),
       ('check_author_sort',        {'name': _('Check author sort'),              'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 1, 'excludable': True,  'image': 'images/check_book.png',                'tooltip':_('Find books with an invalid author sort value')}),
       ('check_isbn',               {'name': _('Check ISBN'),                     'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 1, 'excludable': True,  'image': 'images/check_book.png',                'tooltip':_('Find books with an invalid ISBN')}),
       ('check_pubdate',            {'name': _('Check pubdate'),                  'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 1, 'excludable': True,  'image': 'images/check_book.png',                'tooltip':_('Find books with an invalid pubdate where it is set to the timestamp date')}),
       ('check_dup_isbn',           {'name': _('Check duplicate ISBN'),           'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 2, 'excludable': True,  'image': 'images/check_dup_isbn.png',            'tooltip':_('Find books that have duplicate ISBN values')}),
       ('check_dup_series',         {'name': _('Check duplicate series'),         'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 2, 'excludable': True,  'image': 'series.png',                           'tooltip':_('Find books that have duplicate series values')}),
       ('check_series_gaps',        {'name': _('Check series gaps'),              'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 2, 'excludable': True,  'image': 'series.png',                           'tooltip':_('Find books that have gaps in their series index values')}),
       ('check_series_pubdate',     {'name': _('Check series pubdate order'),     'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 2, 'excludable': True,  'image': 'series.png',                           'tooltip':_('Find books that have gaps in their series index values')}),
       ('check_excess_tags',        {'name': _('Check excess tags'),              'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 3, 'excludable': True,  'image': 'tags.png',                             'tooltip':_('Find books with an excess number of tags')}),
       ('check_html_comments',      {'name': _('Check html comments'),            'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 3, 'excludable': True,  'image': 'images/check_html.png',                'tooltip':_('Find books which have comments html with style formatting embedded')}),
       ('check_no_html_comments',   {'name': _('Check no html comments'),         'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 3, 'excludable': True,  'image': 'images/check_nohtml.png',              'tooltip':_('Find books which have comments with no html tags at all')}),
       ('check_authors_commas',     {'name': _('Check authors with commas'),      'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 4, 'excludable': True,  'image': 'images/check_comma.png',               'tooltip':_('Find authors with commas in their name')}),
       ('check_authors_no_commas',  {'name': _('Check authors missing commas'),   'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 4, 'excludable': True,  'image': 'images/check_nocomma.png',             'tooltip':_('Find authors with no commas in their name')}),
       ('check_authors_case',       {'name': _('Check authors for case'),         'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 4, 'excludable': True,  'image': 'images/check_titlecase.png',           'tooltip':_('Find authors which are all uppercase or all lowercase')}),
       ('check_authors_non_alpha',  {'name': _('Check authors non alphabetic'),   'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 4, 'excludable': True,  'image': 'user_profile.png',                     'tooltip':_('Find authors with non-alphabetic characters such as semi-colons indicating cruft or incorrect separators')}),
       ('check_authors_non_ascii',  {'name': _('Check authors non ascii'),        'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 4, 'excludable': True,  'image': 'user_profile.png',                     'tooltip':_('Find authors with non-ascii names (e.g. with diacritics)')}),
       ('check_authors_initials',   {'name': _('Check authors initials'),         'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 4, 'excludable': True,  'image': 'user_profile.png',                     'tooltip':_('Find authors with initials that do not meet your preferred configuration')}),
       ('check_titles_series',      {'name': _('Check titles with series'),       'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 5, 'excludable': True,  'image': 'images/check_titleseries.png',         'tooltip':_('Find titles with possible series info in their name')}),
       ('check_title_case',         {'name': _('Check titles for title case'),    'cat':'metadata', 'sub_menu': _('Check metadata'), 'group': 5, 'excludable': True,  'image': 'images/check_titlecase.png',           'tooltip':_('Find titles which are candidates to apply the titlecase function to')}),

       ('check_missing_title',      {'name': _('Check missing title'),            'cat':'missing',  'sub_menu': _('Check missing'),  'group': 1, 'excludable': False,  'image': 'images/check_book.png',               'tooltip':_('Find books missing a title')}),
       ('check_missing_author',     {'name': _('Check missing author'),           'cat':'missing',  'sub_menu': _('Check missing'),  'group': 1, 'excludable': False,  'image': 'images/check_book.png',               'tooltip':_('Find books missing authors')}),
       ('check_missing_isbn',       {'name': _('Check missing ISBN'),             'cat':'missing',  'sub_menu': _('Check missing'),  'group': 1, 'excludable': False,  'image': 'images/check_book.png',               'tooltip':_('Find books missing an ISBN identifier')}),
       ('check_missing_pubdate',    {'name': _('Check missing pubdate'),          'cat':'missing',  'sub_menu': _('Check missing'),  'group': 1, 'excludable': False,  'image': 'images/check_book.png',               'tooltip':_('Find books missing published date')}),
       ('check_missing_publisher',  {'name': _('Check missing publisher'),        'cat':'missing',  'sub_menu': _('Check missing'),  'group': 1, 'excludable': False,  'image': 'images/check_book.png',               'tooltip':_('Find books missing publisher')}),
       ('check_missing_tags',       {'name': _('Check missing tags'),             'cat':'missing',  'sub_menu': _('Check missing'),  'group': 1, 'excludable': False,  'image': 'images/check_book.png',               'tooltip':_('Find books missing tags')}),
       ('check_missing_rating',     {'name': _('Check missing rating'),           'cat':'missing',  'sub_menu': _('Check missing'),  'group': 1, 'excludable': False,  'image': 'images/check_book.png',               'tooltip':_('Find books missing rating')}),
       ('check_missing_comments',   {'name': _('Check missing comments'),         'cat':'missing',  'sub_menu': _('Check missing'),  'group': 1, 'excludable': False,  'image': 'images/check_book.png',               'tooltip':_('Find books missing comments')}),
       ('check_missing_languages',  {'name': _('Check missing languages'),        'cat':'missing',  'sub_menu': _('Check missing'),  'group': 1, 'excludable': False,  'image': 'images/check_book.png',               'tooltip':_('Find books missing languages')}),
       ('check_missing_cover',      {'name': _('Check missing cover'),            'cat':'missing',  'sub_menu': _('Check missing'),  'group': 1, 'excludable': False,  'image': 'images/check_book.png',               'tooltip':_('Find books missing a cover')}),
       ('check_missing_formats',    {'name': _('Check missing formats'),          'cat':'missing',  'sub_menu': _('Check missing'),  'group': 1, 'excludable': False,  'image': 'images/check_book.png',               'tooltip':_('Find books missing formats')}),

       ('search_epub',              {'name': _('Search ePubs')+'...',             'cat':'epub',     'sub_menu': '',               'group': 0, 'excludable': False, 'image': 'search.png',                           'tooltip':_('Find ePub books with text matching your own regular expression')}),
       ])


PLUGIN_FIX_MENUS = OrderedDict([
       ('fix_swap_author_names',    {'name': _('Swap author FN LN <-> LN,FN'),   'cat':'fix',  'group': 0, 'image': 'images/check_comma.png',           'tooltip':_('For the selected book(s) swap author names between FN LN and LN, FN formats')}),
       ('fix_author_initials',      {'name': _('Reformat author initials'),      'cat':'fix',  'group': 0, 'image': 'user_profile.png',                 'tooltip':_('For the selected book(s) reformat the author initials to your configured preference')}),
       ('fix_author_ascii',         {'name': _('Rename author to ascii'),        'cat':'fix',  'group': 0, 'image': 'user_profile.png',                 'tooltip':_('For the selected book(s) rename the author to remove any accents and diacritics characters')}),
       ('fix_title_sort',           {'name': _('Set title sort'),                'cat':'fix',  'group': 0, 'image': 'images/check_book.png',            'tooltip':_('For the selected book(s) replace the title sort with a value based on your tweak preference')}),
       ('check_fix_book_size',      {'name': _('Check and repair book sizes'),   'cat':'fix',  'group': 1, 'image': 'images/check_file_size.png',       'tooltip':_('Check and update file sizes for your books')}),
       ('check_fix_book_paths',     {'name': _('Check and rename book paths'),   'cat':'fix',  'group': 1, 'image': 'images/fix_rename.png',            'tooltip':_('Ensure book paths include commas if appropriate')}),
       ('cleanup_opf_files',        {'name': _('Cleanup .opf files/folders'),    'cat':'fix',  'group': 2, 'image': 'images/fix_cleanup_folders.png',   'tooltip':_('Delete orphaned opf/jpg files and remove empty folders')}),
       ('fix_mobi_asin',            {'name': _('Fix ASIN for Kindle Fire'),      'cat':'fix',  'group': 3, 'image': 'images/fix_mobi_asin.png',         'tooltip':_('For MOBI/AZW/AZW3 formats, assign the current amazon identifier (uuid if not present) as an ASIN to EXTH 113 and 504 fields')}),
       ('fix_normalize_fields',     {'name': _('Normalize the fields'),          'cat':'fix',  'group': 4, 'image': 'images/fix_normalize_fields.png',  'tooltip':_('Normalize the text fields by using their canonical form defined by the Unicode Standard, aka merge and reorders diacritics. Can result to unduplicate some values.')}),
       ('fix_normalize_notes',      {'name': _('Normalize the notes'),           'cat':'fix',  'group': 4, 'image': 'images/fix_normalize_notes.png',   'tooltip':_('Normalize the category notes by using their canonical form defined by the Unicode Standard, aka merge and reorders diacritics.')}),
       ])

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Quality Check')

# Set defaults
plugin_prefs.defaults[STORE_OPTIONS] = DEFAULT_STORE_VALUES


def migrate_library_config_if_required(db, library_config):
    schema_version = library_config.get(KEY_SCHEMA_VERSION, 0)
    if schema_version == DEFAULT_SCHEMA_VERSION:
        return
    # We have changes to be made - mark schema as updated
    library_config[KEY_SCHEMA_VERSION] = DEFAULT_SCHEMA_VERSION

    # Any migration code in future will exist in here.
    if schema_version < 1.9:
        # Make sure that any exclusions for checks which aren't allowed them are removed.
        exclusions_map = library_config.get(KEY_EXCLUSIONS_BY_CHECK, {})
        for excl_key in list(exclusions_map.keys()):
            if excl_key.startswith('check_missing_'):
                del exclusions_map[excl_key]

    set_library_config(db, library_config)


def get_library_config(db):
    library_id = db.library_id
    library_config = None
    # Check whether this is a reading list needing to be migrated from json into database
    if 'Libraries' in plugin_prefs:
        libraries = plugin_prefs['Libraries']
        if library_id in libraries:
            # We will migrate this below
            library_config = libraries[library_id]
            # Cleanup from json file so we don't ever do this again
            del libraries[library_id]
            if len(libraries) == 0:
                # We have migrated the last library for this user
                del plugin_prefs['Libraries']
            else:
                plugin_prefs['Libraries'] = libraries

    if library_config is None:
        library_config = db.prefs.get_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS,
                                                 copy.deepcopy(DEFAULT_LIBRARY_VALUES))
    migrate_library_config_if_required(db, library_config)
    return library_config

def set_library_config(db, library_config):
    db.prefs.set_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS, library_config)

def get_excluded_books(db, menu_key):
    library_config = get_library_config(db)
    exclusions_map = library_config[KEY_EXCLUSIONS_BY_CHECK]
    exclusions = exclusions_map.get(menu_key, [])
    return exclusions

def get_valid_excluded_books(db, menu_key):
    book_ids = get_excluded_books(db, menu_key)
    valid_book_ids = [i for i in book_ids if db.data.has_id(i)]
    if len(book_ids) != len(valid_book_ids):
        set_excluded_books(db, menu_key, book_ids)
    return valid_book_ids

def set_excluded_books(db, menu_key, book_ids):
    library_config = get_library_config(db)
    exclusions_map = library_config[KEY_EXCLUSIONS_BY_CHECK]
    exclusions_map[menu_key] = book_ids
    set_library_config(db, library_config)

def show_help():
    open_url(QUrl(HELP_URL))


class VisibleMenuListWidget(QListWidget):
    def __init__(self, parent=None):
        QListWidget.__init__(self, parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setIconSize(QSize(16,16))
        self.populate()

    def populate(self):
        self.clear()
        hidden_prefs = plugin_prefs[STORE_OPTIONS].get(KEY_HIDDEN_MENUS, [])
        for key, value in PLUGIN_MENUS.items():
            name = value['name']
            sub_menu = value['sub_menu']
            if sub_menu:
                name = sub_menu + ' -> ' + name
            item = QListWidgetItem(name, self)
            item.setIcon(get_icon(value['image']))
            item.setData(Qt.UserRole, key)
            if key in hidden_prefs:
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)
            self.addItem(item)

    def get_hidden_menus(self):
        hidden_menus = []
        for x in range(self.count()):
            item = self.item(x)
            if item.checkState() == Qt.Unchecked:
                key = unicode(item.data(Qt.UserRole)).strip()
                hidden_menus.append(key)
        return hidden_menus


class ConfigWidget(QWidget):

    def __init__(self, plugin_action, all_tags):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        c = plugin_prefs[STORE_OPTIONS]
        tags_groupbox = QGroupBox(_('Check excess tags options'))
        layout.addWidget(tags_groupbox)
        tags_layout = QGridLayout()
        tags_groupbox.setLayout(tags_layout)

        max_label = QLabel(_('Maximum tags:'), self)
        max_label.setToolTip(_('Books with more than this value will be displayed'))
        tags_layout.addWidget(max_label, 0, 0, 1, 1)
        self.max_tags_spin = QSpinBox(self)
        self.max_tags_spin.setMinimum(0)
        self.max_tags_spin.setMaximum(100)
        self.max_tags_spin.setProperty('value', c.get(KEY_MAX_TAGS, 5))
        tags_layout.addWidget(self.max_tags_spin, 0, 1, 1, 1)

        exclude_label = QLabel(_('Exclude tags:'), self)
        exclude_label.setToolTip(_('Exclude these tags from when counting the tags for each book'))
        tags_layout.addWidget(exclude_label, 1, 0, 1, 1)
        self.exclude_tags = EditWithComplete(self)
        self.exclude_tags.set_add_separator(True)
        self.exclude_tags.update_items_cache(all_tags)
        self.exclude_tags.setText(', '.join(c.get(KEY_MAX_TAG_EXCLUSIONS, [])))
        tags_layout.addWidget(self.exclude_tags, 1, 1, 1, 2)
        tags_layout.setColumnStretch(2, 1)

        other_groupbox = QGroupBox(_('Other options'))
        layout.addWidget(other_groupbox)
        other_layout = QGridLayout()
        other_groupbox.setLayout(other_layout)

        initials_label = QLabel(_('Author initials format:'), self)
        initials_label.setToolTip(_('For use with the "Check Author initials" option, set your preferred format'))
        other_layout.addWidget(initials_label, 0, 0, 1, 1)
        initials_map = OrderedDict((k,k) for k in AUTHOR_INITIALS_MODES)
        initials_mode = c.get(KEY_AUTHOR_INITIALS_MODE, AUTHOR_INITIALS_MODES[0])
        self.initials_combo = KeyValueComboBox(self, initials_map, initials_mode)
        other_layout.addWidget(self.initials_combo, 0, 1, 1, 1)
 
        self.suppress_dialog_checkbox = QCheckBox(_('Suppress Fix summary dialogs'), self)
        self.suppress_dialog_checkbox.setToolTip(_('Uncheck this option if you do not want interactive dialogs to appear summarising the operation'))
        if c.get(KEY_SUPPRESS_FIX_DIALOG, False):
            self.suppress_dialog_checkbox.setCheckState(Qt.Checked)
        other_layout.addWidget(self.suppress_dialog_checkbox, 1, 0, 1, 2)
        other_layout.setColumnStretch(2, 1)

        menus_groupbox = QGroupBox(_('Visible menus'))
        layout.addWidget(menus_groupbox)
        menus_layout = QVBoxLayout()
        menus_groupbox.setLayout(menus_layout)
        self.visible_menus_list = VisibleMenuListWidget(self)
        menus_layout.addWidget(self.visible_menus_list)
        self.orig_hidden_menus = self.visible_menus_list.get_hidden_menus()

        keyboard_shortcuts_button = QPushButton(_('Keyboard shortcuts')+'...', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        layout.addWidget(keyboard_shortcuts_button)

        view_prefs_button = QPushButton(_('&View library preferences')+'...', self)
        view_prefs_button.setToolTip(_('View data stored in the library database for this plugin'))
        view_prefs_button.clicked.connect(self.view_prefs)
        layout.addWidget(view_prefs_button)

        help_button = QPushButton(' '+_('&Help'), self)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(show_help)
        layout.addWidget(help_button)

    def save_settings(self):
        new_prefs = {}
        new_prefs[KEY_MAX_TAGS] = int(unicode(self.max_tags_spin.value()))
        exclude_tag_text = unicode(self.exclude_tags.text()).strip()
        if exclude_tag_text.endswith(','):
            exclude_tag_text = exclude_tag_text[:-1]
        new_prefs[KEY_MAX_TAG_EXCLUSIONS] = [t.strip() for t in exclude_tag_text.split(',')]
        new_prefs[KEY_AUTHOR_INITIALS_MODE] = self.initials_combo.selected_key()
        new_prefs[KEY_SUPPRESS_FIX_DIALOG] = self.suppress_dialog_checkbox.checkState() == Qt.Checked
        new_prefs[KEY_SEARCH_SCOPE] = plugin_prefs[STORE_OPTIONS].get(KEY_SEARCH_SCOPE, SCOPE_LIBRARY)

        new_prefs[KEY_HIDDEN_MENUS] = self.visible_menus_list.get_hidden_menus()
        # For each menu that was visible but now is not, we need to unregister any
        # keyboard shortcut associated with that action.
        menus_changed = False
        kb = self.plugin_action.gui.keyboard
        for menu_key in new_prefs[KEY_HIDDEN_MENUS]:
            if menu_key not in self.orig_hidden_menus:
                unique_name = menu_action_unique_name(self.plugin_action, menu_key)
                if unique_name in kb.shortcuts:
                    kb.unregister_shortcut(unique_name)
                    menus_changed = True
        if menus_changed:
            self.plugin_action.gui.keyboard.finalize()

        plugin_prefs[STORE_OPTIONS] = new_prefs

    def edit_shortcuts(self):
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()

    def view_prefs(self):
        d = PrefsViewerDialog(self.plugin_action.gui, PREFS_NAMESPACE)
        d.exec_()
