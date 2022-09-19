from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import traceback

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.gui2 import error_dialog

from calibre_plugins.quality_check.check_base import BaseCheck
from calibre_plugins.quality_check.helpers import get_title_authors_text
from calibre_plugins.quality_check.mobi6 import MinimalMobiReader

class MobiCheck(BaseCheck):
    '''
    All checks related to working with MOBI formats.
    '''
    MOBI_FORMATS = ['MOBI', 'AZW', 'AZW3']

    def __init__(self, gui):
        BaseCheck.__init__(self, gui, 'formats:=mobi or formats:=azw or formats:=azw3')

    def perform_check(self, menu_key):
        if menu_key == 'check_mobi_missing_ebok':
            self.check_mobi_missing_ebok()
        elif menu_key == 'check_mobi_missing_asin':
            self.check_mobi_missing_asin()
        elif menu_key == 'check_mobi_share_disabled':
            self.check_mobi_share_disabled()
        elif menu_key == 'check_mobi_clipping_limit':
            self.check_mobi_clipping_limit()
        else:
            return error_dialog(self.gui, _('Quality Check failed'),
                                _('Unknown menu key for %s of \'%s\'')%('MobiCheck', menu_key),
                                show=True, show_copy_button=False)


    def check_mobi_missing_ebok(self):

        def evaluate_book(book_id, db):
            try:
                show_book = False
                for fmt in self.MOBI_FORMATS:
                    if not db.has_format(book_id, fmt, index_is_id=True):
                        continue
                    path_to_book = db.format_abspath(book_id, fmt, index_is_id=True)
                    if not path_to_book:
                        self.log.error('ERROR: %s format is missing: %s'%(fmt, get_title_authors_text(db, book_id)))
                        continue
                    with MinimalMobiReader(path_to_book, self.log) as mmr:
                        if mmr.book_header:
                            exth = mmr.book_header.exth
                            if exth:
                                if exth.cdetype == 'EBOK':
                                    # This book is valid
                                    continue
                                else:
                                    self.log('Missing EBOK tag: <b>%s</b>'% get_title_authors_text(db, book_id))
                                    self.log('\tcdetype:', exth.cdetype)
                            else:
                                self.log('Missing EBOK tag: <b>%s</b>'% get_title_authors_text(db, book_id))
                                self.log.error('\tNo EXTH header found in this %s file')
                        else:
                            self.log('Missing EBOK tag: <b>%s</b>'% get_title_authors_text(db, book_id))
                            self.log.error('\tNo valid book header found in this MOBI file')
                        show_book = True

                return show_book
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched MOBI books have EBOK cdetag values'),
                             marked_text='mobi_missing_ebok_cdetag',
                             status_msg_type=_('MOBI books missing EBOK cdetag'))


    def check_mobi_missing_asin(self):

        def evaluate_book(book_id, db):
            try:
                show_book = False
                for fmt in self.MOBI_FORMATS:
                    if not db.has_format(book_id, fmt, index_is_id=True):
                        continue
                    path_to_book = db.format_abspath(book_id, fmt, index_is_id=True)
                    if not path_to_book:
                        self.log.error('ERROR: %s format is missing: %s'%(fmt, get_title_authors_text(db, book_id)))
                        continue
                    with MinimalMobiReader(path_to_book, self.log) as mmr:
                        if mmr.book_header:
                            exth = mmr.book_header.exth
                            if exth:
                                if exth.asin:
                                    # This is valid
                                    continue
                                else:
                                    self.log('Missing ASIN: <b>%s</b>'% get_title_authors_text(db, book_id))
                            else:
                                self.log('Missing ASIN: <b>%s</b>'% get_title_authors_text(db, book_id))
                                self.log.error('\tNo EXTH header found in this %s file'%fmt)
                        else:
                            self.log('Missing ASIN: <b>%s</b>'% get_title_authors_text(db, book_id))
                            self.log.error('\tNo valid book header found in this %s file'%fmt)
                        show_book = True

                return show_book
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched MOBI books have ASIN values'),
                             marked_text='mobi_missing_asin',
                             status_msg_type=_('MOBI books missing ASIN'))


    def check_mobi_share_disabled(self):

        def evaluate_book(book_id, db):
            try:
                show_book = False
                for fmt in ('MOBI',): #Yes, this is strange but I don't want to rewrite the loop
                    if not db.has_format(book_id, fmt, index_is_id=True):
                        continue
                    path_to_book = db.format_abspath(book_id, 'MOBI', index_is_id=True)
                    if not path_to_book:
                        self.log.error('ERROR: %s format is missing: %s'%(fmt, get_title_authors_text(db, book_id)))
                        continue
                    with MinimalMobiReader(path_to_book, self.log) as mmr:
                        if mmr.book_header:
                            exth = mmr.book_header.exth
                            if exth:
                                if len(exth.asin) and exth.asin2 == exth.asin:
                                    # This is valid for sharing so move on
                                    continue
                                if len(exth.asin) and len(exth.asin2):
                                    self.log('Different ASINs at EXTH 113/504: <b>%s</b>'% get_title_authors_text(db, book_id))
                                elif len(exth.asin) == 0:
                                    self.log('Missing ASIN at EXTH 113: <b>%s</b>'% get_title_authors_text(db, book_id))
                                else:
                                    self.log('Missing ASIN at EXTH 504: <b>%s</b>'% get_title_authors_text(db, book_id))
                            else:
                                self.log('Missing ASIN: <b>%s</b>'% get_title_authors_text(db, book_id))
                                self.log.error('\tNo EXTH header found in this %s file'%fmt)
                        else:
                            self.log('Missing ASIN: <b>%s</b>'% get_title_authors_text(db, book_id))
                            self.log.error('\tNo valid book header found in this %s file'%fmt)
                        show_book = True

                return show_book
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched MOBI books have Twitter/Facebook sharing enabled'),
                             marked_text='mobi_share_disabled',
                             status_msg_type=_('MOBI books unable to share on Twitter/Facebook'))


    def check_mobi_clipping_limit(self):

        def evaluate_book(book_id, db):
            try:
                show_book = False
                for fmt in self.MOBI_FORMATS:
                    if not db.has_format(book_id, fmt, index_is_id=True):
                        continue
                    path_to_book = db.format_abspath(book_id, fmt, index_is_id=True)
                    if not path_to_book:
                        self.log.error('ERROR: %s format is missing: %s'%(fmt, get_title_authors_text(db, book_id)))
                        continue
                    with MinimalMobiReader(path_to_book, self.log) as mmr:
                        if mmr.book_header:
                            exth = mmr.book_header.exth
                            if exth:
                                if exth.clipping_limit and exth.clipping_limit < 100:
                                    self.log('Clipping limit of %d%% in: <b>%s</b>'%(exth.clipping_limit, get_title_authors_text(db, book_id)))
                                    show_book = True
                return show_book
            except:
                self.log.error('ERROR parsing book: ', path_to_book)
                self.log(traceback.format_exc())
                return False

        self.check_all_files(evaluate_book,
                             no_match_msg=_('All searched MOBI books have no clipping limits'),
                             marked_text='mobi_clipping_limit',
                             status_msg_type=_('MOBI books for clipping limits'))

