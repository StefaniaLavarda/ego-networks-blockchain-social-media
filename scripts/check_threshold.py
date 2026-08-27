"""
check_threshold.py

Analizza le personal network estratte e riporta, per ciascun tipo di
interazione (vote, comment, transfer), quanti ego superano la soglia
minima di alter richiesta per l'analisi (default 50, come nei paper
Zignani et al. -- vedi PIPELINE.md, Fase 4).

Uso:
    python3 check_threshold.py <input_pickle> [soglia]

Esempio:
    python3 check_threshold.py data/processed/personal_networks.pkl
    python3 check_threshold.py data/processed/personal_networks.pkl 50
"""

import sys
import os
import pickle
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from personalnetwork import INTERACTION_TYPES


def check_threshold(input_pickle, threshold=50):
    with open(input_pickle, 'rb') as f:
        personal_networks = pickle.load(f)

    print(f"Ego totali nel dataset: {len(personal_networks)}")
    print(f"Soglia analizzata: >= {threshold} alter\n")

    for interaction_type in INTERACTION_TYPES:
        degrees = [ego.out_degree(interaction_type) for ego in personal_networks.values()]
        degrees = np.array(degrees)

        n_above = np.sum(degrees >= threshold)
        n_with_any = np.sum(degrees > 0)

        print(f"--- {interaction_type} ---")
        print(f"  Ego con almeno 1 interazione di questo tipo: {n_with_any}")
        print(f"  Ego con >= {threshold} alter: {n_above} ({100*n_above/len(personal_networks):.2f}% del totale)")
        if n_with_any > 0:
            active_degrees = degrees[degrees > 0]
            print(f"  Distribuzione (solo ego attivi su questo tipo): "
                  f"mediana={np.median(active_degrees):.0f}, "
                  f"media={np.mean(active_degrees):.1f}, "
                  f"max={np.max(active_degrees)}")
        print()


if __name__ == '__main__':
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        sys.exit(1)
    threshold = int(sys.argv[2]) if len(sys.argv) == 3 else 50
    check_threshold(sys.argv[1], threshold)
