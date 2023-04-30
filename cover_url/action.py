from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from functools import partial
try:
    from qt.core import QToolButton, QMenu
except ImportError:
    from PyQt5.Qt import QToolButton, QMenu

# Pull in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.gui2 import error_dialog, question_dialog, Dispatcher
from calibre.gui2.actions import InterfaceAction

import calibre_plugins.cover_url.config as cfg
from calibre_plugins.cover_url.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.cover_url.common_menus import unregister_menu_actions, create_menu_action_unique
from calibre_plugins.cover_url.common_dialogs import ProgressBarDialog
from calibre_plugins.cover_url.jobs import start_download_threaded, get_job_details

PLUGIN_ICONS = ['images/cover_url.png']

class CoverUrlAction(InterfaceAction):

    name = 'Cover Url'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (_('Cover URL'), None, _('Get cover urls from Goodreads into a custom column'), ())
    popup_type = QToolButton.MenuButtonPopup
    action_type = 'current'
    dont_add_to = frozenset(['context-menu-device'])

    def genesis(self):
        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)

        # Assign our menu to this action and an icon
        self.menu = QMenu(self.gui)
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.qaction.triggered.connect(self.get_covers)
        self.menu.aboutToShow.connect(self.about_to_show_menu)

    def about_to_show_menu(self):
        self.rebuild_menus()

    def rebuild_menus(self):
        # Ensure any keyboard shortcuts from previous display of plugin menu are cleared
        unregister_menu_actions(self)

        m = self.menu
        m.clear()
        
        create_menu_action_unique(self, m, _('&Get Goodreads Covers'), 'images/cover_url.png',
                                  triggered=partial(self.get_covers))
        m.addSeparator()
        create_menu_action_unique(self, m, _('&Customize plugin')+'...', 'config.png',
                                  shortcut=False, triggered=self.show_configuration)
        self.gui.keyboard.finalize()

    def get_covers(self):
        db = self.gui.current_db
        library_config = cfg.get_library_config(db)
        custom_cols = db.field_metadata.custom_field_metadata()
        gcover_col_name = library_config.get(cfg.KEY_COL_GCOVER, cfg.DEFAULT_LIBRARY_VALUES[cfg.KEY_COL_GCOVER])
        interval = library_config.get(cfg.KEY_INTERVAL, cfg.DEFAULT_LIBRARY_VALUES[cfg.KEY_INTERVAL])
        is_valid_gcols = (len(gcover_col_name) > 0 and gcover_col_name in custom_cols)
        if not is_valid_gcols:
            if not question_dialog(self.gui, _('Configure plugin'), '<p>'+
                _('You must specify a custom column first. Do you want to configure this now?'),
                show_copy_button=False):
                return
            self.show_configuration()
            return

        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return
        book_ids = self.gui.library_view.get_selected_ids()

        # Retrieve the covers with a cancellable dialog
        start_download_threaded(self.gui, book_ids, interval, Dispatcher(self._get_covers_complete))

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def _get_covers_complete(self, job):
        if job.failed:
            self.gui.job_exception(job, dialog_title=_('Failed to download covers'))
            return
        updated_ids, failed_ids, det_msg = get_job_details(job)
        self.gui.status_bar.show_message(_('Download covers completed'), 3000)

        msg = ''
        update_count = len(updated_ids)
        if update_count > 0:
            msg = '<p>'+_('Downloaded covers for <b>%d book(s)</b>.') % update_count +' '+ \
                  _('Proceed with updating your library?')

        if failed_ids:
            if failed_ids:
                msg += '<p>'+_('Could not find covers for %d book(s).') % len(failed_ids)

        if update_count == 0:
            #return error_dialog(self.gui, _('Download covers failed'), msg, det_msg=det_msg, show=True)
            return

        self._update_covers_column(updated_ids)

    def _update_covers_column(self, updated_ids):
        db = self.gui.current_db

        self.init_progressbar(_('Updating cover urls'), on_top=True)
        total_books = len(updated_ids)
        self.show_progressbar(total_books)
        self.set_progressbar_label(_('Updating'))
        # At this point we want to re-use code in edit_metadata to go ahead and
        # apply the changes. So we will replace the Metadata objects with some
        # empty ones with only the custom column fields set so only that field gets updated
        library_config = cfg.get_library_config(db)
        gcover_col_name = library_config.get(cfg.KEY_COL_GCOVER, '')
        
        db = self.gui.current_db
        db_ref = db.new_api if hasattr(db, 'new_api') else db
        book_ids_to_update = []
        book_values_map = dict()
        for book_id, gcover in updated_ids:
            if db_ref.has_id(book_id):
                self.set_progressbar_label(_('Updating') + ' ' + db_ref.field_for("title", book_id))
                self.increment_progressbar()
                if gcover:
                    book_values_map[book_id] = gcover
                    book_ids_to_update.append(book_id)
        
        db_ref.set_field(gcover_col_name, book_values_map)
        
        if book_ids_to_update:
            #print("About to refresh GUI - book_ids_to_update=", book_ids_to_update)
            self.gui.library_view.model().refresh_ids(book_ids_to_update)
            self.gui.library_view.model().refresh_ids(book_ids_to_update,
                                      current_row=self.gui.library_view.currentIndex().row())
        
        self.hide_progressbar()

    def init_progressbar(self, window_title, on_top=False):
        self.pb = ProgressBarDialog(parent=self.gui, window_title=window_title, on_top=on_top)
        self.pb.show()

    def show_progressbar(self, maximum_count):
        if self.pb:
            self.pb.set_maximum(maximum_count)
            self.pb.set_value(0)
            self.pb.show()

    def set_progressbar_label(self, label):
        if self.pb:
            self.pb.set_label(label)

    def increment_progressbar(self):
        if self.pb:
            self.pb.increment()

    def hide_progressbar(self):
        if self.pb:
            self.pb.hide()
