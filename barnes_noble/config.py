from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from six import text_type as unicode
# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import QLabel, QHBoxLayout, QVBoxLayout, Qt, QGroupBox, QCheckBox, QSpinBox
except ImportError:
    from PyQt5.Qt import QLabel, QHBoxLayout, QVBoxLayout, Qt, QGroupBox, QCheckBox, QSpinBox
from calibre.gui2.metadata.config import ConfigWidget as DefaultConfigWidget
from calibre.utils.config import JSONConfig

# Pull in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

STORE_NAME = 'Options'
KEY_MAX_DOWNLOADS = 'maxDownloads'
KEY_GET_ALL_AUTHORS = 'getAllAuthors'

DEFAULT_STORE_VALUES = {
    KEY_MAX_DOWNLOADS: 1,
    KEY_GET_ALL_AUTHORS: False
}

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Barnes & Noble')

# Set defaults
plugin_prefs.defaults[STORE_NAME] = DEFAULT_STORE_VALUES

class ConfigWidget(DefaultConfigWidget):

    def __init__(self, plugin):
        DefaultConfigWidget.__init__(self, plugin)
        c = plugin_prefs[STORE_NAME]

        options_group_box = QGroupBox('Other Options', self)
        options_group_box_layout = QVBoxLayout()
        options_group_box.setLayout(options_group_box_layout)
        self.l.addWidget(options_group_box, self.l.rowCount(), 0, 1, 2)

        other_group_box_layout = QHBoxLayout()
        max_label = QLabel(_('Maximum title/author search matches to evaluate (1 = fastest):'), self)
        max_label.setToolTip(_('Increasing this value will consider more editions but also increase search times.\n\n'
                             'This will increase the potential likelihood of getting a larger cover image\n'
                             'but does not guarantee it.'))
        other_group_box_layout.addWidget(max_label)
        self.max_downloads_spin = QSpinBox(self)
        self.max_downloads_spin.setMinimum(1)
        self.max_downloads_spin.setMaximum(5)
        self.max_downloads_spin.setProperty('value', c.get(KEY_MAX_DOWNLOADS, DEFAULT_STORE_VALUES[KEY_MAX_DOWNLOADS]))
        other_group_box_layout.addWidget(self.max_downloads_spin)
        other_group_box_layout.addStretch(1)
        options_group_box_layout.addLayout(other_group_box_layout)

        self.all_authors_checkbox = QCheckBox(_('Get all contributing authors (e.g. editors, illustrators etc)'), self)
        self.all_authors_checkbox.setToolTip(_('When this option is checked, all authors are retrieved.\n\n'
                                              'When unchecked (default) only the primary author(s) are returned.'))
        self.all_authors_checkbox.setChecked(c.get(KEY_GET_ALL_AUTHORS, DEFAULT_STORE_VALUES[KEY_GET_ALL_AUTHORS]))
        options_group_box_layout.addWidget(self.all_authors_checkbox)
        
        options_group_box_layout.addStretch(1)

    def commit(self):
        DefaultConfigWidget.commit(self)
        new_prefs = {}
        new_prefs[KEY_MAX_DOWNLOADS] = int(unicode(self.max_downloads_spin.value()))
        new_prefs[KEY_GET_ALL_AUTHORS] = self.all_authors_checkbox.checkState() == Qt.Checked
        plugin_prefs[STORE_NAME] = new_prefs
