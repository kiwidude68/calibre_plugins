from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import time, re
from six import text_type as unicode
from six.moves.urllib.parse import quote
try:
    from queue import Empty, Queue
except ImportError:
    from Queue import Empty, Queue

from lxml.html import fromstring

from calibre import as_unicode
from calibre.ebooks.metadata.sources.base import Source
from calibre.utils.icu import lower
from calibre.utils.cleantext import clean_ascii_chars
from calibre.utils.localization import get_udc

from calibre.devices.usbms.driver import debug_print

class Baen(Source):

    name                    = 'Baen'
    description             = 'Downloads metadata and covers from Baen'
    author                  = 'Grant Drake'
    version                 = (1, 2, 0)
    minimum_calibre_version = (2, 0, 0)

    ID_NAME = 'baen'
    capabilities = frozenset(['identify', 'cover'])
    touched_fields = frozenset(['title', 'authors', 'identifier:baen',
                                'comments', 'publisher', 'pubdate', 'rating'])
    has_html_comments = True
    supports_gzip_transfer_encoding = True

    BASE_URL = 'https://www.baen.com'

    def get_baen_id(self, identifiers):
        baen_id = identifiers.get('baen', None)
        if not baen_id:
            # Try the legacy identifier from previous version of this plugin
            baen_id = identifiers.get('webscription', None)
        if baen_id:
            match_groups = re.search(r"p-\d+-(.*)", baen_id)
            if match_groups and len(match_groups.groups(0)) == 1:
                baen_id = match_groups.groups(0)[0]
        return baen_id
        
    def get_book_url(self, identifiers):
        baen_id = self.get_baen_id(identifiers)
        if baen_id:
            return ('Baen', baen_id,
                    '%s/%s.html'%(Baen.BASE_URL, baen_id))

    def id_from_url(self, url):
        match = re.match(self.BASE_URL + r"/(.*)\.htm.*", url)
        if match:
            return (self.ID_NAME, match.groups(0)[0])
        return None
        
    def get_cached_cover_url(self, identifiers):
        debug_print("get_cached_cover_url: identifiers=", identifiers)
        url = None
        baen_id = self.get_baen_id(identifiers)
        if baen_id is not None:
            url = self.cached_identifier_to_cover_url(baen_id)
        return url

    def create_title_query(self, log, title=None):
        q = ''
        if title:
            title = get_udc().decode(title)
            tokens = []
            title_tokens = list(self.get_title_tokens(title,
                                strip_joiners=False, strip_subtitle=True))
            tokens = [quote(t.encode('utf-8') if isinstance(t, unicode) else t) for t in title_tokens]
            q = '+'.join(tokens)
        if not q:
            return None
        return '%s/allbooks?q=%s' % (Baen.BASE_URL, q)

    def identify(self, log, result_queue, abort, title=None, authors=None,
            identifiers={}, timeout=30):
        '''
        Note this method will retry without identifiers automatically if no
        match is found with identifiers.
        '''
        matches = []

        # If we have a baen id then we do not need to fire a "search".
        # Instead we will go straight to the URL for that book.
        baen_id = self.get_baen_id(identifiers)
        br = self.browser
        if baen_id:
            (name, baen_id, url) = self.get_book_url(identifiers)
            matches.append(url)
        else:
            query = self.create_title_query(log, title=title)
            if query is None:
                log.error('Insufficient metadata to construct query')
                return
            try:
                log.info('Querying: %s'%query)
                raw = br.open_novisit(query, timeout=timeout).read()
                #open('E:\\baen.html', 'wb').write(raw)
            except Exception as e:
                err = 'Failed to make identify query: %r'%query
                log.exception(err)
                return as_unicode(e)
            root = fromstring(clean_ascii_chars(raw))
            # Now grab the match from the search result, provided the
            # title appears to be for the same book
            self._parse_search_results(log, title, authors, root, matches)

        if abort.is_set():
            return

        if not matches:
            log.error('No matches found with query: %r'%query)
            return
        log.info('_parse_search_results: matches=', matches)
        from calibre_plugins.baen.worker import Worker
        author_tokens = list(self.get_author_tokens(authors))
        workers = [Worker(url, author_tokens, result_queue, br, log, i+1, self) for i, url in
                enumerate(matches)]

        for w in workers:
            w.start()
            # Don't send all requests at the same time
            time.sleep(0.1)

        while not abort.is_set():
            a_worker_is_alive = False
            for w in workers:
                w.join(0.2)
                if abort.is_set():
                    break
                if w.is_alive():
                    a_worker_is_alive = True
            if not a_worker_is_alive:
                break

        return None

    def _parse_search_results(self, log, orig_title, orig_authors, root, matches):
        title_tokens = list(self.get_title_tokens(orig_title))
        author_tokens = list(self.get_author_tokens(orig_authors))

        def ismatch(title, authors):
            authors = lower(' '.join(authors))
            title = lower(title)
            match = not title_tokens
            for t in title_tokens:
                if lower(t) in title:
                    match = True
                    break
            amatch = not author_tokens
            for a in author_tokens:
                if lower(a) in authors:
                    amatch = True
                    break
            if not author_tokens: amatch = True
            return match and amatch

        max_results = 5
        for data in root.xpath('//div[contains(@class,"category-books")]/div/div[@class="book-card-info"]'):
            url = ''.join(data.xpath('./p[1]/a/@href'))
            if not url:
                continue
            #log.info('_parse_search_results: url=%s' % url)

            title = ''.join(data.xpath('./p[1]/a/text()'))
            title = title.strip()
            #log.info('_parse_search_results: title=%s' % title)
            authors_text = ','.join(data.xpath('./p[2]/text()')).strip()
            #log.info('Raw authors_text:', authors_text)
            authors = self._cleanup_authors(log, authors_text)
            if not ismatch(title, authors):
                log.info('Rejecting as not close enough match: %s'%(title))
                continue

            matches.append(url)
            if len(matches) >= max_results:
                break

    def _cleanup_authors(self, log, authors_text):
        # Various types of author text formats, horrible metadata in Baen
        # Author
        # by Author
        # By Author
        # by Author1 and Author2
        # by Author1, Author2
        # by Author1, Author2 and Author3
        # by Author1<br />Edited by Author2 (we have replaced <br /> with comma above)
        authors_text = re.sub(r"[Ee]dited\sby ", '', authors_text).strip()
        authors_text = re.sub(r"\sand\s", ',', authors_text)
        if authors_text.lower().startswith('by '):
            authors_text = authors_text[3:]
        #log.info('_cleanup_authors: authors="%s"' % authors_text)
        authors = authors_text.split(',')
        return authors

    def download_cover(self, log, result_queue, abort,
            title=None, authors=None, identifiers={}, timeout=30):
        cached_url = self.get_cached_cover_url(identifiers)
        if cached_url is None:
            log.info('No cached cover found, running identify')
            rq = Queue()
            self.identify(log, rq, abort, title=title, authors=authors,
                    identifiers=identifiers)
            if abort.is_set():
                return
            results = []
            while True:
                try:
                    results.append(rq.get_nowait())
                except Empty:
                    break
            results.sort(key=self.identify_results_keygen(
                title=title, authors=authors, identifiers=identifiers))
            for mi in results:
                cached_url = self.get_cached_cover_url(mi.identifiers)
                if cached_url is not None:
                    break
        if cached_url is None:
            log.info('No cover found')
            return

        if abort.is_set():
            return
        br = self.browser
        log('Downloading cover from:', cached_url)
        try:
            cdata = br.open_novisit(cached_url, timeout=timeout).read()
            result_queue.put((self, cdata))
        except:
            log.exception('Failed to download cover from:', cached_url)


if __name__ == '__main__': # tests
    # To run these test use:
    # calibre-debug -e __init__.py
    from calibre.ebooks.metadata.sources.test import (test_identify_plugin,
            title_test, authors_test, series_test)
    test_identify_plugin(Baen.name,
        [
            ( # A book with a Baen id
                {'title':'Diplomatic Immunity', 'authors':['Lois McMaster Bujold']},
                [title_test('Diplomatic Immunity', exact=True), 
                 authors_test(['Lois McMaster Bujold'])]
            ),
            ( # A book with a title/author search
                {'title':'Diplomatic Immunity', 'authors':['Lois McMaster Bujold']},
                [title_test('Diplomatic Immunity', exact=True), 
                 authors_test(['Lois McMaster Bujold'])]
            ),
        ])


