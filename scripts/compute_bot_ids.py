"""
compute_bot_ids.py

Identifies suspicious (bot) accounts from an already-built
communication graph (build_graph.py). In-degree and out-degree are
computed directly on the graph, for every account with a positive
out-degree, with no minimum personal network size. An account is
flagged as suspicious if its in/out-degree ratio is 0.0, a threshold
identified from a clear gap in the empirical distribution of this
ratio (see PIPELINE.md).

The minimum personal network size used for clustering is applied
separately, later in the pipeline (run_clustering.py), not here.

Usage:
    python3 compute_bot_ids.py data/processed/communication_graph.pkl output/bot_ids.txt output/degrees.csv
    python3 compute_bot_ids.py data/processed/communication_graph_transfer.pkl output/bot_ids_transfer.txt output/degrees_transfer.csv
"""

import sys
import os
import csv
import pickle

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def compute_bot_ids(input_graph_pickle, output_bot_ids, output_degrees_csv=None):
    with open(input_graph_pickle, 'rb') as f:
        G = pickle.load(f)

    print(f"Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    out_degree = dict(G.out_degree())
    in_degree = dict(G.in_degree())

    suspicious = []
    degrees = {}
    for node in G.nodes():
        od = out_degree.get(node, 0)
        idg = in_degree.get(node, 0)
        ratio = idg / od if od > 0 else 0.0
        degrees[node] = (od, idg, ratio)
        if od > 0 and ratio == 0.0:
            suspicious.append((node, od, idg, ratio))

    suspicious.sort(key=lambda r: -r[1])

    n_with_out_degree = sum(1 for od, _, _ in degrees.values() if od > 0)
    print(f"Accounts with out_degree > 0 (population checked for the bot criterion): {n_with_out_degree}")
    print(f"Suspicious accounts (out_degree > 0, ratio = 0.0): {len(suspicious)}"
          + (f" ({100 * len(suspicious) / n_with_out_degree:.2f}% of accounts with out_degree > 0)"
             if n_with_out_degree else ""))

    with open(output_bot_ids, 'w') as f:
        for node, _, _, _ in suspicious:
            f.write(f"{node}\n")
    print(f"Suspicious account IDs saved to {output_bot_ids}")

    if output_degrees_csv:
        with open(output_degrees_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['account_id', 'out_degree', 'in_degree', 'ratio'])
            for node, (od, idg, ratio) in sorted(degrees.items(), key=lambda kv: kv[1][2]):
                writer.writerow([node, od, idg, ratio])
        print(f"Full degree data saved to {output_degrees_csv}")


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        sys.exit(1)
    output_degrees_csv = sys.argv[3] if len(sys.argv) == 4 else None
    compute_bot_ids(sys.argv[1], sys.argv[2], output_degrees_csv)
