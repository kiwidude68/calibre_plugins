from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import socket, re, json
from copy import deepcopy
from threading import Thread

from lxml.html import fromstring, tostring

from calibre.ebooks.metadata.book.base import Metadata
from calibre.library.comments import sanitize_comments_html
from calibre.utils.cleantext import clean_ascii_chars

import calibre_plugins.barnes_noble.config as cfg

class Worker(Thread): # Get details

    '''
    Get book details from Barnes & Noble book page in a separate thread
    '''

    def __init__(self, url, result_queue, browser, log, relevance, plugin, timeout=20):
        Thread.__init__(self)
        self.daemon = True
        self.url, self.result_queue = url, result_queue
        self.log, self.timeout = log, timeout
        self.relevance, self.plugin = relevance, plugin
        self.browser = browser.clone_browser()
        self.browser.set_current_header('Accept','*/*')
        self.browser.set_current_header('Accept-Encoding','gzip, deflate, br')
        self.cover_url = self.barnes_noble_id = self.isbn = None

    def run(self):
        try:
            self.get_details()
        except:
            self.log.exception('get_details failed for url: %r'%self.url)

    def get_details(self):
        try:
            self.log.info('-------------------------------------------')
            self.log.info('    Worker log information')
            self.log.info('-------------------------------------------')
            self.log.info('B&N url: %s'%self.url)
            raw = self.browser.open_novisit(self.url, timeout=self.timeout).read().strip()
        except Exception as e:
            if callable(getattr(e, 'getcode', None)) and \
                    e.getcode() == 404:
                self.log.error('URL malformed: %r'%self.url)
                return
            attr = getattr(e, 'args', [None])
            attr = attr if attr else [None]
            if isinstance(attr[0], socket.timeout):
                msg = 'Barnes & Noble timed out. Try again later.'
                self.log.error(msg)
            else:
                msg = 'Failed to make details query: %r'%self.url
                self.log.exception(msg)
            return

        #open('E:\\barnesnoble.html', 'wb').write(raw)
        raw = raw.decode('utf-8', errors='replace')

        if '<title>404 - ' in raw:
            self.log.error('URL malformed: %r'%self.url)
            return

        try:
            root = fromstring(clean_ascii_chars(raw))
        except:
            msg = 'Failed to parse Barnes & Noble details page: %r'%self.url
            self.log.exception(msg)
            return

        self.parse_details(root)

    def parse_details(self, root):
        for e in root.iter("span"):
            if "display:none" in e.get("style", "").replace(" ", ""):
               e.text = ""

        try:
            barnes_noble_id = self.parse_barnes_noble_id(self.url)
        except:
            self.log.exception('Error parsing Barnes & Noble id for url: %r'%self.url)
            barnes_noble_id = None

        try:
            (title, series, series_index) = self.parse_title_series(root)
        except:
            self.log.exception('Error parsing title and series for url: %r'%self.url)
            title = series = series_index = None

        try:
            authors = self.parse_authors(root)
        except:
            self.log.exception('Error parsing authors for url: %r'%self.url)
            authors = []

        if not title or not authors or not barnes_noble_id:
            self.log.error('Could not find title/authors/Barnes & Noble id for %r'%self.url)
            self.log.error('Barnes & Noble: %r Title: %r Authors: %r'%(barnes_noble_id, title,
                authors))
            return

        mi = Metadata(title, authors)
        if series:
            mi.series = series
            mi.series_index = series_index
        mi.set_identifier('barnesnoble', barnes_noble_id)
        self.barnes_noble_id = barnes_noble_id

        try:
            isbn = self.parse_isbn(root)
            if isbn:
                self.isbn = mi.isbn = isbn
        except:
            self.log.exception('Error parsing ISBN for url: %r'%self.url)

        try:
            mi.rating = self.parse_rating(root)
        except:
            self.log.exception('Error parsing ratings for url: %r'%self.url)

        try:
            mi.comments = self.parse_comments(root)
        except:
            self.log.exception('Error parsing comments for url: %r'%self.url)

        try:
            self.cover_url = self.parse_cover(root)
        except:
            self.log.exception('Error parsing cover for url: %r'%self.url)
        mi.has_cover = bool(self.cover_url)
        mi.cover_url = self.cover_url # This is purely so we can run a test for it!!!

        try:
            mi.publisher = self.parse_publisher(root)
        except:
            self.log.exception('Error parsing publisher for url: %r'%self.url)

        mi.source_relevance = self.relevance

        if self.barnes_noble_id:
            if self.isbn:
                self.plugin.cache_isbn_to_identifier(self.isbn, self.barnes_noble_id)

        self.plugin.clean_downloaded_metadata(mi)
        self.result_queue.put(mi)

    def parse_barnes_noble_id(self, url):
        result = re.search('barnesandnoble.com/.*/(\d+)', url)
        if result:
            return result.groups(0)[0]

    def parse_title_series(self, root):
        title_node = root.xpath('//h1[contains(concat(" ", normalize-space(@class), " "), " product__title ")]')
        if not title_node:
            self.log.info('Aborting search for title')
            return (None, None, None)
        title_text = title_node[0].text.strip()
        #self.log.info('Found title text:',title_text)
        if title_text.endswith('/'):
            title_text = title_text[:-1].strip()
        # Also strip off any NOOK Book stuff from the title
        title_text = title_text.replace('[NOOK Book]','').strip()
        match = re.search(r'\(([^\)]+) Series #(\d+)\)', title_text)
        if not match:
            match = re.search(r'\(([^\)]+), #(\d+)\)', title_text)
        if not match:
            return (title_text, None, None)
        series_name = match.groups(0)[0]
        series_index = float(match.groups(0)[1])
        title = title_text.rpartition('(')[0].strip()
        self.log.info('Title has series info as follows:',title, 'Series:',series_name, 'Idx:',series_index)
        return (title, series_name, series_index)

    def parse_authors(self, root):
        author_nodes = root.xpath('//div[contains(concat(" ", normalize-space(@class), " "), " product__contributor ") and contains(concat(" ", normalize-space(@class), " "), " desktop-only ")]//a')
        if author_nodes:
            authors = []
            for author_node in author_nodes:
                author = author_node.text.strip()
                if author and author not in authors:
                    authors.append(author)
            return authors

    def _product_json_ld(self, root):
        for script_text in root.xpath('//script[@type="application/ld+json"]/text()'):
            try:
                data = json.loads(script_text)
            except (TypeError, ValueError):
                continue
            products = data if isinstance(data, list) else [data]
            for product in products:
                if not isinstance(product, dict):
                    continue
                product_type = product.get('@type')
                if product_type == 'Product' or isinstance(product_type, list) and 'Product' in product_type:
                    return product

    def parse_rating(self, root):
        product = self._product_json_ld(root)
        if product:
            aggregate_rating = product.get('aggregateRating')
            if isinstance(aggregate_rating, dict):
                rating_value = aggregate_rating.get('ratingValue')
                if rating_value is not None:
                    try:
                        self.log.info('Rating from aggregateRating: %s', rating_value)
                        return float(rating_value)
                    except (TypeError, ValueError):
                        pass

    def parse_isbn(self, root):
        product = self._product_json_ld(root)
        if product and product.get('sku'):
            self.log.info('ISBN from sku: %s', product['sku'])
            return product['sku']

    def parse_publisher(self, root):
        product = self._product_json_ld(root)
        if product:
            brand = product.get('brand')
            if isinstance(brand, dict) and brand.get('name'):
                self.log.info('Publisher from brand: %s', brand['name'])
                return brand['name']

    def parse_comments(self, root):
        comments = ''

        # This is a fiction book that has a table of contents at bottom of page
        # Collected Stories by Saul Bellow
        # http://www.barnesandnoble.com/w/collected-stories-saul-bellow/1100154883?ean=9780143107255
        description_node = root.xpath('//div[contains(concat(" ", normalize-space(@class), " "), " product-description ")]')
        if description_node:
            description = deepcopy(description_node[0])
            for button in description.xpath('.//button'):
                button.getparent().remove(button)
            comments = tostring(description, method='html', encoding='unicode').strip()
            comments = sanitize_comments_html(comments)

        if comments:
            self.log.info('Comments from product-description: %s', comments)
            return comments

    def parse_cover(self, root):
        image_nodes = root.xpath('//div[contains(concat(" ", normalize-space(@class), " "), " product-image__main ")]//img/@src')
        if not image_nodes:
            return

        image_url = image_nodes[0].strip().split('?', 1)[0]
        if image_url:
            self.plugin.cache_identifier_to_cover_url(self.barnes_noble_id, image_url)
            return image_url
