from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import socket, re, datetime
from threading import Thread

from lxml.html import fromstring, tostring

from calibre.ebooks.metadata.book.base import Metadata
from calibre.library.comments import sanitize_comments_html
from calibre.utils.cleantext import clean_ascii_chars

import calibre_plugins.fantastic_fiction.config as cfg


class Worker(Thread): # Get details

    '''
    Get book details from Fantastic Fiction book page in a separate thread
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
            self.log.info('FantasticFiction url: %r'%self.url)
            raw = self.browser.open_novisit(self.url, timeout=self.timeout).read().strip()
        except Exception as e:
            if callable(getattr(e, 'getcode', None)) and \
                    e.getcode() == 404:
                self.log.error('URL malformed: %r'%self.url)
                return
            attr = getattr(e, 'args', [None])
            attr = attr if attr else [None]
            if isinstance(attr[0], socket.timeout):
                msg = 'Fantastic Fiction timed out. Try again later.'
                self.log.error(msg)
            else:
                msg = 'Failed to make details query: %r'%self.url
                self.log.exception(msg)
            return

        raw = raw.decode('utf-8', errors='replace')
        #open('D:\\ff.html', 'wb').write(raw)

        if '<title>404 - ' in raw:
            self.log.error('URL malformed: %r'%self.url)
            return

        try:
            root = fromstring(clean_ascii_chars(raw))
        except:
            msg = 'Failed to parse Fantastic Fiction details page: %r'%self.url
            self.log.exception(msg)
            return

        self.parse_details(root)

    def parse_details(self, root):
        try:
            ff_id = self.parse_fantastic_fiction_id(self.url)
        except:
            self.log.exception('Error parsing Fantastic Fiction id for url: %r'%self.url)
            ff_id = None

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

        if not title or not authors or not ff_id:
            self.log.error('Could not find title/authors/Fantastic Fiction id for %r'%self.url)
            self.log.error('Fantastic Fiction: %r Title: %r Authors: %r'%(ff_id, title,
                authors))
            return

        mi = Metadata(title, authors)
        mi.set_identifier('ff', ff_id)
        self.ff_id = ff_id

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

        mi.source_relevance = self.relevance

        if self.ff_id:
            if self.isbn:
                self.plugin.cache_isbn_to_identifier(self.isbn, self.ff_id)
            if self.cover_url:
                self.plugin.cache_identifier_to_cover_url(self.ff_id, self.cover_url)

        self.plugin.clean_downloaded_metadata(mi)

        self.result_queue.put(mi)

    def parse_fantastic_fiction_id(self, url):
        return re.search(self.plugin.BASE_URL + '/(.*)\.htm', url).groups(0)[0]

    def parse_title(self, root):
        title_node = root.xpath('//h1[@itemprop="name"]')
        if title_node:
            return title_node[0].text.strip()

    def parse_series(self, root):
        title = root.xpath('//head/title')
        if title:
            self.log('parse_series - have title - text="%s"' % title[0].text.strip())
            series_match = re.search('\((.*), book ([\.\d+]+)\)', title[0].text.strip())
            if series_match:
                series_name = series_match.groups(0)[0]
                series_index = series_match.groups(0)[1]
                try:
                    series_index = float(series_index)
                except ValueError:
                    self.log.error("parse_series: exception converting series_index: %s" % series_index)
                return (series_name, series_index)
        return (None, None)

    def parse_authors(self, root):
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
        book_year = ''
        pub_date = None
        oldest_edition = cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_OLDEST_EDITION, False)

        # FantasticFiction has the published year with the book title.
        year_node = root.xpath('//div[@class="bookheading"]/span[@class="year"]/a')
        if year_node:
            year = int(year_node[0].text)
            from calibre.utils.date import utc_tz
            book_year = datetime.datetime(year, 1, 1, tzinfo=utc_tz)
            pub_date = book_year
        
        if oldest_edition:
            edition_nodes = root.xpath('//div[@class="ff"]/div[@class="sectionhead"]')
            edition_nodes = root.xpath('//div[@class="ff"]/div[@class="e"]/preceding-sibling::div[@class="sectionhead"]')
            oldest_edition_date = datetime.datetime(pub_date.year + 1, 1, 1, tzinfo=utc_tz)
            have_edition_with_month = False
            if len(edition_nodes) > 0:
                for edition_node in edition_nodes:
                    edition_date = edition_node.text.split(":")[0].strip()
                    if len(edition_date.split()) > 1:
                        have_edition_with_month = True
                        edition_date = datetime.datetime.strptime(edition_date, '%B %Y').replace(tzinfo=utc_tz)
                        if edition_date < oldest_edition_date:
                            oldest_edition_date = edition_date
                    #self.log.info('parse_published_date - edition_date: "%s" ' % (edition_date))
                    #self.log.info('parse_published_date - oldest_edition_date: "%s" ' % (oldest_edition_date))

            pub_date = oldest_edition_date if have_edition_with_month else pub_date
        #self.log.info('parse_published_date - final pub_date: "%s" ' % (pub_date))
        return pub_date

    def parse_comments_and_tags(self, root):
        description_node = root.xpath('//div[@class="ff"]/div[@class="blurb"]')
        comments = None
        tags = None
        if description_node:
            # Remove the Preview link
            for preview in description_node[0].xpath("//span[@id=\'preview\']"):
                preview.getparent().remove(preview)
            # Remove the Google link
            for external_link in description_node[0].xpath("a[@target=\'_blank\']"):
                external_link.getparent().remove(external_link)

            comments = tostring(description_node[0], method='html', encoding='unicode')
            find_text = 'Genre: <a href'
            genre_index = comments.find(find_text)
            if genre_index > -1:
                genre_action = cfg.plugin_prefs[cfg.STORE_NAME][cfg.KEY_GENRE_ACTION]
                # Strip the genre out of the comments
                genre_links = comments[genre_index:-6]
                tags = re.findall(r'<a href="[^"]+">([^<]+)</a>', genre_links)
                if (re.search(r'<br>\s*$', comments[:genre_index])):
                    if genre_action == 'KEEP':
                        comments = comments[:genre_index + len('Genre: ')] + ' ,'.join(tags)
                    else:
                        # Strip ending br tag.
                        comments = comments[:genre_index].strip()
                        while comments.endswith('<br>'):
                            comments = comments[:-len('<br>')].strip()
                    comments += '</div>'
                # We found a genre - what to do about it?
                if genre_action != 'TAGS':
                    # Get the genre values as a list for tags
                    tags = None
            comments = sanitize_comments_html(comments)
            # Additional sanitization replacing header tags
            
            replace_headers = cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_REDUCE_HEADINGS, False)
            if replace_headers:
                comments = self.replace_header_tags(comments)
        return comments, tags
    
    def replace_header_tags(self, comments):
        comments = comments.replace('<h1>',  '<h4>')
        comments = comments.replace('</h1>', '</h4>')
        comments = comments.replace('<h2>',  '<h4>')
        comments = comments.replace('</h2>', '</h4>') 
        comments = comments.replace('<h3>',  '<h4>')
        comments = comments.replace('</h3>', '</h4>')
        return comments

    def parse_cover(self, root):
        cover_node = root.xpath('//div[@class="ff"]/div/img[@class="bookimage"]')
        if cover_node:
            image_url = ''
            image_name = ''
            for country in ["CA", "GB", "US"]:
                attr_name = "data-" + country.lower()
                image_name = cover_node[0].xpath('@' + attr_name)
                if image_name:
                    break
            if image_name:
                image_url = 'https://images-eu.ssl-images-amazon.com/images/I/' + image_name[0]
            return image_url

