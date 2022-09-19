from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import os
try:
    from qt.core import QUrl, QModelIndex
except ImportError:
    from PyQt5.Qt import QUrl, QModelIndex

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.gui2 import error_dialog, open_url
from calibre.gui2.actions import InterfaceAction
from calibre.ptempfile import PersistentTemporaryDirectory, remove_dir

import calibre_plugins.modify_epub.config as cfg
from calibre_plugins.modify_epub import ActionModifyEpub
from calibre_plugins.modify_epub.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.modify_epub.dialogs import (ModifyEpubDialog, QueueProgressDialog,
                                                 AddBooksProgressDialog)
from calibre.utils.config import config_dir

PLUGIN_ICONS = ['images/modify_epub.png']

class ModifyEpubAction(InterfaceAction):

    name = 'Modify ePub'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (_('Modify ePub'), None, _('Modify the contents of an ePub without a conversion'), ())
    action_type = 'current'

    def genesis(self):
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.qaction.triggered.connect(self.modify_epub)

    def modify_epub(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return error_dialog(self.gui, _('Cannot modify ePub'),
                _('You must select one or more books to perform this action.'), show=True)

        book_ids = set(self.gui.library_view.get_selected_ids())
        db = self.gui.library_view.model().db
        book_epubs = []
        for book_id in book_ids:
            if db.has_format(book_id, 'EPUB', index_is_id=True):
                book_epubs.append(book_id)

        if not book_epubs:
            return error_dialog(self.gui, _('Cannot modify ePub'),
                    _('No ePub available. First convert the book to ePub.'),
                    show=True)

        # Launch dialog asking user to specify what options to modify
        dlg = ModifyEpubDialog(self.gui, self)
        if dlg.exec_() == dlg.Accepted:
            # Create a temporary directory to copy all the ePubs to while scanning
            tdir = PersistentTemporaryDirectory('_modify_epub', prefix='')
            QueueProgressDialog(self.gui, book_epubs, tdir, dlg.options, self._queue_job, db)

    def _queue_job(self, tdir, options, books_to_modify):
        if not books_to_modify:
            # All failed so cleanup our temp directory
            remove_dir(tdir)
            return

        func = 'arbitrary_n'
        cpus = self.gui.job_manager.server.pool_size
        args = ['calibre_plugins.modify_epub.jobs', 'do_modify_epubs',
                (books_to_modify, options, cpus)]
        desc = 'Modify ePubs version ' + str(ActionModifyEpub.version)
        job = self.gui.job_manager.run_job(
                self.Dispatcher(self._modify_completed), func, args=args,
                    description=desc)
        job._tdir = tdir
        self.gui.status_bar.show_message('Modifying %d books'%len(books_to_modify))

    def _modify_completed(self, job):
        if job.failed:
            self.gui.job_exception(job, dialog_title=_('Failed to modify ePubs'))
            return
        modified_epubs_map = job.result
        self.gui.status_bar.show_message(_('Modify ePub completed'), 3000)

        update_count = len(modified_epubs_map)
        if update_count == 0:
            msg = _("No ePub files were updated. If this isn't what you expected "
                    "then press the Show details button to check for errors in the log.")
            return error_dialog(self.gui, _("Modify ePub changed no files"), msg,
                                show_copy_button=True, show=True,
                                det_msg=job.details)

        payload = (modified_epubs_map, job._tdir)

        if cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_ASK_FOR_CONFIRMATION,
                                                cfg.DEFAULT_STORE_VALUES[cfg.KEY_ASK_FOR_CONFIRMATION]):
            msg = '<p>'+_('Modify ePub modified <b>%d ePub files(s)</b> into a temporary location. '
                   'Proceed with replacing the versions in your library?') % update_count

            self.gui.proceed_question(self._proceed_with_updating_epubs,
                payload, job.details,
                _('Modify log'), _('Modify ePub complete'), msg,
                show_copy_button=False,
                cancel_callback=self._cancel_updating_epubs)
        else:
            self._proceed_with_updating_epubs(payload)


    def _proceed_with_updating_epubs(self, payload):
        modified_epubs_map, tdir = payload
        AddBooksProgressDialog(self.gui, modified_epubs_map, tdir)
        self.gui.tags_view.recount()
        if self.gui.current_view() is self.gui.library_view:
            current = self.gui.library_view.currentIndex()
            if current.isValid():
                self.gui.library_view.model().current_changed(current, QModelIndex())

    def _cancel_updating_epubs(self, payload):
        _modified_epubs_map, tdir = payload
        # All failed so cleanup our temp directory
        remove_dir(tdir)

    def show_help(self):
        # Extract on demand the help file resource
        def get_help_file_resource():
            # We will write the help file out every time, in case the user upgrades the plugin zip
            # and there is a later help file contained within it.
            HELP_FILE = 'Modify ePub Help.html'
            file_path = os.path.join(config_dir, 'plugins', HELP_FILE)
            file_data = self.load_resources(HELP_FILE)[HELP_FILE]
            with open(file_path,'wb') as f:
                f.write(file_data)
            return file_path
        url = 'file:///' + get_help_file_resource()
        open_url(QUrl(url))

