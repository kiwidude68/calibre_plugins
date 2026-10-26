from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import six
from six import text_type as unicode
from six.moves import range

try:
    from qt.core import (QWidget, QHBoxLayout, QMenu, QTreeWidget, Qt, QIcon,
                        QTreeWidgetItem, QSize, QInputDialog, QToolButton,
                        QVBoxLayout, QAbstractItemView, QBrush, QPushButton,
                        QUrl, QStyledItemDelegate, QStyleOptionViewItem)
except ImportError:                        
    from PyQt5.Qt import (QWidget, QHBoxLayout, QMenu, QTreeWidget, Qt, QIcon,
                        QTreeWidgetItem, QSize, QInputDialog, QToolButton,
                        QVBoxLayout, QAbstractItemView, QBrush, QPushButton,
                        QUrl, QStyledItemDelegate, QStyleOptionViewItem)

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


class ChildIndentDelegate(QStyledItemDelegate):

    INDENT = 12

    def paint(self, painter, option, index):
        if index.parent().isValid():
            option = QStyleOptionViewItem(option)
            option.rect.adjust(self.INDENT, 0, 0, 0)
        QStyledItemDelegate.paint(self, painter, option, index)

    def updateEditorGeometry(self, editor, option, index):
        if index.parent().isValid():
            option = QStyleOptionViewItem(option)
            option.rect.adjust(self.INDENT, 0, 0, 0)
        QStyledItemDelegate.updateEditorGeometry(self, editor, option, index)


class FavMenusListWidget(QTreeWidget):

    SEP = '--- ' + _('Separator') + ' ---'
    def __init__(self, parent):
        QTreeWidget.__init__(self, parent)
        self.header().hide()
        self.setItemDelegate(ChildIndentDelegate(self))
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.blank_icon = get_icon('blank.png')

    def populate_list(self, fav_menus):
        for fav_menu in fav_menus:
            if isinstance(fav_menu, dict) and 'group' in fav_menu:
                group = QTreeWidgetItem(self)
                group.setText(0, fav_menu['group'])
                group.setIcon(0, self.blank_icon)
                group.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
                group.setData(0, Qt.UserRole, ('group',))
                for child in fav_menu.get('items', []):
                    self.populate_list_item(child, group)
                group.setExpanded(True)
            else:
                self.populate_list_item(fav_menu)
        if fav_menus:
            self.setCurrentItem(self.topLevelItem(0))

    def populate_list_item(self, fav_menu, parent=None, idx=-1):
        self.blockSignals(True)
        if fav_menu is None:
            item = QTreeWidgetItem([self.SEP])
            item.setIcon(0, self.blank_icon)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setData(0, Qt.UserRole, ('separator',))
        else:
            text = fav_menu['display']
            item = QTreeWidgetItem([text])
            item.setFlags(Qt.ItemIsEditable | item.flags())
            paths = fav_menu['path']
            item.setToolTip(0, ' -> '.join(paths))
            item.setData(0, Qt.UserRole, ('shortcut', fav_menu))
            icon = fav_menu.get('icon', None)
            if icon is None:
                # This is a menu item that hasn't been found in this session
                # We will display it with a blank icon and disabled
                icon = self.blank_icon
                item.setForeground(0, QBrush(Qt.darkGray))
            item.setIcon(0, icon)
        if parent is not None:
            if idx < 0:
                parent.addChild(item)
            else:
                parent.insertChild(idx, item)
        elif idx < 0:
            self.addTopLevelItem(item)
        else:
            self.insertTopLevelItem(idx, item)
        self.blockSignals(False)

    def remove_matching_item(self, remove_fav_menu):
        paths_text = '/'.join(remove_fav_menu['path'])
        def remove_from(parent):
            count = self.topLevelItemCount() if parent is None else parent.childCount()
            for row in range(count):
                item = self.topLevelItem(row) if parent is None else parent.child(row)
                data = item.data(0, Qt.UserRole)
                if data and data[0] == 'shortcut':
                    if paths_text == '/'.join(data[1]['path']):
                        if parent is None:
                            self.takeTopLevelItem(row)
                        else:
                            parent.takeChild(row)
                        return True
                if remove_from(item):
                    return True
            return False
        remove_from(None)

    def get_fav_menus(self):
        def serialize(parent):
            count = self.topLevelItemCount() if parent is None else parent.childCount()
            entries = []
            for row in range(count):
                item = self.topLevelItem(row) if parent is None else parent.child(row)
                data = item.data(0, Qt.UserRole)
                if data and data[0] == 'separator':
                    if entries and row < count - 1 and entries[-1] is not None:
                        entries.append(None)
                elif data and data[0] == 'group':
                    entries.append({'group': unicode(item.text(0)).strip(),
                                    'items': serialize(item)})
                elif data and data[0] == 'shortcut':
                    fav_menu = data[1]
                    entries.append({'display': unicode(item.text(0)).strip(),
                                    'path': fav_menu['path']})
            return entries
        return serialize(None)

    def add_group(self, name):
        group = QTreeWidgetItem([name])
        group.setIcon(0, self.blank_icon)
        group.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
        group.setData(0, Qt.UserRole, ('group',))
        current = self.currentItem()
        if current is None:
            self.addTopLevelItem(group)
        else:
            if current.parent() is not None:
                current = current.parent()
            index = self.indexOfTopLevelItem(current)
            self.insertTopLevelItem(index + 1, group)
        group.setExpanded(True)
        self.setCurrentItem(group)

    def add_to_current_group(self, fav_menu):
        current = self.currentItem()
        if current is not None:
            data = current.data(0, Qt.UserRole)
            if data and data[0] == 'group':
                parent = current
                index = parent.childCount()
            elif current.parent() is not None and current.parent().data(0, Qt.UserRole)[0] == 'group':
                parent = current.parent()
                index = parent.indexOfChild(current) + 1
            else:
                parent = None
                index = self.indexOfTopLevelItem(current) + 1
        else:
            parent = None
            index = self.topLevelItemCount()
        self.populate_list_item(fav_menu, parent, index)
        item = parent.child(index) if parent is not None else self.topLevelItem(index)
        self.setCurrentItem(item)

    def add_separator_after_current(self):
        current = self.currentItem()
        if current is not None and current.data(0, Qt.UserRole)[0] == 'group':
            self.populate_list_item(None, current)
            self.setCurrentItem(current.child(current.childCount() - 1))
            return
        parent = current.parent() if current is not None else None
        index = ((parent.indexOfChild(current) if parent is not None else
                  self.indexOfTopLevelItem(current)) + 1) if current is not None else -1
        self.populate_list_item(None, parent, index)
        item = parent.child(index) if parent is not None and index >= 0 else (
            self.topLevelItem(index) if index >= 0 else self.topLevelItem(self.topLevelItemCount() - 1))
        self.setCurrentItem(item)


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
        self.items_list.currentItemChanged.connect(self._update_button_states)
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
        self.group_btn = QToolButton(self.gui)
        self.group_btn.setIcon(get_icon('images/add_group.png'))
        self.group_btn.setToolTip(_('Add a submenu group'))
        self.group_btn.clicked.connect(self._add_group)
        self.rename_btn = QToolButton(self.gui)
        self.rename_btn.setIcon(get_icon('edit-undo.png'))
        self.rename_btn.setToolTip(_('Rename the menu item for when it appears on your Favourites menu'))
        self.rename_btn.clicked.connect(self._rename_item)
        button_layout.addWidget(self.up_btn)
        button_layout.addStretch(1)
        button_layout.addWidget(self.rename_btn)
        button_layout.addStretch(1)
        button_layout.addWidget(self.group_btn)
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
        self._move_item(-1)

    def _move_item_down(self):
        self._move_item(1)

    def _move_item(self, offset):
        item = self.items_list.currentItem()
        if item is None:
            return
        parent = item.parent()
        index = parent.indexOfChild(item) if parent is not None else self.items_list.indexOfTopLevelItem(item)
        count = parent.childCount() if parent is not None else self.items_list.topLevelItemCount()
        target = index + offset
        data = item.data(0, Qt.UserRole)
        if parent is None:
            if target < 0 or target >= count:
                return
            adjacent = self.items_list.topLevelItem(target)
            adjacent_data = adjacent.data(0, Qt.UserRole)
            if data and data[0] == 'shortcut' and adjacent_data and adjacent_data[0] == 'group':
                item = self.items_list.takeTopLevelItem(index)
                if offset < 0:
                    adjacent.addChild(item)
                else:
                    adjacent.insertChild(0, item)
                adjacent.setExpanded(True)
            else:
                item = self.items_list.takeTopLevelItem(index)
                self.items_list.insertTopLevelItem(target, item)
        else:
            if 0 <= target < count:
                item = parent.takeChild(index)
                parent.insertChild(target, item)
            elif data and data[0] == 'shortcut':
                group_index = self.items_list.indexOfTopLevelItem(parent)
                item = parent.takeChild(index)
                self.items_list.insertTopLevelItem(
                    group_index if offset < 0 else group_index + 1, item)
            else:
                return
        self.items_list.setCurrentItem(item)
        self._update_button_states()

    def _add_group(self):
        name, ok = QInputDialog.getText(self, _('Add group'), _('Group name:'))
        name = unicode(name).strip()
        if ok and name:
            self.items_list.add_group(name)
            self._update_button_states()

    def _add_separator(self):
        self.items_list.add_separator_after_current()
        self._update_button_states()

    def _remove_item(self):

        item = self.items_list.currentItem()
        if item is None:
            return
        data = item.data(0, Qt.UserRole)
        if data and data[0] == 'shortcut':
            self.tv.blockSignals(True)
            self._uncheck_shortcut(data[1])
            self.tv.blockSignals(False)
        elif data and data[0] == 'group':
            group_index = self.items_list.indexOfTopLevelItem(item)
            promoted_item = None
            row = 0
            while item.childCount():
                child = item.takeChild(0)
                self.items_list.insertTopLevelItem(group_index + row, child)
                if promoted_item is None:
                    promoted_item = child
                row += 1
            self.items_list.takeTopLevelItem(self.items_list.indexOfTopLevelItem(item))
            if promoted_item is not None:
                self.items_list.setCurrentItem(promoted_item)
        else:
            parent = item.parent()
            if parent is None:
                self.items_list.takeTopLevelItem(self.items_list.indexOfTopLevelItem(item))
            else:
                parent.takeChild(parent.indexOfChild(item))
        self._update_button_states()

    def _uncheck_shortcut(self, fav_menu):
        def find_child(twi, paths):
            for i in range(twi.childCount()):
                child = twi.child(i)
                if unicode(child.text(0)) == paths[0]:
                    if len(paths) == 1:
                        return child
                    return find_child(child, paths[1:])

        paths = fav_menu['path']
        plugin = paths[0]
        tree_item = self.top_level_items_map.get(plugin)
        if tree_item is not None:
            if len(paths) > 1:
                tree_item = find_child(tree_item, paths[1:])
            if tree_item is not None:
                tree_item.setCheckState(0, Qt.Unchecked)

    def _rename_item(self):
        item = self.items_list.currentItem()
        if item is None:
            return
        data = item.data(0, Qt.UserRole)
        if data and data[0] == 'shortcut':
            self.items_list.editItem(item)
        elif data and data[0] == 'group':
            name, ok = QInputDialog.getText(self, _('Rename group'), _('Group name:'),
                                            text=item.text(0))
            name = unicode(name).strip()
            if ok and name:
                item.setText(0, name)

    def _update_button_states(self, *args):
        item = self.items_list.currentItem()
        if item is None:
            self.up_btn.setEnabled(False)
            self.down_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)
            self.sep_btn.setEnabled(self.items_list.topLevelItemCount() > 0)
            self.rename_btn.setEnabled(False)
            return
        parent = item.parent()
        index = parent.indexOfChild(item) if parent is not None else self.items_list.indexOfTopLevelItem(item)
        count = parent.childCount() if parent is not None else self.items_list.topLevelItemCount()
        data = item.data(0, Qt.UserRole)
        can_leave_group = parent is not None and data and data[0] == 'shortcut'
        self.up_btn.setEnabled(index > 0 or can_leave_group)
        self.down_btn.setEnabled(index < count - 1 or can_leave_group)
        self.remove_btn.setEnabled(True)
        self.sep_btn.setEnabled(True)
        self.rename_btn.setEnabled(bool(data) and data[0] in ('shortcut', 'group'))

    def _build_lookup_menu_map(self, fav_menus):
        m = {}
        for entry in fav_menus:
            if entry is None:
                continue
            entries = entry.get('items', []) if 'group' in entry else [entry]
            for fav_menu in entries:
                if fav_menu is None:
                    continue
                path = fav_menu['path']
                plugin = path[0]
                if plugin not in m:
                    m[plugin] = []
                fav_menu['paths_text'] = '|'.join(path[1:])
                m[plugin].append(fav_menu)
        return m

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
                tl.setIcon(0, get_icon('reader.png'))
                # Put all actions except library within this node.
                actions = self.gui.location_manager.all_actions[1:]
                self._populate_action_children(actions, tl, possible_menus, [], plugin_name,
                                               is_location_mgr_child=True)
            else:
                # Normal top-level checkable plugin iaction handling
                tl.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                tl.setCheckState(0, Qt.Unchecked)
                tl.setIcon(0, qaction.icon())

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
            it.setIcon(0, ac.icon())

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
            self.items_list.add_to_current_group(fav_menu)
        else:
            # We want to remove the matching item from the list
            self.items_list.remove_matching_item(fav_menu)
            self._update_button_states()

    def save_settings(self):
        plugin_prefs[STORE_MENUS] = self.items_list.get_fav_menus()

