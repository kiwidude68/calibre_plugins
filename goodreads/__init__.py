from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import time, json, os, re, random, traceback
import xml.etree.ElementTree as et

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote
try:
    from queue import Empty, Queue
except ImportError:
    from Queue import Empty, Queue

from six import text_type as unicode

from lxml import etree
from lxml.html import fromstring

from calibre import as_unicode
from calibre.ebooks import normalize
from calibre.ebooks.metadata import check_isbn
from calibre.ebooks.metadata.sources.base import Source, fixcase, fixauthors
from calibre.utils.icu import lower
from calibre.utils.cleantext import clean_ascii_chars
from calibre.constants import numeric_version as calibre_version


RECOVER_PARSER = etree.XMLParser(recover=True, no_network=True, resolve_entities=False)

class Goodreads(Source):

    name = 'Goodreads'
    description = 'Downloads metadata and covers from Goodreads'
    author = 'Grant Drake'
    version = (1, 9, 0)
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
    API_KEY = 'UxvtOM3ogQWjfgiCnMleA'

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
        
    def create_query(self, title=None, authors=None):
        tokens = []
        scope = ''
        if title or authors:
            title_tokens = list(self.get_title_tokens(title, strip_joiners=False, strip_subtitle=True))
            tokens += title_tokens
            author_tokens = self.get_author_tokens(authors, only_first_author=True)
            tokens += author_tokens
            tokens = [quote(t.encode('utf-8') if isinstance(t, unicode) else t) for t in tokens]
            if authors and not title:
                scope = 'search=author&'
            elif title and not authors:
                scope = 'search=title&'
        else:
            return None
        query = '+'.join(tokens)
        return '%s/search/search.xml?%spage=1&q=%s&key=%s' % (Goodreads.BASE_URL, scope, query, self.API_KEY)

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

    def get_goodreads_id_using_api(self, log, abort, timeout=30, identifier=None):
        
        log.debug('get_goodreads_id_using_api - identifiers=%s' % identifier)
        
        if not identifier:
            return None
        
        goodreads_id = None
        
        br = self.browser
        autocomplete_api_url = "https://www.goodreads.com/book/auto_complete?format=json&q="
        query = autocomplete_api_url + identifier

        if abort.is_set():
            return
       
        try:
            log.info('Querying using autocomplete API: %s' % query)
            raw = br.open_novisit(query, timeout=timeout).read()
            log.debug('JSON Result: %s'%raw)
        except Exception as e:
            err = 'Failed to make identify query: %r' % query
            log.exception(err)
            raise

        if raw:
            json_result = json.loads(raw)
            if len(json_result) >= 1:
                goodreads_id = json_result[0].get('bookId', None)
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
            matches.append('%s/book/show/%s' % (Goodreads.BASE_URL, goodreads_id))
        else:
            # Can't find a valid id, so search using the title and authors.
            log.info('No identifiers, searching for title/author')
            title = normalize(title)
            query = self.create_query(title=title, authors=authors)
            if query is None:
                log.error('Insufficient metadata to construct query')
                return
            try:
                log.info('Querying: %s' % query)
                response = br.open_novisit(query, timeout=timeout)
            except Exception as e:
                err = 'Failed to make identify query: %r' % query
                log.exception(err)
                return as_unicode(e)

            try:
                raw = response.read().strip()
                raw = raw.decode('utf-8', errors='replace')
                #open('E:\\goodreads_search.xml', 'wb').write(raw)
                if not raw:
                    log.error('Failed to get raw result for query: %r' % query)
                    return
                root = self.get_xml_tree(raw)
            except:
                msg = 'Failed to parse goodreads page for query: %r' % query
                log.exception(msg)
                return msg
            # Now grab the first value from the search results, provided the
            # title and authors appear to be for the same book
            self._parse_search_results(log, title, authors, root, matches, timeout)

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

    def get_xml_tree(self, content):
        content = clean_ascii_chars(content)
        try:
            root = et.fromstring(content)
        except:
            traceback.format_exc()
            root = et.fromstring(content, parser=RECOVER_PARSER)
        if root is None:
            import tempfile
            cpath = os.path.join(tempfile.gettempdir(), 'xml_fail.xml')
            f = open(cpath, 'w')
            f.write(content)
            f.close()
            raise ValueError('The shelf contains a corrupting response from Goodreads. ' +
                             'This can occur for certain books or may be a temporary issue with the website. ' +
                             'See the Help file for this plugin for more details or try again later.<br><br>' +
                             'The failed xml can be found at:<br>' + cpath)
        return root

    def _convert_goodreads_title_with_series(self, text):
        # This function attempts to convert a myriad of Goodreads title
        # combinations to strip out the series information as it is not
        # available separately in the API
        if text.find('(') == -1:
            return (text, '')
        text_split = text.rpartition('(')
        title = text_split[0]
        series_info = text_split[2]
        series_info = series_info.rpartition(')')
        series_info = series_info[0]
        hash_pos = series_info.find('#')
        if hash_pos <= 0:
            # Cannot find the series # in expression or at start like (#1-7)
            # so consider whole thing just as title
            title = text
            series_info = ''
        else:
            # Check to make sure we have got all of the series information
            while series_info.count(')') != series_info.count('('):
                title_split = title.rpartition('(')
                title = title_split[0].strip()
                series_info = title_split[2] + '(' + series_info
        if series_info:
            series_partition = series_info.rpartition('#')
            series_name = series_partition[0].strip().replace(',', '')
            series_index = series_partition[2].strip()
            if series_index.find('-'):
                # The series is specified as 1-3, 1-7 etc.
                # In future we may offer config options to decide what to do,
                # such as "Use start number", "Use value xxx" like 0 etc.
                # For now will just take the start number and use that
                series_index = series_index.partition('-')[0].strip()
            series_info = '%s [%s]' % (series_name, series_index)
        return (title.strip(), series_info)

    def _parse_search_results(self, log, orig_title, orig_authors, root, matches, timeout):
        work_nodes = root.findall('search/results/work')
        if not work_nodes:
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
        
        for work_node in work_nodes:
            (title, series) = self._convert_goodreads_title_with_series(work_node.findtext('best_book/title').strip())
            author = work_node.findtext('best_book/author/name')
            if author == 'NOT A BOOK':
                # Goodreads use this author to categorise ISBNs in their databases that
                # are not actually books
                continue
            authors = [a.strip() for a in author.split(',')]
            if ismatch(title, authors):
                goodreads_id = work_node.findtext('best_book/id')
                result_url = Goodreads.BASE_URL + '/book/show/%s' % goodreads_id
                log.debug("_parse_search_results: Title: %s, Author: %s, URL: %s" % (title, author, result_url))
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
    from calibre.ebooks.metadata.sources.test import (test_identify_plugin,
            title_test, authors_test, series_test, isbn_test)

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
