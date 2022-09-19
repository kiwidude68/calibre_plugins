#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~

__license__ = 'GPL v3'
__copyright__ = '2020, Ahmed Zaki <azaki00.dev@gmail.com>'

try:
    from qt.core import QDialog
except ImportError:
    from PyQt5.Qt import QDialog

from calibre import prints
from calibre.constants import DEBUG
from calibre.ebooks.metadata.book.base import Metadata
from calibre.ebooks.metadata.book.formatter import SafeFormat
from calibre.gui2 import error_dialog
from calibre.gui2.dialogs.template_dialog import TemplateDialog
from calibre.utils.formatter_functions import formatter_functions

from calibre_plugins.find_duplicates.advanced.common import TEMPLATE_ERROR

try:
    load_translations()
except NameError:
    pass

def dummy_metadata(db):
    fm = db.new_api.field_metadata
    mi = Metadata(_('Title'), [_('Author')])
    mi.author_sort = _('Author Sort')
    mi.series = ngettext('Series', 'Series', 1)
    mi.series_index = 3
    mi.rating = 4.0
    mi.tags = [_('Tag 1'), _('Tag 2')]
    mi.languages = ['eng']
    mi.id = 1
    mi.set_all_user_metadata(fm.custom_field_metadata())
    for col in mi.get_all_user_metadata(False):
        mi.set(col, (col,), 0)
    return mi

def get_metadata_object(gui):
    db = gui.current_db
    try:
        current_row = gui.library_view.currentIndex()
        book_id = gui.library_view.model().id(current_row)
        mi = db.new_api.get_proxy_metadata(book_id)
    except Exception as e:
        if DEBUG:
            prints('Find Duplicates: get_metadata_object: exception trying to get mi from current row')
        try:
            book_id = list(db.all_ids())[0]
            mi = db.new_api.get_proxy_metadata(book_id)
        except:
            mi = dummy_metadata(db)
    return mi

def check_template(template, gui, target_db=None, print_error=True, template_functions=None):
    if template_functions == None:
        template_functions = formatter_functions().get_functions()
    error_msgs = [
        TEMPLATE_ERROR,
        'unknown function',
        'unknown identifier',
        'unknown field',
        'assign requires the first parameter be an id',
        'missing closing parenthesis',
        'incorrect number of arguments for function',
        'expression is not function or constant'
    ]
    gui = gui
    db = gui.current_db
    all_errors = ''
    book_id = list(db.all_ids())[0]
    mi = db.new_api.get_proxy_metadata(book_id)
    if not (template.startswith('{') or template.startswith('program:')):
        if print_error:
            all_errors += 'Template must start with { or program:'
            error_dialog(
            gui,
            _('Template Error'),
            _('Templates must be either enclosed within curly brackets, or starts with: "program:"'),
            show=True
        )
        return _('Template Error'), all_errors
    output = SafeFormat().safe_format(template, mi, TEMPLATE_ERROR, mi, template_functions=template_functions)
    for msg in error_msgs:
        if output.lower().find(msg.lower()) != -1:
            all_errors += output + '\n'
            if print_error:
                error_dialog(
                gui,
                _('Template Error'),
                _('Running the template returned an error:\n{}').format(output.lstrip(TEMPLATE_ERROR)),
                show=True
            )
            return _('Template Error'), all_errors
    if target_db:
        book_id = list(target_db.all_ids())[0]
        mi = db.new_api.get_proxy_metadata(book_id)
        output = SafeFormat().safe_format(template, mi, TEMPLATE_ERROR, mi, template_functions=template_functions)
        for msg in error_msgs:
            if output.lower().find(msg.lower()) != -1:
                all_errors += output + '\n'
                if print_error:
                    error_dialog(
                        gui,
                        _('Target Library Template Error'),
                        _('Running the template in target library returned an error:\n{}').format(output.lstrip(TEMPLATE_ERROR)),
                        show=True
                    )
                return _('Template Error'), all_errors
    return True

class TemplateBox(TemplateDialog):
    def __init__(
        self,
        parent,
        gui,
        template_text='',
        placeholder_text=_('Enter a template to test using data from the selected book'),
        mi=None,
        all_functions=None,
        global_vars={},
        show_buttonbox=True,
        dialog_is_st_editor=False,
        target_db = None
    ):
        self.gui = gui
        self.db = self.gui.current_db
        self.target_db = target_db

        self.all_functions = all_functions
        if not self.all_functions:        
            self.all_functions = formatter_functions().get_functions()

        builtin_functions = formatter_functions().get_builtins()
        
        if not mi:
            mi = get_metadata_object(self.gui)

        if not template_text:
            text = placeholder_text
            text_is_placeholder = True
            window_title = _('Add template')
        else:
            text = None
            text_is_placeholder = False
            window_title = _('Edit Template')

        TemplateDialog.__init__(self,
                                parent,
                                text,
                                mi=mi,
                                text_is_placeholder=text_is_placeholder,
                                all_functions=self.all_functions,
                                builtin_functions=builtin_functions,
                                global_vars=global_vars)

        try:
            self.setup_saved_template_editor(show_buttonbox=show_buttonbox,
                                         show_doc_and_name=dialog_is_st_editor)
        except:
            # For earlier versions of calibre where the above call not yet implemented
            pass

        self.setWindowTitle(window_title)
        if template_text:
            self.textbox.insertPlainText(template_text)

    def accept(self):        
        self.template = str(self.textbox.toPlainText()).rstrip()
        chk = check_template(self.template, self.gui, self.target_db, template_functions=self.all_functions)
        if chk is True:
            # accept and save_geometry
            TemplateDialog.accept(self)

    def reject(self):
        # TemplateDialog.reject() closes parent dialog. So we have to override it.
        QDialog.reject(self)
