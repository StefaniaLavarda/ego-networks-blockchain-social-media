"""
run_clustering.py

Runs adaptive clustering (GMM, X-means, Jenks) to identify Dunbar
circles, for a single interaction type at a time.

Only egos above the minimum personal network size for that specific
interaction type are selected, tie strength is computed from
frequency, and all three clustering algorithms are run in parallel,
one process per ego.

This script is run once per interaction type, and once per dataset for
transfer, since vote/comment and transfer come from two separate raw
files.

Usage:
    python3 run_clustering.py <input_pickle> <interaction_type> <output_pickle> [threshold]

Example:
    python3 run_clustering.py data/processed/personal_networks_filtered.pkl vote data/processed/rings_vote.pkl
    python3 run_clustering.py data/processed/personal_networks_filtered.pkl comment data/processed/rings_comment.pkl
    python3 run_clustering.py data/processed/personal_networks_transfer_filtered.pkl transfer data/processed/rings_transfer.pkl
"""

import sys
import os
import pickle

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from personalnetwork import INTERACTION_TYPES
from personalnetwork.clustering import (
    frequency_tie_strength,
    rings_identification,
    gaussian_mm_clustering,
    xmeans_clustering,
    jenks_clustering,
)
from joblib import Parallel, delayed
from tqdm import tqdm


def run_clustering(input_pickle, interaction_type, output_pickle, threshold=50):
    if interaction_type not in INTERACTION_TYPES:
        print(f"Invalid interaction type: {interaction_type}. Valid types: {INTERACTION_TYPES}")
        sys.exit(1)

    with open(input_pickle, 'rb') as f:
        personal_networks = pickle.load(f)

    # Select only egos above threshold for this specific interaction
    # type, and compute tie strength (frequency) for that type only.
    ego_tie_strength = {}
    for ego_id, ego in personal_networks.items():
        degree = ego.out_degree(interaction_type)
        if degree >= threshold:
            ego_total = ego.total_counts[interaction_type]
            ts = {
                alter: frequency_tie_strength(data, ego_total, interaction_type)
                for alter, data in ego.interactions.items()
                if data.counts[interaction_type] > 0
            }
            ego_tie_strength[ego_id] = ts

    print(f"Interaction type: {interaction_type}")
    print(f"Egos selected for clustering (>= {threshold} alters): {len(ego_tie_strength)}")

    if len(ego_tie_strength) == 0:
        print("No egos above threshold -- stopping.")
        sys.exit(1)

    cluster_functions = {
        'gmm': gaussian_mm_clustering,
        'xmeans': xmeans_clustering,
        'jenks': jenks_clustering,
    }

    print("Running clustering in parallel...")
    with Parallel(n_jobs=-1) as parallel:
        results = parallel(
            delayed(rings_identification)(ego, ts, cluster_functions)
            for ego, ts in tqdm(ego_tie_strength.items())
        )

    # rings_identification returns a (ego, output) tuple on success,
    # or just the ego id (a string) on error -- the latter are
    # filtered out here.
    rings = dict(r for r in results if isinstance(r, tuple))
    n_errors = len(results) - len(rings)
    if n_errors:
        print(f"Warning: {n_errors} egos failed during clustering (excluded from the result).")

    with open(output_pickle, 'wb') as f:
        pickle.dump(rings, f)
    print(f"Saved to {output_pickle} ({len(rings)} egos with valid results)")


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5):
        print(__doc__)
        sys.exit(1)
    threshold = int(sys.argv[4]) if len(sys.argv) == 5 else 50
    run_clustering(sys.argv[1], sys.argv[2], sys.argv[3], threshold)
