from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from functools import partial
try:
    from qt.core import QMenu, QToolButton
except ImportError:
    from PyQt5.Qt import QMenu, QToolButton
from calibre.gui2 import error_dialog
from calibre.gui2.actions import InterfaceAction

import calibre_plugins.user_category.config as cfg
from calibre_plugins.user_category.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.user_category.common_menus import unregister_menu_actions, create_menu_action_unique
from calibre_plugins.user_category.dialogs import ChooseMultipleDialog

# Pull in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

PLUGIN_ICONS = ['images/user_category.png',
                'images/authors_add.png', 'images/authors_move.png', 'images/authors_remove.png',
                'images/series_add.png', 'images/series_move.png', 'images/series_remove.png',
                'images/publishers_add.png', 'images/publishers_move.png', 'images/publishers_remove.png',
                'images/tags_add.png', 'images/tags_move.png', 'images/tags_remove.png',
                'images/show_tag_browser.png']

class UserCategoryAction(InterfaceAction):

    name = 'User Category'
    action_spec = (_('User category'), None, None, None)
    popup_type = QToolButton.InstantPopup
    action_type = 'current'

    def genesis(self):
        self.is_library_selected = True
        self.category_labels = ['authors', 'series', 'publishers', 'tags']
        self.category_labels_trans = { 'authors':_('authors'), 'series':_('series'), \
                                       'publishers':_('publishers'),'tags':_('tags') }
        self.old_actions_unique_map = {}
        self.sub_menus_evaluated = []
        self.menu = QMenu()

        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)

        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.menu.aboutToShow.connect(self.about_to_show_menu)

    def initialization_complete(self):
        # We must delay constructing until the gui view is available
        self.rebuild_menus()

    def library_changed(self, db):
        # We need to reset our menus after switching libraries
        self.rebuild_menus()

    def location_selected(self, loc):
        self.is_library_selected = loc == 'library'

    def about_to_show_menu(self):
        # Top-level menu is being expanded, clear caches of sub menu items
        self.sub_menus_evaluated = []
        # Rebuild the whole menu every time
        self.rebuild_menus()

    def rebuild_menus(self):
        # Ensure any keyboard shortcuts from previous display of plugin menu are cleared
        unregister_menu_actions(self)

        # Build our cache of contents of the user categories
        self.create_category_caches()
        c = cfg.plugin_prefs[cfg.STORE_NAME]
        menus_enabled = c[cfg.MENUS_KEY]
        other_menus_enabled = c[cfg.OTHER_MENUS_KEY]
        self.db = self.gui.library_view.model().db

        m = self.menu
        m.clear()
        self.actions_map = {}
        self.actions_unique_map = {}

        # Create the 'Add...' items
        if other_menus_enabled['add']:
            for label in self.category_labels:
                if menus_enabled[label]:
                    trans_label = self.category_labels_trans[label]
                    add_sub_menu = m.addMenu(get_icon('images/%s_add.png' % label),
                                             _('Add selected')+' '+ trans_label)
                    add_sub_menu.aboutToShow.connect(partial(self.about_to_show_action_sub_menu,
                                                             add_sub_menu, label, 'add'))
                    # Now create the actual menu items for each user category
                    self.create_submenu_for_each_category(add_sub_menu, 'add', label)
            m.addSeparator()

        # Create the 'Move...' items
        if other_menus_enabled.get('move', True):
            for label in self.category_labels:
                if menus_enabled[label]:
                    trans_label = self.category_labels_trans[label]
                    move_sub_menu = m.addMenu(get_icon('images/%s_move.png' % label),
                                             _('Move selected')+' '+ trans_label)
                    move_sub_menu.aboutToShow.connect(partial(self.about_to_show_action_sub_menu,
                                                              move_sub_menu, label, 'move'))
                    # Now create the actual menu items for each user category
                    self.create_submenu_for_each_category(move_sub_menu, 'move', label)
            m.addSeparator()

        # Create the 'Remove...' items
        if other_menus_enabled['remove']:
            for label in self.category_labels:
                if menus_enabled[label]:
                    trans_label = self.category_labels_trans[label]
                    remove_sub_menu = m.addMenu(get_icon('images/%s_remove.png' % label),
                                                _('Remove selected')+' '+ trans_label)
                    remove_sub_menu.aboutToShow.connect(partial(self.about_to_show_action_sub_menu,
                                                                remove_sub_menu, label, 'remove'))
                    self.create_submenu_for_each_category(remove_sub_menu, 'remove', label)
            m.addSeparator()

        # Create the additional configuration menu options
        if other_menus_enabled['view']:
            view_sub_menu = m.addMenu(get_icon('images/show_tag_browser.png'), _('Show in tag browser'))
            self.create_submenu_for_each_category(view_sub_menu, 'view')
        if other_menus_enabled['manage']:
            manage_sub_menu = m.addMenu(get_icon('chapters.png'), _('Manage user categories'))
            self.create_submenu_for_each_category(manage_sub_menu, 'manage')
        m.addSeparator()
        create_menu_action_unique(self, m, _('&Customize plugin')+'...', 'config.png',
                                  shortcut=False, triggered=self.show_configuration)
        create_menu_action_unique(self, m, _('&Help'), 'help.png',
                                  shortcut=False, triggered=cfg.show_help)

        # Before we finalize, make sure we delete any actions for menus that are no longer displayed
        for menu_id, unique_name in list(self.old_actions_unique_map.items()):
            if menu_id not in self.actions_unique_map:
                self.gui.keyboard.unregister_shortcut(unique_name)
        self.old_actions_unique_map = self.actions_unique_map
        self.gui.keyboard.finalize()

    def create_submenu_for_each_category(self, parent_menu, action, label=''):
        for cat_name in self.sorted_cat_names:
            self.create_action_menu_item(parent_menu, cat_name, 'drawer.png',
                                      action, cat_name, label)

    def create_action_menu_item(self, m, menu_text, image_name, action='', cat_name='', label=''):
        trigger = None
        shortcut_name = None
        if action == 'view':
            trigger = partial(self.view_user_category, cat_name)
            shortcut_name = _('View user category')+': ' + cat_name
        elif action == 'manage':
            trigger = partial(self.manage_user_category, cat_name)
            shortcut_name = _('Manage user category')+': ' + cat_name
        else: # add or remove
            trigger = partial(self.modify_user_category, action, cat_name, label)
            trans_label = self.category_labels_trans[label]
            if action == 'add':
                shortcut_name = _('Add %s to user category: %s')%(trans_label,cat_name)
            elif action == 'move':
                shortcut_name = _('Move %s to user category: %s')%(trans_label,cat_name)
            else:
                shortcut_name = _('Remove %s from user category: %s')%(trans_label,cat_name)
        unique_name = action+label+cat_name
        ac = create_menu_action_unique(self, m, menu_text, image_name,
                                       shortcut_name=shortcut_name, unique_name=unique_name,
                                       triggered=trigger)
        self.actions_map[unique_name] = ac
        self.actions_unique_map[unique_name] = ac.calibre_shortcut_unique_name
        return ac

    def about_to_show_action_sub_menu(self, sub_menu, label, action):
        # Second level menu is being expanded of category list names, disabled based on action
        # For performance reasons only evaluate selection first time submenu is rolled over
        if sub_menu in self.sub_menus_evaluated:
            return
        self.sub_menus_evaluated.append(sub_menu)
        db = self.gui.library_view.model().db

        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0 or not self.is_library_selected:
            return

        # Build our unique set of values based on the sub-menu selected
        values = []
        for row in rows:
            self.append_unique_data_from_row(db, values, row.row(), label)
        # Now iterate through each of the categories to test membership of values
        # Any categories that should not have a menu action are disabled
        for cat_name in self.sorted_cat_names:
            menu_enabled = False
            for value in values:
                match_value = value + '|' + label
                if action in ['add','move']:
                    if match_value not in self.cat_sets[cat_name]:
                        menu_enabled = True
                        break
                elif action == 'remove':
                    if match_value in self.cat_sets[cat_name]:
                        menu_enabled = True
                        break
            # Lookup the action from our dictionary built when we rebuilt the menu
            ac = self.actions_map[action+label+cat_name]
            ac.setEnabled(menu_enabled)

    def append_unique_data_from_row(self, db, values, row, label):
        if label == 'authors':
            authors = db.authors(row)
            if authors:
                for author in authors.split(','):
                    safe_author = author.replace('|',',')
                    if author and not safe_author in values:
                        values.append(safe_author)
        elif label == 'series':
            series = db.series(row)
            if series and not series in values:
                values.append(series)
        elif label == 'publisher':
            publisher = db.publisher(row)
            if publisher and not publisher in values:
                values.append(publisher)
        elif label == 'tags':
            tags = db.tags(row)
            if tags:
                for tag in tags.split(','):
                    if not tag in values:
                        values.append(tag)

    def create_category_caches(self):
        # Create a dictionary of sets for performant lookup of membership
        self.cat_sets = {}
        self.sorted_cat_names = []
        cats = self.gui.library_view.model().db.prefs.get('user_categories', {})
        for c in cats:
            self.cat_sets[c] = set([val + '|' + key for (val, key, _ign) in cats[c]])
            self.sorted_cat_names.append(c)
        self.sorted_cat_names.sort()

    def modify_user_category(self, action, cat_name, label):
        rows = self.gui.library_view.selectionModel().selectedRows()
        db = self.gui.library_view.model().db
        # Build our unique set of values based on the sub-menu selected
        values = []
        for row in rows:
            self.append_unique_data_from_row(db, values, row.row(), label)

        # Now remove all values that already exist in the user category as appropriate for action
        modify_values = []
        for value in values:
            match_value = value + '|' + label
            if action in ['add','move']:
                if match_value not in self.cat_sets[cat_name]:
                    modify_values.append(value)
            elif action == 'remove':
                if match_value in self.cat_sets[cat_name]:
                    modify_values.append(value)

        if len(modify_values) > 1:
            # Need to display a picker dialog to allow the user to choose which to apply in this action.
            (modify_values, ok) = self.pick_values_to_modify(modify_values, action, label)
            if not ok:
                return

        if len(modify_values) == 0:
            return error_dialog(self.gui, _('Cannot modify user category'),
                             _('No new values in books selected'), show=True)

        # Get dictionary of all the existing user category values
        self.categories = dict.copy(db.prefs.get('user_categories', {}))

        # Get our selected user category from the dictionary if it exists
        if cat_name not in self.categories:
            return error_dialog(self.gui, _('Cannot modify user category'),
                             _('Selected user category not found. Please restart Calibre.'), show=True)

        self.selected_cat = self.categories[cat_name]
        if action in ['add','move']:
            # Modify our user category contents for any that do not exist already in the list
            for value in modify_values:
                self.selected_cat.append([value, label, 0])
            # Re-sort the collection
            l = []
#            for n in sorted(self.selected_cat, cmp=lambda x,y: cmp(x[0], y[0])):
            from operator import itemgetter
            for n in sorted(self.selected_cat, key=itemgetter(0)):
                l.append(n)
            self.categories[cat_name] = l
        elif action == 'remove':
            # Modify our user category contents for any that exist in the list
            for value in modify_values:
                for item,l in enumerate(self.selected_cat):
                    if l[0] == value and l[1] == label:
                        del self.selected_cat[item]

        # If user did a "move", then remove from any other categories
        if action == 'move':
            for value in modify_values:
                for all_cat_name, all_cat in list(self.categories.items()):
                    changed = False
                    if all_cat_name != cat_name:
                        for item,l in enumerate(all_cat):
                            if l[0] == value and l[1] == label:
                                del all_cat[item]

        # Final steps (point of no return) - update the database
        db.prefs['user_categories'] = self.categories
        # The category contents might have changed, invalidating the search caches
        if hasattr(db, 'new_api'):
            db.new_api.clear_search_caches()
        # Signal the tags panel to refresh it's view.
        self.gui.tags_view.recount()

    def pick_values_to_modify(self, values, action, label):
        ok = False
        icon = '%s_%s.png' % (label, action)
        d = ChooseMultipleDialog(self.gui, values, action, label, icon)
        d.exec_()
        if d.result() == d.Accepted:
            values = d.selected_values
            ok = len(values) > 0
        return (values, ok)

    def view_user_category(self, cat_name):
        if not self.gui.tags_view.pane_is_visible:
            self.gui.tb_splitter.show_side_pane()
        self.gui.tags_view.collapseAll()
        p = self.gui.tags_view.model().find_category_node('@' + cat_name)
        if p:
            self.gui.tags_view.show_item_at_path(p)
            idx = self.gui.tags_view.model().index_for_path(p)
            self.gui.tags_view.setExpanded(idx, True)
        else:
            return error_dialog(self.gui, _('Cannot view user category'),
                             _('User category not found'), show=True)

    def manage_user_category(self, cat_name):
        self.gui.do_edit_user_categories(on_category=cat_name)

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)
