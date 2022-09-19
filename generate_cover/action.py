from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

import six
import os
from calibre.constants import DEBUG
from calibre.gui2 import error_dialog
from calibre.gui2.actions import InterfaceAction

import calibre_plugins.generate_cover.config as cfg
from calibre_plugins.generate_cover.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.generate_cover.dialogs import CoverOptionsDialog, GenerateCoverProgressDialog
from calibre_plugins.generate_cover.draw import generate_cover_for_book

PLUGIN_ICONS = ['images/generate_cover.png', 'images/rename.png',
                'images/import.png', 'images/export.png']

class GenerateCoverAction(InterfaceAction):

    name = 'Generate Cover'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (_('Generate Cover'), None, _('Generate a customised cover'), ())
    action_type = 'current'
    dont_add_to = frozenset(['context-menu-device'])

    def genesis(self):
        self.is_library_selected = True
        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)

        # Assign our menu to this action and an icon
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.qaction.triggered.connect(self._generate_cover)

        self.images_dir = cfg.get_images_dir()
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)

    def location_selected(self, loc):
        self.is_library_selected = loc == 'library'

    def _generate_cover(self):
        if not self.is_library_selected:
            return

        # Do a comparison to see if the config files have become corrupted.
        self._check_corrupted_config()

        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return error_dialog(self.gui, _('Cannot generate covers'),
                                _('No books selected'), show=True)

        books = self._get_selected_books(rows)
        is_multiple_books = len(books) > 1
        d = CoverOptionsDialog(self, self.images_dir, books[0], is_multiple_books)
        d.exec_()

        if d.result() != d.Accepted:
            return

        current_idx = self.gui.library_view.currentIndex()
        db = self.gui.library_view.model().db
        GenerateCoverProgressDialog(self.gui, books, db)
        self.gui.library_view.model().current_changed(current_idx, current_idx)
        if self.gui.cover_flow:
            self.gui.cover_flow.dataChanged()

    def _check_corrupted_config(self):
        failures = []
        saved_settings = cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]
        for setting_name, setting in six.iteritems(saved_settings):
            if setting_name != setting[cfg.KEY_NAME]:
                failures.append(_('Corrupted setting: "%s" has incorrect internal name of: "%s")')%(setting_name, setting[cfg.KEY_NAME]))
                setting[cfg.KEY_NAME] = setting_name
        if len(failures):
            cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS] = saved_settings
            return error_dialog(self.gui, _('Corrupted Configuration File'),
                                _('<p>Your configuration file was corrupted (see Details).</p>)'
                                  '<p>Please report your exact recent actions which led to this '
                                  'on the MobileRead forum thread for this plugin so it can be fixed.</p>'
                                  '<p>The configuration has been fixed automatically.</p>'),
                                det_msg='\n'.join(failures), show=True)

    def _get_selected_books(self, rows):
        db = self.gui.library_view.model().db
        idxs = [row.row() for row in rows]
        books = []
        for idx in idxs:
            mi = db.get_metadata(idx)
            books.append(mi)
        return books

    def get_saved_setting_names(self):
        '''
        This method is designed to be called from other plugins
        It is a convenience wrapper to return a sorted list of saved cover profile setting names
        Returns a list of strings representing the setting names
        '''
        settings = cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]
        sorted_keys = sorted(settings.keys())
        sorted_keys.remove(cfg.KEY_DEFAULT)
        sorted_keys.insert(0, cfg.KEY_DEFAULT)
        return sorted_keys

    def generate_cover_for_book(self, mi, saved_setting_name=None, path_to_cover=None):
        '''
        This method is designed to be called from other plugins
        It is a convenience wrapper to generate a cover for the specified book to a path.
        The caller must take responsibility for updating the UI to ensure the book details panel
        and cover flow if visible are updated if overwriting a book's cover (see _generate_cover above).

        mi                 - the metadata object for the book to convert. e.g. db.get_metadata(idx)
        saved_setting_name - the saved cover profile name within this plugin to use
                             if not specified uses the last cover settings of the plugin
        path_to_cover      - the absolute filepath for where to write the cover image
                             if not specified overwrites the image in the calibre library for this book

        {Return value}     - the Magick image object, None if operation aborted
        '''
        if not mi:
            if DEBUG:
                print('Generate Cover Error: Missing mi parameter in call to generate_cover_for_book')
            if getattr(self, 'gui', None):
                return error_dialog(self.gui, _('Cannot generate cover'),
                                    _('Missing metadata passed for book to generate cover'), show=True)
            return None

        options = cfg.plugin_prefs[cfg.STORE_CURRENT]
        if saved_setting_name:
            if saved_setting_name not in cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]:
                if DEBUG:
                    print('Generate Cover Error: Saved setting %s not found in generate_cover_for_book'%saved_setting_name)
                if getattr(self, 'gui', None):
                    return error_dialog(self.gui, _('Cannot generate cover'),
                                        _('No cover settings exist named: "%s"')%saved_setting_name, show=True)
                return None
            options = cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS][saved_setting_name]

        db = self.gui.current_db
        if path_to_cover:
            mi._path_to_cover = path_to_cover

        cover_data = generate_cover_for_book(mi, options=options, db=db.new_api)

        if not path_to_cover and db:
            # Overwrite the cover for this particular book
            db.set_cover(mi.id, cover_data)
        else:
            # The caller wants the cover written to a specific location
            if callable(getattr(cover_data, 'read', None)):
                cover_data = cover_data.read()
            from calibre.utils.magick.draw import save_cover_data_to
            save_cover_data_to(cover_data, path_to_cover)

        return cover_data
