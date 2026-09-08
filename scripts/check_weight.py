"""
check_weight.py

Inspects the raw values of the 'weight' column, grouped by interaction
type, to verify empirically what this column actually contains for
vote/comment/transfer.

Usage:
    python3 check_weight.py <input_csv> [n_sample_rows_per_type]

Example:
    python3 check_weight.py data/raw/steem_vote_comment_transfer_01012017_30062017.csv
    python3 check_weight.py data/raw/steem_transfer_01112018_31052019.csv
"""

import sys
import csv
from collections import defaultdict

def check_weight(input_csv, n_sample=10):
    samples = defaultdict(list)
    stats = defaultdict(lambda: {'n': 0, 'n_zero': 0, 'n_empty': 0, 'distinct': set()})

    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) != 5:
                continue
            source, target, weight, date, interaction_type = row
            s = stats[interaction_type]
            s['n'] += 1
            if weight == '' or weight is None:
                s['n_empty'] += 1
            elif weight in ('0', '0.0'):
                s['n_zero'] += 1
            if len(s['distinct']) < 20:
                s['distinct'].add(weight)
            if len(samples[interaction_type]) < n_sample:
                samples[interaction_type].append(weight)

    for itype, s in stats.items():
        print(f"--- {itype} ---")
        print(f"  Total rows: {s['n']}")
        print(f"  Empty values: {s['n_empty']} ({100*s['n_empty']/s['n']:.2f}%)")
        print(f"  Zero values: {s['n_zero']} ({100*s['n_zero']/s['n']:.2f}%)")
        print(f"  Sample of distinct values (up to 20): {sorted(s['distinct'])[:20]}")
        print(f"  First {n_sample} raw values: {samples[itype]}")
        print()

if __name__ == '__main__':
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        sys.exit(1)
    n_sample = int(sys.argv[2]) if len(sys.argv) == 3 else 10
    check_weight(sys.argv[1], n_sample)
