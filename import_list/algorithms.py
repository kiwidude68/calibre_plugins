from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import re
from collections import OrderedDict, defaultdict

from calibre.utils.config import tweaks
from calibre.utils.localization import get_udc

TITLE_AUTHOR_ALGORITHMS = [ ('identical', 'identical'),
                            ('similar', 'identical'),
                            ('identical', 'similar'),
                            ('similar', 'similar'),
                            ('fuzzy', 'similar')]

TITLE_ONLY_ALGORITHMS = [ ('identical', ''),
                          ('similar', '') ]

CACHED_ALGORITHMS = TITLE_AUTHOR_ALGORITHMS + TITLE_ONLY_ALGORITHMS

def authors_to_list(db, book_id):
    authors = db.authors(book_id, index_is_id=True)
    if authors:
        return [a.strip().replace('|',',') for a in authors.split(',')]
    return []

def fuzzy_it(text, patterns=None):
    # Changes from Find Duplicates are to strip everything in () and [] brackets
    # rather than just the brackets themselves.
    # Also to replace an ampersand with the word 'and'
    fuzzy_title_patterns = [(re.compile(pat, re.IGNORECASE), repl) for pat, repl in
                [
                    (r'(\[.*\])', ''),
                    (r'(\(.*\))', ''),
                    (r'&', ' and '),
                    (r'[{}<>\'";,:#\?]', ''),
                    (tweaks.get('title_sort_articles', r'^(a|the|an)\s+'), ''),
                    (r'[-._]', ' '),
                    (r'\s+', ' ')
                ]]
    if not patterns:
        patterns = fuzzy_title_patterns
    text = text.strip().lower()
    for pat, repl in patterns:
        text = pat.sub(repl, text)
    return text.strip()


def get_title_tokens(title, strip_subtitle=True, decode_non_ascii=True):
    '''
    Take a title and return a list of tokens useful for an AND search query.
    Excludes subtitles (optionally), punctuation and 'the'.
    Unlike Find Duplicates, does not exclude 'a' and always strips stuff in parenthesis
    Also has extra words to strip like series|trilogy
    '''
    if title:
        # strip sub-titles
        if strip_subtitle:
            subtitle = re.compile(r'([\[\{].*?[\]\}]|[/:\\].*$)')
            if len(subtitle.sub('', title)) > 1:
                title = subtitle.sub('', title)

        title_patterns = [(re.compile(pat, re.IGNORECASE), repl) for pat, repl in
        [
            # Always remove items in parenthesis
            (r'(\(.*\))', ''),
            # Remove things like: (2010) (Omnibus) etc.
            (r'(?i)[({\[](\d{4}|omnibus|anthology|hardcover|paperback|mass\s*market|edition|ed\.|series|trilogy)[\])}]', ''),
            # Remove any strings that contain the substring edition inside
            # parentheses
            (r'(?i)[({\[].*?(edition|ed.).*?[\]})]', ''),
            # Remove commas used a separators in numbers
            (r'(\d+),(\d+)', r'\1\2'),
            # Remove hyphens only if they have whitespace before them
            (r'(\s-)', ' '),
            # Remove single quotes not followed by 's'
            (r"'(?!s)", ''),
            # Replace other special chars with a space
            (r'''[:,;+!@#$%^&*(){}.`~"\s\[\]/]''', ' ')
        ]]

        for pat, repl in title_patterns:
            title = pat.sub(repl, title)

        if decode_non_ascii:
            title = get_udc().decode(title)
        tokens = title.split()
        for token in tokens:
            token = token.strip()
            if token and (token.lower() not in ('the',)):
                yield token.lower()


def get_author_tokens(author, decode_non_ascii=True):
    '''
    Take an author and return a list of tokens useful for duplicate
    hash comparisons. This function tries to return tokens in
    first name middle names last name order, by assuming that if a comma is
    in the author name, the name is in lastname, other names form.
    '''

    ignore_suffixes = ['von', 'van', 'jr', 'sr', 'i', 'ii', 'iii', 'second', 'third',
                       'md', 'phd']
    if author:
        # Leave ' in there for Irish names
        remove_pat = re.compile(r'[,!@#$%^&*(){}`~"\s\[\]/]')
        replace_pat = re.compile(r'[-+.:;]')
        au = replace_pat.sub(' ', author)
        if decode_non_ascii:
            au = get_udc().decode(au)
        parts = au.split()
        if ',' in au:
            # au probably in ln, fn form
            parts = parts[1:] + parts[:1]
        for tok in parts:
            tok = remove_pat.sub('', tok).strip()
            if len(tok) > 0 and tok.lower() not in ignore_suffixes:
                yield tok.lower()


# --------------------------------------------------------------
#           Title Matching Algorithm Functions
# --------------------------------------------------------------

def identical_title_match(title):
    return title.lower()

def similar_title_match(title):
    title = get_udc().decode(title)
    return fuzzy_it(title)

def fuzzy_title_match(title):
    title_tokens = list(get_title_tokens(title))
    result = ''.join(title_tokens)
    return result


# --------------------------------------------------------------
#           Author Matching Algorithm Functions
#
#  Note that these return two hashes
#  - first is based on the author name supplied
#  - second (if not None) is based on swapping name order
# --------------------------------------------------------------

def identical_author_match(author):
    return author.lower(), None

def similar_author_match(author):
    # Unlike Find Duplicates, our notion of "similar" is to strip any initials
    author_tokens = [t for t in get_author_tokens(author) if len(t) > 1]
    hashv = ' '.join(author_tokens)
    rev_hash = None
    if len(author_tokens) > 1:
        author_tokens = author_tokens[1:] + author_tokens[:1]
        rev_hash = ' '.join(author_tokens)
    return hashv, rev_hash

# --------------------------------------------------------------
#                    Algorithm Factories
# --------------------------------------------------------------


def get_title_algorithm_fn(title_match):
    '''
    Return the appropriate function for the desired title match
    '''
    if title_match == 'identical':
        return identical_title_match
    if title_match == 'similar':
        return similar_title_match
    if title_match == 'fuzzy':
        return fuzzy_title_match
    return None


def get_author_algorithm_fn(author_match):
    '''
    Return the appropriate function for the desired author match
    '''
    if author_match == 'identical':
        return identical_author_match
    if author_match == 'similar':
        return similar_author_match
    return None


# --------------------------------------------------------------
#                    LibraryHashBuilder Class
# --------------------------------------------------------------


class LibraryHashBuilder(object):
    '''
    Responsible for creating a dictionary of all the books in your library
    hashed in various combinations of title and author using different
    naming strategies
    '''
    def __init__(self, db):
        self.db = db
        self.hash_maps = {}
        self._create_maps()
        # Update: add match by identifier {
        self._create_maps_by_identifier()
        #}

    def _create_maps(self):
        '''
        The entry point for running the algorithm
        '''
        book_ids = list(self.db.all_ids())

        for alg_tuple in CACHED_ALGORITHMS:
            self.hash_maps[alg_tuple] = defaultdict(set)

        # Get our map of potential duplicate candidates
        self._find_candidates(book_ids)

        # Now ask for these candidate groups to be ordered so that our numbered
        # groups will have some kind of consistent order to them.
        for alg_tuple in CACHED_ALGORITHMS:
            self.hash_maps[alg_tuple] = self._sort_candidate_groups(self.hash_maps[alg_tuple])


    def _find_candidates(self, book_ids):
        for book_id in book_ids:
            title = self.db.title(book_id, index_is_id=True)
            authors = authors_to_list(self.db, book_id)
            for title_alg, author_alg in CACHED_ALGORITHMS:
                candidates_map = self.hash_maps[(title_alg, author_alg)]
                title_eval = get_title_algorithm_fn(title_alg)
                author_eval = get_author_algorithm_fn(author_alg)
                title_hash = title_eval(title)
                if author_eval is not None:
                    if authors:
                        for author in authors:
                            author_hash, rev_author_hash = author_eval(author)
                            candidates_map[title_hash+author_hash].add(book_id)
                            if rev_author_hash and rev_author_hash != author_hash:
                                candidates_map[title_hash+rev_author_hash].add(book_id)
                        continue
                candidates_map[title_hash].add(book_id)

    def _sort_candidate_groups(self, hash_map):
        '''
        Responsible for returning an ordered dict of how to order the groups
        Default implementation will just sort by the fuzzy key of our candidates
        '''
        skeys = sorted(hash_map.keys())
        return OrderedDict([(key, hash_map[key]) for key in skeys])

    # Update: add match by identifier {
    def _create_maps_by_identifier(self):
        db_identifiers = self.db.get_all_identifier_types()
        
        if 'uuid' not in db_identifiers:
            book_ids = self.db.all_ids()
        else:
            book_ids = self.db.data.search_getting_ids('identifier:True', self.db.data.search_restriction)
        
        # add uuid to identifiers after checking the user has no uuid custom identifier
        if 'uuid' not in db_identifiers:
            identifiers_plus = db_identifiers + ['uuid']
        else:
            identifiers_plus = db_identifiers
        for id_type in identifiers_plus:
            self.hash_maps[id_type] = defaultdict(set)

        for book_id in book_ids:
            identifiers = self.db.get_identifiers(book_id, index_is_id=True)
            for k, v in identifiers.items():
                hash_map = self.hash_maps[k]
                hash_map[v].add(book_id)
                # hash uuid value if the user does not have a custom uuid identifier
            if 'uuid' not in db_identifiers:
                hash_map = self.hash_maps['uuid']
                uuid = self.db.uuid(book_id, index_is_id=True)
                hash_map[uuid].add(book_id)

        for id_type in identifiers_plus:
            self._sort_candidate_groups(self.hash_maps[id_type])
#}
