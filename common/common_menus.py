#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2022, Grant Drake'

from calibre.gui2.actions import menu_action_unique_name
from calibre.constants import numeric_version as calibre_version
from common_icons import get_icon

# ----------------------------------------------
#          Global resources / state
# ----------------------------------------------

# Global definition of our menu actions. Used to ensure we can cleanly unregister
# keyboard shortcuts when rebuilding our menus.
plugin_menu_actions = []

# ----------------------------------------------
#                Menu functions
# ----------------------------------------------

def unregister_menu_actions(ia):
    '''
    For plugins that dynamically rebuild their menus, we need to ensure that any
    keyboard shortcuts are unregistered for them each time.
    Make sure to call this before .clear() of the menu items.
    '''
    global plugin_menu_actions
    for action in plugin_menu_actions:
        if hasattr(action, 'calibre_shortcut_unique_name'):
            ia.gui.keyboard.unregister_shortcut(action.calibre_shortcut_unique_name)
        # starting in calibre 2.10.0, actions are registers at
        # the top gui level for OSX' benefit.
        if calibre_version >= (2,10,0):
            ia.gui.removeAction(action)
    plugin_menu_actions = []


def create_menu_action_unique(ia, parent_menu, menu_text, image=None, tooltip=None,
                       shortcut=None, triggered=None, is_checked=None, shortcut_name=None,
                       unique_name=None, favourites_menu_unique_name=None):
    '''
    Create a menu action with the specified criteria and action, using the new
    InterfaceAction.create_menu_action() function which ensures that regardless of
    whether a shortcut is specified it will appear in Preferences->Keyboard

    For a full description of the parameters, see: calibre\\gui2\\actions\\__init__.py
    '''
    orig_shortcut = shortcut
    kb = ia.gui.keyboard
    if unique_name is None:
        unique_name = menu_text
    if not shortcut == False:
        full_unique_name = menu_action_unique_name(ia, unique_name)
        if full_unique_name in kb.shortcuts:
            shortcut = False
        else:
            if shortcut is not None and not shortcut == False:
                if len(shortcut) == 0:
                    shortcut = None

    if shortcut_name is None:
        shortcut_name = menu_text.replace('&','')

    if calibre_version >= (5,4,0):
        # The persist_shortcut parameter only added from 5.4.0 onwards.
        # Used so that shortcuts specific to other libraries aren't discarded.
        ac = ia.create_menu_action(parent_menu, unique_name, menu_text, icon=None,
                                   shortcut=shortcut, description=tooltip,
                                   triggered=triggered, shortcut_name=shortcut_name,
                                   persist_shortcut=True)
    else:
        ac = ia.create_menu_action(parent_menu, unique_name, menu_text, icon=None,
                                   shortcut=shortcut, description=tooltip,
                                   triggered=triggered, shortcut_name=shortcut_name)
    if shortcut == False and not orig_shortcut == False:
        if ac.calibre_shortcut_unique_name in ia.gui.keyboard.shortcuts:
            kb.replace_action(ac.calibre_shortcut_unique_name, ac)
    if image:
        ac.setIcon(get_icon(image))
    if is_checked is not None:
        ac.setCheckable(True)
        if is_checked:
            ac.setChecked(True)
    # For use by the Favourites Menu plugin. If this menu action has text
    # that is not constant through the life of this plugin, then we need
    # to attribute it with something that will be constant that the
    # Favourites Menu plugin can use to identify it.
    if favourites_menu_unique_name:
        ac.favourites_menu_unique_name = favourites_menu_unique_name

    # Append to our list of actions for this plugin to unregister when menu rebuilt
    global plugin_menu_actions
    plugin_menu_actions.append(ac)

    return ac


def create_menu_item(ia, parent_menu, menu_text, image=None, tooltip=None,
                     shortcut=(), triggered=None, is_checked=None):
    '''
    Create a menu action with the specified criteria and action
    Note that if no shortcut is specified, will not appear in Preferences->Keyboard
    This method should only be used for actions which either have no shortcuts,
    or register their menus only once. Use create_menu_action_unique for all else.

    Currently this function is only used by open_with and search_the_internet plugins
    and would like to investigate one day if it can be removed from them.
    '''
    if shortcut is not None:
        if len(shortcut) == 0:
            shortcut = ()
    ac = ia.create_action(spec=(menu_text, None, tooltip, shortcut),
        attr=menu_text)
    if image:
        ac.setIcon(get_icon(image))
    if triggered is not None:
        ac.triggered.connect(triggered)
    if is_checked is not None:
        ac.setCheckable(True)
        if is_checked:
            ac.setChecked(True)

    parent_menu.addAction(ac)
    
    # Append to our list of actions for this plugin to unregister when menu rebuilt
    global plugin_menu_actions
    plugin_menu_actions.append(ac)

    return ac
