"""
check_bot_overlap.py

Counts how many egos with an in/out-degree ratio of 0 (the most
suspicious behaviour: no reciprocity observed) still reach the 50-alter
threshold used for clustering, i.e. how many suspected bots would have
entered the results if left unfiltered.

Usage:
    python3 check_bot_overlap.py <bot_scores.csv> [threshold]

Example:
    python3 check_bot_overlap.py output/bot_scores.csv
    python3 check_bot_overlap.py output/bot_scores.csv 50
"""

import sys
import csv


def check_overlap(bot_scores_csv, threshold=50):
    total = 0
    above_threshold_total = 0
    suspicious = []

    with open(bot_scores_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            out_degree = int(row['out_degree'])
            ratio = float(row['ratio'])

            if out_degree >= threshold:
                above_threshold_total += 1
                if ratio == 0.0:
                    suspicious.append((row['ego_id'], out_degree))

    print(f"Total egos in file: {total}")
    print(f"Egos with out_degree >= {threshold} (population subject to clustering): {above_threshold_total}")
    print(f"Of these, egos with ratio = 0.0 (no reciprocity, most suspicious): {len(suspicious)} "
          f"({100 * len(suspicious) / above_threshold_total:.2f}% of the population above threshold)")

    suspicious.sort(key=lambda x: -x[1])
    print(f"\nTop 20 by out_degree among these:")
    for ego_id, od in suspicious[:20]:
        print(f"  {ego_id}: out_degree={od}")

    # Detailed distribution in the low range (0-0.1), to see whether
    # the natural gap in the distribution sits exactly at ratio=0 or
    # slightly further along, before fixing a final threshold.
    print(f"\nDetailed ratio distribution in the 0-0.1 range "
          f"(egos with out_degree >= {threshold} only):")
    bins = [0.0, 0.01, 0.02, 0.03, 0.05, 0.07, 0.1]
    ratios_above_threshold = []
    with open(bot_scores_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row['out_degree']) >= threshold:
                ratios_above_threshold.append(float(row['ratio']))
    for i in range(len(bins) - 1):
        lo, hi = bins[i], bins[i + 1]
        if i == 0:
            count = sum(1 for r in ratios_above_threshold if r == lo)
            print(f"  ratio = {lo}: {count} egos")
        else:
            count = sum(1 for r in ratios_above_threshold if lo < r <= hi)
            print(f"  {lo} < ratio <= {hi}: {count} egos")


if __name__ == '__main__':
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        sys.exit(1)
    threshold = int(sys.argv[2]) if len(sys.argv) == 3 else 50
    check_overlap(sys.argv[1], threshold)
