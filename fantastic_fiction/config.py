from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from collections import OrderedDict
try:
    from qt.core import QLabel, QVBoxLayout, Qt, QGroupBox, QHBoxLayout, QCheckBox
except ImportError:
    from PyQt5.Qt import QLabel, QVBoxLayout, Qt, QGroupBox, QHBoxLayout, QCheckBox

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.gui2.metadata.config import ConfigWidget as DefaultConfigWidget
from calibre.utils.config import JSONConfig

from calibre_plugins.fantastic_fiction.common_widgets import KeyValueComboBox

STORE_NAME = 'Options'
KEY_GENRE_ACTION = 'genreAction'
KEY_REDUCE_HEADINGS = 'reduceHeadings'
KEY_OLDEST_EDITION = 'oldestEdition'

DEFAULT_STORE_VALUES = {
    KEY_GENRE_ACTION: 'DISCARD',
    KEY_REDUCE_HEADINGS: False,
    KEY_OLDEST_EDITION: False
}

GENRE_TYPES = OrderedDict([
                           ('DISCARD', 'Discard genre from comments'),
                           ('TAGS',    'Move genre into Tags column'),
                           ('KEEP',    'Keep genre in comments')
                           ])

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Fantastic Fiction')

# Set defaults
plugin_prefs.defaults[STORE_NAME] = DEFAULT_STORE_VALUES


class ConfigWidget(DefaultConfigWidget):

    def __init__(self, plugin):
        DefaultConfigWidget.__init__(self, plugin)
        c = plugin_prefs[STORE_NAME]

        options_group_box = QGroupBox(_('Other Options'), self)
        self.l.addWidget(options_group_box, self.l.rowCount(), 0, 1, 2)
        options_group_box_layout = QVBoxLayout()
        options_group_box.setLayout(options_group_box_layout)

        genre_layout = QHBoxLayout()
        options_group_box_layout.addLayout(genre_layout)

        genre_label = QLabel(_('If genre found in comments:'), self)
        genre_label.setToolTip(_('A subset (at this time) of the books in Fantastic Fiction\n'
                               'contain a hyperlinked Genre at the bottom of the comments.'))
        genre_layout.addWidget(genre_label)
        self.genreCombo = KeyValueComboBox(self, GENRE_TYPES, c.get(KEY_GENRE_ACTION, 'KEEP'))
        genre_layout.addWidget(self.genreCombo)

        self.headings_checkbox = QCheckBox(_('Reduce header sizes in comments'), self)
        self.headings_checkbox.setToolTip(_('For some books the website book description uses larger heading\n'
                               'tags that look out of place inside a calibre library.\n'
                               'Enabling this option reduces those header tags in size values'))
        options_group_box_layout.addWidget(self.headings_checkbox)
        reduce_headings = c.get(KEY_REDUCE_HEADINGS, False)
        self.headings_checkbox.setChecked(reduce_headings)
        
        self.oldest_edition_checkbox = QCheckBox(_('Use publishing date from oldest edition'), self)
        self.oldest_edition_checkbox.setToolTip(_('The year the book was first published is shown with the title. '
                                                  'The editions include the publishing month. '
                                                  'Select this option if you want to use the oldest edition from the year of publishing.'))
        options_group_box_layout.addWidget(self.oldest_edition_checkbox)
        oldest_edition = c.get(KEY_OLDEST_EDITION, False)
        self.oldest_edition_checkbox.setChecked(oldest_edition)
        
        options_group_box_layout.addStretch(1)

    def commit(self):
        DefaultConfigWidget.commit(self)
        new_prefs = {}
        new_prefs[KEY_GENRE_ACTION] = self.genreCombo.selected_key()
        new_prefs[KEY_REDUCE_HEADINGS] = self.headings_checkbox.checkState() == Qt.Checked
        new_prefs[KEY_OLDEST_EDITION] = self.oldest_edition_checkbox.checkState() == Qt.Checked
        plugin_prefs[STORE_NAME] = new_prefs
