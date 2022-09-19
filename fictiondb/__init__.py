from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import time, re
try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode
try:
    from queue import Empty, Queue
except ImportError:
    from Queue import Empty, Queue

from lxml.html import fromstring

from calibre import as_unicode
from calibre.ebooks.metadata import check_isbn
from calibre.ebooks.metadata.sources.base import Source
from calibre.utils.icu import lower
from calibre.utils.cleantext import clean_ascii_chars

class FictionDB(Source):

    name                    = 'FictionDB'
    description             = _('Downloads metadata and covers from fictiondb.com')
    author                  = 'Grant Drake'
    version                 = (1, 3, 0)
    minimum_calibre_version = (2, 85, 1)

    ID_NAME = 'fictiondb'
    capabilities = frozenset(['identify', 'cover'])
    touched_fields = frozenset(['title', 'authors', 'identifier:fictiondb',
        'identifier:isbn', 'comments', 'publisher', 'pubdate',
        'tags', 'series'])
    has_html_comments = True
    supports_gzip_transfer_encoding = True

    BASE_URL = 'https://www.fictiondb.com'

    def config_widget(self):
        '''
        Overriding the default configuration screen for our own custom configuration
        '''
        from calibre_plugins.fictiondb.config import ConfigWidget
        return ConfigWidget(self)

    def get_book_url(self, identifiers):
        fictiondb_id = identifiers.get(self.ID_NAME, None)
        if fictiondb_id:
            # Older ids end with a tilde and a letter. Strip this if it exists.
            if fictiondb_id[len(fictiondb_id) - 2] == '~':
                fictiondb_id = fictiondb_id[0: len(fictiondb_id) - 2]

            return (self.ID_NAME, fictiondb_id,
                    '%s/title/%s.htm'%(self.BASE_URL, fictiondb_id))

    def id_from_url(self, url):
        match = re.match(self.BASE_URL + "/title/(.*)\.htm.*", url)
        if match:
            return (self.ID_NAME, match.groups(0)[0])
        return None
        
    def create_query(self, log, title=None, authors=None, identifiers={}):
        '''
        FictionDB was using HTTP POST requests, but has change to GET requests. Still building
        the parts separately for simplicity.
        '''

        isbn = check_isbn(identifiers.get('isbn', None))
        log.error('create_query - isbn: "%s"' % isbn)
        isbn = isbn if isbn is not None else ''
        post_data = None
        base_search_url = FictionDB.BASE_URL + '/search/searchresults.php'

        if title or authors or isbn:
            title_text = None
            author_text = None
            if title:
                title_tokens = list(self.get_title_tokens(title,
                                    strip_joiners=False, strip_subtitle=True))
                title_text = ' '.join(title_tokens)
            if authors:
                author_tokens = self.get_author_tokens(authors, only_first_author=True)
                author_text = ' '.join(author_tokens)

            # http://www.fictiondb.com/search/searchresults.htm?styp=6&author={author}&title={title}&srchtxt=multi&sgcode=0&tpcode=0&imprint=0&pubgroup=0&genretype=--&rating=-&myrating=-&status=-
            # http://www.fictiondb.com/search/searchresults.php?author=zadie+smith&title=on+beauty&series=&isbn=&datepublished=&synopsis=&rating=-&anthology=&imprint=0&pubgroup=0&srchtxt=multi&styp=6
            post_data = urlencode({'author':author_text, 'title':title_text,
                                   'isbn':isbn, 'datepublished':'', 'synopsis':'', 'rating':'-', 'anthology':'',
                                   'imprint':'', 'pubgroup':'', 'srchtxt':'multi', 'styp':'6' })

        return base_search_url, post_data

    def get_cached_cover_url(self, identifiers):
        url = None
        fictiondb_id = identifiers.get(self.ID_NAME, None)
        if fictiondb_id is None:
            isbn = identifiers.get('isbn', None)
            if isbn is not None:
                fictiondb_id = self.cached_isbn_to_identifier(isbn)
        if fictiondb_id is not None:
            url = self.cached_identifier_to_cover_url(fictiondb_id)

        return url

    def identify(self, log, result_queue, abort, title=None, authors=None,
            identifiers={}, timeout=30):
        '''
        Note this method will retry without identifiers automatically if no
        match is found with identifiers.
        '''
        matches = []
        # Unlike the other metadata sources, if we have a fictiondb id then we
        # do not need to fire a "search" at FictionDB.com. Instead we will be
        # able to go straight to the URL for that book.
        fictiondb_id = identifiers.get(self.ID_NAME, None)

        br = self.browser

        if fictiondb_id:
            matches.append(self.get_book_url(identifiers)[2])
        else:
            isbn = check_isbn(identifiers.get('isbn', ''))
            query, post_data = self.create_query(log, title=title, authors=authors,
                                                 identifiers=identifiers)
            if post_data is None:
                log.error('Insufficient metadata to construct query')
                return
            try:
                log.info('Querying: %s - %s'%(query, post_data))
                br.set_handle_redirect(True)
                br.set_debug_redirects(True)
                response = br.open_novisit(query + '?' + post_data, timeout=timeout)
                # Check whether we got redirected to the book page.
                # If we did, will use the url.
                location = response.geturl()
                if '/title/' in location:
                    log.info('Initial search including ISBN found something: %r'%location)
                    matches.append(location)
            except Exception as e:
                err = 'Failed to make identify query: %r - %r'%(query, post_data)
                log.exception(err)
                return as_unicode(e)

            # For ISBN based searches we have already done everything we need to
            # So anything from this point below is for title/author based searches.
            if not isbn or len(matches) == 0:
                try:
                    raw = response.read().strip()
#                     open('E:\\fictiondb_search.html', 'wb').write(raw)
                    raw = raw.decode('utf-8', errors='replace')
                    if not raw:
                        log.error('Failed to get raw result for query: %r - %r'%(query, post_data))
                        return
                    root = fromstring(clean_ascii_chars(raw))
                except:
                    msg = 'Failed to parse fictiondb page for query: %r - %r'%(query, post_data)
                    log.exception(msg)
                    return msg
                # Now grab the first value from the search results, provided the
                # title and authors appear to be for the same book
                self._parse_search_results(log, title, authors, root, matches, timeout)

        if abort.is_set():
            return

        if not matches:
            if identifiers and title and authors:
                log.info('No matches found with identifiers, retrying using only'
                        ' title and authors')
                return self.identify(log, result_queue, abort, title=title,
                        authors=authors, timeout=timeout)
            log.error('No matches found with query: %r - %r'%(query, post_data))
            return

        from calibre_plugins.fictiondb.worker import Worker
        workers = [Worker(url, result_queue, br, log, i, self) for i, url in
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

    def _parse_search_results(self, log, orig_title, orig_authors, root, matches, timeout):
        first_result = root.xpath('//tbody[@id="trows"]/tr')
        if not first_result:
            log.error('_parse_search_results - No first row')
            return
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

        title = first_result[0].xpath('./td[2]')[0].text_content().strip()
        authors = first_result[0].xpath('./td[1]')[0].text_content().strip().split(';')
        if not ismatch(title, authors):
            log.error('Rejecting as not close enough match: %s %s'%(title, authors))
            return

        log.error('_parse_search_results: title="%s", author="%s"'%(title, authors))
        first_result_url_node = root.xpath('//tbody[@id="trows"]/tr[1]/td[2]/a[1]/@href')
        if first_result_url_node:
            log.error('_parse_search_results: have a URL')
            import calibre_plugins.fictiondb.config as cfg
            result_url = FictionDB.BASE_URL + first_result_url_node[0][2:]
            matches.append(result_url)

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
    test_identify_plugin(FictionDB.name,
        [

            ( # A book with no ISBN specified
                {'title':"Harry Potter and the Sorcerer's Stone", 'authors':['J.K. Rowling']},
                [title_test("Harry Potter and the Sorcerer's Stone",
                    exact=True), authors_test(['J. K. Rowling']),
                    series_test('Harry Potter', 1.0)]

            ),

            ( # A book with an ISBN
                {'identifiers':{'isbn': '9780439064866'},
                    'title':'Chamber of Secrets', 'authors':['J.K. Rowling']},
                [title_test('Harry Potter and the Chamber of Secrets',
                    exact=True), authors_test(['J. K. Rowling']),
                    series_test('Harry Potter', 2.0)]

            ),

            ( # A book with a FictionDB id
                {'identifiers':{'fictiondb': '5'},
                    'title':'Prisoner of Azkaban', 'authors':['J.K. Rowling']},
                [title_test('Harry Potter and the Prisoner of Azkaban',
                    exact=True), authors_test(['J. K. Rowling']),
                    series_test('Harry Potter', 3.0)]

            ),

        ])


