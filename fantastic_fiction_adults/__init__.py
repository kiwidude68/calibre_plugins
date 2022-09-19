from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import time, re, json
try:
    from urllib.parse import quote, unquote, urlencode
except ImportError:
    from urllib import quote, unquote, urlencode
try:
    from queue import Empty, Queue
except ImportError:
    from Queue import Empty, Queue
from six import text_type as unicode

from calibre import as_unicode
from calibre.ebooks.metadata.sources.base import Source
from calibre.utils.icu import lower
from calibre.utils.localization import get_udc

# Querying FFAdultsOnly.com is complicated by the fact that the webpage is not a
# single result and is instead built dynamically using javascript iFrames.
# So we need to instead do the same queries the javascript would do and piece
# the results together.

# ------------------------------------------------------------------
# LATEST format of Fantastic Fiction querying
# ------------------------------------------------------------------

# First we need to call a php script to get back a unique timestamp identifier giving the js below:
# http://script.ffadultsonly.com/ff-v3.php

'''
var country = 'GB';var stamp = '20120605082304_10949358814fcdfa28efa8c4.98902069_fa846c05a9d23c2392ce89e5da01d97b';
'''

# Then we fire a query for our search. FF does all sorts of fancy diatrics substitutions, I'm not bothering!
# http://www.ffadultsonly.com/db-search/v4/books/?q={search}&start=0&size=10&rank=-visits_us&return-fields=booktype,title,atitle,vtitle,year,pfn,hasimage,authorsinfo,seriesinfo&stamp={STAMP FROM ABOVE}
#
#    rank = '-visits_us';
#    if (sortby == '0') {
#      if (country == 'GB') {
#        rank = '-visits_uk';
#      } else if (country == 'CA') {
#        rank = '-visits_ca';
#      } else if (country == 'AU') {
#        rank = '-visits_au';
#      } else if (country == 'FR') {
#        rank = '-visits_fr';
#      } else if (country == 'DE') {
#        rank = '-visits_de';
#      }
#
#    } else if (sortby == '1') {
#      rank = 'sorttitle';
#
#    } else if (sortby == '2') {
#      rank = 'year';
#
#    } else if (sortby == '3') {
#      rank = 'sortname';
#    }
#
#    &return-fields for this search results page will determine the data in the "hit" as follows:
#        booktype,title,atitle,vtitle,year,pfn,hasimage,authorsinfo,seriesinfo


'''
json = {"rank":"sortname",
        "match-expr":"(label 'MY SEARCH KEYWORDS')",
        "hits":{"found":1140,
                "start":1,
                "hit":[{"id":"n397891",
                        "data":{"atitle":[],
                                "authorsinfo":["f/christine-feehan|Christine Feehan"],
                                "booktype":["1"],
                                "hasimage":["y"],
                                "pfn":["f/christine-feehan/dark-storm.htm"],
                                "seriesinfo":["Dark|23"],
                                "title":["Dark Storm"],
                                "vtitle":[],
                                "year":["2012"]}}
                      ]
               },
        "info":{"rid":"8a0620f6c72ff3e77494dc4585ada1f6967c087133a4f7daa3888a62e85d6408f98cadc04e3a600e",
                "time-ms":7,
                "cpu-time-ms":0}};
searchResponse = 'ok';
display();
'''

# For querying by ISBN:
# This is the data URL:
#     http://www.ffadultsonly.com/edition/?isbn=



class FantasticFictionAdults(Source):

    name                    = 'Fantastic Fiction Adults'
    description             = _('Downloads metadata and covers from ffadultsonly.com')
    author                  = 'Grant Drake'
    version                 = (1, 3, 0)
    minimum_calibre_version = (2, 85, 1)

    ID_NAME = 'ffa'
    capabilities = frozenset(['identify', 'cover'])
    touched_fields = frozenset(['title', 'authors', 'identifier:' + ID_NAME,
        'identifier:isbn', 'comments', 'publisher', 'pubdate', 'series'])
    has_html_comments = True
    supports_gzip_transfer_encoding = True

    BASE_URL = 'https://www.ffadultsonly.com'

    # These patterns used for querying by ISBN:
    TITLE_PATTERN = re.compile(r'var x_title=unescape\(\'(.*)\'\);')
    AUTHOR_PATTERN = re.compile(r'var x_author=unescape\(\'(.*)\'\);')
    BID_PATTERN = re.compile(r'bid\d+=\'([^\']+)\'')

    def get_book_url(self, identifiers):
        ff_id = identifiers.get(self.ID_NAME, None)
        if ff_id:
            return ('FFAdultsOnly', ff_id,
                    '%s/%s.htm'%(FantasticFictionAdults.BASE_URL, ff_id))

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
        query = 'https://clu.ffadultsonly.com/clu-js'
        # Pattern used to get values from javascript text like "var foo='My value';"
        VALUE_PATTERN = re.compile(r'[^\']*\'(.*)\'')
        country = 'GB'
        return country

        # Country specific stuff is now done differently. Can't see how.
        try:
            log.info('Querying Country preference: %s'%query)
            raw = self.browser.open_novisit(query, timeout=timeout).read()
            raw = raw.decode('utf-8', 'replace')
            #open('c:\\ti.html', 'wb').write(raw)
            lines = raw.split(';')
            country_match = VALUE_PATTERN.search(lines[0])
            if country_match:
                country = country_match.groups(0)[0]
            return country
        except Exception:
            err = 'Failed to query country: %r'%query
            log.exception(err)
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

    def create_title_author_query(self, log, country, title=None, authors=None, bq='FFAO'):
        q = ''
        rank = self.get_rank(country)
        if title or authors:
            # Fantastic Fiction doesn't cope very well with non ascii names so convert
            tokens = []
            if title:
                title = title.replace('?','')
                if ' a novel' in title:
                    title = title.replace(' a novel','')
                if title.startswith('the '):
                    title = title[4:]
                title = get_udc().decode(title)
                title_tokens = list(self.get_title_tokens(title,
                                    strip_joiners=False, strip_subtitle=True))
                tokens += title_tokens
            if authors:
                authors = [get_udc().decode(a) for a in authors]
                author_tokens = self.get_author_tokens(authors,
                        only_first_author=True)
                tokens += author_tokens
            tokens = [quote(t.encode('utf-8') if isinstance(t, unicode) else t) for t in tokens]
            q = ' '.join(tokens)
        if not q:
            return None
#         return self.BASE_URL + "/dbs/books?bq='%s'&%s&start=0&size=20&rank=%s&return-fields=booktype,title,atitle,vtitle,year,pfn,hasimage,authorsinfo,seriesinfo,db,imageloc" \
#             % (bq, q, rank)
        querystring = urlencode({
                'q.parser': 'structured',
                'q': "(and db:'AO' '%s')" % (q,),
                'size': 20,
                'start': 0,
                'sort': "%s desc" % rank,
                'return': 'booktype,title,atitle,vtitle,year,pfn,hasimage,authorsinfo,seriesinfo,db,imageloc',
            })
#         return FantasticFiction.BASE_URL + "/dbs/books?bq='FF'&%s&start=0&size=20&rank=%s&return-fields=booktype,title,atitle,vtitle,year,pfn,hasimage,authorsinfo,seriesinfo,db,imageloc" \
#         return FantasticFiction.BASE_URL + "/dbs/books2?q.parser=structured&q=(and db:'FF' '%s')&start=0&size=20&sort=%s desc&return=booktype,title,atitle,vtitle,year,pfn,hasimage,authorsinfo,seriesinfo,db,imageloc" \
#             % (q, rank)
        return self.BASE_URL + "/dbs/books2?" + querystring

    def query_via_isbn_for_title_author(self, log, isbn, timeout=30):
        query = FantasticFictionAdults.BASE_URL + '/edition/?isbn=%s'%isbn
        try:
            log.info('Querying ISBN: %s'%query)
            raw = self.browser.open_novisit(query, timeout=timeout).read()
            raw = raw.decode('utf-8', 'replace')
            #open('E:\\ti.html', 'wb').write(raw)
            title = None
            authors = []
            title_match = FantasticFictionAdults.TITLE_PATTERN.search(raw)
            author_match = FantasticFictionAdults.AUTHOR_PATTERN.search(raw)
            if title_match and author_match:
                authors = [unquote(author_match.groups(0)[0])]
                title = unquote(title_match.groups(0)[0])
                if '(' in title:
                    # Title has other crap in it like publisher and series
                    title = title.split('(')[0].strip()
                # Any titles with a colon in them we will strip the colon from
                # so that subsequent words are not ignored.
                # e.g. Doom: Hell On Earth
                title = title.replace(':',' ')
            return None, title, authors
        except Exception as e:
            err = 'Failed to make ISBN query: %r'%query
            log.exception(err)
            return as_unicode(e), None, None

    def identify(self, log, result_queue, abort, title=None, authors=None,
            identifiers={}, timeout=30):
        '''
        Note this method will retry without identifiers automatically if no
        match is found with identifiers.
        '''
        matches = []

        # If we have a Fantastic Fiction id then we do not need to fire a "search"
        # at ffadultsonly.com. Instead we will go straight to the URL for that book.
        ff_id = identifiers.get(self.ID_NAME, None)
        br = self.browser
        if ff_id:
            matches.append('%s/%s.htm'%(FantasticFictionAdults.BASE_URL, ff_id))
        else:
            isbn = identifiers.get('isbn', None)
            orig_title = title
            orig_authors = authors
            if isbn and False: # Latest API doesn't seem to support search by ISBN     
                error, isbn_title, isbn_authors = self.query_via_isbn_for_title_author(log, isbn, timeout=30)
                if error and (not title and authors):
                    # We tried with ISBN but cannot fall back to doing a title/author search
                    return error
                # Use the title/author from the ISBN for next phase of search
                # However if that fails (since FF can return some strange titles
                # at this point) then we will retry with the orig title/authors
                if isbn_title and isbn_authors:
                    title = isbn_title
                    authors = isbn_authors

            country = self.get_country(log)
            # Neeed to check two different databases and then with both sets of titles and authors.
            ff_dbs = ['AO'] #['FFA', 'FFAO', 'AO']
            title_authors = [(title, authors), (orig_title, orig_authors)]
            for (dbs, title_author) in ((x,y) for x in ff_dbs for y in title_authors):
#                 log.error('dbs=', dbs)
#                 log.error('title_author=', title_author)
                query = self.create_title_author_query(log, country, title=title_author[0], authors=title_author[1], bq=dbs)
                if query is None:
                    log.error('Insufficient metadata to construct query')
                    return
                try:
                    log.info('Querying: %s'%query)
                    raw = br.open_novisit(query, timeout=timeout).read()
                    #open('C:\\json.html', 'wb').write(raw)
                except Exception as e:
                    err = 'Failed to make identify query'
                    log.exception(err)
                    return as_unicode(e)

                # Our response contains a json dictionary 
                json_result = json.loads(raw)
#                 log.error('json_result=', json_result)
                if json_result['hits']['found'] > 0:
                    log.error('have hits')
                    max_ids_to_search = 33
                    count = 0
                    for hit in json_result['hits']['hit']:
                        data = hit['fields']
#                         log.error('fields=', data)
                        # Now grab the match from the search result, provided the
                        # title and authors appear to be for the same book
                        self._parse_book_script_detail(log, title, authors, orig_title, orig_authors,
                                                       data, matches, timeout)
                        if matches:
                            log.error('have matches')
                            break
                        count += 1
                        if count>= max_ids_to_search:
                            break
                    if matches:
                        break

        if abort.is_set():
            return

        if not matches:
            log.error('No matches found with query: %r'%query)
            return

        from calibre_plugins.fantastic_fiction_adults.worker import Worker
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

    def _parse_book_script_detail(self, log, query_title, query_authors,
                                  orig_title, orig_authors, data_map, matches, timeout):
        title_tokens = list(self.get_title_tokens(query_title))
        author_tokens = list(self.get_author_tokens(query_authors))

        # Now we have our data returned, check the title/author
        title = data_map['title']
        alt_title = ''
        try:
            if len(data_map['vtitle']) > 0:
                alt_title = data_map['vtitle'][0]
        except:
            pass
        authors = [a.split('|')[1] for a in data_map['authorsinfo'].split('^')]

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

        correct_book = ismatch(title, authors)
        if not correct_book and alt_title:
            correct_book = ismatch(alt_title, authors)
        if not correct_book:
            # In case we did an ISBN based lookup that gave dodgy title/authors,
            # try again with the original title/authors
            title_tokens = list(self.get_title_tokens(orig_title))
            author_tokens = list(self.get_author_tokens(orig_authors))
            correct_book = ismatch(title, authors)
            if not correct_book and alt_title:
                correct_book = ismatch(alt_title, authors)
            if not correct_book:
                log.error('Rejecting as not close enough match: %s %s'%(title, authors))
                return

        # Get the detailed url to query next
        pfn = data_map['pfn']
        result_url = '%s/%s' % (self.BASE_URL, pfn)
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
    test_identify_plugin(FantasticFictionAdults.name,
        [

            ( # A book with no ISBN specified
                {'title':'Entwined with You', 'authors':['Sylvia Day']},
                [title_test('Entwined with You',
                    exact=True), authors_test(['Sylvia Day']),
                    series_test('Crossfire', 3.0)]

            ),

            ( # A book with an ISBN
                {'identifiers':{'isbn': '1410455629'},
                    'title':'Entwined with You', 'authors':['Sylvia Day']},
                [title_test('Entwined with You',
                    exact=True), authors_test(['Sylvia Day']),
                    series_test('Crossfire', 3.0)]

            ),

            ( # A book with a Fantastic FictionAdults Only id
                {'identifiers':{'ffa': 'd/sylvia-day/entwined-with-you'},
                    'title':'Entwined with You', 'authors':['Sylvia Day']},
                [title_test('Entwined with You',
                    exact=True), authors_test(['Sylvia Day']),
                    series_test('Crossfire', 3.0)]

            ),

        ])
