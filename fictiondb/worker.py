from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import socket, re, datetime
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
            self.log.info('FictionDB book url: %r'%self.url)
            self.browser.set_handle_redirect(True)
            self.browser.set_debug_redirects(True)
            import sys, logging
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

#        open('e:\\fictiondb.html', 'wb').write(raw)
        raw = raw.decode('utf-8', errors='replace')

        if '<title>404 - ' in raw:
            self.log.error('URL malformed: %r'%self.url)
            return

        try:
            root = fromstring(clean_ascii_chars(raw))
        except:
            msg = 'Failed to parse fictiondb details page: %r'%self.url
            self.log.exception(msg)
            return

        try:
            # Look at the <title> attribute for page to make sure that we were actually returned
            # a details page for a book.
            title_node = root.xpath('//title')
            if title_node:
                page_title = title_node[0].text_content().strip()
                if page_title is None or page_title.find('search results') != -1:
                    self.log.error('Failed to see search results in page title: %r'%self.url)
                    return
        except:
            msg = 'Failed to read fictiondb page title: %r'%self.url
            self.log.exception(msg)
            return

        errmsg = root.xpath('//*[@id="errorMessage"]')
        if errmsg:
            msg = 'Failed to parse fictiondb details page: %r'%self.url
            msg += tostring(errmsg, method='text', encoding='unicode').strip()
            self.log.error(msg)
            return

        self.parse_details(root)

    def parse_details(self, root):
        try:
            fictiondb_id = self.parse_fictiondb_id(self.url)
        except:
            self.log.exception('Error parsing fictiondb id for url: %r'%self.url)
            fictiondb_id = None

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

        if not title or not authors or not fictiondb_id:
            self.log.error('Could not find title/authors/fictiondb id for %r'%self.url)
            self.log.error('FictionDB: %r Title: %r Authors: %r'%(fictiondb_id, title,
                authors))
            return

        try:
            (series, series_index) = self.parse_series(root)
        except:
            self.log.exception('Error parsing series for url: %r'%self.url)
            series = series_index = None

        mi = Metadata(title, authors)
        if series:
            mi.series = series
            mi.series_index = series_index
        mi.set_identifier('fictiondb', fictiondb_id)
        self.fictiondb_id = fictiondb_id

        try:
            isbn = self.parse_isbn(root)
            if isbn:
                self.isbn = mi.isbn = isbn
        except:
            self.log.exception('Error parsing ISBN for url: %r'%self.url)

        try:
            mi.comments = self.parse_comments(root)
        except:
            self.log.exception('Error parsing comments for url: %r'%self.url)

        try:
            self.cover_url = self.parse_cover(root)
        except:
            self.log.exception('Error parsing cover for url: %r'%self.url)
        mi.has_cover = bool(self.cover_url)

        try:
            tags = self.parse_tags(root)
            if tags:
                mi.tags = tags
        except:
            self.log.exception('Error parsing tags for url: %r'%self.url)

        try:
            mi.pubdate = self.parse_publish_date(root)
        except:
            self.log.exception('Error parsing publish date for url: %r'%self.url)

        try:
            mi.publisher = self.parse_publisher(root)
        except:
            self.log.exception('Error parsing publisher for url: %r'%self.url)

        mi.source_relevance = self.relevance

        if self.fictiondb_id:
            if self.isbn:
                self.plugin.cache_isbn_to_identifier(self.isbn, self.fictiondb_id)
            if self.cover_url:
                self.plugin.cache_identifier_to_cover_url(self.fictiondb_id, self.cover_url)

        self.plugin.clean_downloaded_metadata(mi)

        self.result_queue.put(mi)

    def parse_fictiondb_id(self, url):
        return re.search('/title/(.*)\.htm', url).groups(0)[0]

    def parse_title(self, root):
        title_node = ''.join(root.xpath('//h1[@class="white"]/text()'))
        if not title_node:
            self.log("parse_title: no title found")
            return None
        self.log("parse_title: title_node=", title_node)
        return title_node.replace('>','').strip()

    def parse_series(self, root):
        series_name = None
        series_index = None
        series_node = root.xpath('//li/h6[text()[contains(.,"Series")]]/../div[@class="project-terms"]/a')
        if series_node:
            self.log("series_node: series_node found -", series_node[0].text)
            series_info = series_node[0].text.rsplit('-')
            series_name = series_info[0].strip()
            if len(series_name) > 0 and len(series_info) > 1:
                try:
                    series_index = series_info[1].strip()
                    series_index = int(series_index)
                except:
                    self.log("series_node: problem getting series index - series text=", series_node[0].text)

        return series_name, series_index

    def parse_authors(self, root):
        authors_node = ''.join(root.xpath('//h1[@class="white"]/span/a/text()'))
        self.log("parse_authors: authors_node=", authors_node)
        if authors_node:
            if authors_node[0] == '~~':
                authors_node = authors_node.strip('~')
            authors = authors_node.strip('~').strip().split(';')
            return authors

    def parse_comments(self, root):
        description_node = root.xpath('//div[@id="description"]')
        if description_node:
            comments = tostring(description_node[0], method='text',encoding=unicode).strip()
            while comments.find('  ') >= 0:
                comments = comments.replace('  ',' ')
            # Since sanitize strips out line breaks, we will leave this commented out for now...
            #comments = sanitize_comments_html(comments)
            return comments

    def parse_cover(self, root):
        imgcol_node = ''.join(root.xpath('//div/img[@class="img-fluid"]/@src'))
        if imgcol_node:
            img_url = imgcol_node.strip()
            return img_url

    def parse_isbn(self, root):
        isbn_nodes = root.xpath('//li/span[@class="fdbbrown"]')
        if isbn_nodes:
            index = 0
            while index < len(isbn_nodes):
                id_type = isbn_nodes[index].text_content().strip()
                if id_type == 'ISBN:':
                    isbn10_data = isbn_nodes[index].tail.strip()
                    if index < len(isbn_nodes) - 1:
                        # Check for an ISBN13 in the next result
                        id_type = isbn_nodes[index+1].text_content().strip()
                        if id_type == 'ISBN13:':
                            return isbn_nodes[index+1].tail.strip()
                    return isbn10_data
                index += 1

    def parse_publish_date(self, root):
        pub_date_node = ''.join(root.xpath('//h6[text()="Published:"]/../div[contains(@class,"project-terms")]/text()'))
        if pub_date_node:
            # Could be variations of:
            # <div> (paperback)</div>
            # <div>2008 (paperback)</div>
            # <div>Oct-2008 (hardcover)</div>
            # <div>Oct-13-2008 (release date)</div>
            pub_date_text = pub_date_node.strip()
            self.log('parse_publish_date - text: ', pub_date_text)
            if pub_date_text[0] != '(':
                if pub_date_text.find(" ") >= 0:
                    return self._convert_date_text(pub_date_text.rpartition(' ')[0])
                else:
                    return self._convert_date_text(pub_date_text)

    def parse_publisher(self, root):
        publisher_node = root.xpath('//div[@class=" reissues"]/ul/li/text()')
        self.log('parse_publisher - publisher_node: ', publisher_node)
        if publisher_node:
            if publisher_node[0].strip() == 'First Edition': # Probably not needed unless with loop through looking for this
                return publisher_node[1].strip()
            else:
                return publisher_node[1].strip()

    def parse_tags(self, root):
        # FictionDB has multiple optional sections which can be used as tags depending on the user's preference.
        calibre_tags = list()

        if cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_GET_GENRE_AS_TAGS, True):
            self._append_tags(root, 'Genre', calibre_tags, '//div[@id="genres"]/div/div/h6[text()="Genres"]/../ul[@class=""]')
        if cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_GET_SUB_GENRE_AS_TAGS, False):
            self._append_tags(root, 'SubGenres', calibre_tags, '//div[@id="genres"]/div/div/h6[text()="Sub-Genres"]/../ul[@class=""]')
        if cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_GET_THEMES_AS_TAGS, False):
            self._append_tags(root, 'Themes', calibre_tags, '//div[@id="genres"]/div/div/h6[text()="Themes"]/../ul[@class=""]')

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
                            self.log('_append_tags - group=%s tag="%s"' % (group, tag))
                            calibre_tags.append(tag)
                else:
                    tag = tags_node.text_content().strip()
                    if tag and tag not in calibre_tags:
                        self.log('_append_tags - group=%s tag="%s"' % (group, tag))
                        calibre_tags.append(tag)
        self.log('_append_tags - group=%s all tags: "%s"' % (group, calibre_tags))

    def _convert_date_text(self, date_text):
        # Note that the date text could be "2003", "Dec-2003", "Dec-13-2003"
#         self.log('_convert_date_text - date_text: "%s"' % date_text)
        year = int(date_text[-4:]) + 1
        month = 1
        day = 1
        if len(date_text) > 4:
            month_name = date_text[:3]
            # Need to convert the month name into a numeric value
            month_dict = {"Jan":1, "Feb":2, "Mar":3, "Apr":4, "May":5, "Jun":6,
                          "Jul":7, "Aug":8, "Sep":9, "Oct":10, "Nov":11, "Dec":12}
            month = month_dict.get(month_name, 1)
        if len(date_text) > 8:
            day = int(date_text[4:6])
        from calibre.utils.date import utc_tz
        return datetime.datetime(year, month, day, tzinfo=utc_tz)
