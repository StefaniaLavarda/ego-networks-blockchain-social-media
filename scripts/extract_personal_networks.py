"""
extract_personal_networks.py

Reads a raw Steemit interaction CSV (source, target, weight, date,
type) and builds one EgoInteractions object per ego, using interaction
frequency only (weight and date are read but not used).

Personal networks are built with a dictionary lookup, without
assuming the file is sorted by source.

Bot filtering (optional third argument): if a file of suspicious
account IDs is given (produced by compute_bot_ids.py), accounts in
that list are excluded during reading, before any EgoInteractions
object is created for them. Since a suspicious account has zero
in-degree by construction, it never appears as an alter in another
ego's personal network, so excluding it as a source is sufficient.

If the third argument is omitted, all egos are extracted with no
filtering, e.g. to build an unfiltered baseline for comparison.

This script is run once per dataset, since vote/comment and transfer
come from two separate raw files.

Usage:
    python3 extract_personal_networks.py <input_csv> <output_pickle> [exclude_ids_file]

Example:
    python3 extract_personal_networks.py data/raw/steem_vote_comment_transfer_01012017_30062017.csv data/processed/personal_networks_filtered.pkl output/bot_ids.txt
    python3 extract_personal_networks.py data/raw/steem_transfer_01112018_31052019.csv data/processed/personal_networks_transfer_filtered.pkl output/bot_ids_transfer.txt

Example (no filtering, for a before/after comparison):
    python3 extract_personal_networks.py data/raw/steem_vote_comment_transfer_01012017_30062017.csv data/processed/personal_networks_unfiltered.pkl
"""

import sys
import os
import csv
import pickle
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from personalnetwork import EgoInteractions, INTERACTION_TYPES


def load_excluded_ids(exclude_ids_file):
    with open(exclude_ids_file, 'r') as f:
        return set(line.strip() for line in f if line.strip())


def extract(input_csv, output_pickle, exclude_ids_file=None):
    excluded_ids = load_excluded_ids(exclude_ids_file) if exclude_ids_file else set()
    if exclude_ids_file:
        print(f"Excluded accounts on input (bots, from {exclude_ids_file}): {len(excluded_ids)}")

    personal_networks = {}
    n_total = 0
    n_skipped_invalid = 0
    n_self_loop = defaultdict(int)
    n_excluded = 0

    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        print(f"Header: {header}")

        for row in reader:
            n_total += 1
            if len(row) != 5:
                n_skipped_invalid += 1
                continue

            source, target, weight, date, interaction_type = row

            if interaction_type not in INTERACTION_TYPES:
                n_skipped_invalid += 1
                continue

            # Self-loops are excluded here, consistently with
            # build_graph.py, and counted separately from other
            # invalid rows, by interaction type.
            if source == target:
                n_self_loop[interaction_type] += 1
                continue

            # Bot filtering happens here, before any EgoInteractions
            # object is built for the account.
            if source in excluded_ids:
                n_excluded += 1
                continue

            if source not in personal_networks:
                personal_networks[source] = EgoInteractions(source)

            personal_networks[source].process_interaction(target, interaction_type)

            if n_total % 5000000 == 0:
                print(f"  ...{n_total} rows processed, {len(personal_networks)} egos found so far")

    n_self_loop_total = sum(n_self_loop.values())
    print(f"\nDone. Total rows: {n_total}, "
          f"discarded (malformed/invalid type): {n_skipped_invalid}")
    print(f"Self-loops excluded (source == target), by type:")
    for itype in INTERACTION_TYPES:
        print(f"  {itype}: {n_self_loop.get(itype, 0)}")
    print(f"  total self-loops: {n_self_loop_total}")
    print(f"Excluded (bots): {n_excluded}, unique egos: {len(personal_networks)}")

    with open(output_pickle, 'wb') as f:
        pickle.dump(personal_networks, f)
    print(f"Saved to {output_pickle}")


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        sys.exit(1)
    exclude_ids_file = sys.argv[3] if len(sys.argv) == 4 else None
    extract(sys.argv[1], sys.argv[2], exclude_ids_file)
