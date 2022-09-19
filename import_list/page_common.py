from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import re

try:
    from qt.core import QWizardPage, QUrl
except ImportError:    
    from PyQt5.Qt import QWizardPage, QUrl

from calibre.gui2 import open_url
from calibre.utils.date import parse_date, UNDEFINED_DATE

AUTHOR_SEPARATOR = ' & '
TAGS_SEPARATOR = ', '

def parse_series(val):
    if val:
        pat = re.compile(r'\[([.0-9]+)\]')
        match = pat.search(val)
        if match is not None:
            s_index = float(match.group(1))
            val = pat.sub('', val).strip()
        else:
            s_index = 1.0
        return val, s_index
    return None, None

def parse_pubdate(date_text):
    if not date_text:
        return UNDEFINED_DATE
    return parse_date(date_text, assume_utc=True, as_utc=False, default=UNDEFINED_DATE)

class WizardPage(QWizardPage):

    def __init__(self, gui, parent):
        QWizardPage.__init__(self, parent)
        self.gui = gui
        self.db = gui.current_db
        self.info = parent.info
        self.library_config = parent.library_config
        self.reading_list_action = parent.reading_list_action
        self.init_controls()

    def init_controls(self):
        pass

    def open_external_link(self, url):
        open_url(QUrl(url))

