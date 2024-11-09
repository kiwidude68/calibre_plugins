from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

import os
from PIL import Image
from calibre.gui2 import error_dialog

from calibre_plugins.quality_check.check_base import BaseCheck
from calibre_plugins.quality_check.dialogs import CoverOptionsDialog, ResultsSummaryDialog


class CoverCheck(BaseCheck):
    '''
    All checks related to working with covers.
    '''
    def perform_check(self, menu_key):
        if menu_key == 'check_covers':
            self.check_covers()
        else:
            return error_dialog(self.gui, _('Quality Check failed'),
                                _('Unknown menu key for %s of \'%s\'')%('CoverCheck', menu_key),
                                show=True, show_copy_button=False)

    def check_covers(self):
        d = CoverOptionsDialog(self.gui)
        d.exec_()
        if d.result() != d.Accepted:
            return

        if d.opt_no_cover.isChecked():
            # This is a simple search
            self.gui.search.set_search_string('cover:False')
            return

        # The other options require iterating through the library data
        check_type = 'none'
        check_operator = d.check_operator
        if d.opt_file_size.isChecked():
            check_type = 'file_size'
            min_file_size = d.file_size * 1024
        elif d.opt_dimensions.isChecked():
            check_type = 'dimensions'
            min_image_width = d.image_width
            min_image_height = d.image_height
        elif d.opt_aspect_ratio.isChecked():
            check_type = 'aspect'
            target_aspect_ratio = d.aspect_x / d.aspect_y
            aspect_tolerance_amt = d.aspect_tolerance_pct * target_aspect_ratio / 100
            min_aspect_ratio  = target_aspect_ratio - aspect_tolerance_amt
            max_aspect_ratio  = target_aspect_ratio + aspect_tolerance_amt

        def evaluate_book(book_id, db):
            if not db.has_cover(book_id):
                return False
            cover_path = os.path.join(db.library_path, db.path(book_id, index_is_id=True), 'cover.jpg')
            if not os.path.exists(cover_path)or not os.access(cover_path, os.R_OK):
                self.log.error('Unable to access cover: ', cover_path)
                return False

            mark_book = False
            if check_type == 'file_size':
                cover_size = os.path.getsize(cover_path)
                if check_operator == _('less than') and cover_size < min_file_size:
                    mark_book = True
                elif check_operator == _('greater than') and cover_size > min_file_size:
                    mark_book = True
            else: # dimensions or aspect
                try:
                    im = Image.open(cover_path)
                except IOError:
                    self.log(_('Failed to identify cover:'), cover_path)
                else:
                    (cover_width, cover_height) = im.size
                    if check_type == 'dimensions':
                        mark_book = self._evaluate_dimensions(check_operator, cover_width, cover_height, min_image_width, min_image_height)
                    else:
                        mark_book = self._evaluate_aspect_ratio(check_operator, cover_width, cover_height, min_aspect_ratio, max_aspect_ratio)
                    
            return mark_book

        total_count, result_ids, cancelled_msg = self.check_all_files(evaluate_book,
                                                                  marked_text='cover_check',
                                                                  status_msg_type=_('books for covers'))

        msg = _('Checked %d books, found %d cover matches%s') % (total_count, len(result_ids), cancelled_msg)
        self.gui.status_bar.showMessage(msg)
        if len(result_ids) == 0:
            d = ResultsSummaryDialog(self.gui, _('No Matches%s')%cancelled_msg, _('No matches found'), self.log)
            d.exec_()
        elif self.log.plain_text:
            d = ResultsSummaryDialog(self.gui, _('Quality Check'),
                                     _('%d matches found, see log for errors%s')%(total_count,cancelled_msg),
                                     self.log)
            d.exec_()


    def _evaluate_dimensions(self, check_operator, cover_width, cover_height, min_image_width, min_image_height):
        if check_operator == _('less than'):
            if cover_width < min_image_width:
                return True
            elif cover_height < min_image_height:
                return True
        elif check_operator == _('greater than'):
            if cover_width > min_image_width and min_image_width != 0:
                return True
            elif cover_height > min_image_height and min_image_height != 0:
                return True
        elif check_operator == _('equal to'):
            if min_image_height == 0:
                if cover_width == min_image_width:
                    return True
            elif min_image_width == 0:
                if cover_height == min_image_height:
                    return True
            elif cover_width == min_image_width and cover_height == min_image_height:
                return True
        elif check_operator == _('not equal to'):
            if min_image_width != 0:
                if cover_width != min_image_width:
                    return True
            if min_image_height != 0:
                if cover_height != min_image_height:
                    return True
        return False

    def _evaluate_aspect_ratio(self, check_operator, cover_width, cover_height, min_aspect_ratio, max_aspect_ratio):
        aspect_ratio = cover_width / cover_height
        if check_operator == _('less than'):
            if aspect_ratio < min_aspect_ratio:
                return True
        elif check_operator == _('greater than'):
            if aspect_ratio > max_aspect_ratio:
                return True
        elif check_operator == _('equal to'):
            if aspect_ratio == min_aspect_ratio:
                return True
        elif check_operator == _('not equal to'):
            if aspect_ratio < min_aspect_ratio or aspect_ratio > max_aspect_ratio:
                return True
        return False

