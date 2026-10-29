from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import time, json, re, random

try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus
try:
    from queue import Empty, Queue
except ImportError:
    from Queue import Empty, Queue

from six import text_type as unicode

from calibre import as_unicode
from calibre.ebooks import normalize
from calibre.ebooks.metadata import check_isbn
from calibre.ebooks.metadata.sources.base import Source, fixcase, fixauthors
from calibre.utils.icu import lower
from calibre.constants import numeric_version as calibre_version


class Goodreads(Source):

    name = 'Goodreads'
    description = 'Downloads metadata and covers from Goodreads'
    author = 'Grant Drake'
    version = (1, 10, 0)
    minimum_calibre_version = (2, 0, 0)

    capabilities = frozenset(['identify', 'cover'])
    touched_fields = frozenset(['title', 'authors', 'identifier:goodreads',
        'identifier:grrating', 'identifier:grvotes',
        'identifier:isbn', 'rating', 'comments', 'publisher', 'pubdate',
        'tags', 'series', 'languages'])
    has_html_comments = True
    supports_gzip_transfer_encoding = True

    ID_NAME = 'goodreads'
    BASE_URL = 'https://www.goodreads.com'
    MAX_EDITIONS = 5

    @property
    def user_agent(self):
        # This utter filth is necessary to deal with periods of time when calibre did or did not have
        # various iterations of a random chrome user agent function.
        if calibre_version >= (5,40,0):
            from calibre.utils.random_ua import random_common_chrome_user_agent
            return random_common_chrome_user_agent()
        elif  calibre_version <= (5,8,1):
            from calibre.utils.random_ua import random_chrome_ua
            return random_chrome_ua()
        else:
            # From 5.9.0 to 5.39.1 there was no function, we will have to replicate the equivalent code here
            from calibre.utils.random_ua import all_chrome_versions, random_desktop_platform
            chrome_version = random.choice(all_chrome_versions())
            render_chrome_version = 'Mozilla/5.0 ({p}) AppleWebKit/{wv} (KHTML, like Gecko) Chrome/{cv} Safari/{wv}'.format(
                p=random_desktop_platform(), wv=chrome_version['webkit_version'], cv=chrome_version['chrome_version'])
            return render_chrome_version

    def config_widget(self):
        '''
        Overriding the default configuration screen for our own custom configuration
        '''
        from calibre_plugins.goodreads.config import ConfigWidget
        return ConfigWidget(self)

    def get_book_url(self, identifiers):
        goodreads_id = identifiers.get(self.ID_NAME, None)
        if goodreads_id:
            return ('goodreads', goodreads_id,
                    '%s/book/show/%s' % (Goodreads.BASE_URL, goodreads_id))

    def id_from_url(self, url):
        match = re.match(self.BASE_URL + r"/book/show/(\d+).*", url)
        if match:
            return (self.ID_NAME, match.groups(0)[0])
        return None

    def get_details_url(self, goodreads_id):
        # The extensionless book page is protected by AWS WAF. Goodreads still
        # serves the same Next.js page, including __NEXT_DATA__, at this URL.
        return '%s/book/show/%s.xml' % (self.BASE_URL, goodreads_id)
        
    def get_cached_cover_url(self, identifiers):
        url = None
        goodreads_id = identifiers.get(self.ID_NAME, None)
        if goodreads_id is None:
            isbn = identifiers.get('isbn', None)
            if isbn is not None:
                goodreads_id = self.cached_isbn_to_identifier(isbn)
        if goodreads_id is not None:
            url = self.cached_identifier_to_cover_url(goodreads_id)

        return url

    def clean_downloaded_metadata(self, mi):
        '''
        Overridden from the calibre default so that we can stop this plugin messing
        with the tag casing coming from Goodreads
        '''
        docase = mi.language == 'eng' or mi.is_null('language')
        if docase and mi.title:
            mi.title = fixcase(mi.title)
        mi.authors = fixauthors(mi.authors)
        mi.isbn = check_isbn(mi.isbn)

    def _get_autocomplete_results(self, log, abort, query, timeout=30):
        '''Return autocomplete results; raise ValueError on a malformed response.'''
        if not query:
            return []
        url = '%s/book/auto_complete?format=json&q=%s' % (
            self.BASE_URL, quote_plus(unicode(query).encode('utf-8')))
        if abort.is_set():
            return []
        log.info('Querying autocomplete API: %s' % url)
        raw = self.browser.open_novisit(url, timeout=timeout).read()
        log.debug('JSON Result: %s'%raw)
        if not raw:
            return []
        try:
            results = json.loads(raw)
        except ValueError:
            raise ValueError('Invalid autocomplete response for query: %r' % query)
        if not isinstance(results, list):
            raise ValueError('Unexpected autocomplete response for query: %r' % query)
        return [result for result in results if isinstance(result, dict)]

    def get_goodreads_id_using_api(self, log, abort, timeout=30, identifier=None):
        
        log.debug('get_goodreads_id_using_api - identifier=%s' % identifier)
        
        if not identifier:
            return None
        
        results = self._get_autocomplete_results(
            log, abort, query=identifier, timeout=timeout)
        goodreads_id = results[0].get('bookId') if results else None
        log.info('Result using autocomplete API: %s' % goodreads_id)
        return goodreads_id
        
        
    def get_goodreads_id_using_asin(self, log, abort, timeout=30, identifiers={}):
        for identifier_name, identifier in identifiers.items():
            identifier_name = identifier_name.lower()
            if identifier_name in ('amazon', 'asin', 'mobi-asin') or identifier_name.startswith('amazon_'):
                log.info('get_goodreads_id_using_asin - identifier_name=%s, identifier=%s' % (identifier_name, identifier))
                goodreads_id = self.get_goodreads_id_using_api(log, abort, timeout=timeout, identifier=identifier)
                return goodreads_id
        return None


    def get_goodreads_id_from_identifiers(self, log, abort, timeout=30, identifiers={}):
        '''
        Note this method will retry without identifiers automatically if no
        match is found with identifiers.
        '''
        goodreads_id = identifiers.get(self.ID_NAME, None)
        if goodreads_id:
            return goodreads_id
        
        isbn = check_isbn(identifiers.get('isbn', None))
        if isbn:
            log.info('get_goodreads_id_from_identifiers - isbn=%s' % isbn)
            goodreads_id = self.get_goodreads_id_using_api(log, abort, timeout=timeout, identifier=isbn)
        if goodreads_id:
            return goodreads_id

        goodreads_id = self.get_goodreads_id_using_asin(log, abort, timeout=timeout, identifiers=identifiers)
        if goodreads_id:
            return goodreads_id

        return None


    def _strip_series_from_title(self, text):
        '''Strip a trailing '(Series, #N)' suffix.'''
        if text.find('(') == -1:
            return text.strip()
        title, _, series_info = text.rpartition('(')
        series_info = series_info.rpartition(')')[0]
        if series_info.find('#') <= 0:
            return text.strip()
        while series_info.count(')') != series_info.count('('):
            title_split = title.rpartition('(')
            title = title_split[0]
            series_info = title_split[2] + '(' + series_info
        return title.strip()

    def _matches(self, title_tokens, author_tokens, result):
        title = (result.get('bookTitleBare') or '').strip()
        if not title:
            title = self._strip_series_from_title(result.get('title') or '')
        title = lower(title)
        author = result.get('author') or ''
        if isinstance(author, dict):
            author = author.get('name') or ''
        if not result.get('bookId') or author == 'NOT A BOOK':
            return False
        author = lower(author)
        if title_tokens and not any(lower(t) in title for t in title_tokens):
            return False
        if author_tokens and not any(lower(a) in author for a in author_tokens):
            return False
        return True

    def _search_title_author(self, log, abort, title, authors, timeout=30):
        '''Return up to MAX_EDITIONS plausible autocomplete matches.'''
        query_title_tokens = list(self.get_title_tokens(
            title, strip_joiners=False, strip_subtitle=True))
        # Joiners such as 'the'/'a' are useful in the query but must not be
        # used for matching, or any result containing them would be accepted.
        match_title_tokens = list(self.get_title_tokens(title))
        if query_title_tokens and not match_title_tokens:
            match_title_tokens = query_title_tokens
        author_tokens = list(self.get_author_tokens(authors))
        queries = []
        if query_title_tokens:
            queries.append(' '.join(query_title_tokens))
            if author_tokens:
                queries.append(' '.join(author_tokens + query_title_tokens))
        elif author_tokens:
            queries.append(' '.join(author_tokens))
        for query in queries:
            if abort.is_set():
                return []
            matches = []
            seen = set()
            for result in self._get_autocomplete_results(
                    log, abort, query=query, timeout=timeout):
                if self._matches(match_title_tokens, author_tokens, result):
                    book_id = result['bookId']
                    if book_id not in seen:
                        seen.add(book_id)
                        matches.append(result)
            if matches:
                log.info('Autocomplete matches for %r: %s' % (query, ', '.join(
                    '%s (%s)' % (r.get('title'), r['bookId']) for r in matches)))
                return matches[:self.MAX_EDITIONS]
        return []


    def identify(self, log, result_queue, abort, title=None, authors=None,
            identifiers={}, timeout=30):
        '''
        Note this method will retry without identifiers automatically if no
        match is found with identifiers.
        '''
        matches = []
        goodreads_id = None
        log.debug('identify - start. title=%s, authors=%s, identifiers=%s' % (title, authors, identifiers))
        # Unlike the other metadata sources, if we have a goodreads id then we
        # do not need to fire a "search" at Goodreads.com. Instead we will be
        # able to go straight to the URL for that book. We can use some identifiers 
        # to get the Goodreads ID via an API if we don't already have it.
        try:
            if identifiers:
                goodreads_id = self.get_goodreads_id_from_identifiers(log, abort, timeout=timeout, identifiers=identifiers)
        except Exception as e:
            err = 'Failed to trying to get Goodreads id using auto_complete API'
            log.exception(err)
            return as_unicode(e)

        br = self.browser

        if goodreads_id:
            matches.append(self.get_details_url(goodreads_id))
        else:
            # Can't find a valid id, so search using the title and authors.
            if not title and not authors:
                log.error('Insufficient metadata to construct query')
                return
            log.info('No identifiers, searching for title/author using autocomplete API')
            title = normalize(title)
            try:
                matched = self._search_title_author(log, abort, title, authors, timeout=timeout)
            except Exception as e:
                err = 'Failed to search Goodreads for title/author: %r' % title
                log.exception(err)
                return as_unicode(e)
            if not matched:
                log.error('No matching book found for title/author: %r by %r' % (title, authors))
                return
            matches.extend(self.get_details_url(result['bookId']) for result in matched)

        if abort.is_set():
            return

        from calibre_plugins.goodreads.worker import Worker
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

    def test_fields(self, mi):
        '''
        Overridden because for our tests below we don't get all fields back for all books being tested
        and some fields are only populated conditionally based on user settings.
        '''
        ignore_fields = ['identifier:isbn', 'identifier:grrating', 'identifier:grvotes', 'publisher', 'languages', 'tags', 'pubdate']
        for key in self.touched_fields:
            if key not in ignore_fields:
                if key.startswith('identifier:'):
                    key = key.partition(':')[-1]
                    if not mi.has_identifier(key):
                        return 'identifier: ' + key
                elif mi.is_null(key):
                    return key


if __name__ == '__main__': # tests
    # To run these test use:
    # calibre-debug -e __init__.py
    if not __debug__:
        raise SystemExit('These tests use assert; do not run with Python -O')
    from calibre.ebooks.metadata.sources.test import (test_identify_plugin,
            title_test, authors_test, series_test, isbn_test)

    def _make_test_plugin(browser=None):
        # Bypass Source.__init__; the browser property lazily reads _browser.
        plugin = Goodreads.__new__(Goodreads)
        plugin._browser = browser
        return plugin

    class _FakeLog(object):
        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    class _FakeAbort(object):
        def __init__(self, aborted=False):
            self.aborted = aborted

        def is_set(self):
            return self.aborted

    class _FakeBrowser(object):
        def __init__(self, data):
            self.data = data
            self.urls = []

        def open_novisit(self, url, timeout=None):
            self.urls.append(url)
            return self

        def clone_browser(self):
            return self

        def read(self):
            return self.data

    def _make_fake_plugin(responses=None):
        plugin = _make_test_plugin(_FakeBrowser(b''))
        calls = []
        responses = responses or {}

        def fake_get_autocomplete_results(log, abort, query, timeout=30):
            calls.append(query)
            return responses.get(query, [])

        plugin._get_autocomplete_results = fake_get_autocomplete_results
        return plugin, calls

    def _book_ids(results):
        return [result['bookId'] for result in results]

    def title_starts_with_test(prefix):
        # title_test() uses substring matching, so require a word-boundary
        # prefix to reject titles such as 'The Gifts of Imperfection'.
        pattern = re.compile(r'^%s\b' % re.escape(prefix.lower()))

        def test(mi):
            return bool(mi.title) and bool(pattern.match(mi.title.lower()))

        return test

    def test_get_autocomplete_results():
        log, abort = _FakeLog(), _FakeAbort()

        # The query is encoded; empty queries/responses are no results.
        browser = _FakeBrowser(b'[{"bookId": "1"}]')
        plugin = _make_test_plugin(browser)
        assert plugin._get_autocomplete_results(
            log, abort, query='The Gift & More') == [{'bookId': '1'}]
        assert 'q=The+Gift+%26+More' in browser.urls[0]
        assert plugin._get_autocomplete_results(log, abort, query='') == []

        plugin = _make_test_plugin(_FakeBrowser(b''))
        assert plugin._get_autocomplete_results(
            log, abort, query='The Gift') == []

        # Malformed top-level responses raise; non-dict rows are ignored.
        for data in (b'not json', b'{"bookId": "1"}'):
            plugin = _make_test_plugin(_FakeBrowser(data))
            try:
                plugin._get_autocomplete_results(log, abort, query='The Gift')
            except ValueError:
                pass
            else:
                raise AssertionError('Expected malformed response to raise: %r' % data)

        plugin = _make_test_plugin(
            _FakeBrowser(b'[{"bookId": "1"}, "not a dict", null]'))
        assert plugin._get_autocomplete_results(
            log, abort, query='The Gift') == [{'bookId': '1'}]

        plugin = _make_test_plugin(_FakeBrowser(b'["not a dict"]'))
        assert plugin._get_autocomplete_results(
            log, abort, query='The Gift') == []

    def test_search_title_author():
        log, abort = _FakeLog(), _FakeAbort()

        # The title query has no Nora Roberts result, so the author+title
        # retry is required.
        plugin, calls = _make_fake_plugin({
            'The Gift': [
                {'bookId': '7015403', 'bookTitleBare': 'The Gifts of Imperfection',
                 'author': {'name': 'Brene Brown'}},
                {'bookId': '63945326', 'bookTitleBare': 'The Gift',
                 'author': {'name': 'Freida McFadden'}},
            ],
            'Nora Roberts The Gift': [
                {'bookId': '59826',
                 'bookTitleBare': 'The Gift: Home for Christmas / All I Want for Christmas',
                 'author': {'name': 'Nora Roberts'}},
            ],
        })
        matched = plugin._search_title_author(log, abort, 'The Gift', ['Nora Roberts'])
        assert _book_ids(matched) == ['59826']
        assert calls == ['The Gift', 'Nora Roberts The Gift']

        # The matching result is behind a wrong author, but no retry is needed.
        plugin, calls = _make_fake_plugin({
            'Playing with Fire': [
                {'bookId': '48854978', 'bookTitleBare': 'Playing with Fire',
                 'author': {'name': 'L.J. Shen'}},
                {'bookId': '2157243', 'bookTitleBare': 'Playing with Fire',
                 'author': {'name': 'Derek Landy'}},
            ],
        })
        matched = plugin._search_title_author(
            log, abort, 'Playing with Fire', ['Derek Landy'])
        assert _book_ids(matched) == ['2157243']
        assert calls == ['Playing with Fire']

        # Series and subtitle are stripped from the query.
        plugin, calls = _make_fake_plugin({
            '61 Hours': [
                {'bookId': '6977769', 'bookTitleBare': '61 Hours',
                 'author': {'name': 'Lee Child'}},
            ],
        })
        matched = plugin._search_title_author(
            log, abort, '61 Hours (Jack Reacher, #14)', ['Lee Child'])
        assert _book_ids(matched) == ['6977769']
        assert calls == ['61 Hours']

        # Candidates are deduplicated and capped at MAX_EDITIONS.
        plugin, calls = _make_fake_plugin({
            'Series': [
                {'bookId': str(i), 'bookTitleBare': 'Series',
                 'author': {'name': 'Author'}}
                for i in range(Goodreads.MAX_EDITIONS + 1)
            ],
        })
        matched = plugin._search_title_author(log, abort, 'Series', ['Author'])
        assert _book_ids(matched) == [
            str(i) for i in range(Goodreads.MAX_EDITIONS)]
        assert calls == ['Series']

        plugin, calls = _make_fake_plugin({
            'Duplicate': [
                {'bookId': '7', 'bookTitleBare': 'Duplicate',
                 'author': {'name': 'Author'}},
                {'bookId': '7', 'bookTitleBare': 'Duplicate',
                 'author': {'name': 'Author'}},
                {'bookId': '8', 'bookTitleBare': 'Duplicate',
                 'author': {'name': 'Author'}},
            ],
        })
        matched = plugin._search_title_author(log, abort, 'Duplicate', ['Author'])
        assert _book_ids(matched) == ['7', '8']
        assert calls == ['Duplicate']

        # A result that only shares a joiner ('The') is not a match.
        plugin, calls = _make_fake_plugin({
            'The Reckoning': [
                {'bookId': '9', 'bookTitleBare': 'The Crossing',
                 'author': {'name': 'Michael Connelly'}},
            ],
        })
        assert plugin._search_title_author(
            log, abort, 'The Reckoning', ['Michael Connelly']) == []
        assert calls == ['The Reckoning', 'Michael Connelly The Reckoning']

        # Author-only lookups query the author tokens and still reject
        # results by other authors.
        plugin, calls = _make_fake_plugin({
            'Nora Roberts': [
                {'bookId': '59826', 'bookTitleBare': 'The Gift',
                 'author': {'name': 'Nora Roberts'}},
                {'bookId': '99999', 'bookTitleBare': 'The Gift',
                 'author': {'name': 'Freida McFadden'}},
            ],
        })
        matched = plugin._search_title_author(log, abort, None, ['Nora Roberts'])
        assert _book_ids(matched) == ['59826']
        assert calls == ['Nora Roberts']

        # With neither a title nor an author there is nothing to query.
        plugin, calls = _make_fake_plugin()
        assert plugin._search_title_author(log, abort, None, None) == []
        assert calls == []

    def test_matches():
        plugin = _make_test_plugin()
        title_tokens, author_tokens = ['Poet'], ['Michael', 'Connelly']

        # Study guides, NOT A BOOK and incomplete rows are rejected.
        assert not plugin._matches(title_tokens, author_tokens, {
            'bookId': '1',
            'bookTitleBare': 'Summary & Study Guide The Poet by Michael Connelly',
            'author': {'name': 'BookRags'}})
        assert not plugin._matches(title_tokens, author_tokens, {
            'bookId': '2', 'bookTitleBare': 'The Poet',
            'author': {'name': 'NOT A BOOK'}})
        assert not plugin._matches(title_tokens, author_tokens, {
            'bookTitleBare': 'The Poet', 'author': {'name': 'Michael Connelly'}})
        assert not plugin._matches(title_tokens, author_tokens, {
            'bookId': '3', 'author': {'name': 'Michael Connelly'}})
        assert plugin._matches(title_tokens, author_tokens, {
            'bookId': '4', 'bookTitleBare': 'The Poet',
            'author': {'name': 'Michael Connelly'}})
        assert plugin._matches(['Gift'], [], {
            'bookId': '5', 'bookTitleBare': 'The Gift',
            'author': {'name': 'Nora Roberts'}})
        assert not plugin._matches(['Gift'], [], {
            'bookId': '6', 'bookTitleBare': 'The Gift',
            'author': {'name': 'NOT A BOOK'}})

        # When bookTitleBare is absent, strip the series suffix from title
        # before matching, as the old XML search did.
        assert not plugin._matches(['Jack'], [], {
            'bookId': '7', 'title': '61 Hours (Jack Reacher, #14)',
            'author': {'name': 'Lee Child'}})
        assert plugin._matches(['Hours'], [], {
            'bookId': '8', 'title': '61 Hours (Jack Reacher, #14)',
            'author': {'name': 'Lee Child'}})

    def test_identifier_lookup():
        log, abort = _FakeLog(), _FakeAbort()
        isbn = '9780385340588'
        asin = 'B00TEST'

        # Identifier lookup uses the first result, like the old flow; an
        # empty first result falls through to the next identifier lookup.
        plugin, calls = _make_fake_plugin({
            isbn: [{'bookId': ''}, {'bookId': '67890'}],
            asin: [{'bookId': '999'}],
        })
        assert not plugin.get_goodreads_id_using_api(log, abort, identifier=isbn)
        assert calls == [isbn]
        assert plugin.get_goodreads_id_from_identifiers(
            log, abort, identifiers={'isbn': isbn}) is None
        assert calls == [isbn, isbn]
        assert plugin.get_goodreads_id_from_identifiers(
            log, abort, identifiers={'isbn': isbn, 'asin': asin}) == '999'
        assert calls == [isbn, isbn, isbn, asin]

        # A non-empty first result is returned directly.
        plugin, calls = _make_fake_plugin({isbn: [{'bookId': '12345'}]})
        assert plugin.get_goodreads_id_using_api(log, abort, identifier=isbn) == '12345'
        assert calls == [isbn]

        # Empty responses and missing identifiers produce no ID.
        plugin, calls = _make_fake_plugin({isbn: []})
        assert plugin.get_goodreads_id_using_api(log, abort, identifier=isbn) is None
        assert calls == [isbn]
        assert plugin.get_goodreads_id_using_api(log, abort, identifier=None) is None
        assert calls == [isbn]

    def test_aborted_search_returns_no_results():
        log = _FakeLog()
        abort = _FakeAbort(aborted=True)

        browser = _FakeBrowser(b'[{"bookId": "1"}]')
        plugin = _make_test_plugin(browser)
        assert plugin._get_autocomplete_results(log, abort, query='The Gift') == []
        assert browser.urls == []

        plugin, calls = _make_fake_plugin({'The Gift': [{'bookId': '1'}]})
        assert plugin._search_title_author(log, abort, 'The Gift', ['Nora Roberts']) == []
        assert calls == []

    test_get_autocomplete_results()
    test_search_title_author()
    test_matches()
    test_identifier_lookup()
    test_aborted_search_returns_no_results()
    print('Search helper tests passed')

    test_identify_plugin(Goodreads.name,
        [
            (# A book with an ISBN
                {'identifiers':{'isbn': '9780385340588'},
                    'title':'61 Hours', 'authors':['Lee Child']},
                [title_test('61 Hours', exact=True),
                 authors_test(['Lee Child']),
                 series_test('Jack Reacher', 14.0),
                 isbn_test('9780385340588')]
            ),

            (# A book throwing an index error
                {'title':'The Girl Hunters', 'authors':['Mickey Spillane']},
                [title_test('The Girl Hunters', exact=True),
                 authors_test(['Mickey Spillane']),
                 series_test('Mike Hammer', 7.0),
                 isbn_test('9780451055156')]
            ),

            (# A book with no ISBN specified
                {'title':"Playing with Fire", 'authors':['Derek Landy']},
                [title_test("Playing with Fire", exact=True),
                 authors_test(['Derek Landy']),
                 series_test('Skulduggery Pleasant', 2.0),
                 isbn_test('9780061240881')]
            ),

            (# A book with a Goodreads id
                {'identifiers':{'goodreads': '6977769'},
                    'title':'61 Hours', 'authors':['Lee Child']},
                [title_test('61 Hours', exact=True),
                 authors_test(['Lee Child']),
                 series_test('Jack Reacher', 14.0),
                 isbn_test('9780385340588')]
            ),

            (# A book with a Goodreads id and multiple series
                {'identifiers':{'goodreads': '256541'},
                    'title':'The Poet', 'authors':['Michael Connelly']},
                [title_test('The Poet', exact=True),
                 authors_test(['Michael Connelly']),
                 series_test('Jack McEvoy', 1.0),
                 isbn_test('9780752863917')]
            ),

            (# A book with a a large print edition variant
                {'title':'Starship Thrive', 'authors':['Ginger Booth']},
                [title_test('Starship Thrive', exact=True),
                 authors_test(['Ginger Booth']),
                 series_test('Thrive Space Colony Adventures', 4.0)]
            ),
        ])

    # Title-only search falls back to author+title. Kept separate because the
    # selected edition is an omnibus with no series. Accept any edition whose
    # title starts with 'The Gift' (the omnibus does), but reject collections
    # that merely mention it.
    test_identify_plugin(Goodreads.name,
        [
            ({'title':'The Gift', 'authors':['Nora Roberts']},
                [title_starts_with_test('The Gift'),
                 authors_test(['Nora Roberts'])]
            ),
        ], fail_missing_meta=False)
