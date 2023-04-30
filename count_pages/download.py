from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import socket, re

from six import text_type as unicode

from lxml.html import fromstring, tostring
from calibre import browser

from calibre_plugins.count_pages.config import PAGE_DOWNLOADS

def clean_html(raw):
    from calibre.ebooks.chardet import xml_to_unicode
    from calibre.utils.cleantext import clean_ascii_chars
    return clean_ascii_chars(xml_to_unicode(raw, strip_encoding_pats=True,
                                resolve_entities=True, assume_utf8=True)[0])

def parse_html(raw):
    raw = clean_html(raw)
    from html5_parser import parse
    return parse(raw, maybe_xhtml=False, sanitize_names=True, return_root=False,keep_doctype=False)


class DownloadPagesWorker():
    '''
    Get page count from book book page
    '''
    def __init__(self, sources, timeout=20):
        self.timeout = timeout
        self.page_count = None
        self.page_count = None
        self.sources = sources
        self.run()

    def run(self):
        for source_name, source_id in self.sources:
            try:
                print('DownloadPagesWorker::run - source_id=%s, source_name=%s' % (source_id, source_name))
                self.identifier_regex = PAGE_DOWNLOADS[source_name].get('identifier_regex', None)
                if self.identifier_regex is not None:
                    print('DownloadPagesWorker::run - identifier_regex=%s' % (self.identifier_regex,))
                    source_id = re.search(self.identifier_regex, source_id).groups(0)[0]
                    print('DownloadPagesWorker::run - after identifier_regex - source_id=%s,' % (source_id,))

                self.url = PAGE_DOWNLOADS[source_name]['URL'] % source_id
                self.pages_xpath = PAGE_DOWNLOADS[source_name]['pages_xpath']
                self.pages_regex = PAGE_DOWNLOADS[source_name].get('pages_regex')
                print('DownloadPagesWorker::run - PAGE_DOWNLOADS[source_name]=%s' % (PAGE_DOWNLOADS[source_name], ))
                print('DownloadPagesWorker::run - self.pages_regex=%s' % (self.pages_regex, ))
                self._get_details()
                if self.page_count:
                    self.source_name = source_name
                    break
            except:
                print('get_details failed for url: %r'%self.url)
                raise

    def _get_details(self):
        try:
            print('Download source book url: %r'%self.url)
            br = browser()
            raw = br.open_novisit(self.url, timeout=self.timeout).read().strip()
        except Exception as e:
            if callable(getattr(e, 'getcode', None)) and \
                    e.getcode() == 404:
                print('URL malformed: %r'%self.url)
                return
            attr = getattr(e, 'args', [None])
            attr = attr if attr else [None]
            if isinstance(attr[0], socket.timeout):
                msg = 'Download source timed out. Try again later.'
                print(msg)
            else:
                msg = 'Failed to make details query: %r'%self.url
                print(msg)
            return

#         raw = raw.decode('utf-8-sig', errors='replace')
        raw = raw.decode('utf-8', errors='replace')
#         open('E:\\t.html', 'w').write(raw)
        #print("_get_details: len(raw)=", len(raw))

        if '<title>404 - ' in raw:
            print('URL malformed: %r'%self.url)
            return

        try:
            try:
                root = fromstring(clean_html(raw))
            except:
                root = parse_html(raw)
        except:
            msg = 'Failed to parse download source details page: %r'%self.url
            print(msg)
            import traceback
            traceback.print_exc()
            return

        errmsg = root.xpath('//*[@id="errorMessage"]')
        if errmsg:
            msg = 'Failed to parse download source details page: %r'%self.url
            msg += tostring(errmsg, method='text', encoding='unicode').strip()
            print(msg)
            return

        self._parse_page_count(root, self.pages_xpath, self.pages_regex)

    def _parse_page_count(self, root, pages_xpath, pages_regex=None):
        print("_parse_page_count: start")
        print("_parse_page_count: root.__class__=", root.__class__.__name__)
        print("_parse_page_count: pages_xpath='%s', =pages_regex='%s'" % (pages_xpath, pages_regex))
        try:
            pages = root.xpath(pages_xpath)
            print("_parse_page_count: pages=", pages)
            if len(pages) > 0:
                print("_parse_page_count: pages[0]=", pages[0])
                print("_parse_page_count: pages_regex=", pages_regex)
                pages_text = ''.join(pages[0]).strip().partition(' ')[0]
                print("_parse_page_count: pages_text=", pages_text)
                if pages_regex is not None:
                    print("_parse_page_count: have pages_regex='%s'" % pages_regex)
                    for possible_page in pages:
                        if re.search(pages_regex, possible_page):
                            pages_text = re.search(pages_regex, possible_page).groups(0)[0]
                            print("_parse_page_count: result from regex='%s'" % pages_text)
                            break
                self.page_count = int(pages_text)
        except Exception as e:
            print('Error parsing page count for url: %r'%self.url)
            print('exceptions: %s' % e)
        print("_parse_page_count: end")
