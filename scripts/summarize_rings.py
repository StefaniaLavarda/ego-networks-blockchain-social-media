"""
summarize_rings.py

Riepiloga i risultati del clustering (output di run_clustering.py):
per ciascun algoritmo, mostra quanti ego convergono su ciascun numero
di cerchie, il silhouette score medio, e una tabella con dimensione
media/deviazione standard di ciascuna cerchia (stile Tabella 3/4 del
Support Information di Zignani et al.).

Uso:
    python3 summarize_rings.py <input_pickle> [output_csv] [soglia_min_network]

Esempio:
    python3 summarize_rings.py data/processed/rings_vote.pkl
    python3 summarize_rings.py data/processed/rings_vote.pkl output/tabella_vote.csv
"""

import sys
import os
import pickle
import numpy as np
from collections import Counter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from personalnetwork import ring_size_to_table


def summarize(input_pickle, output_csv=None, min_network_size=50):
    with open(input_pickle, 'rb') as f:
        rings = pickle.load(f)

    print(f"Ego totali con risultati di clustering: {len(rings)}\n")

    algo_names = set()
    for ego_data in rings.values():
        algo_names.update(ego_data.keys())

    for algo in sorted(algo_names):
        num_rings_list = [ego_data[algo]['num_rings'] for ego_data in rings.values() if algo in ego_data]
        silhouettes = [ego_data[algo]['silhouette'] for ego_data in rings.values() if algo in ego_data]
        counter = Counter(num_rings_list)
        total = len(num_rings_list)

        print(f"--- {algo} ---")
        print(f"Ego processati: {total}")
        print(f"Silhouette medio: {np.mean(silhouettes):.3f} (std: {np.std(silhouettes):.3f})")
        print("Distribuzione numero di cerchie:")
        for k in sorted(counter.keys()):
            pct = 100 * counter[k] / total
            print(f"  {k} cerchie: {counter[k]} ego ({pct:.1f}%)")
        print()

    # Tabella dimensioni cerchie, stile Tabella 3/4 Zignani et al.
    # L'intervallo 3-6 copre l'intero range del vincolo adattivo
    # (get_ring_interval: da 50-99 alter a >=300 alter).
    intervals = range(3, 7)
    table = ring_size_to_table(rings, intervals, min_network_size)
    print("--- Tabella riepilogativa dimensioni cerchie ---")
    print(table.to_string(index=False))

    if output_csv:
        table.to_csv(output_csv, index=False)
        print(f"\nTabella salvata in {output_csv}")


if __name__ == '__main__':
    if len(sys.argv) not in (2, 3, 4):
        print(__doc__)
        sys.exit(1)
    output_csv = sys.argv[2] if len(sys.argv) >= 3 else None
    min_network_size = int(sys.argv[3]) if len(sys.argv) == 4 else 50
    summarize(sys.argv[1], output_csv, min_network_size)
