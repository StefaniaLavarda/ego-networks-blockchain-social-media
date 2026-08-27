"""
run_clustering.py

Esegue il clustering adattivo (GMM, X-means, Jenks) per identificare le
cerchie di Dunbar, su un singolo tipo di interazione alla volta (per la
decisione di trattare i tipi separatamente -- vedi PIPELINE.md, Fase 6).

Seleziona solo gli ego che superano la soglia minima di alter per quel
tipo specifico di interazione, calcola la tie strength basata su
frequenza, ed esegue tutti e tre gli algoritmi di clustering in
parallelo (uno per ego).

Uso:
    python3 run_clustering.py <input_pickle> <interaction_type> <output_pickle> [soglia]

Esempio:
    python3 run_clustering.py data/processed/personal_networks.pkl vote data/processed/rings_vote.pkl
    python3 run_clustering.py data/processed/personal_networks.pkl comment data/processed/rings_comment.pkl
"""

import sys
import os
import pickle

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# NOTA: il patch per l'incompatibilita' numpy.warnings/pyclustering ora
# vive dentro personalnetwork/clustering/__init__.py (non qui), perche'
# deve essere rieseguito in ogni processo worker di joblib -- vedi il
# commento in quel file per i dettagli.

from personalnetwork import INTERACTION_TYPES
from personalnetwork.clustering import (
    frequency_tie_strength,
    rings_identification,
    gaussian_mm_clustering,
    xmeans_clustering,
    jenks_clustering,
)
from joblib import Parallel, delayed
from tqdm import tqdm


def run_clustering(input_pickle, interaction_type, output_pickle, threshold=50):
    if interaction_type not in INTERACTION_TYPES:
        print(f"Tipo di interazione non valido: {interaction_type}. Validi: {INTERACTION_TYPES}")
        sys.exit(1)

    with open(input_pickle, 'rb') as f:
        personal_networks = pickle.load(f)

    # Seleziona solo gli ego sopra soglia per QUESTO specifico tipo di
    # interazione, e calcola la tie strength (frequenza) solo su quel tipo.
    ego_tie_strength = {}
    for ego_id, ego in personal_networks.items():
        degree = ego.out_degree(interaction_type)
        if degree >= threshold:
            ego_total = ego.total_counts[interaction_type]
            ts = {
                alter: frequency_tie_strength(data, ego_total, interaction_type)
                for alter, data in ego.interactions.items()
                if data.counts[interaction_type] > 0
            }
            ego_tie_strength[ego_id] = ts

    print(f"Tipo di interazione: {interaction_type}")
    print(f"Ego selezionati per il clustering (>= {threshold} alter): {len(ego_tie_strength)}")

    if len(ego_tie_strength) == 0:
        print("Nessun ego sopra soglia -- interrompo.")
        sys.exit(1)

    cluster_functions = {
        'gmm': gaussian_mm_clustering,
        'xmeans': xmeans_clustering,
        'jenks': jenks_clustering,
    }

    print("Eseguo il clustering in parallelo...")
    with Parallel(n_jobs=-1) as parallel:
        results = parallel(
            delayed(rings_identification)(ego, ts, cluster_functions)
            for ego, ts in tqdm(ego_tie_strength.items())
        )

    # rings_identification restituisce una tupla (ego, output) in caso di
    # successo, o solo l'id dell'ego (stringa) in caso di errore -- si
    # filtrano via questi ultimi.
    rings = dict(r for r in results if isinstance(r, tuple))
    n_errors = len(results) - len(rings)
    if n_errors:
        print(f"Attenzione: {n_errors} ego hanno dato errore durante il clustering (esclusi dal risultato).")

    with open(output_pickle, 'wb') as f:
        pickle.dump(rings, f)
    print(f"Salvato in {output_pickle} ({len(rings)} ego con risultati validi)")


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5):
        print(__doc__)
        sys.exit(1)
    threshold = int(sys.argv[4]) if len(sys.argv) == 5 else 50
    run_clustering(sys.argv[1], sys.argv[2], sys.argv[3], threshold)
