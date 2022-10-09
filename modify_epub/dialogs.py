from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import six
import os, traceback
try:
    from qt.core import (QVBoxLayout, QLabel, QCheckBox, QGridLayout,
                      QGroupBox, Qt, QDialogButtonBox, QWidget,
                      QProgressDialog, QTimer, QScrollArea)
except ImportError:
    from PyQt5.Qt import (QVBoxLayout, QLabel, QCheckBox, QGridLayout,
                      QGroupBox, Qt, QDialogButtonBox, QWidget,
                      QProgressDialog, QTimer, QScrollArea)

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

# QWidget and QScrollArea added to support scrolling dialog box

from calibre.ebooks.metadata import authors_to_string
from calibre.gui2 import gprefs, warning_dialog, error_dialog
from calibre.gui2.convert.metadata import create_opf_file, create_cover_file
from calibre.ptempfile import remove_dir
from calibre.utils.config_base import tweaks

import calibre_plugins.modify_epub.config as cfg
from calibre_plugins.modify_epub.common_dialogs import SizePersistedDialog
from calibre_plugins.modify_epub.common_widgets import ImageTitleLayout


FILE_OPTIONS = [
            ('remove_itunes_files',       _('Remove iTunes files'),            _('Removes any iTunesMetadata.plist or artwork files\nadded by viewing the ePub in iTunes')),
            ('remove_calibre_bookmarks',  _('Remove calibre bookmark files'),  _('Remove any bookmark files added by the calibre ebook viewer')),
            ('remove_os_artifacts',       _('Remove OS artifact files'),       _('Removes any OS artifacts like thumbs.db or .DS_Store\nthat are not needed by the ePub')),
            ('remove_unused_images',      _('Remove unused image files'),      _('Remove any unused jpg, png or gif image files that are not referenced\nfrom the html pages. This can occur as the result of careless ePub editing.')),
            ('unpretty',                  _('De-indent (aka unpretty)'),       _('Remove indentation from HTML files')),
            ('strip_kobo',                _('Strip Kobo DRM remnants'),        _('Remove remnants of Kobo DRM')),
            ('strip_spans',               _('Strip spans'),                    _('Remove spans without attributes')),
            ]

MANIFEST_OPTIONS = [
            ('remove_missing_files',      _('Remove missing file entries from manifest'),  _('Remove entries in the manifest for files listed that do not exist in the ePub')),
            ('add_unmanifested_files',    _('Add unmanifested files to manifest'),         _('Add files to manifest that are in the ePub but do not exist in the .opf manifest\n(excluding iTunes/calibre bookmarks)')),
            ('remove_unmanifested_files', _('Remove unmanifested files from ePub'),        _('Remove files from the ePub that do not exist in the .opf manifest\n(excluding iTunes/calibre bookmarks). Will not be applied if the add option is also checked')),
            ]

ADOBE_OPTIONS = [
            ('zero_xpgt_margins',         _('Remove margins from Adobe .xpgt files'),      _('Remove any Adobe .xpgt file margins to prevent them\ninterfering with viewing')),
            ('remove_xpgt_files',         _('Remove Adobe .xpgt files and links'),         _('Delete the .xpgt file completely from the epub\nas well as removing any links from the xhtml files')),
            ('remove_drm_meta_tags',      _('Remove Adobe resource DRM meta tags'),        _('Remove any meta tags from the xhtml files that\ncontain DRM urn identifiers.')),
            ('remove_page_map',           _('Remove page maps'),							_('Removes all types of page map files')),
            ('remove_gp_page_map',		  _('Remove ONLY Google Play page maps'),			_('Removes only Google Play page map files')),
            ]

TOC_OPTIONS = [
            ('flatten_toc',               _('Flatten TOC hierarchy in NCX file'),          _('Restructure the NCX to contain no nesting of navPoint items.\nFor users whose devices do not support a hierarchical TOC.')),
            ('remove_broken_ncx_links',   _('Remove broken TOC entries in NCX file'),      _('Any NCX entries that point to missing html pages will be removed.\nOrphaned NCX links can happen as a result of a calibre conversion for covers.')),
            ]

JACKET_OPTIONS = [
            ('remove_all_jackets',        _('Remove all metadata jackets'),	    _('Remove all calibre jackets, both legacy and current')),
            ('remove_legacy_jackets',     _('Remove legacy metadata jackets'),  _('Remove jackets generated using versions of calibre prior to 0.6.50')),
            ('add_replace_jacket',        _('Add/replace metadata jacket'),	    _('Add a jacket if not existing, or replace a non-legacy jacket')),
            ('jacket_end_book',           _('Jacket at the end of the book'),	_('If a jacket is added/replaced, it is placed at the end of the book instead of the beginning'))
            ]

COVER_OPTIONS = [
            ('remove_broken_covers',      _('Remove broken image pages'),    _('Remove html page(s) that contain only an image tag for which\nthe linked image does not exist in the epub')),
            ('remove_cover',              _('Remove existing cover'),        _('If a cover page is identifiable in the epub then it is completely removed')),
            ('insert_replace_cover',      _('Insert or replace cover'),      _('If a cover page is identifiable in the epub then it is replaced\notherwise a new cover page is inserted')),
            ]

METADATA_OPTIONS = [
            ('update_metadata',           _('Update metadata'),                   _('Update the manifest with the latest calibre metadata\nand replace an existing identifiable cover if possible.')),
            ('remove_non_dc_elements',    _('Remove non dc: metadata elements'),  _('Remove any metadata from the .opf manifest that is not in the dc: namespace.\nSuch entries are created by editing in Sigil or calibre updating metadata.\nUse this option if publishing your ePubs externally.')),
            ]

STYLE_OPTIONS = [
            ('encode_html_utf8',          _('Encode HTML in UTF-8'),                 _('Removes any existing <meta> charset tags on html pages and encodes in UTF-8.\nFor use where ebook does not display quotes in calibre viewer correctly.')),
            ('remove_embedded_fonts',     _('Remove embedded fonts'),                _('Remove embedded fonts from the manifest and their files to reduce ePub size.\nAlso removes @font-face declarations.')),
            ('rewrite_css_margins',       _('Modify @page and body margin styles'),  _('Replace margin styles for @page or body with your calibre defaults in a new @page style.\nIf your calibre defaults are negative, removes the margin attributes and if necessary the CSS file.')),
            ('append_extra_css',          _('Append extra CSS'),                     _('Appends any Extra CSS you have defined in your calibre defaults to every .CSS file.\nIf you have no extra CSS defined or text already contained then it does nothing.')),
            ('smarten_punctuation',       _('Smarten punctuation'),                  _('Convert html to use smart quotes and emdash characters')),
            ('remove_javascript',         _('Remove inline javascript and files'),   _('Remove any .js files and inline javascript blocks')),
            ]

ALL_OPTIONS = FILE_OPTIONS + MANIFEST_OPTIONS + ADOBE_OPTIONS + TOC_OPTIONS + JACKET_OPTIONS + COVER_OPTIONS + METADATA_OPTIONS + STYLE_OPTIONS

class ModifyEpubDialog(SizePersistedDialog):
    '''
    Configure which options you want applied during the modify process
    '''
    def __init__(self, gui, plugin_action):
        self.plugin_action = plugin_action
        SizePersistedDialog.__init__(self, gui, 'modify epub plugin:options dialog')
        self.setWindowTitle(_('Modify ePub'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'images/modify_epub.png', _('Modify ePub Options'))
        layout.addLayout(title_layout)

        # Add hyperlink to a help file at the right. We will replace the correct name when it is clicked.
        help_label = QLabel('<a href="' + cfg.HELP_URL + '">Help</a>', self)
        help_label.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
        help_label.setAlignment(Qt.AlignRight)
        help_label.linkActivated.connect(cfg.show_help)
        title_layout.addWidget(help_label)

        # Make dialog scrollable for smaller screens
        scrollable = QScrollArea()
        scrollcontent = QWidget()
        scrollable.setWidget(scrollcontent)
        scrollable.setWidgetResizable(True)
        layout.addWidget(scrollable)

        layout = QVBoxLayout()
        scrollcontent.setLayout(layout)

        layout.addSpacing(5)
        self.main_layout = QGridLayout()
        layout.addLayout(self.main_layout, 1)
        options = gprefs.get(self.unique_pref_name+':settings', {})

        self._add_groupbox(0, 0, _('Known Artifacts'), FILE_OPTIONS, options)
        self._add_groupbox(1, 0, _('Manifest'), MANIFEST_OPTIONS, options)
        self._add_groupbox(2, 0, _('Adobe'), ADOBE_OPTIONS, options)
        self._add_groupbox(3, 0, _('Table of Contents'), TOC_OPTIONS, options)

        self._add_groupbox(0, 1, _('HTML && Styles'), STYLE_OPTIONS, options)
        self._add_groupbox(1, 1, _('Metadata Jackets'), JACKET_OPTIONS, options)
        self._add_groupbox(2, 1, _('Covers'), COVER_OPTIONS, options)
        self._add_groupbox(3, 1, _('Metadata'), METADATA_OPTIONS, options)

        layout.addSpacing(10)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._ok_clicked)
        button_box.rejected.connect(self.reject)
        self.select_none_button = button_box.addButton(' '+_('Clear all')+' ', QDialogButtonBox.ResetRole)
        self.select_none_button.setToolTip(_('Clear all selections'))
        self.select_none_button.clicked.connect(self._select_none_clicked)
        self.save_button = button_box.addButton(' '+_('Save')+' ', QDialogButtonBox.ResetRole)
        self.save_button.setToolTip(_('Save the current selected settings for future recall with the Restore button'))
        self.save_button.clicked.connect(self._save_clicked)
        self.restore_button = button_box.addButton(' '+_('Restore')+' ', QDialogButtonBox.ResetRole)
        self.restore_button.setToolTip(_('Restore your settings set when the Save button was last clicked'))
        self.restore_button.clicked.connect(self._restore_clicked)
        layout.addWidget(button_box)

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()

    def _add_groupbox(self, row, col, title, option_info, options):
        groupbox = QGroupBox(title)
        self.main_layout.addWidget(groupbox, row, col, 1, 1)
        groupbox_layout = QVBoxLayout()
        groupbox.setLayout(groupbox_layout)

        for key, text, tooltip in option_info:
            checkbox = QCheckBox(text, self)
            checkbox.setToolTip(tooltip)
            checkbox.setCheckState(Qt.Checked if options.get(key, False) else Qt.Unchecked)
            setattr(self, key, checkbox)
            groupbox_layout.addWidget(checkbox)
        groupbox_layout.addStretch(-5)

    def _ok_clicked(self):
        self._set_options()
        gprefs.set(self.unique_pref_name+':settings', self.options)

        # Only if the user has checked at least one option will we continue
        for key in self.options:
            if self.options[key]:
                self.accept()
                return
        return error_dialog(self, _('No options selected'),
                            _('You must select at least one option to continue'),
                            show=True, show_copy_button=False)

    def _set_options(self):
        self.options = {}
        for option_name, _t, _tt in ALL_OPTIONS:
            self.options[option_name] = getattr(self, option_name).checkState() == Qt.Checked

    def _select_none_clicked(self):
        for option_name, _t, _tt in ALL_OPTIONS:
            getattr(self, option_name).setCheckState(Qt.Unchecked)

    def _save_clicked(self):
        self._set_options()
        cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS] = [k for k,v in six.iteritems(self.options) if v]

    def _restore_clicked(self):
        self._select_none_clicked()
        for option_name in cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]:
            if hasattr(self, option_name):
                getattr(self, option_name).setCheckState(Qt.Checked)


class QueueProgressDialog(QProgressDialog):

    def __init__(self, gui, book_epubs, tdir, options, queue, db):
        QProgressDialog.__init__(self, _('Working')+'...', _('Cancel'), 0, len(book_epubs), gui)
        self.setWindowTitle(_('Queueing books for modifying ePubs'))
        self.setMinimumWidth(500)
        self.book_epubs, self.tdir, self.options, self.queue, self.db = \
            book_epubs, tdir, options, queue, db
        self.gui = gui
        self.i, self.bad, self.books_to_modify = 0, [], []
        # QTimer workaround on Win 10 on first go for Win10/Qt6 users not displaying dialog properly.
        QTimer.singleShot(100, self.do_book)
        self.exec_()

    def do_book(self):
        book_id = self.book_epubs[self.i]
        self.i += 1

        try:
            mi, opf_file = create_opf_file(self.db, book_id)
            self.setLabelText(_('Queueing')+' '+mi.title)
            cover_file = create_cover_file(self.db, book_id)
            cover_file_name = cover_file.name if cover_file else None
            authors = authors_to_string(self._authors_to_list(self.db, book_id))
            # Copy the book to the temp directory, using book id as filename
            epub_file = os.path.join(self.tdir, '%d.epub'%book_id)
            with open(epub_file, 'w+b') as f:
                self.db.copy_format_to(book_id, 'EPUB', f, index_is_id=True)
            self.books_to_modify.append((book_id, mi.title, authors, epub_file,
                                         opf_file.name, cover_file_name))
        except:
            traceback.print_exc()
            self.bad.append(book_id)

        self.setValue(self.i)
        if self.i >= len(self.book_epubs):
            return self.do_queue()
        else:
            QTimer.singleShot(0, self.do_book)

    def do_queue(self):
        if self.gui is None:
            # There is a nasty QT bug with the timers/logic above which can
            # result in the do_queue method being called twice
            return
        self.hide()
        if self.bad != []:
            res = []
            for book_id in self.bad:
                title = self.db.title(book_id, True)
                res.append('%s'%title)
            msg = '%s' % '\n'.join(res)
            warning_dialog(self.gui, _('Could not modify ePub for some books'),
                _('Could not modify %d of %d books, because no ePub '
                'source format was found.') % (len(res), len(self.book_epubs)),
                msg).exec_()
        self.gui = None
        self.db = None
        # Queue a job to process these ePub books
        self.queue(self.tdir, self.options, self.books_to_modify)

    def _authors_to_list(self, db, book_id):
        authors = db.authors(book_id, index_is_id=True)
        if authors:
            return [a.strip().replace('|',',') for a in authors.split(',')]
        return []


class AddBooksProgressDialog(QProgressDialog):

    def __init__(self, gui, modified_epubs, tdir):
        self.total_count = len(modified_epubs)
        QProgressDialog.__init__(self, _('Working')+'...', _('Cancel'), 0, self.total_count, gui)
        self.setWindowTitle(_('Adding %d modified ePubs')% self.total_count +'...' )
        self.setMinimumWidth(500)
        self.modified_epubs, self.tdir = modified_epubs, tdir
        self.book_ids = list(modified_epubs.keys())
        self.gui = gui
        self.db = self.gui.current_db
        self.i = 0
        # QTimer workaround on Win 10 on first go for Win10/Qt6 users not displaying dialog properly.
        QTimer.singleShot(100, self.do_book_check)
        self.exec_()
        if self.db:
            self.do_close()

    def do_book_check(self):
        if self.i >= self.total_count:
            return self.do_close()
        book_id = self.book_ids[self.i]
        epub_path = self.modified_epubs[book_id]
        self.i += 1

        title = self.db.title(book_id, index_is_id=True)
        self.setLabelText(_('Adding')+': '+title)

        formats = self.db.formats(book_id, index_is_id=True)
        if tweaks['save_original_format_when_polishing'] and 'ORIGINAL_EPUB' not in formats:
            self.db.save_original_format(book_id, 'EPUB', notify=False)
        # Add the epub back, causing the size information to be updated
        self.db.add_format(book_id, 'EPUB', open(epub_path, 'rb'), index_is_id=True)
        self.setValue(self.i)

        QTimer.singleShot(0, self.do_book_check)

    def do_close(self):
        self.hide()
        self.db.update_last_modified(self.book_ids)
        remove_dir(self.tdir)
        self.gui.status_bar.show_message(_('ePub files updated'), 3000)
        self.gui = None
        self.db = None
