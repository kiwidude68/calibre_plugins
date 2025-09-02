from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from calibre.utils.logging import GUILog

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

import calibre_plugins.quality_check.config as cfg
from calibre_plugins.quality_check.dialogs import QualityProgressDialog, ResultsSummaryDialog

class BaseCheck(object):
    '''
    Base class for all quality check implementations
    '''
    def __init__(self, gui, initial_search=''):
        self.gui = gui
        self.log = GUILog()
        self.menu_key = None
        self.book_ids = []
        self.initial_search = initial_search
        self.show_matches_override = None

    def perform_check(self, menu_key):
        '''
        Override this method to perform the appropriate check for the menu key given
        '''
        pass

    def set_search_scope(self, scope, book_ids=[]):
        self.scope = scope
        self.book_ids = book_ids

    def set_show_matches_override(self, show_matches_override):
        self.show_matches_override = show_matches_override

    def check_all_files(self, callback_fn, status_msg_type='books',
                        no_match_msg=None, show_matches=True, marked_text='true'):
        '''
        Performs the quality check in a threaded fashion with progress dialog
        '''
        # If scope is limited to selected book ids this set will have been set.
        if not self.book_ids:
            self.gui.search.clear()
            self.book_ids = self.gui.current_db.search(self.initial_search, return_matches=True)
        # Exclude any books that have exclusions for this check
        if self.menu_key:
            excluded_ids = cfg.get_valid_excluded_books(self.gui.current_db, self.menu_key)
            if excluded_ids:
                excluded_map = dict((i, True) for i in excluded_ids)
                self.book_ids = [i for i in self.book_ids if i not in excluded_map]
        # Override the show matches behavior if so
        if self.show_matches_override is not None:
            show_matches = self.show_matches_override

        d = QualityProgressDialog(self.gui, self.book_ids, callback_fn, self.gui.current_db,
                                  status_msg_type)
        cancelled_msg = ''
        if d.wasCanceled():
            cancelled_msg = _(' (cancelled)')
        if show_matches:
            if len(d.result_ids) > 0:
                self.show_invalid_rows(d.result_ids, marked_text)
                if self.log.plain_text:
                    sd = ResultsSummaryDialog(self.gui, _('Quality Check'),
                                             _('%d matches found%s, see log for details')%(len(d.result_ids), cancelled_msg),
                                             self.log)
                    sd.exec_()
            if no_match_msg:
                msg = _('Checked %d books, found %d matches%s') %(d.total_count, len(d.result_ids), cancelled_msg)
                self.gui.status_bar.showMessage(msg)
                if len(d.result_ids) == 0:
                    sd = ResultsSummaryDialog(self.gui, _('No Matches'), no_match_msg, self.log)
                    sd.exec_()
        return d.total_count, d.result_ids, cancelled_msg

    def show_invalid_rows(self, result_ids, marked_text='true'):
        marked_ids = dict.fromkeys(result_ids, marked_text)
        self.gui.current_db.set_marked_ids(marked_ids)
        self.gui.search.set_search_string('marked:%s' % marked_text)
