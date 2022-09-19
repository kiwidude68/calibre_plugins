from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

try:
    from qt.core import QToolButton
except ImportError:
    from PyQt5.Qt import QToolButton

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.gui2.actions import InterfaceAction

from calibre_plugins.import_list.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.import_list.wizards import ImportListWizard

PLUGIN_ICONS = ['images/import_list.png', 'images/script.png', 'images/color.png',
                'images/category.png', 'images/web.png', 'images/browser.png',
                'images/regex.png', 'images/regex_specified.png',
                'images/ellipses.png']

class ImportListAction(InterfaceAction):

    name = 'Import List'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (_('Import List'), None, _('Import a list from the clipboard, CSV File or web page'), None)
    popup_type = QToolButton.InstantPopup
    action_type = 'current'

    current_instance = None
    reading_list_plugin = None

    def genesis(self):
        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)

        # Assign our menu to this action and an icon
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.qaction.triggered.connect(self.show_import_list)
        
        self.api_version = 1.0

    def library_changed(self, db):
        if self.current_instance and not self.current_instance.is_closed:
            self.current_instance.close()
            self.current_instance = None

    def show_import_list(self):
        if self.current_instance:
            if not self.current_instance.is_closed:
                return
            self.current_instance = None

        self.reading_list_plugin = self.gui.iactions.get('Reading List', None)
        self.current_instance = ImportListWizard(self, self.reading_list_plugin)
        self.current_instance.show()

