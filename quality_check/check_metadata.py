from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

import re, datetime
from collections import defaultdict
from calibre.ebooks.metadata import authors_to_string, check_isbn, title_sort
from calibre.gui2 import info_dialog, error_dialog
from calibre.utils.localization import get_udc
from calibre.utils.titlecase import titlecase

import calibre_plugins.quality_check.config as cfg
from calibre_plugins.quality_check.check_base import BaseCheck
from calibre_plugins.quality_check.dialogs import ResultsSummaryDialog
from calibre_plugins.quality_check.helpers import get_formatted_author_initials

class MetadataCheck(BaseCheck):
    '''
    All checks related to working with book metadata.
    '''
    def perform_check(self, menu_key):
        if menu_key == 'check_title_sort':
            self.check_title_sort_valid()
        elif menu_key == 'check_author_sort':
            self.check_author_sort_valid()
        elif menu_key == 'check_isbn':
            self.check_isbn_valid()
        elif menu_key == 'check_pubdate':
            self.check_pubdate_valid()
        elif menu_key == 'check_dup_isbn':
            self.check_duplicate_isbn()
        elif menu_key == 'check_dup_series':
            self.check_duplicate_series()
        elif menu_key == 'check_series_gaps':
            self.check_series_gaps()
        elif menu_key == 'check_series_pubdate':
            self.check_series_pubdate()
        elif menu_key == 'check_excess_tags':
            self.check_tags_count()
        elif menu_key == 'check_html_comments':
            self.check_html_comments()
        elif menu_key == 'check_no_html_comments':
            self.check_no_html_comments()
        elif menu_key == 'check_authors_commas':
            self.check_authors_commas()
        elif menu_key == 'check_authors_no_commas':
            self.check_authors_no_commas()
        elif menu_key == 'check_authors_case':
            self.check_authors_case()
        elif menu_key == 'check_authors_non_alpha':
            self.check_authors_non_alpha()
        elif menu_key == 'check_authors_non_ascii':
            self.check_authors_non_ascii()
        elif menu_key == 'check_authors_initials':
            self.check_authors_initials()
        elif menu_key == 'check_titles_series':
            self.check_titles_series()
        elif menu_key == 'check_title_case':
            self.check_titles_titlecase()
        else:
            return error_dialog(self.gui, _('Quality Check failed'),
                                _('Unknown menu key for %s of \'%s\'')%('MetadataCheck', menu_key),
                                show=True, show_copy_button=False)


    def check_title_sort_valid(self):

        def book_lang(self):
            try:
                book_lang = self.languages_edit.lang_codes[0]
            except:
                book_lang = None
            return book_lang

        def evaluate_book(book_id, db):
            current_title_sort = db.title_sort(book_id, index_is_id=True)
            current_languages = db.languages(book_id, index_is_id=True)
            book_lang = None
            if current_languages:
                book_lang = current_languages.split(',')[0]
            title = db.title(book_id, index_is_id=True)
            if current_title_sort != title_sort(title, lang=book_lang):
                return True
            return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched books have a valid Title Sort'),
                             marked_text='invalid_title_sort',
                             status_msg_type=_('books for invalid title sort'))


    def check_author_sort_valid(self):

        def evaluate_book(book_id, db):
            current_author_sort = db.author_sort(book_id, index_is_id=True)
            authors = db.authors(book_id, index_is_id=True)
            if not authors:
                return True
            authors = [a.strip().replace('|', ',') for a in authors.split(',')]
            if current_author_sort != db.author_sort_from_authors(authors):
                return True
            return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched books have a valid Author Sort'),
                             marked_text='invalid_author_sort',
                             status_msg_type=_('books for invalid author sort'))


    def check_isbn_valid(self):

        def evaluate_book(book_id, db):
            isbn = db.isbn(book_id, index_is_id=True)
            if isbn:
                if not check_isbn(isbn):
                    return True
            return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched books have a valid ISBN'),
                             marked_text='invalid_isbn',
                             status_msg_type=_('books for invalid ISBN'))


    def check_pubdate_valid(self):

        def evaluate_book(book_id, db):
            pubdate = db.pubdate(book_id, index_is_id=True)
            timestamp = db.timestamp(book_id, index_is_id=True)
            if pubdate == timestamp:
                return True
            return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched books have a valid pubdate'),
                             marked_text='invalid_pubdate',
                             status_msg_type=_('books for invalid pubdate'))


    def check_duplicate_isbn(self):

        books_by_isbn = {}

        def evaluate_book(book_id, db):
            isbn = db.isbn(book_id, index_is_id=True)
            if isbn:
                if isbn not in books_by_isbn:
                    books_by_isbn[isbn] = set()
                books_by_isbn[isbn].add(book_id)
            # We will determine the match as a post step, not in this function
            return False

        total_count, _result_ids, cancelled_msg = self.check_all_files(evaluate_book, show_matches=False,
                                                                  status_msg_type=_('books for duplicate ISBN'))
        result_ids = list()
        for values in books_by_isbn.values():
            if len(values) > 1:
                result_ids.extend(values)
        # Time to display the results
        if len(result_ids) > 0:
            self.show_invalid_rows(result_ids, 'duplicate_isbn')

        msg = 'Checked %d books, found %d matches' %(total_count, len(result_ids))
        self.gui.status_bar.showMessage(msg)
        if len(result_ids) == 0:
            info_dialog(self.gui, _('No Matches%s')%cancelled_msg,
                               _('All searched books have unique ISBNs'), show=True)


    def check_duplicate_series(self):

        books_by_series = {}

        def evaluate_book(book_id, db):
            series = db.series(book_id, index_is_id=True)
            if series:
                series_index = db.series_index(book_id, index_is_id=True)
                _hash = '%s%0.4f'%(series, series_index)
                if _hash not in books_by_series:
                    books_by_series[_hash] = set()
                books_by_series[_hash].add(book_id)
            # We will determine the match as a post step, not in this function
            return False

        total_count, _result_ids, cancelled_msg = self.check_all_files(evaluate_book, show_matches=False,
                                                                  status_msg_type=_('books for duplicate series'))
        result_ids = list()
        for values in books_by_series.values():
            if len(values) > 1:
                result_ids.extend(values)
        # Time to display the results
        if len(result_ids) > 0:
            self.show_invalid_rows(result_ids, 'duplicate_series')
            self.gui.library_view.sort_by_named_field('series', True)

        msg = 'Checked %d books, found %d matches' %(total_count, len(result_ids))
        self.gui.status_bar.showMessage(msg)
        if len(result_ids) == 0:
            info_dialog(self.gui, _('No Matches%s')%cancelled_msg,
                               _('All searched books have unique series indexes'), show=True)


    def check_series_gaps(self):

        series_name_book_map = defaultdict(list)
        series_name_indexes_map = defaultdict(list)

        def evaluate_book(book_id, db):
            series = db.series(book_id, index_is_id=True)
            if series:
                series_index = db.series_index(book_id, index_is_id=True)
                series_name_book_map[series].append(book_id)
                if round(series_index) == series_index and series_index > 0:
                    series_name_indexes_map[series].append(int(series_index))
            # We will determine the match as a post step, not in this function
            return False

        total_count, _result_ids, cancelled_msg = self.check_all_files(evaluate_book, show_matches=False,
                                                                  status_msg_type='books for series gaps')
        result_ids = list()
        series_gap_count = book_gap_count = 0
        for series_name in sorted(list(series_name_indexes_map.keys()), key=lambda s: s.lower()):
            # Identify whether there are any gaps in this series
            series_indexes = sorted(series_name_indexes_map[series_name])
            max_value = max(series_indexes)

            book_id = series_name_book_map[series_name][0]
            authors = self.gui.current_db.authors(book_id, index_is_id=True)
            if authors:
                authors = [x.replace('|', ',') for x in authors.split(',')]
                header_text = 'Series: <b>%s</b> - Author: <b>%s</b> - Last: #%d' % (series_name, authors_to_string(authors), max_value)
            else:
                header_text = 'Series: <b>%s</b> - Last: #%d'%(series_name, max_value)
            if max_value >= 1000:
                #self.log('\t<span style="color:orange">Ignored due to series index too large (>=1000)</span>')
                continue

            series_gap_count += 1
            series_indexes = sorted(series_indexes)
            idx = 0
            missing_ids = []
            for expected_idx in range(1,max_value):
                if expected_idx != series_indexes[idx]:
                    missing_ids.append(expected_idx)
                    book_gap_count += 1
                else:
                    while expected_idx == series_indexes[idx]:
                        idx += 1
            if missing_ids:
                result_ids.extend(series_name_book_map[series_name])
                self.log(header_text)
                self.log('\tMissing#: ', ','.join(map(str, missing_ids)))

        if len(result_ids) > 0:
            self.show_invalid_rows(result_ids, 'series_gaps')
            self.gui.library_view.sort_by_named_field('series', True)

        msg = _('Checked %d books, found %d gaps in %d series') %(total_count, book_gap_count, series_gap_count)
        self.gui.status_bar.showMessage(msg)
        if len(result_ids) == 0:
            info_dialog(self.gui, _('No Matches%s')%cancelled_msg,
                               _('No series gaps exist in the books searched'), show=True)
        else:
            ResultsSummaryDialog(self.gui, _('Series Gaps Found%s')%cancelled_msg, msg, self.log).exec_()


    def check_series_pubdate(self):

        from calibre.utils.date import utc_tz

        series_name_book_map = defaultdict(list)
        series_name_indexes_map = defaultdict(list)

        def evaluate_book(book_id, db):
            series = db.series(book_id, index_is_id=True)
            if series:
                series_index = db.series_index(book_id, index_is_id=True)
                series_name_book_map[series].append(book_id)
                # Ignore books with series index < 1 - will assume they are anthologies or unrelated books
                if series_index >= 1:
                    # Add a tuple of the series index and the pubdate
                    pubdate = db.pubdate(book_id, index_is_id=True)
                    series_name_indexes_map[series].append( (series_index, pubdate) )
            # We will determine the match as a post step, not in this function
            return False

        total_count, _result_ids, cancelled_msg = self.check_all_files(evaluate_book, show_matches=False,
                                                                  status_msg_type=_('books for series pubdate order'))
        result_ids = list()
        series_disorder_count = book_disorder_count = 0
        for series_name in sorted(series_name_indexes_map.keys()):
            # Identify whether there are any ordering issues in this series
            series_index_dates = sorted(series_name_indexes_map[series_name])

            book_id = series_name_book_map[series_name][0]
            authors = self.gui.current_db.authors(book_id, index_is_id=True)
            if authors:
                authors = [x.replace('|', ',') for x in authors.split(',')]
                self.log('Series: <b>%s</b> - Author: <b>%s</b>'%
                         (series_name, authors_to_string(authors)))
            else:
                self.log('Series: <b>%s</b>'%(series_name,))

            is_series_wrong = False
            last_pubdate = datetime.datetime(101, 1, 1, tzinfo=utc_tz)
            for (sidx, pubdate) in series_index_dates:
                if pubdate < last_pubdate:
                    self.log('\tDate issue at idx: %.2f '% sidx, pubdate, last_pubdate)
                    is_series_wrong = True
                    book_disorder_count += 1
                last_pubdate = pubdate

            if is_series_wrong:
                result_ids.extend(series_name_book_map[series_name])
                series_disorder_count += 1

        if len(result_ids) > 0:
            self.show_invalid_rows(result_ids, 'series_pubdate')
            self.gui.library_view.sort_by_named_field('series', True)

        msg = _('Checked %d books, found %d disordered in %d series') %(total_count, book_disorder_count, series_disorder_count)
        self.gui.status_bar.showMessage(msg)
        if len(result_ids) == 0:
            info_dialog(self.gui, _('No Matches%s')%cancelled_msg,
                               _('No series pubdate disorders exist in the books searched'), show=True)
        else:
            ResultsSummaryDialog(self.gui, _('Series Pubdate Issues Found'), msg, self.log).exec_()


    def check_tags_count(self):
        c = cfg.plugin_prefs[cfg.STORE_OPTIONS]
        max_tags = c[cfg.KEY_MAX_TAGS]
        excluded_tags_set = set(c[cfg.KEY_MAX_TAG_EXCLUSIONS])

        def evaluate_book(book_id, db):
            tags = db.tags(book_id, index_is_id=True)
            if tags:
                tags = [t.strip() for t in tags.split(',')]
                tags_set = set(tags) - excluded_tags_set
                if len(tags_set) > max_tags:
                    return True
            return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched books have a valid tag count'),
                             marked_text='excess_tags',
                             status_msg_type=_('books for invalid tag count'))


    def check_html_comments(self):
        html_patterns = [re.compile(pat, re.IGNORECASE) for pat in
                [
                    r'</b>',
                    r'</i>',
                    r'</s>',
                    r'</u>',
                    r'</a>',
                    r'</h\d+>',
                    r'</sub>',
                    r'</sup>',
                    r'</ol>',
                    r'</ul>',
                    r'</li>'
                ]
        ]

        def evaluate_book(book_id, db):
            comments = db.comments(book_id, index_is_id=True)
            if comments:
                has_html = False
                for pat in html_patterns:
                    if pat.search(comments):
                        has_html = True
                        break
                if has_html:
                    return True
            return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched books have no HTML in comments'),
                             marked_text='html_in_comments',
                             status_msg_type=_('books for no HTML in comments'))


    def check_no_html_comments(self):
        no_html_patterns = [re.compile(pat, re.IGNORECASE) for pat in
                [
                    r'</div>'
                    r'</p>',
                    r'</a>',
                    r'</h\d+>',
                    r'</b>',
                    r'</i>',
                    r'</s>',
                    r'</u>',
                    r'</sub>',
                    r'</sup>',
                    r'</ol>',
                    r'</ul>',
                    r'</li>',
                ]
        ]

        def evaluate_book(book_id, db):
            comments = db.comments(book_id, index_is_id=True)
            if comments:
                has_no_html = True
                for pat in no_html_patterns:
                    if pat.search(comments):
                        has_no_html = False
                        break
                if has_no_html:
                    return True
            return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched books have HTML in comments'),
                             marked_text='no_html_in_comments',
                             status_msg_type=_('books for HTML in comments'))


    def check_authors_commas(self):

        def evaluate_book(book_id, db):
            authors = db.authors(book_id, index_is_id=True)
            if authors:
                authors = [a.strip().replace('|', ',') for a in authors.split(',')]
                for author in authors:
                    if ',' in author:
                        return True
            return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched book authors have no commas'),
                             marked_text='authors_commas',
                             status_msg_type=_('books with authors having commas'))


    def check_authors_no_commas(self):

        def evaluate_book(book_id, db):
            authors = db.authors(book_id, index_is_id=True)
            if authors:
                authors = [a.strip().replace('|', ',') for a in authors.split(',')]
                for author in authors:
                    if ',' not in author:
                        return True
            return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched book authors have commas'),
                             marked_text='authors_no_commas',
                             status_msg_type=_('books with authors not having commas'))


    def check_authors_case(self):

        def evaluate_book(book_id, db):
            authors = db.authors(book_id, index_is_id=True)
            if authors:
                authors = [a.strip().replace('|', ',') for a in authors.split(',')]
                for author in authors:
                    if author == author.upper() or author == author.lower():
                        return True
            return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched authors have a valid casing'),
                             marked_text='invalid_author_case',
                             status_msg_type=_('books for invalid author casing'))


    def check_authors_non_alpha(self):
        RE_ALPHA = re.compile(r'[^A-Za-z\'\.,\- ]', re.UNICODE)
        handler = get_udc()

        def evaluate_book(book_id, db):
            authors = db.authors(book_id, index_is_id=True)
            if authors:
                authors = [a.strip().replace('|', ',') for a in authors.split(',')]
                for author in authors:
                    ascii_author = handler.decode(author)
                    if RE_ALPHA.search(ascii_author):
                        return True
            return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched book authors have alphabetic names'),
                             marked_text='authors_non_alphabetic',
                             status_msg_type=_('books with authors having non-alphabetic names'))


    def check_authors_non_ascii(self):
        handler = get_udc()

        def evaluate_book(book_id, db):
            authors = db.authors(book_id, index_is_id=True)
            if authors:
                authors = [a.strip().replace('|', ',') for a in authors.split(',')]
                for author in authors:
                    ascii_author = handler.decode(author)
                    if ascii_author != author:
                        return True
            return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched book authors have ascii names'),
                             marked_text='authors_non_ascii',
                             status_msg_type=_('books with authors having non-ascii names'))


    def check_authors_initials(self):
        c = cfg.plugin_prefs[cfg.STORE_OPTIONS]
        initials_mode = c.get(cfg.KEY_AUTHOR_INITIALS_MODE, cfg.AUTHOR_INITIALS_MODES[0])

        def evaluate_book(book_id, db):
            authors = db.authors(book_id, index_is_id=True)
            if authors:
                authors = [a.strip().replace('|', ',') for a in authors.split(',')]
                for author in authors:
                    expected_author = get_formatted_author_initials(initials_mode, author)
                    if expected_author != author:
                        return True
            return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched book authors have correct initials'),
                             marked_text='authors_incorrect_initials',
                             status_msg_type=_('books with authors having incorrect initials'))


    def check_titles_series(self):

        def evaluate_book(book_id, db):
            title = db.title(book_id, index_is_id=True)
            if '-' not in title:
                if re.match(r'[0-9]', title) is None:
                    return False
            return True

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched books do not have titles with series names'),
                             marked_text='invalid_titles_series',
                             status_msg_type=_('book titles with possible series names'))


    def check_titles_titlecase(self):

        def evaluate_book(book_id, db):
            title = db.title(book_id, index_is_id=True)
            if title != titlecase(title):
                return True
            return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched titles have a valid title casing'),
                             marked_text='invalid_title_case',
                             status_msg_type=_('books for invalid title casing'))

