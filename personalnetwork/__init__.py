"""
personalnetwork/__init__.py

Adapted for the real Steemit dataset provided by the advisor
(source,target,weight,date,type -- 31M rows, Jan-Jun 2017).

SIMPLIFIED vs. earlier draft: tie strength uses frequency only (per
advisor's instruction), so all hour/day-binning machinery (needed only
for the signature-based metric) has been removed entirely. This is a
much simpler design: just a count per (ego, alter, interaction_type).
"""

from collections import Counter
import numpy as np
import pandas as pd

# Confirmed from the real data: `cut -d',' -f5 ... | sort -u` returned
# exactly these three values (plus the header row itself).
INTERACTION_TYPES = ['vote', 'comment', 'transfer']


class AlterData(object):
    """Tracks one alter's (contact's) interaction counts with a given ego."""

    def __init__(self, alter_id, interaction_types=INTERACTION_TYPES):
        self.alter_id = alter_id
        self.counts = {t: 0 for t in interaction_types}

    def add_interaction(self, interaction_type):
        self.counts[interaction_type] += 1


class EgoInteractions(object):
    """Tracks one ego's whole personal network, as interaction counts."""

    def __init__(self, ego_id, interaction_types=INTERACTION_TYPES):
        self.ego_id = ego_id
        self.interaction_types = interaction_types
        self.interactions = {}  # alter_id -> AlterData
        self.total_counts = {t: 0 for t in interaction_types}

    def _get_alter_data(self, alter_id):
        alter_data = self.interactions.get(alter_id, None)
        if not alter_data:
            alter_data = AlterData(alter_id, self.interaction_types)
            self.interactions[alter_id] = alter_data
        return alter_data

    def process_interaction(self, alter, interaction_type):
        """
        No timestamp parameter -- time is deliberately ignored per the
        advisor's instruction (frequency-only tie strength).
        """
        self._get_alter_data(alter).add_interaction(interaction_type)
        self.total_counts[interaction_type] += 1

    def out_degree(self, interaction_type=None):
        """
        Number of distinct alters contacted. If interaction_type is
        given, counts only alters contacted via that specific type;
        otherwise counts alters contacted via ANY type (union).
        """
        if interaction_type is None:
            return len(self.interactions)
        return sum(1 for a in self.interactions.values() if a.counts[interaction_type] > 0)


def ring_size_to_table(rings_in_personal_network, intervals, min_network_size=50):
    """
    Builds a summary table of ring counts/sizes across all egos.
    Unchanged from the original -- fully data-agnostic.
    """
    algo_results = {}
    for ego_data in rings_in_personal_network.values():
        for c_name, data_all in ego_data.items():
            if c_name not in algo_results:
                algo_results[c_name] = {}
            num_rings = data_all['num_rings']
            if data_all['silhouette'] >= 0 and len(data_all['alter2ring']) >= min_network_size:
                if num_rings not in algo_results[c_name]:
                    algo_results[c_name][num_rings] = {}
                for ring, counting in Counter(np.ravel(list(data_all['alter2ring'].values()))).items():
                    if ring not in algo_results[c_name][num_rings]:
                        algo_results[c_name][num_rings][ring] = []
                    algo_results[c_name][num_rings][ring].append(counting)

    columns = (['Algorithm', '# Rings', '# Egos']
               + ['Ring Avg {}'.format(i) for i in range(1, max(intervals) + 1)]
               + ['Ring std {}'.format(i) for i in range(1, max(intervals) + 1)])
    table = pd.DataFrame(columns=columns)
    count_entries = 0
    for algo, v1 in algo_results.items():
        for num_rings, rings in v1.items():
            data = [np.mean(rings[r]) for r in sorted(rings.keys())]
            data_std = [np.std(rings[r]) for r in sorted(rings.keys())]
            row = ([algo, num_rings, len(rings[1])] + data
                    + [float(0) for _ in range(max(intervals) - len(data))]
                    + data_std
                    + [float(0) for _ in range(max(intervals) - len(data))])[:len(columns)]
            table.loc[count_entries] = row
            count_entries += 1
    table.sort_values(by=['Algorithm', '# Rings'], inplace=True)
    table = table[table['# Rings'].isin(intervals)]
    return table
