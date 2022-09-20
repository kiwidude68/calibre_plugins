from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

try:
    from qt.core import QWizard, QApplication, QWidget
except ImportError:    
    from PyQt5.Qt import QWizard, QApplication, QWidget

try:
    qWizard_NoDefaultButton = QWizard.WizardOption.NoDefaultButton
    qWizard_HaveHelpButton = QWizard.WizardOption.HaveHelpButton
    qWizard_HelpButtonOnRight = QWizard.WizardOption.HelpButtonOnRight
except:
    qWizard_NoDefaultButton = QWizard.NoDefaultButton
    qWizard_HaveHelpButton = QWizard.HaveHelpButton
    qWizard_HelpButtonOnRight = QWizard.HelpButtonOnRight

from calibre.gui2 import gprefs

import calibre_plugins.import_list.config as cfg
from calibre_plugins.import_list.common_icons import get_icon
from calibre_plugins.import_list.page_import import ImportPage
from calibre_plugins.import_list.page_persist import PersistPage
from calibre_plugins.import_list.page_resolve import ResolvePage

try:
    load_translations()
except NameError:
    pass

class ImportListWizard(QWizard):

    def __init__(self, import_list_action, reading_list_action, is_modal=False):
        self.gui = import_list_action.gui
        QWizard.__init__(self, self.gui)
        self.unique_pref_name = 'import list plugin:import list wizard'
        self.setModal(is_modal)
        self.setWindowTitle(_('Import Book List'))
        self.setWindowIcon(get_icon('images/import_list.png'))
        self.setMinimumSize(600, 0)
        self.setOption(qWizard_NoDefaultButton, True)
        self.setOption(qWizard_HaveHelpButton, True)
        self.setOption(qWizard_HelpButtonOnRight, False)
        self.setButtonText(QWizard.HelpButton, _('&Options')+'...')
        self.helpRequested.connect(self._show_options)

        self.is_closed = False
        self.import_list_action = import_list_action
        self.db = import_list_action.gui.current_db
        self.reading_list_action = reading_list_action
        self.info = { 'books': [], 'book_columns':[], 'reading_list': '', 
                      'save_books': [], 'current_setting': '' }
        self.info['state'] = gprefs.get(self.unique_pref_name+':state', {})
        self.library_config = cfg.get_library_config(self.db)

        self.addPages()

        geom = gprefs.get(self.unique_pref_name, None)
        if geom is None:
            self.resize(self.sizeHint())
        else:
            self.restoreGeometry(geom)
        self.finished.connect(self._on_dialog_closing)

    def addPages(self):
        for attr, cls in [
                ('import_page',  ImportPage),
                ('resolve_page', ResolvePage),
                ('persist_page', PersistPage)
                ]:
            setattr(self, attr, cls(self.gui, self))
            self.setPage(getattr(cls, 'ID'), getattr(self, attr))

    def _show_options(self):
        '''
        Display the standard customize plugin dialog.
        '''
        self.import_list_action.interface_action_base_plugin.do_user_config(self.import_list_action.gui)

    def _save_window_state(self):
        geom = bytearray(self.saveGeometry())
        gprefs[self.unique_pref_name] = geom

        state = {}
        state['import_splitter_state'] = bytearray(self.import_page.splitter.saveState())
        state['import_preview_columns'] = self.import_page.get_preview_columns()
        state['import_preview_column_widths'] = self.import_page.get_preview_table_column_widths()
        state['resolve_splitter_state'] = bytearray(self.resolve_page.splitter.saveState())
        state['resolve_search_column_widths'] = self.resolve_page.get_search_matches_table_column_widths()
        gprefs[self.unique_pref_name+':state'] = state

    def _get_marked_book_id_search(self):
        '''
        If the user wants to see the books in isolation on screen rather than on a reading
        list then this function will mark the book ids and return the search text
        '''
        book_ids = [book['!id'] for book in self.info['save_books']]
        marked_text = 'imported_list'
        marked_ids = dict()
        # Build our dictionary of list items in desired order
        for index, book_id in enumerate(book_ids):
            marked_ids[book_id] = '%s_%04d' %(marked_text, index)
        # Mark the results in our database
        self.db.set_marked_ids(marked_ids)
        return 'marked:'+marked_text

    def _on_dialog_closing(self, result):
        if self.is_closed:
            return
        self.is_closed = True
        # We will always save window position/save
        self._save_window_state()
        # Also persist our settings into the library, even though user cancelled
        cfg.set_library_config(self.db, self.library_config)

        if result > 0:
            list_name = self.info['reading_list']
            if list_name:
                try:
                    self.reading_list_action.view_list(list_name)
                except:
                    print('Should display reading list:', list_name)
            else:
                marked_text = self._get_marked_book_id_search()
                try:
                    self.gui.search.set_search_string(marked_text)
                    # Sort by our marked column to display the books in order
                    self.gui.library_view.sort_by_named_field('marked', True)
                except:
                    print('Should search:', marked_text)
        # Make sure no memory leaks (not that there should be anyway)
        self.db = self.gui = self.import_list_action = self.reading_list_action = None
        self.library_config = self.info = None


# Test Wizard {{{
# calibre-debug -e wizards.py
if __name__ == '__main__':
    def show_dialog():
        from calibre.library import db
        from calibre_plugins.import_list.action import ImportListAction
        from calibre_plugins.reading_list.action import ReadingListAction
        _app = QApplication([])
        gui = QWidget()
        gui.current_db = db()
        import_list_action = ImportListAction(gui, None)
        reading_list_action = ReadingListAction(gui, None)

        w = ImportListWizard(import_list_action, reading_list_action, is_modal=True)
        w.exec_()

    show_dialog()
# }}}
