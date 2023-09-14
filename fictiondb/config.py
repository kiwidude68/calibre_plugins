from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

try:
    from qt.core import (QVBoxLayout, Qt, QGroupBox, QCheckBox)
except:
    from PyQt5.Qt import (QVBoxLayout, Qt, QGroupBox, QCheckBox)

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.gui2.metadata.config import ConfigWidget as DefaultConfigWidget
from calibre.utils.config import JSONConfig

STORE_NAME = 'Options'
KEY_GET_GENRE_AS_TAGS          = 'getGenreAsTags'
KEY_GET_SUB_GENRE_AS_TAGS      = 'getSubGenreAsTags'
KEY_GET_THEMES_AS_TAGS         = 'getThemesAsTags'
KEY_GET_AGE_LEVEL_AS_TAGS      = 'getAgeLevelAsTags'

DEFAULT_STORE_VALUES = {
    KEY_GET_GENRE_AS_TAGS: True,
    KEY_GET_SUB_GENRE_AS_TAGS: False,
    KEY_GET_THEMES_AS_TAGS: False,
    KEY_GET_AGE_LEVEL_AS_TAGS: False
}

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/FictionDB')

# Set defaults
plugin_prefs.defaults[STORE_NAME] = DEFAULT_STORE_VALUES

def get_option(option_name):
    return plugin_prefs[STORE_NAME].get(option_name, DEFAULT_STORE_VALUES[option_name])

class ConfigWidget(DefaultConfigWidget):

    def __init__(self, plugin):
        DefaultConfigWidget.__init__(self, plugin)
        c = plugin_prefs[STORE_NAME]

        other_group_box = QGroupBox(_('Other options'), self)
        self.l.addWidget(other_group_box, self.l.rowCount(), 0, 1, 2)
        other_group_box_layout = QVBoxLayout()
        other_group_box.setLayout(other_group_box_layout)

        self.get_genre_as_tags_checkbox = QCheckBox(_('Include \'Genres\' in the Tags column'), self)
        self.get_genre_as_tags_checkbox.setToolTip(_('When checked if a book has any genres defined they will be\n'
                                                   'returned in the Tags column from this plugin.'))
        self.get_genre_as_tags_checkbox.setChecked(get_option(KEY_GET_GENRE_AS_TAGS))
        other_group_box_layout.addWidget(self.get_genre_as_tags_checkbox)

        self.get_sub_genres_as_tags_checkbox = QCheckBox(_('Include \'Sub-Genres\' in the Tags column'), self)
        self.get_sub_genres_as_tags_checkbox.setToolTip(_('When checked if a book has any Sub-Genres defined they will be\n'
                                                        'returned in the Tags column from this plugin.'))
        self.get_sub_genres_as_tags_checkbox.setChecked(get_option(KEY_GET_SUB_GENRE_AS_TAGS))
        other_group_box_layout.addWidget(self.get_sub_genres_as_tags_checkbox)

        self.get_themes_as_tags_checkbox = QCheckBox(_('Include \'Themes\' in the Tags column'), self)
        self.get_themes_as_tags_checkbox.setToolTip(_('When checked if a book has any Themes defined it will be\n'
                                                         'returned in the Tags column from this plugin.'))
        self.get_themes_as_tags_checkbox.setChecked(get_option(KEY_GET_THEMES_AS_TAGS))
        other_group_box_layout.addWidget(self.get_themes_as_tags_checkbox)

        self.get_age_level_as_tags_checkbox = QCheckBox(_("Include 'Age Level' in the Tags column"), self)
        self.get_age_level_as_tags_checkbox.setToolTip(_("When checked, if a book has an 'Age Level' defined it will be\n"
                                                         "returned in the Tags column from this plugin."))
        self.get_age_level_as_tags_checkbox.setChecked(get_option(KEY_GET_AGE_LEVEL_AS_TAGS))
        other_group_box_layout.addWidget(self.get_age_level_as_tags_checkbox)
        
        other_group_box_layout.addStretch(1)

    def commit(self):
        DefaultConfigWidget.commit(self)

        new_prefs = {}
        new_prefs[KEY_GET_GENRE_AS_TAGS] = self.get_genre_as_tags_checkbox.checkState() == Qt.Checked
        new_prefs[KEY_GET_SUB_GENRE_AS_TAGS] = self.get_sub_genres_as_tags_checkbox.checkState() == Qt.Checked
        new_prefs[KEY_GET_THEMES_AS_TAGS] = self.get_themes_as_tags_checkbox.checkState() == Qt.Checked
        new_prefs[KEY_GET_AGE_LEVEL_AS_TAGS]      = self.get_age_level_as_tags_checkbox.checkState() == Qt.Checked

        plugin_prefs[STORE_NAME] = new_prefs

