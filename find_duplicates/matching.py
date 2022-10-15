from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import re
from calibre import prints
from calibre.utils.config import tweaks
from calibre.utils.localization import get_udc

title_soundex_length = 6
author_soundex_length = 8
publisher_soundex_length = 6
series_soundex_length = 6
tags_soundex_length = 4

ignore_author_words = ['von', 'van', 'jr', 'sr', 'i', 'ii', 'iii', 'second', 'third',
                       'md', 'phd']
IGNORE_AUTHOR_WORDS_MAP = dict((k,True) for k in ignore_author_words)

def ids_for_field(db, ids_of_books, field_name):
    # First get all the names for the desired books.
    # Use a set to make them unique
    unique_names = set()
    for tup in db.all_field_for(field_name, ids_of_books).values():
        for val in tup:
            unique_names.add(val)
    # Now get the ids for the names and build the pairs
    id_field_pairs = list()
    for name in unique_names:
        id_field_pairs.append((db.get_item_id(field_name, name), name))
    return id_field_pairs

def get_field_pairs(db, field):
    # Get the list of books in the current VL
    ids_in_vl = db.data.search_getting_ids('', '', use_virtual_library=True)
    # Get the id,val pairs for the desired field
    field_pairs = ids_for_field(db.new_api, ids_in_vl, field)
    return field_pairs

def set_soundex_lengths(title_len, author_len):
    global title_soundex_length
    title_soundex_length = title_len
    global author_soundex_length
    author_soundex_length = author_len

def set_title_soundex_length(title_len):
    global title_soundex_length
    title_soundex_length = title_len

def set_author_soundex_length(author_len):
    global author_soundex_length
    author_soundex_length = author_len

def set_publisher_soundex_length(publisher_len):
    global publisher_soundex_length
    publisher_soundex_length = publisher_len

def set_series_soundex_length(series_len):
    global series_soundex_length
    series_soundex_length = series_len

def set_tags_soundex_length(tags_len):
    global tags_soundex_length
    tags_soundex_length = tags_len


def authors_to_list(db, book_id):
    authors = db.authors(book_id, index_is_id=True)
    if authors:
        return [a.strip().replace('|',',') for a in authors.split(',')]
    return []


def fuzzy_it(text, patterns=None):
    fuzzy_title_patterns = [(re.compile(pat, re.IGNORECASE), repl) for pat, repl in
                [
                    (r'[\[\](){}<>\'";,:#]', ''),
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

def soundex(name, length=4):
    '''
    soundex module conforming to Knuth's algorithm
    implementation 2000-12-24 by Gregory Jorgensen
    public domain
    http://code.activestate.com/recipes/52213-soundex-algorithm/
    '''
    # digits holds the soundex values for the alphabet
    #         ABCDEFGHIJKLMNOPQRSTUVWXYZ
    digits = '01230120022455012623010202'
    sndx = ''
    fc = ''
    orda = ord('A')
    ordz = ord('Z')

    # translate alpha chars in name to soundex digits
    for c in name.upper():
        ordc = ord(c)
        if ordc >= orda and ordc <= ordz:
            if not fc: fc = c   # remember first letter
            d = digits[ordc-orda]
            # duplicate consecutive soundex digits are skipped
            if not sndx or (d != sndx[-1]):
                sndx += d

    # replace first digit with first alpha character
    sndx = fc + sndx[1:]

    # remove all 0s from the soundex code
    sndx = sndx.replace('0','')

    # return soundex code padded to length characters
    return (sndx + (length * '0'))[:length]


# --------------------------------------------------------------
#           Title Matching Algorithm Functions
# --------------------------------------------------------------

def get_title_tokens(title, strip_subtitle=True, decode_non_ascii=True):
    '''
    Take a title and return a list of tokens useful for an AND search query.
    Excludes subtitles (optionally), punctuation and a, the.
    '''
    if title:
        # strip sub-titles
        if strip_subtitle:
            subtitle = re.compile(r'([\(\[\{].*?[\)\]\}]|[/:\\].*$)')
            if len(subtitle.sub('', title)) > 1:
                title = subtitle.sub('', title)

        title_patterns = [(re.compile(pat, re.IGNORECASE), repl) for pat, repl in
        [
            # Remove things like: (2010) (Omnibus) etc.
            (r'(?i)[({\[](\d{4}|omnibus|anthology|hardcover|paperback|mass\s*market|edition|ed\.)[\])}]', ''),
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
            if token and (token.lower() not in ('a', 'the')):
                yield token.lower()

def identical_title_match(title, lang=None):
    if lang:
        return lang + title.lower()
    return title.lower()

def similar_title_match(title, lang=None):
    title = get_udc().decode(title)
    result = fuzzy_it(title)
    if lang:
        return lang + result
    return result

def soundex_title_match(title, lang=None):
    # Convert to an equivalent of "similar" title first before applying the soundex
    title = similar_title_match(title)
    result = soundex(title, title_soundex_length)
    if lang:
        return lang + result
    return result

def fuzzy_title_match(title, lang=None):
    title_tokens = list(get_title_tokens(title))
    # We will strip everything after "and", "or" provided it is not first word in title - this is very aggressive!
    for i, tok in enumerate(title_tokens):
        if tok in ['&', 'and', 'or', 'aka'] and i > 0:
            title_tokens = title_tokens[:i]
            break
    result = ''.join(title_tokens)
    if lang:
        return lang + result
    return result


# --------------------------------------------------------------
#           Author Matching Algorithm Functions
#
#  Note that these return two hashes
#  - first is based on the author name supplied
#  - second (if not None) is based on swapping name order
# --------------------------------------------------------------

def get_author_tokens(author, decode_non_ascii=True, strip_initials=False):
    '''
    Take an author and return a list of tokens useful for duplicate
    hash comparisons. This function tries to return tokens in
    first name middle names last name order, by assuming that if a comma is
    in the author name, the name is in lastname, other names form.
    '''

    if author:
        # Ensure Last,First is treated same as Last, First adding back space after comma.
        comma_no_space_pat = re.compile(r',([^\s])')
        author = comma_no_space_pat.sub(', \\1', author)
        replace_pat = re.compile(r'[-+.:;]')
        au = replace_pat.sub(' ', author)
        if decode_non_ascii:
            au = get_udc().decode(au)
        parts = au.split()
        if ',' in au:
            # au probably in ln, fn form
            parts = parts[1:] + parts[:1]
        # Leave ' in there for Irish names
        remove_pat = re.compile(r'[,!@#$%^&*(){}`~"\s\[\]/]')
        # We will ignore author initials of only one character.
        min_length = 1 if strip_initials else 0
        for tok in parts:
            tok = remove_pat.sub('', tok).strip()
            if len(tok) > min_length and tok.lower() not in IGNORE_AUTHOR_WORDS_MAP:
                yield tok.lower()

def identical_authors_match(author):
    return author.lower(), None

def similar_authors_match(author):
    author_tokens = list(get_author_tokens(author, strip_initials=True))
    ahash = ' '.join(author_tokens)
    rev_ahash = None
    if len(author_tokens) > 1:
        author_tokens = author_tokens[1:] + author_tokens[:1]
        rev_ahash = ' '.join(author_tokens)
    return ahash, rev_ahash

def soundex_authors_match(author):
    # Convert to an equivalent of "similar" author first before applying the soundex
    author_tokens = list(get_author_tokens(author))
    if len(author_tokens) <= 1:
        return soundex(''.join(author_tokens)), None
    # We will put the last name at front as want the soundex to focus on surname
    new_author_tokens = [author_tokens[-1]]
    new_author_tokens.extend(author_tokens[:-1])
    ahash = soundex(''.join(new_author_tokens), author_soundex_length)
    rev_ahash = None
    if len(author_tokens) > 1:
        rev_ahash = soundex(''.join(author_tokens), author_soundex_length)
    return ahash, rev_ahash

def fuzzy_authors_match(author):
    author_tokens = list(get_author_tokens(author))
    if not author_tokens:
        return '', None
    elif len(author_tokens) == 1:
        return author_tokens[0], None
    # We have multiple tokens - create a new list of initial plus last token as surname
    # However we do not want to do a reversed permutation
    # i.e. A. Bronte should return "ABronte" and "", not "BA"!
    new_author_tokens = [author_tokens[0][0], author_tokens[-1]]
    ahash = ''.join(new_author_tokens)
    return ahash, None


# --------------------------------------------------------------
#           Series Matching Algorithm Functions
# --------------------------------------------------------------

def get_series_tokens(series, decode_non_ascii=True):
    '''
    Take a series and return a list of tokens useful for duplicate
    hash comparisons.
    '''

    ignore_words = ['the', 'a', 'and',]
    if series:
        remove_pat = re.compile(r'[,!@#$%^&*(){}`~\'"\s\[\]/]')
        replace_pat = re.compile(r'[-+.:;]')
        s = replace_pat.sub(' ', series)
        if decode_non_ascii:
            s = get_udc().decode(s)
        parts = s.split()
        for tok in parts:
            tok = remove_pat.sub('', tok).strip()
            if len(tok) > 0 and tok.lower() not in ignore_words:
                yield tok.lower()

def similar_series_match(series):
    series_tokens = list(get_series_tokens(series))
    return ' '.join(series_tokens)

def soundex_series_match(series):
    # Convert to an equivalent of "similar" series before applying the soundex
    series_tokens = list(get_series_tokens(series))
    if len(series_tokens) <= 1:
        return soundex(''.join(series_tokens))
    return soundex(''.join(series_tokens), series_soundex_length)

def fuzzy_series_match(series):
    # Fuzzy is going to just be the first name of the series
    series_tokens = list(get_series_tokens(series))
    if not series_tokens:
        return ''
    return series_tokens[0]


# --------------------------------------------------------------
#           Publisher Matching Algorithm Functions
# --------------------------------------------------------------

def get_publisher_tokens(publisher, decode_non_ascii=True):
    '''
    Take a publisher and return a list of tokens useful for duplicate
    hash comparisons.
    '''

    ignore_words = ['the', 'inc', 'ltd', 'limited', 'llc', 'co', 'pty',
                    'usa', 'uk']
    if publisher:
        remove_pat = re.compile(r'[,!@#$%^&*(){}`~\'"\s\[\]/]')
        replace_pat = re.compile(r'[-+.:;]')
        p = replace_pat.sub(' ', publisher)
        if decode_non_ascii:
            p = get_udc().decode(p)
        parts = p.split()
        for tok in parts:
            tok = remove_pat.sub('', tok).strip()
            if len(tok) > 0 and tok.lower() not in ignore_words:
                yield tok.lower()

def similar_publisher_match(publisher):
    publisher_tokens = list(get_publisher_tokens(publisher))
    return ' '.join(publisher_tokens)

def soundex_publisher_match(publisher):
    # Convert to an equivalent of "similar" publisher before applying the soundex
    publisher_tokens = list(get_publisher_tokens(publisher))
    if len(publisher_tokens) <= 1:
        return soundex(''.join(publisher_tokens))
    return soundex(''.join(publisher_tokens), publisher_soundex_length)

def fuzzy_publisher_match(publisher):
    # Fuzzy is going to just be the first name of the publisher, unless
    # that is just a single letter, in which case first two names
    publisher_tokens = list(get_publisher_tokens(publisher))
    if not publisher_tokens:
        return ''
    first = publisher_tokens[0]
    if len(first) > 1 or len(publisher_tokens) == 1:
        return first
    return ' '.join(publisher_tokens[:2])


# --------------------------------------------------------------
#           Tag Matching Algorithm Functions
# --------------------------------------------------------------

def get_tag_tokens(tag, decode_non_ascii=True):
    '''
    Take a tag and return a list of tokens useful for duplicate
    hash comparisons.
    '''

    ignore_words = ['the', 'and', 'a']
    if tag:
        remove_pat = re.compile(r'[,!@#$%^&*(){}`~\'"\s\[\]/]')
        replace_pat = re.compile(r'[-+.:;]')
        t = replace_pat.sub(' ', tag)
        if decode_non_ascii:
            t = get_udc().decode(t)
        parts = t.split()
        for tok in parts:
            tok = remove_pat.sub('', tok).strip()
            if len(tok) > 0 and tok.lower() not in ignore_words:
                yield tok.lower()

def similar_tags_match(tag):
    tag_tokens = list(get_tag_tokens(tag))
    return ' '.join(tag_tokens)

def soundex_tags_match(tag):
    # Convert to an equivalent of "similar" tag before applying the soundex
    tag_tokens = list(get_tag_tokens(tag))
    if len(tag_tokens) <= 1:
        return soundex(''.join(tag_tokens))
    return soundex(''.join(tag_tokens), publisher_soundex_length)

def fuzzy_tags_match(tag):
    # Fuzzy is going to just be the first name of the tag
    tag_tokens = list(get_tag_tokens(tag))
    if not tag_tokens:
        return ''
    return tag_tokens[0]


# --------------------------------------------------------------
#           Find Duplicates Algorithm Factories
# --------------------------------------------------------------


def get_title_algorithm_fn(title_match):
    '''
    Return the appropriate function for the desired title match
    '''
    if title_match == 'identical':
        return identical_title_match
    if title_match == 'similar':
        return similar_title_match
    if title_match == 'soundex':
        return soundex_title_match
    if title_match == 'fuzzy':
        return fuzzy_title_match
    return None


def get_author_algorithm_fn(author_match):
    '''
    Return the appropriate function for the desired author match
    '''
    if author_match == 'identical':
        return identical_authors_match
    if author_match == 'similar':
        return similar_authors_match
    if author_match == 'soundex':
        return soundex_authors_match
    if author_match == 'fuzzy':
        return fuzzy_authors_match
    return None


def get_variation_algorithm_fn(match_type, item_type):
    '''
    Return the appropriate function for the desired variation match where:
        match_type is 'similar', 'soundex' or 'fuzzy'
        item_type is 'author', 'series', 'publisher' or 'tag'
    '''
    fn_name = '%s_%s_match'%(match_type, item_type)
    return globals()[fn_name]

# --------------------------------------------------------------
#                        Test Code
# --------------------------------------------------------------

def do_assert_tests():

    def _assert(test_name, match_type, item_type, value1, value2, equal=True):
        fn = get_variation_algorithm_fn(match_type, item_type)
        hash1 = fn(value1)
        hash2 = fn(value2)
        if (equal and hash1 != hash2) or (not equal and hash1 == hash2):
            prints('Failed: %s %s %s (\'%s\', \'%s\')'%(test_name,
                                match_type, item_type, value1, value2))
            prints(' hash1: %s'%hash1)
            prints(' hash2: %s'%hash2)

    def assert_match(match_type, item_type, value1, value2):
        _assert('is matching', match_type, item_type, value1, value2, equal=True)

    def assert_nomatch(match_type, item_type, value1, value2):
        _assert('not matching', match_type, item_type, value1, value2, equal=False)

    def _assert_author(test_name, match_type, item_type, value1, value2, equal=True):
        fn = get_variation_algorithm_fn(match_type, item_type)
        hash1, rev_hash1 = fn(value1)
        hash2, rev_hash2 = fn(value2)
        results_equal = hash1 in [hash2, rev_hash2] or \
            (rev_hash1 is not None and rev_hash1 in [hash2, rev_hash2])
        if (equal and not results_equal) or (not equal and results_equal):
            prints('Failed: %s %s %s (\'%s\', \'%s\')'% (test_name,
                                match_type, item_type, value1, value2))
            prints(' hash1: ', hash1, ' rev_hash1: ', rev_hash1)
            prints(' hash2: ', hash2, ' rev_hash2: ', rev_hash2)

    def assert_author_match(match_type, item_type, value1, value2):
        _assert_author('is matching', match_type, item_type, value1, value2, equal=True)

    def assert_author_nomatch(match_type, item_type, value1, value2):
        _assert_author('not matching', match_type, item_type, value1, value2, equal=False)


    # Test our identical title algorithms
    assert_match('identical', 'title', 'The Martian Way', 'The Martian Way')
    assert_match('identical', 'title', 'The Martian Way', 'the martian way')
    assert_nomatch('identical', 'title', 'The Martian Way', 'Martian Way')
    assert_nomatch('identical', 'title', 'China Miéville', 'China Mieville')

    # Test our similar title algorithms
    assert_match('similar', 'title', 'The Martian Way', 'The Martian Way')
    assert_match('similar', 'title', 'The Martian Way', 'the martian way')
    assert_match('similar', 'title', 'The Martian Way', 'Martian Way')
    assert_match('similar', 'title', 'The Martian Way', 'The Martian Way')
    assert_match('similar', 'title', 'China Miéville', 'China Mieville')
    assert_nomatch('similar', 'title', 'The Martian Way', 'The Martain Way')
    assert_nomatch('similar', 'title', 'The Martian Way', 'The Martian Way (Foo)')
    assert_nomatch('similar', 'title', 'The Martian Way I', 'The Martian Way II')
    assert_nomatch('similar', 'title', 'The Martian Way', 'The Martian Way and other stories')
    assert_nomatch('similar', 'title', 'The Martian Way', 'The Martian Way, or, My New Title')
    assert_nomatch('similar', 'title', 'The Martian Way', 'The Martian Way aka My New Title')
    assert_nomatch('similar', 'title', 'Foundation and Earth - Foundation 5', 'Foundation and Earth')

    # Test our soundex title algorithms
    assert_match('soundex', 'title', 'The Martian Way', 'The Martian Way')
    assert_match('soundex', 'title', 'The Martian Way', 'the martian way')
    assert_match('soundex', 'title', 'The Martian Way', 'Martian Way')
    assert_match('soundex', 'title', 'The Martian Way', 'The Martian Way')
    assert_match('soundex', 'title', 'The Martian Way', 'The Martain Way')
    assert_match('soundex', 'title', 'The Martian Way I', 'The Martian Way II')
    assert_match('soundex', 'title', 'Angel', 'Angle')
    assert_match('soundex', 'title', 'Foundation and Earth - Foundation 5', 'Foundation and Earth')
    assert_match('soundex', 'title', 'China Miéville', 'China Mieville')
    assert_nomatch('soundex', 'title', 'The Martian Way', 'The Martian Way (Foo)')
    assert_nomatch('soundex', 'title', 'The Martian Way', 'The Martian Way and other stories')
    assert_nomatch('soundex', 'title', 'The Martian Way', 'The Martian Way, or, My New Title')
    assert_nomatch('soundex', 'title', 'The Martian Way', 'The Martian Way aka My New Title')
    assert_nomatch('soundex', 'title', 'Foundation 5 - Foundation and Earth', 'Foundation and Earth')

    # Test our fuzzy title algorithms
    assert_match('fuzzy', 'title', 'The Martian Way', 'The Martian Way')
    assert_match('fuzzy', 'title', 'The Martian Way', 'the martian way')
    assert_match('fuzzy', 'title', 'The Martian Way', 'Martian Way')
    assert_match('fuzzy', 'title', 'The Martian Way', 'The Martian Way')
    assert_match('fuzzy', 'title', 'The Martian Way', 'The Martian Way (Foo)')
    assert_match('fuzzy', 'title', 'The Martian Way', 'The Martian Way: Sequel')
    assert_match('fuzzy', 'title', 'The Martian Way', 'The Martian Way and other stories')
    assert_match('fuzzy', 'title', 'The Martian Way', 'The Martian Way, or, My New Title')
    assert_match('fuzzy', 'title', 'The Martian Way', 'The Martian Way aka My New Title')
    assert_match('fuzzy', 'title', 'Foundation and Earth - Foundation 5', 'Foundation and Earth')
    assert_match('fuzzy', 'title', 'China Miéville', 'China Mieville')
    assert_nomatch('fuzzy', 'title', 'The Martian Way', 'The Martain Way')
    assert_nomatch('fuzzy', 'title', 'The Martian Way I', 'The Martian Way II')
    assert_nomatch('fuzzy', 'title', 'Foundation 5 - Foundation and Earth', 'Foundation and Earth')

    # Test our identical author algorithms
    assert_author_match('identical', 'authors', 'Kevin J. Anderson', 'Kevin J. Anderson')
    assert_author_match('identical', 'authors', 'Kevin J. Anderson', 'Kevin j. Anderson')
    assert_author_nomatch('identical', 'authors', 'Kevin J. Anderson', 'Kevin J Anderson')
    assert_author_nomatch('identical', 'authors', 'China Miéville', 'China Mieville')
    assert_author_nomatch('identical', 'authors', 'Kevin Anderson', 'Anderson Kevin')
    assert_author_nomatch('identical', 'authors', 'Kevin, Anderson', 'Anderson, Kevin')

    # Test our similar author algorithms
    assert_author_match('similar', 'authors', 'Kevin J. Anderson', 'Kevin J. Anderson')
    assert_author_match('similar', 'authors', 'Kevin J. Anderson', 'Kevin j. Anderson')
    assert_author_match('similar', 'authors', 'Kevin J. Anderson', 'Kevin J Anderson')
    assert_author_match('similar', 'authors', 'Kevin J. Anderson', 'Anderson, Kevin J.')
    assert_author_match('similar', 'authors', 'Kevin Anderson', 'Kevin Anderson Jr')
    assert_author_match('similar', 'authors', 'China Miéville', 'China Mieville')
    assert_author_match('similar', 'authors', 'Kevin Anderson', 'Anderson Kevin')
    assert_author_match('similar', 'authors', 'Kevin, Anderson', 'Anderson, Kevin')
    assert_author_match('similar', 'authors', 'Kevin J. Anderson', 'Anderson,Kevin J.')
    assert_author_match('similar', 'authors', 'Kevin Anderson', 'Anderson,Kevin J.')
    assert_author_match('similar', 'authors', 'Kevin Anderson', 'Anderson,Kevin J')
    assert_author_nomatch('identical', 'authors', 'Kevin, Anderson', 'Anderson, Dr Kevin')

    # Test our soundex author algorithms
    assert_author_match('soundex', 'authors', 'Kevin J. Anderson', 'Kevin J. Anderson')
    assert_author_match('soundex', 'authors', 'Kevin J. Anderson', 'Kevin j. Anderson')
    assert_author_match('soundex', 'authors', 'Kevin J. Anderson', 'Kevin J Anderson')
    assert_author_match('soundex', 'authors', 'Kevin J. Anderson', 'Keven J. Andersan')
    assert_author_match('soundex', 'authors', 'Kevin J. Anderson', 'Anderson, Kevin J.')
    assert_author_match('soundex', 'authors', 'Kevin Anderson', 'Kevin Anderson Jr')
    assert_author_match('soundex', 'authors', 'Kevin J. Anderson', 'Kevin Anderson')
    assert_author_match('soundex', 'authors', 'China Miéville', 'China Mieville')
    assert_author_match('soundex', 'authors', 'Kevin Anderson', 'Anderson Kevin')
    assert_author_match('soundex', 'authors', 'Kevin, Anderson', 'Anderson, Kevin')
    assert_author_nomatch('soundex', 'authors', 'Kevin J. Anderson', 'S. Anderson')

    # Test our fuzzy author algorithms
    assert_author_match('fuzzy', 'authors', 'Kevin J. Anderson', 'Kevin J. Anderson')
    assert_author_match('fuzzy', 'authors', 'Kevin J. Anderson', 'Kevin j. Anderson')
    assert_author_match('fuzzy', 'authors', 'Kevin J. Anderson', 'Kevin J Anderson')
    assert_author_match('fuzzy', 'authors', 'Kevin J. Anderson', 'Kevin Anderson')
    assert_author_match('fuzzy', 'authors', 'Kevin J. Anderson', 'Anderson, Kevin J.')
    assert_author_match('fuzzy', 'authors', 'Kevin J. Anderson', 'Anderson, Kevin')
    assert_author_match('fuzzy', 'authors', 'Kevin J. Anderson', 'K. J. Anderson')
    assert_author_match('fuzzy', 'authors', 'Kevin J. Anderson', 'K. Anderson')
    assert_author_match('fuzzy', 'authors', 'Kevin Anderson', 'Kevin Anderson Jr')
    assert_author_match('fuzzy', 'authors', 'Kevin Anderson', 'Anderson Jr, K. S.')
    assert_author_match('fuzzy', 'authors', 'China Miéville', 'China Mieville')
    assert_author_nomatch('fuzzy', 'authors', 'Kevin Anderson', 'Anderson Kevin')
    assert_author_nomatch('fuzzy', 'authors', 'Kevin, Anderson', 'Anderson, Kevin')
    assert_author_nomatch('fuzzy', 'authors', 'Kevin J. Anderson', 'S. Anderson')
    assert_author_nomatch('fuzzy', 'authors', 'A. Brown', 'A. Bronte')

    # Test our similar series algorithms
    assert_match('similar', 'series', 'The Martian Way', 'The Martian Way')
    assert_match('similar', 'series', 'China Miéville', 'China Mieville')
    assert_nomatch('similar', 'series', 'China Miéville', 'China')

    # Test our soundex series algorithms
    assert_match('soundex', 'series', 'Angel', 'Angle')

    # Test our fuzzy series algorithms
    assert_match('fuzzy', 'series', 'China Miéville', 'China')


    # Test our similar publisher algorithms
    assert_match('similar', 'publisher', 'Random House', 'Random House Inc')
    assert_match('similar', 'publisher', 'Random House Inc', 'Random House Inc.')
    assert_nomatch('similar', 'publisher', 'Random House Inc', 'Random')

    # Test our soundex publisher algorithms
    assert_match('soundex', 'publisher', 'Angel', 'Angle')

    # Test our fuzzy publisher algorithms
    assert_match('fuzzy', 'publisher', 'Random House Inc', 'Random')

    prints('Tests completed')


# For testing, run from command line with this:
# calibre-debug -e matching.py
if __name__ == '__main__':
    do_assert_tests()

