from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import QMenu, QToolButton
except ImportError:
    from PyQt5.Qt import QMenu, QToolButton

# Pull in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from functools import partial
from calibre.ebooks.metadata.book.base import Metadata
from calibre.gui2 import error_dialog, question_dialog, Dispatcher
from calibre.gui2.actions import InterfaceAction
from calibre.gui2.dialogs.message_box import ProceedNotification

import calibre_plugins.ratings.config as cfg
from calibre_plugins.ratings.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.ratings.common_menus import unregister_menu_actions, create_menu_action_unique
from calibre_plugins.ratings.jobs import start_download_threaded, get_job_details

PLUGIN_ICONS = ['images/ratings.png','images/amazon.png','images/goodreads.png']

class RatingsAction(InterfaceAction):

    name = 'Ratings'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (_('Ratings'), None, _('Get the rating and counts from Amazon/Goodreads.com'), None)
    action_type = 'current'

    def genesis(self):
        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)
        self.menu = QMenu(self.gui)

        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.qaction.triggered.connect(partial(self.get_rating, include_amazon=True, include_goodreads=True))

    def initialization_complete(self):
        # Must have access to self.gui.current_db to identify cols configured
        self.rebuild_menus()
        # Setup hooks so that we rebuild the dropdown menus each time to represent latest config
        self.menu.aboutToShow.connect(self.rebuild_menus)

    def library_changed(self, db):
        # We need to revalidate which menu options to show after switching libraries
        self.rebuild_menus()

    def rebuild_menus(self):
        # Ensure any keyboard shortcuts from previous display of plugin menu are cleared
        unregister_menu_actions(self)

        m = self.menu
        m.clear()
        (is_valid_acols, is_valid_gcols) = self.get_configured_cols()
        if is_valid_acols and is_valid_gcols:
            create_menu_action_unique(self, m, _('&Get all ratings'), 
                            tooltip=_('Download ratings for all configured sources'),
                            triggered=partial(self.get_rating, include_amazon=True, include_goodreads=True))
            m.addSeparator()
        if is_valid_acols:
            create_menu_action_unique(self, m, _('&Get Amazon ratings'), image=PLUGIN_ICONS[1],
                            tooltip=_('Download ratings for Amazon only'),
                            triggered=partial(self.get_rating, include_amazon=True))
        if is_valid_gcols:
            create_menu_action_unique(self, m, _('&Get Goodreads ratings'), image=PLUGIN_ICONS[2], 
                            tooltip=_('Download ratings for Goodreads only'),
                            triggered=partial(self.get_rating, include_goodreads=True))
        if is_valid_acols or is_valid_gcols:
            m.addSeparator()
        create_menu_action_unique(self, m, _('&Customize plugin')+'...', 'config.png',
                                  shortcut=False, triggered=self.show_configuration)
        self.gui.keyboard.finalize()

    def get_configured_cols(self):
        db = self.gui.current_db
        library_config = cfg.get_library_config(db)
        arating_col_name = library_config.get(cfg.KEY_COL_ARATING, '')
        arating_count_col_name = library_config.get(cfg.KEY_COL_ARATING_COUNT, '')
        grating_col_name = library_config.get(cfg.KEY_COL_GRATING, '')
        grating_count_col_name = library_config.get(cfg.KEY_COL_GRATING_COUNT, '')
        
        custom_cols = db.field_metadata.custom_field_metadata()
        is_valid_acols = (len(arating_col_name) > 0 and arating_col_name in custom_cols) \
                        or (len(arating_count_col_name) > 0 and arating_count_col_name in custom_cols)
        is_valid_gcols = (len(grating_col_name) > 0 and grating_col_name in custom_cols) \
                        or (len(grating_count_col_name) > 0 and grating_count_col_name in custom_cols)
        return (is_valid_acols, is_valid_gcols)

    def get_rating(self, include_amazon=False, include_goodreads=False):
        (is_valid_acols, is_valid_gcols) = self.get_configured_cols()
        if not is_valid_acols and not is_valid_gcols:
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
            
        if not is_valid_acols:
            include_amazon = False
        if not is_valid_gcols:
            include_goodreads = False
        # Retrieve the ratings with a cancellable dialog
        start_download_threaded(self.gui, book_ids, include_amazon, include_goodreads, \
            Dispatcher(self._get_rating_complete))

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def _get_rating_complete(self, job):
        if job.failed:
            self.gui.job_exception(job, dialog_title=_('Failed to download ratings'))
            return
        updated_ids, failed_ids, det_msg = get_job_details(job)
        self.gui.status_bar.show_message(_('Download ratings completed'), 3000)

        msg = ''
        update_count = len(updated_ids)
        if update_count > 0:
            msg = '<p>'+_('Downloaded ratings for <b>%d book(s)</b>.')% update_count + ' ' + \
                  _('Proceed with updating your library?')

        show_copy_button = False
        if failed_ids:
            show_copy_button = True
            if failed_ids:
                msg += '<p>'+_('Could not find ratings for %d book(s).') % len(failed_ids)

        if update_count == 0:
            return error_dialog(self.gui, _('Download ratings failed'), msg, det_msg=det_msg, show=True)

        payload = updated_ids
        p = ProceedNotification(self._check_proceed_with_ratings,
                payload, job.html_details,
                _('Download log'), _('Download ratings complete'), msg,
                det_msg=det_msg, show_copy_button=show_copy_button,
                parent=self.gui)
        p.show()

    def _check_proceed_with_ratings(self, payload):
        updated_ids = payload
        db = self.gui.current_db

        # At this point we want to re-use code in edit_metadata to go ahead and
        # apply the changes. So we will replace the Metadata objects with some
        # empty ones with only the custom column fields set so only that field gets updated
        custom_cols = db.field_metadata.custom_field_metadata()

        arating_column = None
        arating_count_column = None
        grating_column = None
        grating_count_column = None
        library_config = cfg.get_library_config(db)
        arating_col_name = library_config.get(cfg.KEY_COL_ARATING, '')
        arating_count_col_name = library_config.get(cfg.KEY_COL_ARATING_COUNT, '')
        grating_col_name = library_config.get(cfg.KEY_COL_GRATING, '')
        grating_count_col_name = library_config.get(cfg.KEY_COL_GRATING_COUNT, '')
        if arating_col_name:
            arating_column = custom_cols[arating_col_name]
        if arating_count_col_name:    
            arating_count_column = custom_cols[arating_count_col_name]
        if grating_col_name:
            grating_column = custom_cols[grating_col_name]
        if grating_count_col_name:    
            grating_count_column = custom_cols[grating_count_col_name]
        id_map = {}
        for i, arating, arating_count, grating, grating_count in updated_ids:
            mi = Metadata(_('Unknown'))
            if arating and arating_col_name:
                arating_column['#value#'] = arating
                mi.set_user_metadata(arating_col_name, arating_column)
            if arating_count and arating_count_col_name:
                arating_count_column['#value#'] = arating_count
                mi.set_user_metadata(arating_count_col_name, arating_count_column)
            if grating and grating_col_name:
                grating_column['#value#'] = grating
                mi.set_user_metadata(grating_col_name, grating_column)
            if grating_count and grating_count_col_name:
                grating_count_column['#value#'] = grating_count
                mi.set_user_metadata(grating_count_col_name, grating_count_column)
            id_map[i] = mi
        edit_metadata_action = self.gui.iactions['Edit Metadata']
        edit_metadata_action.apply_metadata_changes(id_map, callback=self._display_results)

    def _display_results(self, applied_ids):
        if applied_ids:
            self.gui.library_view.model().refresh_ids(applied_ids)
