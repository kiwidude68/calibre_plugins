from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from six import text_type as unicode
from six.moves import zip

import socket, re, datetime, six.moves.urllib.parse
from collections import OrderedDict
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
        self.cover_url = self.barnes_noble_id = self.isbn = None

    def run(self):
        try:
            self.get_details()
        except:
            self.log.exception('get_details failed for url: %r'%self.url)

    def get_details(self):
        try:
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

        try:
            mi.pubdate = self.parse_published_date(root)
        except:
            self.log.exception('Error parsing published date for url: %r'%self.url)

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

    def parse_series(self, root):
        detail_nodes = root.xpath('//div[@id="ProductDetailsTab"]/table//tr')
        if detail_nodes:
            for th,td in zip(detail_nodes[0].xpath('//th'), detail_nodes[0].xpath('//td')):
                if th.text_content().strip().startswith('Series'):
                    series_info = td.text_content().strip().replace('\n','').split(', #')
                    series_index = None
                    if len(series_info) > 1:
                        series_index = float(series_info[1])
                    series_name = series_info[0].strip()
                    return (series_name, series_index)
        return (None, None)

    def parse_title_series(self, root):
        title_node = root.xpath('//header[@id="prodSummary-header"]//h1[@itemprop="name"]')
        if not title_node:
            title_node = root.xpath('//div[@id="product-title-1"]/h1[@itemprop="name"]')
        if not title_node:
            # Pre v1.2 website format
            title_node = root.xpath('//div[@class="w-box wgt-product-heading"]/h1')
        if not title_node:
            # http://www.barnesandnoble.com/w/c-programming-language-brian-w-kernighan/1000055175
            title_node = root.xpath('//div[@class="w-box wgt-productTitle"]/h1')
        if not title_node:
            self.log('Aborting search for title')
            return (None, None, None)
        title_text = title_node[0].text.strip()
        #self.log('Found title text:',title_text)
        if title_text.endswith('/'):
            title_text = title_text[:-1].strip()
        # Also strip off any NOOK Book stuff from the title
        title_text = title_text.replace('[NOOK Book]','').strip()
        if title_text.find('(') == -1:
            #self.log('Title has no parenthesis for series so done:',title_text)
            (series_name, series_index) = self.parse_series(root)
            #self.log('Series info retrieved separately as follows:',series_name, 'Idx:', series_index)
            return (title_text, series_name, series_index)
        # Contains a Title and possibly a series. Possible values currently handled:
        # "Some title (Some text)"
        # "Some title (XXX #1)"
        # "Some title (XXX Series #1)"
        # "Some title (Some text) (XXX Series #1)"
        match = re.search(r'\(([^\)]+) Series #(\d+)\)', title_text)
        if not match:
            #self.log('Title has no Series word in title, trying without it:',title_text)
            match = re.search(r'\(([^\)]+), #(\d+)\)', title_text)
        if match:
            series_name = match.groups(0)[0]
            series_index = float(match.groups(0)[1])
            title = title_text.rpartition('(')[0].strip()
            self.log('Title has series info as follows:',title, 'Series:',series_name, 'Idx:',series_index)
            return (title, series_name, series_index)
        else:
            # Search series info from the Product Details section of website since it was not found in the title
            (series_name, series_index) = self.parse_series(root)
            self.log('Title and series info retrieved separately as follows:',title_text, 'Series:',series_name, 'Idx:', series_index)
            return (title_text, series_name, series_index)

    def parse_authors(self, root):
        default_get_all_authors = cfg.DEFAULT_STORE_VALUES[cfg.KEY_GET_ALL_AUTHORS]
        get_all_authors = cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_GET_ALL_AUTHORS, default_get_all_authors)
        if get_all_authors:
            author_nodes = root.xpath('//header[@id="prodSummary-header"]//span[contains(@class,"contributors")]/a')
            if not author_nodes:
                author_nodes = root.xpath('//div[@id="product-title-1"]/ul[contains(@class,"contributors")]/li/a')
            if not author_nodes:
                # Pre v1.2 website format
                author_nodes = root.xpath('//div[@class="w-box wgt-product-heading"]/span/a')
            if not author_nodes:
                author_nodes = root.xpath('//div[@class="w-box wgt-productTitle"]/h1/em/a')
            if author_nodes:
                authors = []
                for author_node in author_nodes:
                    author = author_node.text.strip()
                    if author:
                        authors.append(author)
                return authors
        else:
            # We need to more carefully look at the authors to only bring them in if:
            # 1. They have no author type specified
            # 2. There are no authors from 1 and they have an author type of 'Editor'
            span_authors = root.xpath('//header[@id="prodSummary-header"]//span[contains(@class,"contributors")]')
            if not span_authors:
                span_authors = root.xpath('//div[@id="product-title-1"]/ul[contains(@class,"contributors")]/li/a')
            if not span_authors:
                # Pre v1.2 website format
                span_authors = root.xpath('//div[@class="w-box wgt-product-heading"]/span')
            if not span_authors:
                span_authors = root.xpath('//div[@class="w-box wgt-productTitle"]/h1/em')
            if not span_authors:
                return
            authors_html = tostring(span_authors[0], method='text', encoding='unicode').replace('\n','').strip()
            if authors_html.startswith('by'):
                authors_html = authors_html[2:]
            authors_type_map = OrderedDict()
            for a in authors_html.split(','):
                author_parts = a.strip().split('(')
                if len(author_parts) == 1:
                    authors_type_map[author_parts[0]] = ''
                else:
                    authors_type_map[author_parts[0]] = author_parts[1][:-1]
            # At this point we have a dict of authors with their contribution if any in values
            authors = []
            valid_contrib = None
            for a, contrib in six.iteritems(authors_type_map):
                if not a:
                    continue
                if not contrib:
                    authors.append(a)
                elif len(authors) == 0:
                    authors.append(a)
                    valid_contrib = contrib
                elif contrib == valid_contrib:
                    authors.append(a)
                else:
                    break
            return authors

    def parse_rating(self, root):
        # ratings no longer on main page. Need to obtain via a json query.
        # Try the new way
        rating_node = root.xpath('//header[@id="prodSummary-header"]//div[@itemprop="aggregateRating"]/span[@itemprop="ratingValue"]/text()')
        if rating_node:
            rating_value = float(rating_node[0])
            return rating_value
        # Pre v1.2 website format
        rating_node = root.xpath('//div[@class="w-box wgt-product-ratings"]/a/div/@class')
        if rating_node:
            # B&N no longer put the actual values of the rating in the web page
            # Instead they put words like "four half" for 4.5 and "four" for "4" in the style
            # <div class="product-rating four half">
            rating_class = rating_node[0]
            match = re.search('product-rating (.+)', rating_class)
            if match:
                rating_text = match.groups(0)[0]
                rating_parts = rating_text.split(' ')
                rating_values = ['zero','one','two','three','four','five']
                rating_value = float(rating_values.index(rating_parts[0]))
                if len(rating_parts) > 1:
                    rating_value += 0.5
                return rating_value
        else:
            # Try the textbook page rating lookup
            # <span class="avg-4h section_updateRating">
            rating_node = root.xpath('//span[contains(@class,"section_updateRating")]/@class')
            if rating_node:
                rating_text = rating_node[0][4:6]
                rating_value = float(rating_text[0])
                if rating_text[1] == 'h':
                    rating_value += 0.5
                return rating_value

    def parse_isbn(self, root):
        detail_nodes = root.xpath('//div[@id="ProductDetailsTab"]/table//tr')
        if detail_nodes:
            for th,td in zip(detail_nodes[0].xpath('//th'), detail_nodes[0].xpath('//td')):
                if th.text_content().strip().startswith('ISBN'):
                    return td.text_content().strip()

        detail_nodes = root.xpath('//div[@class="product-details box"]/ul/li')
        if detail_nodes:
            for detail_node in detail_nodes:
                if detail_node[0].text_content().strip().startswith('ISBN'):
                    return detail_node[0].tail.strip()
        else:
            # Pre v1.2 website format
            isbn_nodes = root.xpath('//a[@class="isbn-a"]')
            if isbn_nodes:
                return isbn_nodes[0].text_content()
            else:
                # Legacy way (textbooks)
                isbn_nodes = root.xpath('//a[@class="isbn-a"]')
                if isbn_nodes:
                    return isbn_nodes[0].text_content()

    def parse_publisher(self, root):
        detail_nodes = root.xpath('//div[@id="ProductDetailsTab"]/table//tr')
        if detail_nodes:
            for th,td in zip(detail_nodes[0].xpath('//th'), detail_nodes[0].xpath('//td')):
                if th.text_content().strip().startswith('Publisher'):
                    return td.text_content().strip()

        detail_nodes = root.xpath('//div[@class="product-details box"]/ul/li')
        if detail_nodes:
            for detail_node in detail_nodes:
                if detail_node[0].text_content().strip().startswith('Publisher'):
                    return detail_node[0].tail.strip()

        # Pre v1.2 website format
        publisher_node = root.xpath('//div[@class="w-box details"]/ul/li[2]')
        if not publisher_node:
            publisher_node = root.xpath('//li[@class="publisher"]')

        if publisher_node:
            publisher_text = publisher_node[0].text_content()
            # Publisher: Random House Publishing Group
            return publisher_text.rpartition(':')[2].strip()

    def parse_published_date(self, root):
        detail_nodes = root.xpath('//div[@id="ProductDetailsTab"]/table//tr')
        if detail_nodes:
            for th,td in zip(detail_nodes[0].xpath('//th'), detail_nodes[0].xpath('//td')):
                if th.text_content().strip().startswith('Publication date'):
                    pub_date_text = td.text_content().strip()
                    return self._convert_date_text(pub_date_text)

        detail_nodes = root.xpath('//div[@class="product-details box"]/ul/li')
        if detail_nodes:
            for detail_node in detail_nodes:
                if detail_node[0].text_content().strip().startswith('Publication date'):
                    pub_date_text = detail_node[0].tail.strip()
                    return self._convert_date_text(pub_date_text)

        else:
            # Pre v1.2 website format
            pub_date_node = root.xpath('//div[@class="w-box details"]/ul/li[1]')
            if not pub_date_node:
                pub_date_node = root.xpath('//li[@class="pubDate"]')
            if pub_date_node:
                pub_date_text = pub_date_node[0].text_content()
                # Pub. Date: September 2010
                pub_date_text = pub_date_text.rpartition(':')[2].strip()
                return self._convert_date_text_legacy(pub_date_text)

    def _convert_date_text(self, date_text):
        # 8/30/2011
        year = int(date_text[-4:])
        month = 1
        day = 1
        if len(date_text) > 4:
            text_parts = date_text[:len(date_text)-5].partition('/') # m/d
            month = int(text_parts[0])
            if len(text_parts[2]) > 0:
                day = int(text_parts[2])
        from calibre.utils.date import utc_tz
        return datetime.datetime(year, month, day, tzinfo=utc_tz)

    def _convert_date_text_legacy(self, date_text):
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

    def parse_comments(self, root):
        comments = ''

        # This is a fiction book that has a table of contents at bottom of page
        # Collected Stories by Saul Bellow
        # http://www.barnesandnoble.com/w/collected-stories-saul-bellow/1100154883?ean=9780143107255
        description_node = root.xpath('//div[@itemprop="description"]')
        if description_node:
            comments = tostring(description_node[0], method='html', encoding='unicode').strip()
            comments = sanitize_comments_html(comments)

        if comments:
            return comments

    def parse_cover(self, root):
        # First check to make sure it is not an image NA link.
        page_image_node = root.xpath('//img[@id="pdpMainImage"]/@src')
        if not page_image_node:
            page_image_node = root.xpath('//section[contains(@class,"prim-image")]/a/img/@src')
        if not page_image_node:
            page_image_node = root.xpath('//div[contains(@class,"product-image")]/a/img/@src')
        if not page_image_node:
            page_image_node = root.xpath('//div[contains(@class,"look-inside-pdp")]/a/img/@src')
        if not page_image_node:
            page_image_node = root.xpath('//div[contains(@class,"image-block")]/img/@src')
        if page_image_node:
            page_url = page_image_node[0].strip()
            if not self._is_valid_image(page_url):
                self.log.info('Aborting parse_cover')
                return

        data_modal_url = root.xpath('//div[@id="prodImage"]//a[@data-modal-class="BN.Modal.Browse.PDP.ImageViewer"]/@data-modal-url')
        if data_modal_url:
            # Obtain the skuId from the data-modal-url
            qry = six.moves.urllib.parse.parse_qs(six.moves.urllib.parse.urlparse(data_modal_url[0]).query)
            skuid = qry['skuId'][0]
            img_svr_url = root.xpath('//div[@id="prodImage"]//a[@data-modal-class="BN.Modal.Browse.PDP.ImageViewer"]/@data-liquiddomain')
            if img_svr_url:
                #img_url = 'http://' + img_svr_url[0] + '/lf?source=url[file:images/Images/pimages/%s/%s_p0.jpg]&scale=size[%sx%s]&sink' % (skuid[-4:], skuid, width, height)
                img_url = 'http://' + img_svr_url[0] + '/lf?source=url[file:images/Images/pimages/%s/%s_p0.jpg]&sink' % (skuid[-4:], skuid)
            self.plugin.cache_identifier_to_cover_url(self.barnes_noble_id, img_url)
            return img_url

        # New style page layout - look for the expanded node
        # http://www.barnesandnoble.com/w/emperors-tomb-steve-berry/1100058321?ean=9780345505507&itm=1&usri=steve+berry
        imgcol_node = root.xpath('//img[@id="viewer-image-1"]/@data-bn-src-url')
        if not imgcol_node:
            # Try using the on page image
            imgcol_node = root.xpath('//img[@data-bntrack="ProductImageMain"]/@src')
        if imgcol_node:
            img_url = imgcol_node[0]
            if self._is_valid_image(img_url):
                self.plugin.cache_identifier_to_cover_url(self.barnes_noble_id, img_url)
                return img_url

        # Legacy mode (Pre-1.2 & textbooks)
        imgcol_node = root.xpath('//div[contains(@class,"wgt-product-image")]/a/@data-bn-options')
        if not imgcol_node:
            imgcol_node = root.xpath('//div[contains(@class,"look-inside-pdp")]/a/@href')

        if imgcol_node:
            img_options = imgcol_node[0]
            # This gets us a set of data for passing to another page:
            #   "{url:'http://search.barnesandnoble.com/booksearch/imageviewer.asp?ean=9780765342980&amp;imId=',name:'ThumbnailImage',width:'720',height:'900',scrollbars:'yes'}"
            # Or on Textbook pages, it gets us to the href directly:
            #   "http://search.barnesandnoble.com/booksearch/imageviewer.asp?ean=9780470526910&amp;imId=77192995"
            # With the website rewrite, we cannot get directly to the large image, as its details
            # are nowhere inside the page we have just parsed. Which unfortunately means we now
            # have to do another hop to the URL above and parse the results of that page to get
            # the actual large image URL. Very annoyed at the performance hit of doing this!
            match = re.search('(http://.*ean=\d+)', img_options)
            if match:
                detail_page_url = match.groups(0)[0]
                try:
                    raw = self.browser.open_novisit(detail_page_url, timeout=self.timeout).read().strip()
                    raw = raw.decode('utf-8', errors='replace')
                    img_root = fromstring(clean_ascii_chars(raw))
                    image_refs = img_root.xpath('//table[@class="ImageViewerNav"]/tr/td/a/@href')
                    if len(image_refs) > 0:
                        # Now within: <a href="imageviewer.asp?ean=9781593080778&amp;imId=71155241">
                        front_imId = image_refs[0].rpartition('=')[2].strip()
                        parent_folder = front_imId[:-4]
                        img_url = 'http://images.barnesandnoble.com/images/%s0000/%s.jpg'%(parent_folder,front_imId)
                        self.plugin.cache_identifier_to_cover_url(self.barnes_noble_id, img_url)
                        return img_url
                except:
                    pass

        # We didn't find an external image link
        # As a fallback to provide "something" use the on page image link - small but maybe better than nothing
        if page_image_node:
            if self.barnes_noble_id:
                self.plugin.cache_identifier_to_cover_url('small/'+self.barnes_noble_id, page_url)
            # Lower our relevance factor in favour of an ISBN that has a full cover if possible
            self.relevance += 5
            return page_url

    def _is_valid_image(self, img_url):
        # Make sure this image is not an NA style of image
        if img_url.endswith('ImageNA_product.gif') or img_url.endswith('NA-ProductPage2_XXL-53.JPG') or '0000000000017_' in img_url or '0000000000000_p0_v0' in img_url:
            return False
        return True
