"""
plot_circle_count_distribution.py

Plots a grouped bar chart of the percentage of egos converging on
each number of circles, comparing vote, comment, and transfer, for a
single chosen algorithm.

Usage:
    python3 plot_circle_count_distribution.py <rings_vote_pickle> <rings_comment_pickle> <rings_transfer_pickle> <algorithm> <output_png>

Example:
    python3 plot_circle_count_distribution.py data/processed/rings_vote.pkl data/processed/rings_comment.pkl data/processed/rings_transfer.pkl gmm figures/circle_count_distribution_gmm.png
"""

import sys
import pickle
from collections import Counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def get_distribution(rings_pickle, algorithm):
    with open(rings_pickle, 'rb') as f:
        rings = pickle.load(f)

    num_rings_list = [
        ego_data[algorithm]['num_rings']
        for ego_data in rings.values()
        if algorithm in ego_data
    ]
    total = len(num_rings_list)
    counter = Counter(num_rings_list)
    return counter, total


def plot_circle_count_distribution(rings_vote, rings_comment, rings_transfer, algorithm, output_png):
    counter_vote, n_vote = get_distribution(rings_vote, algorithm)
    counter_comment, n_comment = get_distribution(rings_comment, algorithm)
    counter_transfer, n_transfer = get_distribution(rings_transfer, algorithm)

    all_circle_counts = sorted(set(counter_vote) | set(counter_comment) | set(counter_transfer))

    pct_vote = [100 * counter_vote.get(k, 0) / n_vote for k in all_circle_counts]
    pct_comment = [100 * counter_comment.get(k, 0) / n_comment for k in all_circle_counts]
    pct_transfer = [100 * counter_transfer.get(k, 0) / n_transfer for k in all_circle_counts]

    x = np.arange(len(all_circle_counts))
    width = 0.25

    plt.figure(figsize=(8, 5))
    plt.bar(x - width, pct_vote, width, label=f'vote (n={n_vote})')
    plt.bar(x, pct_comment, width, label=f'comment (n={n_comment})')
    plt.bar(x + width, pct_transfer, width, label=f'transfer (n={n_transfer})')

    plt.xlabel('Number of circles')
    plt.ylabel('Percentage of egos')
    plt.title(f'Distribution of the number of circles ({algorithm.upper()})')
    plt.xticks(x, all_circle_counts)
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(output_png, dpi=150)
    print(f"Saved to {output_png}")


if __name__ == '__main__':
    if len(sys.argv) != 6:
        print(__doc__)
        sys.exit(1)
    plot_circle_count_distribution(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
