"""
plot_nmi_distribution.py

Plots the distribution of NMI values between vote-based and
comment-based circle assignment, from the CSV produced by
compare_vote_comment.py. One curve per clustering algorithm.

Usage:
    python3 plot_nmi_distribution.py <comparison_csv> <output_png>

Example:
    python3 plot_nmi_distribution.py output/vote_comment_comparison.csv figures/nmi_distribution.png
"""

import sys
import csv
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def plot_nmi_distribution(comparison_csv, output_png):
    nmi_by_algo = defaultdict(list)

    with open(comparison_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            nmi_by_algo[row['algorithm']].append(float(row['nmi']))

    plt.figure(figsize=(8, 5))
    for algo, values in sorted(nmi_by_algo.items()):
        values_sorted = np.sort(values)
        cdf_y = np.arange(1, len(values_sorted) + 1) / len(values_sorted)
        plt.plot(values_sorted, cdf_y, label=algo)

    plt.xlabel('Normalized Mutual Information')
    plt.ylabel('CDF')
    plt.title('Distribution of NMI between vote-based and comment-based circles')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_png, dpi=150)
    print(f"Saved to {output_png}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    plot_nmi_distribution(sys.argv[1], sys.argv[2])
