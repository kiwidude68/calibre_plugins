from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from calibre.ebooks.metadata import authors_to_string
from calibre.ebooks.metadata.book.base import Metadata
from calibre.gui2 import error_dialog, question_dialog, Dispatcher
from calibre.gui2.actions import InterfaceAction
from calibre.gui2.dialogs.message_box import ErrorNotification

import calibre_plugins.extract_isbn.config as cfg
from calibre_plugins.extract_isbn.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.extract_isbn.dialogs import QueueProgressDialog
from calibre_plugins.extract_isbn.jobs import (start_extract_threaded, get_job_details)

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

PLUGIN_ICONS = ['images/extract_isbn.png']

class ExtractISBNAction(InterfaceAction):

    name = 'Extract ISBN'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (_('Extract ISBN'), None, _('Extract ISBN from the selected book format'), ())
    action_type = 'current'

    def genesis(self):
        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)

        # Assign our menu to this action and an icon
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.qaction.triggered.connect(self.scan_for_isbns)

    def scan_for_isbns(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return error_dialog(self.gui, _('No rows selected'),
                                _('You must select one or more books to perform this action.'), show=True)
        book_ids = self.gui.library_view.get_selected_ids()
        db = self.gui.library_view.model().db

        c = cfg.plugin_prefs[cfg.STORE_NAME]
        worker_threshold = c.get(cfg.KEY_WORKER_THRESHOLD, cfg.DEFAULT_STORE_VALUES[cfg.KEY_WORKER_THRESHOLD])
        if len(book_ids) > worker_threshold:
            # Run the extraction as a background job with workers
            QueueProgressDialog(self.gui, book_ids, self._queue_job, db)
        else:
            # For performance reasons, still do single book extraction as a threaded
            # job in-process
            start_extract_threaded(self.gui, book_ids, Dispatcher(self._scan_for_isbns_complete))

    def _queue_job(self, books_to_scan, failed_ids, no_format_ids):
        '''
        For use when running as a background job with workers
        '''
        c = cfg.plugin_prefs[cfg.STORE_NAME]
        batch_size = c.get(cfg.KEY_BATCH_SIZE, cfg.DEFAULT_STORE_VALUES[cfg.KEY_BATCH_SIZE])
        batches = self._split_jobs(books_to_scan, batch_size)
        for i, batch_ids in enumerate(batches):
            func = 'arbitrary_n'
            cpus = self.gui.job_manager.server.pool_size
            if i > 0:
                # We do not want to report the failed ids in each and every batch
                failed_ids = []
                no_format_ids = []
            args = ['calibre_plugins.extract_isbn.jobs', 'do_extract_worker',
                    (batch_ids, failed_ids, no_format_ids, cpus)]
            desc = _('Extract ISBN')
            self.gui.job_manager.run_job(
                    self.Dispatcher(self._scan_for_isbns_complete), func, args=args,
                        description=desc)
        self.gui.status_bar.show_message(_('Extracting ISBN for {0} books').format(len(books_to_scan)))

    def _split_jobs(self, ids, batch_size):
        ans = []
        ids = list(ids)
        while ids:
            jids = ids[:batch_size]
            ans.append(jids)
            ids = ids[batch_size:]
        return ans

    def _scan_for_isbns_complete(self, job):
        if job.failed:
            self.gui.job_exception(job, dialog_title=_('Failed to extract isbns'))
            return
        extracted_ids, same_isbn_ids, failed_ids, det_msg = get_job_details(job)
        self.gui.status_bar.show_message(_('ISBN extract completed'), 3000)

        msg = ''
        update_count = len(extracted_ids)
        if update_count > 0:
            msg = '<p>'+_('Extract ISBN found <b>{0} new isbn(s)</b>.').format(update_count) + \
                  " " + _('Proceed with updating your library?')

        show_copy_button = False
        if failed_ids or same_isbn_ids:
            show_copy_button = True
            if failed_ids and same_isbn_ids:
                msg += '<p>'+_('Could not find an ISBN for {0} book(s) and '
                        '{1} book(s) matched their existing value.').format(len(failed_ids),len(same_isbn_ids))
            elif failed_ids:
                msg += '<p>'+_('Could not find an ISBN for {0} book(s).').format(len(failed_ids))
            else:
                msg += '<p>'+_('Found {0} book(s) where ISBN matched the existing value.').format(len(same_isbn_ids))
            msg += " "
            msg += _('Click "Show details" to see which books.')

        if update_count == 0:
            p = ErrorNotification(job.html_details, _('Scan log'), _('Scan failed'), msg,
                    det_msg=det_msg, show_copy_button=True, parent=self.gui)
            p.show()
        else:
            payload = (extracted_ids, same_isbn_ids, failed_ids)
            self.gui.proceed_question(self._check_proceed_with_extracted_isbns,
                    payload, job.html_details,
                    _('Scan log'), _('Scan complete'), msg,
                    det_msg=det_msg, show_copy_button=show_copy_button)

    def _check_proceed_with_extracted_isbns(self, payload):
        extracted_ids, _same_isbn_ids, _failed_ids = payload
        modified = set()
        db = self.gui.current_db

        for i, title, last_modified, isbn in extracted_ids:
            lm = db.metadata_last_modified(i, index_is_id=True)
            if lm > last_modified:
                title = db.title(i, index_is_id=True)
                authors = db.authors(i, index_is_id=True)
                if authors:
                    authors = [x.replace('|', ',') for x in authors.split(',')]
                    title += ' - ' + authors_to_string(authors)
                modified.add(title)

        if modified:
            from calibre.utils.icu import lower

            modified = sorted(modified, key=lower)
            if not question_dialog(self.gui, _('Some books changed'), '<p>'+
                    _('The metadata for some books in your library has'
                        ' changed since you started the download. If you'
                        ' proceed, some of those changes may be overwritten. '
                        'Click "Show details" to see the list of changed books. '
                        'Do you want to proceed?'), det_msg='\n'.join(modified)):
                return
        # At this point we want to re-use code in edit_metadata to go ahead and
        # apply the changes. So we will replace the Metadata objects with some
        # empty ones with only the isbn field set so only that field gets updated
        id_map = {}
        for i, title, last_modified, isbn in extracted_ids:
            mi = Metadata(_('Unknown'))
            mi.isbn = isbn
            id_map[i] = mi
        edit_metadata_action = self.gui.iactions['Edit Metadata']
        edit_metadata_action.apply_metadata_changes(id_map,
                                                    callback=self._mark_and_display_results)

    def _mark_and_display_results(self, applied_ids):
        marked_ids = {}
        for book_id in applied_ids:
            marked_ids[book_id] = 'isbn_updated'
        self.gui.current_db.set_marked_ids(marked_ids)
        action = cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_POST_TASK, 'none')
        if action == 'updated' and len(applied_ids) > 0:
            self.gui.search.set_search_string('marked:isbn_updated')
