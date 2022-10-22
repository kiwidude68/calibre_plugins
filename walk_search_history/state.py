from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

# calibre Python 3 compatibility.
from six import text_type as unicode

class SearchHistoryState:
    # Keep a history of searches.
    # This class is our "visited" history, and is used for the dropdown menu
    # It is also the base class for our NavigationSearchHistoryState class which is
    # used for the fwd/bwd navigation.

    MAX_HISTORY = 25

    def __init__(self, search):
        self.clear()
        self.snapshot = list()
        # Seed our history list with the contents of the search combobox history as a starting point
        if search:
            for i in range(search.count()):
                self.snapshot.append(unicode(search.itemText(i)))

    def clear(self):
        self.snapshot = []

    def items(self):
        return self.snapshot

    def insert(self, text):
        # If the item exists in our history, move it to the top
        # Otherwise add it at the top
        if text in self.snapshot:
            self.snapshot.remove(text)
        self.snapshot.insert(0, text)
        # Make sure we don't keep too much history...
        while len(self.snapshot) > self.MAX_HISTORY:
            self.snapshot.pop()


class NavigationSearchHistoryState(SearchHistoryState):
    # Keep track of the recent searches allowing fwd/bwd navigation.
    # When the user issues a new search (breaking the sequence) all
    # "forward" entries if any will be removed.

    def __init__(self, search):
        SearchHistoryState.__init__(self, search)
        # Ensure we have a blank search (as this is system startup) to move forward to if go back
        self.snapshot.insert(0, '')
        self.position = 0

    def clear(self):
        SearchHistoryState.clear(self)
        self.position = -1

    def insert(self, text):
        # Override the base behaviour slightly
        # If we have navigated backwards, remove searches that are considered in future
        if self.position > 0:
            for i in range(self.position):
                self.snapshot.pop(0)
        # It is ok to have duplicates in our list as this reflects order of searches
        self.snapshot.insert(0, text)
        # Make sure we don't keep too much history...
        while len(self.snapshot) > self.MAX_HISTORY:
            self.snapshot.pop()
        # Reset our search position
        self.position = 0

    def get_current(self):
        print('get_current:',self.snapshot)
        if self.position != -1:
            print('get_current at position:',self.snapshot[self.position])
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
