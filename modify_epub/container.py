from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import six
from six import text_type as unicode
from six.moves import range
from polyglot.builtins import unicode_type, is_py3

import os, posixpath, sys, re
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error

from lxml import etree
from lxml.etree import XMLSyntaxError
from six.moves.urllib.parse import urldefrag, urlparse, urlunparse
from six.moves.urllib.parse import unquote as urlunquote

from calibre import guess_type, prepare_string_for_xml
from calibre.ebooks.chardet import xml_to_unicode
from calibre.ebooks.conversion.plugins.epub_input import (
    ADOBE_OBFUSCATION, IDPF_OBFUSCATION, decrypt_font)
from calibre.ebooks.conversion.preprocess import HTMLPreProcessor
from calibre.ebooks.oeb.base import urlnormalize, OEB_DOCS, XPath, SVG, XLINK
from calibre.ebooks.oeb.parse_utils import NotHTML, parse_html
from calibre.utils.zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

RECOVER_PARSER = etree.XMLParser(recover=True, no_network=True, resolve_entities=False)

exists, join = os.path.exists, os.path.join

OCF_NS = 'urn:oasis:names:tc:opendocument:xmlns:container'
OPF_NS = 'http://www.idpf.org/2007/opf'
NCX_NS = 'http://www.daisy.org/z3986/2005/ncx/'

IMAGE_FILES = ['.png','.jpg','.jpeg', '.gif', '.bmp', '.svg']
FONT_FILES = ['.otf','.ttf']
NON_HTML_FILES = IMAGE_FILES + FONT_FILES + ['.opf', '.xpgt', '.ncx', '.css']

class InvalidEpub(ValueError):
    pass

class ParseError(ValueError):

    def __init__(self, name, desc):
        self.name = name
        self.desc = desc
        ValueError.__init__(self,
            _('Failed to parse: %(name)s with error: %(err)s')%dict(
                name=name, err=desc))

class Container(object):
    '''
    Originally this plugin tried to use a Container class used in the calibre
    source code. However having overriden so many methods to fix bugs or alter
    behaviour to suit my needs in the end I gave up on inheritance and copied.
    '''

    META_INF = {
            'container.xml' : True,
            'manifest.xml' : False,
            'encryption.xml' : False,
            'metadata.xml' : False,
            'signatures.xml' : False,
            'rights.xml' : False,
    }

    def __init__(self, path, log):
        self.root = os.path.abspath(path)
        self.log = log
        self.dirtied = set([])
        self.raw_data_map = {}
        self.etree_data_map = {}
        self.mime_map = {}
        self.opf_name = None
        self.opf_dir = None
        self.html_preprocessor = HTMLPreProcessor()

        if exists(join(self.root, 'mimetype')):
            os.remove(join(self.root, 'mimetype'))

        container_path = join(self.root, 'META-INF', 'container.xml')
        if not exists(container_path):
            raise InvalidEpub('No META-INF/container.xml in epub')
        self.container = etree.fromstring(open(container_path, 'rb').read())
        opf_files = self.container.xpath((
            r'child::ocf:rootfiles/ocf:rootfile'
            '[@media-type="%s" and @full-path]'%unicode_type(guess_type('a.opf')[0])
            ), namespaces={'ocf':OCF_NS}
        )
        if not opf_files:
            raise InvalidEpub('META-INF/container.xml contains no link to OPF file')
        opf_path = os.path.join(self.root, *opf_files[0].get('full-path').split('/'))
        if not exists(opf_path):
            raise InvalidEpub('OPF file does not exist at location pointed to'
                    ' by META-INF/container.xml')

        # Map of relative paths with '/' separators from root of unzipped ePub
        # to absolute paths on filesystem with os-specific separators
        self.name_path_map = {}
        for dirpath, _dirnames, filenames in os.walk(self.root):
            for f in filenames:
                path = join(dirpath, f)
                name = os.path.relpath(path, self.root).replace(os.sep, '/')
                self.name_path_map[name] = path
                # Special case if we have stumbled onto the opf manifest
                if path == opf_path:
                    self.opf_name = name
                    self.opf_dir = posixpath.dirname(self.opf_name)
                    self.mime_map[name] = guess_type('a.opf')[0]

        for item in self.opf.xpath(
                '//opf:manifest/opf:item[@href and @media-type]',
                namespaces={'opf':OPF_NS}):
            href = item.get('href')
            self.mime_map[self.href_to_name(href)] = item.get('media-type')

        self.ncx = self.ncx_name = None
        for name in self.manifest_worthy_names():
            if name.endswith('.ncx'):
                try:
                    self.ncx_name = name
                    self.ncx = self.get_parsed_etree(self.ncx_name)
                except ParseError:
                    # This ePub is probably protected with DRM and the NCX is encrypted
                    self.ncx_name = None
                    self.ncx = None
                break

    def manifest_worthy_names(self):
        for name in self.name_path_map:
            if name.endswith('.opf'): continue
            if name.startswith('META-INF') and \
                    posixpath.basename(name) in self.META_INF: continue
            yield name

    def get_manifest_item_for_name(self, name):
        href = self.name_to_href(name)
        q = prepare_string_for_xml(href, attribute=True)
        existing = self.opf.xpath('//opf:manifest/opf:item[@href="%s"]'%q,
                namespaces={'opf':OPF_NS})
        if not existing:
            # Try again with unquoting special characters like %20
            q = urlunquote(q)
            existing = self.opf.xpath('//opf:manifest/opf:item[@href="%s"]'%q,
                    namespaces={'opf':OPF_NS})
        if not existing:
            return None
        return existing[0]

    @property
    def opf(self):
        return self.get_parsed_etree(self.opf_name)

    def href_to_name(self, href, rel_to_opf=True, base=''):
        '''
        Changed to fix a bug in the Calibre function which incorrectly
        splits the href on # when # is part of the filename, and also
        to normalise the path.
        '''
        hash_index = href.find('#')
        period_index = href.find('.')
        if hash_index > 0 and hash_index > period_index:
            href = href.partition('#')[0]
        href = urlunquote(href)
        name = href
        if not base and rel_to_opf:
            base = self.opf_dir
        if base:
            name = posixpath.join(base, href)
        name = os.path.normpath(name).replace('\\', '/')
        return name

    def name_to_href(self, name, rel_to_opf=True, base=''):
        '''
        Changed to ensure that blank href names are correctly
        referenced as "" rather than "."
        '''
        if not base and rel_to_opf:
            base = self.opf_dir
        if not base:
            return six.moves.urllib.parse.quote(name)
        href = posixpath.relpath(name, base)
        if href == '.':
            href = ''
        return six.moves.urllib.parse.quote(href)

    def abshref(self, href, base_name):
        """Convert the URL provided in :param:`href` from a reference
        relative to the base_name to a book-absolute reference.
        """
        purl = urlparse(href)
        scheme = purl.scheme
        if scheme and scheme != 'file':
            return href
        purl = list(purl)
        purl[0] = ''
        href = urlunparse(purl)
        path, frag = urldefrag(href)
        if not path:
            if frag:
                return '#'.join((base_name, frag))
            else:
                return base_name
        if '/' not in base_name:
            return href
        dirname = os.path.dirname(base_name)
        href = os.path.join(dirname, href)
        href = os.path.normpath(href).replace('\\', '/')
        return href

    def get_raw(self, name):
        '''
        Return the named resource as raw data
        '''
        if name in self.raw_data_map:
            return self.raw_data_map[name]
        path = self.name_path_map[name]
        extension = name[name.lower().rfind('.'):].lower()
        # Defensive code: can't be sure that the file is text
        try:
            try:
                with open(path, 'r') as f:
                    raw = f.read()
            except:
                with open(path, 'rb') as f:
                    raw = f.read()
        except:
            self.log('Exception in get_raw: name=', name)
            raise
        self.raw_data_map[name] = raw
        return raw

    def get_parsed_etree(self, name):
        '''
        Return the named resource as an etree parsed object for XPath expressions
        '''
        if name in self.etree_data_map:
            return self.etree_data_map[name]
        data = self.get_raw(name)
        if name in self.mime_map:
            mt = self.mime_map[name].lower()
            try:
                if mt in OEB_DOCS:
                    data = self._parse_xhtml(data, name)
                elif mt[-4:] in ('+xml', '/xml'):
                    self.log('\t  Parsing xml file:', name)
                    data = self._parse_xml(data)
            except XMLSyntaxError as err:
                raise ParseError(name, unicode(err))
        if hasattr(data, 'xpath'):
            self.etree_data_map[name] = data
        return data

    def _parse_xml(self, data):
        data = xml_to_unicode(data, strip_encoding_pats=True, assume_utf8=True,
                             resolve_entities=True)[0].strip()
        return etree.fromstring(data, parser=RECOVER_PARSER)

    def _parse_xhtml(self, data, name):
        orig_data = data
        fname = urlunquote(name)
        try:
            data = parse_html(data, log=self.log,
                    decoder=self.decode,
                    preprocessor=self.html_preprocessor,
                    filename=fname, non_html_file_tags={'ncx'})
        except NotHTML:
            return self._parse_xml(orig_data)
        return data

    def get_spine_items(self):
        spine_items = self.opf.xpath('//opf:spine', namespaces={'opf':OPF_NS})[0]
        for spine_item in spine_items:
            _id = spine_item.get('idref')
            item = self.get_manifest_item_by_id(_id)
            if item is not None:
                yield item

    def get_guide_reference(self, ref_type):
        '''
        Return the guide reference element matching this type if specified.
        '''
        references = self.opf.xpath('//opf:guide/opf:reference[@type="%s"]'%ref_type,
                                    namespaces={'opf':OPF_NS})
        if len(references):
            return references[0]
        return None

    def get_manifest_item_by_id(self, id):
        '''
        Return the manifest item element matching this @id.
        '''
        items = self.opf.xpath('//opf:manifest/opf:item[@id="%s"]'%id,
                                    namespaces={'opf':OPF_NS})
        if len(items) > 0:
            return items[0]
        return None

    def get_meta_content_item(self, name):
        meta_items = self.opf.xpath('//opf:metadata/opf:meta[@name="%s" and @content]'%name,
                                     namespaces={'opf':OPF_NS})
        if len(meta_items):
            return meta_items[0]

    def get_toc_navpoint_content(self, item):
        '''
        Given a manifest item, look through the TOC for a matching content
        element with an @src attribute that points to the same href.
        If found, returns that content node.
        '''
        if not self.ncx_name:
            self.log('\t  No NCX found')
            return None
        href = self.href_to_name(item.get('href'))
        xp = self.ncx.xpath('//ncx:navPoint', namespaces={'ncx':NCX_NS})
        if xp:
            for navpoint in xp:
                content = navpoint.xpath('ncx:content', namespaces={'ncx':NCX_NS})
                if len(content):
                    src = urlunquote(content[0].get('src', None)).partition('#')[0]
                    src_name = self.abshref(src, self.ncx_name)
                    if src_name.lower() == href.lower():
                        return content[0]
        return None

    def decode(self, data, input_encoding = 'utf-8'):
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
        if input_encoding:
            try:
                return fix_data(data.decode(input_encoding, 'replace'))
            except UnicodeDecodeError:
                pass
        try:
            return fix_data(data.decode('utf-8'))
        except UnicodeDecodeError:
            pass
        data, _ = xml_to_unicode(data)
        return fix_data(data)


class WritableContainer(Container):
    '''
    Extensions to Container to do with deleting/modifying the contents
    of the ePub and writing back to disk.
    '''

    def fix_tail_after_insert(self, item):
        '''
        Designed only to work with self closing elements after item has
        just been inserted/appended
        '''
        parent = item.getparent()
        idx = parent.index(item)
        if idx == 0:
            item.tail = parent.text
            # If this is the only child of this parent element, we need a little extra work as we have
            # gone from a self-closing <foo /> element to <foo><item /></foo>
            if len(parent) == 1:
                sibling = parent.getprevious()
                if sibling is None:
                    # Give up!
                    return
                parent.text = sibling.text
                item.tail = sibling.tail
        else:
            item.tail = parent[idx-1].tail
            if idx == len(parent)-1:
                parent[idx-1].tail = parent.text

    def fix_tail_before_delete(self, item):
        '''
        Designed only to work with self closing elements just before item
        is deleted
        '''
        parent = item.getparent()
        idx = parent.index(item)
        if idx == 0:
            # We are removing the first time - only care about adjusting
            # the tail if this was the only child
            if len(parent) == 1:
                parent.text = item.tail
        else:
            # Make sure the preceding item has this tail
            parent[idx-1].tail = item.tail

    def add_name_to_manifest(self, name, mt=None):
        item = self.get_manifest_item_for_name(name)
        if item is not None:
            return
        manifest = self.opf.xpath('//opf:manifest', namespaces={'opf':OPF_NS})[0]
        item = manifest.makeelement('{%s}item'%OPF_NS, nsmap={'opf':OPF_NS},
                href=self.name_to_href(name),
                id=self.generate_manifest_id())
        if not mt:
            mt = guess_type(posixpath.basename(name))[0]
        if not mt:
            mt = 'application/octest-stream'
        item.set('media-type', mt)
        manifest.append(item)
        self.fix_tail_after_insert(item)

    def generate_manifest_id(self):
        items = self.opf.xpath('//opf:manifest/opf:item[@id]',
                namespaces={'opf':OPF_NS})
        ids = set([x.get('id') for x in items])
        # sys.maxsize returns a too-large integer on P2.7 64-bit systems.
        # Fortunately we don't need trillions of ids. Set the max to
        # something arbitrary such as 1 billion. :)
        for x in range(1, 1000000000):
            c = 'id%d'%x
            if c not in ids:
                return c

    def generate_unique(self, id=None, href=None):
        '''
        Generate a new unique identifier and/or internal path for use in
        creating a new manifest item, using the provided :param:`id` and/or
        :param:`href` as bases.

        Returns an two-tuple of the new id and path.  If either :param:`id` or
        :param:`href` are `None` then the corresponding item in the return
        tuple will also be `None`.

        Grant: Copied/modified from calibre.ebooks.oeb.base.Manifest
        '''
        if id is not None:
            items = self.opf.xpath('//opf:manifest/opf:item[@id]',
                    namespaces={'opf':OPF_NS})
            ids = set([x.get('id') for x in items])

            base = id
            index = 1
            while id in ids:
                id = base + str(index)
                index += 1
        if href is not None:
            items = self.opf.xpath('//opf:manifest/opf:item[@href]',
                    namespaces={'opf':OPF_NS})
            hrefs = set([x.get('href') for x in items])

            href = urlnormalize(href)
            base, ext = os.path.splitext(href)
            index = 1
            lhrefs = set([x.lower() for x in hrefs])
            while href.lower() in lhrefs:
                href = base + str(index) + ext
                index += 1
        return id, href

    def add_to_manifest(self, id, href, mt=None):
        '''
        Given an id and an href, create an item in the manifest for it
        '''
        manifest = self.opf.xpath('//opf:manifest', namespaces={'opf':OPF_NS})[0]
        item = manifest.makeelement('{%s}item'%OPF_NS, nsmap={'opf':OPF_NS},
                href=href, id=id)
        if not mt:
            mt = guess_type(href)[0]
        if not mt:
            mt = 'application/octest-stream'
        item.set('media-type', mt)
        manifest.append(item)
        self.fix_tail_after_insert(item)
        self.log('\t  Manifest item added: %s (%s)'%(href, id))
        self.set(self.opf_name, self.opf)

    def add_to_spine(self, id, index=-1):
        '''
        Given an id, add it to the spine, optionally at the specified position
        '''
        spine = self.opf.xpath('//opf:spine', namespaces={'opf':OPF_NS})[0]
        itemref = spine.makeelement('{%s}itemref'%OPF_NS, nsmap={'opf':OPF_NS},
                idref=id)
        if index >= 0:
            spine.insert(index, itemref)
        else:
            spine.append(itemref)
        self.fix_tail_after_insert(itemref)
        self.log('\t  Spine item inserted: %s at pos: %d'%(id, index))
        self.set(self.opf_name, self.opf)

    def add_to_guide(self, href, title, ref_type):
        '''
        Add a reference to the guide
        '''
        guides = self.opf.xpath('//opf:guide', namespaces={'opf':OPF_NS})
        if len(guides):
            guide = guides[0]
        else:
            # This ePub does not currently have a <guide> section
            self.log('\t  No guide parent element found - inserting one')
            guide = self.opf.makeelement('{%s}guide'%OPF_NS, nsmap={'opf':OPF_NS})
            self.opf.append(guide)
            self.fix_tail_after_insert(guide)

        attrib = { 'href':href, 'title':title, 'type':ref_type }
        reference = etree.SubElement(guide, '{%s}reference'%OPF_NS,
                                     attrib=attrib, nsmap={'opf':OPF_NS})
        guide.append(reference)
        self.fix_tail_after_insert(reference)
        self.log('\t  Guide item inserted: %s:%s:%s'%(href,title,ref_type))
        self.set(self.opf_name, self.opf)

    def add_to_metadata(self, name, id, index=-1):
        '''
        Add a <meta name="xxx" content="id" /> tag
        '''
        metadata = self.opf.xpath('//opf:metadata', namespaces={'opf':OPF_NS})[0]
        # Going to insert without the namespace, as found issue where namespace was "double declared"
        # on both the <package> and the <metadata> tag above (prefixed with 'opf' in latter case). As
        # when writing out the xml it would keep the prefix, which looks ugly. ePub should not really
        # need to redefine the opf namespace on the <metadata> element.
        meta = metadata.makeelement('meta')
        meta.attrib['name'] = name
        meta.attrib['content'] = id
        if index >= 0:
            metadata.insert(index, meta)
        else:
            metadata.append(meta)
        self.fix_tail_after_insert(meta)
        self.log('\t  Meta item inserted: %s:%s'%(name,id))
        self.set(self.opf_name, self.opf)

    def delete_name(self, name):
        '''
        Overridden to ensure that it will not blow up if called with
        a name that is not in the map
        '''
        if name in self.mime_map:
            self.mime_map.pop(name, None)
        if name in self.name_path_map:
            path = self.name_path_map[name]
            os.remove(path)
            self.name_path_map.pop(name)

    def delete_from_manifest(self, name, delete_from_toc=True):
        '''
        Remove this item from the manifest, spine, guide and TOC ncx if it exists
        '''
        self.delete_name(name)
        if name in self.raw_data_map:
            self.raw_data_map.pop(name)
        self.dirtied.discard(name)
        item = self.get_manifest_item_for_name(name)
        if item is None:
            return
        manifest = self.opf.xpath('//opf:manifest', namespaces={'opf':OPF_NS})[0]
        self.log('\t  Manifest item removed: %s (%s)'%(item.get('href'), item.get('id')))
        self.fix_tail_before_delete(item)
        manifest.remove(item)
        self.set(self.opf_name, self.opf)

        # Now remove the item from the spine if it exists
        self.delete_from_spine(item)

        # Remove from the guide if it exists
        self.delete_from_guide(item)

        # Finally remove the item from the TOC
        if delete_from_toc:
            self.delete_from_toc(item)

    def delete_from_spine(self, item):
        '''
        Given a manifest item, remove it from the spine
        '''
        item_id = item.get('id')
        itemrefs = self.opf.xpath('//opf:spine/opf:itemref[@idref="%s"]'%item_id,
                namespaces={'opf':OPF_NS})
        if len(itemrefs) > 0:
            self.log('\t  Spine itemref removed:', item_id)
            itemref = itemrefs[0]
            self.fix_tail_before_delete(itemref)
            itemref.getparent().remove(itemref)
            self.set(self.opf_name, self.opf)

    def delete_from_guide(self, item):
        '''
        Given a guide or manifest item, remove it from the guide
        '''
        item_href = item.get('href')
        references = self.opf.xpath('//opf:guide/opf:reference[@href="%s"]'%item_href,
                namespaces={'opf':OPF_NS})
        if len(references):
            self.log('\t  Guide reference removed: %s'%item_href)
            reference = references[0]
            self.fix_tail_before_delete(reference)
            reference.getparent().remove(reference)
            self.set(self.opf_name, self.opf)

    def delete_from_metadata(self, meta_item):
        '''
        Given a meta item, remove it from the metadata section
        '''
        self.log('\t  Meta item removed: %s'%meta_item.get('name'))
        self.fix_tail_before_delete(meta_item)
        meta_item.getparent().remove(meta_item)
        self.set(self.opf_name, self.opf)

    def delete_from_toc(self, item=None, item_name=None):
        '''
        Given an item from the manifest or the name of an item,
        remove any matching entry from the TOC ncx file
        '''
        def test_navpoint_for_removal(navpoint):
            src = navpoint.xpath('ncx:content/@src', namespaces={'ncx':NCX_NS})
            if len(src):
                src = src[0].partition('#')[0]
                src_name = self.abshref(src, self.ncx_name)
                if src_name.lower() == item_name.lower():
                    self.log('\t  TOC Navpoint removed of:', src)
                    return True
            return False

        if self.ncx_name is None:
            return
        if item is None and item_name is None:
            return
        dirtied = False
        if item is not None:
            item_name = self.href_to_name(item.get('href'))
        for navpoint in self.ncx.xpath('//ncx:navPoint', namespaces={'ncx':NCX_NS}):
            if test_navpoint_for_removal(navpoint):
                dirtied = True
                p = navpoint.getparent()
                idx = p.index(navpoint)
                p.remove(navpoint)
                for child in reversed(navpoint):
                    if child.tag == '{%s}navPoint'%NCX_NS:
                        self.log('\t  TOC Navpoint child promoted')
                        p.insert(idx, child)
        if self._fix_toc_playorder() or dirtied:
            self._indent(self.ncx)
            self.set(self.ncx_name, self.ncx)
            dirtied = True

    def _fix_toc_playorder(self):
        playorder_changed = False
        order = 1
        for navpoint in self.ncx.xpath('//ncx:navPoint', namespaces={'ncx':NCX_NS}):
            existing = navpoint.get("playOrder")
            if existing:
                if existing != str(order):
                    self.log("\t  Changing playOrder from: %s to: %s"%(existing, str(order)))
                    navpoint.attrib["playOrder"] = str(order)
                    playorder_changed = True
                order += 1
        return playorder_changed

    def _indent(self, elem, level=0):
        i = '\n' + level*'  '
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + '  '
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for e in elem:
                self._indent(e, level+1)
            if not e.tail or not e.tail.strip():
                e.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def set(self, name, val):
        if hasattr(val, 'xpath'):
            self.etree_data_map[name] = val
            val = unicode_type(etree.tostring(val, encoding='unicode'))
        else:
            # If we have modified the raw text directly then it invalidates
            # any etree we may have stored, so clear from the cache.
            if name in self.etree_data_map:
                self.etree_data_map.pop(name)
        self.raw_data_map[name] = val
        self.dirtied.add(name)

    def write(self, path):
        '''
        Overridden to change how the zip file is assembled as found
        issues with the add_dir function as it was written
        '''
        #self.log('Writing epub contents back to zipfile:', path)
        for name in self.dirtied:
            raw = self.raw_data_map[name]
            #self.log('  Updating file:', self.name_path_map[name])
            if is_py3:
                with open(self.name_path_map[name], 'w', newline='') as f:
                    f.write(raw)
            else:
                with open(self.name_path_map[name], 'w') as f:
                    f.write(raw)
        self.dirtied.clear()
        with ZipFile(path, 'w', compression=ZIP_DEFLATED) as zf:
            # Write mimetype
            zf.writestr('mimetype', guess_type('a.epub')[0], compression=ZIP_STORED)
            # Write everything else
            exclude_files = ['.DS_Store','mimetype']
            for root, _dirs, files in os.walk(self.root):
                for fn in files:
                    if fn in exclude_files:
                        continue
                    absfn = os.path.join(root, fn)
                    zfn = os.path.relpath(absfn,
                            self.root).replace(os.sep, '/')
                    zf.write(absfn, zfn)

class ExtendedContainer(WritableContainer):
    '''
    Extend the our container object with additional functions
    that assist with working with sets of content specific to Modify ePub
    '''

    def is_drm_encrypted(self):
        for name in self.name_path_map.keys():
            if name.lower().endswith('encryption.xml'):
                try:
                    root = etree.fromstring(open(name, 'rb').read())
                    for em in root.xpath('//*[local-name()="EncryptionMethod" and @Algorithm]'):
                        alg = em.get('Algorithm')
                        if alg not in {ADOBE_OBFUSCATION, IDPF_OBFUSCATION}:
                            return True
                except ParseError:
                    # Having a problem reading the encryption xml
                    self.log.error('Error parsing encryption xml for DRM check')
                return False
        return False

    def get_pagemap_names(self):
        '''
        Helper function to return list of pagemap name(s) from this epub
        '''
        PAGEMAP_MIME_TYPES = ['application/oebps-page-map+xml']
        for name in self.name_path_map:
            mt = self.mime_map.get(name, '')
            if (mt.lower() in PAGEMAP_MIME_TYPES):
                yield name

    def get_xpgt_names(self):
        '''
        Helper function to return list of xpgt name(s) from this epub
        '''
        TEMPLATE_MIME_TYPES = ['application/adobe-page-template+xml',
                               'application/vnd.adobe-page-template+xml',
                               'application/vnd.adobe.page-template+xml']
        for name in self.name_path_map:
            mt = self.mime_map.get(name, '')
            if (mt.lower() in TEMPLATE_MIME_TYPES):
                yield name

    def get_html_names(self):
        '''
        Helper function to return the manifest names of the html/xhtml content files
        '''
        for name in self.name_path_map:
            extension = name[name.lower().rfind('.'):].lower()
            if extension not in NON_HTML_FILES:
                mt = self.mime_map.get(name, '')
                if 'html' in mt:
                    yield name

    def get_css_names(self):
        '''
        Helper function to return the manifest names of the css files
        '''
        for name in self.name_path_map:
            if name.lower().endswith('.css'):
                yield name

    def get_image_names(self):
        '''
        Helper function to return the manifest names of the image files
        '''
        for name in self.name_path_map:
            extension = name[name.lower().rfind('.'):].lower()
            if extension in IMAGE_FILES:
                yield name

    def get_page_image_names(self, html_name, data=None):
        '''
        Given a name for an html page, find all <img> and svg <image>
        links within and return tuple of referenced image link converted
        to a normalised image name, original href and image node
        '''
        if html_name not in self.name_path_map:
            return

        def get_svg_image_name(svg):
            for svg_item in svg:
                if svg_item.tag == SVG('image'):
                    image = svg_item
                    href = urlunquote(image.get(XLINK('href'), None))
                    return self.abshref(href, html_name), href, image
            return None, None, None

        if data is None:
            data = self.get_parsed_etree(html_name)

        # Get all <svg><image @xlink:href> links, see if a match in there
        svg_images = []
        try:
            svg_images = XPath('//svg:svg')(data)
        except:
            svg_images = []
        for svg in svg_images:
            name, orig_href, image = get_svg_image_name(svg)
            if name is not None:
                yield name, orig_href, image

        # Get all <img @src> links, see if a match in there
        try:
            images = XPath('//h:img[@src]')(data)
        except:
            images = []
        for img in images:
            href = urlunquote(img.get('src'))
            yield self.abshref(href, html_name), href, img

    def get_page_href_names(self, html_name, data=None):
        '''
        Given a name for an html page, find all <a href> links
        within and return tuple of referenced link converted
        to a normalised name, original href and link node
        '''
        if html_name not in self.name_path_map:
            return
        if data is None:
            data = self.get_parsed_etree(html_name)
        try:
            href_links = XPath('//h:a[@href]')(data)
        except:
            href_links = []
        for href_link in href_links:
            href = urlunquote(href_link.get('href')).partition('#')[0]
            yield self.abshref(href, html_name), href, href_link

    def remove_unused_images(self, image_names):
        '''
        Given a list of "name" objects (paths to images relative to the root)
        look across all html content and css content to see if the image is linked from
        anywhere and if not then remove it.
        '''
        if not image_names:
            return False

        dirtied = False
        missing_map = {image_name.lower() : image_name for image_name in image_names}
        #self.log('Potential missing images:', missing_map)

        def get_image_base_name(resource_name):
            try:
                return os.path.basename(resource_name)
            except:
                return resource_name

        for html_name in self.get_html_names():
            for image_name, _orig_href, _node in self.get_page_image_names(html_name):
                if image_name.lower() in missing_map:
                    missing_map.pop(image_name.lower())
                if len(missing_map) == 0:
                    break
            if len(missing_map) == 0:
                break

        if len(missing_map) > 0:
            # Check for inline style references
            for css_name in self.get_css_names():
                data = self.get_raw(css_name)
                image_keys = list(missing_map.keys())
                for image_key in image_keys:
                    image_name = get_image_base_name(missing_map[image_key])
                    image_regex = re.compile(image_name, re.UNICODE | re.IGNORECASE)
                    #self.log.info('   Scanning css for image: ', image_key, ' regex: ', image_regex)
                    if image_regex.search(data):
                        #self.log.info('   FOUND: ', image_name, ' in: ', css_name)
                        missing_map.pop(image_key)
                if len(missing_map) == 0:
                    break

        if len(missing_map):
            # Check for meta cover references
            cover_id_meta = self.get_meta_content_item('cover')
            if cover_id_meta is not None:
                cover_id = cover_id_meta.get('content', None)
                cover_item = self.get_manifest_item_by_id(cover_id)
                #self.log.info('   Scanning opf for cover_item: ', cover_item, 'id:', cover_id)
                if cover_item is not None:
                    item_href = cover_item.get('href', None)
                    #self.log.info('   Scanning opf for cover_item with href: ', item_href)
                    image_keys = list(missing_map.keys())
                    for image_key in image_keys:
                        image_name = get_image_base_name(missing_map[image_key])
                        image_regex = re.compile(image_name, re.UNICODE | re.IGNORECASE)
                        #self.log.info('   Scanning opf for image: ', image_key, ' regex: ', image_regex)
                        if image_regex.search(item_href):
                            #self.log.info('   FOUND: ', image_name, ' in: ', item_href)
                            missing_map.pop(image_key)

        # Any images we have left are unreferenced so remove from ePub.
        if len(missing_map) > 0:
            dirtied = True
            for image_name in missing_map.values():
                self.log('\t  Removing unused image:', image_name)
                self.delete_from_manifest(image_name)
        return dirtied

    def get_body_text(self, html_name):
        '''
        Return the body text only (all html tags and whitespace removed)
        '''
        data = self.get_parsed_etree(html_name)
        body = XPath('//h:body')(data)
        if body:
            text = etree.tostring(body[0], method='text', encoding='unicode')
        else:
            text = ''
        text = re.sub(r'\s+', '', text)
        return text

    def flatten_toc(self):
        '''
        Flatten the TOC NCX contents so entries are not hierarchical.
        '''
        if not self.ncx_name:
            self.log('\t  No NCX found')
            return False

        nested = self.ncx.xpath(r'descendant::ncx:navPoint/ncx:navPoint',
                                                   namespaces={'ncx':NCX_NS})
        if len(nested) == 0:
            self.log('\t  No nested navPoints')
            return False

        for navpoint in self.ncx.xpath('//ncx:navPoint', namespaces={'ncx':NCX_NS}):
            child_navpoints = navpoint.xpath('ncx:navPoint', namespaces={'ncx':NCX_NS})
            if len(child_navpoints):
                # This navPoint has nested navPoint children, so we need to promote the children
                p = navpoint.getparent()
                idx = p.index(navpoint)+1
                for child in reversed(navpoint):
                    if child.tag == '{%s}navPoint'%NCX_NS:
                        self.log('\t  TOC Navpoint child promoted')
                        p.insert(idx, child)

        self._indent(self.ncx)
        self.set(self.ncx_name, self.ncx)

        return True

    def delete_broken_toc_links(self, html_names_map):
        '''
        Remove any entries from the TOC ncx file which contain broken links
        '''
        if not self.ncx_name:
            self.log('\t  No NCX found')
            return False
        self.log('\tncx name: ', self.ncx_name)
        ncx_dir = os.path.dirname(self.ncx_name).lower()
        if ncx_dir:
            ncx_dir += '/'

        def test_navpoint_for_removal(navpoint):
            src = navpoint.xpath('ncx:content/@src', namespaces={'ncx':NCX_NS})
            if len(src):
                src = urlunquote(src[0]).partition('#')[0]
                link_path = self.abshref(src, self.ncx_name)
                # self.log(f'\t  ncx src={src}, rel path={link_path}, in map: {link_path.lower() in html_names_map}')
                if link_path.lower() not in html_names_map:
                    self.log('\t  Broken TOC Navpoint removed: ', link_path)
                    return True
            return False

        dirtied = False
        # keys = sorted(list(html_names_map.keys()))
        # for i in range(0, len(keys), 5):
        #     self.log(f'\tName map {i}:', ', '.join(keys[i:i+5]))
        self.log('\tLooping over ncx entries')
        for navpoint in self.ncx.xpath('//ncx:navPoint', namespaces={'ncx':NCX_NS}):
            if test_navpoint_for_removal(navpoint):
                dirtied = True
                p = navpoint.getparent()
                idx = p.index(navpoint)
                p.remove(navpoint)
                for child in reversed(navpoint):
                    if child.tag == '{%s}navPoint'%NCX_NS:
                        self.log('\t  TOC Navpoint child promoted')
                        p.insert(idx, child)

        if self._fix_toc_playorder() or dirtied:
            self._indent(self.ncx)
            self.set(self.ncx_name, self.ncx)
            dirtied = True
        return dirtied
