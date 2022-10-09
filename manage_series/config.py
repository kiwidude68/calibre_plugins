from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import os
try:
    from qt.core import QWidget, QVBoxLayout, QPushButton, QUrl
except ImportError:
    from PyQt5.Qt import QWidget, QVBoxLayout, QPushButton, QUrl

from calibre.gui2 import open_url
from calibre.utils.config import config_dir

from calibre_plugins.manage_series.common_icons import get_icon
from calibre_plugins.manage_series.common_dialogs import KeyboardConfigDialog

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/Manage-Series'

# Delete the legacy config file if it exists as plugin no longer stores any configuration
old_json_path = os.path.join(config_dir,'plugins/Manage Series.json')
if os.path.exists(old_json_path):
    os.remove(old_json_path)

def show_help():
    open_url(QUrl(HELP_URL))


class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        keyboard_shortcuts_button = QPushButton(_('Keyboard shortcuts')+'...', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        layout.addWidget(keyboard_shortcuts_button)

        help_button = QPushButton(' '+_('&Help'), self)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(show_help)
        layout.addWidget(help_button)

    def save_settings(self):
        # No longer used
        pass

    def edit_shortcuts(self):
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()
