from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import six
from six import text_type as unicode
from six.moves import range

try:
    from qt.core import (QWidget, QHBoxLayout, QMenu, QTreeWidget, Qt, QIcon,
                        QTreeWidgetItem, QListWidget, QListWidgetItem, QSize,
                        QToolButton, QVBoxLayout, QAbstractItemView,
                        QPainter, QRect, QPixmap, QBrush, QPushButton, QUrl)
except ImportError:                        
    from PyQt5.Qt import (QWidget, QHBoxLayout, QMenu, QTreeWidget, Qt, QIcon,
                        QTreeWidgetItem, QListWidget, QListWidgetItem, QSize,
                        QToolButton, QVBoxLayout, QAbstractItemView,
                        QPainter, QRect, QPixmap, QBrush, QPushButton, QUrl)

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.gui2 import open_url
from calibre.utils.config import JSONConfig
from calibre_plugins.favourites_menu.common_icons import get_icon

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Favourites Menu')

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/Favourites-Menu'

ICON_SIZE = 32

STORE_MENUS = 'menus'
DEFAULT_MENUS = []

# We store the menus as an ordered list.
# Each item in the list is a dictionary of:
# {
#   'display': 'Text to appear in menu',
#   'path': ['iaction name', 'Submenu name',...,'action name']
# }
# If instead the item is "None" then it indicates a separator

plugin_prefs.defaults[STORE_MENUS] = DEFAULT_MENUS


def get_safe_title(action):
    if hasattr(action, 'favourites_menu_unique_name'):
        text = unicode(action.favourites_menu_unique_name)
    else:
        text = unicode(action.text())
    return text.replace('&&', '—').replace('&', '').replace('—', '&')

def show_help():
    open_url(QUrl(HELP_URL))


class FavMenusListWidget(QListWidget):

    SEP = '--- ' + _('Separator') + ' ---'

    def __init__(self, parent):
        QListWidget.__init__(self, parent)
        self.setSortingEnabled(False)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.blank_icon = get_icon('blank.png')

    def populate_list(self, fav_menus):
        for fav_menu in fav_menus:
            self.populate_list_item(fav_menu)
        if fav_menus:
            self.setCurrentRow(0)

    def populate_list_item(self, fav_menu, idx= -1):
        self.blockSignals(True)
        if fav_menu is None:
            item = QListWidgetItem(self.SEP)
            item.setIcon(self.blank_icon)
        else:
            text = fav_menu['display']
            item = QListWidgetItem(text)
            item.setFlags(Qt.ItemIsEditable | item.flags())
            paths = fav_menu['path']
            item.setToolTip(' -> '.join(paths))
            item.setData(Qt.UserRole, (fav_menu,))
            icon = fav_menu.get('icon', None)
            if icon is None:
                # This is a menu item that hasn't been found in this session
                # We will display it with a blank icon and disabled
                icon = self.blank_icon
                item.setForeground(QBrush(Qt.darkGray))
            item.setIcon(icon)
        if idx < 0:
            self.addItem(item)
        else:
            self.insertItem(idx + 1, item)
        self.blockSignals(False)

    def remove_matching_item(self, remove_fav_menu):
        paths_text = '/'.join(remove_fav_menu['path'])
        for row in range(self.count()):
            lw = self.item(row)
            data = lw.data(Qt.UserRole)
            if data is not None:
                fav_menu = data[0]
                if paths_text == '/'.join(fav_menu['path']):
                    self.takeItem(row)
                    break

    def get_fav_menus(self):
        fav_menus = []
        for row in range(self.count()):
            lw = self.item(row)
            data = lw.data(Qt.UserRole)
            if data is None:
                # Only add separators if not first or last item and not duplicated
                if len(fav_menus) > 0 and row < self.count() - 1:
                    if not fav_menus[-1] is None:
                        fav_menus.append(None)
            else:
                fav_menu = data[0]
                new_fav_menu = {'display': unicode(lw.text()).strip(),
                                'path': fav_menu['path']}
                fav_menus.append(new_fav_menu)
        return fav_menus

    def swap_list_widgets(self, src_idx):
        # Swaps this idx row with the one following
        self.blockSignals(True)
        lw = self.takeItem(src_idx)
        self.insertItem(src_idx +1, lw)
        self.blockSignals(False)


class Item(QTreeWidgetItem):
    pass


class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        self.gui = plugin_action.gui
        self._initialise_layout()
        self.blank_icon = QIcon(I('blank.png'))

        fav_menus = plugin_prefs[STORE_MENUS]
        # Rebuild this into a map for comparison purposes
        lookup_menu_map = self._build_lookup_menu_map(fav_menus)
        self._populate_actions_tree(lookup_menu_map)
        self.items_list.populate_list(fav_menus)

        # Hook up our events
        self.tv.itemChanged.connect(self._tree_item_changed)
        self.items_list.currentRowChanged.connect(self._update_button_states)
        self._update_button_states()

    def _initialise_layout(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        main_layout = QHBoxLayout()
        layout.addLayout(main_layout)

        self.tv = QTreeWidget(self.gui)
        self.tv.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.tv.header().hide()
        main_layout.addWidget(self.tv, 1)

        self.items_list = FavMenusListWidget(self.gui)
        self.items_list.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        main_layout.addWidget(self.items_list, 1)

        button_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)

        self.up_btn = QToolButton(self.gui)
        self.up_btn.setIcon(get_icon('arrow-up.png'))
        self.up_btn.setToolTip(_('Move the selected menu item up'))
        self.up_btn.clicked.connect(self._move_item_up)
        self.down_btn = QToolButton(self.gui)
        self.down_btn.setIcon(get_icon('arrow-down.png'))
        self.down_btn.setToolTip(_('Move the selected menu item down'))
        self.down_btn.clicked.connect(self._move_item_down)
        self.remove_btn = QToolButton(self.gui)
        self.remove_btn.setIcon(get_icon('trash.png'))
        self.remove_btn.setToolTip(_('Remove the selected item from the menu'))
        self.remove_btn.clicked.connect(self._remove_item)
        self.sep_btn = QToolButton(self.gui)
        self.sep_btn.setIcon(get_icon('plus.png'))
        self.sep_btn.setToolTip(_('Add a separator to the menu following the selected item'))
        self.sep_btn.clicked.connect(self._add_separator)
        self.rename_btn = QToolButton(self.gui)
        self.rename_btn.setIcon(get_icon('edit-undo.png'))
        self.rename_btn.setToolTip(_('Rename the menu item for when it appears on your Favourites menu'))
        self.rename_btn.clicked.connect(self._rename_item)
        button_layout.addWidget(self.up_btn)
        button_layout.addStretch(1)
        button_layout.addWidget(self.rename_btn)
        button_layout.addStretch(1)
        button_layout.addWidget(self.sep_btn)
        button_layout.addStretch(1)
        button_layout.addWidget(self.remove_btn)
        button_layout.addStretch(1)
        button_layout.addWidget(self.down_btn)

        button_layout = QHBoxLayout()
        help_button = QPushButton(' '+_('&Help'), self)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(show_help)
        button_layout.addWidget(help_button)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)

    def _move_item_up(self):
        idx = self.items_list.currentRow()
        if idx > 0:
            self.items_list.swap_list_widgets(idx-1)
            self.items_list.setCurrentRow(idx-1)
            self._update_button_states()

    def _move_item_down(self):
        idx = self.items_list.currentRow()
        if idx < self.items_list.count() - 1:
            self.items_list.swap_list_widgets(idx)
            self.items_list.setCurrentRow(idx+1)
            self._update_button_states()

    def _add_separator(self):
        idx = self.items_list.currentRow()
        self.items_list.populate_list_item(None, idx)
        self.items_list.setCurrentRow(idx+1)

    def _remove_item(self):

        def find_child(twi, paths):
            for i in range(0, twi.childCount()):
                c = twi.child(i)
                text = unicode(c.text(0))
                if text == paths[0]:
                    if len(paths) == 1:
                        return c
                    else:
                        return find_child(c, paths[1:])

        idx = self.items_list.currentRow()
        if idx < 0:
            return
        item = self.items_list.currentItem()
        data = item.data(Qt.UserRole)
        if data is not None:
            # Not removing a separator
            fav_menu = data[0]
            # Lookup the item to uncheck it.
            self.tv.blockSignals(True)
            paths = fav_menu['path']
            plugin = paths[0]
            # Find the top-level item for the plugin
            tree_item = None
            if plugin in self.top_level_items_map:
                tree_item = self.top_level_items_map[plugin]
                if len(paths) > 1:
                    tree_item = find_child(tree_item, paths[1:])
                if tree_item is not None:
                    tree_item.setCheckState(0, Qt.Unchecked)
            self.tv.blockSignals(False)
        self.items_list.takeItem(idx)
        self._update_button_states()

    def _rename_item(self):
        idx = self.items_list.currentRow()
        if idx < 0:
            return
        item = self.items_list.currentItem()
        data = item.data(Qt.UserRole)
        if data is not None:
            self.items_list.editItem(item)

    def _update_button_states(self):
        idx = self.items_list.currentRow()
        self.up_btn.setEnabled(idx > 0)
        self.down_btn.setEnabled(idx < self.items_list.count() - 1)
        self.remove_btn.setEnabled(self.items_list.count() > 0)
        self.sep_btn.setEnabled(self.items_list.count() > 0)
        data = None
        if idx >= 0:
            item = self.items_list.currentItem()
            data = item.data(Qt.UserRole)
        self.rename_btn.setEnabled(data is not None)

    def _build_lookup_menu_map(self, fav_menus):
        m = {}
        for fav_menu in fav_menus:
            if fav_menu is None:
                continue
            path = fav_menu['path']
            plugin = path[0]
            if plugin not in m:
                m[plugin] = []
            fav_menu['paths_text'] = '|'.join(path[1:])
            m[plugin].append(fav_menu)
        return m

    def _get_scaled_icon(self, icon):
        if icon.isNull():
            return self.blank_icon
        # We need the icon scaled to 16x16
        src = icon.pixmap(ICON_SIZE, ICON_SIZE)
        if src.width() == ICON_SIZE and src.height() == ICON_SIZE:
            return icon
        # Need a new version of the icon
        pm = QPixmap(ICON_SIZE, ICON_SIZE)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.drawPixmap(QRect(0, 0, ICON_SIZE, ICON_SIZE), src)
        p.end()
        return QIcon(pm)

    def _populate_actions_tree(self, lookup_menu_map):
        # Lets re-sort the keys so that items will appear on screen sorted
        # by their display name (not by their key)
        skeys_map = {}
        for plugin_name, iaction in six.iteritems(self.gui.iactions):
            if plugin_name == self.plugin_action.name:
                continue
            if 'toolbar' in iaction.dont_add_to and 'toolbar-device' in iaction.dont_add_to:
                print(('Not adding:', plugin_name))
                continue
            display_name = unicode(iaction.qaction.text())
            if plugin_name == 'Choose Library':
                display_name = 'Library'
            skeys_map[display_name] = (plugin_name, iaction.qaction)
        # Add a special case item for the location manager
        skeys_map['Location Manager'] = ('Location Manager', None)

        self.top_level_items_map = {}
        for display_name in sorted(skeys_map.keys()):
            plugin_name, qaction = skeys_map[display_name]
            possible_menus = lookup_menu_map.get(plugin_name, [])

            # Create a node for our top level plugin name
            tl = Item()
            tl.setText(0, display_name)
            tl.setData(0, Qt.UserRole, plugin_name)
            if plugin_name == 'Location Manager':
                # Special case handling
                tl.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                tl.setCheckState(0, Qt.PartiallyChecked)
                tl.setIcon(0, self._get_scaled_icon(get_icon('reader.png')))
                # Put all actions except library within this node.
                actions = self.gui.location_manager.all_actions[1:]
                self._populate_action_children(actions, tl, possible_menus, [], plugin_name,
                                               is_location_mgr_child=True)
            else:
                # Normal top-level checkable plugin iaction handling
                tl.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                tl.setCheckState(0, Qt.Unchecked)
                tl.setIcon(0, self._get_scaled_icon(qaction.icon()))

                # Lookup to see if we have a menu item for this top-level plugin
                if possible_menus:
                    fav_menu = self._is_in_menu(possible_menus)
                    if fav_menu is not None:
                        fav_menu['icon'] = tl.icon(0)
                        tl.setCheckState(0, Qt.Checked)
                m = qaction.menu()
                if m:
                    # Iterate through all the children of this node
                    self._populate_action_children(QMenu.actions(m), tl,
                                                   possible_menus, [], plugin_name)

            self.tv.addTopLevelItem(tl)
            self.top_level_items_map[plugin_name] = tl

    def _populate_action_children(self, children, parent, possible_menus, paths,
                                  plugin_name, is_location_mgr_child=False):
        for ac in children:
            if ac.isSeparator():
                continue
            if not ac.isVisible() and not is_location_mgr_child:
                # That is special case of location mgr visibility, since it has child
                # actions that will not be visible if device not plugged in at the
                # moment but we want to always be able to configure them.
                continue
            text = get_safe_title(ac)

            it = Item(parent)
            it.setText(0, text)
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            it.setCheckState(0, Qt.Unchecked)
            it.setIcon(0, self._get_scaled_icon(ac.icon()))

            new_paths = list(paths)
            new_paths.append(text)
            if possible_menus:
                fav_menu = self._is_in_menu(possible_menus, new_paths)
                if fav_menu is not None:
                    fav_menu['icon'] = it.icon(0)
                    it.setCheckState(0, Qt.Checked)
            if ac.menu():
                self._populate_action_children(QMenu.actions(ac.menu()), it,
                                               possible_menus, new_paths, plugin_name)

    def _is_in_menu(self, possible_menus, paths=[]):
        path_text = '|'.join(paths)
        for x in range(0, len(possible_menus)):
            fav_menu = possible_menus[x]
            if fav_menu['paths_text'] == path_text:
                del possible_menus[x]
                return fav_menu
        return None

    def _tree_item_changed(self, item, column):
        # Checkstate has been changed - are we adding or removing this item?
        if unicode(item.text(column)) == 'Location Manager':
            # Special case of not allowing this since it is not a "real" plugin,
            # just a special placeholder used for configuring menus that resolves
            # down to a collection of underlying actions.
            self.tv.blockSignals(True)
            item.setCheckState(column, Qt.PartiallyChecked)
            self.tv.blockSignals(False)
            return

        is_checked = item.checkState(column) == Qt.Checked
        paths = []
        fav_menu = {'icon':    item.icon(column),
                    'display': unicode(item.text(column)),
                    'path':    paths}
        while True:
            parent = item.parent()
            if parent is None:
                paths.insert(0, item.data(column, Qt.UserRole))
                break
            else:
                paths.insert(0, unicode(item.text(column)))
            item = parent

        if is_checked:
            # We want to add this item to the list
            self.items_list.populate_list_item(fav_menu)
            self.items_list.setCurrentRow(self.items_list.count() -1)
        else:
            # We want to remove the matching item from the list
            self.items_list.remove_matching_item(fav_menu)
            self._update_button_states()

    def save_settings(self):
        plugin_prefs[STORE_MENUS] = self.items_list.get_fav_menus()

