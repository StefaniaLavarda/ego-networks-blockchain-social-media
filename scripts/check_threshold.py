"""
check_threshold.py

Analyses extracted personal networks and reports, for each
interaction type (vote, comment, transfer), how many egos reach the
minimum personal network size required for circle identification
(default 50).

This script is run once per dataset, since vote/comment and transfer
come from two separate raw files.

Usage:
    python3 check_threshold.py <input_pickle> [threshold]

Example:
    python3 check_threshold.py data/processed/personal_networks_filtered.pkl
    python3 check_threshold.py data/processed/personal_networks_transfer_filtered.pkl
"""

import sys
import os
import pickle
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from personalnetwork import INTERACTION_TYPES


def check_threshold(input_pickle, threshold=50):
    with open(input_pickle, 'rb') as f:
        personal_networks = pickle.load(f)

    print(f"Total egos in dataset: {len(personal_networks)}")
    print(f"Threshold analysed: >= {threshold} alters\n")

    for interaction_type in INTERACTION_TYPES:
        degrees = [ego.out_degree(interaction_type) for ego in personal_networks.values()]
        degrees = np.array(degrees)

        n_above = np.sum(degrees >= threshold)
        n_with_any = np.sum(degrees > 0)

        print(f"--- {interaction_type} ---")
        print(f"  Egos with at least 1 interaction of this type: {n_with_any}")
        print(f"  Egos with >= {threshold} alters: {n_above} ({100*n_above/len(personal_networks):.2f}% of total)")
        if n_with_any > 0:
            active_degrees = degrees[degrees > 0]
            print(f"  Distribution (active egos only): "
                  f"median={np.median(active_degrees):.0f}, "
                  f"mean={np.mean(active_degrees):.1f}, "
                  f"max={np.max(active_degrees)}")
        print()


if __name__ == '__main__':
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        sys.exit(1)
    threshold = int(sys.argv[2]) if len(sys.argv) == 3 else 50
    check_threshold(sys.argv[1], threshold)
