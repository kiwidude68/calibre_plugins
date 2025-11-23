from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import socket
from threading import Thread

from lxml.html import tostring
from calibre import browser, random_user_agent

def parse_html(raw):
    try:
        from html5_parser import parse
    except ImportError:
        # Old versions of calibre
        import html5lib
        return html5lib.parse(raw, treebuilder='lxml', namespaceHTMLElements=False)
    else:
        return parse(raw)

class GoodreadsCoverWorker(Thread):
    '''
    Get book details from Goodreads book page
    '''
    def __init__(self, goodreads_id, log, timeout=20):
        Thread.__init__(self)
        self.daemon = True
        self.goodreads_id = goodreads_id
        self.log = log
        self.timeout = timeout
        self.cover_url = None
        self._browser = None

    def run(self):
        try:
            self.url = 'http://www.goodreads.com/book/show/%s'%self.goodreads_id
            self.get_details()
        except:
            self.log.exception('get_details failed for url: %r'%self.url)

    @property
    def user_agent(self):
        # Pass in an index to random_user_agent() to test with a particular
        # user agent
        return random_user_agent()

    @property
    def browser(self):
        if self._browser is None:
            self._browser = browser(user_agent=self.user_agent)
        return self._browser.clone_browser()

    def get_details(self):
        try:
            self.log.info('Goodreads book url: %r'%self.url)
            raw = self.browser.open_novisit(self.url, timeout=self.timeout).read().strip()
        except Exception as e:
            if callable(getattr(e, 'getcode', None)) and \
                    e.getcode() == 404:
                self.log.error('URL malformed: %r'%self.url)
                return
            attr = getattr(e, 'args', [None])
            attr = attr if attr else [None]
            if isinstance(attr[0], socket.timeout):
                msg = 'Goodreads timed out. Try again later.'
                self.log.error(msg)
            else:
                msg = 'Failed to make details query: %r'%self.url
                self.log.exception(msg)
            return

        #open('D:\\cover_url.html', 'wb').write(raw)
        raw = raw.decode('utf-8', errors='replace')

        if '<title>404 - ' in raw:
            self.log.error('URL malformed: %r'%self.url)
            return

        try:
            root = parse_html(raw)
        except:
            msg = 'Failed to parse goodreads details page: %r'%self.url
            self.log.exception(msg)
            return False

        errmsg = root.xpath('//*[@id="errorMessage"]')
        if errmsg:
            msg = 'Failed to parse goodreads details page: %r'%self.url
            msg += tostring(errmsg, method='text', encoding='unicode').strip()
            self.log.error(msg)
            return

        self.parse_details(root)

    def parse_details(self, root):
        try:
            self.cover_url = self.parse_cover(root)
        except:
            self.log.exception('Error parsing cover for url: %r'%self.url)

    def parse_cover(self, root):
        imgcol_node = root.xpath('//div[@class="bookCoverPrimary"]/a/img/@src')
        if not imgcol_node:
            imgcol_node = root.xpath('//div[@class="BookCover__image"]/div/img/@src')
        if not imgcol_node:
            imgcol_node = root.xpath('//div[@class="BookCover__image"]/div/div/img/@src')
        if imgcol_node:
            img_url = imgcol_node[0]
            return img_url
            # Unfortunately Goodreads sometimes have broken links so we need to do
            # an additional request to see if the URL actually exists
            #info = self.browser.open_novisit(img_url, timeout=self.timeout).info()
            #if int(info.get('Content-Length')) > 1000:
            #    return img_url
            #else:
            #    self.log.warning('Broken image for url: %s'%img_url)
