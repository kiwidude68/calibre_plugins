#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~

__license__   = 'GPL v3'
__copyright__ = '2020, Ahmed Zaki <azaki00.dev@gmail.com>'

from collections import OrderedDict

try:
    from qt.core import QWidget, QVBoxLayout, QSpinBox, QGroupBox
except ImportError:
    from PyQt5.Qt import QWidget, QVBoxLayout, QSpinBox, QGroupBox

from calibre import prints
from calibre.constants import DEBUG
from calibre.gui2 import error_dialog
from calibre.ebooks.metadata.book.formatter import SafeFormat

import calibre_plugins.find_duplicates.matching as matching
from calibre_plugins.find_duplicates.advanced.templates import (get_metadata_object,
                            check_template, TEMPLATE_ERROR, TemplateBox)
from calibre_plugins.find_duplicates.advanced.common import column_metadata

try:
    load_translations()
except NameError:
    pass


class MetadataMatch(object):

    # Matches must have a unique name attribute.
    name = 'no name provided'
    description = ''

    '''
    This is the base class for all algorithms
    '''
    def __init__(self, gui):
        '''
        All algorithms are intialized at startup
        The are re-initialized on library change, and on adding or modifying custom algorithms
        '''
        self.gui = gui
        self.db = self.gui.current_db

    def run(self, field_name, hash_, mi, reverse, has_names, settings, data={}, *args, **kwargs):
        '''
        This is the method that contain the logic of the algorithm.
        The settings is a dictionary with options configured for the specific
        algorithm using the settings button.
        '''
        raise NotImplementedError

    def factory(self, field_name, reverse=False, composite_has_names=False):
        '''
        return function to calculate hash based on filed name
        '''
        return lambda _hash, _mi, _settings, _data: self.run(field_name, _hash, _mi, reverse, composite_has_names, _settings, _data)

    def config_widget(self):
        '''
        If you want your action to have settings dialog, implement this method
        This should return a Qwidget (not dialog) with the following methods:
        [*] __init__(self, gui)
        [*] save_settings(settings)
                This method is used to save the settings from the widget
                it should return a dictionary containing all the settings
        [*] load_settings(self, settings)
                This method is used to load the saved settings into the
                widget
        '''
        return None

    def default_settings(self):
        '''
        default settings to be used if no settings are configured
        '''
        return {}

    def validate(self, settings, target_db=None):
        random_val = '000' #must be numerical, otheriwse might err when function expects number
        mi = get_metadata_object(self.gui)
        try:
            self.run('title', random_val, mi, False, False, settings, data={})
        except Exception as e:
            if DEBUG:
                prints('Find Duplicates: error running function: {} with settings: {}, return this exception: {}'.format(self.name, settings, e))
                import traceback
                print(traceback.format_exc())
            return (_('Match Error'), _('Error when trying to run algorithm: {}').format(self.name))
        return True

    def has_reverse(self, field_name, has_names):
        '''
        Returns True for algorithm that has a reverse alorithm for field_name.
        '''
        return False

class TemplateMatchWidget(TemplateBox):
    def __init__(self, parent, gui, action, name, title):
        self.action = action
        self.gui = gui
        self.db = self.gui.current_db
        mi = get_metadata_object(self.gui)
        TemplateBox.__init__(
                self,
                parent,
                self.gui,
                template_text='',
                placeholder_text = _("Write you algorithm using calibre's template language"),
                mi=mi
            )
        self.setWindowTitle(title)

    def _on_select_chk_change(self):
        state = self.select_chk.isChecked()
        if not state:
            self.search_opt.setChecked(True)
        self.ids_opt.setEnabled(state)

    def load_settings(self, settings):
        if settings:
            template = settings['template']
            self.textbox.insertPlainText(template)

    def save_settings(self):
        settings = {}
        settings['template'] = str(self.textbox.toPlainText()).rstrip()
        return settings

    def accept(self):
        self.settings = self.save_settings()
        # validate settings
        is_valid = self.action.validate(self.settings)
        if is_valid is not True:
            msg, details = is_valid
            error_dialog(
                self,
                msg,
                details,
                show=True
            )
            return
        TemplateBox.accept(self)

class TemplateMatch(MetadataMatch):

    name = _('Template Match')
    _is_builtin = True
    description = _('Custom algorithms using calibre template language.')

    def run(self, field_name, hash_, mi, reverse, has_names, settings, data={}, *args, **kwargs):
        # update the mi to presist the hash as this the only way a template can see the result of the previous algorithm/template
        self.do_update_mi(mi, field_name, hash_)

        template = settings['template']
        hash_ = SafeFormat().safe_format(template, mi, TEMPLATE_ERROR, mi)

        return hash_

    def do_update_mi(self, mi, field_name, value):
        if field_name.startswith('identifier:'):
            # 'identifier:' has no entry in field_metadata and would raise an exception
            pass
        # all composite fields (even those where ['is_multiple'] != {}) are of string type
        elif not mi.metadata_for_field(field_name)['datatype'] == 'composite':
            if field_name == 'authors' or ( mi.metadata_for_field(field_name)['is_multiple'] != {} ):
                # for fields with multiple items, when we update a single item, we must put it in a list
                # because mi expect multiple value field, if you don't do this it will treat the string
                # value as iterable and split it into letters.
                value = [value]
            elif mi.metadata_for_field(field_name)['datatype'] == 'datetime':
                try:
                    value = parse_date(value)
                except:
                    if DEBUG:
                        prints('Find Duplicates: Unable to update mi object with value ({}) for field ({}) for book_id ({})'.format(value, field_name, mi.id))
                    return
            elif mi.metadata_for_field(field_name)['datatype'] in ['rating', 'float']:
                try:
                    value = float(value)
                except:
                    if DEBUG:
                        prints('Find Duplicates: Unable to update mi object with value ({}) for field ({}) for book_id ({})'.format(value, field_name, mi.id))
                    return
            elif mi.metadata_for_field(field_name)['datatype'] == 'int':
                try:
                    value = int(value)
                except:
                    if DEBUG:
                        prints('Find Duplicates: Unable to update mi object with value ({}) for field ({}) for book_id ({})'.format(value, field_name, mi.id))
                    return
        mi.set(field_name, value)

    def validate(self, settings, target_db=None):
        template = settings['template']
        if not template:
            return _('Empty template'), _('You must have a template for this algorithm')
        is_valid = check_template(template, self.gui, target_db, print_error=False)
        if is_valid is True:
            return True
        else:
            msg, details = is_valid
            if DEBUG:
                prints('Find Duplicates: tepmlate: "{}" returned this error: {}'.format(name, details))
            return msg, details

    def config_widget(self):
        return TemplateMatchWidget

class IdenticalMatch(MetadataMatch):

    name = _('Identical Match')
    description = _('Case insensitive exact match')
    _is_builtin = True

    def run(self, field_name, hash_, mi, reverse, has_names, settings, data={}, *args, **kwargs):
        if has_names:
            algorithm = self.factory('authors', reverse)
        else:
            algorithm = self.factory(field_name, reverse)
        hash_ = algorithm(hash_, mi, settings, data, *args, **kwargs)
        return hash_

    def factory(self, field_name, reverse=False, composite_has_names=False):
        delegate = column_metadata(self.db, field_name)['delegate']
        if composite_has_names:
            delegate = 'authors'
        return getattr(self, 'identical_{}_match'.format(delegate))

    def identical_title_match(self, title, mi, settings, data, *args, **kwargs):
        lang = settings.get('lang', None)
        return matching.identical_title_match(title, lang=lang)

    def identical_authors_match(self, author, mi, settings, data, *args, **kwargs):
        ahash, rev_ahash = matching.identical_authors_match(author)
        return ahash

    def identical_series_match(self, series, mi, settings, data, *args, **kwargs):
        return matching.identical_title_match(series)

    def identical_publisher_match(self, publisher, mi, settings, data, *args, **kwargs):
        return matching.identical_title_match(publisher)

    def identical_tags_match(self, tags, mi, settings, data, *args, **kwargs):
        return matching.identical_title_match(tags)

class SimilarMatch(MetadataMatch):

    name = _('Similar Match')
    description = _('Removal of common punctuation and prefixes')
    _is_builtin = True

    def run(self, field_name, hash_, mi, reverse, has_names, settings, data={}, *args, **kwargs):
        if has_names:
            algorithm = self.factory('authors', reverse)
        else:
            algorithm = self.factory(field_name, reverse)
        hash_ = algorithm(hash_, mi, settings, data, *args, **kwargs)
        return hash_

    def factory(self, field_name, reverse=False, composite_has_names=False):
        delegate = column_metadata(self.db, field_name)['delegate']
        if composite_has_names:
            delegate = 'authors'
        if reverse:
            return getattr(self, 'rev_similar_{}_match'.format(delegate))        
        else:
            return getattr(self, 'similar_{}_match'.format(delegate))

    def similar_title_match(self, title, mi, settings, data, *args, **kwargs):
        lang = settings.get('lang', None)
        return matching.similar_title_match(title, lang=lang)

    def similar_authors_match(self, author, mi, settings, data, *args, **kwargs):
        author_tokens = list(matching.get_author_tokens(author))
        ahash = ' '.join(author_tokens)
        return ahash

    def rev_similar_authors_match(self, author, mi, settings, data, *args, **kwargs):
        author_tokens = list(matching.get_author_tokens(author))
        rev_ahash = ''
        if len(author_tokens) > 1:
            author_tokens = author_tokens[1:] + author_tokens[:1]
            rev_ahash = ' '.join(author_tokens)
        return rev_ahash

    def similar_series_match(self, series, mi, settings, data, *args, **kwargs):
        return matching.similar_series_match(series)

    def similar_publisher_match(self, publisher, mi, settings, data, *args, **kwargs):
        return matching.similar_publisher_match(publisher)

    def similar_tags_match(self, tags, mi, settings, data, *args, **kwargs):
        return matching.similar_tags_match(tags)

    def has_reverse(self, field_name, has_names):
        if has_names:
            return True
        if column_metadata(self.db, field_name)['delegate'] == 'authors':
            return True
        else:
            return False

class SoundexConfigWidget(QWidget):
    def __init__(self, gui, *args, **kwargs):
        QWidget.__init__(self)
        self.gui = gui
        self.db = self.gui.current_db
        self._init_controls()

    def _init_controls(self):

        l = self.l = QVBoxLayout()
        self.setLayout(l)
        
        groupbox = QGroupBox(_('Soundex length'))
        l.addWidget(groupbox)
        groupbox_l = QVBoxLayout()
        groupbox.setLayout(groupbox_l)
        self.spin = QSpinBox()
        groupbox_l.addWidget(self.spin)

        self.spin.setMinimum(1)
        self.spin.setMaximum(100)
        self.spin.setSingleStep(1)
        self.spin.setValue(6)
        
        l.addStretch(1)

        self.setMinimumSize(300,300)

    def load_settings(self, settings):
        if settings:
            self.spin.setValue(settings['soundex_length'])

    def save_settings(self):
        settings = {}
        settings['soundex_length'] = self.spin.value()
        return settings

class SoundexMatch(MetadataMatch):

    name = _('Soundex Match')
    description = _('Phonetic representation of names')
    _is_builtin = True

    def run(self, field_name, hash_, mi, reverse, has_names, settings, data={}, *args, **kwargs):
        if has_names:
            algorithm = self.factory('authors', reverse)
        else:
            algorithm = self.factory(field_name, reverse)
        hash_ = algorithm(hash_, mi, settings, data, *args, **kwargs)
        return hash_

    def factory(self, field_name, reverse=False, composite_has_names=False):
        delegate = column_metadata(self.db, field_name)['delegate']
        if composite_has_names:
            delegate = 'authors'
        if reverse:
            return getattr(self, 'rev_soundex_{}_match'.format(delegate))        
        else:
            return getattr(self, 'soundex_{}_match'.format(delegate))

    def soundex_title_match(self, title, mi, settings, data, *args, **kwargs):
        soundex_length = settings.get('soundex_length', 6)
        lang = kwargs.get('lang', None)
        matching.set_title_soundex_length(soundex_length)
        return matching.soundex_title_match(title, lang=lang)

    def soundex_authors_match(self, author, mi, settings, data, *args, **kwargs):
        soundex_length = settings.get('soundex_length', 6)
        # Convert to an equivalent of "similar" author first before applying the soundex
        author_tokens = list(matching.get_author_tokens(author))
        if len(author_tokens) <= 1:
            return matching.soundex(''.join(author_tokens))
        # We will put the last name at front as want the soundex to focus on surname
        new_author_tokens = [author_tokens[-1]]
        new_author_tokens.extend(author_tokens[:-1])
        ahash = matching.soundex(''.join(new_author_tokens), soundex_length)
        return ahash

    def rev_soundex_authors_match(self, author, mi, settings, data, *args, **kwargs):
        soundex_length = settings.get('soundex_length', 6)
        # Convert to an equivalent of "similar" author first before applying the soundex
        author_tokens = list(matching.get_author_tokens(author))
        if len(author_tokens) <= 1:
            return ''
        # We will put the last name at front as want the soundex to focus on surname
        rev_ahash = matching.soundex(''.join(author_tokens), soundex_length)
        return rev_ahash

    def soundex_series_match(self, series, mi, settings, data, *args, **kwargs):
        soundex_length = settings.get('soundex_length', 6)
        matching.set_series_soundex_length(soundex_length)
        return matching.soundex_series_match(series)

    def soundex_publisher_match(self, publisher, mi, settings, data, *args, **kwargs):
        soundex_length = settings.get('soundex_length', 6)
        matching.set_publisher_soundex_length(soundex_length)
        return matching.soundex_publisher_match(publisher)

    def soundex_tags_match(self, tags, mi, settings, data, *args, **kwargs):
        soundex_length = settings.get('soundex_length', 6)
        matching.set_tags_soundex_length(soundex_length)
        return matching.soundex_tags_match(tags)

    def config_widget(self):
        return SoundexConfigWidget

    def has_reverse(self, field_name, has_names):
        if has_names:
            return True
        if column_metadata(self.db, field_name)['delegate'] == 'authors':
            return True
        else:
            return False

class FuzzyMatch(MetadataMatch):

    name = _('Fuzzy Match')
    description = _("Remove all punctuation, subtitles and any words after 'and', 'or' or 'aka'")
    _is_builtin = True

    def run(self, field_name, hash_, mi, reverse, has_names, settings, data={}, *args, **kwargs):
        if has_names:
            algorithm = self.factory('authors', reverse)
        else:
            algorithm = self.factory(field_name, reverse)
        hash_ = algorithm(hash_, mi, settings, data, *args, **kwargs)
        return hash_

    def factory(self, field_name, reverse=False, composite_has_names=False):
        delegate = column_metadata(self.db, field_name)['delegate']
        if composite_has_names:
            delegate = 'authors'
        return getattr(self, 'fuzzy_{}_match'.format(delegate))

    def fuzzy_title_match(self, title, mi, settings, data, *args, **kwargs):
        lang = settings.get('lang', None)
        return matching.fuzzy_title_match(title, lang=lang)

    def fuzzy_authors_match(self, author, mi, settings, data, *args, **kwargs):
        ahash, rev_ahash = matching.fuzzy_authors_match(author)
        return ahash

    def fuzzy_series_match(self, series, mi, settings, data, *args, **kwargs):
        return matching.fuzzy_series_match(series)

    def fuzzy_publisher_match(self, publisher, mi, settings, data, *args, **kwargs):
        return matching.fuzzy_publisher_match(publisher)

    def fuzzy_tags_match(self, tags, mi, settings, data, *args, **kwargs):
        return matching.fuzzy_tags_match(tags)

#=================

def get_all_algorithms(gui, user_algorithm_classes):

    builtin_algorithms = OrderedDict()
    
    _builtin_algorithms = [
        IdenticalMatch,
        SimilarMatch,
        SoundexMatch,
        FuzzyMatch,
        TemplateMatch
    ]

    for algorithm_cls in _builtin_algorithms:
        builtin_algorithms[algorithm_cls.name] = algorithm_cls

    all_algorithms = OrderedDict()
    user_algorithms = OrderedDict()
    
    for algorithm_name, algorithm_cls in builtin_algorithms.items():
        algorithm = algorithm_cls(gui)
        all_algorithms[algorithm_name]= algorithm

    for algorithm_name, algorithm_cls in user_algorithm_classes.items():
        # dont override builtin algorithms
        if algorithm_name in builtin_algorithms.keys():
            continue
        if algorithm_name in ['', 'no name provided']:
            continue
        try:
            algorithm = algorithm_cls(gui)
            algorithm.is_user_algorithm = True
            all_algorithms[algorithm_name]= algorithm
            user_algorithms[algorithm_name]= algorithm
        except Exception as e:
            import traceback
            if DEBUG:
                prints('Find Duplicates: Error intializing user action: {}\n{}'.format(algorithm_name, traceback.format_exc()))

    return all_algorithms, builtin_algorithms, user_algorithms
