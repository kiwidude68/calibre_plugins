# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
#         Trevor Cohn <tacohn@csse.unimelb.edu.au>
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

"""
Tokenizers that divide strings into substrings using regular
expressions that can match either tokens or separators between tokens.
"""

import re
import types

def _mro(cls):
    """
    Return the I{method resolution order} for C{cls} -- i.e., a list
    containing C{cls} and all its base classes, in the order in which
    they would be checked by C{getattr}.  For new-style classes, this
    is just cls.__mro__.  For classic classes, this can be obtained by
    a depth-first left-to-right traversal of C{__bases__}.
    """
    if isinstance(cls, type):
        return cls.__mro__
    else:
        mro = [cls]
        for base in cls.__bases__: mro.extend(_mro(base))
        return mro


def overridden(method):
    """
    @return: True if C{method} overrides some method with the same
    name in a base class.  This is typically used when defining
    abstract base classes or interfaces, to allow subclasses to define
    either of two related methods:

        >>> class EaterI:
        ...     '''Subclass must define eat() or batch_eat().'''
        ...     def eat(self, food):
        ...         if overridden(self.batch_eat):
        ...             return self.batch_eat([food])[0]
        ...         else:
        ...             raise NotImplementedError()
        ...     def batch_eat(self, foods):
        ...         return [self.eat(food) for food in foods]

    @type method: instance method
    """
    # [xx] breaks on classic classes!
    if isinstance(method, types.MethodType) and method.im_class is not None:
        name = method.__name__
        funcs = [cls.__dict__[name]
                 for cls in _mro(method.im_class)
                 if name in cls.__dict__]
        return len(funcs) > 1
    else:
        raise TypeError('Expected an instance method.')
    
    
def string_span_tokenize(s, sep):
    """
    Identify the tokens in the string, as defined by the token
    delimiter, and generate (start, end) offsets.
    
    @param s: the string to be tokenized
    @type s: C{str}
    @param sep: the token separator
    @type sep: C{str}
    @rtype: C{iter} of C{tuple} of C{int}
    """
    if len(sep) == 0:
        raise ValueError("Token delimiter must not be empty")
    left = 0
    while True:
        try:
            right = s.index(sep, left)
            if right != 0:
                yield left, right
        except ValueError:
            if left != len(s):
                yield left, len(s)
            break

        left = right + len(sep)


def regexp_span_tokenize(s, regexp):
    """
    Identify the tokens in the string, as defined by the token
    delimiter regexp, and generate (start, end) offsets.
    
    @param s: the string to be tokenized
    @type s: C{str}
    @param regexp: the token separator regexp
    @type regexp: C{str}
    @rtype: C{iter} of C{tuple} of C{int}
    """
    left = 0
    for m in re.finditer(regexp, s):
        right, next_pos = m.span()
        if right != 0:
            yield left, right
        left = next_pos
    yield left, len(s)


def convert_regexp_to_nongrouping(pattern):
    """
    Convert all grouping parentheses in the given regexp pattern to
    non-grouping parentheses, and return the result.  E.g.:

        >>> convert_regexp_to_nongrouping('ab(c(x+)(z*))?d')
        'ab(?:c(?:x+)(?:z*))?d'

    @type pattern: C{str}
    @rtype: C{str}
    """
    # Sanity check: back-references are not allowed!
    for s in re.findall(r'\\.|\(\?P=', pattern):
        if s[1] in '0123456789' or s == '(?P=':
            raise ValueError('Regular expressions with back-references '
                             'are not supported: %r' % pattern)

    # This regexp substitution function replaces the string '('
    # with the string '(?:', but otherwise makes no changes.
    def subfunc(m):
        return re.sub('^\((\?P<[^>]*>)?$', '(?:', m.group())

    # Scan through the regular expression.  If we see any backslashed
    # characters, ignore them.  If we see a named group, then
    # replace it with "(?:".  If we see any open parens that are part
    # of an extension group, ignore those too.  But if we see
    # any other open paren, replace it with "(?:")
    return re.sub(r'''(?x)
        \\.           |  # Backslashed character
        \(\?P<[^>]*>  |  # Named group
        \(\?          |  # Extension group
        \(               # Grouping parenthasis''', subfunc, pattern)


class TokenizerI(object):
    """
    A processing interface for I{tokenizing} a string, or dividing it
    into a list of substrings.
    
    Subclasses must define:
      - either L{tokenize()} or L{batch_tokenize()} (or both)
    """
    def tokenize(self, s):
        """
        Divide the given string into a list of substrings.
        
        @return: C{list} of C{str}
        """
        if overridden(self.batch_tokenize):
            return self.batch_tokenize([s])[0]
        else:
            raise NotImplementedError()

    def span_tokenize(self, s):
        """
        Identify the tokens using integer offsets (start_i, end_i),
        where s[start_i:end_i] is the corresponding token.
        
        @return: C{iter} of C{tuple} of C{int}
        """
        raise NotImplementedError()

    def batch_tokenize(self, strings):
        """
        Apply L{self.tokenize()} to each element of C{strings}.  I.e.:

            >>> return [self.tokenize(s) for s in strings]

        @rtype: C{list} of C{list} of C{str}
        """
        return [self.tokenize(s) for s in strings]

    def batch_span_tokenize(self, strings):
        """
        Apply L{self.span_tokenize()} to each element of C{strings}.  I.e.:

            >>> return [self.span_tokenize(s) for s in strings]

        @rtype: C{iter} of C{list} of C{tuple} of C{int}
        """
        for s in strings:
            yield list(self.span_tokenize(s))


class RegexpTokenizer(TokenizerI):
    """
    A tokenizer that splits a string into substrings using a regular
    expression.  The regular expression can be specified to match
    either tokens or separators between tokens.

    Unlike C{re.findall()} and C{re.split()}, C{RegexpTokenizer} does
    not treat regular expressions that contain grouping parenthases
    specially.
    """
    def __init__(self, pattern, gaps=False, discard_empty=True,
                 flags=re.UNICODE | re.MULTILINE | re.DOTALL):
        """
        Construct a new tokenizer that splits strings using the given
        regular expression C{pattern}.  By default, C{pattern} will be
        used to find tokens; but if C{gaps} is set to C{False}, then
        C{patterns} will be used to find separators between tokens
        instead.

        @type pattern: C{str}
        @param pattern: The pattern used to build this tokenizer.
            This pattern may safely contain grouping parenthases.
        @type gaps: C{bool}
        @param gaps: True if this tokenizer's pattern should be used
            to find separators between tokens; False if this
            tokenizer's pattern should be used to find the tokens
            themselves.
        @type discard_empty: C{bool}
        @param discard_empty: True if any empty tokens (C{''})
            generated by the tokenizer should be discarded.  Empty
            tokens can only be generated if L{_gaps} is true.
        @type flags: C{int}
        @param flags: The regexp flags used to compile this
            tokenizer's pattern.  By default, the following flags are
            used: C{re.UNICODE | re.MULTILINE | re.DOTALL}.
        """
        # If they gave us a regexp object, extract the pattern.
        pattern = getattr(pattern, 'pattern', pattern)
        
        self._pattern = pattern
        """The pattern used to build this tokenizer."""
        
        self._gaps = gaps
        """True if this tokenizer's pattern should be used to find
        separators between tokens; False if this tokenizer's pattern
        should be used to find the tokens themselves."""

        self._discard_empty = discard_empty
        """True if any empty tokens (C{''}) generated by the tokenizer
        should be discarded.  Empty tokens can only be generated if
        L{_gaps} is true."""

        self._flags = flags
        """The flags used to compile this tokenizer's pattern."""
        
        self._regexp = None
        """The compiled regular expression used to tokenize texts."""
        
        # Remove grouping parentheses -- if the regexp contains any
        # grouping parentheses, then the behavior of re.findall and
        # re.split will change.
        nongrouping_pattern = convert_regexp_to_nongrouping(pattern)

        try: 
            self._regexp = re.compile(nongrouping_pattern, flags)
        except re.error as e:
            raise ValueError('Error in regular expression %r: %s' %
                             (pattern, e))

    def tokenize(self, text):
        # If our regexp matches gaps, use re.split:
        if self._gaps:
            if self._discard_empty:
                return [tok for tok in self._regexp.split(text) if tok]
            else:
                return self._regexp.split(text)

        # If our regexp matches tokens, use re.findall:
        else:
            return self._regexp.findall(text)

    def span_tokenize(self, text):
        if self._gaps:
            for left, right in regexp_span_tokenize(text, self._regexp):
                if not (self._discard_empty and left == right):
                    yield left, right
        else:
            for m in re.finditer(self._regexp, text):
                yield m.span()
    
    def __repr__(self):
        return ('%s(pattern=%r, gaps=%r, discard_empty=%r, flags=%r)' %
                (self.__class__.__name__, self._pattern, self._gaps,
                 self._discard_empty, self._flags))


class WhitespaceTokenizer(RegexpTokenizer):
    r"""
    A tokenizer that divides a string into substrings by treating any
    sequence of whitespace characters as a separator.  Whitespace
    characters are space (C{' '}), tab (C{'\t'}), and newline
    (C{'\n'}).  If you are performing the tokenization yourself
    (rather than building a tokenizer to pass to some other piece of
    code), consider using the string C{split()} method instead:

        >>> words = s.split()
    """

    def __init__(self):
        RegexpTokenizer.__init__(self, r'\s+', gaps=True)


class BlanklineTokenizer(RegexpTokenizer):
    """
    A tokenizer that divides a string into substrings by treating any
    sequence of blank lines as a separator.  Blank lines are defined
    as lines containing no characters, or containing only space
    (C{' '}) or tab (C{'\t'}) characters.
    """
    def __init__(self):
        RegexpTokenizer.__init__(self, r'\s*\n\s*\n\s*', gaps=True)


class WordPunctTokenizer(RegexpTokenizer):
    r"""
    A tokenizer that divides a text into sequences of alphabetic and
    non-alphabetic characters.  E.g.:

        >>> WordPunctTokenizer().tokenize("She said 'hello'.")
        ['She', 'said', "'", 'hello', "'."]
    """
    def __init__(self):
        RegexpTokenizer.__init__(self, r'\w+|[^\w\s]+')


######################################################################
#{ Tokenization Functions
######################################################################

def regexp_tokenize(text, pattern, gaps=False, discard_empty=True,
                    flags=re.UNICODE | re.MULTILINE | re.DOTALL):
    """
    Split the given text string, based on the given regular expression
    pattern.  See the documentation for L{RegexpTokenizer.tokenize()}
    for descriptions of the arguments.
    """
    tokenizer = RegexpTokenizer(pattern, gaps, discard_empty, flags)
    return tokenizer.tokenize(text)

blankline_tokenize = BlanklineTokenizer().tokenize
wordpunct_tokenize = WordPunctTokenizer().tokenize
