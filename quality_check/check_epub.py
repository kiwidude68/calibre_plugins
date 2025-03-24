from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from polyglot.builtins import unicode_type, is_py3
from six import text_type as unicode
from six.moves.urllib.parse import unquote as urlunquote
import traceback, os, posixpath, six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error, re
try:
    from cgi import escape as esc
except:
    from html import escape as esc

from lxml import etree

from calibre import guess_type
from calibre.gui2 import error_dialog
from calibre.ebooks.chardet import xml_to_unicode
from calibre.ebooks.conversion.preprocess import HTMLPreProcessor
from calibre.ebooks.metadata.epub import Encryption
from calibre.ebooks.oeb.base import XPath
from calibre.ebooks.oeb.parse_utils import RECOVER_PARSER, NotHTML, parse_html
from calibre.utils.zipfile import ZipFile, BadZipfile

from calibre_plugins.quality_check.check_base import BaseCheck
from calibre_plugins.quality_check.dialogs import SearchEpubDialog
from calibre_plugins.quality_check.helpers import get_title_authors_text

META_INF = {
        'container.xml' : True,
        'manifest.xml' : False,
        'encryption.xml' : False,
        'metadata.xml' : False,
        'signatures.xml' : False,
        'rights.xml' : False,
}

ITUNES_FILES = ['iTunesMetadata.plist', 'iTunesArtwork']
BOOKMARKS_FILES = ['META-INF/calibre_bookmarks.txt']
OS_FILES = ['.DS_Store', 'thumbs.db']
ALL_ARTIFACTS = ITUNES_FILES + BOOKMARKS_FILES + OS_FILES

IMAGE_FILES = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp']
FONT_FILES  = ['.otf', '.ttf']
CSS_FILES   = ['.xpgt', '.css']
OPF_FILES   = ['.opf']
NCX_FILES   = ['.ncx']
JAVASCRIPT_FILES = ['.js']
CRAP_FILES = ['.thmx','.plist']
EPUB_FILES = ['.epub']
NON_HTML_FILES = IMAGE_FILES + FONT_FILES + CSS_FILES + OPF_FILES + NCX_FILES + JAVASCRIPT_FILES + CRAP_FILES + EPUB_FILES

NCX_NS = 'http://www.daisy.org/z3986/2005/ncx/'

ENCRYPTION_PATH = 'META-INF/encryption.xml'

RE_HTML_BODY = re.compile(u'<body[^>]*>(.*)</body>', re.UNICODE | re.DOTALL)
RE_STRIP_MARKUP = re.compile(u'<[^>]+>', re.UNICODE)
RE_WHITESPACE = re.compile(r'\s+', re.UNICODE | re.DOTALL)

OCF_NS = 'urn:oasis:names:tc:opendocument:xmlns:container'
OPF_NS = 'http://www.idpf.org/2007/opf'

class InvalidEpub(ValueError):
    pass

class EpubCheck(BaseCheck):
    '''
    All checks related to working with ePub formats.
    '''
    def __init__(self, gui):
        BaseCheck.__init__(self, gui, 'formats:epub')
        self.html_preprocessor = HTMLPreProcessor()
        self.input_encoding = 'utf-8'

    def perform_check(self, menu_key):
        if menu_key == 'check_epub_jacket':
            self.check_epub_jacket(check_has_jacket=True)
        elif menu_key == 'check_epub_legacy_jacket':
            self.check_epub_jacket(check_has_jacket=True, check_legacy_only=True)
        elif menu_key == 'check_epub_multi_jacket':
            self.check_epub_multiple_jacket()
        elif menu_key == 'check_epub_no_jacket':
            self.check_epub_jacket(check_has_jacket=False)

        elif menu_key == 'check_epub_namespaces':
            self.check_epub_namespaces()
        elif menu_key == 'check_epub_non_dc_meta':
            self.check_epub_non_dc_metadata()
        elif menu_key == 'check_epub_files_missing':
            self.check_epub_opf_files_missing()
        elif menu_key == 'check_epub_xpgt':
            self.check_epub_xpgt_margins()
        elif menu_key == 'check_epub_inline_xpgt':
            self.check_epub_inline_xpgt_links()
        elif menu_key == 'check_epub_unman_files':
            self.check_epub_unmanifested_files()
        elif menu_key == 'check_epub_unused_css':
            self.check_epub_unused_css_files()

        elif menu_key == 'check_epub_unused_images':
            self.check_epub_unused_images()
        elif menu_key == 'check_epub_broken_images':
            self.check_epub_broken_image_links()

        elif menu_key == 'check_epub_itunes':
            self.check_epub_files(ITUNES_FILES, _('iTunes files'), 'epub_itunes', show_log=True)
        elif menu_key == 'check_epub_bookmark':
            self.check_epub_files(BOOKMARKS_FILES, _('calibre bookmarks'), 'epub_calibre_bookmarks', show_log=False)
        elif menu_key == 'check_epub_os_artifacts':
            self.check_epub_files(OS_FILES, _('OS artifacts'), 'epub_os_artifacts', show_log=True)

        elif menu_key == 'check_epub_repl_cover':
            self.check_epub_replaceable_cover(check_has_cover=True)
        elif menu_key == 'check_epub_no_repl_cover':
            self.check_epub_replaceable_cover(check_has_cover=False)
        elif menu_key == 'check_epub_svg_cover':
            self.check_epub_calibre_svg_cover(check_has_svg_cover=True)
        elif menu_key == 'check_epub_no_svg_cover':
            self.check_epub_calibre_svg_cover(check_has_svg_cover=False)

        elif menu_key == 'check_epub_toc_hierarchy':
            self.check_epub_toc_hierarchical()
        elif menu_key == 'check_epub_toc_size':
            self.check_epub_toc_size()
        elif menu_key == 'check_epub_toc_broken':
            self.check_epub_toc_broken_links()

        elif menu_key == 'check_epub_guide_broken':
            self.check_epub_guide_broken_links()

        elif menu_key == 'check_epub_html_size':
            self.check_epub_html_size()

        elif menu_key == 'check_epub_drm':
            self.check_epub_drm()
        elif menu_key == 'check_epub_drm_meta':
            self.check_epub_drm_meta()

        elif menu_key == 'check_epub_converted':
            self.check_epub_conversion(check_converted=True)
        elif menu_key == 'check_epub_not_converted':
            self.check_epub_conversion(check_converted=False)
        elif menu_key == 'check_epub_corrupt_zip':
            self.check_epub_corrupt_zip()

        elif menu_key == 'check_epub_no_container':
            self.check_epub_no_container()

        elif menu_key == 'check_epub_address':
            self.check_epub_address()

        elif menu_key == 'check_epub_fonts':
            self.check_epub_embedded_fonts()
        elif menu_key == 'check_epub_font_faces':
            self.check_epub_font_faces()

        elif menu_key == 'check_epub_css_justify':
            self.check_epub_css_justify()
        elif menu_key == 'check_epub_css_margins':
            self.check_epub_css_margins()
        elif menu_key == 'check_epub_css_no_margins':
            self.check_epub_css_no_margins()
        elif menu_key == 'check_epub_inline_margins':
            self.check_epub_inline_margins()

        elif menu_key == 'check_epub_javascript':
            self.check_epub_javascript()
        elif menu_key == 'check_epub_smarten_punc':
            self.check_epub_smarten_punctuation()

        elif menu_key == 'check_epub_inside_epub':
            self.check_epub_inside_epub()

        elif menu_key == 'search_epub':
            self.search_epub()

        else:
            return error_dialog(self.gui, _('Quality Check failed'),
                                _('Unknown menu key for %s of \'%s\'')%('EpubCheck', menu_key),
                                show=True, show_copy_button=False)

    def zf_read(self, zf, name):
        data = zf.read(name)
        if is_py3:
            return data.decode('utf-8', errors='replace')
        return data

    def search_epub(self):
        '''
        Search epubs for text matching the user's criteria
        '''
        d = SearchEpubDialog(self.gui)
        d.exec_()
        if d.result() != d.Accepted:
            return

        self.search_opts = d.search_options
        re_options = re.UNICODE + re.DOTALL
        if self.search_opts['ignore_case']:
            re_options |= re.IGNORECASE
        self.log('*** Searching for expression: <span style="color:blue"><b>%s</b></span> ***' % esc(self.search_opts['previous_finds'][0]))
        self.search_expression = re.compile(self.search_opts['previous_finds'][0], re_options)

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False

            def search_for_match(text, show_all_matches):
                matches = []
                text = text.replace('&nbsp;', ' ')
                for m in self.search_expression.finditer(text):
                    # Get the previous and following characters
                    CHARS = 25
                    prefix = suffix = ''
                    start = m.start()
                    end = start + len(m.group())
                    if start >= CHARS:
                        prefix = text[start-CHARS:start]
                    else:
                        prefix = text[0:start]
                    if end + CHARS <= len(text):
                        suffix = text[end:end+CHARS]
                    else:
                        suffix = text[end:len(text)]
                    prefix = RE_WHITESPACE.sub(' ', prefix)
                    suffix = RE_WHITESPACE.sub(' ', suffix)
                    matches.append('\t<span style="color:darkgray">%s</span> <span style="color:green">...%s<span style="color:orange"><b>%s</b></span>%s...</span>'%(
                                resource_name, esc(prefix), esc(m.group()), esc(suffix)))
                    if not show_all_matches:
                        break
                if matches:
                    log_lines.extend(matches)
                return bool(matches)

            try:
                show_all_matches = self.search_opts['show_all_matches']
                with ZipFile(path_to_book, 'r') as zf:
                    contents = zf.namelist()
                    log_lines = []
                    for resource_name in contents:
                        extension = resource_name[resource_name.rfind('.'):].lower()
                        check_file = extract_body_text = False
                        if extension not in NON_HTML_FILES:
                            extract_body_text = self.search_opts['scope_plaintext']
                            check_file = self.search_opts['scope_html'] or extract_body_text
                        elif extension in CSS_FILES:
                            check_file = self.search_opts['scope_css']
                        elif extension in OPF_FILES:
                            check_file = self.search_opts['scope_opf']
                        elif extension in NCX_FILES:
                            check_file = self.search_opts['scope_ncx']
                        if check_file:
                            content = zf.read(resource_name).decode('utf-8',errors='replace')
                            if extract_body_text:
                                content = self._extract_body_text(content)
                            if search_for_match(content, show_all_matches):
                                if not show_all_matches:
                                    break
                        if self.search_opts['scope_zip']:
                            filename = os.path.basename(resource_name)
                            if search_for_match(filename, show_all_matches):
                                if not show_all_matches:
                                    break
                    if log_lines:
                        if show_all_matches:
                            self.log('%s '%len(log_lines) + _('Matches in book: <b>%s</b>')%get_title_authors_text(db, book_id))
                        else:
                            self.log(_('First match in book: <b>%s</b>')%get_title_authors_text(db, book_id))
                        for log_line in log_lines:
                            self.log(log_line)
                        return True
                return False

            except InvalidEpub as e:
                self.log.error(_('Invalid epub:'), e)
                return False
            except:
                self.log.error(_('ERROR parsing book: '), path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books have your search text'),
                             marked_text='epub_search_text',
                             status_msg_type=_('ePub books for search text'))


    def check_epub_jacket(self, check_has_jacket, check_legacy_only=False):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error(_('ERROR: EPUB format is missing: '), get_title_authors_text(db, book_id))
                return not check_has_jacket
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    for resource_name in self._manifest_worthy_names(zf):
                        if 'jacket' in resource_name and resource_name.endswith('.xhtml'):
                            html = zf.read(resource_name).decode('utf-8')
                            if not check_legacy_only and self._is_current_jacket(html):
                                return check_has_jacket
                            if self._is_legacy_jacket(html):
                                return check_has_jacket
                return not check_has_jacket

            except InvalidEpub as e:
                self.log.error(_('Invalid epub:'), e)
                return not check_has_jacket
            except:
                self.log.error(_('ERROR parsing book: '), path_to_book)
                self.log(traceback.format_exc())
                return not check_has_jacket

        if check_legacy_only:
            msg = _('No searched ePub books have legacy jackets')
            marked_text = 'epub_has_legacy_jacket'
        elif check_has_jacket:
            msg = _('No searched ePub books have jackets')
            marked_text = 'epub_has_jacket'
        else:
            msg = _('All searched ePub books have jackets')
            marked_text = 'epub_missing_jacket'
        self.check_all_files(evaluate_book,
                             status_msg_type=_('ePub books for jackets'),
                             no_match_msg=msg, marked_text=marked_text)


    def check_epub_multiple_jacket(self):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error(_('ERROR: EPUB format is missing: '), get_title_authors_text(db, book_id))
                return False
            try:
                jacket_count = 0
                with ZipFile(path_to_book, 'r') as zf:
                    for resource_name in self._manifest_worthy_names(zf):
                        if 'jacket' in resource_name and resource_name.endswith('.xhtml'):
                            html = self.zf_read(zf, resource_name)
                            if self._is_current_jacket(html) or \
                               self._is_legacy_jacket(html):
                                jacket_count += 1
                return jacket_count > 1

            except InvalidEpub as e:
                self.log.error(_('Invalid epub:'), e)
                return False
            except:
                self.log.error(_('ERROR parsing book: '), path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books have multiple jackets'),
                             marked_text='epub_multiple_jacket',
                             status_msg_type=_('ePub books for multiple jackets'))


    def _is_legacy_jacket(self, html):
        if html.find('<h1 class="calibrerescale') != -1 or \
           html.find('<h2 class="calibrerescale') != -1:
            return True
        return False

    def _is_current_jacket(self, html):
        if html.find('<meta content="jacket" name="calibre-content"') != -1 or \
           html.find('<meta name="calibre-content" content="jacket"') != -1:
            return True
        return False


    def check_epub_xpgt_margins(self):
        TEMPLATE_MIME_TYPES = ['application/adobe-page-template+xml',
                               'application/vnd.adobe-page-template+xml',
                               'application/vnd.adobe.page-template+xml']

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error(_('ERROR: EPUB format is missing: '), get_title_authors_text(db, book_id))
                return False
            try:
                displayed_path = False
                with ZipFile(path_to_book, 'r') as zf:
                    opf_name = self._get_opf_xml(path_to_book, zf)
                    if opf_name:
                        for mt in TEMPLATE_MIME_TYPES:
                            xpgt_name = self._get_opf_item(zf, opf_name,
                                    xpath=unicode_type(r'child::opf:manifest/opf:item'
                                           '[@media-type="%s"]')%mt)
                            if xpgt_name:
                                if not displayed_path:
                                    displayed_path = True
                                    self.log('<b>%s</b>'%get_title_authors_text(db, book_id))
                                xpgt_content = self.zf_read(zf, xpgt_name)
                                if 'margin' in xpgt_content:
                                    self.log('\t<span style="color:darkgray">Margins still present in: %s</span>'%xpgt_name)
                                    return True
                                self.log('\t<span style="color:darkgray">XPGT has no margins: %s</span>'%xpgt_name)
                                break
                return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books have non-zero .xpgt margins'),
                             marked_text='epub_xpgt_margins',
                             status_msg_type=_('ePub books for .xpgt margins'))


    def check_epub_inline_xpgt_links(self):
        RE_LINK = re.compile(r'<link[^>]+?href\s*=\s*".*?\.xpgt"[^>]*?>', re.UNICODE)
        RE_CSS_IMPORT1 = re.compile(r'@import url\([\'\"]*(.*?)[\'"]*\)', re.UNICODE | re.DOTALL)
        RE_CSS_IMPORT2 = re.compile(r'@import\s+"(.*?)"', re.UNICODE | re.DOTALL)

        def check_for_import_xpgt(data):
            for match in RE_CSS_IMPORT1.finditer(data):
                self.log('Match1', match.group(0))
                if match.group(1).lower().endswith('.xpgt'):
                    return True
            for match in RE_CSS_IMPORT2.finditer(data):
                self.log('Match2', match.group(0))
                if match.group(1).lower().endswith('.xpgt'):
                    return True

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    contents = zf.namelist()
                    for resource_name in contents:
                        extension = resource_name[resource_name.rfind('.'):].lower()
                        if extension in CSS_FILES:
                            data = self.zf_read(zf, resource_name).lower()
                            self.log(_('Checking css import'), resource_name)
                            if check_for_import_xpgt(data):
                                return True
                        elif extension in NON_HTML_FILES:
                            continue
                        else:
                            data = self.zf_read(zf, resource_name).lower()
                            if RE_LINK.search(data):
                                return True
                            self.log(_('Checking html import'), resource_name)
                            if check_for_import_xpgt(data):
                                return True
                    return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books have inline xpgt links'),
                             marked_text='epub_inline_xpgt_links',
                             status_msg_type=_('ePub books for inline xpgt links'))


    def check_epub_unmanifested_files(self):
        all_artifacts = [f.lower() for f in ALL_ARTIFACTS]

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                displayed_path = False
                with ZipFile(path_to_book, 'r') as zf:
                    opf_name = self._get_opf_xml(path_to_book, zf)
                    if opf_name:
                        manifest_items_map = self._get_opf_items_map(zf, opf_name)
                        resource_names = list(self._manifest_worthy_names(zf))
                        for resource_name in resource_names:
                            if resource_name not in manifest_items_map:
                                # Special exclusion for bookmarks, itunes files and other OS artifacts
                                known_artifact = False
                                if resource_name.lower() in all_artifacts:
                                    known_artifact = True
                                if not known_artifact:
                                    for a in all_artifacts:
                                        if resource_name.lower().endswith('/'+a):
                                            known_artifact = True
                                            break
                                if known_artifact:
                                    if not displayed_path:
                                        displayed_path = True
                                        self.log('<b>%s</b>'%get_title_authors_text(db, book_id))
                                    self.log('\t<span style="color:darkgray">Ignoring unmanifested file: %s</span>'%resource_name)
                                    continue
                                if not displayed_path:
                                    displayed_path = True
                                    self.log('<b>%s</b>'%get_title_authors_text(db, book_id))
                                self.log('\t<span style="color:darkgray">Unmanifested file: %s</span>'%resource_name)
                                return True
                return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books have unmanifested files'),
                             marked_text='epub_unmanifested_files',
                             status_msg_type=_('ePub books for unmanifested files'))


    def check_epub_unused_css_files(self):
        RE_CSS = r'<\s*link.*?\s+href\s*=\s*"[^"]*%s"'

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    contents = zf.namelist()
                    if self._is_drm_encrypted(zf, contents):
                        self.log.error(_('SKIPPING BOOK (DRM Encrypted): '), get_title_authors_text(db, book_id))
                        return False
                    # Build a list of regexes for all the css files in this epub
                    css_regexes = {}
                    html_resource_names = []
                    for resource_name in self._manifest_worthy_names(zf):
                        extension = resource_name[resource_name.rfind('.'):].lower()
                        if extension in CSS_FILES:
                            try:
                                css = os.path.basename(resource_name).lower()
                                css_enc = six.moves.urllib.request.pathname2url(css).lower()
                            except:
                                self.log.error(_('ERROR parsing book: '), path_to_book)
                                self.log.error(_('\tIssue with CSS name: '), resource_name)
                                self.log(traceback.format_exc())
                                return False
                            css_regexes[resource_name] = [re.compile(RE_CSS % css, re.UNICODE)]
                            if css_enc != css:
                                css_regexes[resource_name].append(re.compile(RE_CSS % css_enc, re.UNICODE))
                        elif extension not in NON_HTML_FILES:
                            html_resource_names.append(resource_name)

                    if css_regexes and html_resource_names:
                        for resource_name in html_resource_names:
                            data = self.zf_read(zf, resource_name).lower()
                            css_keys = list(css_regexes.keys())
                            for css_key in css_keys:
                                regexes = css_regexes[css_key]
                                for css_regex in regexes:
                                    if css_regex.search(data):
                                        css_regexes.pop(css_key)
                                        break
                            if not css_regexes:
                                break
                    if css_regexes:
                        self.log(get_title_authors_text(db, book_id))
                        for resource_name in css_regexes.keys():
                            self.log(_('\tUnused CSS file: %s')%resource_name)
                        return True
                    return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books have unused CSS files'),
                             marked_text='epub_unused_css_files',
                             status_msg_type=_('ePub books for unused CSS files'))


    def check_epub_unused_images(self):
        RE_IMAGE = r'<(?:[a-z]*?\:)*?ima?ge?[^>]*?"[^"]*?%s"'
        RE_IMAGE_STYLE = r'background-image:[^\'>]*?url\(\'?[^\)]*?%s\'?\)'
        
        def check_for_images_in_html_resources(zf, image_regexes, image_name_regexes, resource_names):
            for resource_name in resource_names:
                data = self.zf_read(zf, resource_name)
                image_keys = list(image_regexes.keys())
                for image_key in image_keys:
                    regexes = image_regexes[image_key]
                    for image_regex in regexes:
                        if image_regex.search(data):
                            #self.log.info('\tFOUND (HTML): ', image_key, ' in: ', resource_name)
                            image_regexes.pop(image_key)
                            image_name_regexes.pop(image_key)
                            break
                if not image_regexes:
                    break
        
        def check_for_images_in_css_resources(zf, image_regexes, image_name_regexes, resource_names):
            #self.log.info('*** Scanning CSS for images')
            for resource_name in resource_names:
                data = self.zf_read(zf, resource_name)
                image_keys = list(image_name_regexes.keys())
                for image_key in image_keys:
                    image_regex = image_name_regexes[image_key]
                    #self.log.info('  Scanning css for image: ', image_key, ' regex: ', image_regex)
                    if image_regex.search(data):
                        #self.log.info('\tFOUND (CSS): ', image_key, ' in: ', resource_name)
                        image_name_regexes.pop(image_key)
                        image_regexes.pop(image_key)
                if not image_name_regexes:
                    break

        def check_for_images_in_opf_cover_meta(path_to_book, zf, image_regexes, image_name_regexes):
            #self.log.info('*** Scanning OPF for images')            
            opf_name = self._get_opf_xml(path_to_book, zf)
            if not opf_name:
                return
            opf_xml = self._get_opf_tree(zf, opf_name)
            covers = opf_xml.xpath(r'child::opf:metadata/opf:meta[@name="cover" and @content]',
                                   namespaces={'opf':OPF_NS})
            cover_id = None
            if covers:
                cover_id = covers[0].get('content')
            if cover_id:
                items = opf_xml.xpath(r'child::opf:manifest/opf:item',
                                      namespaces={'opf':OPF_NS})
                image_keys = list(image_name_regexes.keys())
                for item in items:
                    if item.get('id', None) == cover_id:
                        item_href = item.get('href', None)
                        for image_key in image_keys:
                            image_regex = image_name_regexes[image_key]
                            #self.log.info('  Scanning opf meta for image: ', image_key, ' regex: ', image_regex)
                            if image_regex.search(item_href):
                                #self.log.info('\tFOUND (OPF): ', image_key)
                                image_name_regexes.pop(image_key)
                                image_regexes.pop(image_key)
                        if not image_name_regexes:
                            break

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error(_('ERROR: EPUB format is missing: '), get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    contents = zf.namelist()
                    if self._is_drm_encrypted(zf, contents):
                        self.log.error(_('SKIPPING BOOK (DRM Encrypted): '), get_title_authors_text(db, book_id))
                        return False
                    # Build a list of regexes for all the image files in this epub
                    image_regexes = {}
                    image_name_regexes = {}
                    html_resource_names = []
                    css_resource_names = []
                    for resource_name in self._manifest_worthy_names(zf):
                        extension = resource_name[resource_name.rfind('.'):].lower()
                        if extension in IMAGE_FILES:
                            # Use the base name for the image since relative path might differ from html
                            # compared to the opf manifest
                            try:
                                image = os.path.basename(resource_name)
                                image_enc = six.moves.urllib.request.pathname2url(image)
                                #self.log.info('Image: ', image)
                            except:
                                self.log.error('ERROR parsing book: ', path_to_book)
                                self.log.error(_('\tIssue with image name: '), resource_name)
                                self.log(traceback.format_exc())
                                return False
                            image_name_regexes[resource_name] = re.compile(image, re.UNICODE | re.IGNORECASE)
                            image_regexes[resource_name] = [re.compile(RE_IMAGE % image, re.UNICODE | re.IGNORECASE)]
                            image_regexes[resource_name].append(re.compile(RE_IMAGE_STYLE % image, re.UNICODE | re.IGNORECASE))
                            if image_enc != image:
                                image_regexes[resource_name].append(re.compile(RE_IMAGE % image_enc, re.UNICODE | re.IGNORECASE))
                                image_regexes[resource_name].append(re.compile(RE_IMAGE_STYLE % image_enc, re.UNICODE | re.IGNORECASE))
                        elif extension in CSS_FILES:
                            css_resource_names.append(resource_name)
                        elif extension not in NON_HTML_FILES:
                            html_resource_names.append(resource_name)

                    if image_regexes or html_resource_names:
                        check_for_images_in_html_resources(zf, image_regexes, image_name_regexes, html_resource_names)
                    if image_regexes or css_resource_names:
                        check_for_images_in_css_resources(zf, image_regexes, image_name_regexes, css_resource_names)
                    if image_regexes:
                        check_for_images_in_opf_cover_meta(path_to_book, zf, image_regexes, image_name_regexes)
                    
                    if image_regexes:
                        self.log('----------------------------------------------------')
                        self.log(get_title_authors_text(db, book_id))
                        for resource_name in image_regexes.keys():
                            self.log(_('\tUNUSED image file: %s')%resource_name)
                        return True
                    return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books have unused image files'),
                             marked_text='epub_unused_images',
                             status_msg_type=_('ePub books for unused image files'))


    def check_epub_broken_image_links(self):
        RE_IMAGE = re.compile(r'<(?:[a-z]*?\:)*?image[^>]*href=?"([^"]*?)"', re.UNICODE)
        RE_IMG = re.compile(r'<(?:[a-z]*?\:)*?img[^>]*src="([^"]*?)"', re.UNICODE)

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error(_('ERROR: EPUB format is missing: '), get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    contents = zf.namelist()
                    if self._is_drm_encrypted(zf, contents):
                        self.log.error(_('SKIPPING BOOK (DRM Encrypted): '), get_title_authors_text(db, book_id))
                        return False
                    # Build a list of all the image files in this epub
                    image_map = {}
                    html_resource_names = []
                    for resource_name in self._manifest_worthy_names(zf):
                        extension = resource_name[resource_name.rfind('.'):].lower()
                        if extension in IMAGE_FILES:
                            # Use the base name for the image since relative path might differ from html
                            # compared to the opf manifest
                            try:
                                image = six.moves.urllib.request.url2pathname(resource_name.lower())
                            except:
                                self.log.error('ERROR parsing book: ', path_to_book)
                                self.log.error('\tIssue with image name: ', resource_name)
                                self.log(traceback.format_exc())
                                return False
                            image_map[image] = resource_name
                        elif extension not in NON_HTML_FILES:
                            html_resource_names.append(resource_name)

                    found_broken = False
                    if html_resource_names:
                        for resource_name in html_resource_names:
                            raw_data = self.zf_read(zf, resource_name)
                            data = raw_data.lower()
                            html_dir = os.path.dirname(resource_name).lower()
                            if html_dir:
                                html_dir += os.sep

                            img_tag_matches = RE_IMG.findall(data)
                            image_tag_matches = RE_IMAGE.findall(data)
                            for match in img_tag_matches + image_tag_matches:
                                rel_path = os.path.normpath(html_dir + match)
                                normalised_image_name = six.moves.urllib.request.url2pathname(rel_path)
                                if normalised_image_name not in image_map:
                                    if not found_broken:
                                        self.log(get_title_authors_text(db, book_id))
                                        found_broken = True
                                    self.log(_('\tBroken image link in:'), resource_name, _(' of '), match)
                    return found_broken

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books have broken image links'),
                             marked_text='epub_broken_image_links',
                             status_msg_type=_('ePub books for broken image links'))


    def check_epub_files(self, files, text, marked, show_log=True):
        match_files = [f.lower() for f in files]

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                match = False
                displayed_path = False
                with ZipFile(path_to_book, 'r') as zf:
                    contents = zf.namelist()
                    for resource_name in contents:
                        found = False
                        if resource_name.lower() in match_files:
                            found = True
                        else:
                            for a in match_files:
                                if resource_name.lower().endswith('/'+a):
                                    found = True
                                    break
                        if found:
                            if show_log:
                                if not displayed_path:
                                    displayed_path = True
                                    self.log('Match found in: <b>%s</b>'%get_title_authors_text(db, book_id))
                                self.log('\t<span style="color:darkgray">%s</span>'%resource_name)
                            match = True
                return match

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books have ')+text,
                             marked_text=marked,
                             status_msg_type=_('ePub books for ')+text)


    def check_epub_replaceable_cover(self, check_has_cover):

        def raster_cover(opf_xml):
            covers = opf_xml.xpath(r'child::opf:metadata/opf:meta[@name="cover" and @content]',
                                   namespaces={'opf':OPF_NS})
            if covers:
                cover_id = covers[0].get('content')
                items = opf_xml.xpath(r'child::opf:manifest/opf:item',
                                      namespaces={'opf':OPF_NS})
                for item in items:
                    if item.get('id', None) == cover_id:
                        mt = item.get('media-type', '')
                        if 'xml' not in mt:
                            return item.get('href', None)
                for item in items:
                    if item.get('href', None) == cover_id:
                        mt = item.get('media-type', '')
                        if mt.startswith('image/'):
                            return item.get('href', None)

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return not check_has_cover
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    opf_name = self._get_opf_xml(path_to_book, zf)
                    if not opf_name:
                        self.log.error(_('No OPF file in:'), get_title_authors_text(db, book_id))
                        return not check_has_cover
                    opf_xml = self._get_opf_tree(zf, opf_name)
                    rcover = raster_cover(opf_xml)
                    if not rcover:
                        self.log(_('No supported meta tag or non-xml cover in:'), get_title_authors_text(db, book_id))
                        return not check_has_cover
                    cpath = posixpath.join(posixpath.dirname(opf_name), rcover)
                    is_encrypted_cover = self._get_encryption_meta(zf).is_encrypted(cpath)
                    if is_encrypted_cover:
                        self.log(_('DRM Encrypted cover in:'), get_title_authors_text(db, book_id))
                        return check_has_cover

                    image_extension = os.path.splitext(cpath)[1].lower()
                    if image_extension not in ('.png', '.jpg', '.jpeg'):
                        self.log(_('Invalid cover image extension (%s) in:')%image_extension, get_title_authors_text(db, book_id))
                        return not check_has_cover
                return check_has_cover

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return not check_has_cover
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return not check_has_cover

        if check_has_cover:
            msg = _('No searched ePub books have replaceable covers')
            marked_text = 'epub_has_replaceable_cover'
        else:
            msg = _('All searched ePub books have replaceable covers')
            marked_text = 'epub_not_replaceable_cover'
        self.check_all_files(evaluate_book,
                             no_match_msg=msg, marked_text=marked_text,
                             status_msg_type=_('ePub books for replaceable covers'))


    def check_epub_calibre_svg_cover(self, check_has_svg_cover):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return not check_has_svg_cover
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    opf_name = self._get_opf_xml(path_to_book, zf)
                    if opf_name:
                        cover_name = self._get_opf_item(zf, opf_name,
                                    xpath=r'child::opf:guide/opf:reference'
                                           '[@type="cover"and @href]')
                        if cover_name and cover_name.endswith('.xhtml'):
                            html = self.zf_read(zf, cover_name)
                            data = self._parse_xhtml(html, cover_name)
                            metas = XPath('//h:meta[@content="true" and @name="calibre:cover"]')(data)
                            if len(metas):
                                svg = XPath('//svg:svg')(data)
                                if len(svg):
                                    return check_has_svg_cover
                return not check_has_svg_cover

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return not check_has_svg_cover
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return not check_has_svg_cover

        if check_has_svg_cover:
            msg = _('No searched ePub books have calibre SVG covers embedded')
            marked_text = 'epub_has_calibre_svg_cover'
        else:
            msg = _('All searched ePub books have calibre SVG covers embedded')
            marked_text = 'epub_missing_calibre_svg_cover'
        self.check_all_files(evaluate_book,
                             no_match_msg=msg, marked_text=marked_text,
                             status_msg_type=_('ePub books for calibre SVG covers'))


    def check_epub_calibre_cover(self, check_has_cover):
        '''
        This function is DEPRECATED by check_epub_replaceable_cover above
        Keeping only in case someone decides they want this check resurrected
        '''

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return not check_has_cover
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    opf_name = self._get_opf_xml(path_to_book, zf)
                    if opf_name:
                        cover_name = self._get_opf_item(zf, opf_name,
                                    xpath=r'child::opf:guide/opf:reference'
                                           '[@type="cover"and @href]')
                        if cover_name and cover_name.endswith('.xhtml'):
                            html = self.zf_read(zf, cover_name)
                            if html.find('<meta content="true" name="calibre:cover"') != -1 or \
                               html.find('<meta name="calibre:cover" content="true"') != -1:
                                return check_has_cover
                return not check_has_cover

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return not check_has_cover
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return not check_has_cover

        if check_has_cover:
            msg = _('No searched ePub books have calibre covers embedded')
            marked_text = 'epub_has_calibre_cover'
        else:
            msg = _('All searched ePub books have calibre covers embedded')
            marked_text = 'epub_missing_calibre_cover'
        self.check_all_files(evaluate_book,
                             no_match_msg=msg, marked_text=marked_text,
                             status_msg_type=_('ePub books for calibre covers'))


    def check_epub_conversion(self, check_converted):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return not check_converted
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    opf_name = self._get_opf_xml(path_to_book, zf)
                    if opf_name:
                        opf_xml = self.zf_read(zf, opf_name)
                        if opf_xml.find('name="calibre:timestamp"') != -1 or \
                           opf_xml.find('<dc:contributor opf:role="bkp">calibre ') != -1:
                            return check_converted
                return not check_converted

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return not check_converted
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return not check_converted

        if check_converted:
            msg = _('No searched ePub books have been converted by calibre')
            marked_text = 'epub_calibre_converted'
        else:
            msg = _('All searched ePub books have been converted by calibre')
            marked_text = 'epub_not_calibre_converted'
        self.check_all_files(evaluate_book,
                             no_match_msg=msg, marked_text=marked_text,
                             status_msg_type=_('ePub books for calibre conversions'))


    def check_epub_corrupt_zip(self):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    for e in zf.infolist():
                        if e.filename.endswith('/'): #file represent a folder
                            continue
                        if e.file_size == 0: #file is empty (cannot be read)
                            continue
                        zf.read(e)
                    return False

            except InvalidEpub:
                return True
            except BadZipfile:
                return True
            except:
                return True

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched ePub books have a valid zip format'),
                             marked_text='epub_corrupt_zip',
                             status_msg_type=_('ePub books for corrupted zip format'))


    def check_epub_no_container(self):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    opf_name = self._get_opf_xml(path_to_book, zf)
                    if opf_name:
                        return False
                return True

            except InvalidEpub:
                return True
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched ePub books have a valid container.xml file'),
                             marked_text='epub_missing_container_xml',
                             status_msg_type=_('ePub books for missing container.xml'))


    def check_epub_namespaces(self):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    contents = zf.namelist()
                    if 'META-INF/container.xml' not in contents:
                        # We have no container xml so file is completely knackered
                        self.log.info(path_to_book)
                        self.log.error(_('\tMissing container.xml file in'), path_to_book)
                        return True
                    data = self.zf_read(zf, 'META-INF/container.xml')
                    if OCF_NS not in data:
                        self.log.info(path_to_book)
                        self.log.error(_('\tIncorrect container.xml namespace in'), path_to_book)
                        return True
                    opf_name = self._get_opf_xml(path_to_book, zf)
                    if opf_name:
                        data = self.zf_read(zf, opf_name)
                        if OPF_NS not in data:
                            self.log.info(path_to_book)
                            self.log.error(_('\tIncorrect .opf manifest namespace in'), path_to_book)
                            return True
                return False

            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched ePub books have valid namespaces'),
                             marked_text='epub_namespace_invalid',
                             status_msg_type=_('ePub books for namespaces check'))


    def check_epub_non_dc_metadata(self):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    opf_name = self._get_opf_xml(path_to_book, zf)
                    if opf_name:
                        opf = self._get_opf_tree(zf, opf_name)
                        metadata = opf.xpath('//opf:metadata', namespaces={'opf':OPF_NS})
                        if len(metadata):
                            for child in metadata[0]:
                                try:
                                    if child.tag.startswith('{http://purl.org/dc/'):
                                        continue
                                    # Make sure we exclude the mandatory dcterms:modified meta element for epub3
                                    if child.attrib.get('property') == 'dcterms:modified':
                                        continue
                                    return True
                                except:
                                    # Dunno how to elegantly handle in lxml parsing
                                    # text like <!-- stuff --> which blows up when
                                    # calling the .tag function.
                                    pass
                return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched ePub books have only dc: elements in manifest'),
                             marked_text='epub_non_dc_metadata',
                             status_msg_type=_('ePub books for non dc: metadata check'))


    def check_epub_opf_files_missing(self):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                displayed_path = False
                missing = False
                with ZipFile(path_to_book, 'r') as zf:
                    opf_name = self._get_opf_xml(path_to_book, zf)
                    if opf_name:
                        manifest_items_map = self._get_opf_items_map(zf, opf_name)
                        contents = zf.namelist()
                        for resource_name in manifest_items_map:
                            if resource_name not in contents:
                                if not displayed_path:
                                    displayed_path = True
                                    self.log(_('Manifest file missing from: <b>%s</b>')%get_title_authors_text(db, book_id))
                                self.log('\t<span style="color:darkgray">%s</span>'%resource_name)
                                missing = True
                return missing

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched ePub books have a valid opf manifest'),
                             marked_text='epub_manifest_files_missing',
                             status_msg_type=_('ePub books for missing files in opf'))


    def check_epub_toc_hierarchical(self):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    contents = zf.namelist()
                    if self._is_drm_encrypted(zf, contents):
                        self.log.error('SKIPPING BOOK (DRM Encrypted): ', get_title_authors_text(db, book_id))
                        return False
                    for name in self._manifest_worthy_names(zf):
                        if name.endswith('.ncx'):
                            try:
                                ncx = self._parse_xml(self.zf_read(zf, name))
                                nested = ncx.xpath(r'descendant::ncx:navPoint/ncx:navPoint',
                                                   namespaces={'ncx':NCX_NS})
                                if len(nested) > 0:
                                    return True
                            except UnicodeDecodeError:
                                self.log.error(_('Ignoring DRM protected ePub: '), path_to_book)
                                return False
                return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched ePub books have a flattened NCX TOC'),
                             marked_text='epub_ncx_toc_hierarchical',
                             status_msg_type=_('ePub books for NCX TOC hierarchy'))


    def check_epub_toc_size(self):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                count = None
                with ZipFile(path_to_book, 'r') as zf:
                    contents = zf.namelist()
                    if self._is_drm_encrypted(zf, contents):
                        self.log.error('SKIPPING BOOK (DRM Encrypted): ', get_title_authors_text(db, book_id))
                        return False
                    for name in self._manifest_worthy_names(zf):
                        if name.endswith('.ncx'):
                            try:
                                ncx_xml = self.zf_read(zf, name)
                                count = len(ncx_xml.split('<navLabel>')) - 1
                                break
                            except UnicodeDecodeError:
                                self.log.error(_('Ignoring DRM protected ePub: '), path_to_book)
                                return True
                if count >= 3:
                    return False
                self.log(get_title_authors_text(db, book_id))
                if count is None:
                    self.log('\t<span style="color:orange">No NCX file found</span>')
                else:
                    self.log('\t<span style="color:orange">Only %d items in TOC</span>'%count)
                return True

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched ePub books have a NCX TOC with at least 3 items'),
                             marked_text='epub_ncx_toc_too_small',
                             status_msg_type=_('ePub books for NCX TOC count'))


    def check_epub_toc_broken_links(self):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                broken_links = []
                with ZipFile(path_to_book, 'r') as zf:
                    contents = zf.namelist()
                    if self._is_drm_encrypted(zf, contents):
                        self.log.error('SKIPPING BOOK (DRM Encrypted): ', get_title_authors_text(db, book_id))
                        return False
                    manifest_names = list(self._manifest_worthy_names(zf))
                    html_names_map = dict((os.path.normpath(six.moves.urllib.request.url2pathname(k)),True) for k in manifest_names
                                          if k[k.rfind('.'):].lower() not in NON_HTML_FILES)
                    for name in manifest_names:
                        if name.endswith('.ncx'):
                            ncx_dir = os.path.dirname(name)
                            if ncx_dir:
                                ncx_dir += '/'
                            try:
                                ncx = self._parse_xml(self.zf_read(zf, name))
                                src_nodes = ncx.xpath(r'descendant::ncx:content/@src',
                                                   namespaces={'ncx':NCX_NS})
                                for src_node in src_nodes:
                                    link = src_node.partition('#')[0]
                                    link_path = os.path.normpath(six.moves.urllib.request.url2pathname(ncx_dir + link))
                                    #self.log.info('\tLooking for:', link_path)
                                    if link_path not in html_names_map:
                                        broken_links.append(link)
                                break
                            except UnicodeDecodeError:
                                self.log.error('Ignoring DRM protected ePub: ', path_to_book)
                                return True
                if broken_links:
                    self.log(get_title_authors_text(db, book_id))
                    for broken_link in broken_links:
                        self.log('\t<span style="color:orange">NCX node broken: </span><span style="color:darkgray">%s</span>'%broken_link)
                    return True
                return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched ePub books have a NCX TOC with valid links'),
                             marked_text='epub_ncx_toc_broken_links',
                             status_msg_type=_('ePub books for broken NCX TOC links'))


    def check_epub_guide_broken_links(self):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                broken_links = []
                with ZipFile(path_to_book, 'r') as zf:
                    opf_name = self._get_opf_xml(path_to_book, zf)
                    if opf_name:
                        manifest_items_map = self._get_opf_items_map(zf, opf_name, rebase_href=False)
                        #self.log('Items map:', manifest_items_map)
                        opf_xml = self._get_opf_tree(zf, opf_name)
                        guide_refs = opf_xml.xpath(r'child::opf:guide/opf:reference[@href]',
                                               namespaces={'opf':OPF_NS})
                        if len(guide_refs):
                            for guide_ref in guide_refs:
                                href = guide_ref.get('href', None)
                                if href:
                                    link = href.partition('#')[0]
                                    if link not in manifest_items_map:
                                        broken_links.append(link)
                if broken_links:
                    self.log(get_title_authors_text(db, book_id))
                    for broken_link in broken_links:
                        self.log('\t<span style="color:orange">Guide href broken: </span><span style="color:darkgray">%s</span>'%broken_link)
                    return True
                return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched ePub books have valid guide entries'),
                             marked_text='epub_guide_broken_links',
                             status_msg_type=_('ePub books for broken guide links'))


    def check_epub_html_size(self):
        MAX_SIZE = 260*1024

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    contents = zf.infolist()
                    for resource in contents:
                        if resource.file_size > MAX_SIZE:
                            # Is this an HTML file?
                            ext = os.path.splitext(resource.filename.lower())[1]
                            if ext in ['.htm', '.html', '.xhtml']:
                                self.log.info(path_to_book)
                                self.log('\t<span style="color:orange">Oversize file: %s of %d bytes</span>'% \
                                               (resource.filename, resource.file_size))
                                return True
                return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books have oversize html files'),
                             marked_text='epub_html_oversize',
                             status_msg_type=_('ePub books for oversize html files'))


    def check_epub_drm(self):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    contents = zf.namelist()
                    return self._is_drm_encrypted(zf, contents)
                return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books have DRM'),
                             marked_text='epub_drm',
                             status_msg_type=_('ePub books for DRM'))


    def check_epub_drm_meta(self):
        RE_DRM_META = re.compile(r'<meta [^>]*?name="adept\.[expctd\.]*?resource"', re.UNICODE)

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    for resource_name in self._manifest_worthy_names(zf):
                        extension = resource_name[resource_name.rfind('.'):].lower()
                        if extension in NON_HTML_FILES:
                            continue
                        else:
                            data = self.zf_read(zf, resource_name).lower()
                            if RE_DRM_META.search(data):
                                return True
                    return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books have Adobe DRM meta tags'),
                             marked_text='epub_adobe_meta_tags',
                             status_msg_type=_('ePub books for Adobe DRM meta tags'))


    def check_epub_address(self):
        RE_ADDRESS = re.compile(r'</address>', re.UNICODE)

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    for resource_name in self._manifest_worthy_names(zf):
                        extension = resource_name[resource_name.rfind('.'):].lower()
                        if extension in NON_HTML_FILES:
                            continue
                        else:
                            data = self.zf_read(zf, resource_name).lower()
                            if RE_ADDRESS.search(data):
                                return True
                    return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_(r'No searched ePub books have \<address\> smart tags'),
                             marked_text='epub_address_tags',
                             status_msg_type=_('ePub books for <address> smart tags'))


    def check_epub_embedded_fonts(self):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                found = False
                displayed_path = False
                with ZipFile(path_to_book, 'r') as zf:
                    for resource_name in self._manifest_worthy_names(zf):
                        extension = resource_name[resource_name.rfind('.'):].lower()
                        if extension in FONT_FILES:
                            if not displayed_path:
                                displayed_path = True
                                self.log(_('Font found in: <b>%s</b>')%get_title_authors_text(db, book_id))
                            self.log('\t<span style="color:darkgray">%s</span>'%resource_name)
                            found = True
                return found

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books have embedded fonts'),
                             marked_text='epub_embedded_fonts',
                             status_msg_type=_('ePub books for embedded fonts'))


    def check_epub_font_faces(self):
        RE_FONT_FACE = re.compile(r'@font\-face', re.UNICODE)

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    for resource_name in self._manifest_worthy_names(zf):
                        extension = resource_name[resource_name.rfind('.'):].lower()
                        if extension in CSS_FILES:
                            css = self.zf_read(zf, resource_name).lower()
                            if RE_FONT_FACE.search(css):
                                self.log(_('CSS file contains @font-face: <b>%s</b>')%get_title_authors_text(db, book_id))
                                self.log('\t<span style="color:darkgray">%s</span>'%resource_name)
                                return True
                        elif extension not in NON_HTML_FILES:
                            data = self.zf_read(zf, resource_name).lower()
                            if RE_FONT_FACE.search(data):
                                self.log(_('At least one html file contains @font-face: <b>%s</b>')%get_title_authors_text(db, book_id))
                                self.log('\t<span style="color:darkgray">%s</span>'%resource_name)
                                return True
                return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books have @font-face declarations'),
                             marked_text='epub_font_face',
                             status_msg_type=_('ePub books for @font-face declarations'))


    def check_epub_css_justify(self):
        RE_TEXT_ALIGN = re.compile(r'text\-align:\s*justify', re.UNICODE)

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    for resource_name in self._manifest_worthy_names(zf):
                        if resource_name.lower().endswith('css'):
                            css = self.zf_read(zf, resource_name).lower()
                            if RE_TEXT_ALIGN.search(css):
                                return False
                return True

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched ePub books have text-align:justify'),
                             marked_text='epub_css_justify',
                             status_msg_type=_('ePub books for text-align:justify'))


    def check_epub_css_margins(self):
        RE_BOOK_MGNS = re.compile(r'(#\w+\s+)?(?P<selector>(?<!\.)\bbody|@page)\b\s*{(?P<styles>[^}]*margin[^}]+);?\s*\}', re.UNICODE)

        def match_margins(data, allow_less=False):
            self.user_margins = get_user_margins()
            doc_defined_margins = {}

            for match in RE_BOOK_MGNS.finditer(data):
                styles = match.group('styles').lower().strip()
                # delete trailing semicolons
                styles = re.sub(r'\s*;$', '', styles)
                if match.group('selector').lower() == 'body' and styles.find('margin') != -1:
                    self.log('\t\tMargins are defined in a body tag')
                    return True

                stylelist = styles.split(';')
                for style in stylelist:
                    if style:
                        style = [s.strip() for s in style.split(':')]
                        property_type = re.sub('-','_', style[0])
                        value = float(re.sub(r'[^\d.]+', '', style[1]))

                        if property_type == 'margin': # Not a calibre set value, so we will just replace the whole value
                            self.log(_('\t\t\'margin\' property found, so does not match calibre preferences'))
                            return True
                        if value < 0:  # Definitely not going to match, since negative values reserved to omit margins
                            self.log(_('\t\tNegative margin found, so does not match calibre preferences'))
                            return True
                        if property_type.startswith('margin_'):
                            if style[1].endswith('pt'):  # Possibly created by calibre since in pts, add to our dimensions
                                doc_defined_margins[property_type] = value
                            elif not style[1][-1:].isalpha():  # This is a value with an unspecified unit, might still be by calibre if zero
                                if value == 0.0:
                                    doc_defined_margins[property_type] = value
                                else:
                                    self.log(_('\t\tMargins is not defined in pts so does not match calibre preferences'))
                                    return True

            # If we got to here, then we found "some" margins in the style that are
            # either identical or a subset of our preferred margins
            for pref, pref_value in self.user_margins.items():
                if pref_value < 0.0:  # The user does not want this margin defined
                    if pref in doc_defined_margins:  # Currently is defined, so remove it
                        self.log(_('\t\tMargins are defined in pts but don\'t match calibre preferences'))
                        return True
                elif pref not in doc_defined_margins: # Not defined, so add it
                    self.log(_('\t\tMargins are defined in pts but don\'t match calibre preferences'))
                    return True
                else:
                    doc_value = doc_defined_margins[pref]
                    if doc_value != pref_value:
                        if not (doc_value < pref_value and allow_less):
                            self.log(_('\t\tMargins are defined in pts but don\'t match calibre preferences'))
                            return True
            # If we got to here everything matches our prefs
            self.log(_('\t\tMargins match calibre preferences'))
            return False

        def get_user_margins():
            calibre_default_margins = {
                                        'margin_right' : 5.0,
                                          'margin_top' : 5.0,
                                         'margin_left' : 5.0,
                                       'margin_bottom' : 5.0
                                      }
            from calibre.ebooks.conversion.config import load_defaults
            ps = load_defaults('page_setup')
            # Only interested in the margins out of page setup settings
            prefs_margins = dict((k,v) for k,v in ps.items() if k.startswith('margin_'))
            if 'margin_top' not in prefs_margins:
                # The user has never changed their page setup defaults to save settings
                prefs_margins = calibre_default_margins
            return prefs_margins

        def evaluate_book(book_id, db):
            self.path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not self.path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(self.path_to_book, 'r') as zf:
                    self.log(_('\tAnalyzing margins in ')+self.path_to_book)
                    contents = list(self._manifest_worthy_names(zf))
                    # Check the CSS files for @page and body declarations
                    for resource_name in contents:
                        if resource_name.lower().endswith('css'):
                            css = self.zf_read(zf, resource_name).lower()
                            if RE_BOOK_MGNS.search(css):
                                return match_margins(css)
                    # Check the xhtml files for inline @page and body declarations
                    for resource_name in contents:
                        extension = resource_name[resource_name.rfind('.'):].lower()
                        if extension in NON_HTML_FILES:
                            continue
                        elif resource_name.endswith('titlepage.xhtml'):
                            continue
                        else:
                            data = self.zf_read(zf, resource_name).lower()
                            if RE_BOOK_MGNS.search(data[:1000]):
                                if match_margins(data[:1000], True):
                                    return True

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', self.path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched ePub books match the calibre page setup preferences'),
                             marked_text='epub_css_margins',
                             status_msg_type=_('ePub books for body or @page css margins'))


    def check_epub_css_no_margins(self):
        RE_BOOK_MGNS = re.compile(r'(#\w+\s+)?(?P<selector>\bbody|@page)\b\s*{(?P<styles>[^}]+margin[^}]+);?\s*\}', re.UNICODE)

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    contents = list(self._manifest_worthy_names(zf))
                    for resource_name in contents:
                        if resource_name.lower().endswith('css'):
                            css = self.zf_read(zf, resource_name).lower()
                            if RE_BOOK_MGNS.search(css):
                                return False
                    for resource_name in contents:
                        extension = resource_name[resource_name.rfind('.'):].lower()
                        if extension in NON_HTML_FILES:
                            continue
                        else:
                            data = self.zf_read(zf, resource_name).lower()
                            if RE_BOOK_MGNS.search(data[:1000]):
                                return False
                    return True

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched ePub books have book level margins defined'),
                             marked_text='epub_css_no_margins',
                             status_msg_type=_('ePub books lacking body or @page css margins'))


    def check_epub_inline_margins(self):
        RE_BOOK_MGNS = re.compile(r'(#\w+\s+)?(?P<selector>\bbody|@page)\b\s*{(?P<styles>[^}]+margin[^}]+);?\s*\}', re.UNICODE)

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    for resource_name in self._manifest_worthy_names(zf):
                        extension = resource_name[resource_name.rfind('.'):].lower()
                        if extension in NON_HTML_FILES:
                            continue
                        elif resource_name.lower().find('title') != -1:
                            continue
                        elif resource_name.lower().find('cover') != -1:
                            continue
                        else:
                            data = self.zf_read(zf, resource_name).lower()
                            if RE_BOOK_MGNS.search(data[:1000]):
                                return True
                    return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books inline @page margins'),
                             marked_text='epub_inline_margins',
                             status_msg_type=_('ePub books using inline @page or body css margins'))


    def check_epub_javascript(self):
        RE_JAVASCRIPT = re.compile(r'<script [^>]+?type\s*=\s*"text/javascript"[^>]*?>')

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    contents = zf.namelist()
                    if self._is_drm_encrypted(zf, contents):
                        self.log.error('SKIPPING BOOK (DRM Encrypted): ', get_title_authors_text(db, book_id))
                        return False
                    reasons = []
                    for resource_name in self._manifest_worthy_names(zf):
                        extension = resource_name[resource_name.rfind('.'):].lower()
                        if extension in JAVASCRIPT_FILES:
                            reasons.append(_('\tContains .js file: %s')% resource_name)
                        elif extension in NON_HTML_FILES:
                            continue
                        else:
                            data = self.zf_read(zf, resource_name)
                            if RE_JAVASCRIPT.search(data):
                                reasons.append(_('\tContains inline javascript: %s')% resource_name)
                    if reasons:
                        self.log(_('ePub with Javascript: %s')%get_title_authors_text(db, book_id))
                        for reason in reasons:
                            self.log(reason)
                        return True
                    return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books have javascript'),
                             marked_text='epub_javascript',
                             status_msg_type=_('ePub books for javascript'))


    def check_epub_smarten_punctuation(self):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                with ZipFile(path_to_book, 'r') as zf:
                    contents = zf.namelist()
                    if self._is_drm_encrypted(zf, contents):
                        self.log.error('SKIPPING BOOK (DRM Encrypted): ', get_title_authors_text(db, book_id))
                        return False
                    opf_name = self._get_opf_xml(path_to_book, zf)
                    if opf_name:
                        manifest_items_map = self._get_opf_items_map(zf, opf_name, spine_only=True)
                        contents = zf.namelist()
                        for resource_name in manifest_items_map:
                            extension = resource_name[resource_name.rfind('.'):].lower()
                            if extension in NON_HTML_FILES:
                                continue
                            data = self.zf_read(zf, resource_name).lower()
                            # Only interested in the body without any html tags
                            body_text = self._extract_body_text(data)
                            if body_text.find('\'') != -1 or body_text.find('"') != -1:
                                self.log(_('Unsmartened punctuation in: <b>%s</b>')% get_title_authors_text(db, book_id))
                                self.log('\t<span style="color:darkgray">%s</span>'% resource_name)
                                return True
                    return False

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('No searched ePub books need punctuation smartened'),
                             marked_text='epub_smarten_punctuation',
                             status_msg_type=_('ePub books for smarten punctuation'))


    # -----------------------------------------------------------
    #
    #   Helper functions
    #
    # -----------------------------------------------------------

    def _get_opf_xml(self, path_to_book, zf):
        contents = zf.namelist()
        if 'META-INF/container.xml' not in contents:
            raise InvalidEpub('Missing container.xml from:%s'%path_to_book)
        container = self._parse_xml(zf.read('META-INF/container.xml'))
        opf_files = container.xpath((r'child::ocf:rootfiles/ocf:rootfile'
                                      '[@media-type="%s" and @full-path]'%guess_type('a.opf')[0]
                                     ), namespaces={'ocf':OCF_NS})
        if not opf_files:
            raise InvalidEpub(_('Could not find OPF in:%s')%path_to_book)
        opf_name = opf_files[0].attrib['full-path']
        if opf_name not in contents:
            raise InvalidEpub(_('OPF file in container.xml not found in:%s')%path_to_book)
        return opf_name

    def _get_opf_item(self, zf, opf_name, xpath, opf_xml=None):
        if not opf_xml:
            opf_xml = self._get_opf_tree(zf, opf_name)
        items = opf_xml.xpath(xpath, namespaces={'opf':OPF_NS})
        if len(items):
            opf_dir = posixpath.dirname(opf_name)
            item_name = self._href_to_name(items[0].attrib['href'], opf_dir)
            if item_name in zf.namelist():
                return item_name

    def _get_opf_items_map(self, zf, opf_name, opf_xml=None, rebase_href=True, spine_only=False):
        if not opf_xml:
            opf_xml = self._get_opf_tree(zf, opf_name)
        items = opf_xml.xpath(r'child::opf:manifest/opf:item[@href]',
                              namespaces={'opf':OPF_NS})
        spine_items = []
        if spine_only:
            spine_items = opf_xml.xpath(r'child::opf:spine/opf:itemref/@idref',
                              namespaces={'opf':OPF_NS})

        items_map = {}
        opf_dir = posixpath.dirname(opf_name)
        for item in items:
            if spine_only:
                id = item.attrib['id']
                if not id in spine_items:
                    continue
            if rebase_href:
                item_name = self._href_to_name(item.attrib['href'], opf_dir)
            else:
                item_name = item.attrib['href']
            items_map[item_name] = item
        return items_map

    def _get_opf_tree(self, zf, opf_name):
        data = zf.read(opf_name)
        data = data.decode('utf-8')
        data = re.sub(r'http://openebook.org/namespaces/oeb-package/1.0/',
                OPF_NS, data)
        return self._parse_xml(data)

    def _href_to_name(self, href, base=''):
        hash_index = href.find('#')
        period_index = href.find('.')
        if hash_index > 0 and hash_index > period_index:
            href = href.partition('#')[0]
        href = six.moves.urllib.parse.unquote(href)
        name = href
        if base:
            name = posixpath.join(base, href)
        name = os.path.normpath(name).replace('\\', '/')
        return name

    def _manifest_worthy_names(self, zf, suppress_apple_fonts=True):
        for name in zf.namelist():
            if name == 'mimetype': continue
            if name.endswith('/'): continue
            if name.endswith('pagemap.xml'): continue
            if name == 'META-INF/com.apple.ibooks.display-options.xml' and suppress_apple_fonts: continue
            if name.endswith('.opf'): continue
            if name.startswith('META-INF') and \
                    posixpath.basename(name) in META_INF: continue
            yield name

    def _is_drm_encrypted(self, zf, contents):
        for resource_name in contents:
            if resource_name.lower().endswith('encryption.xml'):
                root = self._parse_xml(self.zf_read(zf, resource_name))
                for em in root.xpath('descendant::*[contains(name(), "EncryptionMethod")]'):
                    algorithm = em.get('Algorithm', '')
                    if algorithm != 'http://ns.adobe.com/pdf/enc#RC':
                        return True
                return False
        return False

    def _get_encryption_meta(self, zf):
        for name in zf.namelist():
            if name == ENCRYPTION_PATH:
                try:
                    return Encryption(self.zf_read(zf, name))
                except:
                    return Encryption(None)
        return Encryption(None)

    def _extract_body_text(self, data):
        '''
        Get the body text of this html content wit any html tags stripped
        '''
        body = RE_HTML_BODY.findall(data)
        if body:
            return RE_STRIP_MARKUP.sub('', body[0])
        return ''

    def _parse_xml(self, data):
        data = xml_to_unicode(data, strip_encoding_pats=True, assume_utf8=True,
                             resolve_entities=True)[0].strip()
        return etree.fromstring(data, parser=RECOVER_PARSER)

    def _parse_xhtml(self, data, name):
        orig_data = data
        fname = urlunquote(name)
        # Don't fill our QC log up with errors about html parsing
        from calibre.utils.logging import Log
        log = Log()
        try:
            data = parse_html(data, log=log,
                    decoder=self._decode,
                    preprocessor=self.html_preprocessor,
                    filename=fname, non_html_file_tags={'ncx'})
        except NotHTML:
            return self._parse_xml(orig_data)
        return data

    def _decode(self, data):
        """Automatically decode :param:`data` into a `unicode` object."""
        def fix_data(d):
            return d.replace('\r\n', '\n').replace('\r', '\n')
        if isinstance(data, unicode):
            return fix_data(data)
        bom_enc = None
        if data[:4] in ('\0\0\xfe\xff', '\xff\xfe\0\0'):
            bom_enc = {'\0\0\xfe\xff':'utf-32-be',
                    '\xff\xfe\0\0':'utf-32-le'}[data[:4]]
            data = data[4:]
        elif data[:2] in ('\xff\xfe', '\xfe\xff'):
            bom_enc = {'\xff\xfe':'utf-16-le', '\xfe\xff':'utf-16-be'}[data[:2]]
            data = data[2:]
        elif data[:3] == '\xef\xbb\xbf':
            bom_enc = 'utf-8'
            data = data[3:]
        if bom_enc is not None:
            try:
                return fix_data(data.decode(bom_enc))
            except UnicodeDecodeError:
                pass
        if self.input_encoding:
            try:
                return fix_data(data.decode(self.input_encoding, 'replace'))
            except UnicodeDecodeError:
                pass
        try:
            return fix_data(data.decode('utf-8'))
        except UnicodeDecodeError:
            pass
        data, _ = xml_to_unicode(data)
        return fix_data(data)

    def check_epub_inside_epub(self):

        def evaluate_book(book_id, db):
            path_to_book = db.format_abspath(book_id, 'EPUB', index_is_id=True)
            if not path_to_book:
                self.log.error('ERROR: EPUB format is missing: ', get_title_authors_text(db, book_id))
                return False
            try:
                found = False
                displayed_path = False
                with ZipFile(path_to_book, 'r') as zf:
                    for resource_name in self._manifest_worthy_names(zf):
                        extension = resource_name[resource_name.rfind('.'):].lower()
                        if extension in EPUB_FILES:
                            if not displayed_path:
                                displayed_path = True
                                self.log('ePub found in: <b>%s</b>'%get_title_authors_text(db, book_id))
                            self.log('\t<span style="color:darkgray">%s</span>'%resource_name)
                            found = True
                return found

            except InvalidEpub as e:
                self.log.error('Invalid epub:', e)
                return False
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg='No searched ePub books have a ePub inside',
                             marked_text='epub_inside_epub',
                             status_msg_type='ePub books with a ePub inside')