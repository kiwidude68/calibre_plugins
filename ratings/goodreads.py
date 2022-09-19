from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import socket, re, json
from threading import Thread

from lxml.html import fromstring, tostring
from calibre import browser
from calibre.utils.cleantext import clean_ascii_chars

class GoodreadsRatingWorker(Thread):
    '''
    Get book details from Goodreads book page
    '''
    def __init__(self, goodreads_id, log, timeout=20):
        Thread.__init__(self)
        self.daemon = True
        self.goodreads_id = goodreads_id
        self.log = log
        self.timeout = timeout
        self.rating = None
        self.rating_count = None

    def run(self):
        try:
            self.url = 'http://www.goodreads.com/book/show/%s'%self.goodreads_id
            self.get_details()
        except:
            self.log.exception('get_details failed for url: %r'%self.url)

    def get_details(self):
        try:
            self.log.info('Goodreads book url: %r'%self.url)
            br = browser()
            raw = br.open_novisit(self.url, timeout=self.timeout).read().strip()
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

        raw = raw.decode('utf-8', errors='replace')
        #open('E:\\goodreads.html', 'wb').write(raw)

        if '<title>404 - ' in raw:
            self.log.error('URL malformed: %r'%self.url)
            return

        try:
            root = fromstring(clean_ascii_chars(raw))
        except:
            msg = 'Failed to parse goodreads details page: %r'%self.url
            self.log.exception(msg)
            return

        errmsg = root.xpath('//*[@id="errorMessage"]')
        if errmsg:
            msg = 'Failed to parse goodreads details page: %r'%self.url
            msg += tostring(errmsg, method='text', encoding='unicode').strip()
            self.log.error(msg)
            return

        try:
            work_json = self.parse_book_json(root)
            self.parse_details(root, work_json)
        except:
            msg = 'Failed attempting to read book json meta tag from: %r'%self.url
            self.log.exception(msg)
            return
        
    def parse_book_json(self, root):
        script_node = root.xpath('//script[@id="__NEXT_DATA__"]')
        if not script_node:
            self.log.info('Goodreads page is legacy html format')
            return None
        try:
            self.log.info('Goodreads json script node found, page in 2022+ html format')
            book_props_json = json.loads(script_node[0].text)
            # script has a complicated hierarchy we need to traverse to get node we want
            apolloState = book_props_json["props"]["pageProps"]["apolloState"]
            # now must iterate keys to find the one starting with Book, and array of all Contributors
            work_json = None
            for key in apolloState.keys():
                if key.startswith("Work:"):
                    # Should only be one Work node.
                    work_json = apolloState[key]
             
            return work_json
        except:
            self.log.exception('Goodreads failed to parse book json: %r'%script_node[0].text)
            return None

    def parse_details(self, root, work_json):
        try:
            if work_json:
                self.rating = self.parse_rating(work_json)
            else:
                self.rating = self.parse_rating_legacy(root)
        except:
            self.log.exception('Error parsing ratings for url: %r'%self.url)
        try:
            if work_json:
                self.rating_count = self.parse_rating_count(work_json)
            else:
                self.rating_count = self.parse_rating_count_legacy(root)
        except:
            self.log.exception('Error parsing rating count for url: %r'%self.url)

    def parse_rating(self, work_json):
        if "stats" not in work_json:
            return None
        stats_json = work_json["stats"]        
        if "averageRating" not in stats_json:
            return None
        rating = float(stats_json["averageRating"])
        return rating

    def parse_rating_legacy(self, root):
        rating_node = root.xpath('//span[@itemprop="ratingValue"]')
        if rating_node:
            rating_text = tostring(rating_node[0], method='text', encoding='unicode')
            rating_text = re.sub('[^0-9]', '', rating_text)
            rating_value = float(rating_text)
            if rating_value >= 100:
                return rating_value / 100
            return rating_value

    def parse_rating_count(self, work_json):
        if "stats" not in work_json:
            return None
        stats_json = work_json["stats"]        
        if "ratingsCount" not in stats_json:
            return None
        rating_count = int(stats_json["ratingsCount"])
        return rating_count

    def parse_rating_count_legacy(self, root):
        rating_node = root.xpath('//meta[@itemprop="ratingCount"]')
        if rating_node:
            rating_text = tostring(rating_node[0], method='text', encoding='unicode').strip()
            rating_text = re.sub('[^0-9]', '', rating_text)
            rating_count = int(rating_text)
            return rating_count
