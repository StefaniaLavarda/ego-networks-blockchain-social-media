"""
tie_strength_by_ring.py

For each clustering algorithm and number of circles found, groups
alters across all egos by their assigned ring and examines the
distribution of tie strength within each ring. Used to verify that
tie strength decreases from the innermost ring (ring 0) to the
outermost one.

Usage:
    python3 tie_strength_by_ring.py <personal_networks_pickle> <rings_pickle> <interaction_type> <output_csv> [output_png_dir]

Example:
    python3 tie_strength_by_ring.py data/processed/personal_networks_filtered.pkl data/processed/rings_vote.pkl vote output/tie_strength_vote.csv figures/
    python3 tie_strength_by_ring.py data/processed/personal_networks_filtered.pkl data/processed/rings_comment.pkl comment output/tie_strength_comment.csv figures/
    python3 tie_strength_by_ring.py data/processed/personal_networks_transfer_filtered.pkl data/processed/rings_transfer.pkl transfer output/tie_strength_transfer.csv figures/
"""

import sys
import os
import pickle
import csv
import statistics
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from personalnetwork.clustering import frequency_tie_strength


def collect_tie_strength_by_ring(personal_networks, rings, interaction_type):
    """
    Returns dict[(algorithm, num_rings, ring)] -> list of tie
    strength values, pooled across all egos sharing that combination.
    """
    grouped = defaultdict(list)

    for ego_id, algo_results in rings.items():
        ego = personal_networks.get(ego_id)
        if ego is None:
            continue
        ego_total = ego.total_counts[interaction_type]
        if ego_total == 0:
            continue

        for algo, data in algo_results.items():
            num_rings = data['num_rings']
            for alter_id, ring in data['alter2ring'].items():
                alter_data = ego.interactions.get(alter_id)
                if alter_data is None:
                    continue
                ts = frequency_tie_strength(alter_data, ego_total, interaction_type)
                grouped[(algo, num_rings, ring)].append(ts)

    return grouped


def summarize(personal_networks_pickle, rings_pickle, interaction_type, output_csv, output_png_dir=None):
    print(f"Loading {personal_networks_pickle}...")
    with open(personal_networks_pickle, 'rb') as f:
        personal_networks = pickle.load(f)
    print(f"Loading {rings_pickle}...")
    with open(rings_pickle, 'rb') as f:
        rings = pickle.load(f)
    print(f"Loaded {len(personal_networks)} personal networks and {len(rings)} clustering results.")
    print("Grouping tie strength by ring...")

    grouped = collect_tie_strength_by_ring(personal_networks, rings, interaction_type)
    print("Grouping done.")

    rows = []
    for (algo, num_rings, ring), values in sorted(grouped.items()):
        rows.append({
            'algorithm': algo,
            'num_rings': num_rings,
            'ring': ring,
            'n_alters': len(values),
            'mean_tie_strength': statistics.mean(values),
            'median_tie_strength': statistics.median(values),
            'std_tie_strength': statistics.pstdev(values) if len(values) > 1 else 0.0,
        })

    with open(output_csv, 'w', newline='') as f:
        writer = csv.DictWriter(
            f, fieldnames=['algorithm', 'num_rings', 'ring', 'n_alters',
                           'mean_tie_strength', 'median_tie_strength', 'std_tie_strength']
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved to {output_csv}")

    print("\nMonotonicity check (mean tie strength should decrease from ring 0 outward):")
    by_algo_numrings = defaultdict(dict)
    for row in rows:
        by_algo_numrings[(row['algorithm'], row['num_rings'])][row['ring']] = row['mean_tie_strength']

    for (algo, num_rings), ring_means in sorted(by_algo_numrings.items()):
        ordered_rings = sorted(ring_means.keys())
        means_in_order = [ring_means[r] for r in ordered_rings]
        is_monotonic = all(means_in_order[i] >= means_in_order[i + 1] for i in range(len(means_in_order) - 1))
        status = "OK" if is_monotonic else "NOT monotonic"
        print(f"  {algo}, {num_rings} rings: {[f'{m:.4f}' for m in means_in_order]} -> {status}")

    if output_png_dir:
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np
            from scipy.stats import gaussian_kde

            algos = sorted(set(k[0] for k in grouped.keys()))
            for algo in algos:
                num_rings_values = sorted(set(k[1] for k in grouped.keys() if k[0] == algo))
                for num_rings in num_rings_values:
                    plt.figure(figsize=(8, 5))
                    for ring in range(num_rings):
                        values = grouped.get((algo, num_rings, ring), [])
                        if len(values) < 2:
                            continue
                        density = gaussian_kde(values)
                        xs = np.linspace(min(values), max(values), 200)
                        plt.plot(xs, density(xs), label=f'ring {ring}')
                    plt.xlabel('tie strength')
                    plt.ylabel('density (log scale)')
                    plt.yscale('log')
                    plt.title(f'{algo}, {num_rings} circles ({interaction_type})')
                    plt.legend()
                    plt.tight_layout()
                    fname = os.path.join(output_png_dir, f'tie_strength_kde_{interaction_type}_{algo}_{num_rings}.png')
                    plt.savefig(fname, dpi=150)
                    plt.close()
                    print(f"Saved plot to {fname}")
        except ImportError as e:
            print(f"\nPlotting libraries not available ({e}) -- plots not generated, but the CSV is ready.")


if __name__ == '__main__':
    if len(sys.argv) not in (5, 6):
        print(__doc__)
        sys.exit(1)
    output_png_dir = sys.argv[5] if len(sys.argv) == 6 else None
    summarize(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], output_png_dir)
