from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

import copy, os, shutil
import six
from six import text_type as unicode

try:
    from qt.core import (QWidget, QVBoxLayout, QPushButton, QGridLayout,
                        QLabel, QLineEdit, QGroupBox, QUrl)
except ImportError:
    from PyQt5.Qt import (QWidget, QVBoxLayout, QPushButton, QGridLayout,
                        QLabel, QLineEdit, QGroupBox, QUrl)

from calibre import prints
from calibre.constants import DEBUG
from calibre.gui2 import open_url
from calibre.utils.config import JSONConfig, config_dir

from calibre_plugins.generate_cover.common_icons import get_icon
from calibre_plugins.generate_cover.common_dialogs import KeyboardConfigDialog, PrefsViewerDialog
from calibre_plugins.generate_cover.common_widgets import CustomColumnComboBox

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/Generate-Cover'

STORE_SCHEMA_VERSION = 'SchemaVersion'
DEFAULT_SCHEMA_VERSION = 2.21

PREFS_NAMESPACE = 'GenerateCoverPlugin'
PREFS_KEY_SETTINGS = 'settings'
PREFS_KEY_UPDATE_COLUMN = 'updateColumn'
PREFS_KEY_UPDATE_VALUE = 'updateValue'
PREFS_LIBRARY_DEFAULT = { PREFS_KEY_UPDATE_COLUMN: '',
                          PREFS_KEY_UPDATE_VALUE:  '',
                          STORE_SCHEMA_VERSION: DEFAULT_SCHEMA_VERSION }

STORE_SAVED_SETTINGS = 'SavedSettings'

STORE_CURRENT = 'Current'
KEY_DEFAULT = '{Default}'
KEY_NAME = 'name'
KEY_IMAGE_FILE = 'imageFile'
KEY_SWAP_AUTHOR = 'swapAuthor'
KEY_BACKGROUND_IMAGE = 'backgroundImage'
KEY_RESIZE_IMAGE_TO_FIT = 'resizeImageToFit'
KEY_RESIZE_TO_IMAGE = 'resizeToImage'
KEY_SIZE = 'size'
KEY_MARGINS = 'margins'
KEY_BORDERS = 'borders'
KEY_COLORS = 'colors'
KEY_COLOR_APPLY_STROKE = 'colorApplyStroke'
KEY_FONTS = 'fonts'
KEY_FONTS_LINKED = 'fontsLinked'
KEY_FONTS_AUTOREDUCED = 'fontsAutoReduced'
KEY_FIELD_ORDER = 'fieldOrder'
KEY_CUSTOM_TEXT = 'customText'
KEY_SERIES_TEXT = 'seriesText'

DEFAULT_SERIES_TEXT = 'Book {series_index} of {series}'

STORE_FILES = 'Files'
TOKEN_CURRENT_COVER = '{Current Cover}'
TOKEN_DEFAULT_COVER = '{Default Image}'
TOKEN_COVERS = [TOKEN_CURRENT_COVER, TOKEN_DEFAULT_COVER]

STORE_OTHER_OPTIONS = 'OtherOptions'
KEY_AUTOSAVE = 'autoSave'
DEFAULT_OTHER_OPTIONS = { KEY_AUTOSAVE: False }

DEFAULT_CURRENT = {
    KEY_NAME: KEY_DEFAULT,
    KEY_IMAGE_FILE: I('library.png'),
    KEY_SWAP_AUTHOR: False,
    KEY_BACKGROUND_IMAGE: False,
    KEY_RESIZE_IMAGE_TO_FIT: False,
    KEY_RESIZE_TO_IMAGE: False,
    KEY_SIZE: (590, 750),
    KEY_MARGINS: { 'top': 10, 'bottom': 10, 'left': 0, 'right': 0, 'image': 10, 'text': 30 },
    KEY_BORDERS: { 'coverBorder': 0, 'imageBorder': 0, },
    KEY_COLORS: { 'border': '#000000', 'background': '#ffffff',
                     'fill': '#000000', 'stroke': '#000000' },
    KEY_COLOR_APPLY_STROKE: False,
    KEY_FONTS: { 'title':  { 'name': None, 'size': 46, 'align': 'center' },
                 'author': { 'name': None, 'size': 36, 'align': 'center' },
                 'series': { 'name': None, 'size': 36, 'align': 'center' },
                 'custom': { 'name': None, 'size': 24, 'align': 'center' } },
    KEY_FONTS_LINKED: True,
    KEY_FONTS_AUTOREDUCED: False,
    KEY_FIELD_ORDER: [{'name': 'Title',  'display': True},
                         {'name': 'Author', 'display': True},
                         {'name': 'Series', 'display': True},
                         {'name': 'Image',  'display': True},
                         {'name': 'Custom Text', 'display': False}],
    KEY_CUSTOM_TEXT: '',
    KEY_SERIES_TEXT: DEFAULT_SERIES_TEXT
}

DEFAULT_SETTINGS = { KEY_DEFAULT: DEFAULT_CURRENT }

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Generate Cover')

# Set defaults
plugin_prefs.defaults[STORE_SAVED_SETTINGS] = copy.deepcopy(DEFAULT_SETTINGS)
plugin_prefs.defaults[STORE_CURRENT] = copy.deepcopy(DEFAULT_CURRENT)
plugin_prefs.defaults[STORE_FILES] = [TOKEN_CURRENT_COVER, I('library.png')]
plugin_prefs.defaults[STORE_OTHER_OPTIONS] = copy.deepcopy(DEFAULT_OTHER_OPTIONS)

def get_images_dir():
    return os.path.join(config_dir, 'plugins/Generate Cover')

def show_help():
    open_url(QUrl(HELP_URL))


def migrate_image_file_path(path):
    # Version 1.5.3 changed image paths to be stored as relative to the calibre config
    # folder and to use a token to represent the default library image
    if path in TOKEN_COVERS:
        return path
    if os.path.basename(path) == 'library.png':
        return TOKEN_DEFAULT_COVER
    if os.path.isabs(path):
        # Make the path relative to our generate cover images folder
        return os.path.relpath(path, get_images_dir())

def migrate_image_file(path):
    # Version 2.2.1 moved GC images to
    # <calibre>/plugins/Generate Cover because cal5->6 migration can
    # delete contents of <calibre>/resources/images
    old_images_dir = os.path.join(config_dir, 'resources/images/generate_cover')
    if path in TOKEN_COVERS:
        return path
    if os.path.basename(path) == 'library.png':
        return TOKEN_DEFAULT_COVER
    old_file = os.path.join(old_images_dir, path)
    new_file = os.path.join(get_images_dir(), path)
    if DEBUG:
        prints('Copying existing cover image:')
        prints(old_file)
        prints(new_file)
    if os.path.exists(old_file):
        if not os.path.exists(get_images_dir()):
            os.makedirs(get_images_dir())
        shutil.move(old_file,new_file)
    return path

def remove_old_images_folder_if_empty():
    old_images_dir = os.path.join(config_dir, 'resources/images/generate_cover')
    try:
        if len(os.listdir(old_images_dir)) == 0:
            os.rmdir(old_images_dir)
    except:
        if DEBUG:
            prints('Failed to remove old images folder')
        pass
  

def migrate_config_if_required():
    # Contains code for migrating versions of json schema
    # Make sure we store our schema version in the file
    schema_version = plugin_prefs.get(STORE_SCHEMA_VERSION, 0)
    if schema_version != DEFAULT_SCHEMA_VERSION:
        plugin_prefs[STORE_SCHEMA_VERSION] = DEFAULT_SCHEMA_VERSION

    # Ensure our token for the current cover is in the files store (v1.35)
    files = plugin_prefs[STORE_FILES]
    if TOKEN_CURRENT_COVER not in files:
        files.insert(0, TOKEN_CURRENT_COVER)
        plugin_prefs[STORE_FILES] = files

    # Upgrading to 1.5, need to fix corrupted settings from earlier bug which
    # mean't the internal setting name differed from the dictionary key.
    if schema_version < 1.5:
        if DEBUG:
            prints('Generate Cover - Upgrading from schema:', schema_version)
        saved_settings = plugin_prefs[STORE_SAVED_SETTINGS]
        for setting_name, saved_setting in six.iteritems(saved_settings):
            if saved_setting[KEY_NAME] == 'Current':
                continue
            if setting_name != saved_setting[KEY_NAME]:
                if DEBUG:
                    prints('Generate Cover - Fixing saved setting:', setting_name, saved_setting[KEY_NAME])
                saved_setting[KEY_NAME] = setting_name
        plugin_prefs[STORE_SAVED_SETTINGS] = saved_settings

    # Version 1.5.3 changed image paths to be stored as relative to the calibre config
    # folder and to use a token to represent the default library image
    if schema_version < 1.53:
        files = [migrate_image_file_path(f) for f in plugin_prefs[STORE_FILES]]
        plugin_prefs[STORE_FILES] = files

    if schema_version < 1.59:
        if DEBUG:
            prints('Generate Cover - Upgrading from schema:', schema_version)
        current = plugin_prefs[STORE_CURRENT]
        plugin_prefs[STORE_CURRENT] = migrate_config_setting(schema_version, STORE_CURRENT, current, is_current=True)

        saved_settings = plugin_prefs[STORE_SAVED_SETTINGS]
        for setting_name, saved_setting in six.iteritems(saved_settings):
            migrate_config_setting(schema_version, setting_name, saved_setting)
        plugin_prefs[STORE_SAVED_SETTINGS] = saved_settings

    # Version 2.2.1 changed images to be stored in the calibre/plugins
    # folder
    if schema_version < 2.21:
        if DEBUG:
            prints('Generate Cover - Upgrading to 2.21 schema')
        files = [migrate_image_file(f) for f in plugin_prefs[STORE_FILES]]
        plugin_prefs[STORE_FILES] = files
        # Remove the old folder to prevent confusion if it is now empty
        remove_old_images_folder_if_empty()

def migrate_config_setting(schema_version, setting_name, setting, is_current=False):
    # To upgrade to 1.2 we need to add a schema version and
    # ensure that all settings have a 'Custom Text' entry
    if schema_version < 1.2:
        if DEBUG:
            prints('Generate Cover - Upgrading to 1.2 schema for setting: ',setting_name)
        if len(setting[KEY_FIELD_ORDER]) == 4:
            setting[KEY_FIELD_ORDER].append({'name': 'Custom Text', 'display':False})
        if 'custom' not in setting[KEY_FONTS]:
            setting[KEY_FONTS]['custom'] = { 'name': None, 'size': 24 }
        setting[KEY_CUSTOM_TEXT] = ''
        setting[KEY_FONTS_AUTOREDUCED] = False

    # To upgrade to 1.5 we need to copy the settings for left margin into a right margin
    # and support an alignment option for each text (font) item.
    if schema_version < 1.5:
        if DEBUG:
            prints('Generate Cover - Upgrading to 1.50 schema for setting: ',setting_name)
        if 'right' not in setting[KEY_MARGINS]:
            setting[KEY_MARGINS]['right'] = setting[KEY_MARGINS]['left']
        for value_map in six.itervalues(setting[KEY_FONTS]):
            if 'align' not in value_map:
                value_map['align'] = 'center'

    # Version 1.5.2 added the option to autosize the cover to the background image chosen
    if schema_version < 1.52:
        if DEBUG:
            prints('Generate Cover - Upgrading to 1.52 schema for setting: ',setting_name)
        if KEY_RESIZE_TO_IMAGE not in setting:
            setting[KEY_RESIZE_TO_IMAGE] = False

    # Version 1.5.3 changed image paths to be stored as relative to the calibre config
    # folder and to use a token to represent the default library image
    if schema_version < 1.53:
        if DEBUG:
            prints('Generate Cover - Upgrading to 1.53 schema for setting: ',setting_name)
        setting[KEY_IMAGE_FILE] = migrate_image_file_path(setting[KEY_IMAGE_FILE])

    # Version 1.5.4 added a series text field
    if schema_version < 1.54:
        if DEBUG:
            prints('Generate Cover - Upgrading to 1.54 schema for setting: ',setting_name)
        setting[KEY_SERIES_TEXT] = DEFAULT_SERIES_TEXT

    # Version 1.5.8 attempts to fix corrupted config files where the "name" element
    # does not match the parent dictionary key.
    if schema_version < 1.58 and not is_current:
        if setting[KEY_NAME] != setting_name:
            if DEBUG:
                prints('Generate Cover - Fixing corrupted setting name from: ', setting[KEY_NAME], ' to:', setting_name)
                setting[KEY_NAME] = setting_name

    # Version 1.5.13 (which will call 1.5.9 to make the < work!) added a resize image to fit setting
    if schema_version < 1.59:
        if DEBUG:
            prints('Generate Cover - Upgrading to 1.59 schema for setting: ',setting_name)
        setting[KEY_RESIZE_IMAGE_TO_FIT] = False
    return setting

    # Version 2.2.1 changed images to be stored in the calibre/plugins
    # folder
    if schema_version < 2.21:
        if DEBUG:
            prints('Generate Cover - Upgrading to 2.21 schema for setting: ',setting_name)
        setting[KEY_IMAGE_FILE] = migrate_image_file(setting[KEY_IMAGE_FILE])


def migrate_library_config_if_required(db, library_config):
    schema_version = library_config.get(STORE_SCHEMA_VERSION, 0)
    if schema_version == DEFAULT_SCHEMA_VERSION:
        return
    # We have changes to be made - mark schema as updated
    library_config[STORE_SCHEMA_VERSION] = DEFAULT_SCHEMA_VERSION

def get_library_config(db):
    library_config = db.prefs.get_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS, copy.deepcopy(PREFS_LIBRARY_DEFAULT))
    migrate_library_config_if_required(db, library_config)
    return library_config

def set_library_config(db, library_config):
    db.prefs.set_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS, library_config)


class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        self.column_keys = self.plugin_action.gui.current_db.field_metadata.displayable_field_keys()
        self.library_config = get_library_config(plugin_action.gui.current_db)
        self._initialise_controls()

    def _initialise_controls(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        cust_col = self.library_config.get(PREFS_KEY_UPDATE_COLUMN, '')
        cust_val = self.library_config.get(PREFS_KEY_UPDATE_VALUE, '')

        content_groupbox = QGroupBox(_('After generating cover:'), self)
        layout.addWidget(content_groupbox)

        col_layout = QGridLayout()
        content_groupbox.setLayout(col_layout)
        update_custom_columns = self._get_custom_columns(['text','bool'])
        self.update_column_combo = CustomColumnComboBox(self, update_custom_columns, cust_col, ['', 'tags'])
        self.update_column_combo.setMinimumWidth(120)
        self.update_value_ledit = QLineEdit(cust_val, self)
        col_layout.addWidget(QLabel(_('Update column:'), self), 0, 0, 1, 1)
        col_layout.addWidget(QLabel(_('Update value:'), self), 1, 0, 1, 1)
        col_layout.addWidget(self.update_column_combo, 0, 1, 1, 1)
        col_layout.addWidget(self.update_value_ledit, 1, 1, 1, 1)

        keyboard_shortcuts_button = QPushButton(_('Keyboard shortcuts')+'...', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self._edit_shortcuts)
        layout.addWidget(keyboard_shortcuts_button)

        view_prefs_button = QPushButton(_('View library preferences')+'...', self)
        view_prefs_button.setToolTip(_('View data stored in the library database for this plugin'))
        view_prefs_button.clicked.connect(self._view_prefs)
        layout.addWidget(view_prefs_button)

        help_button = QPushButton(' '+_('&Help'), self)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(show_help)
        layout.addWidget(help_button)

    def _get_custom_columns(self, column_types):
        custom_columns = self.plugin_action.gui.library_view.model().custom_columns
        available_columns = {}
        for key, column in six.iteritems(custom_columns):
            typ = column['datatype']
            if typ in column_types:
                available_columns[key] = column
        return available_columns

    def _edit_shortcuts(self):
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()

    def _view_prefs(self):
        d = PrefsViewerDialog(self.plugin_action.gui, PREFS_NAMESPACE)
        d.exec_()

    def save_settings(self):
        self.library_config[PREFS_KEY_UPDATE_COLUMN] = self.update_column_combo.get_selected_column()
        self.library_config[PREFS_KEY_UPDATE_VALUE] = unicode(self.update_value_ledit.text()).strip()
        set_library_config(self.plugin_action.gui.current_db, self.library_config)


# Ensure our config gets migrated
migrate_config_if_required()
