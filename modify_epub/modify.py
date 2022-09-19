from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import six
import os, time, traceback, re

from calibre import CurrentDir, guess_type
from calibre.ebooks.chardet import strip_encoding_declarations
from calibre.ebooks.conversion.plumber import OptionValues
from calibre.ebooks.metadata.opf2 import OPF
from calibre.ebooks.metadata.meta import set_metadata
from calibre.ebooks.oeb.base import XPath
from calibre.customize.ui import apply_null_metadata
from calibre.libunzip import extract as zipextract
from calibre.ptempfile import TemporaryDirectory

from calibre_plugins.modify_epub.container import ExtendedContainer, OPF_NS
from calibre_plugins.modify_epub.covers import CoverUpdater
from calibre_plugins.modify_epub.css import CSSUpdater
from calibre_plugins.modify_epub.jacket import (remove_legacy_jackets, remove_all_jackets,
                                                add_replace_jacket)
from calibre_plugins.modify_epub.margins import MarginsUpdater

ITUNES_FILES = ['iTunesMetadata.plist', 'iTunesArtwork']
BOOKMARKS_FILES = ['META-INF/calibre_bookmarks.txt']
OS_FILES = ['.DS_Store', 'thumbs.db']
ALL_ARTIFACTS = ITUNES_FILES + BOOKMARKS_FILES + OS_FILES

class TAG:
    content = ''    #actual content
    pair = 0        #tag pair
    e_type = 0      #1=OPEN 2=CLOSE 3=CONTAINED 4=TEXT OR CR/LF 9=REMOVE-EMPTY-SPAN

def modify_epub(log, title, epub_path, calibre_opf_path, cover_path, options):
    start_time = time.time()
    modifier = BookModifier(log)
    new_book_path = modifier.process_book(title, epub_path, calibre_opf_path,
                                          cover_path, options)
    if new_book_path:
        log('ePub updated in %.2f seconds'%(time.time() - start_time))
    else:
        log('ePub not changed after %.2f seconds'%(time.time() - start_time))
    return new_book_path


class BookModifier(object):

    def __init__(self, log):
        self.log = log

    def process_book(self, title, epub_path, calibre_opf_path, cover_path, options):
        self.log('  Modifying: ', epub_path)
        try:
            self._restore_metadata_from_opf(calibre_opf_path, cover_path)
            self._setup_user_options()

            # If the user is updating metadata, we need to do this as a separate
            # step at the start, because it takes a stream object as input so is
            # run before we have written any container changes to disk below.
            is_metadata_updated = False
            if options['update_metadata']:
                is_metadata_updated = self._update_metadata_and_cover(epub_path)

            # Extract the epub into a temp directory
            with TemporaryDirectory('_modify-epub') as tdir:
                with CurrentDir(tdir):
                    zipextract(epub_path, tdir)

                    # Use our own simplified wrapper around an ePub that will
                    # preserve the file structure and css
                    container = ExtendedContainer(tdir, self.log)
                    is_modified = self._process_book(container, options)
                    if is_modified:
                        container.write(epub_path)

            # Only return path to the ePub if we have changed it
            if is_metadata_updated or is_modified:
                return epub_path
        except:
            self.log.exception('%s - ERROR: %s' %(title, traceback.format_exc()))
        finally:
            if calibre_opf_path and os.path.exists(calibre_opf_path):
                os.remove(calibre_opf_path)
            if cover_path and os.path.exists(cover_path):
                os.remove(cover_path)

    def _restore_metadata_from_opf(self, calibre_opf_path, cover_path):
        '''
        Create an mi object from our copy of the latest Calibre metadata
        stored in an OPF, so that we can perform functions that update
        the book metadata, such as generating a new jacket.
        '''
        if calibre_opf_path and os.path.exists(calibre_opf_path):
            with open(calibre_opf_path, 'r') as f:
                calibre_opf = OPF(f, os.path.dirname(calibre_opf_path))
            self.mi = calibre_opf.to_book_metadata()

        # Store our link to a copy of the book cover, so that we can perform
        # functions such as replacing the cover image.
        self.cover_path = cover_path

    def _update_metadata_and_cover(self, epub_path):
        self.log('\tUpdating metadata and cover')
        # Populate our mi object with the cover data
        if self.cover_path:
            if os.access(self.cover_path, os.R_OK):
                fmt = self.cover_path.rpartition('.')[-1]
                data = open(self.cover_path, 'rb').read()
                self.mi.cover_data = (fmt, data)
        with open(epub_path, 'r+b') as f:
            with apply_null_metadata:
                set_metadata(f, self.mi, stream_type='epub')
        return True # Going to "assume" it did something

    def _process_book(self, container, options):
        is_changed = False

        # MANIFEST OPTIONS
        if options['remove_missing_files']:
            is_changed |= self._remove_missing_files(container)
        if options['add_unmanifested_files']:
            is_changed |= self._process_unmanifested_files(container, add=True)
        elif options['remove_unmanifested_files']:
            is_changed |= self._process_unmanifested_files(container, add=False)
        if options['flatten_toc']:
            is_changed |= self._flatten_toc(container)
        if options['remove_broken_ncx_links']:
            is_changed |= self._remove_broken_ncx_links(container)

        # ADOBE OPTIONS
        if options['zero_xpgt_margins'] and not options['remove_xpgt_files']:
            is_changed |= self._zero_xpgt_margins(container)
        if options['remove_xpgt_files']:
            is_changed |= self._remove_xpgt_files(container)
        if options['remove_page_map']:
            is_changed |= self._remove_pagemaps(container)
        if options['remove_gp_page_map']:
            is_changed |= self._remove_gp_pagemaps(container)
        if options['remove_drm_meta_tags']:
            is_changed |= self._remove_drm_meta_tags(container)

        # JACKET OPTIONS
        if options['remove_legacy_jackets'] and not options['remove_all_jackets']:
            is_changed |= remove_legacy_jackets(container, self.log)
        if options['remove_all_jackets']:
            is_changed |= remove_all_jackets(container, self.log)
        if options['add_replace_jacket']:
            if options['jacket_end_book']:
                jacket_end_book = True
            else:
                jacket_end_book = False
            is_changed |= add_replace_jacket(container, self.log, self.mi, self.opts.output_profile, jacket_end_book)

        # METADATA/COVER OPTIONS
        if options['remove_broken_covers']:
            is_changed |= self._remove_broken_covers(container)
        if options['remove_cover'] and not options['insert_replace_cover']:
            is_changed |= self._remove_cover(container)
        if options['remove_non_dc_elements']:
            is_changed |= self._remove_non_dc_elements(container)

        # HTML/STYLE OPTIONS
        if options['encode_html_utf8']:
            is_changed |= self._encode_html_utf8(container)
        if options['remove_embedded_fonts']:
            is_changed |= self._remove_embedded_fonts(container)
        if options['rewrite_css_margins']:
            is_changed |= self._rewrite_css_margins(container)
        if options['append_extra_css']:
            is_changed |= self._append_extra_css(container)
        if options['remove_javascript']:
            is_changed |= self._remove_javascript(container)
        if options['smarten_punctuation']:
            is_changed |= self._smarten_punctuation(container)

        # FILE OPTIONS
        if options['strip_kobo']:
            is_changed |= self._strip_kobo(container)
        if options['remove_itunes_files']:
            is_changed |= self._remove_files_if_exist(container, ITUNES_FILES)
        if options['remove_calibre_bookmarks']:
            is_changed |= self._remove_files_if_exist(container, BOOKMARKS_FILES)
        if options['remove_os_artifacts']:
            is_changed |= self._remove_files_if_exist(container, OS_FILES)
        if options['remove_unused_images']:
            is_changed |= self._remove_unused_images(container)
        if options['strip_spans']:
            is_changed |= self._strip_spans(container)
        if options['unpretty']:
            is_changed |= self._unpretty(container)

        # WARNING: This must be the very last option run, because afterwards
        # the container object may not be perfectly synchronised with changes
        # made by inserting or updating covers.
        # Rather than re-initialising all the internal dictionaries etc. for
        # now will get away with it by running no modifications after it.
        if options['insert_replace_cover']:
            is_changed |= self._insert_replace_cover(container)

        return is_changed

    def _remove_files_if_exist(self, container, files):
        '''
        Helper function to remove items from manifest whose filename is
        in the set of 'files'
        '''
        dirtied = False
        self.log('\tLooking for files to remove:', files)
        files = [f.lower() for f in files]
        for name in list(container.name_path_map.keys()):
            found = False
            if name.lower() in files:
                found = True
            if not found:
                for f in files:
                    if name.lower().endswith('/'+f):
                        found = True
                        break
            if found:
                self.log('\t  Found file to remove:', name)
                container.delete_from_manifest(name)
                dirtied = True
        return dirtied

    def _remove_unused_images(self, container):
        self.log('\tLooking for unused images')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot remove unused images from DRM encrypted book')
            return False

        dirtied = container.remove_unused_images(container.get_image_names())
        return dirtied

    def _remove_missing_files(self, container):
        self.log('\tLooking for redundant entries in manifest')
        missing_files = set(container.mime_map.keys()) - set(container.name_path_map.keys())
        dirtied = False
        for name in missing_files:
            self.log('\t  Found entry to remove:', name)
            container.delete_from_manifest(name)
            dirtied = True
        if dirtied:
            container.set(container.opf_name, container.opf)
        return dirtied

    def _process_unmanifested_files(self, container, add=False):
        self.log('\tLooking for unmanifested files')
        all_artifacts = [f.lower() for f in ALL_ARTIFACTS]
        dirtied = False
        for name in list(container.manifest_worthy_names()):
            # Special exclusion for bookmarks, plist files and other OS artifacts
            known_artifact = False
            if name.lower() in all_artifacts:
                known_artifact = True
            if not known_artifact:
                for a in all_artifacts:
                    if name.lower().endswith('/'+a):
                        known_artifact = True
                        break
            if known_artifact:
                continue

            item = container.get_manifest_item_for_name(name)
            if item is None:
                if add:
                    self.log('\t  Found file to to add:', name)
                    ext = os.path.splitext(name)[1]
                    mt = None   # Let the mime-type be guessed from the extension
                    if ext.lower().startswith('.htm'):
                        # If this is really an xhtml file, need to explicitly declare it
                        raw = container.get_raw(name)
                        if raw.find('xmlns="http://www.w3.org/1999/xhtml"') != -1:
                            mt = guess_type('a.xhtml')[0]
                            self.log('\t Switching mimetype to:', mt)
                    container.add_name_to_manifest(name, mt)
                else:
                    self.log('\t  Found file to to remove:', name)
                    container.delete_name(name)
                dirtied = True
        if dirtied:
            container.set(container.opf_name, container.opf)
        return dirtied

    def _remove_non_dc_elements(self, container):
        self.log('\tLooking for non dc: elements in manifest')
        if not container.opf_name:
            self.log('\t  No opf manifest found')
            return False
        to_remove = []
        metadata = container.opf.xpath('//opf:metadata', namespaces={'opf':OPF_NS})[0]
        for child in metadata:
            try:
                if not child.tag.startswith('{http://purl.org/dc/'):
                    to_remove.append(child)
                    self.log('\t  Removing child:', child.tag)
            except:
                # Dunno how to elegantly handle in lxml parsing
                # text like <!-- stuff --> which blows up when
                # calling the .tag function.
                to_remove.append(child)
                self.log('\t  Removing child of commented out text:', child.text)
        if to_remove:
            for node in to_remove:
                metadata.remove(node)
            container.set(container.opf_name, container.opf)
        return bool(to_remove)

    def _flatten_toc(self, container):
        self.log('\tLooking for NCX to flatten')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot flatten TOC NCX in DRM encrypted book')
            return False
        return container.flatten_toc()

    def _remove_broken_ncx_links(self, container):
        self.log('\tLooking for broken links in the NCX')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot remove broken NCX links in DRM encrypted book')
            return False
        html_names_map = dict((k.lower(), True) for k in container.get_html_names())
        return container.delete_broken_toc_links(html_names_map)

    def _zero_xpgt_margins(self, container):
        dirtied = False
        self.log('\tLooking for Adobe xpgt page template margins')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot zero xpgt margins in DRM encrypted book')
            return False
        for name in container.get_xpgt_names():
            data = container.get_parsed_etree(name)
            if hasattr(data, 'xpath'):
                for elem in data.xpath(
                        '//*[@margin-bottom or @margin-top '
                        'or @margin-left or @margin-right]'):
                    for margin in ('left', 'right', 'top', 'bottom'):
                        attr = 'margin-'+margin
                        elem.attrib.pop(attr, None)
                        dirtied = True
            if dirtied:
                self.log('\t  Removed page margins from:', name)
                container.set(name, data)
                break
        return dirtied

    def _remove_xpgt_files(self, container):
        dirtied = False
        self.log('\tLooking for Adobe xpgt files and links to remove')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot remove xpgt files from DRM encrypted book')
            return False

        for name in list(container.get_xpgt_names()):
            self.log('\t  Found xpgt file to to remove:', name)
            container.delete_from_manifest(name)
            dirtied = True

        for name in container.get_html_names():
            html = container.get_parsed_etree(name)
            try:
                xpgt_links = XPath('//h:link[(@rel="stylesheet" or @rel="xpgt") and @href]')(html)
            except:
                xpgt_links = []
            for xpgt_link in xpgt_links:
                href = xpgt_link.get('href').lower()
                if href.endswith('.xpgt'):
                    xpgt_link.getparent().remove(xpgt_link)
                    self.log('\t  Removed xpgt link from:', name)
                    container.set(name, html)
                    dirtied = True

        # Look for import statments for xpgt files. Will support any of:
        # @import url(path); @import url("path"); @import url('path'); @import "path"
        # Plus the variations of semi-colon delimited or inlined style
        RE_CSS_IMPORT1 = re.compile(r'@import url\([\'\"]*(.*?)[\'"]*\)[^;<\-]*;?', re.UNICODE | re.DOTALL)
        RE_CSS_IMPORT2 = re.compile(r'@import\s+"(.*?)"[^;<\-]*;?', re.UNICODE | re.DOTALL)

        def compare_import_match(match, name, data):
            if match.group(1).lower().endswith('.xpgt'):
                data = data.replace(match.group(0), '')
                self.log('\t  Removed xpgt @import from:', name)
                container.set(name, data)
                return True

        for name in list(container.get_css_names()) + list(container.get_html_names()):
            data = container.get_raw(name)
            for match in RE_CSS_IMPORT1.finditer(data):
                if compare_import_match(match, name, data):
                    dirtied = True
            for match in RE_CSS_IMPORT2.finditer(data):
                if compare_import_match(match, name, data):
                    dirtied = True
        return dirtied

    def _remove_drm_meta_tags(self, container):
        RE_DRM_META = re.compile(r'(\n*\s*)?<meta [^>]*?name="adept\.[expctd\.]*?resource"[^>]*?>', re.UNICODE | re.IGNORECASE)
        dirtied = False
        self.log('\tLooking for Adobe DRM meta tags to remove')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot remove Adobe meta tags from DRM encrypted book')
            return False
        for name in container.get_html_names():
            html = container.get_raw(name)
            new_html = RE_DRM_META.sub('', html)
            if html != new_html:
                dirtied = True
                container.set(name, new_html)
                self.log('\t  Removed meta tag from:', name)
        return dirtied

    def _rewrite_css_margins(self, container):
        self.log('\tLooking for CSS margins')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot modify css margins in DRM encrypted book')
            return False
        mu = MarginsUpdater(self.log, container)
        dirtied = mu.rewrite_css_margins()
        return dirtied

    def _append_extra_css(self, container):
        self.log('\tLooking for extra CSS to append')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot append extra css in DRM encrypted book')
            return False
        mu = CSSUpdater(self.log, container)
        dirtied = mu.rewrite_css()
        return dirtied

    def _remove_embedded_fonts(self, container):
        RE_FONT_FACE = re.compile(r'@font\-face[^}]+?}\s*', re.UNICODE | re.IGNORECASE)
        self.log('\tLooking for embedded fonts')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot remove embedded fonts from DRM encrypted book')
            return False
        dirtied = False
        for name in list(container.name_path_map.keys()):
            if name.lower().endswith('.ttf') or name.lower().endswith('.otf'):
                self.log('\t  Found font to remove:', name)
                container.delete_from_manifest(name)
                dirtied = True

        self.log('\tLooking for css @font-face style declarations')
        for name in container.get_css_names():
            css = container.get_raw(name)
            new_css = RE_FONT_FACE.sub('', css)
            if css != new_css:
                dirtied = True
                container.set(name, new_css)
                self.log('\t  Removed @font-face from:', name)

        self.log('\tLooking for inline @font-face style declarations')
        for name in container.get_html_names():
            html = container.get_raw(name)
            new_html = RE_FONT_FACE.sub('', html)
            if html != new_html:
                dirtied = True
                container.set(name, new_html)
                self.log('\t  Removed @font-face from:', name)
        return dirtied

    def _encode_html_utf8(self, container):
        self.log('\tLooking for html files to remove charset meta tags/encode to utf-8')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot switch a DRM encrypted book to UTF-8 encoding')
            return False

        dirtied = False
        for name in container.get_html_names():
            html = container.get_raw(name)
            try:
                new_html = strip_encoding_declarations(html)
                #new_html = new_html.encode('utf-8')
                if not new_html.strip().startswith('<?xml'):
                    new_html = '<?xml version="1.0" encoding="utf-8"?>'+new_html
                    new_html = re.sub(r'<\?xml([^\?]*?)\?><', r'<?xml\1?>\n<', new_html)
                if new_html != html:
                    dirtied = True
                    container.set(name, new_html)
                    self.log('\t  Switched to UTF-8 encoding for:', name)
            except:
                pass
        return dirtied

    def _smarten_punctuation(self, container):
        from calibre.utils.smartypants import smartyPants
        from calibre.ebooks.chardet import substitute_entites
        from calibre.ebooks.conversion.utils import HeuristicProcessor
        from uuid import uuid4
        dirtied = False
        self.log('\tApplying smarten punctuation')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot smarten punctuation in DRM encrypted book')
            return False

        def smarten_punctuation_for_page(html):
            preprocessor = HeuristicProcessor(None, self.log)
            start = 'calibre-smartypants-'+str(uuid4())
            stop = 'calibre-smartypants-'+str(uuid4())
            html = html.replace('<!--', start)
            html = html.replace('-->', stop)
            html = preprocessor.fix_nbsp_indents(html)
            html = smartyPants(html)
            html = html.replace(start, '<!--')
            html = html.replace(stop, '-->')
            # convert ellipsis to entities to prevent wrapping
            html = re.sub(r'(?u)(?<=\w)\s?(\.\s?){2}\.', '&hellip;', html)
            # convert double dashes to em-dash
            html = re.sub(r'\s--\s', u'\u2014', html)
            return substitute_entites(html)

        for name in container.get_html_names():
            html = container.get_raw(name)
            new_html = smarten_punctuation_for_page(html)
            if html != new_html:
                dirtied = True
                container.set(name, new_html)
                self.log('\t  Smartened punctuation in:', name)
        return dirtied

    def _unpretty(self, container):
        dirtied = False
        self.log('\tUnprettying files')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot de-indent a DRM encrypted book')
            return False

        def unpretty_for_page(html_text):
            if re.search(r'<pre\s*([^>]*?)>', html_text, re.I):
                self.log('\t  Skipped:', name, ' - not safe to unpretty files which contain PRE elements.');
            else:
                html_text = re.sub(r'\r\n?', r'\n', html_text)
                html_text = re.sub(r'<!--([\s\S]*?)-->', r'', html_text)
                html_text = re.sub(r'</(b|h)r>', r'', html_text)
                html_text = re.sub(r'!DOCTYPE([^>]*?)\n([^>]*?)>', r'!DOCTYPE\1 \2>', html_text)
                html_text = re.sub(r'!DOCTYPE([^>]*?)>\s*', r'!DOCTYPE\1>\n', html_text)
                html_text = re.sub(r'>\n\s+<', r'>\n<', html_text)
                html_text = re.sub(r'\s+</([^>]+)>', r'</\1> ', html_text)
                html_text = re.sub(r'[^\S\n]+\n', r'\n', html_text)
                html_text = re.sub(r'<(\S+)([^/>]*?) style="display: ?none;?"([^/>]*?)></\1>', r'', html_text)
                html_text = re.sub(r'>\s*<(html|head|title|meta|link|style|body|h\d|ul|ol|li|p|div|section|nav|tr|td)([^>]*?)(/?)>', r'>\n<\1\2\3>', html_text)
                html_text = re.sub(r'<(h\d|li|p|div|section|nav|td)([^/>]*?)>\s*<(span|b|i|a|small)', r'<\1\2><\3', html_text)
                html_text = re.sub(r'<(span|b|i|a|u|em|strong|small)([^>]*?)> <(span|b|i|a|u|em|strong|small)', r' <\1\2><\3', html_text)
                html_text = re.sub(r'>\s+<(span|b|i|a|u|em|strong|big|small)', r'> <\1', html_text)
                html_text = re.sub(r'\s*<(section|nav|div)([^>]*?)>', r'\n<\1\2>', html_text)
                html_text = re.sub(r'<(section|nav|div)([^>]*?)>\s*', r'<\1\2>\n', html_text)
                html_text = re.sub(r'\s*</(title|body|html)>\s*', r'</\1>\n', html_text)
                html_text = re.sub(r'\s*</(h\d|ul|ol|p|table|tr)>\s*', r'</\1>\n\n', html_text)
                html_text = re.sub(r'\s*<(b|h)r([^>]*?)/?>\s*', r'<\1r\2/>\n', html_text)
                html_text = re.sub(r'<(meta|link)([^>]*?)/?>\s*', r'<\1\2/>\n', html_text)
                html_text = re.sub(r'>\n*<(body|h\d|ul|ol|p|hr|table)( ?)', r'>\n\n<\1\2', html_text)
                html_text = re.sub(r'<(body|table|tr)([^>]*?)>\n*', r'<\1\2>\n', html_text)
                html_text = re.sub(r'<td([^>]*?)>\n+', r'<td\1>\n', html_text)
                html_text = re.sub(r'\n+</td>', r'\n</td>', html_text)
                html_text = re.sub(r'\s*</(div|section|nav|table|tr|ul|ol|body)>', r'\n</\1>', html_text)
                html_text = re.sub(r'\s*</head>\s*', r'\n</head>\n\n', html_text)
                html_text = re.sub(r'\s*</(body|style)>', r'\n</\1>', html_text)
                html_text = re.sub(r'/html>\s+', r'/html>', html_text)
                html_text = re.sub(r' +', r' ', html_text)
            return html_text

        for name in container.get_html_names():
            orig_html = container.get_raw(name)
            html = orig_html
            new_html = unpretty_for_page(html)
            while html != new_html:
                dirtied = True
                html = new_html;
                new_html = unpretty_for_page(html)
            if orig_html != new_html:
                container.set(name, new_html)
                self.log('\t  De-indented:', name)
        return dirtied

    def _remove_pagemaps(self, container):
        self.log('\tLooking for pagemaps')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot remove pagemaps from DRM encrypted book')
            return False
        dirtied = False
        dirtied |= self._remove_gp_pagemaps(container)

        for name in list(container.get_pagemap_names()):
            mapcode = container.get_raw(name)
            self.log('\t  Removing pagemap file:', name)
            container.delete_from_manifest(name)
            dirtied = True
            html = container.get_raw(container.opf_name)
            new_html = re.sub(r'<spine page-map="([^"]+?)"', r'<spine', html)
            if html != new_html:
                container.set(container.opf_name, new_html)
                dirtied = True
        return dirtied

    def _remove_gp_pagemaps(self, container):
        self.log('\tLooking for Google Play pagemaps')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot remove pagemaps from DRM encrypted book')
            return False
        dirtied = False
        RE_GBS_ANCHOR1 = re.compile(r'<div( style="display:none;")?>\s*<a id="GBS\.\d+\.\d+"/>\s*</div>', re.UNICODE | re.IGNORECASE)
        RE_GBS_ANCHOR2 = re.compile(r'<a id="GBS\.\d+\.\d+"/>', re.UNICODE | re.IGNORECASE)

        for name in list(container.get_pagemap_names()):
            mapcode = container.get_raw(name)
            gbscheck = re.compile(r'#GBS\.\d+\.\d+')
            if gbscheck.search(mapcode) is not None:
                for hname in container.get_html_names():
                    html = container.get_raw(hname)
                    new_html = RE_GBS_ANCHOR1.sub('', html)
                    new_html = RE_GBS_ANCHOR2.sub('', new_html)
                    if html != new_html:
                        dirtied = True
                        container.set(hname, new_html)
                        html = new_html
                        self.log('\t  Removed Google Play anchors from:', hname)
                self.log('\t  Removing Google Play pagemap file:', name)
                container.delete_from_manifest(name)
                dirtied = True
                html = container.get_raw(container.opf_name)
                new_html = re.sub(r'<spine page-map="([^"]+?)"', r'<spine', html)
                if html != new_html:
                    container.set(container.opf_name, new_html)
                    dirtied = True
        return dirtied

    def _strip_spans(self, container):
        dirtied = False
        self.log('\tStripping spans')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot strip spans in DRM encrypted book')
            return False

        def strip_span_for_page(html_text):
            HTML_ENTITY = []

            html_text = re.sub(r'<(\S+)([^/>]*?) style="display: ?none;"([^/>]*?)></\1>', r'', html_text)
            html_text = re.sub(r'<(\S+)([^/>]*?)></\1>', r'<\1\2/>', html_text)
            html_text = re.sub(r'<([^>]*?)(\s+?)/>', r'<\1/>', html_text)
            html_text = re.sub(r'</(b|h)r>', r'', html_text)
            html_text = re.sub(r'<(b|h)r([^/>]*?)/?>', r'<\1r\2/>', html_text)
            html_text = re.sub(r'<(b|i|u|a|em|strong|span|big|small)/>', r'', html_text)
            html_text = re.sub(r'<\?dp([^>]*?)\?>\n?', r'', html_text)

            entities = re.split(r'(<.+?>)', html_text)

            total = 0
            for entity in entities:
                if entity:
                    entity = container.decode(entity)
                    total += 1
                    this_entity = TAG()
                    this_entity.content = entity
                    if entity == u'<span>':
                        this_entity.e_type = 9
                    elif entity[-2:] == u'/>':
                        this_entity.e_type = 3
                    elif entity[0] != u'<':
                        this_entity.e_type = 4
                    elif entity[:2] == u'</':
                        this_entity.e_type = 2
                    else:
                        this_entity.e_type = 1
                    HTML_ENTITY.append(this_entity)

            pos = -1
            PAIR = 0
            while pos < total-1:
                pos+=1
                if HTML_ENTITY[pos].e_type == 2:
                    PAIR += 1
                    HTML_ENTITY[pos].pair = PAIR
                    pair_pos = pos
                    while True:
                        pair_pos += -1
                        if pair_pos<0 : break
                        e_type = HTML_ENTITY[pair_pos].e_type
                        if e_type == 1 or e_type==9:
                            if HTML_ENTITY[pair_pos].pair == 0:
                                HTML_ENTITY[pair_pos].pair = PAIR
                                if e_type == 9: HTML_ENTITY[pos].e_type = 9
                                break

            output = []
            for entry in HTML_ENTITY:
                if entry.e_type < 9:
                    output.append(entry.content)

            out_text = ''.join(output)
            return out_text

        for name in container.get_html_names():
            orig_html = container.get_raw(name)
            html = orig_html
            new_html = strip_span_for_page(html)
            while html != new_html:
                dirtied = True
                html = new_html;
                new_html = strip_span_for_page(html)
            if orig_html != new_html:
                container.set(name, new_html)
                self.log('\t  Stripped spans in:', name)
        return dirtied

    def _strip_kobo(self, container):
        dirtied = False
        self.log('\tStripping Kobo remnants')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot strip Kobo remnants in DRM encrypted book')
            return False

        RE_KOBO_META1 = re.compile(r'\s*<!-- kobo-style -->', re.UNICODE | re.IGNORECASE)
        RE_KOBO_META2 = re.compile(r'\s*<script[^>]*? src="[^"]*?js/kobo(|-android)\.js"(/|></script)>', re.UNICODE | re.IGNORECASE)
        RE_KOBO_META3 = re.compile(r'\s*<style[^>]*? id="kobo[\s\S]*?</style>', re.UNICODE | re.IGNORECASE)
        RE_KOBO_META4 = re.compile(r'\s*<link[^>]*? href="[^"]*?css/kobo(|-android)\.css"[\s\S]*?(/|></link)>', re.UNICODE | re.IGNORECASE)
        dirtied = False
        for name in container.get_html_names():
            html = container.get_raw(name)
            new_html = RE_KOBO_META1.sub('', html)
            new_html = RE_KOBO_META2.sub('', new_html)
            new_html = RE_KOBO_META3.sub('', new_html)
            new_html = RE_KOBO_META4.sub('', new_html)
            if html != new_html:
                dirtied = True
                container.set(name, new_html)
                self.log('\t  Removed Kobo HEAD elements from:', name)

        for name in list(container.name_path_map.keys()):
            if name.lower().endswith('js/kobo.js'):
                self.log('\t  Removed kobo.js file:', name)
                container.delete_from_manifest(name)
                dirtied = True
            elif name.lower().endswith('css/kobo.css'):
                self.log('\t  Removed kobo.css file:', name)
                container.delete_from_manifest(name)
                dirtied = True
            elif name.lower() == 'rights.xml':
                self.log('\t  Removed rights.xml file:', name)
                container.delete_from_manifest(name)
                dirtied = True

        def strip_kobo_for_page(html_text):
            HTML_ENTITY = []

            html_text = re.sub(r'<(\S+)([^/>]*?)></\1>', r'<\1\2/>', html_text)
            html_text = re.sub(r'<([^>]*?)(\s+?)/>', r'<\1/>', html_text)
            html_text = re.sub(r'<span([^>]+?) id="kobo([^"]+?)"', r'<span id="kobo\2"\1', html_text)
            html_text = re.sub(r'</(b|h)r>', r'', html_text)
            html_text = re.sub(r'<(b|h)r([^/>]*?)/?>', r'<\1r\2/>', html_text)
            html_text = re.sub(r'<(b|i|u|a|em|strong|span|big|small)/>', r'', html_text)

            entities = re.split(r'(<.+?>)', html_text)

            total = 0
            for entity in entities:
                if entity:
                    entity = container.decode(entity)
                    total += 1
                    this_entity = TAG()
                    this_entity.content = entity
                    if entity[:15] == u'<span id="kobo.':
                        this_entity.e_type = 9
                    elif entity[-2:] == u'/>':
                        this_entity.e_type = 3
                    elif entity[0] != u'<':
                        this_entity.e_type = 4
                    elif entity[:2] == u'</':
                        this_entity.e_type = 2
                    else:
                        this_entity.e_type = 1
                    HTML_ENTITY.append(this_entity)

            pos = -1
            PAIR = 0
            while pos < total-1:
                pos+=1
                if HTML_ENTITY[pos].e_type == 2:
                    PAIR += 1
                    HTML_ENTITY[pos].pair = PAIR
                    pair_pos = pos
                    while True:
                        pair_pos += -1
                        if pair_pos<0 : break
                        e_type = HTML_ENTITY[pair_pos].e_type
                        if e_type == 1 or e_type==9:
                            if HTML_ENTITY[pair_pos].pair == 0:
                                HTML_ENTITY[pair_pos].pair = PAIR
                                if e_type == 9: HTML_ENTITY[pos].e_type = 9
                                break

            output = []
            for entry in HTML_ENTITY:
                if entry.e_type < 9:
                    output.append(entry.content)

            out_text = ''.join(output)
            return out_text

        for name in container.get_html_names():
            html = container.get_raw(name)
            new_html = strip_kobo_for_page(html)
            if html != new_html:
                dirtied = True
                container.set(name, new_html)
                self.log('\t  Stripped Kobo spans in:', name)
        return dirtied

    def _remove_javascript(self, container):
        dirtied = False
        self.log('\tLooking for inline javascript blocks to remove')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot remove javascript from DRM encrypted book')
            return False
        for name in container.get_html_names():
            html = container.get_parsed_etree(name)
            try:
                scripts = XPath('//h:script[@type="text/javascript"]')(html)
            except:
                scripts = []
            if scripts:
                for script in scripts:
                    script.getparent().remove(script)
                    self.log('\t  Removed script block from:', name)
                dirtied = True
                container.set(name, html)

        self.log('\tLooking for .js files to remove')
        for name in list(container.name_path_map.keys()):
            if name.lower().endswith('.js'):
                self.log('\t  Found .js file to remove:', name)
                container.delete_from_manifest(name)
                dirtied = True
        return dirtied

    def _remove_broken_covers(self, container):
        dirtied = False
        self.log('\tLooking for html pages containing only broken image links')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot remove broken covers from DRM encrypted book')
            return False

        avail_image_names = {x.lower() : True for x in container.get_image_names()}
        if not avail_image_names:
            return False

        names_to_delete = []

        for html_name in container.get_html_names():
            delete_candidate = False
            for image_name, orig_href, _node in container.get_page_image_names(html_name):
                if image_name.lower() in avail_image_names:
                    # This page has at least one valid link
                    delete_candidate = False
                    break
                else:
                    # This page has a broken link
                    self.log('\t    Broken image link: "%s" in: %s'%(orig_href, html_name))
                    delete_candidate = True

            if delete_candidate:
                names_to_delete.append(html_name)

        for html_name in names_to_delete:
            # Verify there is no other text within the body of this document.
            if container.get_body_text(html_name):
                self.log('\t  Body contains other text so will not be removed:', html_name)
                continue
            else:
                dirtied = True
                self.log('\t  Removing html containing only broken image link:', html_name)
                container.delete_from_manifest(html_name)
        return dirtied

    def _remove_cover(self, container):
        self.log('\tRemove cover')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot remove cover in DRM encrypted book')
            return False
        cu = CoverUpdater(self.log, container, None, None)
        cu.remove_existing_cover()
        return True

    def _insert_replace_cover(self, container):
        self.log('\tInsert or replace cover')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot insert/replace cover in DRM encrypted book')
            return False
        if not self.cover_path:
            self.log('\t  ERROR - no cover image assigned to this book in the library')
            return False

        cu = CoverUpdater(self.log, container, self.cover_path, self.opts)
        cu.insert_or_replace_cover()
        return True

    def _setup_user_options(self):
        '''
        Initialise the self.opts which is required for passing to some of the
        tasks within this plugin that are utilising calibre pipeline code or
        are wanting to lookup the user's default values
        '''
        def get_user_margins():
            default_margins = {
                'margin_right' : 5.0,
                  'margin_top' : 5.0,
                 'margin_left' : 5.0,
               'margin_bottom' : 5.0,
                        }
            prefs_margins = {}

            from calibre.ebooks.conversion.config import load_defaults
            ps = load_defaults('page_setup')
            if 'margin_top' in ps:
                prefs_margins = ps
            else:
                prefs_margins = default_margins

            for s, v in six.iteritems(prefs_margins):
                setattr(self.opts, s, v)

        def get_epub_output_options():
            default_values = {
                'preserve_cover_aspect_ratio' : False,
                'no_svg_cover' : False
                        }
            prefs_options = {}

            from calibre.ebooks.conversion.config import load_defaults
            ps = load_defaults('epub_output')
            if 'preserve_cover_aspect_ratio' in ps:
                prefs_options = ps
            else:
                prefs_options = default_values

            for s, v in six.iteritems(prefs_options):
                setattr(self.opts, s, v)

        self.opts = OptionValues()
        get_user_margins()
        get_epub_output_options()
        self.opts.output_profile = self._get_output_profile()
        self.opts.dest = self.opts.output_profile

    def _get_output_profile(self):
        from calibre.ebooks.conversion.config import load_defaults
        from calibre.customize.ui import output_profiles
        ps = load_defaults('page_setup')
        output_profile_name = 'default'
        if 'output_profile' in ps:
            output_profile_name = ps['output_profile']
        for x in output_profiles():
            if x.short_name == output_profile_name:
                return x
        self.log.warn('Output Profile %s is no longer available, using default'%output_profile_name)
        for x in output_profiles():
            if x.short_name == 'default':
                return x
