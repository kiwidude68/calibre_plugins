from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import six

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from collections import OrderedDict
from calibre.gui2 import error_dialog
from calibre.gui2.actions import InterfaceAction
from calibre.utils.icu import sort_key

from calibre_plugins.manage_series.book import SeriesBook
from calibre_plugins.manage_series.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.manage_series.dialogs import SeriesDialog

PLUGIN_ICONS = ['images/manage_series.png', 'images/lock.png', 'images/lock32.png',
                'images/lock_delete.png', 'images/lock_open.png', 'images/sort.png',
                'images/ms_ff.png', 'images/ms_goodreads.png',
                'images/ms_google.png', 'images/ms_wikipedia.png']

class ManageSeriesAction(InterfaceAction):

    name = 'Manage Series'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (_('Manage Series'), None, None, ())
    action_type = 'current'
    dont_add_to = frozenset(['context-menu-device'])

    def genesis(self):
        self.is_library_selected = True
        # Read the plugin icons and store for potential sharing with the config widget
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)

        # Assign our menu to this action and an icon
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.qaction.triggered.connect(self.manage_series)

    def location_selected(self, loc):
        self.is_library_selected = loc == 'library'

    def manage_series(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0 or not self.is_library_selected:
            return error_dialog(self.gui, _('Cannot manage series'),
                             _('No books selected'), show=True)
        series_columns = self.get_series_columns()
        books = self.get_selected_books(rows, series_columns)
        db = self.gui.library_view.model().db
        all_series = db.all_series()
        all_series.sort(key=lambda x : sort_key(x[1]))

        d = SeriesDialog(self.gui, books, all_series, series_columns)
        d.exec_()
        if d.result() != d.Accepted:
            return

        updated_ids = []
        # Prevent the TagView from updating due to signals from the database
        self.gui.tags_view.blockSignals(True)
        num_added = 0
        try:
            for book in books:
                calibre_id = book.id()
                if calibre_id is None:
                    db.import_book(book.get_mi_to_persist(), [])
                    num_added += 1
                elif book.is_series_changed() or book.is_title_changed() or book.is_pubdate_changed():
                    updated_ids.append(calibre_id)
                    db.set_metadata(calibre_id, book.get_mi_to_persist(), commit=False)
            db.commit()
        finally:
            self.gui.tags_view.blockSignals(False)
        if num_added > 0:
            self.gui.library_view.model().books_added(num_added)
            if hasattr(self.gui, 'db_images'):
                self.gui.db_images.reset()
        self.gui.library_view.model().refresh_ids(updated_ids)
        self.gui.tags_view.recount()

    def get_series_columns(self):
        custom_columns = self.gui.library_view.model().custom_columns
        series_columns = OrderedDict()
        for key, column in six.iteritems(custom_columns):
            typ = column['datatype']
            if typ == 'series':
                series_columns[key] = column
        return series_columns

    def get_selected_books(self, rows, series_columns):
        db = self.gui.library_view.model().db
        idxs = [row.row() for row in rows]
        books = []
        for idx in idxs:
            mi = db.get_metadata(idx)
            book = SeriesBook(mi, series_columns)
            books.append(book)
        # Sort books by the current series
        books = sorted(books, key=lambda k: k.sort_key())
        return books
