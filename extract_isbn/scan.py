from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import re

# calibre Python 3 compatibility.
from six import text_type as unicode

from calibre.ebooks.metadata import check_isbn

import calibre_plugins.extract_isbn.config as cfg

RE_ISBN = re.compile(u'\s*([0-9\-\.–­―—\^ ]{9,18}[0-9xX])', re.UNICODE)

RE_STRIP_STYLE = re.compile(u'<style[^<]+</style>', re.MULTILINE | re.UNICODE)
RE_STRIP_MARKUP = re.compile(u'<[^>]+>', re.UNICODE)

class BookScanner(object):

    def __init__(self, log):
        self.log = log
        self.isbns10 = []
        self.isbns13 = []
        c = cfg.plugin_prefs[cfg.STORE_NAME]
        self.valid_isbn13s = c.get(cfg.KEY_VALID_ISBN13_PREFIX,
                                   cfg.DEFAULT_STORE_VALUES[cfg.KEY_VALID_ISBN13_PREFIX])

    def get_isbn_result(self):
        if self.isbns13:
            return self.isbns13[0]
        elif self.isbns10:
            return self.isbns10[0]
        return None

    def has_identifier(self):
        return len(self.isbns13) + len(self.isbns10) > 0

    def look_for_identifiers_in_text(self, book_files, forward=True):
        '''
        Scans text (string) for identifiers, returns one if found
        '''
        if not forward:
            book_files = reversed(book_files)
        for book_file in book_files:
            # Strip all the html markup tags out in case we get clashes with svg covers
            book_file = unicode(RE_STRIP_STYLE.sub('', book_file))
            book_file = unicode(RE_STRIP_MARKUP.sub('!', book_file))
            #open('E:\\isbn.html', 'wb').write(book_file)
            if forward:
                for match in RE_ISBN.finditer(book_file):
                    txt = match.group(1)
                    txt = re.sub('\n', '', txt)     # it's possible that because of the pdf formatting the isbn will be spread over multiple lines
                    self._evaluate_isbn_match(txt)
            else:
                matches = RE_ISBN.findall(book_file)
                for match in reversed(matches):
                    self._evaluate_isbn_match(match)
            if self.has_identifier():
                break

    def _evaluate_isbn_match(self, original_text):
        txt = re.sub('[^0-9X]','', original_text)
        txt_len = len(txt)
        # Grant - next check for repeating digits like 1111111111
        # is redundant as of Calibre 0.8, but not exactly
        # sure which version Kovid changed so rather than dragging
        # extract isbn dependency forward will repeat here.
        all_same = re.match(r'(\d)\1{9,12}$', txt)
        if all_same is None:
            if txt_len == 10:
                if check_isbn(txt):
                    self.log.warn('      Valid ISBN10:', txt)
                    self.isbns10.append(txt)
                    return
            elif txt_len == 13:
                if txt[:3] in self.valid_isbn13s:
                    if check_isbn(txt):
                        self.log.warn('      Valid ISBN13:', txt)
                        self.isbns13.append(txt)
                        return
        self.log.debug('      Invalid ISBN match:', original_text)
