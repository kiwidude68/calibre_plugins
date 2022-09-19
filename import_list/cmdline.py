from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2020, Ahmed Zaki <azaki00.dev@gmail.com>'

# Call the import list plugin from the command line using calibre-debug -e $0

import os
import types

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (QApplication, QWidget, QHBoxLayout, QVBoxLayout,
                        QGroupBox, QToolButton, QComboBox, QDialog, QGroupBox,
                        QCheckBox, QSpinBox, QDialogButtonBox)
except ImportError:
    from PyQt5.Qt import (QApplication, QWidget, QHBoxLayout, QVBoxLayout,
                        QGroupBox, QToolButton, QComboBox, QDialog, QGroupBox,
                        QCheckBox, QSpinBox, QDialogButtonBox)

from calibre import prints
from calibre.constants import DEBUG
from calibre.gui2 import error_dialog, choose_dir, choose_files
from calibre.library import db
from calibre_plugins.import_list.action import ImportListAction
try:
    from calibre_plugins.reading_list.action import ReadingListAction
except:
    ReadingListAction = None

from calibre_plugins.import_list.common_compatibility import qSizePolicy_Preferred, qSizePolicy_Maximum
from calibre_plugins.import_list.common_icons import get_icon
from calibre_plugins.import_list.wizards import ImportListWizard


#========================================================
# method will be added to the the persist_page instance
#========================================================

def reinitialize_db(self, idx, add_empty_books, metadata_update_books, pbar):
    if idx % self.reinitialize_step != 0:
        return
    prints('DEBUG: re-intializeing db at idx: {}'.format(idx))
    self.db.commit()
    # if you close you have to update db in wizard instance
    self.db.close()
    w = self.wizard()
    self.db = w.db = w.gui.current_db = None
    self.db = w.db = w.gui.current_db = db(w.library_path)

#===========================================

def exists_at(path):
    return path and os.path.exists(os.path.join(path, 'metadata.db'))

def arg_parser(args):

    import argparse, os

    def is_valid_calibre_library(library):
        if not library:
            raise argparse.ArgumentTypeError('({}) is not a valid calibre library'.format(library))
        exists = exists_at(library)
        if not exists:
            raise argparse.ArgumentTypeError('({}) is not a valid calibre library'.format(library))
        return library

    def is_valid_db(db_path):
        if os.path.exists(db_path):
            if db_path.endswith('metadata.db'):
                return db_path
        raise argparse.ArgumentTypeError('({}) is not a valid calibre database'.format(db_path))

    parser = argparse.ArgumentParser(
        description="Run calibre's import list from the command line"
    )

    parser.add_argument(
        "library",
        type=is_valid_calibre_library,
        help="path to a valid calibre library"
    )
    parser.add_argument(
        "--override-db",
        dest="override_db",
        type=is_valid_db,
        default=None,
        help="Override the path to the database metadata.db file"
    )

    parser.add_argument(
        "--reinitialize-step",
        dest="reinitialize_step",
        default=0,
        type=int,
        help="Set number of books imported after which db must be re-initialized \
              to prevent drop in performance when importing large numberof books. default is zero"
    )
    
    args = parser.parse_args(args)
    
    return args.library, args.override_db, args.reinitialize_step


class LibraryOpenCombo(QGroupBox):

    def __init__(self, text='', choose_function=choose_dir, file_list=[], max_files=10):
        QGroupBox.__init__(self, text)
        self.current_loc = None
        self.file_list = file_list
        self.max_files = max_files
        self.choose_function = choose_function
        l = QHBoxLayout()
        self.setLayout(l)
        self.file_combo = QComboBox()
        self.file_combo.setMaxCount(max_files)

        self.browse_button = QToolButton(self)
        self.browse_button.setIcon(get_icon('document_open.png'))
        self.browse_button.clicked.connect(self._choose_location)
        
        l.addWidget(self.file_combo)
        l.addWidget(self.browse_button)
        
        self.setSizePolicy(qSizePolicy_Preferred, qSizePolicy_Maximum)

    def _choose_location(self, *args):
        loc = self.choose_function(self, 'choose duplicate library',
                _('Choose library location to compare against'))
        if loc:
            exists = exists_at(loc)
            if not exists:
                return error_dialog(self, _('No existing library found'),
                        _('There is no existing calibre library at {0}').format(loc),
                        show=True)

            idx = self.file_combo.findText(loc)
            if idx != -1:
                self.file_combo.removeItem(idx)
            self.file_combo.insertItem(0, loc)
            self.file_combo.setCurrentIndex(0)
            self.file_list = [ self.file_combo.itemText(x) for x in range(self.file_combo.count()) ]

    def text(self):
        return self.file_combo.currentText()

class DatabaseOpenCombo(LibraryOpenCombo):
    def _choose_location(self, *args):
        path_list = self.choose_function(self, 'import_database', _('Choose database'), filters=[
            (_('Calibre db'), ['db'])], all_files=False, select_only_single_file=True)
        if not path_list: return
        loc = path_list[0]
        if not loc.endswith('metadata.db'):
            return error_dialog(self, _('Not a valid database file'),
                    _('File ({}) is not a valid database file').format(loc),
                    show=True)
        idx = self.file_combo.findText(loc)
        if idx != -1:
            self.file_combo.removeItem(idx)
        self.file_combo.insertItem(0, loc)
        self.file_combo.setCurrentIndex(0)
        self.file_list = [ self.file_combo.itemText(x) for x in range(self.file_combo.count()) ]

class TagsView(object):

    '''dummy class to replace tag_views in cmdline mode'''
    
    def dummy(self, *args, **kwargs):
        pass

    blockSignals = recount = dummy

def run_import_wizard(library_path, db_path=None, reinitialize_step=None):
    gui = QWidget()
    gui.tags_view = TagsView()
    if db_path:
        os.environ['CALIBRE_OVERRIDE_DATABASE_PATH'] = db_path
    gui.current_db = db(library_path)
    import_list_action = ImportListAction(gui, None)
    if ReadingListAction:
        reading_list_action = ReadingListAction(gui, None)
    else:
        reading_list_action = None

    w = ImportListWizard(import_list_action, reading_list_action, is_modal=True)
    if reinitialize_step:
        w.persist_page.reinitialize_step = reinitialize_step
        # add the following methods that will be needed in cmdline mode
        w.persist_page.reinitialize_db = types.MethodType(reinitialize_db, w.persist_page)
        # insert library_path to used in re-initializing the db for performace
        w.library_path = library_path
    w.exec_()
    return w.result()

class ImportListOptionsDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setup_ui()

    def setup_ui(self):
        l = QVBoxLayout()
        self.setLayout(l)
        
        lgb = QGroupBox(_('Choose Library'))
        lgb_l = QVBoxLayout()
        lgb.setLayout(lgb_l)
        l.addWidget(lgb)
        library_open = self.library_open = LibraryOpenCombo(_('Choose library'))
        lgb_l.addWidget(library_open)

        ogb = QGroupBox(_('Options'))
        ogb_l = QVBoxLayout()
        ogb.setLayout(ogb_l)
        l.addWidget(ogb)

        db_l = QVBoxLayout()
        ogb_l.addLayout(db_l)
        db_override_chk = self.db_override_chk = QCheckBox(_('Override Database Path'))
        db_override_chk.setChecked(False)
        db_override_chk.stateChanged.connect(self._on_db_override_chk)
        db_override_chk.setToolTip(_('Allows you to specify the full path to metadata.db. '
                             'Using this variable you can have metadata.db be in a '
                             'location other than the library folder.'))
        db_l.addWidget(db_override_chk)
        db_open = self.db_open = DatabaseOpenCombo(_('Choose database path'), choose_function=choose_files)
        db_l.addWidget(db_open)

        r_l = QHBoxLayout()
        ogb_l.addLayout(r_l)
        r_chk = self.r_chk = QCheckBox(_('Re-initialize db every nth book (Experimental):'))
        r_chk.setChecked(False)
        r_chk.setToolTip(_('Prevent gradual speed deterioration when importing large number of books'))
        r_chk.stateChanged.connect(self._on_reinitialize_chk)
        r_spin = self.r_spin = QSpinBox(self)
        r_spin.setMinimum(1000)
        r_spin.setMaximum(100000)
        r_spin.setSingleStep(100)
        r_spin.setValue(2000)
        r_l.addWidget(r_chk)
        r_l.addWidget(r_spin)
        
        self._on_reinitialize_chk()
        self._on_db_override_chk()

        self.bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.bb.accepted.connect(self.accept)
        self.bb.rejected.connect(self.reject)

        l.addWidget(self.bb)

    def _on_reinitialize_chk(self):
        self.r_spin.setEnabled(self.r_chk.isChecked())

    def _on_db_override_chk(self):
        self.db_open.setEnabled(self.db_override_chk.isChecked())

    def accept(self):
        library_path = self.library_open.text()
        if not library_path:
            return error_dialog(self, _('Error'), _('You must choose a library'), show=True)
        self.library_path = os.path.abspath(library_path)
        self.reinitialize_step = None
        if self.r_chk.isChecked():
            self.reinitialize_step = self.r_spin.value()
        self.db_path = self.db_open.text()
        if self.db_path:
            self.db_path = os.path.abspath(self.db_path)
        QDialog.accept(self)

if __name__ == '__main__':
    _app = QApplication([])
    import sys
    args = sys.argv
    args.remove("Import List")
    if args:
        library, override_db, reinitialize_step = arg_parser(args)
        res = run_import_wizard(library, override_db, reinitialize_step)
    else:
        d =  ImportListOptionsDialog()
        if d.exec_() == d.Accepted:
            res = run_import_wizard(d.library_path, d.db_path, d.reinitialize_step)

    # change dialog results to suit shell exit codes        
    if res == QDialog.Rejected:
        res = 1
    elif res == QDialog.Accepted:
        res = 0
    sys.exit(res)
