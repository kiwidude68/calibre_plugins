from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import socket, re, datetime, json
from collections import OrderedDict
from threading import Thread

from lxml.html import tostring
from six import text_type as unicode

from calibre.ebooks.metadata.book.base import Metadata
from calibre.library.comments import sanitize_comments_html
from calibre.utils.localization import canonicalize_lang
from calibre.utils.date import utcfromtimestamp
import calibre_plugins.goodreads.config as cfg


def clean_html(raw):
    from calibre.ebooks.chardet import xml_to_unicode
    from calibre.utils.cleantext import clean_ascii_chars
    return clean_ascii_chars(xml_to_unicode(raw, strip_encoding_pats=True,
                                resolve_entities=True, assume_utf8=True)[0])

def parse_html(raw):
    try:
        from html5_parser import parse
    except ImportError:
        # Old versions of calibre
        import html5lib
        return html5lib.parse(raw, treebuilder='lxml', namespaceHTMLElements=False)
    else:
        return parse(raw)


class Worker(Thread): # Get details

    '''
    Get book details from Goodreads book page in a separate thread
    '''

    def __init__(self, url, result_queue, browser, log, relevance, plugin, timeout=20):
        Thread.__init__(self)
        self.daemon = True
        self.url, self.result_queue = url, result_queue
        self.log, self.timeout = log, timeout
        self.relevance, self.plugin = relevance, plugin
        self.browser = browser.clone_browser()
        self.cover_url = self.goodreads_id = self.isbn = None

        lm = {
                'eng': ('English', 'Englisch'),
                'fra': ('French', 'Français'),
                'ita': ('Italian', 'Italiano'),
                'dut': ('Dutch',),
                'deu': ('German', 'Deutsch'),
                'spa': ('Spanish', 'Espa\xf1ol', 'Espaniol'),
                'jpn': ('Japanese', u'日本語'),
                'por': ('Portuguese', 'Português'),
                }
        self.lang_map = {}
        for code, names in lm.items():
            for name in names:
                self.lang_map[name] = code

    def run(self):
        try:
            self.get_details()
        except:
            self.log.exception('get_details failed for url: %r'%self.url)

    def get_details(self):
        try:
            self.log.info('Goodreads book url: %r'%self.url)
            raw = self.browser.open_novisit(self.url, timeout=self.timeout).read().strip()
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

        #open('e:\\goodreads.html', 'wb').write(raw)
        raw_utf8 = raw.decode('utf-8', errors='replace')

        if '<title>404 - ' in raw_utf8:
            self.log.error('URL malformed: %r'%self.url)
            return

        try:
            root = parse_html(raw_utf8)
        except:
            msg = 'Failed to parse goodreads details page: %r'%self.url
            self.log.exception(msg)
            return

        try:
            # Look at the <title> attribute for page to make sure that we were actually returned
            # a details page for a book. If the user had specified an invalid ISBN, then the results
            # page will just do a textual search.
            title_node = root.xpath('//title')
            if title_node:
                page_title = title_node[0].text.strip()
                if page_title is None or page_title.find('search results for') != -1:
                    self.log.error('Failed to see search results in page title: %r'%self.url)
                    return
        except:
            msg = 'Failed to read goodreads page title: %r'%self.url
            self.log.exception(msg)
            return

        errmsg = root.xpath('//*[@id="errorMessage"]')
        if errmsg:
            msg = 'Failed to parse goodreads details page: %r'%self.url
            msg += tostring(errmsg, method='text', encoding=unicode).strip()
            self.log.error(msg)
            return

        try:
            (book_json, series_json, contributors_list_json, work_json) = self.parse_book_json(root)
            self.parse_details(root, book_json, series_json, contributors_list_json, work_json)
        except:
            msg = 'Failed attempting to read book json meta tag from: %r'%self.url
            self.log.exception(msg)
            return
        
    def parse_book_json(self, root):
        self.log.info('Trying to parse book json for 2022 web page format')
        script_node = root.xpath('//script[@id="__NEXT_DATA__"]')
        if not script_node:
            self.log.info('Page is legacy html format as NO Json found')
            return (None, None, None, None)
        try:
            self.log.info('Json script node found, page in 2022+ html format')
            book_props_json = json.loads(script_node[0].text)
            # script has a complicated hierarchy we need to traverse to get node we want
            apolloState = book_props_json["props"]["pageProps"]["apolloState"]
            # now must iterate keys to find the one starting with Book, and array of all Contributors
            book_json = None
            series_json = None
            contributors_list_json = []
            work_json = None
            for key in apolloState.keys():
                if key.startswith("Book:"):
                    # There can be multiple book nodes. Want the most useful one.
                    if "title" in apolloState[key]:
                        book_json = apolloState[key]
                elif key.startswith("Series:") and series_json is None:
                    # There can be multiple series nodes. Want only the first one.
                    series_json = apolloState[key]
                elif key.startswith("Contributor:"):
                    # There can be multiple contributor nodes, add to list.
                    contributors_list_json.append(apolloState[key])
                elif key.startswith("Work:"):
                    # Should only be one Work node, just grab the Stats from within it.
                    work_json = apolloState[key]
             
            #self.log.info('Got book json: ', book_json)
            #self.log.info('Got contributors json: ', contributors_list_json)
            return (book_json, series_json, contributors_list_json, work_json)
        except:
            self.log.exception('Failed to parse book json: %r'%script_node[0].text)
            return (None, None, None, None)
    
    def parse_details(self, root, book_json, series_json, contributors_list_json, work_json):
        try:
            goodreads_id = self.parse_goodreads_id(self.url)
        except:
            self.log.exception('Error parsing goodreads id for url: %r'%self.url)
            goodreads_id = None

        try:
            if book_json:
                title = self.parse_title(book_json)
            else:
                title = self.parse_title_legacy(root)
        except:
            self.log.exception('Error parsing title for url: %r'%self.url)
            title = None

        try:
            if (book_json):
                authors = self.parse_authors(contributors_list_json)
            else:
                authors = self.parse_authors_legacy(root)
        except:
            self.log.exception('Error parsing authors for url: %r'%self.url)
            authors = []

        if not title or not authors or not goodreads_id:
            self.log.error('Could not parse all of title/authors/goodreads id from: %r'%self.url)
            self.log.error('Found Goodreads id: %r Title: %r Authors: %r'%(goodreads_id, title,
                authors))
            return

        mi = Metadata(title, authors)
        self.log.info('parse_details - goodreads_id: {0}, mi: {1}'.format(goodreads_id,mi))
        mi.set_identifier('goodreads', goodreads_id)
        self.goodreads_id = goodreads_id

        try:
            if book_json:
                (series, series_index) = self.parse_series(book_json, series_json)
            else:
                (series, series_index) = self.parse_series_legacy(root)
            if series is not None:
                mi.series = series
                mi.series_index = series_index
        except:
            self.log.exception('Error parsing series for url: %r'%self.url)

        try:
            if book_json:
                isbn = self.parse_isbn(book_json)
            else:
                isbn = self.parse_isbn_legacy(root)
            if isbn is not None:
                self.isbn = mi.isbn = isbn
        except:
            self.log.exception('Error parsing ISBN for url: %r'%self.url)

        try:
            get_asin = cfg.plugin_prefs[cfg.STORE_NAME][cfg.KEY_GET_ASIN]
            if get_asin is not None:
                if book_json:
                    asin = self.parse_asin(book_json)
                else:
                    asin = self.parse_asin_legacy(root)
                if asin is not None:
                    mi.set_identifier('amazon', asin)
        except:
            self.log.exception('Error parsing ASIN for url: %r'%self.url)

        try:
            if work_json:
                mi.rating = self.parse_rating(work_json)
            else:
                mi.rating = self.parse_rating_legacy(root)
            get_rating = cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_GET_RATING, False)
            if get_rating:
                mi.set_identifier('grrating', str(mi.rating))
        except:
            self.log.exception('Error parsing ratings for url: %r'%self.url)

        try:
            get_votes = cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_GET_VOTES, False)
            if get_votes:
                if work_json:
                    votes = self.parse_rating_count(work_json)
                else:
                    votes = self.parse_rating_count_legacy(root)
                mi.set_identifier('grvotes', str(votes))
        except:
            self.log.exception('Error parsing ratings for url: %r'%self.url)

        try:
            if book_json:
                comments = self.parse_comments(book_json)
            else:
                comments = self.parse_comments_legacy(root)
            self.log.info('parse_comments: ', comments)
            if comments:
                mi.comments = comments
        except:
            self.log.exception('Error parsing comments for url: %r'%self.url)

        try:
            if book_json:
                self.cover_url = self.parse_cover(book_json)
            else:
                self.cover_url = self.parse_cover_legacy(root)
        except:
            self.log.exception('Error parsing cover for url: %r'%self.url)
        mi.has_cover = bool(self.cover_url)

        try:
            if book_json:
                tags = self.parse_tags(book_json)
            else:
                tags = self.parse_tags_legacy(root)
            if tags is not None:
                mi.tags = tags
        except:
            self.log.exception('Error parsing tags for url: %r'%self.url)

        try:
            first_published = cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_FIRST_PUBLISHED, True)
            if book_json:
                mi.publisher = self.parse_publisher(book_json)
                mi.pubdate = self.parse_publish_date(book_json, work_json, first_published)
            else:
                mi.publisher, mi.pubdate = self.parse_publisher_and_date_legacy(root, first_published)
        except:
            self.log.exception('Error parsing publisher and date for url: %r'%self.url)

        try:
            if book_json:
                lang = self.parse_language(book_json)
            else:
                lang = self.parse_language_legacy(root)
            if lang is not None:
                mi.language = lang
        except:
            self.log.exception('Error parsing language for url: %r'%self.url)

        mi.source_relevance = self.relevance

        if self.goodreads_id is not None:
            if self.isbn is not None:
                self.plugin.cache_isbn_to_identifier(self.isbn, self.goodreads_id)
            if self.cover_url is not None:
                self.plugin.cache_identifier_to_cover_url(self.goodreads_id,
                        self.cover_url)
        self.plugin.clean_downloaded_metadata(mi)

        self.result_queue.put(mi)

    def parse_goodreads_id(self, url):
        return re.search('/show/(\d+)', url).groups(0)[0]

    def parse_title(self, book_json):
        if "title" not in book_json:
            return None
        title = book_json["title"]
        self.log.info("parse_title: ", title)
        return title

    def parse_title_legacy(self, root):
        title_node = root.xpath('//div[@id="metacol"]/h1[@id="bookTitle"]')
        if not title_node:
            return None
        title_text = title_node[0].text.strip()
        self.log.info("parse_title: title_text='%s'" % title_text)
        return title_text

    def parse_series(self, book_json, series_json):
        if series_json is None or "title" not in series_json:
            return (None, None)
        series_name = series_json["title"]

        if "bookSeries" not in book_json:
            return (None, None)
        # It is an array of series, but we will only use the first one
        for book_series in book_json["bookSeries"]:
            if "userPosition" not in book_series:
                return (None, None)
            try:
                series_index = float(book_series["userPosition"])
            except:
                self.log.error('Could not parse series index: ', book_series["userPosition"])
                return (None, None)

            self.log.info("parse_series: series_name='%s', series_index='%s'" % (series_name, series_index))
            return (series_name, series_index)

    def parse_series_legacy(self, root):
        # Prior 2022 page format, includes parenthesis around outside
        series_node = root.xpath('//div[@id="metacol"]/h2[@id="bookSeries"]/a')
        #self.log.info("parse_series_legacy: series_node[0].text='%s'" % series_node[0].text)
        if not series_node:
            return (None, None)
        series_text = series_node[0].text.strip()
        self.log.info("parse_series: series_text='%s'" % series_text)
        if not series_text:
            return (None, None)
        # Series can look like the following:
        # "(Series Name #1-3)"
        # "(Series Name #1)"
        # "(Series Name #05)"
        # "(Series Name 0.5)"
        #self.log.info("parse_series_legacy: series_text='%s'" % series_text)
        series_text = series_text.strip('(').strip(')')
        series = series_text
        series_index = None
        #self.log.info("parse_series_legacy: series_text after stripping parenthesis='%s'" % series_text)
        series_split = series_text.split(' ')
        if len(series_split) > 1:
            series_index_str = series_split[-1]
            series_name = series_text[:-(len(series_index_str) + 1)]
            #self.log.info("parse_series_legacy: series_name='%s', series_index_str='%s'" % (series_name, series_index_str))
            series_index_str = series_index_str.strip('#')
            if series_index_str.find('-'):
                # The series is specified as 1-3, 1-7 etc.
                # In future we may offer config options to decide what to do,
                # such as "Use start number", "Use value xxx" like 0 etc.
                # For now will just take the start number and use that
                series_index = series_index_str.partition('-')[0].strip()
            else:
                series_index = series_index_str
            try:
                series_index = float(series_index)
                series = series_name
            except ValueError:
                # We have a series index which isn't really a series index
                self.log.error("parse_series_legacy: exception converting series_index: %s" % series_index)

        self.log.info("parse_series_legacy: series_name='%s', series_index='%s'" % (series_name, series_index))
        return (series, series_index)

    def parse_authors(self, contributors_list_json):
        # 2022 version we use the json from script in page to retrieve the details
        # User either requests all authors, or only the primary authors (latter is the default)
        # If "only primary authors", only bring them in if:
        # 1. They are first author in the list, and/or
        # 2. They are a 'Goodreads Author'
        get_all_authors = cfg.plugin_prefs[cfg.STORE_NAME][cfg.KEY_GET_ALL_AUTHORS]
        authors = []
        for contributor_json in contributors_list_json:
            if (contributor_json.get("name") is None):
                continue

            author_name = contributor_json["name"]
            self.log.info('parse_authors - author: %s'%author_name)
            if get_all_authors:
                authors.append(author_name)
            else:
                if contributor_json["isGrAuthor"]:
                    authors.append(author_name)
                elif len(authors) == 0:
                    authors.append(author_name)
                else:
                    break
        return authors

    def parse_authors_legacy(self, root):
        # Build a dict of authors with their contribution if any in values
        # Prior 2022 page format
        div_authors = root.xpath('//div[@id="metacol"]/div[@id="bookAuthors"]')
        if not div_authors:
            return
        authors_html = tostring(div_authors[0], method='text', encoding=unicode).replace('\n','').strip()
        if authors_html.startswith('by'):
            authors_html = authors_html[2:]
        authors_type_map = OrderedDict()
        for a in authors_html.split(','):
            self.log.info('parse_authors_legacy - author: %s'%a)
            author = a.strip()
            if author.startswith('more…'):
                author = author[5:]
            elif author.endswith('…less'):
                author = author[:-5]
            author_parts = author.strip().split('(')
            if len(author_parts) == 1:
                authors_type_map[author_parts[0]] = ''
            else:
                authors_type_map[author_parts[0]] = author_parts[1][:-1]
        # User either requests all authors, or only the primary authors (latter is the default)
        # If only primary authors, only bring them in if:
        # 1. They have no author type specified
        # 2. They have an author type of 'Goodreads Author'
        # 3. There are no authors from 1&2 and they have an author type of 'Editor'
        get_all_authors = cfg.plugin_prefs[cfg.STORE_NAME][cfg.KEY_GET_ALL_AUTHORS]
        authors = []
        valid_contrib = None
        for a, contrib in authors_type_map.items():
            self.log.info('parse_authors_legacy - author: %s'%a)
            if get_all_authors:
                authors.append(a)
            else:
                if not contrib or contrib == 'Goodreads Author':
                    authors.append(a)
                elif len(authors) == 0:
                    authors.append(a)
                    valid_contrib = contrib
                elif contrib == valid_contrib:
                    authors.append(a)
                else:
                    break
        return authors

    def parse_rating(self, work_json):
        if "stats" not in work_json:
            return None
        stats_json = work_json["stats"]        
        if "averageRating" not in stats_json:
            return None
        rating = float(stats_json["averageRating"])
        self.log.info("parse_rating: ", rating)
        return rating

    def parse_rating_legacy(self, root):
        rating_node = root.xpath('//span[@itemprop="ratingValue"]')
        #self.log.info("parse_rating_legacy: rating_node=", rating_node)
        if rating_node and len(rating_node) > 0:
            try:
                #self.log.info("parse_rating_legacy: have rating node - rating_node[0].text=", rating_node[0].text)
                rating_text = rating_node[0].text
                rating_value = float(rating_text)
                self.log.info("parse_rating_legacy: ", rating_value)
                return rating_value
            except:
                self.log.info("parse_rating_legacy: Exception getting rating")
                import traceback
                traceback.print_stack()
                return None

    def parse_rating_count(self, work_json):
        if "stats" not in work_json:
            return None
        stats_json = work_json["stats"]        
        if "ratingsCount" not in stats_json:
            return None
        rating_count = int(stats_json["ratingsCount"])
        self.log.info("parse_rating_count: ", rating_count)
        return rating_count

    def parse_rating_count_legacy(self, root):
        rating_node = root.xpath('//meta[@itemprop="ratingCount"]')
        if rating_node:
            rating_text = tostring(rating_node[0], method='text', encoding='unicode').strip()
            rating_text = re.sub('[^0-9]', '', rating_text)
            rating_count = int(rating_text)
            self.log.info("parse_rating_count_legacy: ", rating_count)
            return rating_count

    def parse_comments(self, book_json):
        if "description" not in book_json:
            return None
        description = book_json["description"]
        if not description:
            return None
        comments = sanitize_comments_html(description)
        return comments

    def parse_comments_legacy(self, root):
        # Look for description in a second span that gets expanded when interactively displayed [@id="display:none"]
        description_node = root.xpath('//div[@id="descriptionContainer"]/div[@id="description"]/span')
        if description_node:
            desc = description_node[0] if len(description_node) == 1 else description_node[1]
            if not desc or not desc.strip():
                return None
            less_link = desc.xpath('a[@class="actionLinkLite"]')
            if less_link is not None and len(less_link):
                desc.remove(less_link[0])
            comments = tostring(desc, method='html', encoding=unicode).strip()
            while comments.find('  ') >= 0:
                comments = comments.replace('  ',' ')
            comments = sanitize_comments_html(comments)
            return comments

    def parse_cover(self, book_json):
        if "imageUrl" in book_json:
            img_url = book_json["imageUrl"]
            if img_url:
                # Unfortunately Goodreads sometimes have broken links so we need to do
                # an additional request to see if the URL actually exists
                info = self.browser.open_novisit(img_url, timeout=self.timeout).info()
                if int(info.get('Content-Length')) > 1000:
                    return img_url
                else:
                    self.log.warning('Broken image for url: %s'%img_url)

    def parse_cover_legacy(self, root):
        imgcol_node = root.xpath('//div[@class="bookCoverPrimary"]/a/img/@src')
        if imgcol_node:
            img_url = imgcol_node[0]
            # Unfortunately Goodreads sometimes have broken links so we need to do
            # an additional request to see if the URL actually exists
            info = self.browser.open_novisit(img_url, timeout=self.timeout).info()
            if int(info.get('Content-Length')) > 1000:
                return img_url
            else:
                self.log.warning('Broken image for url: %s'%img_url)

    def parse_isbn(self, book_json):
        isbn = None
        if "details" in book_json:
            details_json = book_json["details"]
            if "isbn13" in details_json:
                isbn = details_json["isbn13"]
            elif "isbn" in details_json:
                isbn = details_json["isbn"]
        self.log.info("parse_isbn: ", isbn)
        return isbn

    def parse_isbn_legacy(self, root):
        data_nodes = root.xpath('//div[@id="metacol"]/div[@id="details"]/div[@class="buttons"]/div[@id="bookDataBox"]/div')
        if data_nodes:
            for data_node in data_nodes:
                id_type = tostring(data_node, method='text', encoding=unicode).strip()
                if 'ISBN' in id_type:
                    # The first line does not contain an ISBN or an ISBN13 so check the next line
                    isbn_title_node = data_node.xpath('./div')[0]
                    id_type = tostring(isbn_title_node, method='text', encoding=unicode).strip()
                    if id_type == 'ISBN':
                        isbn10_data = tostring(data_node.xpath('./div')[1], method='text', encoding=unicode).strip()
                        isbn13_pos = isbn10_data.find('ISBN13:')
                        if isbn13_pos == -1:
                            return isbn10_data[:10]
                        else:
                            return isbn10_data[isbn13_pos+8:isbn13_pos+21]
                    elif id_type == 'ISBN13':
                        # We have just an ISBN13, without an ISBN10
                        return tostring(data_node.xpath('./div')[1], method='text', encoding=unicode).strip()
                    break

    def parse_asin(self, book_json):
        asin = None
        if "details" in book_json:
            details_json = book_json["details"]
            if "asin" in details_json:
                asin = details_json["asin"]
        self.log.info("parse_asin: ", asin)
        return asin

    def parse_asin_legacy(self, root):
        data_nodes = root.xpath('//div[@id="metacol"]/div[@id="details"]/div[@class="buttons"]/div[@id="bookDataBox"]/div')
        #self.log.info("parse_asin: data_nodes=", data_nodes)
        if data_nodes:
            for data_node in data_nodes:
                id_type = tostring(data_node, method='text', encoding=unicode).strip()
                if 'ASIN' in id_type:
                    asin_title_node = data_node.xpath('./div')[0]
                    id_type = tostring(asin_title_node, method='text', encoding=unicode).strip()
                    #self.log.info("parse_asin: id_type=", id_type)
                    if id_type == 'ASIN':
                        return tostring(data_node.xpath('./div')[1], method='text', encoding=unicode).strip()
                    break

    def parse_publisher(self, book_json):
        publisher = None
        if "publisher" in book_json["details"]:
            publisher = book_json["details"]["publisher"]
            self.log.info('parse_publisher: ', publisher)
        return publisher

    def parse_publish_date(self, book_json, work_json, first_published):
        pub_date = None
        # Publication time can be in multiple places. In book_json it will be the
        # edition publication date, whereas in work_json it seems to be the first published.
        parent_json = book_json
        if first_published:
            parent_json = work_json
        if "publicationTime" in parent_json["details"]:
            epoch_time = parent_json["details"]["publicationTime"]
            #self.log.info('Raw publication time: ', epoch_time)
            if epoch_time is not None:
                # Their time seems to have an extra 3 trailing zeroes which causes conversion grief!
                try:
                    epoch_time = int(epoch_time) // 1000
                    #self.log.info('Unix epoch publication time: ', epoch_time)
                    pub_date = utcfromtimestamp(epoch_time)
                    if first_published:
                        self.log.info('parse_publish_date: %s (First published)'%pub_date)
                    else:
                        self.log.info('parse_publish_date: %s (Edition)'%pub_date)
                except:
                    self.log.error('Failed to convert unix pub date to datetime of: ', epoch_time)
        return pub_date

    def parse_publisher_and_date_legacy(self, root, first_published):
        publisher = None
        pub_date = None
        first_pubdate_text = None
        publisher_node = root.xpath('//div[@id="metacol"]/div[@id="details"]/div[2]')
        if publisher_node:
            # Publisher is specified within the div above with variations of:
            #  Published December 2003 by Books On Tape <nobr class="greyText">(first published 1982)</nobr>
            #  Published June 30th 2010
            # Note that the date could be "2003", "December 2003" or "December 10th 2003"
            publisher_node_text = tostring(publisher_node[0], method='text', encoding=unicode)
            # See if we can find the publisher name
            pub_text_parts = publisher_node_text.partition(' by ')
            if pub_text_parts[2]:
                publisher = pub_text_parts[2].strip()
                if '(first' in publisher:
                    # The publisher name is followed by (first published xxx) so strip that off
                    publisher = publisher.rpartition('(first')[0].strip()
            self.log.info('parse_publisher_and_date_legacy: Publisher: %s'%publisher)

            # Now look for the pubdate. There should always be one at start of the string
            pubdate_text_match = re.search('Published[\n\s]*([\w\s]+)', pub_text_parts[0].strip())
            pubdate_text = None
            if pubdate_text_match is not None:
                pubdate_text = pubdate_text_match.groups(0)[0]
            # If we have a first published section of text use that for the date if user prefers it.
            if first_published and '(first' in publisher_node_text:
                # For the publication date we will use first published date
                # Note this date could be just a year, or it could be monthname year
                pubdate_text_match = re.search('.*\(first published ([\w\s]+)', publisher_node_text)
                if pubdate_text_match is not None:
                    first_pubdate_text = pubdate_text_match.groups(0)[0]
                    pubdate_text = first_pubdate_text
            if pubdate_text:
                pub_date = self._convert_date_text(pubdate_text)
                if first_pubdate_text:
                    self.log.info('parse_publisher_and_date_legacy: %s (First published)'%pub_date)
                else:
                    self.log.info('parse_publisher_and_date_legacy: %s (Edition)'%pub_date)
        return (publisher, pub_date)

    def parse_tags(self, book_json):
        # Goodreads does not have "tags", but it does have Genres (wrapper around popular shelves)
        # We will use those as tags (with a bit of massaging)
        # In 2022 version there is no hierarchy of genres, so just a flat list of tags really.
        if "bookGenres" not in book_json:
            return []
        genre_tags = list()
        for book_genre_json in book_json["bookGenres"]:
            if "genre" in book_genre_json:
                genre_name = book_genre_json["genre"]["name"]
                genre_tags.append(genre_name)
        calibre_tags = self._convert_genres_to_calibre_tags(genre_tags)
        self.log.info("parse_tags: %s"%','.join(calibre_tags))
        if len(calibre_tags) > 0:
            return calibre_tags

    def parse_tags_legacy(self, root):
        # Goodreads does not have "tags", but it does have Genres (wrapper around popular shelves)
        # We will use those as tags (with a bit of massaging)
        genres_node = root.xpath('//div[@class="stacked"]/div/div/div[contains(@class, "bigBoxContent")]/div/div[@class="left"]')
        if genres_node:
            genre_tags = list()
            for genre_node in genres_node:
                sub_genre_nodes = genre_node.xpath('a')
                genre_tags_list = [sgn.text.strip() for sgn in sub_genre_nodes]
                #self.log.info("Found genres_tags list:", genre_tags_list)
                if genre_tags_list:
                    # As of 1.7.1 we will only get the last genre and pass this through, because
                    # the new website design in 2022 does not have hierachical genres.
                    # Old website would have e.g. Fantasy, Fantasy -> Urban Fantasy, ...
                    # New website just has: Fantasy, Urban Fantasy, ...
                    genre_tags.append(genre_tags_list[-1])
            calibre_tags = self._convert_genres_to_calibre_tags(genre_tags)
            self.log.info("parse_tags_legacy: ",','.join(calibre_tags))
            if len(calibre_tags) > 0:
                return calibre_tags

    def _convert_genres_to_calibre_tags(self, genre_tags):
        map_genres = cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_MAP_GENRES, cfg.DEFAULT_STORE_VALUES[cfg.KEY_MAP_GENRES])
        if not map_genres:
            # User has disabled Goodreads tag filtering/mapping - all genres become tags
            return genre_tags
        # for each tag, add if we have a dictionary lookup
        calibre_tag_lookup = cfg.plugin_prefs[cfg.STORE_NAME][cfg.KEY_GENRE_MAPPINGS]
        calibre_tag_map = dict((k.lower(),v) for (k,v) in calibre_tag_lookup.items())
        tags_to_add = list()
        for genre_tag in genre_tags:
            tags = calibre_tag_map.get(genre_tag.lower(), None)
            if tags:
                for tag in tags:
                    if tag not in tags_to_add:
                        tags_to_add.append(tag)
        return list(tags_to_add)

    def _convert_date_text(self, date_text):
        # Note that the date text could be "2003", "December 2003" or "December 10th 2003"
        year = int(date_text[-4:])
        month = 1
        day = 1
        if len(date_text) > 4:
            text_parts = date_text[:len(date_text)-5].partition(' ')
            month_name = text_parts[0]
            # Need to convert the month name into a numeric value
            # For now I am "assuming" the Goodreads website only displays in English
            # If it doesn't will just fallback to assuming January
            month_dict = {"January":1, "February":2, "March":3, "April":4, "May":5, "June":6,
                "July":7, "August":8, "September":9, "October":10, "November":11, "December":12}
            month = month_dict.get(month_name, 1)
            if len(text_parts[2]) > 0:
                day = int(re.match('([0-9]+)', text_parts[2]).groups(0)[0])
        from calibre.utils.date import utc_tz
        return datetime.datetime(year, month, day, tzinfo=utc_tz)

    def parse_language(self, book_json):
        if "language" in book_json["details"]:
            lang_name = book_json["details"]["language"]["name"]
            ans = self.lang_map.get(lang_name, None)
            if ans:
                self.log.info('parse_language: ', ans)
                return ans
            ans = canonicalize_lang(lang_name)
            if ans:
                self.log.info('parse_language: ', ans)
                return ans
    
    def parse_language_legacy(self, root):
        lang_node = root.xpath('//div[@id="metacol"]/div[@id="details"]/div[@class="buttons"]/div[@id="bookDataBox"]/div/div[@itemprop="inLanguage"]')
        if lang_node:
            #self.log.info("parse_language_legacy: Have language node")
            raw = tostring(lang_node[0], method='text', encoding=unicode).strip()
            #self.log.info("parse_language_legacy: raw=", raw)
            ans = self.lang_map.get(raw, None)
            if ans:
                self.log.info('parse_language_legacy: ', ans)
                return ans
            ans = canonicalize_lang(raw)
            if ans:
                self.log.info('parse_language_legacy: ', ans)
                return ans
