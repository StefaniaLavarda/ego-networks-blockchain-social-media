"""
check_self_loops.py

Conta quante righe del CSV grezzo hanno source == target (self-loop),
suddivise per tipo di interazione -- prima di decidere come trattarle
in Sezione 3.3.1, serve sapere quante sono e per quali tipi compaiono,
non solo se compaiono.

Uso:
    python3 check_self_loops.py <input_csv>
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
        next(reader)  # salta header
        for row in reader:
            if len(row) != 5:
                continue
            source, target, weight, date, interaction_type = row
            n_total[interaction_type] += 1
            if source == target:
                n_self_loop[interaction_type] += 1
                if len(self_loop_examples[interaction_type]) < 5:
                    self_loop_examples[interaction_type].append((source, weight, date))

    print("Self-loop (source == target) per tipo di interazione:\n")
    for itype in n_total:
        n = n_self_loop.get(itype, 0)
        tot = n_total[itype]
        pct = 100 * n / tot if tot else 0
        print(f"--- {itype} ---")
        print(f"  Righe totali: {tot}")
        print(f"  Self-loop: {n} ({pct:.4f}%)")
        if self_loop_examples[itype]:
            print(f"  Esempi (account, weight, date): {self_loop_examples[itype]}")
        print()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    check_self_loops(sys.argv[1])
