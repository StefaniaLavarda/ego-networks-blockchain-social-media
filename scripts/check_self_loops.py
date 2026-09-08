"""
check_self_loops.py

Counts how many rows of a raw CSV have source == target (self-loop),
broken down by interaction type.

This script is run once per dataset, since vote/comment and transfer
come from two separate raw files.

Usage:
    python3 check_self_loops.py <input_csv>

Example:
    python3 check_self_loops.py data/raw/steem_vote_comment_transfer_01012017_30062017.csv
    python3 check_self_loops.py data/raw/steem_transfer_01112018_31052019.csv
"""

import sys
import csv
from collections import defaultdict

def check_self_loops(input_csv):
    n_total = defaultdict(int)
    n_self_loop = defaultdict(int)
    self_loop_examples = defaultdict(list)

    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) != 5:
                continue
            source, target, weight, date, interaction_type = row
            n_total[interaction_type] += 1
            if source == target:
                n_self_loop[interaction_type] += 1
                if len(self_loop_examples[interaction_type]) < 5:
                    self_loop_examples[interaction_type].append((source, weight, date))

    print("Self-loops (source == target) by interaction type:\n")
    for itype in n_total:
        n = n_self_loop.get(itype, 0)
        tot = n_total[itype]
        pct = 100 * n / tot
