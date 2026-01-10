from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import time, re, json
try:
    from urllib.parse import quote, urlencode
except ImportError:
    from urllib import quote, urlencode
try:
    from queue import Empty, Queue
except ImportError:
    from Queue import Empty, Queue

from six import text_type as unicode

from calibre import as_unicode
from calibre.ebooks.metadata.sources.base import Source
from calibre.utils.icu import lower as icu_lower
from calibre.utils.localization import get_udc

# Querying FantasticFiction is complicated by the fact that the webpage is not a
# single result and is instead built dynamically using javascript iFrames.
# So we need to instead do the same queries the javascript would do and piece
# the results together.

# ------------------------------------------------------------------
# LATEST format of Fantastic Fiction querying
# ------------------------------------------------------------------

'''
json = {
  "status": {
    "rid": "l4uHja8zm+OBAQrUR7k=",
    "time-ms": 0
  },
  "hits": {
    "found": 1,
    "start": 0,
    "hit": [
      {
        "id": "w253217",
        "fields": {
          "booktype": "1",
          "title": "61 Hours",
          "pfn": "c/lee-child/61-hours.htm",
          "year": "2010",
          "authorsinfo": "c/lee-child|Lee Child|15807|FF",
          "genrepage": [
            "T"
          ],
          "series_links": [
            "/c/lee-child/jack-reacher/"
          ],
          "seriesinfo": "Jack Reacher|14",
          "imageurl_amazon": "https://m.media-amazon.com/images/I/51PdZTNGZ5L._SL500_.jpg",
          "imageurl_amazonuk": "https://m.media-amazon.com/images/I/41UR4mMa8CS._SL500_.jpg",
          "imageurl_amazonca": "https://m.media-amazon.com/images/I/51PdZTNGZ5L._SL500_.jpg",
          "db": [
            "FF"
          ]
        }
      }
    ]
  }
}
'''

class FantasticFiction(Source):

    name = 'Fantastic Fiction'
    description = 'Downloads metadata and covers from FantasticFiction.com'
    author = 'Grant Drake'
    version = (1, 7, 4)
    minimum_calibre_version = (2, 85, 1)

    ID_NAME = 'ff'
    capabilities = frozenset(['identify', 'cover'])
    touched_fields = frozenset(['title', 'authors', 'identifier:' + ID_NAME,
        'comments', 'pubdate', 'series', 'tags'])
    has_html_comments = True
    supports_gzip_transfer_encoding = True

    BASE_URL = 'https://www.fantasticfiction.com'

    def config_widget(self):
        '''
        Overriding the default configuration screen for our own custom configuration
        '''
        from calibre_plugins.fantastic_fiction.config import ConfigWidget
        return ConfigWidget(self)

    def get_book_url(self, identifiers):
        ff_id = identifiers.get(self.ID_NAME, None)
        if ff_id:
            # Check for a special case of the ff_id ending in index, indicating the authors page
            # In this case the suffix needs to be html, not htm
            if ff_id.endswith('/index'):
                return ('FantasticFiction', ff_id, '%s/%s.html' % (FantasticFiction.BASE_URL, ff_id))
            return ('FantasticFiction', ff_id, '%s/%s.htm' % (FantasticFiction.BASE_URL, ff_id))
            

    def id_from_url(self, url):
        match = re.match(self.BASE_URL + "/(.*)\.htm.*", url)
        if match:
            return (self.ID_NAME, match.groups(0)[0])
        return None
        
    def get_cached_cover_url(self, identifiers):
        url = None
        ff_id = identifiers.get(self.ID_NAME, None)
        if ff_id is None:
            isbn = identifiers.get('isbn', None)
            if isbn is not None:
                ff_id = self.cached_isbn_to_identifier(isbn)
        if ff_id is not None:
            url = self.cached_identifier_to_cover_url(ff_id)
        return url

    def get_country(self, log, timeout=30):
        # Just return the default - previous website logic no longer works.
        country = 'GB'
        return country

    def get_rank(self, country):
        rank = 'visits_us';
        if country == 'GB':
            rank = 'visits_uk';
        elif country == 'CA':
            rank = 'visits_ca';
        elif country == 'AU':
            rank = 'visits_au';
        elif country == 'FR':
            rank = 'visits_fr';
        elif country == 'DE':
            rank = 'visits_de';
        return rank

    def create_title_query(self, log, country, title=None):
        # Originally this function queries for both title and authors, however the FF website
        # search only support searching one or the other. So we choose title, and then in
        # the JSON results will find the result that matches our author.
        q = ''
        rank = self.get_rank(country)
        if title:
            # Fantastic Fiction doesn't cope very well with non ascii names so convert
            tokens = []
            if title:
                title = title.replace('?', '')
                title = title.replace('&', 'and')
                if ' a novel' in title:
                    title = title.replace(' a novel', '')
                if title.startswith('the '):
                    title = title[4:]
                title = get_udc().decode(title)
                title_tokens = list(self.get_title_tokens(title,
                                    strip_joiners=False, strip_subtitle=True))
                tokens += title_tokens
            '''
                GRANT: 13 Nov 2021 - Apostrophes cause a problem for FF queries - need to strip them
                out which get_title_tokens and get_author_tokens does not do, otherwise they get 
                double encoded and results in a likelihood of no matches from FF.
            '''     
            tokens = [t.replace('\'','') for t in tokens]             
            tokens = [quote(t.encode('utf-8') if isinstance(t, unicode) else t) for t in tokens]
            q = ' '.join(tokens)
        if not q:
            return None
        querystring = urlencode({
                'q.parser': 'structured',
                'q': "(and db:'FF' searchstr:'%s')" % q,
                'start': 0,
                'size': 20,
                'sort': "%s desc" % rank,
                'return': 'booktype,title,atitle,vtitle,year,pfn,hasimage,authorsinfo,seriesinfo,db,imageloc,imageurl_amazon,imageurl_amazonuk,imageurl_amazonca,genrepage,series_links,vtitlecountry,hidevtitle',
            })
        return FantasticFiction.BASE_URL + "/dbs/books2?" + querystring

    def identify(self, log, result_queue, abort, title=None, authors=None,
            identifiers={}, timeout=30):
        '''
        Note this method will retry without identifiers automatically if no
        match is found with identifiers.
        '''
        matches = []
        br = self.browser
        br.set_current_header('Referer', 'https://www.fantasticfiction.com/search/?searchfor=book')
        from calibre_plugins.fantastic_fiction.config import plugin_prefs, STORE_NAME, KEY_AWS_COOKIE
        c = plugin_prefs[STORE_NAME]
        cookie_value = c.get(KEY_AWS_COOKIE, '')
        if cookie_value:
            br.set_current_header('Cookie', cookie_value)
        else:
            log.error(_('No AWS WAF cookie value configured in options for this plugin, requests will fail'))

        # If we have a Fantastic Fiction id then we do not need to fire a "search"
        # at fantasticfiction.co.uk. Instead we will go straight to the URL for that book.
        ff_id = identifiers.get(self.ID_NAME, None)
        if ff_id:
            matches.append('%s/%s.htm' % (FantasticFiction.BASE_URL, ff_id))
        else:
            country = self.get_country(log)
            query = self.create_title_query(log, country, title=title)
            if query is None:
                log.error('Insufficient metadata to construct query')
                return
            try:
                log.info('Querying: %s' % query)
                raw = br.open_novisit(query, timeout=timeout).read()
                #log.info('JSON Result: %s' % raw)
                # open('E:\\json.html', 'wb').write(raw)
            except Exception as e:
                err = 'Failed to make identify query'
                log.exception(err)
                return as_unicode(e)

            # Our response contains a json dictionary 
            if not raw:
                log.error('No JSON data received from query - FF are being mean to us')
                return
            json_result = json.loads(raw)
            if json_result['hits']['found'] > 0:
                for hit in json_result['hits']['hit']:
                    data = hit['fields']
                    # Now grab the match from the search result, provided the
                    # title and authors appear to be for the same book
                    self._parse_book_script_detail(log, title, authors, data, matches)
            if not matches:
                log.error('No matches found')
                return

        if abort.is_set():
            return

        if not matches:
            log.error('No matches found with query: %r' % query)
            return

        from calibre_plugins.fantastic_fiction.worker import Worker
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

    def _parse_book_script_detail(self, log, query_title, query_authors, data_map, matches):
        # Now we have our data returned, check the title/author
        title = data_map['title']
        alt_title = ''
        try:
            if len(data_map['vtitle']) > 0:
                alt_title = data_map['vtitle'][0]
        except:
            pass
        authors = [a.split('|')[1] for a in data_map['authorsinfo'].split('^')]

        correct_book = self.filter_result(log, query_title, query_authors, title, authors)
        if not correct_book and alt_title:
            correct_book = self.filter_result(log, query_title, query_authors, alt_title, authors)
        if not correct_book:
            return

        # Get the detailed url to query next
        pfn = data_map['pfn']
        result_url = '%s/%s' % (FantasticFiction.BASE_URL, pfn)
        matches.append(result_url)

    def filter_result(self, log, query_title, query_authors, title, authors):
        if title is not None:

            def tokenize_title(x):
                return icu_lower(x).replace("'", '').replace('"', '').rstrip(':')

            tokens = {tokenize_title(x) for x in title.split() if len(x) > 3}
            if tokens:
                result_tokens = {tokenize_title(x) for x in query_title.split()}
                if not tokens.intersection(result_tokens):
                    log('Ignoring result:', title, 'as its title does not match')
                    return False
        if authors:
            author_tokens = set()
            for author in authors:
                author_tokens |= {icu_lower(x) for x in author.split() if len(x) > 2}
            result_tokens = set()
            for author in query_authors:
                result_tokens |= {icu_lower(x) for x in author.split() if len(x) > 2}
            if author_tokens and not author_tokens.intersection(result_tokens):
                log('Ignoring result:', title, 'by', ' & '.join(authors), 'as its author does not match')
                return False
        log('Potential match:', title, 'by', ' & '.join(authors))
        return True
    
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


if __name__ == '__main__':  # tests
    # To run these test use:
    # calibre-debug -e __init__.py
    from calibre.ebooks.metadata.sources.test import (test_identify_plugin,
            title_test, authors_test, series_test)
    test_identify_plugin(FantasticFiction.name,
        [

            (# A book with no ISBN specified
                {'title':"Harry Potter and the Sorcerer's Stone", 'authors':['J.K. Rowling']},
                [title_test("Harry Potter and the Sorcerer's Stone",
                    exact=True), authors_test(['J. K. Rowling']),
                    series_test('Harry Potter', 1.0)]

            ),

            (# A book with an ISBN
                {'identifiers':{'isbn': '9780439064866'},
                    'title':'Chamber of Secrets', 'authors':['J.K. Rowling']},
                [title_test('Harry Potter and the Chamber of Secrets',
                    exact=True), authors_test(['J. K. Rowling']),
                    series_test('Harry Potter', 2.0)]

            ),

            (# A book with a Fantastic Fiction id
                {'identifiers':{'ff': 'c/lee-child/61-hours'},
                    'title':'61 Hours', 'authors':['Lee Child']},
                [title_test('61 Hours',
                    exact=True), authors_test(['Lee Child']),
                    series_test('Jack Reacher', 14.0)]

            ),
            
            (# A book with an ampersand
                {'title':"Prosper & Thrive", 'authors':['Ginger Booth']},
                [title_test("Prosper & Thrive", exact=True), 
                 authors_test(['Ginger Booth']),
                 series_test('Thrive Space Colony Adventures', 7.0)]

            ),

        ])
