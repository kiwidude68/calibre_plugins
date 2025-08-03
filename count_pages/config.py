from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import copy

from six import text_type as unicode

try:
    from qt.core import (Qt, QWidget, QGridLayout, QLabel, QPushButton, QUrl,
                          QGroupBox, QComboBox, QVBoxLayout, QCheckBox,
                          QLineEdit, QTabWidget, QAbstractItemView,
                          QTableWidget, QHBoxLayout, QSize, QToolButton)
except ImportError:
    from PyQt5.Qt import (Qt, QWidget, QGridLayout, QLabel, QPushButton, QUrl,
                          QGroupBox, QComboBox, QVBoxLayout, QCheckBox,
                          QLineEdit, QTabWidget,QAbstractItemView,
                          QTableWidget, QHBoxLayout, QSize, QToolButton)

from calibre.gui2 import open_url, dynamic, info_dialog
from calibre.utils.config import JSONConfig

from calibre_plugins.count_pages.common_icons import get_icon
from calibre_plugins.count_pages.common_dialogs import KeyboardConfigDialog, PrefsViewerDialog
from calibre_plugins.count_pages.common_widgets import (CustomColumnComboBox, KeyValueComboBox,
                                     ReadOnlyTextIconWidgetItem, ReadOnlyCheckableTableWidgetItem, CheckableTableWidgetItem)

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/Count-Pages'

PREFS_NAMESPACE = 'CountPagesPlugin'
PREFS_KEY_SETTINGS = 'settings'

KEY_PAGES_CUSTOM_COLUMN = 'customColumnPages'
KEY_WORDS_CUSTOM_COLUMN = 'customColumnWords'
KEY_FLESCH_READING_CUSTOM_COLUMN = 'customColumnFleschReading'
KEY_FLESCH_GRADE_CUSTOM_COLUMN = 'customColumnFleschGrade'
KEY_GUNNING_FOG_CUSTOM_COLUMN = 'customColumnGunningFog'

KEY_BUTTON_DEFAULT = 'buttonDefault'
KEY_OVERWRITE_EXISTING = 'overwriteExisting'
KEY_UPDATE_IF_UNCHANGED = 'updateIfUnchanged'
KEY_USE_PREFERRED_OUTPUT = 'usePreferredOutput'
KEY_ASK_FOR_CONFIRMATION = 'askForConfirmation'
KEY_CHECK_ALL_SOURCES = 'checkAllSources'
KEY_DOWNLOAD_SOURCES = 'downloadSources'
KEY_SHOW_TRY_ALL_SOURCES = 'showTryAllSources'
KEY_USE_ICU_WORDCOUNT = 'useIcuWordcount'

STORE_NAME = 'Options'
KEY_PAGES_ALGORITHM = 'algorithmPages'
KEY_CUSTOM_CHARS_PER_PAGE = 'customCharsPerPage'

PAGE_ALGORITHMS = [_('Paragraphs (APNX accurate)'), _('E-book Viewer (calibre)'), _('Adobe Digital Editions (ADE)'), _('Custom (Chars Per Page)')]

PAGE_DOWNLOADS = {
                  'goodreads':
                    {
                     'URL': 'https://www.goodreads.com/book/show/%s',
                     'pages_xpath': '//div[@class="FeaturedDetails"]/p[@data-testid="pagesFormat"]/text()',
                     'name': 'Goodreads',
                     'id': 'goodreads',
                     'icon': 'images/goodreads.png',
                     'active': True,
                     'pages_regex': r'([0-9]+) pages'
                    },
                  'lubimyczytac.pl':
                    {
                     'URL': 'https://lubimyczytac.pl/ksiazka/%s/ksiazka',
                     'pages_xpath': '//span[contains(@class, "book-pages")]/text()[contains(.,"str")]',
                     'name': 'lubimyczytac.pl',
                     'id': 'lubimyczytac',
                     'icon': 'images/lubimyczytac.png',
                     'active': False
                    },
                  'skoob':
                    {
                     'URL': 'https://www.skoob.com.br/livro/%s',
                     'pages_xpath': '//div[@class="sidebar-desc"]/text()[contains(., "ginas")]',
                     'name': 'Skoob',
                     'id': 'skoob',
                     'icon': 'images/skoob.png',
                     'active': False,
                     'pages_regex': r'ginas: ([0-9]+)' # First group in match should be the page counts
                    },
                  'databazeknih.cz':
                    {
                     'URL': 'https://www.databazeknih.cz/book-detail-more-info/%s',
                     'identifier_regex': r'(?:-{0,1})(\d+)$',   # Only want the number at the end of the identifier
                     'pages_xpath': '//span[@itemprop="numberOfPages"]/text()',
                     'name': 'databazeknih.cz',
                     'id': 'databazeknih',
                     'icon': 'images/databazeknih.png',
                     'active': False
                    },
                  'cbdb.cz':
                    {
                     'URL': 'https://www.cbdb.cz/kniha-%s',
                     'pages_xpath': '//span[@itemprop="numberOfPages"]/text()',
                     'name': 'CBDB.cz',
                     'id': 'cbdb',
                     'icon': 'images/cbdb.png',
                     'active': False
                    }
                  }

# The DOWNLOAD_SOURCES_DEFAULTS is an order list of tuples. The order of the tuples is the order in the list
# and when used. The elements in the tuple are the source identifier, and booleans for whether the source is
# to be used and whether it is on the menu.
DOWNLOAD_SOURCES_DEFAULTS = ( # This is an orderer list of tuples
                              ('goodreads', True, True),
                              ('lubimyczytac.pl', False, False),
                              ('skoob', False, False),
                              ('databazeknih.cz', False, False),
                              ('cbdb.cz', False, False),
                             )
DOWNLOAD_SOURCE_OPTION_STRING = _('Download page/word counts')
BUTTON_DEFAULTS = {
                   'Estimate':  _('Estimate page/word counts'),
                   'Download':  DOWNLOAD_SOURCE_OPTION_STRING + _(' - all sources'),
                  }

STATISTIC_PAGE_COUNT = 'PageCount'
STATISTIC_WORD_COUNT = 'WordCount'
STATISTIC_FLESCH_READING = 'FleschReading'
STATISTIC_FLESCH_GRADE = 'FleschGrade'
STATISTIC_GUNNING_FOG = 'GunningFog'
ALL_STATISTICS = {
                  STATISTIC_PAGE_COUNT: KEY_PAGES_CUSTOM_COLUMN,
                  STATISTIC_WORD_COUNT: KEY_WORDS_CUSTOM_COLUMN,
                  STATISTIC_FLESCH_READING: KEY_FLESCH_READING_CUSTOM_COLUMN,
                  STATISTIC_FLESCH_GRADE: KEY_FLESCH_GRADE_CUSTOM_COLUMN,
                  STATISTIC_GUNNING_FOG: KEY_GUNNING_FOG_CUSTOM_COLUMN
                  }

DEFAULT_STORE_VALUES = {
                        KEY_BUTTON_DEFAULT: 'Estimate',
                        KEY_OVERWRITE_EXISTING: True,
                        KEY_UPDATE_IF_UNCHANGED: False,
                        KEY_USE_PREFERRED_OUTPUT: False,
                        KEY_ASK_FOR_CONFIRMATION: True,
                        KEY_USE_ICU_WORDCOUNT: True,
                        KEY_CHECK_ALL_SOURCES: True,
                        KEY_SHOW_TRY_ALL_SOURCES: True,
                        KEY_DOWNLOAD_SOURCES: DOWNLOAD_SOURCES_DEFAULTS
                        }
DEFAULT_LIBRARY_VALUES = {
                          KEY_PAGES_ALGORITHM: 0,
                          KEY_CUSTOM_CHARS_PER_PAGE: 1500,
                          KEY_PAGES_CUSTOM_COLUMN: '',
                          KEY_WORDS_CUSTOM_COLUMN: '',
                          KEY_FLESCH_READING_CUSTOM_COLUMN: '',
                          KEY_FLESCH_GRADE_CUSTOM_COLUMN: '',
                          KEY_GUNNING_FOG_CUSTOM_COLUMN: ''
                          }

PLUGIN_ICONS = [
                'images/count_pages.png',
                'images/estimate.png', 
                'images/download_all_sources.png',
                'images/goodreads.png',
                'images/lubimyczytac.png',
                'images/skoob.png',
                'images/databazeknih.png',
                'images/cbdb.png',
                ]

KEY_SCHEMA_VERSION = 'SchemaVersion'
DEFAULT_SCHEMA_VERSION = 1.61


# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Count Pages')

# Set defaults
plugin_prefs.defaults[STORE_NAME] = DEFAULT_STORE_VALUES


def migrate_library_config_if_required(db, library_config):
    schema_version = library_config.get(KEY_SCHEMA_VERSION, 0)
    if schema_version == DEFAULT_SCHEMA_VERSION:
        return
    # We have changes to be made - mark schema as updated
    library_config[KEY_SCHEMA_VERSION] = DEFAULT_SCHEMA_VERSION

    # Any migration code in future will exist in here.
    if schema_version < 1.61:
        if 'customColumn' in library_config:
            library_config[KEY_PAGES_CUSTOM_COLUMN] = library_config['customColumn']
            del library_config['customColumn']
        store_prefs = plugin_prefs[STORE_NAME]
        if KEY_PAGES_ALGORITHM not in library_config:
            library_config[KEY_PAGES_ALGORITHM] = store_prefs.get('algorithm', 0)
            # Unfortunately cannot delete since user may have other libraries
        if 'algorithmWords' in store_prefs:
            del store_prefs['algorithmWords']
            plugin_prefs[STORE_NAME] = store_prefs        

    set_library_config(db, library_config)


def get_library_config(db):
    library_id = db.library_id
    library_config = None
    # Check whether this is a configuration needing to be migrated from json into database
    if 'libraries' in plugin_prefs:
        libraries = plugin_prefs['libraries']
        if library_id in libraries:
            # We will migrate this below
            library_config = libraries[library_id]
            # Cleanup from json file so we don't ever do this again
            del libraries[library_id]
            if len(libraries) == 0:
                # We have migrated the last library for this user
                del plugin_prefs['libraries']
            else:
                plugin_prefs['libraries'] = libraries

    if library_config is None:
        library_config = db.prefs.get_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS,
                                                 copy.deepcopy(DEFAULT_LIBRARY_VALUES))
    
    migrate_library_config_if_required(db, library_config)
    return library_config

def set_library_config(db, library_config):
    db.prefs.set_namespaced(PREFS_NAMESPACE, PREFS_KEY_SETTINGS, library_config)

def show_help():
    open_url(QUrl(HELP_URL))


class AlgorithmComboBox(QComboBox):

    def __init__(self, parent, algorithms, selected_algorithm):
        QComboBox.__init__(self, parent)
        self.populate_combo(algorithms, selected_algorithm)

    def populate_combo(self, algorithms, selected_algorithm):
        self.clear()
        for item in algorithms:
            self.addItem(item)
        self.setCurrentIndex(selected_algorithm)


class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        tab_widget = QTabWidget(self)
        layout.addWidget(tab_widget)

        self.statistics_tab = StatisticsTab(self)
        self.other_tab = OtherTab(self)
        tab_widget.addTab(self.statistics_tab, _('Statistics'))
        tab_widget.addTab(self.other_tab, _('Other'))


    def save_settings(self):
        new_prefs = {}
        new_prefs[KEY_BUTTON_DEFAULT] = self.other_tab.button_default_combo.selected_key()
        new_prefs[KEY_OVERWRITE_EXISTING] = self.other_tab.overwrite_checkbox.isChecked()
        new_prefs[KEY_UPDATE_IF_UNCHANGED] = self.other_tab.update_if_unchanged_checkbox.isChecked()
        new_prefs[KEY_USE_PREFERRED_OUTPUT] = self.other_tab.use_preferred_output_checkbox.isChecked()
        new_prefs[KEY_CHECK_ALL_SOURCES] = self.other_tab.check_all_checkbox.isChecked()
        new_prefs[KEY_SHOW_TRY_ALL_SOURCES] = self.other_tab.show_try_all_sources_checkbox.isChecked()
        new_prefs[KEY_DOWNLOAD_SOURCES] = self.get_source_list()
        new_prefs[KEY_ASK_FOR_CONFIRMATION] = self.other_tab.ask_for_confirmation_checkbox.isChecked()
        new_prefs[KEY_USE_ICU_WORDCOUNT] = self.statistics_tab.icu_wordcount_checkbox.isChecked()
        plugin_prefs[STORE_NAME] = new_prefs

        db = self.plugin_action.gui.current_db
        library_config = get_library_config(db)
        library_config[KEY_PAGES_ALGORITHM] = self.statistics_tab.page_algorithm_combo.currentIndex()
        custom_chars = unicode(self.statistics_tab.page_custom_char_ledit.text()).strip()
        if not custom_chars:
            custom_chars = '1500'
        library_config[KEY_CUSTOM_CHARS_PER_PAGE] = int(custom_chars)
        library_config[KEY_PAGES_CUSTOM_COLUMN] = self.statistics_tab.page_column_combo.get_selected_column()
        library_config[KEY_WORDS_CUSTOM_COLUMN] = self.statistics_tab.word_column_combo.get_selected_column()
        library_config[KEY_FLESCH_READING_CUSTOM_COLUMN] = self.statistics_tab.flesch_reading_column_combo.get_selected_column()
        library_config[KEY_FLESCH_GRADE_CUSTOM_COLUMN] = self.statistics_tab.flesch_grade_column_combo.get_selected_column()
        library_config[KEY_GUNNING_FOG_CUSTOM_COLUMN] = self.statistics_tab.gunning_fog_column_combo.get_selected_column()
        set_library_config(db, library_config)

    def get_custom_columns(self):
        column_types = ['float','int']
        custom_columns = self.plugin_action.gui.library_view.model().custom_columns
        available_columns = {}
        for key, column in custom_columns.items():
            typ = column['datatype']
            if typ in column_types:
                available_columns[key] = column
        return available_columns

    def _link_activated(self, url):
        open_url(QUrl(url))

    def edit_shortcuts(self):
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()

    def view_prefs(self):
        d = PrefsViewerDialog(self.plugin_action.gui, PREFS_NAMESPACE)
        d.exec_()

    def get_source_list(self):
        return self.other_tab.get_source_list()

class OtherTab(QWidget):

    def __init__(self, parent_dialog):
        self.parent_dialog = parent_dialog
        QWidget.__init__(self)
        layout = QVBoxLayout()
        self.setLayout(layout)

        c = plugin_prefs[STORE_NAME]
        button_default = c.get(KEY_BUTTON_DEFAULT, DEFAULT_STORE_VALUES[KEY_BUTTON_DEFAULT])
        overwrite_existing = c.get(KEY_OVERWRITE_EXISTING, DEFAULT_STORE_VALUES[KEY_OVERWRITE_EXISTING])
        update_if_unchanged = c.get(KEY_UPDATE_IF_UNCHANGED, DEFAULT_STORE_VALUES[KEY_UPDATE_IF_UNCHANGED])
        use_preferred_output = c.get(KEY_USE_PREFERRED_OUTPUT, DEFAULT_STORE_VALUES[KEY_USE_PREFERRED_OUTPUT])
        ask_for_confirmation = c.get(KEY_ASK_FOR_CONFIRMATION, DEFAULT_STORE_VALUES[KEY_ASK_FOR_CONFIRMATION])
        check_all_sources = c.get(KEY_CHECK_ALL_SOURCES, DEFAULT_STORE_VALUES[KEY_CHECK_ALL_SOURCES])
        download_sources = c.get(KEY_DOWNLOAD_SOURCES, DEFAULT_STORE_VALUES[KEY_DOWNLOAD_SOURCES])
        if len(download_sources) < len(DEFAULT_STORE_VALUES[KEY_DOWNLOAD_SOURCES]):
            download_sources_names = [x[0] for x in download_sources]
            for default_download_source in DEFAULT_STORE_VALUES[KEY_DOWNLOAD_SOURCES]:
                if default_download_source[0] not in download_sources_names:
                    download_sources.append(default_download_source)
        show_try_all_sources = c.get(KEY_SHOW_TRY_ALL_SOURCES, DEFAULT_STORE_VALUES[KEY_SHOW_TRY_ALL_SOURCES])

        # Fudge the button default to cater for the options no longer supported by plugin as of 1.5
        if button_default in ['Estimate', 'EstimatePage', 'EstimateWord']:
            button_default = 'Estimate'
        elif button_default in PAGE_DOWNLOADS.keys():
            pass
        else:
            button_default = 'Download'

        # --- Download options ---
        layout.addSpacing(5)
        download_group_box = QGroupBox(_('Download options:'), self)
        layout.addWidget(download_group_box)
        download_group_box_layout = QGridLayout()
        download_group_box.setLayout(download_group_box_layout)

        table_layout = QHBoxLayout()
        download_group_box_layout.addLayout(table_layout, 0, 0, 1, 1)

        self.download_sources_table = DownloadSourcesTableWidget(self)
        table_layout.addWidget(self.download_sources_table)
        self.download_sources_table.populate_table(download_sources)

        table_button_layout = QVBoxLayout()
        table_layout.addLayout(table_button_layout)
        move_up_button = QToolButton(self)
        move_up_button.setToolTip(_('Move source up (Alt+Up)'))
        move_up_button.setIcon(get_icon('arrow-up.png'))
        move_up_button.setShortcut(_('Alt+Up'))
        move_up_button.clicked.connect(self.move_rows_up)
        table_button_layout.addWidget(move_up_button)
        move_down_button = QToolButton(self)
        move_down_button.setToolTip(_('Move source down (Alt+Down)'))
        move_down_button.setIcon(get_icon('arrow-down.png'))
        move_down_button.setShortcut(_('Alt+Down'))
        move_down_button.clicked.connect(self.move_rows_down)
        table_button_layout.addWidget(move_down_button)

        self.show_try_all_sources_checkbox = QCheckBox(_('Show download from all sources menu item'), self)
        self.show_try_all_sources_checkbox.setToolTip(
                                            _('Show a menu item to attempt to download the page\n'
                                             'count from all active sources. Only sources for which\n'
                                             'the book has an id will be tried.\n')
                                            )
        self.show_try_all_sources_checkbox.setChecked(show_try_all_sources)
        download_group_box_layout.addWidget(self.show_try_all_sources_checkbox, 2, 0, 1, 1)

        self.check_all_checkbox = QCheckBox(_('Try to download page count from each source'), self)
        self.check_all_checkbox.setToolTip(_('If this option is checked, each download source is\n'
                                             'tried until a page count is successfully\n'
                                             'fetched.\n'))
        self.check_all_checkbox.setChecked(check_all_sources)
        download_group_box_layout.addWidget(self.check_all_checkbox, 4, 0, 1, 1)

        # --- Other options ---
        layout.addSpacing(5)
        other_group_box = QGroupBox(_('Other options:'), self)
        layout.addWidget(other_group_box)
        other_group_box_layout = QGridLayout()
        other_group_box.setLayout(other_group_box_layout)

        layout.addStretch(1)
        button_default_label = QLabel(_('&Button default:'), self)
        toolTip = _('If plugin is placed as a toolbar button, choose a default action when clicked on')
        button_default_label.setToolTip(toolTip)
        button_defaults = BUTTON_DEFAULTS
        for source in download_sources:
            button_defaults[source[0]] = DOWNLOAD_SOURCE_OPTION_STRING + ' - ' + PAGE_DOWNLOADS[source[0]]['name']
        self.button_default_combo = KeyValueComboBox(self, button_defaults, button_default)
        self.button_default_combo.setToolTip(toolTip)
        button_default_label.setBuddy(self.button_default_combo)
        other_group_box_layout.addWidget(button_default_label, 0, 0, 1, 1)
        other_group_box_layout.addWidget(self.button_default_combo, 0, 1, 1, 2)

        self.overwrite_checkbox = QCheckBox(_('Always overwrite an existing word/page count'), self)
        self.overwrite_checkbox.setToolTip(_('Uncheck this option if you have manually populated values in\n'
                                             'either of your page/word custom columns, and never want the\n'
                                             'plugin to overwrite it. Acts as a convenience option for users\n'
                                             'who have the toolbar button configured to populate both page\n'
                                             'and word count, but for some books have already assigned values\n'
                                             'into a column and just want the zero/blank column populated.'))
        self.overwrite_checkbox.setChecked(overwrite_existing)
        other_group_box_layout.addWidget(self.overwrite_checkbox, 1, 0, 1, 3)

        self.update_if_unchanged_checkbox = QCheckBox(_('Update the statistics even if they have not changed'), self)
        self.update_if_unchanged_checkbox.setToolTip(_('Check this option if you want the statistics to be updated in\n'
                                                       'the books metadata even if they have not changed. Using this\n'
                                                       'option will always update the modified timestamp for the book\n'
                                                       'even when the statistics have not changed.'))
        self.update_if_unchanged_checkbox.setChecked(update_if_unchanged)
        other_group_box_layout.addWidget(self.update_if_unchanged_checkbox, 2, 0, 1, 3)

        self.use_preferred_output_checkbox = QCheckBox(_('Use Preferred Output Format if available'), self)
        self.use_preferred_output_checkbox.setToolTip(_('Check this option to calculate the statistics using the format selected\n'
                                                        'as the Preferred Output Format. If this format is not found, or the\n'
                                                        'option is not checked, the first format found in the Preferred Input\n'
                                                        'Format list will be used. The Preferred Output and Input settings\n'
                                                        'are specified in Behavior page of the calibre Preferences.\n'
                                                        'Note: ePub will always be used if the ADE page count algorithm is selected.'))
        self.use_preferred_output_checkbox.setChecked(use_preferred_output)
        other_group_box_layout.addWidget(self.use_preferred_output_checkbox, 3, 0, 1, 3)

        self.ask_for_confirmation_checkbox = QCheckBox(_('Prompt to save counts'), self)
        self.ask_for_confirmation_checkbox.setToolTip(_('Uncheck this option if you want changes applied without\n'
                                                        'a confirmation dialog. There is a small risk with this\n'
                                                        'option unchecked that if you are making other changes to\n'
                                                        'this book record at the same time they will be lost.'))
        self.ask_for_confirmation_checkbox.setChecked(ask_for_confirmation)
        other_group_box_layout.addWidget(self.ask_for_confirmation_checkbox, 4, 0, 1, 3)

        button_layout = QHBoxLayout()
        keyboard_shortcuts_button = QPushButton(' '+_('Keyboard shortcuts')+'... ', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.parent_dialog.edit_shortcuts)
        view_prefs_button = QPushButton(' '+_('&Library preferences')+'... ', self)
        view_prefs_button.setToolTip(_('View data stored in the library database for this plugin'))
        view_prefs_button.clicked.connect(self.parent_dialog.view_prefs)
        button_layout.addWidget(keyboard_shortcuts_button)
        button_layout.addWidget(view_prefs_button)

        help_button = QPushButton(' '+_('&Help'), self)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(show_help)
        button_layout.addWidget(help_button)
        layout.addLayout(button_layout)

    def reset_dialogs(self):
        for key in dynamic.keys():
            if key.startswith('reading_list_') and key.endswith('_again') \
                                                  and dynamic[key] is False:
                dynamic[key] = True
        info_dialog(self, _('Done'),
                _('Confirmation dialogs have all been reset'), show=True)

    def move_rows_up(self):
        self.download_sources_table.setFocus()
        rows = self.download_sources_table.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        first_sel_row = rows[0].row()
        if first_sel_row <= 0:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        for selrow in selrows:
            self.download_sources_table.swap_row_widgets(selrow - 1, selrow + 1)

        scroll_to_row = first_sel_row - 1
        if scroll_to_row > 0:
            scroll_to_row = scroll_to_row - 1
        self.download_sources_table.scrollToItem(self.download_sources_table.item(scroll_to_row, 0))

    def move_rows_down(self):
        self.download_sources_table.setFocus()
        rows = self.download_sources_table.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        last_sel_row = rows[-1].row()
        if last_sel_row == self.download_sources_table.rowCount() - 1:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        for selrow in reversed(selrows):
            self.download_sources_table.swap_row_widgets(selrow + 2, selrow)

        scroll_to_row = last_sel_row + 1
        if scroll_to_row < self.download_sources_table.rowCount() - 1:
            scroll_to_row = scroll_to_row + 1
        self.download_sources_table.scrollToItem(self.download_sources_table.item(scroll_to_row, 0))

    def get_source_list(self):
        return self.download_sources_table.get_source_list()


class DownloadSourcesTableWidget(QTableWidget):

    def __init__(self, parent):
        QTableWidget.__init__(self, parent)
        self.setSortingEnabled(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setMinimumSize(380, 0)

    def populate_table(self, download_sources):
        self.clear()
        self.setRowCount(len(PAGE_DOWNLOADS))
        header_labels = [_('Source'), _('Identifier'), _('On Menu'), ]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(32)
        self.horizontalHeader().setStretchLastSection(False)
        self.setIconSize(QSize(32, 32))

        for row, source in enumerate(download_sources):
            self.populate_table_row(row, source[0], PAGE_DOWNLOADS[source[0]], source[1], source[2])

        self.resizeColumnsToContents()
        self.setMinimumColumnWidth(1, 100)
        self.selectRow(0)

    def setMinimumColumnWidth(self, col, minimum):
        if self.columnWidth(col) < minimum:
            self.setColumnWidth(col, minimum)

    def populate_table_row(self, row, source_id, source_definition, active, on_menu):
        name_widget = ReadOnlyTextIconWidgetItem(source_definition['name'], get_icon(source_definition['icon']))
        name_widget.setData(Qt.UserRole, source_id)
        source_id_widget = ReadOnlyCheckableTableWidgetItem(source_definition['id'], checked=active)
        
        self.setItem(row, 0, name_widget)
        self.setItem(row, 1, source_id_widget)
        self.setItem(row, 2, CheckableTableWidgetItem(on_menu))

    def get_source_list(self):
        download_sources = []
        for row in range(self.rowCount()):
            source_id = unicode(self.item(row, 0).data(Qt.UserRole))
            active = self.item(row, 1).get_boolean_value()
            on_menu = self.item(row, 2).get_boolean_value()
            download_sources.append((source_id, active, on_menu))
        return download_sources

    def swap_row_widgets(self, src_row, dest_row):
        self.blockSignals(True)
        self.insertRow(dest_row)
        for col in range(self.columnCount()):
            self.setItem(dest_row, col, self.takeItem(src_row, col))
        self.removeRow(src_row)
        self.blockSignals(False)

    def select_and_scroll_to_row(self, row):
        self.selectRow(row)
        self.scrollToItem(self.currentItem())


class StatisticsTab(QWidget):

    def __init__(self, parent_dialog):
        self.parent_dialog = parent_dialog
        QWidget.__init__(self)
        layout = QVBoxLayout()
        self.setLayout(layout)

        c = plugin_prefs[STORE_NAME]
        avail_columns = self.parent_dialog.get_custom_columns()
        library_config = get_library_config(self.parent_dialog.plugin_action.gui.current_db)
        pages_algorithm = library_config.get(KEY_PAGES_ALGORITHM, DEFAULT_LIBRARY_VALUES[KEY_PAGES_ALGORITHM])
        custom_chars_per_page = library_config.get(KEY_CUSTOM_CHARS_PER_PAGE, DEFAULT_LIBRARY_VALUES[KEY_CUSTOM_CHARS_PER_PAGE])
        icu_wordcount = c.get(KEY_USE_ICU_WORDCOUNT, DEFAULT_STORE_VALUES[KEY_USE_ICU_WORDCOUNT])

        # --- Pages ---
        page_group_box = QGroupBox(_('Page count options:'), self)
        layout.addWidget(page_group_box)
        page_group_box_layout = QGridLayout()
        page_group_box.setLayout(page_group_box_layout)

        page_column_label = QLabel(_('&Custom column:'), self)
        toolTip = _('Column must be of type float or int. Leave this blank if you do not want to count pages')
        page_column_label.setToolTip(toolTip)
        page_col = library_config.get(KEY_PAGES_CUSTOM_COLUMN, '')
        self.page_column_combo = CustomColumnComboBox(self, avail_columns, page_col)
        self.page_column_combo.setToolTip(toolTip)
        page_column_label.setBuddy(self.page_column_combo)
        page_group_box_layout.addWidget(page_column_label, 0, 0, 1, 1)
        page_group_box_layout.addWidget(self.page_column_combo, 0, 1, 1, 2)

        page_algorithm_label = QLabel(_('&Algorithm:'), self)
        toolTip = _('Choose which algorithm to use if you have specified a page count column')
        page_algorithm_label.setToolTip(toolTip)
        self.page_algorithm_combo = AlgorithmComboBox(self, PAGE_ALGORITHMS, pages_algorithm)
        self.page_algorithm_combo.setToolTip(toolTip)
        self.page_algorithm_combo.currentIndexChanged.connect(self._page_algorithm_changed)
        page_algorithm_label.setBuddy(self.page_algorithm_combo)
        page_group_box_layout.addWidget(page_algorithm_label, 1, 0, 1, 1)
        page_group_box_layout.addWidget(self.page_algorithm_combo, 1, 1, 1, 2)

        self.page_custom_char_label = QLabel(_('C&hars per page:'), self)
        toolTip = _('If using the Custom algorithm, specify how many characters per page including spaces.')
        self.page_custom_char_label.setToolTip(toolTip)
        self.page_custom_char_ledit = QLineEdit(str(custom_chars_per_page), self)
        self.page_custom_char_ledit.setToolTip(toolTip)
        self.page_custom_char_label.setBuddy(self.page_custom_char_ledit)
        page_group_box_layout.addWidget(self.page_custom_char_label, 2, 0, 1, 1)
        page_group_box_layout.addWidget(self.page_custom_char_ledit, 2, 1, 1, 2)

        # --- Words ---
        layout.addSpacing(5)
        word_group_box = QGroupBox(_('Word count options:'), self)
        layout.addWidget(word_group_box)
        word_group_box_layout = QGridLayout()
        word_group_box.setLayout(word_group_box_layout)
        word_column_label = QLabel(_('C&ustom column:'), self)
        toolTip = _('Column must be of type float or int. Leave this blank if you do not want to count words')
        word_column_label.setToolTip(toolTip)
        word_col = library_config.get(KEY_WORDS_CUSTOM_COLUMN, '')
        self.word_column_combo = CustomColumnComboBox(self, avail_columns, word_col)
        self.word_column_combo.setToolTip(toolTip)
        word_column_label.setBuddy(self.word_column_combo)
        word_group_box_layout.addWidget(word_column_label, 0, 0, 1, 1)
        word_group_box_layout.addWidget(self.word_column_combo, 0, 1, 1, 2)

        self.icu_wordcount_checkbox = QCheckBox(_('Use ICU algorithm'), self)
        self.icu_wordcount_checkbox.setToolTip(_('The ICU algorithm is a more complete word count and supports multiple locales.\n'
                                                 'Uncheck this to use the original word count algorithm.'))
        self.icu_wordcount_checkbox.setChecked(icu_wordcount)
        word_group_box_layout.addWidget(self.icu_wordcount_checkbox, 1, 0, 1, 3)
#         self.icu_wordcount_checkbox.setVisible(False)

        # --- Readability ---
        layout.addSpacing(5)
        readability_group_box = QGroupBox(_('Readability options:'), self)
        layout.addWidget(readability_group_box)
        readability_layout = QGridLayout()
        readability_group_box.setLayout(readability_layout)

        readability_label = QLabel(_('Readability statistics available are <a href="https://en.wikipedia.org/wiki/Flesch-Kincaid_readability_test">Flesch-Kincaid</a> '
                                     'or <a href="https://en.wikipedia.org/wiki/Gunning_fog_index">Gunning Fog Index</a>.'), self)
        readability_layout.addWidget(readability_label, 0, 0, 1, 3)
        readability_label.linkActivated.connect(self.parent_dialog._link_activated)

        flesch_reading_column_label = QLabel(_('&Flesch Reading Ease:'), self)
        toolTip = _('Specify the custom column to store a computed Flesch Reading Ease score.\n'
                    'Leave this blank if you do not want to calculate it')
        flesch_reading_column_label.setToolTip(toolTip)
        flesch_reading_col = library_config.get(KEY_FLESCH_READING_CUSTOM_COLUMN, '')
        self.flesch_reading_column_combo = CustomColumnComboBox(self, avail_columns, flesch_reading_col)
        self.flesch_reading_column_combo.setToolTip(toolTip)
        flesch_reading_column_label.setBuddy(self.flesch_reading_column_combo)
        readability_layout.addWidget(flesch_reading_column_label, 1, 0, 1, 1)
        readability_layout.addWidget(self.flesch_reading_column_combo, 1, 1, 1, 2)

        flesch_grade_column_label = QLabel(_('Flesch-&Kincaid Grade:'), self)
        toolTip = _('Specify the custom column to store a computed Flesch-Kincaid Grade Level score.\n'
                    'Leave this blank if you do not want to calculate it')
        flesch_grade_column_label.setToolTip(toolTip)
        flesch_grade_col = library_config.get(KEY_FLESCH_GRADE_CUSTOM_COLUMN, '')
        self.flesch_grade_column_combo = CustomColumnComboBox(self, avail_columns, flesch_grade_col)
        self.flesch_grade_column_combo.setToolTip(toolTip)
        flesch_grade_column_label.setBuddy(self.flesch_grade_column_combo)
        readability_layout.addWidget(flesch_grade_column_label, 2, 0, 1, 1)
        readability_layout.addWidget(self.flesch_grade_column_combo, 2, 1, 1, 2)

        gunning_fog_column_label = QLabel(_('&Gunning Fog Index:'), self)
        toolTip = _('Specify the custom column to store a computed Gunning Fog Index score.\n'
                    'Leave this blank if you do not want to calculate it')
        gunning_fog_column_label.setToolTip(toolTip)
        gunning_fog_col = library_config.get(KEY_GUNNING_FOG_CUSTOM_COLUMN, '')
        self.gunning_fog_column_combo = CustomColumnComboBox(self, avail_columns, gunning_fog_col)
        self.gunning_fog_column_combo.setToolTip(toolTip)
        gunning_fog_column_label.setBuddy(self.gunning_fog_column_combo)
        readability_layout.addWidget(gunning_fog_column_label, 3, 0, 1, 1)
        readability_layout.addWidget(self.gunning_fog_column_combo, 3, 1, 1, 2)
        
        layout.addStretch(1)
        self._page_algorithm_changed()

    def _page_algorithm_changed(self):
        custom_chars_enabled = False
        if self.page_algorithm_combo.currentIndex() == 3:
            custom_chars_enabled = True
        self.page_custom_char_label.setEnabled(custom_chars_enabled)
        self.page_custom_char_ledit.setEnabled(custom_chars_enabled)

