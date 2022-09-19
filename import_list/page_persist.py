from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import copy
from functools import partial
from threading import Thread

try:
    from qt.core import (Qt, QGridLayout, QLabel, QGroupBox, QComboBox, QApplication,
                          QHBoxLayout, QLineEdit, QRadioButton, QCheckBox,
                          QDialog, pyqtSignal, QVBoxLayout, QProgressBar, QDialogButtonBox)
except ImportError:                          
    from PyQt5.Qt import (Qt, QGridLayout, QLabel, QGroupBox, QComboBox, QApplication,
                          QHBoxLayout, QLineEdit, QRadioButton, QCheckBox,
                          QDialog, pyqtSignal, QVBoxLayout, QProgressBar, QDialogButtonBox)

from calibre.ebooks.metadata import MetaInformation
from calibre.ebooks.metadata.book.base import field_from_string
from calibre.gui2 import error_dialog
from calibre.utils.date import parse_date

import calibre_plugins.import_list.config as cfg
from calibre_plugins.import_list.page_common import WizardPage, parse_series, parse_pubdate

try:
    load_translations()
except NameError:
    pass

def truncate(string, length=50):
    return (string[:length] + '..') if len(string) > length else string

def to_int(val, strict_int=True):
    '''
    calibre templates return numbers in text float form (e.g. 5.0)
    which fails when python try to convert using int('5.0')
    this function converts to float first
    '''
    try:
        val = float(val)
    except:
        raise ValueError
    if strict_int:
        if not val.is_integer():
            raise ValueError
    return int(val)

class NullContext(object):

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        return None

    def __exit__(self, *args):
        pass


class DoubleProgressDialog(QDialog):

    all_done = pyqtSignal()
    progress_update = pyqtSignal(int, str)
    overall_update = pyqtSignal(int)

    class UserInterrupt(Exception):
        pass

    def __init__(self, selected_options, callback_fn, parent, cancelable=True):
        QDialog.__init__(self, parent)
        self.selected_options = selected_options
        self.callback_fn = callback_fn
        self._layout =  l = QVBoxLayout()
        self.setLayout(l)
        self.msg = QLabel()
        self.current_step_pb = QProgressBar(self)
        self.current_step_pb.setFormat(_('Current step progress:')+' %p %')
        if self.selected_options > 1:
            # More than one Step needs to be done! Add Overall ProgressBar
            self.overall_pb = QProgressBar(self)
            self.overall_pb.setRange(0, self.selected_options)
            self.overall_pb.setValue(0)
            self.overall_pb.setFormat(_('Step')+' %v/%m')
            self._layout.addWidget(self.overall_pb)
            self._layout.addSpacing(15)
        self.overall_step = 0
        self.current_step_value = 0
        self._layout.addWidget(self.current_step_pb)
        self._layout.addSpacing(15)
        self._layout.addWidget(self.msg, 0, Qt.AlignLeft)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Abort, self)
        self.button_box.rejected.connect(self._canceled)
        l.addWidget(self.button_box)
        if not cancelable:
            self.button_box.setVisible(False)
        self.cancelable = cancelable
        self.canceled = False
        self.setWindowTitle(_('Importing')+'...')
        self.setMinimumWidth(800)
        self.error = None
        self.progress_update.connect(self.on_progress_update, type=Qt.QueuedConnection)
        self.overall_update.connect(self.on_overall_update, type=Qt.QueuedConnection)
        self.all_done.connect(self.on_all_done, type=Qt.QueuedConnection)

    def _canceled(self, *args):
        self.canceled = True
        self.button_box.setDisabled(True)
        self.title = _('Aborting')+'...'

    def reject(self):
        pass

    def accept(self):
        pass

    def update_progress(self, processed_steps, msg):
        if self.canceled:
            raise self.UserInterrupt
        self.progress_update.emit(processed_steps, msg)

    def on_progress_update(self, processed_steps, msg):
        self.current_step_value += processed_steps
        self.current_step_pb.setValue(self.current_step_value)
        self.msg.setText(msg)

    def update_overall(self, steps):
        self.overall_update.emit(steps)

    def on_overall_update(self, steps):
        self.current_step_value = 0
        self.current_step_pb.setRange(0, steps)
        if self.selected_options > 1:
            self.overall_step += 1
            self.overall_pb.setValue(self.overall_step)

    def exec_(self):
        self.thread = Thread(target=self.do_it)
        self.thread.start()
        return QDialog.exec_(self)

    def on_all_done(self):
        QApplication.beep()
        QDialog.accept(self)

    def do_it(self):
        try:
            self.callback_fn(pbar=self)
        except self.UserInterrupt as e:
            # raised when abort button is pressed.
            QDialog.reject(self)
        except Exception as err:
            import traceback
            try:
                err = str(err)
            except:
                err = repr(err)
            self.error = (err, traceback.format_exc())
        finally:
            self.all_done.emit()


class PersistPage(WizardPage):

    ID = 3

    def init_controls(self):
        self.block_events = True
        self.setTitle(_('Step 3: Save your imported list / configuration'))
        l = QHBoxLayout(self)
        self.setLayout(l)

        rlgb = QGroupBox(_('Reading List plugin:'), self)
        rlgb.setStyleSheet('QGroupBox { font-weight: bold; }')
        l.addWidget(rlgb, 1)
        rlgbl = QGridLayout()
        rlgb.setLayout(rlgbl)
        rl_lbl = QLabel(_('If you have the <a href="http://www.mobileread.com/forums/showthread.php?t=134856">Reading list</a> plugin installed, '
                        'you can store the imported books into a list for use by that plugin.'), self)
        rl_lbl.setWordWrap(True)
        rl_lbl.linkActivated.connect(self.open_external_link)
        self.rl_ignore_opt = QRadioButton(_('&Do not use the Reading List plugin'), self)
        self.rl_ignore_opt.setChecked(True)
        self.rl_create_opt = QRadioButton(_('Create a &new list:'), self)
        self.rl_create_opt.toggled[bool].connect(self._on_create_reading_list_toggled)
        self.rl_update_opt = QRadioButton(_('&Update an existing list:'), self)
        self.rl_update_opt.toggled[bool].connect(self._on_update_reading_list_toggled)
        self.rl_clear_chk = QCheckBox(_('&Clear list first replacing with the imported books'), self)
        self.rl_clear_chk.setChecked(True)
        self.rl_create_ledit = QLineEdit('', self)
        self.rl_create_ledit.textChanged.connect(self._on_create_reading_list_name_changed)
        self.rl_update_combo = QComboBox(self)
        self.rl_update_combo.activated[int].connect(self._on_reading_list_activated)
        rlgbl.addWidget(rl_lbl, 0, 0, 1, 4)
        rlgbl.addWidget(self.rl_ignore_opt, 2, 0, 1, 3)
        rlgbl.addWidget(self.rl_create_opt, 3, 0, 1, 2)
        rlgbl.addWidget(self.rl_create_ledit, 3, 2, 1, 1)
        rlgbl.addWidget(self.rl_update_opt, 4, 0, 1, 2)
        rlgbl.addWidget(self.rl_update_combo, 4, 2, 1, 1)
        rlgbl.addWidget(self.rl_clear_chk, 5, 1, 1, 2)
        rlgbl.setColumnMinimumWidth(0, 16)
        rlgbl.setColumnStretch(3, 1)
        rlgbl.setRowMinimumHeight(1, 10)
        rlgbl.setRowStretch(6, 1)

        l.addSpacing(10)

        sgb = QGroupBox(_('Save configuration:'), self)
        sgb.setStyleSheet('QGroupBox { font-weight: bold; }')
        l.addWidget(sgb, 1)
        sgbl = QGridLayout()
        sgb.setLayout(sgbl)
        settings_lbl = QLabel(_('You can choose to store the current import settings, if you intend to import from this source again in future.'), self)
        settings_lbl.setWordWrap(True)
        self.settings_dont_save_opt = QRadioButton(_('&Do not save the current settings'), self)
        self.settings_dont_save_opt.setChecked(True)
        self.settings_save_opt = QRadioButton(_('&Save settings as:'), self)
        self.save_settings_combo = QComboBox(self)
        self.save_settings_combo.setMinimumWidth(150)
        self.save_settings_combo.setEditable(True)
        self.save_settings_combo.setMaxCount(25)
        self.save_settings_combo.setInsertPolicy(QComboBox.InsertAtTop)
        self.save_settings_combo.activated[int].connect(self._on_save_settings_activated)
        self.save_settings_combo.editTextChanged.connect(self._on_save_settings_edit_text_changed)
        sgbl.addWidget(settings_lbl, 0, 0, 1, 4)
        sgbl.addWidget(self.settings_dont_save_opt, 2, 0, 1, 2)
        sgbl.addWidget(self.settings_save_opt, 3, 0, 1, 1)
        sgbl.addWidget(self.save_settings_combo, 3, 1, 1, 1)
        sgbl.setColumnStretch(3, 1)
        sgbl.setRowMinimumHeight(1, 10)
        sgbl.setRowStretch(4, 1)

        self.block_events = False

    def initializePage(self):
        self.block_events = True
        if self.reading_list_action is None:
            self.rl_create_opt.setEnabled(False)
            self.rl_create_ledit.setEnabled(False)
            self.rl_update_opt.setEnabled(False)
            self.rl_update_combo.setEnabled(False)
            self.rl_clear_chk.setEnabled(False)
        else:
            self.all_list_names = self.reading_list_action.get_list_names(exclude_auto=False)
            list_names = self.reading_list_action.get_list_names()
            self.rl_update_combo.clear()
            for list_name in list_names:
                self.rl_update_combo.addItem(list_name)

            context = self.library_config[cfg.KEY_CURRENT][cfg.KEY_READING_LIST]
            list_name = context[cfg.KEY_READING_LIST_NAME]
            if list_name in list_names:
                self.rl_update_opt.setChecked(True)
                idx = max(list_names.index(list_name), 0)
                self.rl_update_combo.setCurrentIndex(idx)

            clear_list = context[cfg.KEY_READING_LIST_CLEAR]
            self.rl_clear_chk.setChecked(clear_list)

        setting_names = cfg.get_setting_names(self.db)
        self.save_settings_combo.clear()
        for setting_name in setting_names:
            self.save_settings_combo.addItem(setting_name)
        default_setting_name = self.info['current_setting']
        if default_setting_name in setting_names:
            idx = max(setting_names.index(default_setting_name), 0)
            self.save_settings_combo.setCurrentIndex(idx)
        else:
            self.save_settings_combo.clearEditText()

        self.block_events = False

    def _on_create_reading_list_toggled(self, checked):
        if self.block_events:
            return
        if checked:
            self.rl_create_ledit.setFocus()

    def _on_create_reading_list_name_changed(self):
        if self.block_events:
            return
        self.rl_create_opt.setChecked(True)

    def _on_update_reading_list_toggled(self, checked):
        if self.block_events:
            return
        if checked:
            self.rl_update_combo.setFocus()

    def _on_reading_list_activated(self, new_index):
        if self.block_events:
            return
        self.rl_update_opt.setChecked(True)

    def _on_save_settings_activated(self, index):
        if self.block_events:
            return
        self.settings_save_opt.setChecked(True)

    def _on_save_settings_edit_text_changed(self):
        if self.block_events:
            return
        self.settings_save_opt.setChecked(True)

    # Update: Modified to operate on a single book instead of iterating over a list {
    def _create_empty_book(self, book):
        mi = MetaInformation(book['!calibre_title'], book['!calibre_authors'].split('&'))
        book['!id'] = self.db.import_book(mi, [])
        book['!mi'] = self.db.get_metadata(book['!id'], index_is_id=True, get_user_categories=False)
        self._apply_metadata_updates(book)
            
    def _apply_metadata_updates(self, book):
        mi = book['!mi']
        self._update_mi_for_book(book, mi)
        self.db.set_metadata(book['!id'], mi, commit=False)
        #self.db.commit()
    #}
            
    def _update_mi_for_book(self, book, mi):
        self.custom_columns = self.db.field_metadata.custom_field_metadata()
        invalid_columns = []
        overwrite_title_author = book['!status'] != 'empty'
        for k, val in book.items():
#             debug_print("page_persist::_update_mi_for_book loop start- k=", k, " val=", val)
            if not k.startswith('!calibre_') or k == '!calibre_authors_sort':
                # Original data from import list or special status fields etc to ignore
                continue
            if k == '!calibre_title':
                if overwrite_title_author:
                    mi.title = val
            elif k == '!calibre_authors':
                if overwrite_title_author:
                    mi.authors = val.split('&')
            elif k == '!calibre_series':
                series_name, series_index = parse_series(val)
                if series_name:
                    mi.series = series_name
                    mi.series_index = series_index
            elif k == '!calibre_pubdate':
                mi.pubdate = parse_pubdate(val)
            elif k == '!calibre_publisher':
                mi.publisher = val
            elif k == '!calibre_rating':
                if val:
                    mi.rating = 2 * float(val)
            elif k == '!calibre_tags':
                tags = [t.strip() for t in val.split(',')]
                if tags:
                    mi.tags = list(set(mi.tags).union(set(tags)))
            elif k == '!calibre_comments':
                mi.comments = val
            elif k == '!calibre_languages':
                from calibre.ebooks import normalize
                from calibre.utils.localization import langnames_to_langcodes
                raw_langs = [normalize(l.strip()) for l in val.split(',')]
                langs = langnames_to_langcodes(raw_langs)
                langs = set([x if y is None else y for (x, y) in langs.items()])
                if langs:
                    mi.languages = langs
            elif k.startswith('!calibre_identifier:'):
                id_name = k.split('!calibre_identifier:')[1]
                mi.set_identifier(id_name, val)
            else:
                # Must be a custom column
                column = k.split('!calibre_')[1]
                if column not in invalid_columns:
                    if not self._update_mi_custom_column(mi, column, val):
                        invalid_columns.append(column)
                
    def _update_mi_custom_column(self, mi, column, val):
        # FIX: { : empty values for numerical fields throwing exception ValueError: could not convert string to float: ''
        # fields that are not selected in the d.selected_names can have None values returned by mi.format_field
        if val in ['', None]:
            return False
        #}
        if column not in self.custom_columns:
            # The user has deleted the custom column without updating the action rules
            error_dialog(self, _('Custom Column Missing'),
                _('You are importing to a custom column \'%s\' which does not exist in this library.<p>')%column +
                _('This column will be ignored. Either add a matching custom column or edit your import statement.'),
                show=True)
            return False
        
        col = self.custom_columns[column]
        cmeta = mi.get_user_metadata(column, True)
        if cmeta is None:
            print((_('ImportList plugin: no metadata found for column:'), column))
            return False
        if col['datatype'] == 'bool':
            if val.lower() in ['true','yes','y','1']:
                new_value = True
            elif val.lower() in ['n/a']:
                new_value = ''
            else:
                new_value = False
        # field_from_string priority for dates is for the month to be one in all timezones
        # thid can lead to the date being one day off. We call parse_date directly instead.
        elif col['datatype'] == 'datetime':
            new_value = parse_date(val)
        # use to_int to convert float with zero fractional part (e.g 1.0) to integer
        # python int() (and consequently field_from_string) cannot handle these
        elif col['datatype'] == 'int':
            new_value = to_int(val)
        else:
            new_value = field_from_string(column, val, cmeta)
        mi.set(column, new_value)
        return True

    def _add_to_reading_list(self, list_name, is_new_list, clear_list_first):
        book_id_list = [book['!id'] for book in self.info['save_books']]
        if is_new_list:
            self.reading_list_action.create_list(list_name, book_id_list)
        else:
            if clear_list_first:
                self.reading_list_action.clear_list(list_name, refresh_screen=False, display_warnings=False)
            self.reading_list_action.add_books_to_list(list_name, book_id_list, refresh_screen=False, display_warnings=False)

    def _save_setting(self, setting_name, is_new_setting):
        if is_new_setting:
            setting = {}
            self.library_config[cfg.KEY_SAVED_SETTINGS][setting_name] = setting
        else:
            setting = self.library_config[cfg.KEY_SAVED_SETTINGS][setting_name]
        current = self.library_config[cfg.KEY_CURRENT]
        import_type = current[cfg.KEY_IMPORT_TYPE]
        setting.clear()
        for k,v in current[import_type].items():
            setting[k] = copy.deepcopy(v)
        setting[cfg.KEY_IMPORT_TYPE] = import_type
        setting[cfg.KEY_READING_LIST] = copy.deepcopy(current[cfg.KEY_READING_LIST])
        if import_type == cfg.KEY_IMPORT_TYPE_CLIPBOARD:
            self.library_config[cfg.KEY_LAST_CLIPBOARD_SETTING] = setting_name
        elif import_type == cfg.KEY_IMPORT_TYPE_CSV:
            self.library_config[cfg.KEY_LAST_CSV_SETTING] = setting_name
        elif import_type == cfg.KEY_IMPORT_TYPE_WEB:
            self.library_config[cfg.KEY_LAST_WEB_SETTING] = setting_name

    # Update: add progress bar {
    def pd_callback(self, add_empty_books, metadata_update_books, pbar):
        try:
            count = len(add_empty_books)
            if  count > 0:
                pbar.update_overall(count)
                for idx, book in enumerate(add_empty_books, 1):
                    self._create_empty_book(book)
                    msg = _('Adding books (%(idx)d of %(count)d): %(title)s') % \
                                {'idx':idx, 'title':truncate(book['!calibre_title']), 'count':count}
                    pbar.update_progress(1, msg)
                    # this is called only if running from cmdline
                    if hasattr(self, 'reinitialize_db'):
                        self.reinitialize_db(idx, add_empty_books, metadata_update_books, pbar)

            count = len(metadata_update_books)
            if count > 0:
                pbar.update_overall(count)
                for idx, book in enumerate(metadata_update_books, 1):
                    self._apply_metadata_updates(book)
                    msg = _('Updating books (%(idx)d of %(count)d): %(title)s') % \
                            {'idx':idx, 'title':truncate(book['!calibre_title']), 'count':count}
                    pbar.update_progress(1, msg)
                    # this is called only if running from cmdline
                    if hasattr(self, 'reinitialize_db'):
                        self.reinitialize_db(idx, add_empty_books, metadata_update_books, pbar)

        finally:
            self.db.commit()
       #}

    def validatePage(self):
        reading_list_name = ''
        is_new_list = False
        clear_list_first = True
        setting_name = ''
        is_new_setting = False

        if self.rl_create_opt.isChecked():
            # Validate the user has specified a valid reading list name
            reading_list_name = str(self.rl_create_ledit.text()).strip()
            if len(reading_list_name) == 0:
                error_dialog(self, _('Invalid List Name'), _('You have not specified a reading list name'), show=True)
                self.rl_create_ledit.setFocus()
                return False
            # This is a new item that shouldn't currently be in the list.
            for name in self.all_list_names:
                if name.lower() == reading_list_name.lower():
                    error_dialog(self, _('Invalid List Name'), _('Another list exists with this name'), show=True)
                    self.rl_create_ledit.setFocus()
                    return False
            is_new_list = True

        elif self.rl_update_opt.isChecked():
            # No validation required if updating a list, since user can only choose from the combo.
            reading_list_name = str(self.rl_update_combo.currentText()).strip()
            clear_list_first = self.rl_clear_chk.isChecked()

        if self.settings_save_opt.isChecked():
            # Validate the user has specified a valid save setting name
            setting_name = str(self.save_settings_combo.currentText()).strip()
            if len(setting_name) == 0:
                error_dialog(self, _('Invalid Setting Name'), _('You have not specified a setting name'), show=True)
                self.save_settings_combo.setFocus()
                return False

            same_name_index = self.save_settings_combo.findText(setting_name, Qt.MatchExactly)
            if same_name_index >= 0:
                setting_name = str(self.save_settings_combo.itemText(same_name_index))
            else:
                is_new_setting = True

        # Once we get to this point we are definitely going ahead with the actions

        add_empty_books = [book for book in self.info['save_books']
                           if book['!status'] == 'empty' and book['!id'] == '']

        metadata_update_books = [book for book in self.info['save_books']
                                 if book['!mi'] is not None and book['!overwrite_metadata']]

        # Update: add progress bar {
        selected_options = 0
        if len(add_empty_books) > 0: selected_options += 1
        if len(metadata_update_books) > 0: selected_options += 1
        
        pd = DoubleProgressDialog(
            selected_options,
            partial(self.pd_callback, add_empty_books, metadata_update_books),
            self
        )
        
        gui = self.wizard().gui
        gui.tags_view.blockSignals(True)
        try:
            # Put Last Modified plugin into hibernation mode durating lifetime of the chain
            last_modified_hibernate = NullContext()
            # Test in case plugin not run from gui
            if gui and hasattr(gui, 'iactions'):
                last_modified_hibernate = getattr(gui.iactions.get('Last Modified'), 'hibernate', NullContext())
            with last_modified_hibernate:
                pd.exec_()

            pd.thread = None

            if pd.error is not None:
                return error_dialog(self, _('Failed'),
                        pd.error[0], det_msg=pd.error[1],
                        show=True)
        finally:   
            gui.tags_view.blockSignals(False)
            gui.tags_view.recount()
        #}

        context = self.library_config[cfg.KEY_CURRENT][cfg.KEY_READING_LIST]
        context[cfg.KEY_READING_LIST_NAME] = ''
        context[cfg.KEY_READING_LIST_CLEAR] = True
        if reading_list_name:
            context[cfg.KEY_READING_LIST_NAME] = reading_list_name
            context[cfg.KEY_READING_LIST_CLEAR] = clear_list_first
            self._add_to_reading_list(reading_list_name, is_new_list, clear_list_first)
            self.info['reading_list'] = reading_list_name

        if setting_name:
            self._save_setting(setting_name, is_new_setting)

        return True
