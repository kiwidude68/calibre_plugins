from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import traceback
try:
    from qt.core import QProgressDialog, QTimer
except ImportError:
    from PyQt5.Qt import QProgressDialog, QTimer
    
from calibre.gui2 import warning_dialog
from calibre.gui2.convert.single import sort_formats_by_preference
from calibre.utils.config import prefs

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

class QueueProgressDialog(QProgressDialog):

    def __init__(self, gui, book_ids, queue, db):
        QProgressDialog.__init__(self, '', u'', 0, len(book_ids), gui)
        self.setWindowTitle(_('Queueing books for extracting ISBN'))
        self.setMinimumWidth(500)
        self.book_ids, self.queue, self.db = book_ids, queue, db
        self.gui = gui
        self.i = 0
        self.failed_ids, self.no_format_ids, self.books_to_scan = [], [], []
        self.input_map = prefs['input_format_order']
        # QTimer workaround on Win 10 on first go for Win10/Qt6 users not displaying dialog properly.
        QTimer.singleShot(100, self.do_book)
        self.exec_()

    def do_book(self):
        book_id = self.book_ids[self.i]
        self.i += 1
        title = ''
        try:
            mi = self.db.get_metadata(book_id, index_is_id=True, get_user_categories=False)
            title, formats = mi.title, mi.formats
            if not formats:
                self.failed_ids.append((book_id, title))
                self.no_format_ids.append((book_id, title))
            else:
                # Sorted formats using the preferred input conversion list.
                sorted_formats = sort_formats_by_preference(formats, self.input_map)
                paths_for_formats = []
                for f in sorted_formats:
                    paths_for_formats.append((f,
                                          self.db.format_abspath(book_id, f, index_is_id=True)))
                self.setLabelText(_('Queueing') + ' ' + title)
                self.books_to_scan.append((book_id, title, mi.last_modified,
                                           mi.isbn, paths_for_formats))
            self.setValue(self.i)
        except:
            traceback.print_exc()
            self.failed_ids.append((book_id, title))

        if self.i >= len(self.book_ids):
            return self.do_queue()
        else:
            QTimer.singleShot(0, self.do_book)

    def do_queue(self):
        if self.gui is None:
            # There is a nasty QT bug with the timers/logic above which can
            # result in the do_queue method being called twice
            return
        self.hide()
        if self.books_to_scan == []:
            warning_dialog(self.gui, _('Extract ISBN failed'),
                _('Scan aborted as no books with formats found.'),
                show_copy_button=False).exec_()
        self.gui = None
        if self.books_to_scan:
            # Queue a job to process these books
            self.queue(self.books_to_scan, self.failed_ids, self.no_format_ids)
