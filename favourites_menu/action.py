from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import weakref
from six import text_type as unicode

try:
    from qt.core import (QToolButton, QMenu, QAction)
except ImportError:
    from PyQt5.Qt import (QToolButton, QMenu, QAction)

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.gui2.actions import InterfaceAction

import calibre_plugins.favourites_menu.config as cfg
from calibre_plugins.favourites_menu.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.favourites_menu.common_menus import unregister_menu_actions, create_menu_action_unique

PLUGIN_ICONS = ['images/favourites_menu.png']

class ActionWrapper(QAction):

    def __init__(self, orig_action, parent=None):
        QAction.__init__(self, orig_action.icon(), orig_action.text(), parent)
        if orig_action.isCheckable():
            self.setCheckable(True)
            self.setChecked(orig_action.isChecked())
            self.toggled.connect(self.toggle_orig)
        self.setEnabled(orig_action.isEnabled())
        self.setVisible(orig_action.isVisible())
        self.setToolTip(orig_action.toolTip())
        self.orig = weakref.ref(orig_action)
        self.triggered.connect(self.fire_orig)
        # If this plugin has a menu need to iterate through making clone wrappers of it.
        if orig_action.menu():
            clone_m = QMenu(orig_action.text(), parent)
            self._clone_menu(orig_action.menu(), clone_m)
            self.setMenu(clone_m)

    def _clone_menu(self, orig_m, clone_m):
        for ac in QMenu.actions(orig_m):
            if ac.isSeparator():
                clone_m.addSeparator()
                continue
            clone_m.addAction(ActionWrapper(ac, clone_m))

    def fire_orig(self):
        orig = self.orig()
        if orig is not None:
            orig.trigger()

    def toggle_orig(self, is_checked):
        orig = self.orig()
        if orig is not None:
            orig.toggle()


class FavouritesMenuAction(InterfaceAction):

    name = 'Favourites Menu'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (_('Favourites'), None, None, None)
    dont_add_to = frozenset(['context-menu-device'])
    popup_type = QToolButton.InstantPopup
    action_type = 'current'

    def genesis(self):
        self.menu = QMenu(self.gui)
        self.menu.aboutToShow.connect(self._about_to_show_menu)

        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)

        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))

    def _about_to_show_menu(self):
        # Need to rebuild our menus each time shown, because the associated
        # QAction objects may have been orphaned/removed/not relevant now.
        self.rebuild_menus()

    def rebuild_menus(self):
        # Ensure any keyboard shortcuts from previous display of plugin menu are cleared
        unregister_menu_actions(self)

        fav_menus = cfg.plugin_prefs[cfg.STORE_MENUS]
        m = self.menu
        m.clear()
        in_device_mode = self.gui.location_manager.has_device
        discovered_plugins = {}

        for fav_menu in fav_menus:
            if fav_menu is None:
                m.addSeparator()
                continue
            ac = None
            paths = list(fav_menu['path'])
            plugin_name = paths[0]
            is_device_only_plugin = False
            if plugin_name == 'Location Manager':
                # Special case handling since not iaction instances
                is_device_only_plugin = True
                paths = paths[1:]
                for loc_action in self.gui.location_manager.all_actions[1:]:
                    if unicode(loc_action.text()) == paths[0]:
                        if len(paths) > 1:
                            # This is an action on the menu for this plugin or its submenus
                            ac = self._find_action_for_menu(loc_action.menu(), paths[1:], plugin_name)
                        else:
                            # This is a top-level plugin being added to the menu
                            ac = loc_action
                        break
            else:
                iaction = self.gui.iactions.get(plugin_name, None)
                if iaction is not None:
                    if iaction not in discovered_plugins:
                        discovered_plugins[iaction] = True
                        if hasattr(iaction, 'menu'):
                            iaction.menu.aboutToShow.emit()
                    is_device_only_plugin = 'toolbar' in iaction.dont_add_to and 'toolbar-device' not in iaction.dont_add_to
                    if len(paths) > 1:
                        # This is an action on the menu for this plugin or its submenus
                        ac = self._find_action_for_menu(iaction.qaction.menu(), paths[1:], plugin_name)
                    else:
                        # This is a top-level plugin being added to the menu
                        ac = iaction.qaction

            if ac is None:
                # We have a menu action that is not available. Perhaps the user
                # has switched libraries, uninstalled a plugin or for some other
                # reason that underlying item is not available any more. We still add
                # a placeholder menu item, but will have no icon and be disabled.
                mac = QAction(fav_menu['display'], m)
                mac.setEnabled(False)
                #print('Favourite Menu: action not found:', fav_menu)
            else:
                # We have found the underlying action for this menu item.
                # Clone the original QAction in order to alias the text for it
                mac = ActionWrapper(ac, m)
                mac.setText(fav_menu['display'])

            if is_device_only_plugin and not in_device_mode:
                mac.setEnabled(False)
            m.addAction(mac)

        m.addSeparator()
        create_menu_action_unique(self, m, _('&Customize plugin') + '...', 'config.png',
                                  shortcut=False, triggered=self.show_configuration)
        create_menu_action_unique(self, m, _('&Help'), 'help.png',
                                  shortcut=False, triggered=cfg.show_help)

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def _find_action_for_menu(self, parent, paths, plugin_name):
        if parent is not None:
            find_text = paths[0]
            for ac in QMenu.actions(parent):
                if ac.isSeparator():
                    continue
                #print('Looking at action:',unicode(ac.text()))
                safe_title = cfg.get_safe_title(ac)
                if safe_title == find_text:
                    if len(paths) == 1:
                        return ac
                    return self._find_action_for_menu(ac.menu(), paths[1:], plugin_name)

