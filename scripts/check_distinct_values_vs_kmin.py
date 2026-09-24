"""
check_distinct_values_vs_kmin.py

For each ego above the alter threshold on a given interaction type,
checks whether the number of DISTINCT tie strength values it has is
enough to structurally support the minimum number of circles required
by the adaptive constraint for its personal network size. If an ego
has fewer distinct values than the minimum k required, forming that
many non-empty clusters is logically impossible, not just unlikely.

Splits egos into "succeeded" and "failed" (using the clustering
results pickle) and reports, for each group, how many fall into this
structurally impossible case, plus the overall distribution of the
number of distinct values relative to the required minimum.

Usage:
    python3 check_distinct_values_vs_kmin.py <personal_networks_pickle> <rings_pickle> <interaction_type> [threshold]

Example:
    python3 check_distinct_values_vs_kmin.py data/processed/personal_networks_filtered.pkl data/processed/rings_vote.pkl vote
    python3 check_distinct_values_vs_kmin.py data/processed/personal_networks_filtered.pkl data/processed/rings_comment.pkl comment
    python3 check_distinct_values_vs_kmin.py data/processed/personal_networks_transfer_filtered.pkl data/processed/rings_transfer.pkl transfer
"""

import sys
import os
import pickle
import statistics

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from personalnetwork.clustering import frequency_tie_strength, get_ring_interval


def analyse(personal_networks_pickle, rings_pickle, interaction_type, threshold=50):
    with open(personal_networks_pickle, 'rb') as f:
        personal_networks = pickle.load(f)
    with open(rings_pickle, 'rb') as f:
        rings = pickle.load(f)

    succeeded_ids = set(rings.keys())

    groups = {'succeeded': {'n_distinct': [], 'margin': [], 'n_impossible': 0, 'n': 0},
              'failed': {'n_distinct': [], 'margin': [], 'n_impossible': 0, 'n': 0}}

    for ego_id, ego in personal_networks.items():
        degree = ego.out_degree(interaction_type)
        if degree < threshold:
            continue

        ego_total = ego.total_counts[interaction_type]
        ts_values = [
            frequency_tie_strength(data, ego_total, interaction_type)
            for data in ego.interactions.values()
            if data.counts[interaction_type] > 0
        ]

        n_distinct = len(set(ts_values))
        k_min, k_max = get_ring_interval(len(ts_values))
        margin = n_distinct - k_min  # negative or zero means structurally impossible

        group = 'succeeded' if ego_id in succeeded_ids else 'failed'
        groups[group]['n'] += 1
        groups[group]['n_distinct'].append(n_distinct)
        groups[group]['margin'].append(margin)
        if n_distinct < k_min:
            groups[group]['n_impossible'] += 1

    print(f"Interaction type: {interaction_type}\n")
    for group_name in ('succeeded', 'failed'):
        data = groups[group_name]
        n = data['n']
        print(f"--- {group_name} (n={n}) ---")
        if n == 0:
            print("  (no egos in this group)\n")
            continue
        print(f"  Distinct tie strength values: mean={statistics.mean(data['n_distinct']):.1f}, "
              f"median={statistics.median(data['n_distinct']):.0f}")
        print(f"  Margin (distinct values - minimum k required): "
              f"mean={statistics.mean(data['margin']):.1f}, median={statistics.median(data['margin']):.0f}")
        print(f"  Egos with FEWER distinct values than the minimum k required "
              f"(structurally impossible to form that many clusters): "
              f"{data['n_impossible']} ({100 * data['n_impossible'] / n:.1f}%)\n")


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5):
        print(__doc__)
        sys.exit(1)
    threshold = int(sys.argv[4]) if len(sys.argv) == 5 else 50
    analyse(sys.argv[1], sys.argv[2], sys.argv[3], threshold)
