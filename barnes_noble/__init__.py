from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import time, re, random
from six import text_type as unicode
from six.moves.urllib.parse import quote
try:
    from queue import Empty, Queue
except ImportError:
    from Queue import Empty, Queue
from collections import OrderedDict

from lxml.html import fromstring

from calibre import as_unicode
from calibre.constants import numeric_version as calibre_version
from calibre.ebooks.metadata import check_isbn
from calibre.ebooks.metadata.sources.base import Source
from calibre.utils.icu import lower
from calibre.utils.cleantext import clean_ascii_chars
from calibre.utils.localization import get_udc

class BarnesNoble(Source):

    name = 'Barnes & Noble'
    description = 'Downloads metadata and covers from Barnes & Noble'
    author = 'Grant Drake'
    version = (1, 5, 6)
    minimum_calibre_version = (2, 0, 0)

    ID_NAME = 'barnesnoble'
    capabilities = frozenset(['identify', 'cover'])
    touched_fields = frozenset(['title', 'authors', 'identifier:' + ID_NAME,
        'identifier:isbn', 'rating', 'comments', 'publisher', 'pubdate',
        'series'])
    has_html_comments = True
    supports_gzip_transfer_encoding = True

    BASE_URL = 'https://search.barnesandnoble.com'
    BROWSE_URL = 'https://www.barnesandnoble.com'
    SEARCH_URL = 'https://www.barnesandnoble.com/s'

    def config_widget(self):
        '''
        Overriding the default configuration screen for our own custom configuration
        '''
        from calibre_plugins.barnes_noble.config import ConfigWidget
        return ConfigWidget(self)

    @property
    def user_agent(self):
        # May 2024 - B&N started getting picky about the user agent, rejecting Chrome version 80 which was the calibre default.
        return 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0'

    def get_book_url(self, identifiers):
        barnes_noble_id = identifiers.get(self.ID_NAME, None)
        if barnes_noble_id:
            url = self.format_url_for_id(barnes_noble_id)
            return (self.ID_NAME, barnes_noble_id, url)

    def format_url_for_id(self, barnes_noble_id):
        if '/' in barnes_noble_id:
            # historically the B&N identifier was the full path to the book 
            # e.g. w/loyalty-lisa-scottoline/1141707914
            url = '%s/%s' % (BarnesNoble.BROWSE_URL, barnes_noble_id)
        else:
            # As of 1.5.0 the B&N identifier will just be a numeric identifier e.g. 1141707914
            # B&N will itself redirect to a page with the full URL, or we use w/<id> e.g. w/1141707914
            url = '%s/w/%s' % (BarnesNoble.BROWSE_URL, barnes_noble_id)
        return url

    def id_from_url(self, url):
        match = re.match(self.BROWSE_URL + r"/.*/(\d+).*", url)
        if match:
            return (self.ID_NAME, match.groups(0)[0])
        return None

    def create_query(self, log, title=None, authors=None, identifiers={}):
        isbn = check_isbn(identifiers.get('isbn', None))
        if isbn is not None:
            return '%s/s/%s?ean=%s' % (BarnesNoble.BROWSE_URL, isbn, isbn)
        tokens = []
        if title:
            title = title.replace('?', '')
            title_tokens = list(self.get_title_tokens(title,
                                strip_joiners=False, strip_subtitle=True))
            if title_tokens:
                tokens += [quote(t.encode('utf-8') if isinstance(t, unicode) else t) for t in title_tokens]
        if authors:
            author_tokens = self.get_author_tokens(authors,
                    only_first_author=True)
            if author_tokens:
                tokens += [quote(t.encode('utf-8') if isinstance(t, unicode) else t) for t in author_tokens]
        if len(tokens) == 0:
            return None
        return BarnesNoble.SEARCH_URL + '/' + '%20'.join(tokens).lower()

    def get_cached_cover_url(self, identifiers):
        url = None
        barnes_noble_id = identifiers.get('barnesnoble', None)
        if barnes_noble_id is None:
            isbn = identifiers.get('isbn', None)
            if isbn is not None:
                barnes_noble_id = self.cached_isbn_to_identifier(isbn)
        if barnes_noble_id is not None:
            url = self.cached_identifier_to_cover_url(barnes_noble_id)
        return url

    def cached_identifier_to_cover_url(self, id_):
        with self.cache_lock:
            url = self._get_cached_identifier_to_cover_url(id_)
            if not url:
                # Try for a "small" image in the cache
                url = self._get_cached_identifier_to_cover_url('small/' + id_)
            return url

    def _get_cached_identifier_to_cover_url(self, id_):
        # This must only be called once we have the cache lock
        url = self._identifier_to_cover_url_cache.get(id_, None)
        if not url:
            # We could not get a url for this particular B&N id
            # However we might have one for a different isbn for this book
            # Barnes & Noble are not very consistent with their covers and
            # it could be that the particular ISBN we chose does not have
            # a large image but another ISBN we retrieved does.
            for key in self._identifier_to_cover_url_cache.keys():
                if key.startswith('key_prefix'):
                    return self._identifier_to_cover_url_cache[key]
        return url

    def identify(self, log, result_queue, abort, title=None, authors=None,
            identifiers={}, timeout=30):
        '''
        Note this method will retry without identifiers automatically if no
        match is found with identifiers.
        '''
        matches = []
        # If we have a Barnes & Noble id then we do not need to fire a "search"
        # at barnesnoble.com. Instead we will go straight to the URL for that book.
        barnes_noble_id = identifiers.get('barnesnoble', None)
        isbn = check_isbn(identifiers.get('isbn', None))
        br = self.browser
        if barnes_noble_id:
            log.info('Found barnes noble ID: %r' % barnes_noble_id)
            id_url = self.format_url_for_id(barnes_noble_id)
            log.info('Adding match: %s' % id_url)
            matches.append(id_url)
        else:
            # Barnes & Noble doesn't cope very well with non ascii names so convert
            title = get_udc().decode(title)
            authors = [get_udc().decode(a) for a in authors]
            query = self.create_query(log, title=title, authors=authors,
                    identifiers=identifiers)
            if query is None:
                log.error('Insufficient metadata to construct query')
                return
            multiple_results_found = False
            try:
                log.info('Querying: %s' % query)
                br.set_current_header('Accept','*/*')
                br.set_current_header('Accept-Encoding','gzip, deflate, br')
                response = br.open_novisit(query, timeout=timeout)
                # Check whether we got redirected to a book page.
                # If we did, will use the url.
                # If we didn't then treat it as no matches on Barnes & Noble
                location = response.geturl()
                # If not an exact match we can get a search results page back
                multiple_results_found = location.find('/s/') > 0
                if location.find('noresults') == -1 and not multiple_results_found:
                    # This still might not be a specific book page
                    # e.g. if no ISBN match, B&N can bounce back to the home page.
                    if len(location) > len(BarnesNoble.BROWSE_URL) + 2:
                        log.info('match location: %r' % location)
                        matches.append(location)
            except Exception as e:
                if isbn and callable(getattr(e, 'getcode', None)) and e.getcode() == 404:
                    # We did a lookup by ISBN but did not find a match
                    # We will fallback to doing a lookup by title author
                    log.info('Failed to find match for ISBN: %s' % isbn)
                elif callable(getattr(e, 'getcode', None)) and e.getcode() == 404:
                    log.error('No matches for identify query')
                    return as_unicode(e)
                else:
                    err = 'Failed to make identify query'
                    log.exception(err)
                    return as_unicode(e)

            if multiple_results_found:
                try:
                    log.info('Parsing search results')
                    raw = response.read().strip()
                    #open('E:\\search_results.html', 'wb').write(raw)
                    raw = raw.decode('utf-8', errors='replace').replace('&hellip;','')
                    if not raw:
                        log.error('Failed to get raw result for query')
                        return
                    root = fromstring(clean_ascii_chars(raw))
                    # Now grab the matches from the search results, provided the
                    # title and authors appear to be for the same book
                    self._parse_search_results(log, title, authors, root, matches, timeout)
                except:
                    msg = 'Failed to parse Barnes & Noble page for query'
                    log.exception(msg)
                    return msg

        if abort.is_set():
            return

        if not matches:
            if (barnes_noble_id or isbn) and title and authors:
                log.info('No matches found with identifiers, retrying using only'
                        ' title and authors')
                return self.identify(log, result_queue, abort, title=title,
                        authors=authors, timeout=timeout)
            log.error('No matches found with query: %r' % query)
            return

        from calibre_plugins.barnes_noble.worker import Worker
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
        for e in root.iter("span"):
            if "display:none" in e.get("style", "").replace(" ", ""):
                e.text = ""

        UNSUPPORTED_FORMATS = ['audiobook', 'other format', 'cd', 'item', 'see all formats & editions']
        results = root.xpath('//div[contains(@class, "resultsListContainer")]//div[contains(@class, "product-info-view")]')
        if not results:
            results = root.xpath('//ol[contains(@class, "result-set")]/li[contains(@class, "result")]')
        if not results:
            log.info('FOUND NO RESULTS:')
            return

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

        import calibre_plugins.barnes_noble.config as cfg
        max_results = cfg.plugin_prefs[cfg.STORE_NAME][cfg.KEY_MAX_DOWNLOADS]
        title_url_map = OrderedDict()
        for result in results:
            #log.info('Looking at result:')
            #title = ''.join(result.xpath('.//img[contains(@class, "product-image")]/@alt'))
            title = result.xpath('.//div[contains(@class, "product-shelf-title")]')
            if not title:
                #log.info('Could not find title')
                continue
            title = title[0].text_content().strip()
            # Strip off any series information from the title
            #log.info('FOUND TITLE:',title)
            if '(' in title:
                #log.info('Stripping off series(')
                title = title.rpartition('(')[0].strip()
            # Also strip off any NOOK Book stuff from the title
            title = title.replace('[NOOK Book]', '').strip()

            #contributors = result.xpath('.//ul[@class="contributors"]//li[position()>1]//a')
            #contributors = result.xpath('.//a[@class="contributor"]')
            contributors = result.xpath('.//div[contains(@class, "product-shelf-author")]/a')
            authors = []
            for c in contributors:
                author = c.text_content().split(',')[0]
                #log.info('Found author:',author)
                if author.strip():
                    authors.append(author.strip())

            #log.info('Looking at tokens: %r %r'% title_tokens, author_tokens)
            title_tokens = list(self.get_title_tokens(orig_title))
            author_tokens = list(self.get_author_tokens(orig_authors))
            if not ismatch(title, authors):
                log.info('Rejecting as not close enough match: %s by %s' % (title, ' & '.join(authors)))
                continue
            
            log.info('Considering search result: %s by %s' % (title, ' & '.join(authors)))

            # Validate that the format is one we are interested in
            #format_details = result.xpath('.//span[@class="format"]/text()')
            format_details = result.xpath('(.//div[contains(@class, "product-shelf-pricing")]//span)[1]') # gridView format
            if not format_details:
                format_details = result.xpath('(.//div[contains(@class, "product-shelf-pricing")]//a)[1]') # listView format

            #format_details = result.xpath('.//ul[@class="formats"]/li/a/text()')
            valid_format = False
            for format in format_details:
                format_text = format.text_content().strip().lower()
                #log.info('**Found format: %s'%format_text)
                if format_text not in UNSUPPORTED_FORMATS:
                    valid_format = True
                    break
            result_url = None
            if valid_format:
                # Get the detailed url to query next
                #result_url = ''.join(result.xpath('.//a[@class="title"]/@href'))
                result_url = ''.join(result.xpath('.//div[contains(@class, "product-shelf-title")]/a/@href'))
                if result_url.startswith('/'):
                    result_url = BarnesNoble.BROWSE_URL + result_url
                #log.info('**Found href: %s'%result_url)

            if result_url and title not in title_url_map:
                title_url_map[title] = result_url
                if len(title_url_map) >= 5:
                    break

        for title in title_url_map.keys():
            matches.append(title_url_map[title])
            if len(matches) >= max_results:
                break


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
        br.set_current_header('Accept','*/*')
        br.set_current_header('Accept-Encoding','gzip, deflate, br')
        log('Downloading cover from:', cached_url)
        try:
            cdata = br.open_novisit(cached_url, timeout=timeout).read()
            result_queue.put((self, cdata))
        except:
            log.exception('Failed to download cover from:', cached_url)


if __name__ == '__main__': # tests
    # To run these test use:
    # calibre-debug -e __init__.py
    from calibre import prints
    from calibre.ebooks.metadata.sources.test import (test_identify_plugin,
            title_test, authors_test, series_test)

    def cover_test(cover_url):
        if cover_url is not None:
            cover_url = cover_url.lower()

        def test(mi):
            mc = mi.cover_url
            if mc is not None:
                mc = mc.lower()
            if mc == cover_url:
                return True
            prints('Cover test failed. Expected: \'%s\' found: ' % cover_url, mc)
            return False

        return test

    test_identify_plugin(BarnesNoble.name,
        [

            (# A book with an ISBN
                {'identifiers':{'isbn': '9780439064866'},
                    'title':'Chamber of Secrets', 'authors':['J.K. Rowling']},
                [title_test('Harry Potter and the Chamber of Secrets', exact=True),
                 authors_test(['J. K. Rowling']),
                 series_test('Harry Potter', 2.0),
                 cover_test('http://prodimage.images-bn.com/lf?source=url[file:images/Images/pimages/4866/9780439064866_p0.jpg]&sink')]
            ),

            (# A book with no ISBN specified
                {'title':"Stone of Tears", 'authors':['Terry Goodkind']},
                [title_test("Stone of Tears", exact=True),
                 authors_test(['Terry Goodkind']),
                 series_test('Sword of Truth', 2.0),
                 cover_test('http://prodimage.images-bn.com/lf?source=url[file:images/Images/pimages/8099/9780812548099_p0.jpg]&sink')]
            ),

            (# A book with a Barnes & Noble id
                {'identifiers':{'barnesnoble': 'w/61-hours-lee-child/1018914303'},
                    'title':'61 Hours', 'authors':['Lee Child']},
                [title_test('61 Hours', exact=True),
                 authors_test(['Lee Child']),
                 series_test('Jack Reacher', 14.0),
                 cover_test('http://prodimage.images-bn.com/lf?source=url[file:images/Images/pimages/1598/9780345541598_p0.jpg]&sink')]
            ),

            (# A book with an NA cover
                {'identifiers':{'isbn':'9780451063953'},
                 'title':'The Girl Hunters', 'authors':['Mickey Spillane']},
                [title_test('The Girl Hunters', exact=True),
                 authors_test(['Mickey Spillane']),
                 cover_test(None)]
            ),

        ], fail_missing_meta=False)
