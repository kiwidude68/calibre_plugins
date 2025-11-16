from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import os, traceback
from collections import OrderedDict
try:
    from qt.core import (Qt, QProgressDialog, QTimer, QVBoxLayout, QTableWidget, 
                         QHeaderView, QDialogButtonBox, QTableWidgetItem)
except ImportError:
    from PyQt5.Qt import (Qt, QProgressDialog, QTimer, QVBoxLayout, QTableWidget, 
                          QHeaderView, QDialogButtonBox, QTableWidgetItem)

from calibre.gui2 import warning_dialog
try: # Needed as part of calibre conversion changes in 3.27.0.
    from calibre.ebooks.conversion.config import get_available_formats_for_book
except ImportError:
    from calibre.gui2.convert.single import get_available_formats_for_book
        
from calibre.gui2.dialogs.message_box import MessageBox
from calibre.utils.config import prefs

import calibre_plugins.count_pages.config as cfg
from calibre_plugins.count_pages.common_dialogs import SizePersistedDialog
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

def authors_to_string(authors):
    if authors is not None:
        return ' & '.join([a.replace('&', '&&') for a in authors if a])
    else:
        return ''

class QueueProgressDialog(QProgressDialog):

    def __init__(self, gui, book_ids, tdir, statistics_cols_map,
                 pages_algorithm, custom_chars_per_page, overwrite_existing, use_preferred_output,
                 icu_wordcount, queue, db, page_count_mode='Estimate', download_source=None):
        QProgressDialog.__init__(self, _('Working')+'...', _('Cancel'), 0, len(book_ids), gui)
        self.setWindowTitle(_('Queueing books for counting statistics'))
        self.setMinimumWidth(500)
        self.book_ids, self.tdir, self.queue, self.db = book_ids, tdir, queue, db
        self.statistics_cols_map = statistics_cols_map
        self.pages_algorithm = pages_algorithm
        self.page_count_mode = page_count_mode
        self.download_source = download_source
        self.custom_chars_per_page = custom_chars_per_page
        self.overwrite_existing = overwrite_existing
        self.use_preferred_output = use_preferred_output
        self.icu_wordcount = icu_wordcount
        self.gui = gui
        self.i, self.books_to_scan = 0, []
        self.bad = OrderedDict()
        self.warnings = []
        self.input_order = []
        if self.use_preferred_output:
            self.input_order.append(prefs['output_format'])
        self.input_order += [f.lower() for f in prefs['input_format_order']]

        self.page_col_label = self.word_col_label = None
        self.labels_map = dict((col_name, db.field_metadata.key_to_label(col_name))
                               for col_name in statistics_cols_map.values() if col_name)

         # QTimer workaround on Win 10 on first go for Win10/Qt6 users not displaying dialog properly.
        QTimer.singleShot(100, self.do_book)
        self.exec_()

    def _getTitleAuthor(self, book_id):
        title = self.db.title(book_id, index_is_id=True)
        authors = self.db.authors(book_id, index_is_id=True)
        if authors:
            authors = [x.replace('|', ',') for x in authors.split(',')]
            title += ' - ' + authors_to_string(authors)
        return title

    def do_book(self):
        book_id = self.book_ids[self.i]
        self.i += 1
        try:
            self._prepare_book(book_id)
        except:
            traceback.print_exc()
            self.bad[book_id] = traceback.format_exc()

        self.setValue(self.i)
        if self.i >= len(self.book_ids):
            return self.do_queue()
        else:
            QTimer.singleShot(0, self.do_book)

    def _prepare_book(self, book_id):
        title_author = self._getTitleAuthor(book_id)
        book_formats = get_available_formats_for_book(self.db, book_id)

        # We have a set of configured custom columns indicating the set of possible stats to run.
        # For each of those statistics, evaluate whether it should be recalculated for this book.
        statistics_to_run = []
        for statistic, col_name in self.statistics_cols_map.items():
            if not col_name:
                continue
            # Special case for the Adobe page count algorithm - requires an EPUB.
            if statistic == cfg.STATISTIC_PAGE_COUNT and self.pages_algorithm == 2 and 'epub' not in book_formats \
                and not self.page_count_mode == 'Download':
                self.warnings.append((book_id, _('ADOBE page count requires EPUB format')))
                continue
            lbl = self.labels_map[col_name]
            # If user is not overwriting existing stats and we have a value for this stat then we won't include it.
            existing_val = self.db.get_custom(book_id, label=lbl, index_is_id=True)
            if self.overwrite_existing or existing_val is None or existing_val == 0:
                statistics_to_run.append(statistic)

        if not self.overwrite_existing and not statistics_to_run:
            # Since we are not forcing overwriting an existing value we need
            # to check whether this book has an existing value in each column.
            # No point in performing statistics if book already has values.
            self.bad[book_id] = _('Book already has all statistics and overwrite is turned off')
            return

        download_sources = []
        if self.page_count_mode == 'Download' and cfg.STATISTIC_PAGE_COUNT in statistics_to_run:
            # We will be attempting to download a page count from a website.
            identifiers = self.db.get_identifiers(book_id, index_is_id=True)
            if self.download_source:
                # Download from this specific website
                identifier = identifiers.get(cfg.PAGE_DOWNLOADS[self.download_source]['id'], None)
                if identifier:
                    download_sources.append((self.download_source, identifier))
            else:
                # Attempt to download from configured websites or first that has a matching identifier.
                c = cfg.plugin_prefs[cfg.STORE_NAME]
                configured_download_sources = c.get(cfg.KEY_DOWNLOAD_SOURCES, cfg.DEFAULT_STORE_VALUES[cfg.KEY_DOWNLOAD_SOURCES])
                check_all_sources = c.get(cfg.KEY_CHECK_ALL_SOURCES, cfg.DEFAULT_STORE_VALUES[cfg.KEY_CHECK_ALL_SOURCES])
                for download_source in configured_download_sources:
                    if download_source[1]: # Whether source is to be used
                        identifier = identifiers.get(cfg.PAGE_DOWNLOADS[download_source[0]]['id'], None)
                        if identifier:
                            download_sources.append((download_source[0], identifier))
                            if not check_all_sources:
                                break
            if not len(download_sources):
                # No point in continuing with this book
                self.warnings.append((book_id, _('No identifiers for selected download sources')))
                return
            if len(statistics_to_run) == 1:
                # Since not counting anything else, we have all we need at this point to continue
                self.books_to_scan.append((book_id, title_author, None,
                                            download_sources, statistics_to_run))
                return

        found_format = False
        input_formats = [f for f in self.input_order if f in book_formats]
        for bf in input_formats:
            # Special case for the Adobe page count algorithm - only EPUB format can be analysed.
            if bf != 'epub' and cfg.STATISTIC_PAGE_COUNT in statistics_to_run and self.pages_algorithm == 2:
                continue
            if self.db.has_format(book_id, bf, index_is_id=True):
                self.setLabelText(_('Queueing ')+title_author)
                try:
                    # Copy the book to the temp directory, using book id as filename
                    dest_file = os.path.join(self.tdir, '%d.%s'%(book_id, bf.lower()))
                    with open(dest_file, 'w+b') as f:
                        self.db.copy_format_to(book_id, bf, f, index_is_id=True)
                    self.books_to_scan.append((book_id, title_author, dest_file,
                                                download_sources, statistics_to_run))
                    found_format = True
                    print("For book '%s', using format %s" % (title_author, bf))
                except:
                    traceback.print_exc()
                    self.bad[book_id] = traceback.format_exc()
                # Either found a format or book is bad - stop looking through formats
                break

        # If we didn't find a compatible format, did we absolutely need one?
        # If we are doing a page count using downloads, we should still allow that to go ahead
        if not found_format:
            if len(download_sources) > 0:
                self.warnings.append((book_id, _('No format found for word count, but page count download will be attempted')))
                self.books_to_scan.append((book_id, title_author, None,
                                            download_sources, statistics_to_run))
            else:
                self.bad[book_id] = _('No convertible format found')

    def do_queue(self):
        self.hide()
        res = []
        distinct_problem_ids = {}
        msg = ''
        for book_id, warning in self.warnings:
            if book_id not in distinct_problem_ids:
                distinct_problem_ids[book_id] = True
            title_author = self._getTitleAuthor(book_id)
            res.append('%s (%s)'%(title_author, warning))
        if len(self.bad):
            for book_id, error in self.bad.items():
                if book_id not in distinct_problem_ids:
                    distinct_problem_ids[book_id] = True
                title_author = self._getTitleAuthor(book_id)
                res.append('%s (%s)'%(title_author, error))
        msg = msg + '\n'.join(res)
        if len(res) > 0:
            summary_msg = _('Could not analyse some statistics in %d of %d books, for reasons shown in details below.')
            warning_dialog(self.gui, _('Page/word/statistics warnings'),
                summary_msg % (len(distinct_problem_ids), len(self.book_ids)), msg).exec_()
        self.gui = None
        # Queue a job to process these books
        self.queue(self.tdir, self.books_to_scan, self.statistics_cols_map,
                   self.pages_algorithm, self.custom_chars_per_page, self.icu_wordcount, self.page_count_mode, self.download_source)

class TotalSummaryDialog(MessageBox): # {{{

    def __init__(self, parent, title, msg):
        '''
        A modal popup that shows the totals of statistics.

        :param log: An HTML or plain text log
        :param title: The title for this popup
        :param msg: The msg to display
        :param det_msg: Detailed message
        '''
        MessageBox.__init__(self, MessageBox.INFO, title, msg,
                show_copy_button=False, parent=parent)

class TotalStatisticsDialog(SizePersistedDialog):

    def __init__(self, parent, totals, averages):
        SizePersistedDialog.__init__(self, parent, 'count pages plugin:total statistics dialog')
        self.initialize_controls()
        self.populate_table(totals, averages)

    def initialize_controls(self):
        self.setWindowTitle(_('Statistic Totals'))
        layout = QVBoxLayout(self)
        self.setMinimumSize(400, 120)

        # Add a table with 3 columns - Statistic, Total, Average
        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([_('Statistic'), _('Total'), _('Average')])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)
        
        # Add a close button
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def populate_table(self, totals, averages):
        self.table.setRowCount(len(totals))
        row = 0
        for statistic, total in totals.items():
            # Statistic column
            self.table.setItem(row, 0, QTableWidgetItem(cfg.DISPLAY_STATISTIC_NAMES[statistic]))
            
            # Total column
            total_item = QTableWidgetItem(f"{total:,.0f}" if total >= 0 else "-")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 1, total_item)
            
            # Average column
            if statistic in averages:
                avg = averages[statistic]
                avg_item = QTableWidgetItem(f"{avg:,.0f}")
            else:
                avg_item = QTableWidgetItem("-")
            avg_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 2, avg_item)
            
            row += 1
        self.table.resizeColumnsToContents()
