from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import socket, re, datetime
from threading import Thread

from lxml.html import fromstring, tostring

from calibre.ebooks.metadata.book.base import Metadata
from calibre.library.comments import sanitize_comments_html
from calibre.utils.cleantext import clean_ascii_chars
from calibre.utils.icu import lower

class Worker(Thread): # Get details

    '''
    Get book details from Baen book page in a separate thread
    '''

    def __init__(self, url, match_authors, result_queue, browser, log, relevance, plugin, timeout=20):
        Thread.__init__(self)
        self.daemon = True
        self.url, self.result_queue = url,  result_queue
        self.match_authors = match_authors
        self.log, self.timeout = log, timeout
        self.relevance, self.plugin = relevance, plugin
        self.browser = browser.clone_browser()
        self.cover_url = self.baen_id = self.isbn = None

    def run(self):
        try:
            self.get_details()
        except:
            self.log.exception('get_details failed for url: %r'%self.url)

    def get_details(self):
        try:
            self.log.info('Baen url: %r'%self.url)
            self.log.info('Baen relevance: %r'%self.relevance)
            raw = self.browser.open_novisit(self.url, timeout=self.timeout).read().strip()
        except Exception as e:
            if callable(getattr(e, 'getcode', None)) and \
                    e.getcode() == 404:
                self.log.error('URL malformed: %r'%self.url)
                return
            attr = getattr(e, 'args', [None])
            attr = attr if attr else [None]
            if isinstance(attr[0], socket.timeout):
                msg = 'Baen timed out. Try again later.'
                self.log.error(msg)
            else:
                msg = 'Failed to make details query: %r'%self.url
                self.log.exception(msg)
            return

        raw = raw.decode('utf-8', errors='replace')
        #open('E:\\t3.html', 'wb').write(raw)

        if '<title>404 - ' in raw:
            self.log.error('URL malformed: %r'%self.url)
            return

        try:
            root = fromstring(clean_ascii_chars(raw))
        except:
            msg = 'Failed to parse Baen details page: %r'%self.url
            self.log.exception(msg)
            return

        self.parse_details(root)

    def parse_details(self, root):
        try:
            baen_id = self.parse_baen_id(self.url)
        except:
            self.log.exception('Error parsing Baen id for url: %r'%self.url)
            baen_id = None

        try:
            title = self.parse_title(root)
        except:
            self.log.exception('Error parsing title for url: %r'%self.url)
            title = None

        try:
            authors = self.parse_authors(root)
        except:
            self.log.exception('Error parsing authors for url: %r'%self.url)
            authors = []

        if not title or not authors or not baen_id:
            self.log.error('Could not find title/authors/Baen id for %r'%self.url)
            self.log.error('Baen: %r Title: %r Authors: %r'%(baen_id, title,
                authors))
            return

        mi = Metadata(title, authors)
        mi.set_identifier('baen', baen_id)
        self.baen_id = baen_id

        try:
            mi.pubdate = self.parse_published_date(root)
        except:
            self.log.exception('Error parsing published date for url: %r'%self.url)

        try:
            self.cover_url = self.parse_cover(root)
        except:
            self.log.exception('Error parsing cover for url: %r'%self.url)
        mi.has_cover = bool(self.cover_url)

        try:
            mi.comments = self.parse_comments(root)
        except:
            self.log.exception('Error parsing comments for url: %r'%self.url)

        try:
            mi.rating = self.parse_rating(root)
        except:
            self.log.exception('Error parsing rating for url: %r'%self.url)

        # There will be no other on Baen's website!
        mi.publisher = 'Baen'

        mi.source_relevance = self.relevance

        if self.baen_id:
            if self.cover_url:
                self.plugin.cache_identifier_to_cover_url(self.baen_id, self.cover_url)

        self.plugin.clean_downloaded_metadata(mi)

        self.result_queue.put(mi)

    def parse_baen_id(self, url):
        from calibre_plugins.baen import Baen # import BASE_URL
        return re.search(Baen.BASE_URL + '/(.*)\.html', url).groups(0)[0]

    def parse_title(self, root):
        title_node = root.xpath('//span[@class="product-title"]')
        if title_node:
            self.log.info("parse_title: title=", title_node[0].text)
            return title_node[0].text

    def parse_authors(self, root):
        author_node = root.xpath('//div[@class="product-shop"]/div/span[@class="author-name"]/a/text()')
        self.log.info('parse_authors: author_node=', author_node)
        authors = [a.strip() for a in author_node]

        def ismatch(authors):
            authors = lower(' '.join(authors))
            amatch = not self.match_authors
            for a in self.match_authors:
                if lower(a) in authors:
                    amatch = True
                    break
            if not self.match_authors: amatch = True
            return amatch

        if not self.match_authors or ismatch(authors):
            return authors
        self.log.info('Rejecting authors as not a close match: ', ','.join(authors))

    def parse_published_date(self, root):
        published_node = root.xpath('//div[@class="product-shop"]//p[@class="publish-date"]')
        if published_node:
            date_match = re.search(r'Published:\s+(\d+)/(\d+)/(\d+)', published_node[0].text.strip())
            if date_match:
                year = int(date_match.groups(0)[2])
                month = int(date_match.groups(0)[0])
                day = int(date_match.groups(0)[1])
                self.log.info('parse_published_date: year=%s, month=%s, day=%s' %(year, month, day))
                from calibre.utils.date import utc_tz
                return datetime.datetime(year, month, day, tzinfo=utc_tz)

    def parse_comments(self, root):
        description_node = root.xpath('//div[contains(@class,"product-description")]')
        if description_node:
            comments = tostring(description_node[0], method='html')
            comments = sanitize_comments_html(comments)
            return comments

    def parse_rating(self, root):
        rating_node = root.xpath('//p[@class="review-overall-score-container"]/span[@class="review-overall-score"]')
        if rating_node:
            rating_text = rating_node[0].text.strip()
            self.log.info('parse_rating: rating_text=', rating_text )
            try:
                rating = float(rating_text)
            except:
                rating = None
            return rating

    def parse_cover(self, root):
        cover_node = root.xpath('//div[@class="product-img-box"]')
        if cover_node:
            cover_node = cover_node[0].xpath('//a[@onclick]')
            #self.log.info('parse_cover: cover_node=', cover_node[0].get('onclick') )
            match = re.search(r'window.open\(\'(.*?)\'', cover_node[0].get('onclick'))
            if match:
                self.log.info('parse_cover: cover="%s"' % match.groups(0)[0])
                cover_url = match.groups(0)[0]
                cover_url = None if cover_url.endswith('nopicture.gif') else cover_url
                return cover_url
