from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import socket, re
from threading import Thread
from lxml.html import tostring

from calibre import browser, random_user_agent, as_unicode
from calibre.ebooks.chardet import xml_to_unicode
from calibre.utils.cleantext import clean_ascii_chars
from calibre.ebooks.oeb.base import urlquote

AMAZON_DOMAINS = {
    'com': _('US'),
    'fr': _('France'),
    'de': _('Germany'),
    'uk': _('UK'),
    'au': _('Australia'),
    'it': _('Italy'),
    'jp': _('Japan'),
    'es': _('Spain'),
    'br': _('Brazil'),
    'in': _('India'),
    'nl': _('Netherlands'),
    'cn': _('China'),
    'ca': _('Canada'),
    'se': _('Sweden'),
}

def iri_quote_plus(url):
    ans = urlquote(url)
    if isinstance(ans, bytes):
        ans = ans.decode('utf-8')
    return ans.replace('%20', '+')

def parse_html(raw):
    try:
        from html5_parser import parse
    except ImportError:
        # Old versions of calibre
        import html5lib
        return html5lib.parse(raw, treebuilder='lxml', namespaceHTMLElements=False)
    else:
        return parse(raw)

class CaptchaError(Exception):
    pass


class AmazonRatingWorker(Thread):
    '''
    Get book details from Amazon book page
    '''
    def __init__(self, amazon_id, amazon_domain, log, timeout=20):
        Thread.__init__(self)
        self.daemon = True
        self.amazon_id = amazon_id
        self.domain = amazon_domain
        self.log = log
        self.timeout = timeout
        self.browser = browser(user_agent=random_user_agent())
        self.rating = None
        self.rating_count = None
        self.ratings_pat = re.compile(
            r'([0-9.]+) ?(out of|von|su|étoiles sur|つ星のうち|de un máximo de|de) ([\d\.]+)( (stars|Sternen|stelle|estrellas|estrelas)){0,1}')

    def get_website_domain(self, domain):
        return {'uk': 'co.uk', 'jp': 'co.jp', 'br': 'com.br', 'au': 'com.au'}.get(domain, domain)

    def create_query(self):
        try:
            from urllib.parse import urlencode, unquote_plus
        except ImportError:
            from urllib import urlencode, unquote_plus
        domain = self.domain

        q = {'search-alias': 'aps',
             'unfiltered': '1',
            }

        if domain == 'com':
            q['sort'] = 'relevanceexprank'
        else:
            q['sort'] = 'relevancerank'

        q['field-keywords'] = self.amazon_id

        if domain == 'nl':
            q['__mk_nl_NL'] = 'ÅMÅŽÕÑ'
            if 'field-keywords' not in q:
                q['field-keywords'] = ''
            for f in 'field-isbn field-title field-author'.split():
                q['field-keywords'] += ' ' + q.pop(f, '')
            q['field-keywords'] = q['field-keywords'].strip()
            
        encoded_q = dict([(x.encode('utf-8', 'ignore'), y.encode(
            'utf-8', 'ignore')) for x, y in q.items()])
        url_query = urlencode(encoded_q)
        # amazon's servers want IRIs with unicode characters not percent esaped
        parts = []
        for x in url_query.split(b'&' if isinstance(url_query, bytes) else '&'):
            k, v = x.split(b'=' if isinstance(x, bytes) else '=', 1)
            parts.append('{}={}'.format(iri_quote_plus(unquote_plus(k)), iri_quote_plus(unquote_plus(v))))
        url_query = '&'.join(parts)
        url = 'https://www.amazon.%s/s/?' % self.get_website_domain(
            domain) + url_query
        return url

    def parse_results_page(self, root, domain):
        matches = []

        def title_ok(title):
            title = title.lower()
            bad = ['bulk pack', '[audiobook]', '[audio cd]',
                   '(a book companion)', '( slipcase with door )', ': free sampler']
            if self.domain == 'com':
                bad.extend(['(%s edition)' % x for x in ('spanish', 'german')])
            for x in bad:
                if x in title:
                    return False
            if title and title[0] in '[{' and re.search(r'\(\s*author\s*\)', title) is not None:
                # Bad entries in the catalog
                return False
            return True

        for query in (
                '//div[contains(@class, "s-result-list")]//h2/a[@href]',
                '//div[contains(@class, "s-result-list")]//div[@data-index]//h5//a[@href]',
                r'//li[starts-with(@id, "result_")]//a[@href and contains(@class, "s-access-detail-page")]',
        ):
            result_links = root.xpath(query)
            if result_links:
                break
        for a in result_links:
            title = tostring(a, method='text', encoding='unicode')
            if title_ok(title):
                url = a.get('href')
                if url.startswith('/'):
                    url = 'https://www.amazon.%s%s' % (
                        self.get_website_domain(domain), url)
                matches.append(url)

        if not matches:
            # Previous generation of results page markup
            for div in root.xpath(r'//div[starts-with(@id, "result_")]'):
                links = div.xpath(r'descendant::a[@class="title" and @href]')
                if not links:
                    # New amazon markup
                    links = div.xpath('descendant::h3/a[@href]')
                for a in links:
                    title = tostring(a, method='text', encoding='unicode')
                    if title_ok(title):
                        url = a.get('href')
                        if url.startswith('/'):
                            url = 'https://www.amazon.%s%s' % (
                                self.get_website_domain(domain), url)
                        matches.append(url)
                    break

        if not matches:
            # This can happen for some user agents that Amazon thinks are
            # mobile/less capable
            for td in root.xpath(
                    r'//div[@id="Results"]/descendant::td[starts-with(@id, "search:Td:")]'):
                for a in td.xpath(r'descendant::td[@class="dataColumn"]/descendant::a[@href]/span[@class="srTitle"]/..'):
                    title = tostring(a, method='text', encoding='unicode')
                    if title_ok(title):
                        url = a.get('href')
                        if url.startswith('/'):
                            url = 'https://www.amazon.%s%s' % (
                                self.get_website_domain(domain), url)
                        matches.append(url)
                    break
        if not matches and root.xpath('//form[@action="/errors/validateCaptcha"]'):
            raise CaptchaError('Amazon returned a CAPTCHA page. Recently Amazon has begun using statistical'
                               ' profiling to block access to its website. As such this metadata plugin is'
                               ' unlikely to ever work reliably.')

        # Keep only the top 1 matches as the matches are sorted by relevance by
        # Amazon so lower matches are not likely to be very relevant
        return matches[:1]

    def run(self):
        try:
            query = self.create_query()
            self.log.info('Searching Amazon: ',query)
            br = self.browser
            try:
                raw = br.open_novisit(query, timeout=self.timeout).read().strip()
            except Exception as e:
                if callable(getattr(e, 'getcode', None)) and \
                        e.getcode() == 404:
                    self.log.error('Query malformed: %r'%query)
                    return
                attr = getattr(e, 'args', [None])
                attr = attr if attr else [None]
                if isinstance(attr[0], socket.timeout):
                    msg = 'Amazon timed out. Try again later.'
                    self.log.error(msg)
                else:
                    msg = 'Failed to make identify query: %r'%query
                    self.log.exception(msg)
                return as_unicode(msg)

            raw = clean_ascii_chars(xml_to_unicode(raw,
                strip_encoding_pats=True, resolve_entities=True)[0])

            matches = []
            found = '<title>404 - ' not in raw

            if found:
                try:
                    root = parse_html(raw)
                except:
                    msg = 'Failed to parse amazon page for query: %r' % query
                    self.log.exception(msg)
                    return as_unicode(msg)

            if found:
                matches = self.parse_results_page(root, self.domain)

            if not matches:
                self.log.error('No matches found with query: %r'%query)
                return

            self.get_details(matches[0])
        except:
            self.log.exception('get_details failed')

    def get_details(self, url):
        self.url = url
        try:
            self.log.info('Amazon book url: %r'%self.url)
            br = self.browser
            raw = br.open_novisit(self.url, timeout=self.timeout).read().strip()
        except Exception as e:
            if callable(getattr(e, 'getcode', None)) and \
                    e.getcode() == 404:
                self.log.error('URL malformed: %r'%self.url)
                return
            attr = getattr(e, 'args', [None])
            attr = attr if attr else [None]
            if isinstance(attr[0], socket.timeout):
                msg = 'Amazon timed out. Try again later.'
                self.log.error(msg)
            else:
                msg = 'Failed to make details query: %r'%self.url
                self.log.exception(msg)
            return

        raw = xml_to_unicode(raw, strip_encoding_pats=True,
                resolve_entities=True)[0]
        #open('E:/amazon.html', 'wb').write(raw)

        if '<title>404 - ' in raw:
            self.log.error('URL malformed: %r'%self.url)
            return

        try:
            root = parse_html(clean_ascii_chars(raw))
        except:
            msg = 'Failed to parse amazon details page: %r'%self.url
            self.log.exception(msg)
            return

        errmsg = root.xpath('//*[@id="errorMessage"]')
        if errmsg:
            msg = 'Failed to parse amazon details page: %r'%self.url
            msg += tostring(errmsg, method='text', encoding='unicode').strip()
            self.log.error(msg)
            return

        self.parse_details(root)

    def parse_details(self, root):
        try:
            self.rating = self.parse_rating(root)
        except:
            self.log.exception('Error parsing ratings for url: %r'%self.url)
        try:
            self.rating_count = self.parse_rating_count(root)
        except:
            self.log.exception('Error parsing rating count for url: %r'%self.url)

    def parse_rating(self, root):
        for x in root.xpath('//div[@id="cpsims-feature" or @id="purchase-sims-feature" or @id="rhf"]'):
            # Remove the similar books section as it can cause spurious
            # ratings matches
            x.getparent().remove(x)

        rating_paths = ('//div[@data-feature-name="averageCustomerReviews" or @id="averageCustomerReviews"]',
                        '//div[@class="jumpBar"]/descendant::span[contains(@class,"asinReviewsSummary")]',
                        '//div[@class="buying"]/descendant::span[contains(@class,"asinReviewsSummary")]',
                        '//span[@class="crAvgStars"]/descendant::span[contains(@class,"asinReviewsSummary")]')
        ratings = None
        for p in rating_paths:
            ratings = root.xpath(p)
            if ratings:
                break

        def parse_ratings_text(text):
            try:
                m = self.ratings_pat.match(text)
                return float(m.group(1).replace(',', '.')) / float(m.group(3)) * 5
            except Exception:
                pass

        if ratings:
            ratings = ratings[0]
            for elem in ratings.xpath('descendant::*[@title]'):
                t = elem.get('title').strip()
                if self.domain == 'cn':
                    m = self.ratings_pat_cn.match(t)
                    if m is not None:
                        return float(m.group(1))
                elif self.domain == 'jp':
                    m = self.ratings_pat_jp.match(t)
                    if m is not None:
                        return float(m.group(1))
                else:
                    ans = parse_ratings_text(t)
                    if ans is not None:
                        return ans
            for elem in ratings.xpath('descendant::span[@class="a-icon-alt"]'):
                t = self.tostring(
                    elem, encoding='unicode', method='text', with_tail=False).strip()
                ans = parse_ratings_text(t)
                if ans is not None:
                    return ans

    def parse_rating_count(self, root):
        rating_paths = ('//span[@id="acrCustomerReviewText"]',)
        rating_node = None
        for p in rating_paths:
            rating_node = root.xpath(p)
            if rating_node:
                #self.log('Found rating count match using:',p)
                break
        if rating_node:
            rating_text = tostring(rating_node[0], method='text', encoding='unicode')
            #self.log('CHOSE Rating text:',rating_text)
            rating_text = re.sub('[^0-9]', '', rating_text)
            rating_count = int(rating_text)
            return rating_count
