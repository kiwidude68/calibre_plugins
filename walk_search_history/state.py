from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

# calibre Python 3 compatibility.
from six import text_type as unicode

MAX_HISTORY = 25

def get_initial_search_items(search):
    # Seed our history list with the contents of the search combobox history as a starting point
    snapshot = list()
    if search:
        for i in range(search.count()):
            snapshot.append(unicode(search.itemText(i)))
    return snapshot


class SearchHistoryState:
    '''
    Keep a history of searches.
    This class is our "visited" history, and is used for the dropdown menu
    This should always look the same as the contents of the calibre search dropdown
    other than our specified threshold of 25 items.
    '''
    def __init__(self, search):
        self.snapshot = get_initial_search_items(search)

    def clear(self):
        self.snapshot = []

    def items(self):
        return self.snapshot

    def append(self, text):
        # If the item exists in our history, move it to the top
        # Otherwise add it at the top
        if text in self.snapshot:
            self.snapshot.remove(text)
        self.snapshot.insert(0, text)
        # Make sure we don't keep too much history...
        while len(self.snapshot) > MAX_HISTORY:
            self.snapshot.pop()


class NavigationSearchHistoryState:
    '''
    Keep track of the recent searches allowing fwd/bwd navigation.
    Starts off the same as the calibre search history at plugin
    startup then diverges over time based on user navigation in
    a similar way to how a web browser navigation works.
    When the user issues a new search (breaking the sequence) all
    "forward" entries if any will be removed.
    '''

    def __init__(self, search):
        self.position = -1
        self.snapshot = get_initial_search_items(search)

    def clear(self):
        self.position = -1
        self.snapshot = []

    def reset_after_empty_search(self):
        # We don't want to insert an empty search in the history list to navigate to.
        # However we do want to make sure that if the user navigates backwards after a
        # empty search that they hit the topmost item in the search list.
        # My decision is that a user applying empty text search should remove any
        # history "forward" of the current position.
        if self.position > 0:
            for _i in range(self.position):
                self.snapshot.pop(0)
        # Now ensure that if they navigate "back" they get the new topmost item.
        self.position = -1

    def append(self, text):
        # Override the base behaviour slightly
        # If we have navigated backwards, remove searches that are considered in future
        if self.position > 0:
            for _i in range(self.position):
                self.snapshot.pop(0)
        # It is ok to have duplicates in our list as this reflects order of searches
        self.snapshot.insert(0, text)
        # Make sure we don't keep too much history...
        while len(self.snapshot) > MAX_HISTORY:
            self.snapshot.pop()
        # Reset our search position to reflect the current text
        self.position = 0

    def get_current(self):
        if self.position != -1:
            return self.snapshot[self.position]
        return ''

    def get_current_position(self):
        return self.position

    def goto_previous(self):
        if self.position < len(self.snapshot) - 1:
            self.position = self.position + 1
            return True
        return False

    def goto_next(self):
        if self.position > 0:
            self.position = self.position - 1
            return True
        return False
