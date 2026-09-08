"""
filter_suspicious_accounts.py

Removes suspicious (bot) accounts from an already-built
personal_networks.pkl, using the same criterion as compute_bot_ids.py:
combined out-degree above size_threshold, and in/out-degree ratio of
0.0 (no reciprocity observed).

This script filters an existing, unfiltered pickle rather than the
raw CSV, and is used to produce the before/after comparison pair
needed for the effect of bot filtering on network structure, without
re-reading the full raw file.

Since ratio = 0.0 implies in-degree = 0 by definition, a suspicious
account never appears as an alter in another ego's personal network:
removing it as its own dictionary entry is therefore sufficient.

Usage:
    python3 filter_suspicious_accounts.py <personal_networks.pkl> <output_pickle> [size_threshold]

Example:
    python3 filter_suspicious_accounts.py data/processed/personal_networks_unfiltered.pkl data/processed/personal_networks_filtered.pkl
    python3 filter_suspicious_accounts.py data/processed/personal_networks_transfer_unfiltered.pkl data/processed/personal_networks_transfer_filtered.pkl
"""

import sys
import os
import pickle
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from personalnetwork import INTERACTION_TYPES


def compute_degrees(personal_networks):
    """Combined in/out-degree across all interaction types."""
    out_degree = {}
    in_degree_sources = defaultdict(set)

    for ego_id, ego in personal_networks.items():
        alters_reached = set()
        for alter_id, alter_data in ego.interactions.items():
            if any(alter_data.counts[t] > 0 for t in INTERACTION_TYPES):
                alters_reached.add(alter_id)
                in_degree_sources[alter_id].add(ego_id)
        out_degree[ego_id] = len(alters_reached)

    in_degree = {ego_id: len(in_degree_sources.get(ego_id, set())) for ego_id in personal_networks.keys()}
    return out_degree, in_degree


def filter_suspicious(input_pickle, output_pickle, size_threshold=50):
    with open(input_pickle, 'rb') as f:
        personal_networks = pickle.load(f)

    print(f"Total egos before filtering: {len(personal_networks)}")
    print("Computing in/out-degree to identify suspicious accounts...")

    out_degree, in_degree = compute_degrees(personal_networks)

    suspicious_ids = set()
    for ego_id in personal_networks.keys():
        od = out_degree[ego_id]
        idg = in_degree[ego_id]
        if od >= size_threshold and idg == 0:
            suspicious_ids.add(ego_id)

    print(f"Suspicious accounts identified (out_degree >= {size_threshold}, ratio = 0.0): {len(suspicious_ids)}")

    filtered_networks = {
        ego_id: ego for ego_id, ego in personal_networks.items()
        if ego_id not in suspicious_ids
    }

    print(f"Egos remaining after filtering: {len(filtered_networks)}")

    with open(output_pickle, 'wb') as f:
        pickle.dump(filtered_networks, f)
    print(f"Saved to {output_pickle}")

    excluded_path = output_pickle.replace('.pkl', '_excluded_ids.txt')
    with open(excluded_path, 'w') as f:
        for ego_id in sorted(suspicious_ids, key=lambda x: -out_degree[x]):
            f.write(f"{ego_id}\t{out_degree[ego_id]}\n")
    print(f"List of excluded accounts saved to {excluded_path}")


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        sys.exit(1)
    size_threshold = int(sys.argv[3]) if len(sys.argv) == 4 else 50
    filter_suspicious(sys.argv[1], sys.argv[2], size_threshold)
