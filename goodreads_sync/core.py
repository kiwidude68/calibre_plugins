from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import re, json, os, traceback, collections
import xml.etree.ElementTree as et

# calibre Python 3 compatibility.
try:
    from urllib.parse import parse_qsl, urlencode, quote_plus
except ImportError:
    from urlparse import parse_qsl
    from urllib import urlencode, quote_plus
from six import text_type as unicode

try:
    from qt.core import QUrl
except ImportError:
    from PyQt5.Qt import QUrl

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.constants import DEBUG
from calibre.ebooks.metadata import fmt_sidx, authors_to_string, check_isbn
from calibre.ebooks.oeb.parse_utils import RECOVER_PARSER
from calibre.gui2 import error_dialog, open_url
from calibre.utils.config import tweaks
from calibre.utils.cleantext import clean_ascii_chars
from calibre.utils.date import parse_date, now, UNDEFINED_DATE
from calibre import get_parsed_proxy
from calibre import browser
from calibre.devices.usbms.driver import debug_print

import calibre_plugins.goodreads_sync.oauth2 as oauth
import calibre_plugins.goodreads_sync.httplib2 as httplib2
import calibre_plugins.goodreads_sync.config as cfg

def get_searchable_author(authors):
    # Take the authors displayed and convert it into a search string we can
    # pass to the Goodreads website in FN LN format for just the first author.
    # We do this because Goodreads uses FN LN format and can get grumpy when it isn't.
    # Not really sure of the best way of determining if the user is using LN, FN
    # Approach will be to check the tweak and see if a comma is in the name
    if authors == _('Unknown'):
        return ''
    author_list = authors.split('&')
    fn_ln_author = author_list[0]
    if fn_ln_author.find(',') > -1:
        # This might be because of a FN LN,Jr - check the tweak
        sort_copy_method = tweaks['author_sort_copy_method']
        if sort_copy_method == 'invert':
            # Calibre default. Hence "probably" using FN LN format.
            fn_ln_author = fn_ln_author.replace(',', ' ')
        else:
            # We will assume that we need to switch the names from LN,FN to FN LN
            parts = fn_ln_author.partition(',')
            fn_ln_author = parts[2] + ' ' + parts[0]
    return fn_ln_author.strip()

def update_calibre_isbn_if_required(calibre_book, goodreads_isbn, update_isbn=None):
    if not update_isbn:
        c = cfg.plugin_prefs[cfg.STORE_PLUGIN]
        update_isbn = c.get(cfg.KEY_UPDATE_ISBN, 'NEVER')
    if update_isbn == 'NEVER':
        return
    if update_isbn == 'ALWAYS':
        calibre_book['calibre_isbn'] = goodreads_isbn
        return
    # else only overwrite if missing
    if goodreads_isbn and not calibre_book['calibre_isbn']:
        calibre_book['calibre_isbn'] = goodreads_isbn


class HttpHelper(object):

    month_dict = {"Jan":1, "Feb":2, "Mar":3, "Apr":4,  "May":5,  "Jun":6,
                  "Jul":7, "Aug":8, "Sep":9, "Oct":10, "Nov":11, "Dec":12}

    def __init__(self, gui=None, plugin_action=None):
        c = cfg.plugin_prefs[cfg.STORE_PLUGIN]
        self.devkey_token = c[cfg.KEY_DEV_TOKEN]
        self.devkey_secret = c[cfg.KEY_DEV_SECRET]
        self.gui = gui
        self.plugin_action = plugin_action
        self._browser = None
        
        proxy = get_parsed_proxy()
        if proxy:
            proxy_type = httplib2.socks.PROXY_TYPE_HTTP_NO_TUNNEL

            self.proxy_info = httplib2.ProxyInfo(proxy_type, 
                                                 proxy['host'], 
                                                 proxy['port'], 
                                                 proxy_rdns=None, 
                                                 proxy_user=proxy['user'], 
                                                 proxy_pass=proxy['pass']
                                                 )
        else:
            self.proxy_info = None

    def create_oauth_client(self, user_name=None, oauth_token=None, oauth_secret=None):
        consumer = oauth.Consumer(key=self.devkey_token,
                                  secret=self.devkey_secret)
        # Callers can either specify the token/secret if known, or lookup
        # in the config store for that user name if known.
        if user_name:
            users = cfg.plugin_prefs[cfg.STORE_USERS]
            user_info = users[user_name]
            oauth_token = user_info[cfg.KEY_USER_TOKEN]
            oauth_secret = user_info[cfg.KEY_USER_SECRET]
        if oauth_token:
            token = oauth.Token(oauth_token, oauth_secret)
            return oauth.Client(consumer, token, proxy_info=self.proxy_info)
        else:
            return oauth.Client(consumer, proxy_info=self.proxy_info)

    def _oauth_request_get(self, oauth_client, url, success_status='200'):
        # Perform a GET request using the supplied oauth client.
        debug_print('_oauth_request_get: url=%s' % url)
        try:
            if self.gui:
                self.gui.status_bar.showMessage('Communicating with Goodreads...')

            headers = {'Accept-Encoding': 'gzip'}
            response, content = oauth_client.request(url, 'GET', headers=headers)
            if response['status'] != success_status:
                return self._handle_failure(response, content, url)
            return (response, content)
        finally:
            if self.gui:
                self.gui.status_bar.clearMessage()

    def _oauth_request_post(self, oauth_client, url, body='', success_status='200', method='POST'):
        # Perform a POST request using the supplied oauth client.
        debug_print('HttpHelper::_oauth_request_post: url=%s' % url)
        debug_print('HttpHelper::_oauth_request_post: body=%s' % body)
        try:
            if self.gui:
                self.gui.status_bar.showMessage('Communicating with Goodreads...')

            headers = {'content-type': 'application/x-www-form-urlencoded',
                       'Accept-Encoding': 'gzip'}
            response, content = oauth_client.request(url, method, body, headers)
            if response['status'] != success_status:
                return self._handle_failure(response, content, url)
            debug_print('HttpHelper::_oauth_request_post: response=%s' % response)
            debug_print('HttpHelper::_oauth_request_post: content=%s' % content)
            return (response, content)
        finally:
            if self.gui:
                self.gui.status_bar.clearMessage()

    @property
    def browser(self):
        if self._browser is None:
            self._browser = browser()
        return self._browser.clone_browser()

    def _request_get(self, url, encoding='utf-8', add_devkey=True, success_status='200', suppress_status=''):
        # Perform a standard http request (OAUTH not required)
        # Set suppress_status for an invalid response code that you do not want to prompt
        # the user about.
        debug_print('_request_get: url=%s' % url)
        try:
            if self.gui:
                self.gui.status_bar.showMessage('Communicating with Goodreads...')

            if add_devkey:
                url = url + '&key=%s' % self.devkey_token
                debug_print('_request_get: url=%s' % url)
            h = httplib2.Http(proxy_info=self.proxy_info, ca_certs=None, disable_ssl_certificate_validation=True)
            response, content = h.request(url, method='GET')
            status = response['status']
            if status != success_status and status != suppress_status:
                return self._handle_failure(response, content, url)
            if encoding:
                content = content.decode(encoding, errors='replace')
            return (response, content)
        finally:
            if self.gui:
                self.gui.status_bar.clearMessage()

    def _handle_failure(self, response, content, url):
        if DEBUG:
            debug_print('Goodreads failure calling: %s' % url)
            debug_print('Response: %s' % response)
            debug_print('Content: %s' % content)
            #traceback.print_stack()
        detail = 'URL: {0}\nResponse Code: {1}\n{2}'.format(url, response['status'], content)
        if (response['status'] == '404'):
            root = et.fromstring(content)
            errorNode = root.find('error')
            if errorNode:
                friendlyMessage = errorNode.findtext('friendly')
                if not friendlyMessage:
                    friendlyMessage = errorNode.findtext('detail')
                if (friendlyMessage):
                    error_dialog(self.gui, _('Goodreads Failure'),
                                friendlyMessage,
                                det_msg=detail, show=True)
                return (None, None)
        
        error_dialog(self.gui, _('Goodreads Failure'),
                    _('The request contacting Goodreads has failed.')+'\n'+
                    _('If it reoccurs you may have exceeded a request limit imposed by Goodreads.')+'\n'+
                    _('In which case wait an additional 5-10 minutes before retrying.'),
                    det_msg=detail, show=True)
        return (None, None)

    def view_shelf(self, user_name, shelf_name):
        users = cfg.plugin_prefs[cfg.STORE_USERS]
        user_id = users[user_name][cfg.KEY_USER_ID]
        url = '%s/review/list/%s?shelf=%s' % (cfg.URL_HTTPS, user_id, shelf_name)
        open_url(QUrl(url))

    def view_book_on_goodreads(self, goodreads_id):
        url = '%s/book/show/%s' % (cfg.URL_HTTPS, goodreads_id)
        open_url(QUrl(url))

    def get_request_token_secret(self):
        # Returns (token, secret) for authorizing a user
        REQUEST_TOKEN_URL = '%s/oauth/request_token' % cfg.URL_HTTPS
        oauth_client = self.create_oauth_client()
        response, content = self._oauth_request_get(oauth_client, REQUEST_TOKEN_URL)
        if not response:
            return None, None
        request_token = parse_qsl(content)
        request_token = {key_value[0].decode('utf-8'): key_value[1].decode('utf-8') for key_value in request_token}
        return (request_token['oauth_token'], request_token['oauth_token_secret'])

    def get_user_token_secret(self, oauth_token, oauth_secret):
        # Returns (token, secret) for a user who has authorized against the specified oauth_token/secret
        ACCESS_TOKEN_URL = '%s/oauth/access_token' % cfg.URL_HTTPS
        oauth_client = self.create_oauth_client(oauth_token=oauth_token, oauth_secret=oauth_secret)
        response, content = self._oauth_request_post(oauth_client, ACCESS_TOKEN_URL)
        if not response:
            return None, None
        access_token = parse_qsl(content)
        access_token = {key_value[0].decode('utf-8'): key_value[1].decode('utf-8') for key_value in access_token}
        return (access_token['oauth_token'], access_token['oauth_token_secret'])

    def get_goodreads_user_id(self, oauth_token, oauth_secret):
        # Returns the Goodreads user id for this token/secret, None if an error
        oauth_client = self.create_oauth_client(oauth_token=oauth_token, oauth_secret=oauth_secret)
        response, content = self._oauth_request_get(oauth_client, '%s/api/auth_user' % cfg.URL_HTTPS)
        if not response:
            return None
        root = et.fromstring(content)
        user_node = root.find('user')
        user_id = None
        if user_node is not None:
            user_id = user_node.attrib.get('id')
        return user_id

    def create_shelf(self, user_name, new_shelf_name, is_featured, is_exclusive, is_sortable):
        # Creates a shelf
        oauth_client = self.create_oauth_client(user_name)
        url = '%s/user_shelves.xml' % cfg.URL_HTTPS
        body = urlencode({
                                 'user_shelf[name]': str(new_shelf_name).lower(),
                                'user_shelf[featured]': str(is_featured).lower(),
                                'user_shelf[exclusive_flag]': str(is_exclusive).lower(),
                                 'user_shelf[sortable_flag ]': str(is_sortable).lower(),
                                 'user_shelf[recommend_for]': str(is_sortable).lower()
                                })
        response, content = self._oauth_request_post(oauth_client, url, body, success_status='201')
        if response:
            return True
        else:
            return False

    def get_shelf_list(self, user_id):
        # Returns a list of shelves for this user, None if an error
        shelves = []
        page = 0
        while True:
            # Will need to retrieve books in pages with multiple calls if many on the list
            page = page + 1
            url='%s/shelf/list.xml?user_id=%s&page=%d' % (cfg.URL_HTTPS, user_id, page)
            response, content = self._request_get(url)
            if not response:
                return None
#             debug_print("get_shelf_list: content=", content)
            # Get the latest list of shelf names, order same as they are set on Goodreads
            root = et.fromstring(content)
            shelves_node = root.find('shelves')
            if shelves_node is None:
                break
            total = int(shelves_node.attrib.get('total'))
            end = int(shelves_node.attrib.get('end'))
            shelf_nodes = root.findall('shelves/user_shelf')
            for shelf_node in shelf_nodes:
                shelf_name = shelf_node.findtext('name')
                book_count = shelf_node.findtext('book_count')
                is_exclusive = shelf_node.findtext('exclusive_flag') == 'true'
                # By default make all shelves active
                shelves.append({'active': True, 'name': shelf_name,
                                'exclusive': is_exclusive, 'book_count': book_count,
                                'sync_actions': []})
            if end >= total:
                break
        return shelves

    def add_remove_book_to_shelf(self, oauth_client, shelf_name, goodreads_id, action='add'):
        # Return Review id if book was added.
        url = '%s/shelf/add_to_shelf.xml' % cfg.URL_HTTPS
        body_info = {'name': shelf_name, 'book_id': goodreads_id}
        if DEBUG:
            debug_print('Add/remove book action: %s book: %s' % (action, body_info))
        success_status = '201'
        if action == 'remove':
            body_info['a'] = 'remove'
            success_status = '200'
        body = urlencode(body_info)
        _response, content = self._oauth_request_post(oauth_client, url, body, success_status)
        if _response:
            if action == 'add':
                root = self.get_xml_tree(content)
                review_id = root.findtext('review-id')
                if (review_id):
                    return int(review_id)
                # If we didnt get the review id then we probably got rate limited in the response.
                # Don't currently have the actual response goodreads send to detect this.
                self._handle_failure(_response, content, url)
            else:
                 # For remove from shelf actions we don't get the review id back but we need to 
                 # pretend we have one so the calling code does not abort processing books
                 return -1
        return None

    def create_review(self, oauth_client, shelf_name, goodreads_id, rating, date_read, review_text):
        # Return True if review was created, False if not. Not currently used in code
        url = '%s/review.xml' % (cfg.URL_HTTPS, )
        body_info = { 'book_id': goodreads_id }
        if rating is not None:
            body_info['review[rating]'] = int(rating)
        if date_read:
            body_info['review[read_at]'] = date_read.isoformat()[:10]
        if review_text:
            body_info['review[review_text]'] = review_text
        success_status = '201'
        body = urlencode(body_info)
        response = self._oauth_request_post(oauth_client, url, body, success_status)
        if response:
            return True
        else:
            return False

    def update_review(self, oauth_client, shelf_name, review_id, book_id, rating, date_read, review_text):
        # Return True if review was updated, False if not.
        url = '%s/review/%d.xml' % (cfg.URL_HTTPS, review_id)
        body_info = { 'shelf': shelf_name, 'book_id': book_id }
        if rating is not None:
            body_info['review[rating]'] = int(rating)
        if date_read:
            if date_read == UNDEFINED_DATE:
                body_info['review[read_at]'] = ''
            else:
                body_info['review[read_at]'] = date_read.isoformat()[:10]
        if review_text:
            body_info['review[review]'] = review_text

        success_status = '200'
        body = urlencode(body_info)
        response, _content = self._oauth_request_post(oauth_client, url, body, success_status, method='PUT')
        if response:
            return True
        else:
            return False

    def update_status(self, oauth_client, book_id, reading_progress=None, progress_is_percent=True, comment=None):
        # Return True if status was updated, False if not.
        debug_print('HttpHelper::update_status: reading_progress=%s, comment=%s' % (reading_progress, comment))
        if not reading_progress and not comment:
            return True
        url = '%s/user_status.xml' % (cfg.URL_HTTPS)
        body_info = { 'user_status[book_id]': book_id }
        if reading_progress:
            if progress_is_percent:
                body_info['user_status[percent]'] = reading_progress
            else:
                body_info['user_status[page]'] = reading_progress
        if comment and len(comment) > 0:
            body_info['user_status[body]'] = comment
        success_status = '201'
        body = urlencode(body_info)
        response, _content = self._oauth_request_post(oauth_client, url, body, success_status)
        debug_print('HttpHelper::update_status: response=%s' % (response, ))
        debug_print('HttpHelper::update_status: _content=%s' % (_content, ))
        if response:
            return True
        else:
            return False

    def get_statuses(self, oauth_client, book_id, reading_progress=None, progress_is_percent=True, comment=None):
        # Return True if status was updated, False if not.
        debug_print('HttpHelper::get_statuses: reading_progress=%s, comment=%s' % (reading_progress, comment))
        if not reading_progress and not comment:
            return True
        url = '%s/user_status/index.xml' % (cfg.URL_HTTPS)
        (response, _content) = self._request_get(url, suppress_status='404')
        debug_print('HttpHelper::get_statuses: response=%s' % (response, ))
        debug_print('HttpHelper::get_statuses: _content=%s' % (_content, ))
        if response:
            return True
        else:
            return False

    def get_goodreads_id_for_isbn(self, isbn):
        # Returns a goodreads_id for a given ISBN from Goodreads, None if an error or not found
        url = '%s/book/isbn_to_id?isbn=%s' % (cfg.URL_HTTPS, isbn)
        (response, content) = self._request_get(url, suppress_status='404')
        if not response or response['status'] == '404' or content == 'No book with that ISBN':
            return ''
        return content

    def get_goodreads_books_on_shelves(self, user_name, shelves, per_page=100):
        # Returns a dictionary of books on these Goodreads shelf by goodreads id, None if an error
        debug_print("HttpHelper::get_goodreads_books_on_shelves: user_name=%s" % (user_name, ))
        oauth_client = self.create_oauth_client(user_name)
        shelf_books = collections.OrderedDict()
        
        self.plugin_action.progressbar_format(_('Page')+': %v')
        for shelf in shelves:
            shelf_name = shelf['name']
            self.plugin_action.progressbar_label(_("Syncing from shelf: {0}").format(shelf_name))
            page = 0
            while True:
                self.plugin_action.progressbar_increment()
                # Will need to retrieve books in pages with multiple calls if many on the list
                page = page + 1
                debug_print("HttpHelper::get_goodreads_books_on_shelves: shelf='%s', page=%s" % (shelf_name, page))
                # Use this url to test reading from someone elses shelf
                url = '%s/review/list.xml?v=2&shelf=%s&page=%d&per_page=%d' % \
                            (cfg.URL_HTTPS, shelf_name, page, per_page)
                (response, content) = self._oauth_request_get(oauth_client, url)
#                 debug_print("get_goodreads_books_on_shelves: content=", content)
#                 open('E:\\test.xml','w').write(content)
                if not response:
                    return
                root = self.get_xml_tree(content)
                reviews_node = root.find('reviews')
                if reviews_node is None:
                    break
                total = int(reviews_node.attrib.get('total'))
                end = int(reviews_node.attrib.get('end'))
                review_nodes = reviews_node.findall('review')
                for review_node in review_nodes:
                    book = self._convert_review_xml_node_to_book(review_node)
                    if book and book['goodreads_id'] not in shelf_books:
                        shelf_books[book['goodreads_id']] = book
                if end >= total:
                    break
        return shelf_books

    def get_review_book(self, user_name, goodreads_id):
        # Get the user's review for a book
        users = cfg.plugin_prefs[cfg.STORE_USERS]
        user_id = users[user_name][cfg.KEY_USER_ID]
        url = '%s/review/show_by_user_and_book.xml?user_id=%s&book_id=%s' % \
            (cfg.URL_HTTPS, user_id, goodreads_id)
        (response, content) = self._request_get(url, suppress_status='404')
        debug_print('get_review_book: content=%s' %(content,))
        if not response:
            return
        if response['status'] == '404':
            if DEBUG:
                debug_print('User \'%s\' does not have a review for book: %s' %(user_name, goodreads_id))
            return
        #open('D:\\test_review.xml','w').write(content)
        root = self.get_xml_tree(content)
        review_node = root.find('review')
#         debug_print('get_review_book: show content=%s' %(content,))
        if review_node is None:
            return None
        return self._convert_review_xml_node_to_book(review_node)

    def search_for_goodreads_books(self, title='', authors=''):
        # Returns a list of books matching this search criteria
        if title == _('Unknown'):
            title = ''
        if authors == _('Unknown'):
            authors = ''
        if not title and not authors:
            return []
        pat = re.compile(r'''[-,:;+!@#$%^&*(){}`~"\[\]/]''')
        title = pat.sub('', title)
        query = title.replace('.', ' ') + ' ' + get_searchable_author(authors)
        scope = ''
        if authors and not title:
            scope = 'search=author&'
            query = authors
        elif title and not authors:
            scope = 'search=title&'
            query = title
        query = quote_plus(query.strip().encode('utf-8')).replace('++', '+')
        search_books = []
        url = '%s/search/search.xml?%spage=1&q=%s' % (cfg.URL_HTTPS, scope, query)
        (response, content) = self._request_get(url)
        if not response:
            return
        root = self.get_xml_tree(content)
        work_nodes = root.findall('search/results/work')
        for work_node in work_nodes:
            book = {}
            book['goodreads_work_id'] = work_node.findtext('id')
            book['goodreads_id'] = work_node.findtext('best_book/id')
            book['goodreads_author'] = work_node.findtext('best_book/author/name')
            if book['goodreads_author'] == 'NOT A BOOK':
                # Goodreads use this author to categorise ISBNs in their databases that
                # are not actually books
                continue
            (title, series) = self._convert_goodreads_title_with_series(work_node.findtext('best_book/title').strip())
            book['goodreads_title'] = title
            book['goodreads_series'] = series
            search_books.append(book)
        return search_books

    def get_goodreads_book_for_id(self, goodreads_id):
        # Returns a dictionary of information about a book, obtained from the "get reviews" API
        # This seems to be the only way to get information about a book, without web scraping
        # when you can't guarantee that the book is on one of your shelves.
        # Returns None if an error
        # This particular URL has the option of a JSON file result (yay!)
        url = '%s/book/show?format=json&id=%s&page=1' % (cfg.URL_HTTPS, goodreads_id)
        (response, content) = self._request_get(url)
        if not response:
            return
        content = clean_ascii_chars(content)
        content_json = json.loads(content)
        return self.convert_json_to_book(content_json)

    def get_goodreads_book_with_work_id(self, goodreads_id):
        # Returns Goodreads book with extra information related to the work id, which is used
        # so we can then use to query for other editions. Not available in the json query above, grrr.
        url = '%s/book/show?format=xml&id=%s&page=1' % (cfg.URL_HTTPS, goodreads_id)
        (response, content) = self._request_get(url)
        if not response:
            return
        content = clean_ascii_chars(content)
        root = self.get_xml_tree(content)
        return self._convert_review_xml_node_to_book(root, include_work=True)

    def convert_json_to_book(self, content_json):
        book = {}
        book['goodreads_id'] = str(content_json['id'])
        book['goodreads_isbn'] = content_json.get('isbn13', '')
        if not book['goodreads_isbn']:
            book['goodreads_isbn'] = content_json.get('isbn', '')
        authors = content_json['authors']
        authors_text = ''
        for i, author in enumerate(authors):
            if i == 0:
                authors_text = author['name']
            else:
                authors_text= '%s & %s' % (authors_text, author['name'])
        book['goodreads_author'] = authors_text
        (title, series) = self._convert_goodreads_title_with_series(content_json['title'].strip())
        book['goodreads_title'] = title
        book['goodreads_series'] = series
        # Stuff that is not available at JSON level (only at review level)
        book['goodreads_shelves'] = ''
        book['goodreads_shelves_list'] = []
        book['goodreads_review_id'] = ''
        book['goodreads_rating'] = 0
        book['goodreads_started_at'] = UNDEFINED_DATE
        book['goodreads_read_at'] = UNDEFINED_DATE
        book['goodreads_date_added'] = UNDEFINED_DATE
        book['goodreads_date_updated'] = UNDEFINED_DATE
        book['goodreads_review_text'] = ''
        return book

    def _convert_review_xml_node_to_book(self, review_node, include_work=False):
#         debug_print("HttpHelper::_convert_review_xml_node_to_book - review_node=", tostring(review_node))
        book_node = review_node.find('book')
        book = {}
        goodreads_id = book_node.findtext('id')
        book['goodreads_id'] = goodreads_id
        isbn = book_node.findtext('isbn13')
        book['goodreads_isbn'] = isbn
        (title, series) = self._convert_goodreads_title_with_series(book_node.findtext('title').strip())
        book['goodreads_title'] = title
        book['goodreads_series'] = series
        if book_node.find('authors') is None:
            # We have an error situation where the returned xml is being corrupted due to the
            # Goodreads bug for encodings. We will skip this book
            if DEBUG:
                debug_print('Goodreads shelf error due to corruption bug. Skipping book: %s' % book)
            return None
        author_nodes = book_node.findall('authors/author')
        authors = [author_node.findtext('name').strip() for author_node in author_nodes]
        book['goodreads_author'] = '& '.join(authors)
        shelve_nodes = review_node.find('shelves')
        # May not be present when reusing this code from a different api call.
        if shelve_nodes is not None and len(shelve_nodes):
            shelves = [shelve_node.attrib.get('name').strip() for shelve_node in shelve_nodes]
            book['goodreads_shelves'] = ', '.join(shelves)
            book['goodreads_shelves_list'] = shelves
            book['goodreads_review_id'] = review_node.findtext('id')
            book['goodreads_rating'] = int(review_node.findtext('rating'))
            # Get the various date fields in case the user has sync actions for them
            book['goodreads_started_at'] = self._parse_goodreads_date(review_node.findtext('started_at'))
            book['goodreads_read_at'] = self._parse_goodreads_date(review_node.findtext('read_at'))
            book['goodreads_date_added'] = self._parse_goodreads_date(review_node.findtext('date_added'))
            book['goodreads_date_updated'] = self._parse_goodreads_date(review_node.findtext('date_updated'))
            #review_text = review_node.findtext('body')
            book['goodreads_review_text'] = review_node.findtext('body').strip()
            if len(book['goodreads_review_text']) > 0:
                debug_print("_convert_review_xml_node_to_book: length of review_text=", len(book['goodreads_review_text']))
#                 debug_print("_convert_review_xml_node_to_book: review_text=", book['goodreads_review_text'])
        else:
            book['goodreads_shelves'] = ''
            book['goodreads_shelves_list'] = []
            book['goodreads_review_id'] = ''
            book['goodreads_rating'] = 0
            book['goodreads_started_at'] = ''
            book['goodreads_read_at'] = ''
            book['goodreads_date_added'] = ''
            book['goodreads_date_updated'] = ''
            book['goodreads_review_text'] = ''
        if include_work:
            work_node = book_node.find('work')
            if work_node is not None:
                book['goodreads_work_id'] = work_node.findtext('id')
        return book

    def _parse_goodreads_date(self, date_text):
        if date_text == '':
            return UNDEFINED_DATE
        return parse_date(date_text, assume_utc=True, as_utc=False)

    def _convert_goodreads_title_with_series(self, text):
        # This function attempts to convert a myriad of Goodreads title
        # combinations to strip out the series information as it is not
        # available separately in the API
        if text.find('(') == -1:
            return (text, '')
        text_split = text.rpartition('(')
        title = text_split[0]
        series_info = text_split[2]
        series_info = series_info.rpartition(')')
        series_info = series_info[0]
        hash_pos = series_info.find('#')
        if hash_pos <= 0:
            # Cannot find the series # in expression or at start like (#1-7)
            # so consider whole thing just as title
            title = text
            series_info = ''
        else:
            # Check to make sure we have got all of the series information
            while series_info.count(')') != series_info.count('('):
                title_split = title.rpartition('(')
                title = title_split[0].strip()
                series_info = title_split[2] + '(' + series_info
        if series_info:
            series_partition = series_info.rpartition('#')
            series_name = series_partition[0].strip().replace(',', '')
            series_index = series_partition[2].strip()
            if series_index.find('-'):
                # The series is specified as 1-3, 1-7 etc.
                # In future we may offer config options to decide what to do,
                # such as "Use start number", "Use value xxx" like 0 etc.
                # For now will just take the start number and use that
                series_index = series_index.partition('-')[0].strip()
            series_info = '%s [%s]' % (series_name, series_index)
        return (title.strip(), series_info)

    def get_xml_tree(self, content):
        content = clean_ascii_chars(content)
        try:
            root = et.fromstring(content)
        except:
            traceback.format_exc()
            root = et.fromstring(content, parser=RECOVER_PARSER)
        if root is None:
            import tempfile
            cpath = os.path.join(tempfile.tempdir, 'xml_fail.xml')
            f = open(cpath, 'w')
            f.write(content)
            f.close()
            raise ValueError('The shelf contains a corrupting response from Goodreads. ' +
                             'This can occur for certain books or may be a temporary issue with the website. ' +
                             'See the Help file for this plugin for more details or try again later.<br><br>' +
                             'The failed xml can be found at:<br>' + cpath)
        return root

    def get_edition_books_for_work_id(self, work_id):
        # This is a bit of filth - currently do not have access to the API call which will do
        # the equivalent so must scrape from the website instead.
        from calibre import browser
        import socket
        from lxml.html import fromstring, tostring

        url = 'https://www.goodreads.com/work/editions/%s'%work_id
        try:
            br = browser()
            raw = br.open_novisit(url, timeout=20).read().strip()
        except Exception as e:
            if isinstance(getattr(e, 'getcode', None), collections.Callable):
                error_code = e.getcode()
            else:
                error_code = None
            attr = getattr(e, 'args', [None])
            attr = attr if attr else [None]
            if error_code == 404:
                msg = ('URL malformed: %r'%url)
            elif isinstance(attr[0], socket.timeout):
                msg = 'Request timed out. Try again later.'
            else:
                msg = 'Failed to query goodreads: %r'%url
            if error_code:
                msg = msg + '\nError Code: %s' % error_code
            if getattr(e, 'reason', None):
                msg = msg + '\nError Reason: %s' % e.reason
            error_dialog(self.gui, 'Goodreads Failure',
                         'The request contacting Goodreads has failed. Please try again.',
                         det_msg=msg, show=True)
            return None
        raw = raw.decode('utf-8', errors='replace')
        root = fromstring(clean_ascii_chars(raw))

        goodreads_edition_books = []

        edition_nodes = root.xpath('//div[@class="leftContainer workEditions"]/div[@class="elementList clearFix"]')
        for edition_node in edition_nodes:
            edition_data_node = edition_node.xpath('div[@class="editionData"]')[0]

            goodreads_edition_book = {}
            goodreads_edition_book['goodreads_edition'] = ''
            goodreads_edition_book['goodreads_isbn'] = ''

            # To get the edition it might be preceded by the Published
            for idx, data_row_node in enumerate(edition_data_node.xpath('div[@class="dataRow"]')):
                if idx == 0:
                    continue # Will be the title
                text = tostring(data_row_node, method='text', encoding='unicode').strip()
                if text.startswith('Published'):
                    continue
                goodreads_edition_book['goodreads_edition'] = text
                break

            book_url = ''.join(edition_data_node.xpath('div[@class="dataRow"]/a/@href'))
            goodreads_edition_book['goodreads_id'] = re.search(r'/book/show/(\d+)', book_url).groups(0)[0]
            goodreads_edition_book['goodreads_title'] = ''.join(edition_data_node.xpath('div[@class="dataRow"]/a[@class="bookTitle"]/text()'))
            cover_url = ''.join(edition_node.xpath('div[@class="leftAlignedImage"]/a/img/@src'))
            if 'nocover' in cover_url:
                goodreads_edition_book['goodreads_cover'] = 'No'
            else:
                goodreads_edition_book['goodreads_cover'] = 'Yes'
            goodreads_edition_book['goodreads_isbn'] = ''
            isbn_node = edition_data_node.xpath('div[@class="moreDetails hideDetails"]/div[@class="dataRow"][2]/div[@class="dataValue"]/span[@class="greyText"]/text()')
            if len(isbn_node) > 0:
                isbn = None
                match_isbn = re.search(r': (\d+)', isbn_node[0])
                if not match_isbn:
                    match_isbn = re.search(r'(\d+)', isbn_node[0])
                if match_isbn:
                    isbn = match_isbn.groups(0)[0]
                    if check_isbn(isbn):
                        goodreads_edition_book['goodreads_isbn'] = isbn
            goodreads_edition_books.append(goodreads_edition_book)

        return goodreads_edition_books


class IdCaches(object):

    def __init__(self, gui):
        self.gui = gui
        self.invalidate_caches()

    def invalidate_caches(self):
        self._goodreads_to_calibre_id_cache = None
        self._calibre_to_goodreads_id_cache = None

    def goodreads_to_calibre_ids(self):
        # Construct on demand a cache mapping goodreads ids to Calibre ids.
        if self._goodreads_to_calibre_id_cache is None:
            self.build_caches()
        return self._goodreads_to_calibre_id_cache

    def calibre_to_goodreads_ids(self):
        # Construct on demand a cache mapping Calibre ids to Goodreads ids.
        # This is purely a performance optimisation.
        if self._calibre_to_goodreads_id_cache is None:
            self.build_caches()
        return self._calibre_to_goodreads_id_cache

    def get_calibre_ids_linked(self, goodreads_id):
        # Offers a safe way of retrieving calibre ids linked to this goodreads id
        # by checking to see if each calibre id has been deleted first.
        existing_calibre_ids = self.goodreads_to_calibre_ids().get(goodreads_id, [])
        valid_ids = []
        db = self.gui.library_view.model().db
        for calibre_id in existing_calibre_ids:
            if db.data.has_id(calibre_id):
                valid_ids.append(calibre_id)
            else:
                self.remove_calibre_id_from_cache(calibre_id)
        return valid_ids

    def build_caches(self):
        gr_cache = {}
        cb_cache = {}
        db = self.gui.library_view.model().db
        calibre_ids = db.data.search_getting_ids('identifiers:goodreads:True', search_restriction='')
        for calibre_id in calibre_ids:
            goodreads_id = db.get_identifiers(calibre_id, index_is_id=True).get('goodreads', '')
            if goodreads_id:
                # We will allow multiple Calibre ids per Goodreads id.
                calibre_ids_mapped = gr_cache.get(goodreads_id, [])
                calibre_ids_mapped.append(calibre_id)
                gr_cache[goodreads_id] = calibre_ids_mapped
                cb_cache[calibre_id] = goodreads_id
        self._goodreads_to_calibre_id_cache = gr_cache
        self._calibre_to_goodreads_id_cache = cb_cache

    def remove_calibre_id_from_cache(self, deleted_id):
        if not self._calibre_to_goodreads_id_cache:
            return
        if deleted_id in self._calibre_to_goodreads_id_cache:
            goodreads_id = self._calibre_to_goodreads_id_cache[deleted_id]
            del self._calibre_to_goodreads_id_cache[deleted_id]
            calibre_ids_mapped = self._goodreads_to_calibre_id_cache[goodreads_id]
            calibre_ids_mapped.remove(deleted_id)
            if len(calibre_ids_mapped) == 0:
                del self._goodreads_to_calibre_id_cache[goodreads_id]
            else:
                self._goodreads_to_calibre_id_cache[goodreads_id] = calibre_ids_mapped


class CalibreSearcher(object):
    '''
    Encapsulates the search logic and algorithms used to find books in Calibre
    using fuzzy matching.
    '''
    fuzzy_title_patterns = [(re.compile(pat, re.IGNORECASE), repl) for pat, repl in
            [
                (r'[\[\](){}<>\'";,:#]', ''),
                (tweaks.get('title_sort_articles', r'^(a|the|an)\s+'), ''),
                (r'[-._]', ' '),
                (r'\s+', ' ')
            ]
    ]
    fuzzy_author_patterns = [(re.compile(pat, re.IGNORECASE), repl) for pat, repl in
            [
                (r'[()\'";,|]', ''),
                (r'\.', '. '),
                (r'\s+', ' ')
            ]
    ]

    def __init__(self, id_caches):
        self.id_caches = id_caches
        self.fuzzy_book_map = None

    def search_calibre_fuzzy_map(self, title, author):
        fuzzy_map_cache = self.get_fuzzy_search_map_cache()
        fuzzy_match_title = self.fuzzyit(title, self.fuzzy_title_patterns)
        fuzzy_match_author = self.fuzzyit(author, self.fuzzy_author_patterns)
        try:
            if fuzzy_match_title not in fuzzy_map_cache:
                return []
            authors_for_title = fuzzy_map_cache[fuzzy_match_title]
            if fuzzy_match_author not in authors_for_title:
                return []
            calibre_book_ids = authors_for_title[fuzzy_match_author]
            search_books = []
            for calibre_id in calibre_book_ids:
                search_book = {}
                if not self.get_calibre_data_for_book(search_book, calibre_id):
                    continue
                if len(fuzzy_match_title) == 0:
                    search_books.append(search_book)
                else:
                    found_fuzzy_title = self.fuzzyit(search_book['calibre_title'], self.fuzzy_title_patterns)
                    if found_fuzzy_title == fuzzy_match_title:
                        search_books.append(search_book)
            return search_books
        except:
            traceback.print_exc()
            return []

    def search_calibre_using_query(self, title, author):
        def build_query_title(title):
            words = ['title:' + w for w in title.strip().split()]
            query_title = ' and '.join(words)
            return query_title.strip()

        def build_query_author(author):
            words = ['author:' + w for w in author.split()]
            query_author = ' and '.join(words)
            return query_author.strip()

        query_title = build_query_title(title)
        query_author = build_query_author(author)
        if query_title and query_author:
            query = '%s and %s' % (query_title, query_author)
        elif query_title:
            query = query_title
        else:
            query = query_author
        try:
            db = self.id_caches.gui.library_view.model().db
            calibre_book_ids = db.data.search_getting_ids(query, search_restriction='')
            search_books = []
            for calibre_id in calibre_book_ids:
                search_book = {}
                if self.get_calibre_data_for_book(search_book, calibre_id):
                    search_books.append(search_book)
            return search_books
        except:
            traceback.print_exc()
            return []

    def get_calibre_data_for_book(self, book, calibre_id):
        db = self.id_caches.gui.library_view.model().db
        if not db.data.has_id(calibre_id):
            # We have a problem. This id is not in the database.
            self.id_caches.remove_calibre_id_from_cache(calibre_id)
            book['calibre_id'] = ''
            book['calibre_isbn'] = ''
            book['calibre_title'] = ''
            book['calibre_title_sort'] = ''
            book['calibre_author'] = ''
            book['calibre_author_sort'] = ''
            book['calibre_series'] = ''
            book['calibre_rating'] = 0.
            book['calibre_date_read'] = UNDEFINED_DATE
            book['calibre_review_text'] = ''
            book['calibre_reading_progress'] = -1
            return False

        book['calibre_id'] = calibre_id
        mi = db.get_metadata(calibre_id, index_is_id=True)
        book['calibre_title'] = '' if mi.title is None else mi.title
        book['calibre_title_sort'] = book['calibre_title'] if mi.title_sort is None else mi.title_sort
        book['calibre_author'] = authors_to_string(mi.authors)
        book['calibre_author_sort'] = '' if mi.author_sort is None else mi.author_sort
        book['calibre_isbn'] = '' if mi.isbn is None else mi.isbn
        book['calibre_series'] = ''
        if mi.series:
            seridx = fmt_sidx(mi.series_index)
            book['calibre_series'] = '%s [%s]' % (mi.series, seridx)
        self.get_uploadable_columns(mi, book)

        if not 'goodreads_id' in book:
            goodreads_id = self.id_caches.calibre_to_goodreads_ids().get(calibre_id, '')
            book['goodreads_id'] = goodreads_id
        return True

    def get_uploadable_columns(self, mi, book):
        rating_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_RATING_COLUMN, '')
        book['calibre_rating'] = 0
        if rating_column:
            rating = mi.get(rating_column)
            if rating:
                book['calibre_rating'] = int(rating)

        date_read_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_DATE_READ_COLUMN, '')
        book['calibre_date_read'] = UNDEFINED_DATE
        if date_read_column:
            date_read = mi.get(date_read_column)
            if date_read:
                book['calibre_date_read'] = date_read

        review_text_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_REVIEW_TEXT_COLUMN, '')
        book['calibre_review_text'] = ''
        if review_text_column:
            review_text = mi.get(review_text_column)
            if review_text:
                book['calibre_review_text'] = review_text

        reading_progress_column = cfg.plugin_prefs[cfg.STORE_PLUGIN].get(cfg.KEY_READING_PROGRESS_COLUMN, '')
        book['calibre_reading_progress'] = -1
        if reading_progress_column:
            reading_progress = mi.get(reading_progress_column)
            if reading_progress:
                book['calibre_reading_progress'] = reading_progress

    def get_fuzzy_search_map_cache(self):
        if not self.fuzzy_book_map:
            self.fuzzy_book_map = self.build_cache()
        return self.fuzzy_book_map

    def fuzzyit(self, text, patterns):
        text = text.strip().lower()
        for pat, repl in patterns:
            text = pat.sub(repl, text)
        return text

    def build_cache(self):
        def switch_author_names(author):
            names = author.partition('|')
            if names[2]:
                return names[2]+', '+names[0]
            return author

        db = self.id_caches.gui.library_view.model().db
        self.fuzzy_book_map = collections.defaultdict(dict)
        for bid in db.data.iterallids():
            # Create an entry for the fuzzy of this title
            title = db.title(bid, index_is_id=True)
            fuzzy_title = self.fuzzyit(title, self.fuzzy_title_patterns)
            title_dict = {}
            if fuzzy_title not in self.fuzzy_book_map:
                self.fuzzy_book_map[fuzzy_title] = title_dict
            else:
                title_dict = self.fuzzy_book_map[fuzzy_title]
            # Create an entry within title for fuzzy of the author if it has one
            authors = db.authors(bid, index_is_id=True)
            if authors:
                authors = authors.split(',')
            if authors is None or len(authors) == 0:
                if '' in title_dict:
                    title_dict[''].add(bid)
                else:
                    title_dict[''] = set([bid])
                continue
            author = authors[0].replace('|', ', ')
            fuzzy_author_fn_ln = self.fuzzyit(author, self.fuzzy_author_patterns)
            fuzzy_author_fn_ln_set = set()
            if fuzzy_author_fn_ln not in title_dict:
                title_dict[fuzzy_author_fn_ln] = fuzzy_author_fn_ln_set
            else:
                fuzzy_author_fn_ln_set = title_dict[fuzzy_author_fn_ln]
            fuzzy_author_fn_ln_set.add(bid)
            # Also add a mapping swapping FN LN to LN FN as we don't know how
            # the user stores them in Calibre. Single name authors excluded.
            reverse_author = switch_author_names(authors[0])
            if reverse_author != authors[0]:
                fuzzy_author_ln_fn = self.fuzzyit(reverse_author, self.fuzzy_author_patterns)
                fuzzy_author_ln_fn_set = set()
                if fuzzy_author_ln_fn not in title_dict:
                    title_dict[fuzzy_author_ln_fn] = fuzzy_author_ln_fn_set
                else:
                    fuzzy_author_ln_fn_set = title_dict[fuzzy_author_ln_fn]
                fuzzy_author_ln_fn_set.add(bid)
        return self.fuzzy_book_map


class CalibreDbHelper(object):

    def apply_actions_to_calibre(self, gui, goodreads_books, actions):
        self.gui = gui
        self.db = gui.current_db
        self.custom_columns = self.db.field_metadata.custom_field_metadata()
        debug_print("CalibreDbHelper::apply_actions_to_calibre - actions:", actions)
        for sync_action in actions:
            if sync_action['column'] == 'tags':
                self._apply_tag_changes_to_books(goodreads_books, sync_action['action'], sync_action['value'])
            elif sync_action['column'] == 'rating':
                self._apply_rating_changes_to_books(goodreads_books, sync_action['action'], sync_action['value'])
            elif sync_action['column'] == 'comments':
                self._apply_comment_changes_to_books(goodreads_books, sync_action['action'], sync_action['value'])
            else:
                # Applying values to a custom column
                self._apply_custom_column_changes_to_books(goodreads_books, sync_action['column'],
                                                          sync_action['action'], sync_action['value'],
                                                          sync_action.get('special',''))
        self.db.commit()

    def _apply_tag_changes_to_books(self, goodreads_books, action, value):
        '''
        Apply changes to a tags column.
        '''
        ids = [book['calibre_id'] for book in goodreads_books]
        value = value.split(',')
        if action == 'ADD':
            self.db.bulk_modify_tags(ids, add=value)
        else:
            self.db.bulk_modify_tags(ids, remove=value)

    def _apply_rating_changes_to_books(self, goodreads_books, action, value):
        '''
        Apply changes to a rating column. Currently there is only one way this is allowed which is
        by using the sync rating functionality so simplified because of this.
        '''
        for book in goodreads_books:
            calibre_id = book['calibre_id']
            existing_value = self.db.rating(calibre_id, index_is_id=True)
            if action == 'ADD':
                if value == 'none':
                    new_value = 0.
                else:
                    rating_value = book.get('goodreads_rating','0')
                    # Adapt the Goodreads value (0-5) to calibre db value (range 0-10)
                    new_value = float(rating_value) * 2
            elif action == 'REMOVE':
                new_value = 0.0 # Value for any REMOVE action
            if new_value != existing_value:
                self.db.set_rating(calibre_id, new_value, notify=False, commit=False)

    def _apply_comment_changes_to_books(self, goodreads_books, action, value):
        '''
        Apply changes to a rating column. Currently there is only one way this is allowed which is
        by using the sync review text functionality so simplified because of this.
        '''
        for book in goodreads_books:
            calibre_id = book['calibre_id']
            existing_value = self.db.comments(calibre_id, index_is_id=True)
            if action == 'ADD':
                if value == 'none':
                    new_value = ''
                else:
                    new_value = book['goodreads_review_text']
            elif action == 'REMOVE':
                new_value = '' # Value for any REMOVE action
            if new_value != existing_value:
                self.db.set_comment(calibre_id, new_value, notify=False, commit=False)

    def _apply_custom_column_changes_to_books(self, goodreads_books, column, action, value, special_action):
        '''
        Apply changes to a custom column. This could be a special case sync of rating/date/review text
        or it could be a straightforward applying of a value configured as an action by the user.
        '''
        if column not in self.custom_columns:
            # The user has deleted the custom column without updating the action rules
            return error_dialog(self.gui, 'Custom Column Missing',
                'You have a sync rule for custom column \'%s\' which does not exist in this library.<p>'%column +
                'This rule will be ignored. Either add a matching custom column or edit your sync rules.',
                show=True)
        col = self.custom_columns[column]
        typ = col['datatype']
        label = self.db.field_metadata.key_to_label(column)
        if typ == 'bool':
            for book in goodreads_books:
                calibre_id = book['calibre_id']
                new_value = value.lower() == 'y'
                if action == 'REMOVE':
                    existing_value = self.db.get_custom(calibre_id, label=label, index_is_id=True)
                    if existing_value != new_value:
                        # Nothing to do if the existing value does not match that to remove
                        continue
                    if self.db.prefs.get('bools_are_tristate'):
                        new_value = None
                    else:
                        new_value = not new_value
                self.db.set_custom(calibre_id, new_value, label=label, commit=False)
            return

        elif typ == 'datetime':
            for book in goodreads_books:
                calibre_id = book['calibre_id']
                existing_value = self.db.get_custom(calibre_id, label=label, index_is_id=True)
                if action == 'ADD':
                    if value == 'none':
                        new_value = None
                    elif value == 'today':
                        new_value = now()
                    else:
                        try:
                            date_value = book['goodreads_'+value]
                            if date_value:
                                new_value = date_value
                        except:
                            continue
                elif action == 'REMOVE':
                    new_value = None
                if new_value != existing_value:
                    self.db.set_custom(calibre_id, new_value, label=label, commit=False)
            return

        elif typ == 'rating':
            for book in goodreads_books:
                debug_print("_apply_custom_column_changes_to_books: book=", book )
                if not (value in book):
                    continue
                calibre_id = book['calibre_id']
                existing_value = self.db.get_custom(calibre_id, label=label, index_is_id=True)
                if action == 'ADD':
                    debug_print("_apply_custom_column_changes_to_books: rating - value=%s, existing_value=%s" % (value, existing_value) )
                    if value == 'none':
                        new_value = 0.0
                    else:
                        rating_value = book[value]
                        # Adapt the Goodreads value (0-5) to calibre db value (range 0-10)
                        new_value = float(rating_value) * 2
                elif action == 'REMOVE':
                    new_value = 0.0 # Value for any REMOVE action
                if new_value != existing_value:
                    self.db.set_custom(calibre_id, new_value, label=label, commit=False)
            return

        elif typ in ('float','int'):
            for book in goodreads_books:
                calibre_id = book['calibre_id']
                existing_value = self.db.get_custom(calibre_id, label=label, index_is_id=True)
                if action == 'ADD':
                    if value == 'none':
                        new_value = 0.
                    else:
                        new_value = book[value]
                        new_value = float(new_value)
                elif action == 'REMOVE':
                    new_value = 0 # Value for any REMOVE action
                if new_value != existing_value:
                    self.db.set_custom(calibre_id, new_value, label=label, commit=False)
            return

        elif typ in ('text', 'comments', 'enumeration'):
            if col['is_multiple']:
                # Will do the add or remove actions in bulk
                ids = [book['calibre_id'] for book in goodreads_books]
                value = value.split(',')
                if action == 'ADD':
                    self.db.set_custom_bulk_multiple(ids, add=value, label=label)
                else:
                    self.db.set_custom_bulk_multiple(ids, remove=value, label=label)
                return
            # A text/comments column we need to replace values in.
            for book in goodreads_books:
                calibre_id = book['calibre_id']
                existing_value = self.db.get_custom(calibre_id, label=label, index_is_id=True)
                if special_action == 'review_text':
                    value = book['goodreads_review_text']
                    if typ != 'comments':
                        value = value.replace('<br />',' ').strip()

                if action == 'ADD':
                    new_value = value
                elif existing_value:
                    new_value = existing_value.replace(value, '')
                else:
                    continue # Removing but has no current text
                if new_value != existing_value:
                    self.db.set_custom(calibre_id, new_value, label=label, commit=False)
        else:
            # Shouldn't happen due to validation when configuring actions
            raise ValueError('Unsupported custom column type for: ' + column + ' of ' + typ)

