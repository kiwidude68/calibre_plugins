from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from functools import partial
try:
    from qt.core import QMenu, QToolButton, QPixmap, Qt
except ImportError:
    from PyQt5.Qt import QMenu, QToolButton, QPixmap, Qt

from calibre.gui2 import pixmap_to_data
from calibre.gui2.actions import InterfaceAction

import calibre_plugins.resize_cover.config as cfg
from calibre_plugins.resize_cover.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.resize_cover.common_menus import (unregister_menu_actions, create_menu_action_unique)

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

PLUGIN_ICONS = ['images/resize_cover.png']

class ResizeCoverAction(InterfaceAction):

    name = 'Resize Cover'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (_('Resize Cover'), None, None, None)
    popup_type = QToolButton.MenuButtonPopup
    action_type = 'current'

    def genesis(self):
        self.menu = QMenu(self.gui)
        self.old_actions_unique_map = {}
        self.default_size_data = None

        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)

        self.rebuild_menus()

        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.qaction.triggered.connect(self.resize_covers_pressed)
        self.menu.aboutToShow.connect(self.about_to_show_menu)

    def about_to_show_menu(self):
        self.rebuild_menus()

    def rebuild_menus(self):
        # Ensure any keyboard shortcuts from previous display of plugin menu are cleared
        unregister_menu_actions(self)

        c = cfg.plugin_prefs[cfg.STORE_NAME]
        size_data_items = c[cfg.KEY_SIZES]
        m = self.menu
        m.clear()

        for size_data in size_data_items:
            keep_aspect_ratio = size_data.get(cfg.KEY_KEEP_ASPECT_RATIO, cfg.DEFAULT_STORE_VALUES[cfg.KEY_KEEP_ASPECT_RATIO])
            only_shrink = size_data.get(cfg.KEY_ONLY_SHRINK, cfg.DEFAULT_STORE_VALUES[cfg.KEY_ONLY_SHRINK])
            menu_text = _('Size: {0}(w) x {1}(h)').format(size_data[cfg.KEY_WIDTH], size_data[cfg.KEY_HEIGHT])
            menu_options = []
            if keep_aspect_ratio:
                menu_options.append(_('Keep aspect ratio'))
            if only_shrink:
                menu_options.append(_('Only shrink'))
            if len(menu_options) > 0:
                menu_text = menu_text + ' - ' + ', '.join(menu_options)
            is_default = bool(size_data[cfg.KEY_DEFAULT])
            ac = create_menu_action_unique(self, m, menu_text, is_checked=is_default,
                                           triggered=partial(self.resize_covers, size_data[cfg.KEY_WIDTH], size_data[cfg.KEY_HEIGHT], keep_aspect_ratio, only_shrink))

            if is_default:
                self.default_size_data = size_data
        m.addSeparator()
        create_menu_action_unique(self, m, _('&Customize plugin')+'...', 'config.png',
                                  shortcut=False, triggered=self.show_configuration)
        create_menu_action_unique(self, m, _('&Help'), 'help.png',
                                  shortcut=False, triggered=cfg.show_help)
        self.gui.keyboard.finalize()

    def resize_covers_pressed(self, clicked):
        if self.default_size_data is not None:
            width = self.default_size_data[cfg.KEY_WIDTH]
            height = self.default_size_data[cfg.KEY_HEIGHT]
            keep_aspect_ratio = self.default_size_data.get(cfg.KEY_KEEP_ASPECT_RATIO, cfg.DEFAULT_STORE_VALUES[cfg.KEY_KEEP_ASPECT_RATIO])
            only_shrink = self.default_size_data.get(cfg.KEY_ONLY_SHRINK, cfg.DEFAULT_STORE_VALUES[cfg.KEY_ONLY_SHRINK])
            self.resize_covers(width, height, keep_aspect_ratio, only_shrink)

    def resize_covers(self, width=None, height=None, keep_aspect_ratio=False, only_shrink=False):
        #print("Resize Covers::resize_covers - width=%s, height=%s, keep_aspect_ratio=%s, only_shrink=%s" % (width, height, keep_aspect_ratio, only_shrink))
        if width is None or height is None:
            return
        rows = self.gui.library_view.selectionModel().selectedRows()
        if rows is None or len(rows) == 0:
            return
        current_idx = self.gui.library_view.currentIndex()
        db = self.gui.library_view.model().db
        ids = set(self.gui.library_view.get_selected_ids())
        options = cfg.plugin_prefs[cfg.STORE_NAME]
        only_if_width_smaller = options.get(cfg.KEY_ONLY_IF_WIDTH_SMALLER, cfg.DEFAULT_STORE_VALUES[cfg.KEY_ONLY_IF_WIDTH_SMALLER])
        width_threshold = options.get(cfg.KEY_WIDTH_THRESHOLD, cfg.DEFAULT_STORE_VALUES[cfg.KEY_WIDTH_THRESHOLD])
        only_if_height_smaller = options.get(cfg.KEY_ONLY_IF_HEIGHT_SMALLER, cfg.DEFAULT_STORE_VALUES[cfg.KEY_ONLY_IF_HEIGHT_SMALLER])
        height_threshold = options.get(cfg.KEY_HEIGHT_THRESHOLD, cfg.DEFAULT_STORE_VALUES[cfg.KEY_HEIGHT_THRESHOLD])
        only_if_width_greater = options.get(cfg.KEY_ONLY_IF_WIDTH_GREATER, cfg.DEFAULT_STORE_VALUES[cfg.KEY_ONLY_IF_WIDTH_GREATER])
        width_minimum = options.get(cfg.KEY_WIDTH_MINIMUM, cfg.DEFAULT_STORE_VALUES[cfg.KEY_WIDTH_MINIMUM])
        only_if_height_greater = options.get(cfg.KEY_ONLY_IF_HEIGHT_GREATER, cfg.DEFAULT_STORE_VALUES[cfg.KEY_ONLY_IF_HEIGHT_GREATER])
        height_minimum = options.get(cfg.KEY_HEIGHT_MINIMUM, cfg.DEFAULT_STORE_VALUES[cfg.KEY_HEIGHT_MINIMUM])
        resized_ids = []
        for book_id in ids:
            if db.has_cover(book_id):
                cover = db.cover(book_id, index_is_id=True)
                updated_cover = self.resize_cover_for_book(
                    cover, width, height, keep_aspect_ratio, only_shrink,
                    only_if_width_smaller, width_threshold,
                    only_if_height_smaller, height_threshold,
                    only_if_width_greater, width_minimum,
                    only_if_height_greater, height_minimum)
                if updated_cover is not None:
                    db.set_cover(book_id, updated_cover)
                    resized_ids.append(book_id)

        if len(resized_ids) == 0:
            self.gui.status_bar.show_message(_('No selected covers met the resize conditions'), 3000)
            return

        self.gui.library_view.model().refresh_ids(resized_ids)
        self.gui.library_view.model().current_changed(current_idx, current_idx)
        if self.gui.cover_flow:
            self.gui.cover_flow.dataChanged()


    def resize_cover_for_book(self, cover, width, height, keep_aspect_ratio, only_shrink,
                              only_if_width_smaller, width_threshold,
                              only_if_height_smaller, height_threshold,
                              only_if_width_greater, width_minimum,
                              only_if_height_greater, height_minimum):
        cover_pixmap = QPixmap()
        cover_pixmap.loadFromData(cover)
        org_width = cover_pixmap.width()
        org_height = cover_pixmap.height()

        if only_shrink and not (width < org_width or height < org_height):
            return None

        resize_conditions = []
        if only_if_width_smaller:
            resize_conditions.append(org_width < width_threshold)
        if only_if_height_smaller:
            resize_conditions.append(org_height < height_threshold)
        if only_if_width_greater:
            resize_conditions.append(org_width > width_minimum)
        if only_if_height_greater:
            resize_conditions.append(org_height > height_minimum)
        if resize_conditions and not any(resize_conditions):
            return None

        if keep_aspect_ratio:
            cover_pixmap = cover_pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            cover_pixmap = cover_pixmap.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        return pixmap_to_data(cover_pixmap)

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)
