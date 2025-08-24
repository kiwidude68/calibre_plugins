from __future__ import absolute_import, division, print_function, unicode_literals

__license__   = 'GPL v3'
__copyright__ = '2011, un_pogaz'

# Allow fix actions to be called by the "Action Chains" plugin

try:
    from qt.core import (QAbstractItemView, QListWidget, QListWidgetItem,
        QRadioButton, QSize, Qt, QVBoxLayout, QWidget)
except:
    from PyQt5.Qt import (QAbstractItemView, QListWidget, QListWidgetItem,
        QRadioButton, QSize, Qt, QVBoxLayout, QWidget)

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre_plugins.action_chains.actions.base import ChainAction
from calibre_plugins.quality_check.check_fix import FixCheck
from calibre_plugins.quality_check.common_icons import get_icon
from calibre_plugins.quality_check.config import PLUGIN_FIX_MENUS, SCOPE_SELECTION


class RunQualityCheckAction(ChainAction):

    name = 'Run Quality Check fix'
    support_scopes = False

    def run(self, gui, settings, chain):
        book_ids = chain.scope().get_book_ids()
        if not book_ids:
            # empty ids list perform action on the all library
            return
        check = FixCheck(gui)
        check.set_search_scope(SCOPE_SELECTION, book_ids)
        check.menu_key = settings['menu_key']
        check.perform_check(check.menu_key)

    def validate(self, settings):
        if not settings or not settings['menu_key']:
            return _('No action selected'), _('No Quality Check fix action has been selected.')
        if not settings['menu_key'] not in PLUGIN_FIX_MENUS:
            return _('Invalid action selected'), _('The Quality Check fix action is unknown and not supported.')
        return True

    def config_widget(self):
        return ConfigWidget


class ConfigWidget(QWidget):
    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        self.gui = plugin_action.gui
        self.db = self.gui.current_db
        self._init_controls()

    def _init_controls(self):
        self.setMinimumSize(300,100)
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        self.fix_list = FixListWidget(self)
        self._layout.addWidget(self.fix_list)

    def load_settings(self, settings):
        if not settings:
            settings = {}
        self.fix_list.set_action(settings.get('menu_key'))

    def save_settings(self):
        settings = {}
        settings['menu_key'] = self.fix_list.selected_action()
        return settings

    validate = RunQualityCheckAction.validate

class FixListWidget(QListWidget):
    def __init__(self, parent=None):
        QListWidget.__init__(self, parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setIconSize(QSize(16,16))
        self._items = []
        self.populate()

    def populate(self):
        self._items = []
        self.clear()
        for key, value in PLUGIN_FIX_MENUS.items():
            item = QListWidgetItem(self)
            item.setIcon(get_icon(value['image']))
            item.setData(Qt.UserRole, key)
            radio = QRadioButton(value['name'], self)
            self.setItemWidget(item, radio)
            self._items.append((radio, key))

    def selected_action(self):
        for radio, key in self._items:
            if radio.isChecked():
                return key

    def set_action(self, value):
        for radio, key in self._items:
            if key == value:
                radio.setChecked(True)
