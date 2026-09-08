"""
build_graph.py

Builds a single directed graph (networkx.DiGraph) from a raw CSV
interaction file. One edge is created per observed (source, target)
pair, with a separate weight attribute for each interaction type
(c_vote, c_comment, c_transfer) stored on the same edge.

Self-loops (source == target, e.g. a self-vote on Steemit) are
discarded and counted separately, per interaction type, from other
invalid rows (malformed rows, unrecognised interaction type).

This script is run once per dataset, since vote/comment and transfer
come from two separate raw files covering different time periods.
Each run produces its own graph; the two are never merged.

Usage:
    python3 build_graph.py <input_csv> <output_graph_pickle>

Example:
    python3 build_graph.py data/raw/steem_vote_comment_transfer_01012017_30062017.csv data/processed/communication_graph.pkl
    python3 build_graph.py data/raw/steem_transfer_01112018_31052019.csv data/processed/communication_graph_transfer.pkl
"""

import sys
import os
import csv
import pickle
import networkx as nx
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from personalnetwork import INTERACTION_TYPES


def build_graph(input_csv, output_pickle):
    communication_graph = nx.DiGraph()
    n_total = 0
    n_skipped_invalid = 0
    n_self_loop = defaultdict(int)
    types_seen = set()

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

            types_seen.add(interaction_type)

            if source == target:
                n_self_loop[interaction_type] += 1
                continue

            attr_name = f'c_{interaction_type}'
            if communication_graph.has_edge(source, target):
                communication_graph[source][target][attr_name] = \
                    communication_graph[source][target].get(attr_name, 0) + 1
            else:
                communication_graph.add_edge(source, target, **{attr_name: 1})

            if n_total % 5000000 == 0:
                print(f"  ...{n_total} rows processed, "
                      f"{communication_graph.number_of_nodes()} nodes so far")

    n_self_loop_total = sum(n_self_loop.values())
    print(f"\nDone. Total rows: {n_total}, discarded (malformed/invalid type): {n_skipped_invalid}")
    print(f"Interaction types found in this file: {sorted(types_seen)}")
    print(f"Self-loops excluded (source == target), by type:")
    for itype in INTERACTION_TYPES:
        print(f"  {itype}: {n_self_loop.get(itype, 0)}")
    print(f"  total self-loops: {n_self_loop_total}")
    print(f"Nodes: {communication_graph.number_of_nodes()}, "
          f"edges: {communication_graph.number_of_edges()}")

    with open(output_pickle, 'wb') as f:
        pickle.dump(communication_graph, f)
    print(f"Saved to {output_pickle}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    build_graph(sys.argv[1], sys.argv[2])
