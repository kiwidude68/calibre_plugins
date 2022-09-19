from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.gui2 import error_dialog

from calibre_plugins.quality_check.check_base import BaseCheck

class MissingDataCheck(BaseCheck):
    '''
    All checks related to executing searches for blank data in calibre.
    '''
    def perform_check(self, menu_key):
        if menu_key == 'check_missing_title':
            self.gui.search.set_search_string('title:"=Unknown"')
        elif menu_key == 'check_missing_author':
            self.gui.search.set_search_string('authors:"=Unknown"')
        elif menu_key == 'check_missing_isbn':
            self.gui.search.set_search_string('isbn:False')
        elif menu_key == 'check_missing_pubdate':
            self.gui.search.set_search_string('pubdate:False')
        elif menu_key == 'check_missing_publisher':
            self.gui.search.set_search_string('publisher:False')
        elif menu_key == 'check_missing_tags':
            self.gui.search.set_search_string('tags:False')
        elif menu_key == 'check_missing_rating':
            self.gui.search.set_search_string('rating:False')
        elif menu_key == 'check_missing_comments':
            self.gui.search.set_search_string('comments:False')
        elif menu_key == 'check_missing_languages':
            self.gui.search.set_search_string('languages:False')
        elif menu_key == 'check_missing_cover':
            self.gui.search.set_search_string('cover:False')
        elif menu_key == 'check_missing_formats':
            self.gui.search.set_search_string('formats:False')
        else:
            return error_dialog(self.gui, _('Quality Check failed'),
                                _('Unknown menu key for %s of \'%s\'')%('MissingDataCheck', menu_key),
                                show=True, show_copy_button=False)


