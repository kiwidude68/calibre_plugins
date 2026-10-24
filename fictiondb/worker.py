from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import socket, re, datetime, json
from threading import Thread
import six
from six import text_type as unicode

from lxml.html import fromstring, tostring

from calibre.ebooks.metadata.book.base import Metadata
from calibre.utils.cleantext import clean_ascii_chars

import calibre_plugins.fictiondb.config as cfg

class Worker(Thread): # Get details

    '''
    Get book details from FictionDB book page in a separate thread
    '''

    def __init__(self, url, result_queue, browser, log, relevance, plugin, timeout=20):
        Thread.__init__(self)
        self.daemon = True
        self.url, self.result_queue = url, result_queue
        self.log, self.timeout = log, timeout
        self.relevance, self.plugin = relevance, plugin
        self.browser = browser.clone_browser()
        self.cover_url = self.fictiondb_id = self.isbn = None

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
            self.log.info('FictionDB book url: %r'%self.url)
            self.browser.set_handle_redirect(True)
            self.browser.set_debug_redirects(True)
            import logging
            logger = logging.getLogger("mechanize.http_redirects")
            logger.addHandler(self.log)
            logger.setLevel(logging.INFO)
            raw = self.browser.open_novisit(self.url, timeout=self.timeout).read().strip()
        except Exception as e:
            if callable(getattr(e, 'getcode', None)) and \
                    e.getcode() == 404:
                self.log.error('URL malformed: %r'%self.url)
                return
            attr = getattr(e, 'args', [None])
            attr = attr if attr else [None]
            if isinstance(attr[0], socket.timeout):
                msg = 'FictionDB timed out. Try again later.'
                self.log.error(msg)
            else:
                msg = 'Failed to make details query: %r'%self.url
                self.log.exception(msg)
            return

        #open('e:\\fictiondb.html', 'wb').write(raw)
        raw_bytes = raw
        raw = raw.decode('utf-8', errors='replace')

        if '<title>404 - ' in raw:
            self.log.error('URL malformed: %r'%self.url)
            return

        if not '/book/' in self.url:
            self.log.error('URL unexpected - not a book page with /book: %r'%self.url)
            return
        
        # This is a structured book page, so we can parse the JSON-LD data instead of the HTML.
        # We can only get name, author, description, isbn, datePublished, and image from the structured data, 
        # so we will still need to parse the HTML for series, series_index, publisher, and tags.
        mi = self.parse_structured_book(raw)

        try:
            root = fromstring(clean_ascii_chars(raw))
        except Exception:
            try:
                root = fromstring(raw_bytes)
            except Exception:
                msg = 'Failed to parse fictiondb details page: %r'%self.url
                self.log.exception(msg)
                return

        self.parse_html_details(root, mi)
        self.plugin.clean_downloaded_metadata(mi)
        self.result_queue.put(mi)

    def parse_fictiondb_id(self, url):
        match = re.search(r'/(?:title|book)/([^?#]+)\.htm', url)
        return match.group(1) if match else None

    def parse_structured_book(self, raw):
        script = re.search(
            r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            raw, re.IGNORECASE | re.DOTALL)
        if not script:
            self.log.error('No structured book metadata found for %r'%self.url)
            return

        try:
            data = json.loads(script.group(1))
            self.log.info('parse_structured_book - data: %r'%data)
            if isinstance(data, list):
                data = next(item for item in data if item.get('@type') == 'Book')
            if data.get('@type') != 'Book':
                data = next(item for item in data.get('@graph', []) if item.get('@type') == 'Book')
        except Exception:
            self.log.exception('Failed to read structured book metadata for %r'%self.url)
            return

        title = data.get('name')
        self.log.info('parse_structured_book - title: %r'%title)

        author_data = data.get('author', [])        
        if isinstance(author_data, dict):
            author_data = [author_data]
        authors = [author.get('name') if isinstance(author, dict) else author
                   for author in author_data]
        authors = [author for author in authors if author]
        self.log.info('parse_structured_book - authors: %r'%authors)

        fictiondb_id = self.parse_fictiondb_id(self.url)
        self.log.info('parse_structured_book - fictiondb_id: %r'%fictiondb_id)
        if not title or not authors or not fictiondb_id:
            self.log.error('Missing title, author, or FictionDB id for %r'%self.url)
            return

        mi = Metadata(title, authors)
        mi.set_identifier('fictiondb', fictiondb_id)
        mi.comments = data.get('description')
        mi.isbn = data.get('isbn')

        published = data.get('datePublished')
        if published:
            try:
                mi.pubdate = datetime.datetime.strptime(published[:10], '%Y-%m-%d')
                self.log.info('parse_structured_book - pubdate: %r'%mi.pubdate)
            except ValueError:
                self.log.exception('Failed to parse publication date for %r'%self.url)
                mi.pubdate = None

        cover = data.get('image')
        if isinstance(cover, list):
            cover = cover[0] if cover else None
        self.log.info('parse_structured_book - cover_url: %r'%cover)

        self.fictiondb_id, self.isbn, self.cover_url = fictiondb_id, mi.isbn, cover
        mi.has_cover = bool(cover)
        mi.source_relevance = self.relevance

        if self.isbn:
            self.plugin.cache_isbn_to_identifier(self.isbn, fictiondb_id)
        if cover:
            self.plugin.cache_identifier_to_cover_url(fictiondb_id, cover)
        return mi

    def parse_html_details(self, root, mi):
        try:
            self.log.info('parsing series')
            (series, series_index) = self.parse_series(root)
        except:
            self.log.exception('Error parsing series for url: %r'%self.url)
            series = series_index = None

        if series:
            mi.series = series
            mi.series_index = series_index

        try:
            self.log.info('parsing tags')
            tags = self.parse_tags(root)
            if tags:
                mi.tags = tags
        except:
            self.log.exception('Error parsing tags for url: %r'%self.url)

        mi.source_relevance = self.relevance

    def parse_series(self, root):
        series_name = None
        series_index = None

        series_rows = root.xpath(
            '//div[contains(concat(" ", normalize-space(@class), " "), " meta-row ")]'
            '[span[contains(concat(" ", normalize-space(@class), " "), " meta-label ")'
            ' and normalize-space(.)="Series"]]'
        )
        if series_rows:
            meta_values = series_rows[0].xpath(
                './span[contains(concat(" ", normalize-space(@class), " "), " meta-value ")]'
            )
            if meta_values:
                links = meta_values[0].xpath('./a')
                if links:
                    series_name = links[0].text_content().strip()
                    self.log.info('parse_series - series_name: %r'%series_name)

                match = re.search(
                    r'\bBook\s+(\d+(?:\.\d+)?)\b',
                    meta_values[0].text_content(),
                    re.IGNORECASE
                )
                if match:
                    index_text = match.group(1)
                    self.log.info('parse_series - series_index: %r'%index_text)
                    series_index = float(index_text) if '.' in index_text else int(index_text)

        return series_name, series_index

    def parse_tags(self, root):
        # FictionDB has multiple optional sections which can be used as tags depending on the user's preference.
        calibre_tags = list()

        # First look for the Main Genre section, which is always present and contains the main genre of the book.
        self.log.info('parse_tags - getting Main Genre as tags')
        self._append_tags(root, 'Main Genre', calibre_tags, '//div[@class="book-hero-details"]/div[@class="book-hero-detail"][div[@class="book-hero-detail-label" and contains(., "Main Genre")]]/div[@class="book-hero-detail-value book-hero-detail-value--truncate"]/span[@class="genre-full"]')

        if cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_GET_GENRE_AS_TAGS, True):
            self.log.info('parse_tags - getting Genres as tags (if present)')
            self._append_tags(root, 'Genres', calibre_tags, '//section[@id="genres-themes"]/div/h3[text()="Genres"]/../div/a[@class="tag-chip"]')
        if cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_GET_SUB_GENRE_AS_TAGS, False):
            self.log.info('parse_tags - getting Subgenres as tags (if present)')
            self._append_tags(root, 'SubGenres', calibre_tags, '//section[@id="genres-themes"]/div//h3[text()="Subgenres"]/../div/a[@class="tag-chip"]')
        if cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_GET_THEMES_AS_TAGS, False):
            self.log.info('parse_tags - getting Themes as tags (if present)') 
            self._append_tags(root, 'Themes', calibre_tags, '//section[@id="genres-themes"]/div/h3[text()="Themes"]/../div/a[@class="tag-chip"]')
        if cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_GET_CHARACTERS_AS_TAGS, False):
            self.log.info('parse_tags - getting Characters & Occupations as tags (if present)') 
            self._append_tags(root, 'Characters', calibre_tags, '//section[@id="genres-themes"]/div[@class="tag-group"][h3[@class="tag-group-title" and contains(., "Characters") and contains(., "Occupations")]]/div[@class="tag-list"]/a[@class="tag-chip"]')
        if cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_GET_AGE_LEVEL_AS_TAGS, False):
            self.log.info('parse_tags - getting Age Level as tags (if present)')
            age_level_node = root.xpath('//section[@id="genres-themes"]/div/h3[text()="Age Level"]/../div/a[@class="tag-chip"]')
            if age_level_node:
                self.log.info("parse_tags: age_level_node found - %s", age_level_node[0].text.strip())
                try:
                    age_level = age_level_node[0].text.strip()
                    if len(age_level) > 0:
                        self.log.info("parse_tags: age_level found - %s", age_level)
                        calibre_tags.append(age_level)
                except:
                    self.log.info("parse_tags: problem getting age_level - age_level text= %s", age_level_node[0].text)


        if len(calibre_tags) > 0:
            return calibre_tags

    def _append_tags(self, root, group, calibre_tags, xpath_statement):
        tags_nodes = root.xpath(xpath_statement)
        if tags_nodes:
            for tags_node in tags_nodes:
                sub_tags_nodes = tags_node.xpath('./li')
                if sub_tags_nodes:
                    for sub_tags_node in sub_tags_nodes:
                        tag = sub_tags_node.text_content().strip()
                        if tag and tag not in calibre_tags:
                            self.log.info('_append_tags - group=%s tag="%s"' % (group, tag))
                            calibre_tags.append(tag)
                else:
                    tag = tags_node.text_content().strip()
                    if tag and tag not in calibre_tags:
                        self.log.info('_append_tags - group=%s tag="%s"' % (group, tag))
                        calibre_tags.append(tag)
