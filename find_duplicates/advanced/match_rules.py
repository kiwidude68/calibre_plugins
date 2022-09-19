#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~

__license__ = 'GPL v3'
__copyright__ = '2020, Ahmed Zaki <azaki00.dev@gmail.com>'

import copy
from collections import OrderedDict

from calibre import prints
from calibre.constants import DEBUG
from calibre.ebooks.metadata.book.base import Metadata

from calibre_plugins.find_duplicates.advanced.common import composite_to_list, column_metadata

try:
    load_translations()
except NameError:
    pass

class HashBuilder(object):

    def __init__(self, gui, algorithms, match_rules):
        self.gui = gui
        self.db = gui.current_db
        self.algorithms = algorithms
        self.match_rules = match_rules
        self.processed_match_rules = self._process_match_rules(match_rules)

    def _add_reversed_rules(self, match_rules):
        '''
        match rules that contain algothims that should produce rev_ahash (similar_authors, soundex_authors)
        will be copied, replacing the algorithm with its reversed counter algorithm, leaving all other 
        algorithms/templates that does pre/post processing the same
        '''
        # detect match rules that needs copying
        add_reversed = []
        for match_rule in match_rules:
            algo_dicts = match_rule['algos']
            field = match_rule['field']
            has_names = match_rule.get('composite_has_names')
            if column_metadata(self.db, field)['delegate'] != 'authors':
                # check no composite fields with names (we cannot know these in advance to set the delegate flag)
                if not has_names:
                    continue
            for algo_dict in algo_dicts:
                name = algo_dict['name']
                algorithm = self.algorithms[name]
                if algorithm.has_reverse(field, has_names):
                    reverse_rule = copy.deepcopy(match_rule)
                    reverse_rule['reverse'] = True
                    add_reversed.append(reverse_rule)
                    break

        # add new reversed match rules to match rules
        match_rules += add_reversed
        return match_rules


    def _attach_match_functions(self, match_rules):
        '''
        match rules that contain algothims that should produce rev_ahash (similar_authors, soundex_authors)
        will be copied, replacing the algorithm with its reversed counter algorithm, leaving all other 
        algorithms/templates that does pre/post processing the same
        '''
        for match_rule in match_rules:
            algo_dicts = match_rule['algos']
            field = match_rule['field']
            reverse = match_rule.get('reverse', False)
            has_names = match_rule.get('composite_has_names')
            for algo_dict in algo_dicts:
                name = algo_dict['name']
                algorithm = self.algorithms[name]
                algo_dict['func'] = algorithm.factory(field, reverse, has_names)

        return match_rules

    def _process_match_rules(self, match_rules):
        # use deepcopy as this will be rendered non json serializable
        match_rules = copy.deepcopy(match_rules)                                  

        # add reversed rules for algorithms like soundex_authors_match and similar_authors_match
        match_rules = self._add_reversed_rules(match_rules)

        # process match rules to attach functions to them
        match_rules = self._attach_match_functions(match_rules)
        
        return match_rules

    def from_book_metadata(self, mi, data={}):
        '''
        Take an iterable of match rules for duplicate processing.
        Each match rule specify one or more algorithms (or templates) to act on a certain field.
        All the algorithms/templates in a matching rule act on the same field successivley, handing
        the generated hash to the next algorithm/template to act on.
        For fields with multiple items, unless the multiply flag is turned off, each
        item is processed by the algorithms/templates separately, producing one hash for each item.
        In the end results of all the match rules are combined into one or more
        hashes depending on the muliply flag for multiple item fields.
        '''
        book_id = mi.id
        hash_string = ''
        hash_multipliers = OrderedDict()
        for match_rule in self.processed_match_rules:
            field_name = match_rule['field']
            multiply = match_rule['multiply']
            algo_dicts = match_rule['algos']
            reverse = match_rule.get('reverse', False)
            # this flag is used for composite columns with multiple items to determine the separator
            composite_has_names = match_rule.get('composite_has_names')            
            field_value = mi.get(field_name)
            if composite_has_names:
                field_value = composite_to_list(field_name, field_value, mi, composite_has_names)
            if field_name == 'formats' and not field_value:
                # mi.get('formats') returns None if no formats
                field_value = []
            
            is_multiple = mi.metadata_for_field(field_name)['is_multiple'] != {}
            if is_multiple:
                hashes_to_join = set()
                if multiply and not hash_multipliers.get(field_name):
                    hash_multipliers[field_name] = set()
                for item in field_value:
                    item_hash = item.strip()
                    for algo_dict in algo_dicts:
                        settings = algo_dict['settings']
                        func = algo_dict.get('func')
                        item_hash = func(item_hash, mi, settings, data)
                    if item_hash:
                        if multiply:
                            if DEBUG:
                                item_hash = '|{}:{}|'.format(field_name, item_hash)
                            hash_multipliers[field_name].add(item_hash)
                        else:
                            hashes_to_join.add(item_hash)
                            
                # join hashes for field with multiple items (author, tag ... etc) if multiply was set to False
                if len(hashes_to_join) > 0:
                    hash_ = '|'.join(sorted(hashes_to_join))
                    if DEBUG:
                        hash_ = '|{}:{}|'.format(field_name, hash_)
                    hash_string += hash_
                    
            else:
                if field_value:
                    hash_ = str(field_value)
                    for algo_dict in algo_dicts:
                        settings = algo_dict['settings']
                        func = algo_dict.get('func')
                        hash_ = func(hash_, mi, settings, data)
                    if DEBUG:
                        hash_ = '|{}:{}|'.format(field_name, hash_)
                    if hash_:
                        hash_string += hash_

            # Template Match changes the field_vlaue inside mi, restore it for later match_rules that might
            # need to do conditional matching based on this field value
            mi.set(field_name, field_value)
                    
        # multiply the generated hash by hashes generated by fields with multiple items whose multiply flag is set to True
        all_hashes = set()
        all_hashes.add(hash_string)
        for mf_hashes in hash_multipliers.values():
            new_hashes = set()
            for mf_hash in mf_hashes:
                for hash_ in all_hashes:
                    new_hash = hash_ + mf_hash
                    new_hashes.add(new_hash)
            if new_hashes:
                all_hashes = new_hashes
#        if DEBUG:
#            prints('Find Duplicates: Hashes for book_id ({}): {}'.format(book_id, all_hashes))
        return all_hashes

    def from_category_item(self, data, item_text):
        '''
        This functions operates on metadata item like author, tag, ... etc
        Each match rule specify one or more algorithms to act on a certain field.
        All the algorithms in a matching rule act on the same field successivley, handing
        the generated hash to the next algorithm to act on.
        The data object is a Python dict that persists between all successive invocations of
        from_category_item() while looping through all items.
        '''
        # we have either one match rule, or two (the second being the rule to generate rev_hash)
        hashes = []
        for match_rule in self.processed_match_rules:
            field_name = match_rule['field']
            algo_dicts = match_rule['algos']
            reverse = match_rule.get('reverse', False)
            
            hash_ = str(item_text)
            
            # create a mi instance to persist the hash value for templates to read from
            mi = Metadata(_('Unknown'))
            mi.set_all_user_metadata(self.db.field_metadata.custom_field_metadata())
            is_multiple = self.db.field_metadata.all_metadata()[field_name]['is_multiple']
            if is_multiple or field_name == 'authors':
                mi.set(field_name, [hash_])
            else:
                mi.set(field_name, hash_)
            
            for algo_dict in algo_dicts:
                settings = algo_dict['settings']
                func = algo_dict.get('func')
                hash_ = func(hash_, mi, settings, data)

            hashes.append(hash_)

        if len(hashes) == 1:
            # no rule for rev_hash
            hashes.append(None)

        return hashes

def check_match_rule(gui, algorithms, match_rule, possible_cols, target_db):
    '''
    check match rule for errors, and produce new match rule containing the remaining
    valid fields and algorithms.
    also produce dict detailing errors found
    '''
    gui = gui
    db = gui.current_db
    book_id = list(db.all_ids())[0]
    mi = db.new_api.get_proxy_metadata(book_id)
    new_match_rule = {
        'algos': [],
        'multiply': match_rule.get('multiply', True),
        'composite_has_names': match_rule.get('composite_has_names', False)
    }
    errors = {
        'field': '',
        'missing_functions': set(),
        'error_functions': set(),
        'templates': set()
    }
    has_errors = False
    algo_dicts = match_rule['algos']
    field = match_rule['field']
    if field in possible_cols:
        new_match_rule['field'] = field
    else:
        errors['field'] = field
        has_errors = True
        if DEBUG:
            if not field:
                prints('Find Duplicates: Match rule has no field')
            else:
                prints('Find Duplicates: cannot add column to match rule: {}, possible columns: {}'.format(field, possible_cols))
    for algo_dict in algo_dicts:
        name = algo_dict['name']
        settings = algo_dict.get('settings')
        algorithm = algorithms.get(name)
        
        if algorithm:
            # test the algorithm
            is_valid = algorithm.validate(settings, target_db)
            if is_valid is not True:
                msg, details = is_valid
                errors['error_functions'].add(name)
                has_errors = True
            else:
                new_match_rule['algos'].append({'name': name, 'settings': settings})

        # must be a user function that is no longer there
        else:
            errors['missing_functions'].add(name)
            has_errors = True
            if DEBUG:
                prints('Find Duplicates: cannot find algorithm: {}'.format(name))
    return new_match_rule, has_errors, errors

def parse_match_rule_errors(errors, idx):
    msg = _('Errors for match:') + '\n'
    sep = '\n   • '
    if idx:
        msg = _('Errors for match rule no. {}:').format(idx) + '\n'
    field = errors.get('field')
    if field:
        msg += ' ‣' + _('Column "{}" cannot be added to match rule').format(field) + '\n'
    missing_functions = errors['missing_functions']
    if missing_functions:
        msg += ' ‣' + _('The following functions are missing and cannot be restored:{}{}').format(sep, sep.join(list(missing_functions))) + '\n'
    error_functions = errors['error_functions']
    if error_functions:
        msg += ' ‣' + _('Encountered errors while running the following functions:{}{}').format(sep, sep.join(list(error_functions))) + '\n'
    error_templates = errors['templates']
    if error_templates:
        msg += ' ‣' + _('Encountered errors while running the following templates:{}{}').format(sep, sep.join(list(error_templates))) + '\n'
    return msg


def validate_match_rule(gui, algorithms, match_rule, possible_cols, idx=1, target_db=None):
    db = gui.current_db
    new_match_rule, has_errors, errors = check_match_rule(gui, algorithms, match_rule, possible_cols, target_db)
    if has_errors:
        details = parse_match_rule_errors(errors, idx)
        return _('Validation Error'), details
    else:
        return True

