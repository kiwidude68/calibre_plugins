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
DEFAULT_SCHEMA_VERSION = 2.52

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
KEY_IMAGE_BORDER_COLOR = 'image_border'
KEY_FILL_COLORS_LINKED = 'fillColorsLinked'
KEY_FONTS = 'fonts'
KEY_FONTS_LINKED = 'fontsLinked'
KEY_FONTS_AUTOREDUCED = 'fontsAutoReduced'
KEY_FIELD_ORDER = 'fieldOrder'
KEY_CUSTOM_TEXT = 'customText'
KEY_CUSTOM_TEXT_2 = 'customText2'
KEY_CUSTOM_TEXT_3 = 'customText3'
KEY_CUSTOM_TEXT_FIELDS = (KEY_CUSTOM_TEXT, KEY_CUSTOM_TEXT_2, KEY_CUSTOM_TEXT_3)
KEY_SERIES_TEXT = 'seriesText'
KEY_FIELD_BACKDROP_PADDING = 'padding'
KEY_FIELD_IMAGE_PADDING = 'padding'
KEY_FIELD_TEXT_PADDING = 'textPadding'
KEY_FIELD_ROTATION = 'rotation'
KEY_FIELD_ROTATION_SIDE = 'rotationSide'
KEY_FIELD_BACKDROP = 'backdrop'
KEY_FIELD_BACKDROP_FULL_WIDTH = 'backdropFullWidth'
KEY_ELEMENT_BACKDROP_COLOR = 'elementBackdropColor'
KEY_ELEMENT_BACKDROP_OPACITY = 'elementBackdropOpacity'
KEY_FIELD_BACKDROP_COLOR = 'backdropColor'
KEY_FIELD_BACKDROP_OPACITY = 'backdropOpacity'
KEY_BACKDROPS_LINKED = 'backdropsLinked'

DEFAULT_SERIES_TEXT = 'Book {series_index} of {series}'
DEFAULT_PADDING = {'top': 0, 'bottom': 0, 'left': 0, 'right': 0}
DEFAULT_ELEMENT_OPTIONS = {
    KEY_FIELD_BACKDROP_PADDING: dict(DEFAULT_PADDING, top=4),
    KEY_FIELD_TEXT_PADDING: dict(DEFAULT_PADDING, top=30),
    KEY_FIELD_ROTATION: 0,
    KEY_FIELD_ROTATION_SIDE: 'left',
    KEY_FIELD_BACKDROP: False,
    KEY_FIELD_BACKDROP_FULL_WIDTH: False,
    KEY_FIELD_BACKDROP_COLOR: '#000000',
    KEY_FIELD_BACKDROP_OPACITY: 70,
}

DEFAULT_IMAGE_OPTIONS = {
    KEY_FIELD_IMAGE_PADDING: dict(DEFAULT_PADDING)
}

def default_field(name, display):
    field = copy.deepcopy(DEFAULT_ELEMENT_OPTIONS)
    field.update({'name': name, 'display': display})
    return field

def default_image_field(name, display):
    field = copy.deepcopy(DEFAULT_IMAGE_OPTIONS)
    field.update({'name': name, 'display': display})
    return field

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
    KEY_MARGINS: { 'top': 10, 'bottom': 10, 'left': 0, 'right': 0,
                   'image': dict(DEFAULT_PADDING, top=10) },
    KEY_BORDERS: { 'coverBorder': 0, 'imageBorder': 0, },
    KEY_COLORS: { 'border': '#000000', 'image_border': '#000000',
                    'background': '#ffffff',
                    'title_fill': '#000000', 'author_fill': '#000000',
                    'series_fill': '#000000', 'custom_fill': '#000000',
                    'custom2_fill': '#000000', 'custom3_fill': '#000000' },
    KEY_FILL_COLORS_LINKED: True,
    KEY_FONTS: { 'title':  { 'name': None, 'size': 46, 'align': 'center', 'weight': 'Normal', 'italic': False, 'underline': False },
                 'author': { 'name': None, 'size': 36, 'align': 'center', 'weight': 'Normal', 'italic': False, 'underline': False },
                 'series': { 'name': None, 'size': 36, 'align': 'center', 'weight': 'Normal', 'italic': False, 'underline': False },
                 'custom': { 'name': None, 'size': 24, 'align': 'center', 'weight': 'Normal', 'italic': False, 'underline': False },
                 'custom2': { 'name': None, 'size': 24, 'align': 'center', 'weight': 'Normal', 'italic': False, 'underline': False },
                 'custom3': { 'name': None, 'size': 24, 'align': 'center', 'weight': 'Normal', 'italic': False, 'underline': False } },
    KEY_FONTS_LINKED: True,
    KEY_FONTS_AUTOREDUCED: False,
    KEY_FIELD_ORDER: [default_field('Title', True),
                      default_field('Author', True),
                      default_field('Series', True),
                      default_image_field('Image', True),
                      default_field('Custom Text 1', False),
                      default_field('Custom Text 2', False),
                      default_field('Custom Text 3', False)],
    KEY_CUSTOM_TEXT: '',
    KEY_CUSTOM_TEXT_2: '',
    KEY_CUSTOM_TEXT_3: '',
    KEY_BACKDROPS_LINKED: False,
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

    # Version 2.2.1 changed images to be stored in the calibre/plugins folder
    if schema_version < 2.21:
        if DEBUG:
            prints('Generate Cover - Upgrading to 2.21 schema')
        files = [migrate_image_file(f) for f in plugin_prefs[STORE_FILES]]
        plugin_prefs[STORE_FILES] = files
        # Remove the old folder to prevent confusion if it is now empty
        remove_old_images_folder_if_empty()

    if schema_version < 2.52:
        if DEBUG:
            prints('Generate Cover - Upgrading from schema:', schema_version)
        current = plugin_prefs[STORE_CURRENT]
        plugin_prefs[STORE_CURRENT] = migrate_config_setting(schema_version, STORE_CURRENT, current, is_current=True)

        saved_settings = plugin_prefs[STORE_SAVED_SETTINGS]
        for setting_name, saved_setting in six.iteritems(saved_settings):
            migrate_config_setting(schema_version, setting_name, saved_setting)
        plugin_prefs[STORE_SAVED_SETTINGS] = saved_settings
    
def migrate_padding(value, default):
    if isinstance(value, dict):
        padding = dict(DEFAULT_PADDING)
        padding.update(value)
        return padding
    padding = dict(DEFAULT_PADDING)
    padding['top'] = default if value is None else value
    return padding

def migrate_individual_colors(setting):
    colors = setting.get(KEY_COLORS, {})
    # Use the existing 'fill' color as the default for all text types
    existing_fill = colors.get('fill', '#000000')
    # Remove the old fill color if it exists
    if 'fill' in colors:
        del colors['fill']
    colors['title_fill'] = existing_fill
    colors['author_fill'] = existing_fill
    colors['series_fill'] = existing_fill
    colors['custom_fill'] = existing_fill
    setting[KEY_COLORS] = colors
    # Default to using the same fill color for backward compatibility
    setting[KEY_FILL_COLORS_LINKED] = True

def migrate_padding_options(setting):
    margins = setting.get(KEY_MARGINS, {})
    margins['image'] = migrate_padding(margins.get('image'), 10)
    setting[KEY_MARGINS] = margins
    for field in setting.get(KEY_FIELD_ORDER, []):
        field[KEY_FIELD_BACKDROP_PADDING] = migrate_padding(field.get(KEY_FIELD_BACKDROP_PADDING), 4)
        if field['name'] != 'Image':
            field[KEY_FIELD_TEXT_PADDING] = migrate_padding(
                field.get(KEY_FIELD_TEXT_PADDING), 30)

def migrate_rotation_options(setting):
    for field in setting.get(KEY_FIELD_ORDER, []):
        if field['name'] != 'Image':
            field.setdefault(KEY_FIELD_ROTATION, 0)
            field.setdefault(KEY_FIELD_ROTATION_SIDE, 'left')

def migrate_backdrop_width_options(setting):
    for field in setting.get(KEY_FIELD_ORDER, []):
        if field['name'] != 'Image':
            field.setdefault(KEY_FIELD_BACKDROP_FULL_WIDTH, False)

def migrate_font_style_options(setting):
    for font in six.itervalues(setting.get(KEY_FONTS, {})):
        font.setdefault('italic', False)

def migrate_image_border_color(setting):
    colors = setting.setdefault(KEY_COLORS, {})
    colors.setdefault(KEY_IMAGE_BORDER_COLOR, colors.get('border', '#000000'))

def migrate_custom_text_field_order(setting):
    field_order = setting[KEY_FIELD_ORDER]
    for field in field_order:
        if field['name'] == 'Custom Text':
            field['name'] = 'Custom Text 1'

    existing_names = [field['name'] for field in field_order]
    custom_text_index = existing_names.index('Custom Text 1') + 1 if 'Custom Text 1' in existing_names else len(field_order)
    missing_fields = [
        {'name': 'Custom Text %d' % index, 'display': False}
        for index in (1, 2, 3) if 'Custom Text %d' % index not in existing_names
    ]
    field_order[custom_text_index:custom_text_index] = missing_fields
    setting[KEY_FIELD_ORDER] = field_order

def migrate_element_options(setting):
    backdrop_color = setting.get(KEY_ELEMENT_BACKDROP_COLOR, '#000000')
    backdrop_opacity = setting.get(KEY_ELEMENT_BACKDROP_OPACITY, 70)
    for field in setting.get(KEY_FIELD_ORDER, []):
        if field['name'] == 'Image':
            continue
        field.setdefault(KEY_FIELD_BACKDROP_PADDING, 4)
        field.setdefault(KEY_FIELD_BACKDROP, False)
        field.setdefault(KEY_FIELD_BACKDROP_COLOR, backdrop_color)
        field.setdefault(KEY_FIELD_BACKDROP_OPACITY, backdrop_opacity)

def migrate_custom_font_options(setting):
    fonts = setting.setdefault(KEY_FONTS, {})
    custom_font = fonts.get('custom', {'name': None, 'size': 24, 'align': 'center'})
    fonts.setdefault('custom2', copy.deepcopy(custom_font))
    fonts.setdefault('custom3', copy.deepcopy(custom_font))
    setting[KEY_FONTS] = fonts

    colors = setting.setdefault(KEY_COLORS, {})
    custom_fill = colors.get('custom_fill', '#000000')
    colors.setdefault('custom2_fill', custom_fill)
    colors.setdefault('custom3_fill', custom_fill)
    setting[KEY_COLORS] = colors

def migrate_text_padding(setting):
    margins = setting.get(KEY_MARGINS, {})
    text_padding = margins.pop('text', 30)
    setting[KEY_MARGINS] = margins
    for field in setting.get(KEY_FIELD_ORDER, []):
        if field['name'] != 'Image':
            field.setdefault(KEY_FIELD_TEXT_PADDING, text_padding)

def migrate_font_style_weight_options(setting):
    for font in six.itervalues(setting.get(KEY_FONTS, {})):
        font.setdefault('weight', 'Normal')
        # if we have a key for 'bold' then we need to convert it to the new weight option
        if 'bold' in font:
            font['weight'] = 'Bold' if font.pop('bold') else 'Normal'

def migrate_image_margin_padding_options(setting):
    # Make sure padding is zero by default, to ensure people with background images don't get a white border
    # This is a fix for a bug introduced in 2.5.0 where the image padding settings were migrated incorrectly,
    # in conjunction with a change to actually respect image padding when set on the background.
    for field in setting.get(KEY_FIELD_ORDER, []):
        if field['name'] == 'Image':
            field[KEY_FIELD_IMAGE_PADDING] = {'top': 0, 'bottom': 0, 'left': 0, 'right': 0}
            break
    # Also delete the incorrect image margin setting from the margins, if it exists
    margins = setting.get(KEY_MARGINS, {})
    if 'image' in margins:
        del margins['image']
    setting[KEY_MARGINS] = margins

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

    # Version 2.2.2 added per-text-type fill colors and a checkbox to use same color for all
    if schema_version < 2.22:
        if DEBUG:
            prints('Generate Cover - Upgrading to 2.22 schema for setting: ',setting_name)
        migrate_individual_colors(setting)

    # Version 2.35 (actually release 2.5.0) added a huge number of new options and fields.
    if schema_version < 2.35:
        for key in KEY_CUSTOM_TEXT_FIELDS:
            setting.setdefault(key, '')
        migrate_custom_text_field_order(setting)
        migrate_element_options(setting)
        migrate_custom_font_options(setting)
        migrate_text_padding(setting)
        migrate_padding_options(setting)
        setting.setdefault(KEY_BACKDROPS_LINKED, False)
        migrate_rotation_options(setting)
        migrate_backdrop_width_options(setting)
        migrate_font_style_options(setting)
        migrate_image_border_color(setting)

    # Version 2.5.1 added a font weight option for each text type
    if schema_version < 2.51:
        migrate_font_style_weight_options(setting)

    # Version 2.5.2 cleaned up and fixed the image margin/padding which got messed up in 2.5.0
    if schema_version < 2.52:
        migrate_image_margin_padding_options(setting)


    return setting

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
