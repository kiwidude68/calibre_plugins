from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from functools import partial
try:
    from qt.core import QToolButton, QMenu
except ImportError:
    from PyQt5.Qt import QToolButton, QMenu

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.gui2 import question_dialog
from calibre.gui2.actions import InterfaceAction
from calibre.gui2.dialogs.message_box import ErrorNotification
from calibre.ptempfile import PersistentTemporaryDirectory, remove_dir

import calibre_plugins.count_pages.config as cfg
from calibre_plugins.count_pages.config import ALL_STATISTICS
from calibre_plugins.count_pages.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.count_pages.common_menus import unregister_menu_actions, create_menu_action_unique
from calibre_plugins.count_pages.common_dialogs import ProgressBarDialog
from calibre_plugins.count_pages.jobs import call_plugin_callback
from calibre_plugins.count_pages.dialogs import QueueProgressDialog, TotalStatisticsDialog


class CountPagesAction(InterfaceAction):

    name = 'Count Pages'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (_('Count Pages'), None, _('Count the number of pages and/or words in a book\n'
                                          'to store in custom column(s)'), ())
    popup_type = QToolButton.MenuButtonPopup
    action_type = 'current'
    dont_add_to = frozenset(['context-menu-device'])

    def genesis(self):
        self.is_library_selected = True
        self.menu = QMenu(self.gui)
        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(cfg.PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)

        self.rebuild_menus()
        self.nltk_pickle = self._get_nltk_resource()

        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon(cfg.PLUGIN_ICONS[0]))
        self.qaction.triggered.connect(self.toolbar_triggered)
        self.menu.aboutToShow.connect(self.about_to_show_menu)

        # Used to store callback details when called from another plugin.
        self.plugin_callback = None

    def about_to_show_menu(self):
        self.rebuild_menus()

    def library_changed(self, db):
        # We need to reapply keyboard shortcuts after switching libraries
        self.rebuild_menus()

    def location_selected(self, loc):
        self.is_library_selected = loc == 'library'

    def rebuild_menus(self):
        # Ensure any keyboard shortcuts from previous display of plugin menu are cleared
        unregister_menu_actions(self)

        m = self.menu
        m.clear()
        show_download_separator = False
        c = cfg.plugin_prefs[cfg.STORE_NAME]
        show_try_all_sources = c.get(cfg.KEY_SHOW_TRY_ALL_SOURCES, cfg.DEFAULT_STORE_VALUES[cfg.KEY_SHOW_TRY_ALL_SOURCES])
        download_sources = c.get(cfg.KEY_DOWNLOAD_SOURCES, cfg.DEFAULT_STORE_VALUES[cfg.KEY_DOWNLOAD_SOURCES])
        if len(download_sources[0]) < 3:
            download_sources = cfg.DEFAULT_STORE_VALUES[cfg.KEY_DOWNLOAD_SOURCES]
        
        create_menu_action_unique(self, m, _('&Estimate page/word counts'), 'images/count.png',
                                  triggered=partial(self._count_pages_on_selected, 'Estimate'))
        m.addSeparator()
        if show_try_all_sources:
            create_menu_action_unique(self, m, _('&Download page/word counts - all sources'), 'images/download_all_sources.png',
                                      triggered=partial(self._count_pages_on_selected, 'Download'))
            show_download_separator = True

        for download_source in download_sources:
            if download_source[2]:
                create_menu_action_unique(self, m, cfg.DOWNLOAD_SOURCE_OPTION_STRING + ' - ' + cfg.PAGE_DOWNLOADS[download_source[0]]['name'], cfg.PAGE_DOWNLOADS[download_source[0]]['icon'],
                                      triggered=partial(self._count_pages_on_selected, 'Download', download_source=download_source[0]))
                show_download_separator = True

        if show_download_separator:
            m.addSeparator()
        create_menu_action_unique(self, m, _('&Statistic totals for selected books'), 'images/estimate.png',
                                  triggered=self._show_totals_for_selected)
        m.addSeparator()
        create_menu_action_unique(self, m, _('&Customize plugin')+'...', 'config.png',
                                  shortcut=False, triggered=self.show_configuration)
        create_menu_action_unique(self, m, _('&Help'), 'help.png',
                                  shortcut=False, triggered=cfg.show_help)
        self.gui.keyboard.finalize()

    def toolbar_triggered(self):
        c = cfg.plugin_prefs[cfg.STORE_NAME]
        mode = c.get(cfg.KEY_BUTTON_DEFAULT, cfg.DEFAULT_STORE_VALUES[cfg.KEY_BUTTON_DEFAULT])
        download_source = None
        print("toolbar_triggered - mode=", mode)
        if mode in cfg.PAGE_DOWNLOADS.keys():
            download_source = mode
            mode = 'Download'
        print("toolbar_triggered - mode=", mode)
        print("toolbar_triggered - download_source=", download_source)
        self._count_pages_on_selected(mode, download_source=download_source)

    def _get_nltk_resource(self):
        # Retrieve the english pickle file. Can't do it from within the nltk code
        # because of our funky situation of executing a plugin from a zip file.
        # So we retrieve it here and pass it through when executing jobs.
        ENGLISH_PICKLE_FILE = 'nltk_lite/english.pickle'
        pickle_data = self.load_resources([ENGLISH_PICKLE_FILE])[ENGLISH_PICKLE_FILE]
        return pickle_data

    def _count_pages_on_selected(self, mode, download_source=None):
        if not self.is_library_selected:
            return
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0 :
            return
        book_ids = self.gui.library_view.get_selected_ids()

        statistics_to_run = [k for k in ALL_STATISTICS.keys()]
        any_valid, statistics_cols_map = self._get_column_validity(statistics_to_run)
        if not any_valid:
            if not question_dialog(self.gui, _('Configure plugin'), '<p>'+
                _('You must specify custom column(s) first. Do you want to configure this now?'),
                show_copy_button=False):
                return
            self.show_configuration()
            return

        self._do_count_pages(book_ids, statistics_cols_map, page_count_mode=mode, download_source=download_source)

    def _show_totals_for_selected(self):
        if not self.is_library_selected:
            return
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0 :
            return
        book_ids = self.gui.library_view.get_selected_ids()
        
        statistics_to_run = [k for k in ALL_STATISTICS.keys()]
        any_valid, statistics_cols_map = self._get_column_validity(statistics_to_run)
        if not any_valid:
            if not question_dialog(self.gui, _('Configure plugin'), '<p>'+
                _('You must specify custom column(s) first. Do you want to configure this now?'),
                show_copy_button=False):
                return
            self.show_configuration()
            return

        # Iterate over all the selected books and sum up the statistics
        self._do_show_totals(book_ids, statistics_cols_map)

    def _get_column_validity(self, statistics_to_run):
        '''
        Given a list of algorithms requested to be run, lookup what custom
        columns are configured and return a dict for each possible statistic
        and its associated custom column (blank if not to be run).
        '''
        db = self.gui.current_db
        all_cols = db.field_metadata.custom_field_metadata()

        library_config = cfg.get_library_config(db)
        statistics_cols_map = {}
        any_valid = False
        for statistic, statistic_col_key in cfg.ALL_STATISTICS.items():
            col = library_config.get(statistic_col_key, '')
            is_requested = statistic in statistics_to_run
            is_valid = is_requested and len(col) > 0 and col in all_cols
            if not is_valid or not col:
                statistics_cols_map[statistic] = ''
            else:
                any_valid = True
                statistics_cols_map[statistic] = col
        return any_valid, statistics_cols_map

    def count_statistics(self, book_ids, statistics_to_run, page_count_mode='Estimate', download_source=None, plugin_callback=None):
        '''
        This function is designed to be called from other plugins
        Note that the statistics functions can only be used if a
        custom column has been configured by the user first.

          book_ids - list of calibre book ids to run the statistics against

          statistics_to_run - list of statistic names to be run. Possible values:
              'PageCount', 'WordCount', 'FleschReading', 'FleschGrade', 'GunningFog'

          page_count_mode - only applies to PageCount, whether to retrieve from a website 
                rather than using an estimation algorithm. Requires each book to 
                have an identifier for the site.
                
          download_source - id of website for downloading the page count. The list is in
                  config.py in dictionary PAGE_DOWNLOADS.
                          
          plugin_callback - This is a dictionary defining the callback function.
        '''
        if statistics_to_run is None or len(statistics_to_run) == 0:
            print('Page count called but neither page nor word count requested')
            return

        # Verify we have a custom column configured to store the page/word count in
        any_valid, statistics_cols_map = self._get_column_validity(statistics_to_run)
        if (not any_valid):
            if not question_dialog(self.gui, _('Configure plugin'), '<p>'+
                _('You must specify custom column(s) first. Do you want to configure this now?'),
                show_copy_button=False):
                return
            self.show_configuration()
            return

        self.plugin_callback = plugin_callback
        
        self._do_count_pages(book_ids, statistics_cols_map, page_count_mode=page_count_mode, download_source=download_source)

    def _do_count_pages(self, book_ids, statistics_cols_map, page_count_mode='Estimate', download_source=None):
        # Create a temporary directory to copy all the ePubs to while scanning
        tdir = PersistentTemporaryDirectory('_count_pages', prefix='')

        # Queue all the books and kick off the job
        c = cfg.plugin_prefs[cfg.STORE_NAME]
        db = self.gui.current_db
        library_config = cfg.get_library_config(db)
        pages_algorithm = library_config.get(cfg.KEY_PAGES_ALGORITHM,
                                cfg.DEFAULT_LIBRARY_VALUES[cfg.KEY_PAGES_ALGORITHM])
        overwrite_existing = c.get(cfg.KEY_OVERWRITE_EXISTING,
                                   cfg.DEFAULT_STORE_VALUES[cfg.KEY_OVERWRITE_EXISTING])
        use_preferred_output = c.get(cfg.KEY_USE_PREFERRED_OUTPUT,
                                   cfg.DEFAULT_STORE_VALUES[cfg.KEY_USE_PREFERRED_OUTPUT])
        custom_chars_per_page = library_config.get(cfg.KEY_CUSTOM_CHARS_PER_PAGE,
                                   cfg.DEFAULT_LIBRARY_VALUES[cfg.KEY_CUSTOM_CHARS_PER_PAGE])
        icu_wordcount = c.get(cfg.KEY_USE_ICU_WORDCOUNT,
                              cfg.DEFAULT_STORE_VALUES[cfg.KEY_USE_ICU_WORDCOUNT])
        QueueProgressDialog(self.gui, book_ids, tdir, statistics_cols_map,
                            pages_algorithm, custom_chars_per_page, overwrite_existing, use_preferred_output, 
                            icu_wordcount, self._queue_job, db, page_count_mode=page_count_mode, download_source=download_source)

    def _queue_job(self, tdir, books_to_scan, statistics_cols_map, pages_algorithm, 
                   custom_chars_per_page, icu_wordcount, page_count_mode='Estimate', download_source=None):
        if not books_to_scan:
            if tdir:
                # All failed so cleanup our temp directory
                remove_dir(tdir)
            return

        func = 'arbitrary_n'
        cpus = self.gui.job_manager.server.pool_size
        args = ['calibre_plugins.count_pages.jobs', 'do_count_statistics',
                (books_to_scan, pages_algorithm, self.nltk_pickle, custom_chars_per_page,
                 icu_wordcount, page_count_mode, download_source, cpus)]
        desc = _('Count Page/Word Statistics')
        job = self.gui.job_manager.run_job(
                self.Dispatcher(self._get_statistics_completed), func, args=args,
                    description=desc)
        job.tdir = tdir
        job.statistics_cols_map = statistics_cols_map
        job.page_count_mode = page_count_mode
        job.download_source = download_source
        job.plugin_callback = self.plugin_callback
        self.gui.status_bar.show_message(_('Counting statistics in %d books') % len(books_to_scan))
        self.plugin_callback = None

    def _get_statistics_completed(self, job):
        if job.tdir:
            remove_dir(job.tdir)
        if job.failed:
            return self.gui.job_exception(job, dialog_title=_('Failed to count statistics'))
        self.gui.status_bar.show_message(_('Counting statistics completed'), 3000)
        book_statistics_map = job.result

        if len(book_statistics_map) == 0:
            # Must have been some sort of error in processing this book
            msg = _('Failed to generate any statistics. <b>View Log</b> for details')
            p = ErrorNotification(job.details, _('Count log'), _('Count Pages failed'), msg,
                    show_copy_button=False, parent=self.gui)
            p.show()
        else:            
            payload = (job.statistics_cols_map, book_statistics_map)
            
            if cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_ASK_FOR_CONFIRMATION, 
                                                    cfg.DEFAULT_STORE_VALUES[cfg.KEY_ASK_FOR_CONFIRMATION]):
                all_ids = set(book_statistics_map.keys())
                msg = _('<p>Count Pages plugin found <b>%d statistics(s)</b>. ') % len(all_ids) + \
                      _('Proceed with updating columns in your library?')
                self.gui.proceed_question(self._update_database_columns,
                        payload, job.details,
                        _('Count log'), _('Count complete'), msg,
                        show_copy_button=False)
            else:
                self._update_database_columns(payload)

        if job.plugin_callback:
            print("_get_statistics_completed: have callback:", job.plugin_callback)
            call_plugin_callback(job.plugin_callback, self.gui, plugin_results=book_statistics_map)

    def _update_database_columns(self, payload):
        (statistics_cols_map, book_statistics_map) = payload
 
        self.progressbar(_("Updating statistics"), on_top=True)
        total_books = len(book_statistics_map)
        self.show_progressbar(total_books)
        self.set_progressbar_label(_("Updating"))
        update_if_unchanged = cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_UPDATE_IF_UNCHANGED, 
                                                    cfg.DEFAULT_STORE_VALUES[cfg.KEY_UPDATE_IF_UNCHANGED])
 
        db = self.gui.current_db
        db_ref = db.new_api if hasattr(db, 'new_api') else db
        book_ids_to_update = []
 
        col_name_books_map = dict((col_name, dict())
                               for col_name in statistics_cols_map.values() if col_name)
        for book_id, statistics in book_statistics_map.items():
            if db_ref.has_id(book_id):
                self.set_progressbar_label(_("Updating") + " " + db_ref.field_for("title", book_id))
                self.increment_progressbar()
                for statistic, value in statistics.items():
                    col_name = statistics_cols_map[statistic]
                    
                    if update_if_unchanged or value != db_ref.field_for(col_name, book_id):
                        col_name_books_map[col_name][book_id] = value
                        book_ids_to_update.append(book_id)
            else:
                print("Book with id %d is no longer in the library." % book_id)

        for col_name, book_statistcs_map in col_name_books_map.items():
            db_ref.set_field(col_name, book_statistcs_map)

        if book_ids_to_update:
            print("About to refresh GUI - book_ids_to_update=", book_ids_to_update)
            self.gui.library_view.model().refresh_ids(book_ids_to_update)
            self.gui.library_view.model().refresh_ids(book_ids_to_update,
                                      current_row=self.gui.library_view.currentIndex().row())

        self.hide_progressbar()

    def _do_show_totals(self, book_ids, statistics_cols_map):
        totals = {}
        counts = {}
        totals[_('Selected')] = len(book_ids)
        labels_map = dict((col_name, self.gui.current_db.field_metadata.key_to_label(col_name))
                               for col_name in statistics_cols_map.values() if col_name)
        missing_statistic = False
        for book_id in book_ids:
            if not self.gui.current_db.has_id(book_id):
                print("Book with id %d is no longer in the library." % book_id)
                continue
            for statistic, col_name in statistics_cols_map.items():
                if col_name:
                    value = self.gui.current_db.get_custom(book_id, label=labels_map[col_name], index_is_id=True)
                    book_stat_total = 0
                    if value is not None and value != '':
                        try:
                            book_stat_total = float(value)
                        except ValueError:
                            missing_statistic = True
                            continue
                    else:
                        missing_statistic = True
                        continue
                    if statistic in totals:
                        totals[statistic] += book_stat_total
                        counts[statistic] += 1
                    else:
                        totals[statistic] = book_stat_total
                        counts[statistic] = 1

        # Calculate averages for all the gathered statistics except the Selected count
        averages = {}
        for statistic in statistics_cols_map.keys():
            if statistic in totals and statistic in counts and counts[statistic] > 0:
                averages[statistic] = totals[statistic] / counts[statistic]
        # Some fudgery where for the Flesch statistics we show averages only
        for stat in [cfg.STATISTIC_FLESCH_READING, cfg.STATISTIC_FLESCH_GRADE, cfg.STATISTIC_GUNNING_FOG]:
            if stat in totals:
                totals[stat] = -1  # Indicate no total available
        
        d = TotalStatisticsDialog(self.gui, totals, averages, missing_statistic)
        d.exec_()

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def progressbar(self, window_title, on_top=False):
        self.pb = ProgressBarDialog(parent=self.gui, window_title=window_title, on_top=on_top)
        self.pb.show()

    def show_progressbar(self, maximum_count):
        if self.pb:
            self.pb.set_maximum(maximum_count)
            self.pb.set_value(0)
            self.pb.show()

    def set_progressbar_label(self, label):
        if self.pb:
            self.pb.set_label(label)

    def increment_progressbar(self):
        if self.pb:
            self.pb.increment()

    def hide_progressbar(self):
        if self.pb:
            self.pb.hide()
