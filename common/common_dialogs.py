#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2022, Grant Drake'

# calibre Python 3 compatibility.
import six
from six import text_type as unicode

try:
    from qt.core import (QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, 
                        QListWidget, QProgressBar, QAbstractItemView, QTextEdit, 
                        QIcon, QApplication, Qt, QTextBrowser, QSize, QLabel)
except ImportError:
    from PyQt5.Qt import (QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, 
                        QListWidget, QProgressBar, QAbstractItemView, QTextEdit, 
                        QIcon, QApplication, Qt, QTextBrowser, QSize, QLabel)

try:
    load_translations()
except NameError:
    pass # load_translations() 

from calibre.gui2 import gprefs, info_dialog, Application
from calibre.gui2.keyboard import ShortcutConfig
from common_icons import get_icon


# ----------------------------------------------
#               Dialog functions
# ----------------------------------------------

class SizePersistedDialog(QDialog):
    '''
    This dialog is a base class for any dialogs that want their size/position
    restored when they are next opened.
    '''
    def __init__(self, parent, unique_pref_name):
        QDialog.__init__(self, parent)
        self.unique_pref_name = unique_pref_name
        self.geom = gprefs.get(unique_pref_name, None)
        self.finished.connect(self.dialog_closing)

    def resize_dialog(self):
        if self.geom is None:
            self.resize(self.sizeHint())
        else:
            self.restoreGeometry(self.geom)

    def dialog_closing(self, result):
        geom = bytearray(self.saveGeometry())
        gprefs[self.unique_pref_name] = geom
        self.persist_custom_prefs()

    def persist_custom_prefs(self):
        '''
        Invoked when the dialog is closing. Override this function to call
        save_custom_pref() if you have a setting you want persisted that you can
        retrieve in your __init__() using load_custom_pref() when next opened
        '''
        pass

    def load_custom_pref(self, name, default=None):
        return gprefs.get(self.unique_pref_name+':'+name, default)

    def save_custom_pref(self, name, value):
        gprefs[self.unique_pref_name+':'+name] = value

    def help_link_activated(self, url):
        if self.plugin_action is not None:
            self.plugin_action.show_help(anchor=self.help_anchor)


class KeyboardConfigDialog(SizePersistedDialog):
    '''
    This dialog is used to allow editing of keyboard shortcuts.
    '''
    def __init__(self, gui, group_name):
        SizePersistedDialog.__init__(self, gui, 'Keyboard shortcut dialog')
        self.gui = gui
        self.setWindowTitle(_('Keyboard shortcuts'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.keyboard_widget = ShortcutConfig(self)
        layout.addWidget(self.keyboard_widget)
        self.group_name = group_name

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.commit)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Cause our dialog size to be restored from prefs or created on first usage
        self.resize_dialog()
        self.initialize()

    def initialize(self):
        self.keyboard_widget.initialize(self.gui.keyboard)
        self.keyboard_widget.highlight_group(self.group_name)

    def commit(self):
        self.keyboard_widget.commit()
        self.accept()


def prompt_for_restart(parent, title, message):
    d = info_dialog(parent, title, message, show_copy_button=False)
    b = d.bb.addButton(_('Restart calibre now'), d.bb.AcceptRole)
    b.setIcon(QIcon(I('lt.png')))
    d.do_restart = False
    def rf():
        d.do_restart = True
    b.clicked.connect(rf)
    d.set_details('')
    d.exec_()
    b.clicked.disconnect()
    return d.do_restart


class PrefsViewerDialog(SizePersistedDialog):

    def __init__(self, gui, namespace):
        SizePersistedDialog.__init__(self, gui, 'Prefs Viewer dialog')
        self.setWindowTitle(_('Preferences for:')+' '+namespace)
        
        self.gui = gui
        self.db = gui.current_db
        self.namespace = namespace
        self._init_controls()
        self.resize_dialog()

        self._populate_settings()

        if self.keys_list.count():
            self.keys_list.setCurrentRow(0)

    def _init_controls(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        ml = QHBoxLayout()
        layout.addLayout(ml, 1)

        self.keys_list = QListWidget(self)
        self.keys_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.keys_list.setFixedWidth(150)
        self.keys_list.setAlternatingRowColors(True)
        ml.addWidget(self.keys_list)
        self.value_text = QTextEdit(self)
        self.value_text.setReadOnly(False)
        ml.addWidget(self.value_text, 1)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._apply_changes)
        button_box.rejected.connect(self.reject)
        self.clear_button = button_box.addButton(_('Clear'), QDialogButtonBox.ResetRole)
        self.clear_button.setIcon(get_icon('trash.png'))
        self.clear_button.setToolTip(_('Clear all settings for this plugin'))
        self.clear_button.clicked.connect(self._clear_settings)
        layout.addWidget(button_box)

    def _populate_settings(self):
        self.keys_list.clear()
        ns_prefix = self._get_ns_prefix()
        keys = sorted([k[len(ns_prefix):] for k in six.iterkeys(self.db.prefs)
                       if k.startswith(ns_prefix)])
        for key in keys:
            self.keys_list.addItem(key)
        self.keys_list.setMinimumWidth(self.keys_list.sizeHintForColumn(0))
        self.keys_list.currentRowChanged[int].connect(self._current_row_changed)

    def _current_row_changed(self, new_row):
        if new_row < 0:
            self.value_text.clear()
            return
        key = unicode(self.keys_list.currentItem().text())
        val = self.db.prefs.get_namespaced(self.namespace, key, '')
        self.value_text.setPlainText(self.db.prefs.to_raw(val))

    def _get_ns_prefix(self):
        return 'namespaced:%s:'% self.namespace

    def _apply_changes(self):
        from calibre.gui2.dialogs.confirm_delete import confirm
        message = '<p>'+_('Are you sure you want to change your settings in this library for this plugin?')+'</p>' \
                  '<p>'+_('Any settings in other libraries or stored in a JSON file in your calibre plugins ' \
                  'folder will not be touched.')+'</p>' \
                  '<>'+_('You must restart calibre afterwards.')+'</p>'
        if not confirm(message, self.namespace+'_clear_settings', self):
            return

        val = self.db.prefs.raw_to_object(unicode(self.value_text.toPlainText()))
        key = unicode(self.keys_list.currentItem().text())
        self.db.prefs.set_namespaced(self.namespace, key, val)

        restart = prompt_for_restart(self, _('Settings changed'),
                           '<p>'+_('Settings for this plugin in this library have been changed.')+'</p>' \
                           '<p>'+_('Please restart calibre now.')+'</p>')
        self.close()
        if restart:
            self.gui.quit(restart=True)

    def _clear_settings(self):
        from calibre.gui2.dialogs.confirm_delete import confirm
        message = '<p>'+_('Are you sure you want to clear your settings in this library for this plugin?')+'</p>' \
                  '<p>'+_('Any settings in other libraries or stored in a JSON file in your calibre plugins ' \
                  'folder will not be touched.')+'</p>' \
                  '<p>'+_('You must restart calibre afterwards.')+'</p>'
        if not confirm(message, self.namespace+'_clear_settings', self):
            return

        ns_prefix = self._get_ns_prefix()
        keys = [k for k in six.iterkeys(self.db.prefs) if k.startswith(ns_prefix)]
        for k in keys:
            del self.db.prefs[k]
        self._populate_settings()
        restart = prompt_for_restart(self, _('Settings deleted'),
                           '<p>'+_('All settings for this plugin in this library have been cleared.')+'</p>'
                           '<p>'+_('Please restart calibre now.')+'</p>')
        self.close()
        if restart:
            self.gui.quit(restart=True)



class ProgressBarDialog(QDialog):
    def __init__(self, parent=None, max_items=100, window_title='Progress Bar',
                 label='Label goes here', on_top=False):
        if on_top:
            super(ProgressBarDialog, self).__init__(parent=parent, flags=Qt.WindowStaysOnTopHint)
        else:
            super(ProgressBarDialog, self).__init__(parent=parent)
        self.application = Application
        self.setWindowTitle(window_title)
        self.l = QVBoxLayout(self)
        self.setLayout(self.l)

        self.label = QLabel(label)
#         self.label.setAlignment(Qt.AlignHCenter)
        self.l.addWidget(self.label)

        self.progressBar = QProgressBar(self)
        self.progressBar.setRange(0, max_items)
        self.progressBar.setValue(0)
        self.l.addWidget(self.progressBar)

    def increment(self):
        self.progressBar.setValue(self.progressBar.value() + 1)
        self.refresh()

    def refresh(self):
        self.application.processEvents()

    def set_label(self, value):
        self.label.setText(value)
        self.refresh()

    def left_align_label(self):
        self.label.setAlignment(Qt.AlignLeft )

    def set_maximum(self, value):
        self.progressBar.setMaximum(value)
        self.refresh()

    def set_value(self, value):
        self.progressBar.setValue(value)
        self.refresh()

    def set_progress_format(self, progress_format=None):
        pass


class ViewLogDialog(QDialog):

    def __init__(self, title, html, parent=None):
        QDialog.__init__(self, parent)
        self.l = l = QVBoxLayout()
        self.setLayout(l)

        self.tb = QTextBrowser(self)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        # Rather than formatting the text in <pre> blocks like the calibre
        # ViewLog does, instead just format it inside divs to keep style formatting
        html = html.replace('\t','&nbsp;&nbsp;&nbsp;&nbsp;').replace('\n', '<br/>')
        html = html.replace('> ','>&nbsp;')
        self.tb.setHtml('<div>%s</div>' % html)
        QApplication.restoreOverrideCursor()
        l.addWidget(self.tb)

        self.bb = QDialogButtonBox(QDialogButtonBox.Ok)
        self.bb.accepted.connect(self.accept)
        self.bb.rejected.connect(self.reject)
        self.copy_button = self.bb.addButton(_('Copy to clipboard'),
                self.bb.ActionRole)
        self.copy_button.setIcon(QIcon(I('edit-copy.png')))
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        l.addWidget(self.bb)
        self.setModal(False)
        self.resize(QSize(700, 500))
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(I('debug.png')))
        self.show()

    def copy_to_clipboard(self):
        txt = self.tb.toPlainText()
        QApplication.clipboard().setText(txt)
