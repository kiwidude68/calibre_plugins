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
from calibre.gui2 import question_dialog, config
from calibre.gui2.actions import InterfaceAction

import calibre_plugins.walk_search_history.config as cfg
from calibre_plugins.walk_search_history.state import SearchHistoryState, NavigationSearchHistoryState
from calibre_plugins.walk_search_history.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.walk_search_history.common_menus import unregister_menu_actions, create_menu_action_unique

PLUGIN_ICONS = ['images/goto_previous.png', 'images/goto_next.png']


class WalkSearchHistoryAction(InterfaceAction):

    name = 'Walk Search History'
    action_spec = (_('History'), None, None, None)
    action_type = 'current'

    def genesis(self):
        self.default_action_is_previous = False
        self.is_navigating_history = False
        self.last_search_text = ''
        self.library_history = dict()
        self.menu = QMenu()

        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)

        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))

    def initialization_complete(self):
        # We must delay constructing until the gui view is available to modify the toolbar button
        # This is not available from the genesis() method.
        self.visited_history_state = SearchHistoryState(self.gui.search)
        self.navigation_history_state = NavigationSearchHistoryState(self.gui.search)
        library_id = self.gui.current_db.library_id
        self.library_history[library_id] = (self.visited_history_state, self.navigation_history_state)

        self.rebuild_menus()
        # Setup hooks so that we rebuild the dropdown menus each time to represent latest history
        self.menu.aboutToShow.connect(self.rebuild_menus)
        # Hook into the search signal so that we can keep track of the searches being performed
        self.gui.search.search.connect(self.search_performed)

    def library_changed(self, db):
        # Supporting the option of resetting/restoring search history on a per library bases
        perLibrary = cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_PER_LIBRARY, False)
        if perLibrary:
            library_id = db.library_id
            if library_id in self.library_history:
                (visited, navigation) = self.library_history[library_id]
                self.visited_history_state = visited
                self.navigation_history_state = navigation
            else:
                self.visited_history_state = SearchHistoryState(None)
                self.navigation_history_state = NavigationSearchHistoryState(None)
                self.library_history[library_id] = (self.visited_history_state, self.navigation_history_state)

    def rebuild_menus(self):
        # Ensure any keyboard shortcuts from previous display of plugin menu are cleared
        unregister_menu_actions(self)
        
        c = cfg.plugin_prefs[cfg.STORE_NAME]
        m = self.menu
        m.clear()

        create_menu_action_unique(self, m, _('Goto previous'), PLUGIN_ICONS[0],
                                  shortcut='Alt+Left',  triggered=self.find_previous_search)
        create_menu_action_unique(self, m, _('Goto next'), PLUGIN_ICONS[1],
                                  shortcut='Alt+Right', triggered=self.find_next_search)

        # Now create menu items for each of the searches currently in the history
        if len(self.visited_history_state.items()) > 0:
            m.addSeparator()
            current_search = self.current_search_text()
            limit = c[cfg.KEY_LIMIT]
            for i, history_item in enumerate(self.visited_history_state.items()):
                if limit > 0 and i == limit:
                    break
                # Ensure we escape ampersands
                display_history_item = history_item.replace('&','&&')
                ac = create_menu_action_unique(self, m, display_history_item, shortcut=False,
                                      triggered=partial(self.goto_search_item, history_item))
                if history_item == current_search:
                    ac.setCheckable(True)
                    ac.setChecked(True)

        # Finally add a menu item for configuring the plugin
        m.addSeparator()
        create_menu_action_unique(self, m, _('Clear search history'),
                                  triggered=self.clear_search_history)
        m.addSeparator()
        create_menu_action_unique(self, m, _('&Customize plugin')+'...', 'config.png',
                                  shortcut=False, triggered=self.show_configuration)
        create_menu_action_unique(self, m, _('&Help'), 'help.png',
                                  shortcut=False, triggered=cfg.show_help)
        self.gui.keyboard.finalize()

        # Set the desired default action for the toolbar button when clicked on
        if self.default_action_is_previous:
            self.qaction.triggered.disconnect()
        self.default_action_is_previous = c[cfg.KEY_DEFAULT_ACTION] == cfg.KEY_PREVIOUS
        popup_type = QToolButton.InstantPopup
        if self.default_action_is_previous:
            popup_type = QToolButton.MenuButtonPopup
            self.qaction.triggered.connect(self.find_previous_search)
        # Apply the popup type for this action in the toolbar
        # Only update on the toolbar if it is actually visible there
        self.change_toolbar_popup_type(popup_type)

    def change_toolbar_popup_type(self, popup_type):
        self.popup_type = popup_type
        for bar in self.gui.bars_manager.bars:
            if hasattr(bar, 'setup_tool_button'):
                if self.qaction in bar.added_actions:
                    bar.setup_tool_button(bar, self.qaction, self.popup_type)

    def current_search_text(self):
        if self.gui.search.count() == 0:
            return ''
        return self.last_search_text

    def search_performed(self, text):
        # A search has been performed - either triggered by this plugin or by user using the GUI
        # If search is the same as the last search executed, nothing to do
        if text == self.last_search_text:
            return
        self.last_search_text = text
        if self.is_navigating_history:
            # Search has been triggered by this plugin - nothing to do:
            return
        # Only add it to our history if it is not an empty search
        if text:
            self.visited_history_state.append(text)
            # Ensure our navigation history of searches is updated
            self.navigation_history_state.append(text)
        else:
            # Special behavior depending on where we are in the history navigation.
            self.navigation_history_state.reset_after_empty_search()

    def find_previous_search(self):
        if self.gui.search.count() == 0:
            # First-time user, has never done a search
            return
        # Only if there is a previous search to display do we perform a search
        if self.navigation_history_state.goto_previous():
            previous_search = self.navigation_history_state.get_current()
            try:
                self.is_navigating_history = True
                self.gui.search.set_search_string(previous_search, store_in_history=True)
            finally:
                self.is_navigating_history = False

    def find_next_search(self):
        if self.gui.search.count() == 0:
            # First-time user
            return
        # Only if there is a next search to display do we perform a search
        if self.navigation_history_state.goto_next():
            next_search = self.navigation_history_state.get_current()
            # We want to store the selection in the combo history so as to "re-add" it
            try:
                self.is_navigating_history = True
                self.gui.search.set_search_string(next_search, store_in_history=True)
            finally:
                self.is_navigating_history = False

    def goto_search_item(self, selected_text):
        # User has selected an item in the history to jump to from the menu
        # Update our history menu to reflect the new position moving it to the top
        self.visited_history_state.append(selected_text)
        self.gui.search.set_search_string(selected_text, store_in_history=True)

    def clear_search_history(self):
        if not question_dialog(self.gui, _('Are you sure?'), '<p>'+
                           _('Are you sure you want to clear the search history?'), show_copy_button=False):
            return
        # Turn off event signals for combobox to prevent a search being triggered
        self.gui.search.block_signals(True)
        while self.gui.search.count() > 0:
            self.gui.search.removeItem(0)
        self.gui.search.block_signals(False)
        # Clear the config history where the history is persisted
        config[self.gui.search.opt_name] = []
        # Ensure our own state histories are cleared too
        self.visited_history_state.clear()
        self.navigation_history_state.clear()

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)
