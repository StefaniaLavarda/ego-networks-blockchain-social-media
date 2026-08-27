"""
compute_bot_scores.py

Fase diagnostica per il filtraggio di account sospetti/bot -- replica
l'approccio del relatore (rapporto in-degree/out-degree, soglia scelta
visivamente da un grafico CDF) ma sui dati Steemit reali, PRIMA di
scegliere una soglia (vedi PIPELINE.md, Fase 2: "replicate the
professor's diagnostic first... purely to see whether the same visual
pattern appears").

Per ogni ego in personal_networks.pkl calcola:
  - out_degree: numero di alter distinti contattati (gia' disponibile
    via EgoInteractions.out_degree())
  - in_degree: numero di account distinti che hanno interagito CON
    quell'ego (va calcolato invertendo la struttura -- non
    memorizzato direttamente in EgoInteractions, che e' organizzata
    per ego come sorgente)
  - ratio = in_degree / out_degree

Salva un CSV con questi valori per ogni ego, un grafico CDF del
rapporto (in figures/), e stampa un riepilogo per percentili per un
primo sguardo senza dover aprire il grafico.

Uso:
    python3 compute_bot_scores.py <personal_networks.pkl> <output_csv> [output_png] [interaction_type]

Esempio (tutti i tipi combinati, come il metodo originale del relatore):
    python3 compute_bot_scores.py data/processed/personal_networks.pkl output/bot_scores.csv figures/bot_ratio_cdf.png

Esempio (solo un tipo specifico):
    python3 compute_bot_scores.py data/processed/personal_networks.pkl output/bot_scores_vote.csv figures/bot_ratio_cdf_vote.png vote
"""

import sys
import os
import pickle
import csv
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from personalnetwork import INTERACTION_TYPES


def compute_degrees(personal_networks, interaction_type=None):
    """
    Calcola out-degree e in-degree per ogni ego.

    interaction_type=None: combina tutti i tipi (unione degli alter
    distinti su vote/comment/transfer), replicando l'approccio originale
    del relatore su calls+texts combinati.
    interaction_type='vote' (o altro): calcola solo su quel tipo.
    """
    types_to_use = [interaction_type] if interaction_type else INTERACTION_TYPES

    out_degree = {}
    in_degree_sources = defaultdict(set)  # alter_id -> set di ego che l'hanno contattato

    for ego_id, ego in personal_networks.items():
        # out-degree: alter distinti raggiunti da questo ego, su questi tipi
        alters_reached = set()
        for alter_id, alter_data in ego.interactions.items():
            if any(alter_data.counts[t] > 0 for t in types_to_use):
                alters_reached.add(alter_id)
                in_degree_sources[alter_id].add(ego_id)
        out_degree[ego_id] = len(alters_reached)

    in_degree = {ego_id: len(in_degree_sources.get(ego_id, set())) for ego_id in personal_networks.keys()}

    return out_degree, in_degree


def compute_bot_scores(input_pickle, output_csv, output_png=None, interaction_type=None):
    with open(input_pickle, 'rb') as f:
        personal_networks = pickle.load(f)

    print(f"Calcolo in/out-degree per {len(personal_networks)} ego "
          f"({'tutti i tipi combinati' if interaction_type is None else interaction_type})...")

    out_degree, in_degree = compute_degrees(personal_networks, interaction_type)

    rows = []
    for ego_id in personal_networks.keys():
        od = out_degree[ego_id]
        idg = in_degree[ego_id]
        ratio = idg / od if od > 0 else 0.0
        rows.append((ego_id, od, idg, ratio))

    rows.sort(key=lambda r: r[3])  # ordina per ratio, come nel CDF del relatore

    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ego_id', 'out_degree', 'in_degree', 'ratio'])
        writer.writerows(rows)
    print(f"Salvato in {output_csv}")

    ratios = [r[3] for r in rows]
    print("\nRiepilogo del rapporto in-degree/out-degree (percentili):")
    import statistics
    n = len(ratios)
    for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
        idx = min(int(n * p / 100), n - 1)
        print(f"  {p}° percentile: {ratios[idx]:.4f}")
    print(f"  Media: {statistics.mean(ratios):.4f}")

    if output_png:
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np

            cdf_y = np.arange(1, n + 1) / n
            plt.figure(figsize=(8, 5))
            plt.plot(ratios, cdf_y)
            # NOTA: scala 'symlog', non 'log' -- una scala log pura non puo'
            # rappresentare il valore 0 (log(0) non esiste), e lo escluderebbe
            # silenziosamente dal grafico. Un bot con in_degree=0 (nessuno lo
            # ricambia mai) avrebbe ratio esattamente 0 -- proprio il caso piu'
            # importante da vedere. 'symlog' gestisce correttamente lo zero
            # (lineare vicino a 0, logaritmica altrove).
            plt.xscale('symlog', linthresh=0.01)
            plt.xlabel('in-degree / out-degree ratio')
            plt.ylabel('CDF')
            plt.title('Distribuzione del rapporto in/out-degree'
                       + ('' if interaction_type is None else f' ({interaction_type})'))
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(output_png, dpi=150)
            print(f"\nGrafico CDF salvato in {output_png}")
        except ImportError:
            print("\nmatplotlib non disponibile -- grafico non generato, ma il CSV e' pronto per l'analisi.")


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4, 5):
        print(__doc__)
        sys.exit(1)
    output_png = sys.argv[3] if len(sys.argv) >= 4 else None
    interaction_type = sys.argv[4] if len(sys.argv) == 5 else None
    compute_bot_scores(sys.argv[1], sys.argv[2], output_png, interaction_type)
