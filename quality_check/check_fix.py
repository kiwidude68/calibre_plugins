from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from collections import defaultdict
import os
import shutil
import traceback
import unicodedata

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.db.fields import CompositeField
from calibre.ebooks.metadata import title_sort
from calibre.gui2 import info_dialog, choose_dir, error_dialog
from calibre.ptempfile import TemporaryDirectory
from calibre.utils.config import prefs
from calibre.utils.localization import get_udc

import calibre_plugins.quality_check.config as cfg
from calibre_plugins.quality_check.check_base import BaseCheck
from calibre_plugins.quality_check.dialogs import (ResultsSummaryDialog, ApplyFixProgressDialog,
                                                   QualityProgressDialog)
from calibre_plugins.quality_check.helpers import get_formatted_author_initials, get_title_authors_text
from calibre_plugins.quality_check.mobi6 import MinimalMobiUpdater


class FixCheck(BaseCheck):
    '''
    All fix operations.
    '''
    def perform_check(self, menu_key):
        if menu_key == 'fix_swap_author_names':
            self.fix_swap_author_names()
        elif menu_key == 'fix_author_initials':
            self.fix_author_initials()
        elif menu_key == 'fix_author_ascii':
            self.fix_author_names_to_ascii()
        elif menu_key == 'fix_title_sort':
            self.fix_title_sort()
        elif menu_key == 'check_fix_book_size':
            self.check_and_update_file_sizes()
        elif menu_key == 'check_fix_book_paths':
            self.check_and_rename_book_paths()
        elif menu_key == 'cleanup_opf_files':
            self.cleanup_opf_folders()
        elif menu_key == 'fix_mobi_asin':
            self.fix_mobi_asin()
        elif menu_key == 'fix_normalize_fields':
            self.fix_normalize_fields()
        elif menu_key == 'fix_normalize_notes':
            self.fix_normalize_notes()
        else:
            return error_dialog(self.gui, _('Quality Check failed'),
                                _('Unknown menu key for %s of \'%s\'')%('FixCheck', menu_key),
                                show=True, show_copy_button=False)


    def fix_swap_author_names(self):
        '''
        This operation works only on selected ids, it does not change all author
        occurrences across the library!
        '''
        def swap_names(a, target_with_comma):
            if not target_with_comma and ',' in a:
                parts = a.split(',')
                if len(parts) <= 1:
                    return a
                surname = parts[0]
                return '%s %s' % (' '.join(parts[1:]), surname)
            if target_with_comma and ',' not in a:
                parts = a.split(None)
                if len(parts) <= 1:
                    return a
                surname = parts[-1]
                return '%s, %s' % (surname, ' '.join(parts[:-1]))
            return a    # Don't need to change

        db = self.gui.current_db
        previous = self.gui.library_view.currentIndex()
        book_ids = self.gui.library_view.get_selected_ids()
        if book_ids:
            for book_id in book_ids:
                authors = db.authors(book_id, index_is_id=True)
                if authors:
                    authors = [a.strip().replace('|', ',') for a in authors.split(',')]
                    has_comma = ',' in authors[0]
                    new_authors = [swap_names(a, not has_comma) for a in authors]
                    db.set_authors(book_id, new_authors, notify=False)

            self.gui.library_view.model().refresh_ids(book_ids)
            current = self.gui.library_view.currentIndex()
            self.gui.library_view.model().current_changed(current, previous)
            self.gui.tags_view.recount()

    def fix_author_initials(self):
        '''
        This operation works only on selected ids, it does not change all author
        occurrences across the library!
        '''
        def rename_book_author(book_id, db):
            authors = db.authors(book_id, index_is_id=True)
            if authors:
                authors = [a.strip().replace('|', ',') for a in authors.split(',')]
                new_authors = [get_formatted_author_initials(initials_mode, a)
                               for a in authors]
                if authors != new_authors:
                    db.set_authors(book_id, new_authors, notify=False)
                    return True
            return False

        c = cfg.plugin_prefs[cfg.STORE_OPTIONS]
        initials_mode = c.get(cfg.KEY_AUTHOR_INITIALS_MODE, cfg.AUTHOR_INITIALS_MODES[0])
        previous = self.gui.library_view.currentIndex()
        book_ids = self.gui.library_view.get_selected_ids()
        if book_ids:
            d = QualityProgressDialog(self.gui, book_ids, rename_book_author, self.gui.current_db,
                              action_type=_('Reformatting author initials for'))
            self.gui.library_view.model().refresh_ids(book_ids)
            current = self.gui.library_view.currentIndex()
            self.gui.library_view.model().current_changed(current, previous)
            self.gui.tags_view.recount()
            msg = _('Reformatted initials for %d of %d book authors') %(len(d.result_ids), d.total_count)
            self.gui.status_bar.showMessage(msg)


    def fix_author_names_to_ascii(self):
        '''
        This operation works only on selected ids, it does not change all author
        occurrences across the library!
        '''
        handler = get_udc()

        def rename_book_author(book_id, db):
            authors = db.authors(book_id, index_is_id=True)
            if authors:
                authors = [a.strip().replace('|', ',') for a in authors.split(',')]
                new_authors = [handler.decode(a) for a in authors]
                if authors != new_authors:
                    db.set_authors(book_id, new_authors, notify=False)
                    return True
            return False

        previous = self.gui.library_view.currentIndex()
        book_ids = self.gui.library_view.get_selected_ids()
        if book_ids:
            d = QualityProgressDialog(self.gui, book_ids, rename_book_author, self.gui.current_db,
                              action_type=_('Renaming authors to ascii for'))
            self.gui.library_view.model().refresh_ids(book_ids)
            current = self.gui.library_view.currentIndex()
            self.gui.library_view.model().current_changed(current, previous)
            self.gui.tags_view.recount()
            msg = _('Renamed to ascii %d of %d book authors') %(len(d.result_ids), d.total_count)
            self.gui.status_bar.showMessage(msg)


    def fix_title_sort(self):

        def adjust_book_title_sort(book_id, db):
            current_title_sort = db.title_sort(book_id, index_is_id=True)
            current_languages = db.languages(book_id, index_is_id=True)
            book_lang = None
            if current_languages:
                book_lang = current_languages.split(',')[0]
            title = db.title(book_id, index_is_id=True)
            new_sort = title_sort(title, lang=book_lang)
            if current_title_sort != new_sort:
                db.set_title_sort(book_id, new_sort, notify=False)
                return True
            return False

        total_count, result_ids, cancelled_msg = self.check_all_files(adjust_book_title_sort, show_matches=False,
                                                                  status_msg_type=_('books with incorrect title sort'))
        msg = _('Checked %d books, updated %d title sorts%s') % \
                    (total_count, len(result_ids), cancelled_msg)
        self.gui.status_bar.showMessage(msg)
        if len(result_ids) == 0:
            self.gui.status_bar.showMessage(_('All title sorts are correct'))
            return
        self.gui.library_view.model().refresh_ids(list(result_ids))


    def check_and_update_file_sizes(self):
        self.updated_format_count = 0

        def evaluate_book(book_id, db):
            formats = db.formats(book_id, index_is_id=True, verify_formats=False)
            if not formats:
                return False
            mark_book = False
            for fmt in formats.split(','):
                db_size = db.new_api.format_db_size(book_id, fmt)
                book_path = db.format_abspath(book_id, fmt, index_is_id=True)
                if not book_path:
                    self.log.error('Unable to find path to book id:', book_id, db.title(book_id, index_is_id=True))
                    continue
                if os.path.exists(book_path):
                    actual_size = os.path.getsize(book_path)
                    if actual_size != db_size:
                        mark_book = True
                        self.updated_format_count += 1
                        self.log('Format size change for fmt:',fmt,'from:',db_size,'to:',actual_size)
                        db.format_metadata(book_id, fmt, update_db=True, commit=True)
            return mark_book
        if not (hasattr(self.gui.current_db, 'new_api') and
                hasattr(self.gui.current_db.new_api, 'format_db_size')):
            return error_dialog(self.gui, _('Quality Check failed'),
                            _('"Check and repair book sizes" requires calibre '
                              'version 5.9 or higher.'),
                            show=True, show_copy_button=False)
        total_count, result_ids, cancelled_msg = self.check_all_files(evaluate_book,
                                                                  marked_text='file_size_updated',
                                                                  status_msg_type=_('books for invalid file sizes'))
        msg = _('Checked %d books, updated %d format sizes in %d books%s') % \
                    (total_count, self.updated_format_count, len(result_ids), cancelled_msg)
        self.gui.status_bar.showMessage(msg)
        if len(result_ids) == 0:
            self.gui.status_bar.showMessage(_('All book format sizes are correct'))
            return
        self.gui.library_view.model().refresh_ids(list(result_ids))


    def check_and_rename_book_paths(self):

        def evaluate_book(book_id, db):
            existing_path = db.path(book_id, index_is_id=True).replace(os.sep, '/')
            title = db.title(book_id, index_is_id=True)
            author = [a.replace('|', ',') for a in (db.authors(book_id, index_is_id=True) or '').split(',')][0]
            new_path = db.backend.construct_path_name(book_id, title, author).replace(os.sep, '/')
            if existing_path == new_path:
                return False
            self.log('Renaming book: %s => %s' % (existing_path, new_path))
            db.new_api.update_path(set([book_id]))
            return True

        total_count, result_ids, cancelled_msg = self.check_all_files(evaluate_book,
                                                                  marked_text='book_path_updated',
                                                                  status_msg_type=_('books with paths missing commas'))
        msg = _('Checked %d books, updated %d paths%s') % \
                    (total_count, len(result_ids), cancelled_msg)
        self.gui.status_bar.showMessage(msg)
        if len(result_ids) == 0:
            self.gui.status_bar.showMessage(_('All books have up to date paths'))
            return
        self.gui.library_view.model().refresh_ids(list(result_ids))


    def cleanup_opf_folders(self):
        '''
        Requested by theducks. Caters for a behaviour in Calibre whereby using the
        "Remove books from device" menu option against a folder will only delete the
        book formats and not any cover.jpg or .opf files, leaving orphaned files.
        '''
        path = choose_dir(self.gui, 'quality check plugin:clean empty folder dialog',
                _('Choose directory to cleanup'))
        if not path:
            return
        library_path = prefs['library_path']
        if path.startswith(library_path):
            return error_dialog(self.gui, _('Invalid Folder'),
                    _('You should not run this feature against a Calibre library folder.')+'<br>' +
                    _('If you do you will remove "Empty book" entries and corrupt your database.'),
                    show=True)

        messages = []
        errors = []
        # For our very top level folder we will NEVER delete this.
        self._cleanup_directory_if_needed(path, messages, errors, delete_parent=False)

        if len(messages) == 0 and len(errors) == 0:
            self.gui.status_bar.showMessage(_('No files/folders were found to be deleted'))
            return

        c = cfg.plugin_prefs[cfg.STORE_OPTIONS]
        suppress_dialog = c.get(cfg.KEY_SUPPRESS_FIX_DIALOG, False)
        if suppress_dialog:
            self.gui.status_bar.showMessage(_('Cleanup completed'))
            return

        msg = _('Deleted %d files/folders with %d errors. See details for more info.') % \
                (len(messages), len(errors))
        messages.extend(errors)
        det_msg = '\n'.join(messages)
        return info_dialog(self.gui, _('Cleanup completed'), msg, det_msg=det_msg, show=True)


    def _cleanup_directory_if_needed(self, dirname, messages, errors, delete_parent=True):
        self.log('Analysing folder', dirname)
        self._delete_orphaned_opf_files(dirname, messages, errors)

        files = os.listdir(dirname)
        safe_to_delete_folder = True
        for filename in files:
            full_path = os.path.join(dirname, filename)
            if os.path.isdir(full_path):
                if not self._cleanup_directory_if_needed(full_path, messages, errors):
                    # As we still have a subfolder, cannot delete this parent
                    self.log('Non empty subfolder', full_path)
                    safe_to_delete_folder = False
            else:
                # Any other file being present in this folder means we should not delete it
                safe_to_delete_folder = False

        if safe_to_delete_folder and delete_parent:
            self.log('Removing folder', dirname)
            try:
                shutil.rmtree(dirname)
                messages.append(_('Removed folder: %s') % dirname)
            except:
                self.log.error('Unable to remove folder:', dirname)
                self.log(traceback.format_exc())
                errors.append(_('ERROR removing folder: %s') % dirname)
                safe_to_delete_folder = False
        return safe_to_delete_folder


    def _delete_orphaned_opf_files(self, dirname, messages, errors):
        all_files = os.listdir(dirname)
        all_opf_files = [f for f in all_files if f.lower().endswith('.opf')]
        all_non_opf_files = set(all_files) - set(all_opf_files)
        files_to_delete = []

        for opf_file in all_opf_files:
            base, _extension = os.path.splitext(opf_file)
            matching_files = [f for f in all_non_opf_files if f.lower().startswith(base.lower()+'.')]
            self.log('\tAnalysing opf file: ', opf_file)
            self.log('\tMatching files: ', matching_files)
            safe_to_delete = True

            for m in matching_files:
                matching_extension = os.path.splitext(m)[1]
                if matching_extension.lower() != '.jpg':
                    self.log('\tCannot remove .opf because found: ', m)
                    safe_to_delete = False
                    break
            if safe_to_delete:
                self.log('\tSafe to delete: ', opf_file)
                files_to_delete.append(os.path.join(dirname, opf_file))
                for m in matching_files:
                    files_to_delete.append(os.path.join(dirname, m))

        for f in files_to_delete:
            self.log('\tRemoving file', f)
            try:
                os.remove(f)
                messages.append(_('Removed file: %s')%f)
            except:
                self.log.error('Unable to remove file:', f)
                self.log(traceback.format_exc())
                errors.append(_('ERROR removing file: %s')%f)

    def fix_mobi_asin(self):

        def get_asin(book_id):
            identifiers = db.get_identifiers(book_id, index_is_id=True)
            if identifiers is not None:
                for key, val in identifiers.items():
                    if key.lower() in ['asin','mobi-asin']:
                        return 'ASIN '+_('identifier found'), val
                for key, val in identifiers.items():
                    if key.lower() == 'amazon':
                        return 'Amazon.com '+_('identifier found'), val
                for key, val in identifiers.items():
                    if key.lower().startswith('amazon_'):
                        return key+' '+_('identifier found'), val
            # No amazon id present, so use value off the book
            uuid = db.uuid(book_id, index_is_id=True)
            return _('No ASIN found, using uuid'), uuid

        def apply_fix(book_id):
            fmts_to_fix = []
            for fmt in ['MOBI', 'AZW', 'AZW3']:
                if db.has_format(book_id, fmt, index_is_id=True):
                    fmts_to_fix.append(fmt)
            if not fmts_to_fix:
                self.log('No MOBI/AZW/AZW3 format for book: <b>%s</b>'% get_title_authors_text(db, book_id))
                return False

            for fmt in fmts_to_fix:
                self.log('%s book to update: <b>%s</b>' % (fmt, get_title_authors_text(db, book_id)))

                asin_info, asin = get_asin(book_id)
                self.log('\t%s: %s' % (asin_info, asin))

                file_src = os.path.join(tdir, u'%d.%s'%(book_id, fmt.lower()))
                with lopen(file_src, 'wb') as f:
                    db.copy_format_to(book_id, fmt, f, index_is_id=True)

                with open(file_src, 'r+b') as stream:
                    mu = MinimalMobiUpdater(stream)
                    mu.update(asin, b'EBOK')
                    stream.seek(0)

                    # Add the format back into our library
                    db.add_format(book_id, fmt, stream, index_is_id=True)
            return True

        db = self.gui.current_db
        book_ids = self.gui.library_view.get_selected_ids()
        if book_ids:
            with TemporaryDirectory('_qc_asin_fix') as tdir:
                d = ApplyFixProgressDialog(self.gui, _('Fixing ASIN for %d books'), book_ids, tdir, apply_fix)
                d.exec_()

            c = cfg.plugin_prefs[cfg.STORE_OPTIONS]
            suppress_dialog = c.get(cfg.KEY_SUPPRESS_FIX_DIALOG, False)
            if suppress_dialog:
                self.gui.status_bar.showMessage(_('Fix ASIN completed'))
                return
            sd = ResultsSummaryDialog(self.gui, _('Quality Check'),
                                     _('%d books updated, see log for details')%len(d.updated_ids),
                                     self.log)
            sd.exec_()


    def fix_normalize_fields(self):
        db = self.gui.current_db.new_api

        # retrive text fields
        fields = set()
        for k,v in db.fields.items():
            if v.metadata['datatype'] != 'text' or isinstance(v, CompositeField):
                continue
            fields.add(k)
        for f in ['languages', 'identifiers', 'ondevice', 'formats', 'path', 'uuid']:
            if f in fields:
                fields.remove(f)

        update_map = defaultdict(dict)

        def normalize(val):
            if isinstance(val, str):
                return unicodedata.normalize('NFC', val)
            else:
                return tuple(normalize(v) for v in val)

        # retrive new values
        def evaluate_book(book_id, db):
            mark_book = False

            for field in fields:
                val = db.new_api.field_for(field, book_id)
                if not val:
                    continue
                val_norm = normalize(val)
                if val != val_norm:
                    mark_book = True
                    update_map[field][book_id] = val_norm

            return mark_book

        total_count, result_ids, cancelled_msg = self.check_all_files(evaluate_book,
                                                                  marked_text='fix_normalize_fields',
                                                                  status_msg_type=_('books for normalize text fields'))

        # update the fields
        total_field_count = 0
        for field, val_map in update_map.items():
            total_field_count += len(val_map)
            db.set_field(field, val_map)

        # the default author sort are stored separatly
        sort_map = {}
        for author_id, val in db.fields['authors'].table.asort_map.items():
            val_norm = normalize(val)
            if val != val_norm:
                sort_map[author_id] = val_norm
        if sort_map:
            db.set_sort_for_authors(sort_map, update_books=False)

        msg = _('Checked %d books, normalize fields %d in %d books, and %d author sort key%s') % \
                    (total_count, total_field_count, len(result_ids), len(sort_map), cancelled_msg)
        self.gui.status_bar.showMessage(msg)
        if len(result_ids) == 0 and len(sort_map) == 0:
            self.gui.status_bar.showMessage(_('All text fields are normalize'))
            return
        self.gui.library_view.model().refresh_ids(list(result_ids))

    def fix_normalize_notes(self):
        db = self.gui.current_db.new_api
        if not hasattr(db, 'get_all_items_that_have_notes'):
            return error_dialog(self.gui, _('Quality Check failed'),
                            _('"Normalize the notes" requires calibre version 7.0 or higher.'),
                            show=True, show_copy_button=False)

        def normalize(val):
            return unicodedata.normalize('NFC', val)

        field_id_notes = defaultdict(dict)
        total_count = 0
        total_update_count = 0
        all_notes = db.get_all_items_that_have_notes()

        for field, notes in all_notes:
            for item_id in notes:
                note_data = db.notes_data_for(field, item_id)
                note = note_data.get('doc')
                if not note:
                    continue
                note_norm = normalize(note)
                if note != note_norm:
                    note_data['doc'] = note_norm
                    field_id_notes[field][item_id] = note_data

        with db.backend.conn:
            for field, values in field_id_notes.items():
                total_update_count += len(values)
                for item_id, note_data in values.items():
                    db.set_notes_for(
                        field, item_id,
                        note_data['doc'],
                        searchable_text=note_data['searchable_text'],
                        resource_hashes=note_data['resource_hashes'],
                    )

        msg = ('\nChecked %d notes, normalize %d in %d fields') % \
                    (total_count, total_update_count, len(field_id_notes))
        self.gui.status_bar.showMessage(msg)
        if len(field_id_notes) == 0:
            self.gui.status_bar.showMessage(_('All category notes are normalize'))
            return
