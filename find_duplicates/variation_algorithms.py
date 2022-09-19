from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import time
from collections import OrderedDict, defaultdict

from calibre import prints
from calibre.constants import DEBUG

from calibre_plugins.find_duplicates.matching import get_variation_algorithm_fn

# --------------------------------------------------------------
#              Variation Algorithm Class
# --------------------------------------------------------------

class VariationAlgorithm(object):
    '''
    Perform the search for metadata variations
    '''
    def __init__(self, db):
        self.db = db

    def run_variation_check(self, match_type, item_type):
        '''
        The entry point for running the algorithm
        '''
        data_map = self._get_items_to_consider(item_type)
        self.fn = get_variation_algorithm_fn(match_type, item_type)
        start = time.time()

        # Get our map of potential duplicate candidates
        if DEBUG:
            prints('Analysing %d %s for duplicates...' % (len(data_map), item_type))
        candidates_map = self._find_candidates(data_map)

        # Convert our dictionary of potential candidates into a map by
        # item id that has flattened the results out.
        matches_for_item_map = self._flatten_candidates_for_item(candidates_map, data_map)

        # Now lookup how many books there are for each candidate
        count_map = self._get_counts_for_candidates(matches_for_item_map, item_type)

        if DEBUG:
            prints('Completed duplicate analysis in:', time.time() - start)
            prints('Found %d duplicate groups'%(len(matches_for_item_map),))
        return data_map, count_map, matches_for_item_map

    def _get_items_to_consider(self, item_type):
        '''
        Return a map of id:text appropriate to the item being analysed
        '''
        if item_type == 'authors':
            results = self.db.get_authors_with_ids()
            results = [(a[0], a[1].replace('|',',')) for a in results]
        elif item_type == 'series':
            results = self.db.get_series_with_ids()
        elif item_type == 'publisher':
            results = self.db.get_publishers_with_ids()
        elif item_type == 'tags':
            results = self.db.get_tags_with_ids()
        else:
            raise Exception('Unknown item type:', item_type)
        return dict((x[0],x[1]) for x in results)

    def _find_candidates(self, data_map):
        '''
        Iterate across the data_map to consider and call find_candidate.
        Return a dictionary of candidates.
        '''
        candidates_map = defaultdict(set)
        for item_id, item_text in list(data_map.items()):
            result = self.fn(item_text)
            # Have to cope with functions returning 1 or 2 results since
            # author functions do the reverse hash too
            if isinstance(result, str):
                candidates_map[result].add(item_id)
            else:
                hash1 = result[0]
                hash2 = result[1]
                candidates_map[hash1].add(item_id)
                if hash2 and hash2 != hash1:
                    candidates_map[hash2].add(item_id)
        return candidates_map

    def _shrink_candidates_map(self, candidates_map):
        for key in list(candidates_map.keys()):
            if len(candidates_map[key]) < 2:
                del candidates_map[key]

    def _flatten_candidates_for_item(self, candidates_map, data_map):
        '''
        Given a dictionary of sets of item ids keyed by some a common hash key
          - remove any sets that are subsets of other sets
          - ignore all groups with less than two members
          - create a flattened map keyed by each item id of all the other
            item ids that particular item was considered a duplicate of
          - sort the flattened map to order the keys by the item name
        '''
        # Convert our map of groups into a list of sets with any duplicate groups removed
        candidates_list = self._clean_dup_groups(candidates_map)

        unsorted_item_map = defaultdict(set)
        for item_id_set in candidates_list:
            for item_id in item_id_set:
                for other_item_id in item_id_set:
                    if other_item_id != item_id:
                        unsorted_item_map[item_id].add(other_item_id)

        skeys = sorted(list(unsorted_item_map.keys()),
                   key=lambda ckey: data_map[ckey])
        return OrderedDict([(key, unsorted_item_map[key]) for key in skeys])

    def _clean_dup_groups(self, candidates_map):
        '''
        Given a dictionary of sets, convert into a list of sets removing any sets
        that are subsets of other sets.
        '''
        res = [set(d) for d in list(candidates_map.values())]
        res.sort(key=lambda x: len(x))
        candidates_list = []
        for i,a in enumerate(res):
            for b in res[i+1:]:
                if a.issubset(b):
                    break
            else:
                candidates_list.append(a)
        return candidates_list

    def _get_counts_for_candidates(self, matches_for_item_map, item_type):
        all_counts = self.db.get_usage_count_by_id(item_type)
        # Only return counts for items we are indicating are duplicate candidates
        count_map = {}
        for item_id, count in all_counts:
            if item_id in matches_for_item_map:
                count_map[item_id] = count
        return count_map


# --------------------------------------------------------------
#                        Test Code
# --------------------------------------------------------------

def run_variation_algorithm(match_type, item_type):
    from calibre.library import db
    alg = VariationAlgorithm(db())
    dm, cm, im = alg.run_variation_check(match_type, item_type)
    print('---')
    print('%s %s Duplicate Results:'%(match_type, item_type))
    for k, matches in list(im.items()):
        texts = ['%s (%d)'%(dm[i],cm[i]) for i in matches]
        print('  %s (%d) => {%s}'%(dm[k], cm[k], ', '.join(texts)))

# For testing, run from command line with this:
# calibre-debug -e algorithms.py
if __name__ == '__main__':
    run_variation_algorithm('similar','author')
    #run_variation_algorithm('similar','series')
    #run_variation_algorithm('similar','publisher')
    #run_variation_algorithm('similar','tag')

