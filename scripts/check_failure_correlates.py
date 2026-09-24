"""
check_failure_correlates.py

For a given interaction type, splits egos above the alter threshold
into "succeeded" (present in the clustering results pickle) and
"failed" (above threshold but absent from it, due to degenerate
clustering), then compares two things between the two groups:

1. Personal network size (number of alters), mean/median.
2. Coefficient of variation of tie strength (std/mean of an ego's own
   tie strength values), mean/median. A lower CV means values are more
   compressed/homogeneous relative to their scale.

Usage:
    python3 check_failure_correlates.py <personal_networks_pickle> <rings_pickle> <interaction_type> [threshold]

Example:
    python3 check_failure_correlates.py data/processed/personal_networks_filtered.pkl data/processed/rings_vote.pkl vote
    python3 check_failure_correlates.py data/processed/personal_networks_filtered.pkl data/processed/rings_comment.pkl comment
    python3 check_failure_correlates.py data/processed/personal_networks_transfer_filtered.pkl data/processed/rings_transfer.pkl transfer
"""

import sys
import os
import pickle
import statistics

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from personalnetwork.clustering import frequency_tie_strength


def analyse(personal_networks_pickle, rings_pickle, interaction_type, threshold=50):
    with open(personal_networks_pickle, 'rb') as f:
        personal_networks = pickle.load(f)
    with open(rings_pickle, 'rb') as f:
        rings = pickle.load(f)

    succeeded_ids = set(rings.keys())

    groups = {'succeeded': {'n_alters': [], 'cv': []},
              'failed': {'n_alters': [], 'cv': []}}

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

        group = 'succeeded' if ego_id in succeeded_ids else 'failed'
        groups[group]['n_alters'].append(len(ts_values))

        mean_ts = statistics.mean(ts_values)
        std_ts = statistics.pstdev(ts_values) if len(ts_values) > 1 else 0.0
        cv = std_ts / mean_ts if mean_ts > 0 else 0.0
        groups[group]['cv'].append(cv)

    print(f"Interaction type: {interaction_type}\n")
    for group_name in ('succeeded', 'failed'):
        data = groups[group_name]
        n = len(data['n_alters'])
        print(f"--- {group_name} (n={n}) ---")
        if n == 0:
            print("  (no egos in this group)\n")
            continue
        print(f"  Personal network size: mean={statistics.mean(data['n_alters']):.1f}, "
              f"median={statistics.median(data['n_alters']):.0f}")
        print(f"  Coefficient of variation: mean={statistics.mean(data['cv']):.4f}, "
              f"median={statistics.median(data['cv']):.4f}\n")


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5):
        print(__doc__)
        sys.exit(1)
    threshold = int(sys.argv[4]) if len(sys.argv) == 5 else 50
    analyse(sys.argv[1], sys.argv[2], sys.argv[3], threshold)
