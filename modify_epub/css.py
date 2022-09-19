from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import six
import re

from calibre.constants import iswindows
from calibre.ebooks.oeb.base import XPath

RE_BOOK_MGNS = re.compile(r'(?P<cssid>#\w+\s+)?(?P<selector>(?<!\.)\bbody|@page)\b\s*{(?P<styles>[^}]*margin[^}]+);?\s*\}', re.UNICODE)
CSS_MIME_TYPES = ['text/css']
HTML_MIME_TYPES = ['application/xhtml+xml']
EOLF = '\r\n' if iswindows else '\r'

class CSSUpdater(object):

    def __init__(self, log, container):
        self.log = log
        self.container = container

    def _get_user_extra_css(self):
        from calibre.ebooks.conversion.config import load_defaults
        ps = load_defaults('look_and_feel')
        # Only interested in the extra_css out of settings
        prefs_css = dict((k,v) for k,v in six.iteritems(ps) if k == 'extra_css')
        return prefs_css.get('extra_css', '')

    def rewrite_css(self):
        dirtied = False

        # check user margin prefs
        extra_css = self._get_user_extra_css()
        if not extra_css:
            return False

        for name in self.container.name_path_map:
            mt = self.container.mime_map.get(name, '')
            data = self.container.get_raw(name)

            extension = name[name.lower().rfind("."):].lower()

            if mt.lower() in CSS_MIME_TYPES:
                css_dirtied = False
                # Have we already put this extra css into this file on a previous run?
                if extra_css not in data:
                    data = data + EOLF + extra_css
                    self.log('\t  Modified CSS margins in:', name)
                    self.container.set(name, data)
                    dirtied = True
                else:
                    self.log('\t  Skipping as file contains extra CSS already:', name)

        return dirtied

