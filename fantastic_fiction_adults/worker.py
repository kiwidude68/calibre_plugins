from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import socket, re, datetime
from threading import Thread

from lxml.html import fromstring, tostring

from calibre.ebooks.metadata.book.base import Metadata
from calibre.library.comments import sanitize_comments_html
from calibre.utils.cleantext import clean_ascii_chars

class Worker(Thread): # Get details

    '''
    Get book details from Fantastic Fiction Adults Only book page in a separate thread
    '''

    def __init__(self, url, result_queue, browser, log, relevance, plugin, timeout=20):
        Thread.__init__(self)
        self.daemon = True
        self.url, self.result_queue = url, result_queue
        self.log, self.timeout = log, timeout
        self.relevance, self.plugin = relevance, plugin
        self.browser = browser.clone_browser()
        self.cover_url = self.ff_id = self.isbn = None

    def run(self):
        try:
            self.get_details()
        except:
            self.log.exception('get_details failed for url: %r'%self.url)

    def get_details(self):
        try:
            self.log.info('FFAdultsOnly url: %r'%self.url)
            raw = self.browser.open_novisit(self.url, timeout=self.timeout).read().strip()
        except Exception as e:
            if callable(getattr(e, 'getcode', None)) and \
                    e.getcode() == 404:
                self.log.error('URL malformed: %r'%self.url)
                return
            attr = getattr(e, 'args', [None])
            attr = attr if attr else [None]
            if isinstance(attr[0], socket.timeout):
                msg = 'FFAdultsOnly timed out. Try again later.'
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
            msg = 'Failed to parse FFAdultsOnly details page: %r'%self.url
            self.log.exception(msg)
            return

        self.parse_details(root)

    def parse_details(self, root):
        try:
            ffa_id = self.parse_fantastic_fiction_id(self.url)
        except:
            self.log.exception('Error parsing FFAdultsOnly id for url: %r'%self.url)
            ffa_id = None

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

        if not title or not authors or not ffa_id:
            self.log.error('Could not find title/authors/FFAdultsOnly id for %r'%self.url)
            self.log.error('FFAdultsOnly: %r Title: %r Authors: %r'%(ffa_id, title,
                authors))
            return

        mi = Metadata(title, authors)
        mi.set_identifier('ffa', ffa_id)
        self.ffa_id = ffa_id

        try:
            (mi.series, mi.series_index) = self.parse_series(root)
        except:
            self.log.exception('Error parsing series for url: %r'%self.url)

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
            mi.comments, mi.tags = self.parse_comments_and_tags(root)
        except:
            self.log.exception('Error parsing comments for url: %r'%self.url)

        try:
            isbn, mi.publisher = self.parse_isbn_and_publisher(root)
            if isbn:
                self.isbn = mi.isbn = isbn
        except:
            self.log.exception('Error parsing ISBN/publisher for url: %r'%self.url)

        mi.source_relevance = self.relevance

        if self.ffa_id:
            if self.isbn:
                self.plugin.cache_isbn_to_identifier(self.isbn, self.ffa_id)
            if self.cover_url:
                self.plugin.cache_identifier_to_cover_url(self.ffa_id, self.cover_url)

        self.plugin.clean_downloaded_metadata(mi)

        self.result_queue.put(mi)

    def parse_fantastic_fiction_id(self, url):
        return re.search(self.plugin.BASE_URL + '/(.*)\.htm', url).groups(0)[0]

    def parse_title(self, root):
#        title_node = root.xpath('//div[@class="ff"]/table[2]/tr/td[2]/font[@size="+3"]')
        title_node = root.xpath('//h1[@itemprop="name"]')
        if title_node:
            return title_node[0].text

    def parse_series(self, root):
        title = root.xpath('//head/title')
        if title:
            series_match = re.search('\((.*), book ([\.\d+]+)\)', title[0].text.strip())
            if series_match:
                series_name = series_match.groups(0)[0].strip()
                series_index = series_match.groups(0)[1]
                try:
                    series_index = float(series_index)
                except ValueError:
                    self.log.error("parse_series: exception converting series_index: %s" % series_index)
                return (series_name, series_index)
        return (None, None)

    def parse_authors(self, root):
        #[contains(@href,"/p/")]
#        author_nodes = root.xpath('//div[@class="ff"]/table[2]/tr/td[2]/font[@size="+3"]/../a')
        author_nodes = root.xpath('//span[@itemprop="author"]/span/a')
        if author_nodes:
            authors = [author_node.text for author_node in author_nodes]
            self.log('Found authors:', authors)
            # Add some periods in after each author initial
            fixed_authors = []
            for author in authors:
                author_parts = author.split(' ')
                author_parts = [p+'.' if len(p) == 1 else p for p in author_parts]
                fixed_authors.append(' '.join(author_parts))
            return fixed_authors
        else:
            self.log('No authors')


    def parse_published_date(self, root):
        # We can only get the year from FantasticFiction
        year_node = root.xpath('//div[@class="bookheading"]/span[@class="year"]')
        if year_node:
            year = int(year_node[0].text.strip(' ()'))
            from calibre.utils.date import utc_tz
            return datetime.datetime(year, 1, 1, tzinfo=utc_tz)
#         year_node = root.xpath('//div[@id="content"]/span[@class="year"]')
#         if year_node:
#             year = year_node[0].text.strip()
#             year = re.search('(\d+)', year)
#             if year is not None:
#                 year = year.groups(0)[0]
#                 year = int(year)
#                 from calibre.utils.date import utc_tz
#                 return datetime.datetime(year, 1, 1, tzinfo=utc_tz)

    def parse_comments_and_tags(self, root):
        description_node = root.xpath('//div[@class="blurb"]')
        comments = None
        tags = None
        if description_node:
            comments = tostring(description_node[0], method='html')
            comments = sanitize_comments_html(comments)
        return comments, tags

    def parse_isbn_and_publisher(self, root):
        # We will just grab the first ISBN that we can find on the page with a publisher
        isbn = None
        publisher = None
        edition_nodes = root.xpath('//div[@id="content"]/div/table/tr/td[2]/text()')
        edition_nodes = root.xpath('//div/div[@class="e"]/div/text()')
#         self.log('parse_isbn_and_publisher: edition_nodes=', edition_nodes)
        RE_ISBN = re.compile(u'([0-9\-])+', re.UNICODE)
        for i, edition_text in enumerate(edition_nodes):
#             self.log('parse_isbn_and_publisher: edition_text=', edition_text)
            if edition_text[:5] == 'ISBN:':
                isbn_text = edition_text[6:]
                isbn_match = re.search(RE_ISBN, isbn_text)
                if isbn_match:
                    isbn = isbn_match.groups(0)[0]
                    isbn = isbn_match.group()
            if edition_text[:10] == 'Publisher:':
                publisher = edition_text[11:]
                break
        return isbn, publisher

    def parse_cover(self, root):
        cover_node = root.xpath('//div[@id="content"]/div/img[@class="bookimage"]')
#         self.log.info("parse_cover - cover_node=%s" % cover_node)
        if cover_node:
#             self.log.info("parse_cover - cover_node=%s" % tostring(cover_node[0]))
            image_url = ''
            image_name = ''
            for country in ["CA", "GB", "US"]:
                attr_name = "data-" + country.lower()
                image_name = cover_node[0].xpath('@' + attr_name)
#                 self.log.info("parse_cover - attr_name=%s, image_name=%s" % (attr_name,image_name))
                if image_name:
                    break
            if image_name:
                image_url = 'https://images-eu.ssl-images-amazon.com/images/I/' + image_name[0]
#             self.log.info("parse_cover - image_url=%s" % (image_url,))
            return image_url
