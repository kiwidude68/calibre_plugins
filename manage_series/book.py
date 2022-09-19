from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from calibre.ebooks.metadata.book.base import Metadata
from calibre.utils.date import format_date

def get_indent_for_index(series_index):
    if not series_index:
        return 0
    return len(str(series_index).split('.')[1].rstrip('0'))

class SeriesBook(object):
    series_column = 'Series'

    def __init__(self, mi, series_columns):
        self._orig_mi = Metadata(_('Unknown'), other=mi)
        self._mi = mi
        self._series_columns = series_columns
        self._assigned_indexes = { 'Series': None }
        self._series_indents = { 'Series': get_indent_for_index(mi.series_index) }
        self._is_valid_index = True
        self._orig_custom_series = {}

        for key in self._series_columns:
            self._orig_custom_series[key] = mi.get_user_metadata(key, True)
            self._series_indents[key] = get_indent_for_index(self.series_index(column=key))
            self._assigned_indexes[key] = None

    def get_mi_to_persist(self):
        # self._mi will be potentially polluted with changes applied to multiple series columns
        # Instead return a Metadata object with only changes relevant to the last series column selected.
        self._orig_mi.title = self._mi.title
        if hasattr(self._mi, 'pubdate'):
            self._orig_mi.pubdate = self._mi.pubdate
        if self.series_column == 'Series':
            self._orig_mi.series = self._mi.series
            self._orig_mi.series_index = self._mi.series_index
        else:
            mod_col = self._mi.get_user_metadata(self.series_column, False)
            col = self._orig_mi.get_user_metadata(self.series_column, False)
            col['#value#'] = mod_col['#value#']
            col['#extra#'] = mod_col['#extra#']

        return self._orig_mi

    def id(self):
        if hasattr(self._mi, 'id'):
            return self._mi.id

    def authors(self):
        return self._mi.authors

    def title(self):
        return self._mi.title

    def set_title(self, title):
        self._mi.title = title

    def is_title_changed(self):
        return self._mi.title != self._orig_mi.title

    def pubdate(self):
        if hasattr(self._mi, 'pubdate'):
            return self._mi.pubdate

    def set_pubdate(self, pubdate):
        self._mi.pubdate = pubdate

    def is_pubdate_changed(self):
        if hasattr(self._mi, 'pubdate') and hasattr(self._orig_mi, 'pubdate'):
            return self._mi.pubdate != self._orig_mi.pubdate
        return False

    def is_series_changed(self):
        if self.series_column == 'Series':
            if self._mi.series != self._orig_mi.series:
                return True
            if self._mi.series_index != self._orig_mi.series_index:
                return True
        else:
            col = self._mi.get_user_metadata(self.series_column, False)
            orig_col = self._orig_custom_series[self.series_column]
            if col.get('#value#', None) != orig_col.get('#value#', None):
                return True
            if col.get('#extra#', None) != orig_col.get('#extra#', None):
                return True
        return False

    def orig_series_name(self):
        if self.series_column == 'Series':
            return self._orig_mi.series
        else:
            col = self._orig_custom_series[self.series_column]
            if col:
                return col.get('#value#', None)

    def orig_series_index(self):
        if self.series_column == 'Series':
            return self._orig_mi.series_index
        else:
            col = self._orig_custom_series[self.series_column]
            if col:
                return col.get('#extra#', None)

    def series_name(self):
        if self.series_column == 'Series':
            return self._mi.series
        else:
            col = self._mi.get_user_metadata(self.series_column, False)
            if col:
                return col.get('#value#', None)

    def set_series_name(self, series_name):
        if self.series_column == 'Series':
            self._mi.series = series_name
        else:
            col = self._mi.get_user_metadata(self.series_column, False)
            if col:
                col['#value#'] = series_name

    def series_index(self, column=None):
        if not column:
            column = self.series_column
        if column == 'Series':
            if self._mi.series:
                return self._mi.series_index
        else:
            col = self._mi.get_user_metadata(column, False)
            if col and col.get('#value#', None):
                return col.get('#extra#',
                               0) # can't compare None in py3
        return 0

    def set_series_index(self, series_index):
        if self.series_column == 'Series':
            self._mi.series_index = series_index
        else:
            col = self._mi.get_user_metadata(self.series_column, False)
            col['#extra#'] = series_index
        self.set_series_indent(get_indent_for_index(series_index))

    def series_indent(self):
        return self._series_indents[self.series_column]

    def set_series_indent(self, index):
        self._series_indents[self.series_column] = index

    def assigned_index(self):
        return self._assigned_indexes[self.series_column]

    def set_assigned_index(self, index):
        self._assigned_indexes[self.series_column] = index

    def is_valid(self):
        return self._is_valid_index

    def set_is_valid(self, is_valid_index):
        self._is_valid_index = is_valid_index

    def sort_key(self, sort_by_pubdate=False, sort_by_name=False):
        if sort_by_pubdate:
            pub_date = self.pubdate()
            if pub_date is not None and pub_date.year > 101:
                return format_date(pub_date, 'yyyyMMdd')
        else:
            series = self.orig_series_name()
            if series:
                if sort_by_name:
                    return '%s%06.2f'% (series, self.orig_series_index())
                else:
                    return '%06.2f%s'% (self.orig_series_index(), series)
        return ''

