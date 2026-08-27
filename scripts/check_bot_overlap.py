"""
check_bot_overlap.py

Conta quanti ego con rapporto in/out-degree pari a 0 (comportamento
massimamente sospetto: nessuna reciprocita' osservata) hanno comunque
superato la soglia di 50 alter usata per il clustering -- cioe' quanti
"bot sospetti" sono gia' entrati nei risultati analizzati finora.

Uso:
    python3 check_bot_overlap.py <bot_scores.csv> [soglia]

Esempio:
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

    print(f"Ego totali nel file: {total}")
    print(f"Ego con out_degree >= {threshold} (popolazione soggetta a clustering): {above_threshold_total}")
    print(f"Di questi, ego con ratio = 0.0 (nessuna reciprocita', massimamente sospetti): {len(suspicious)} "
          f"({100 * len(suspicious) / above_threshold_total:.2f}% della popolazione sopra soglia)")

    suspicious.sort(key=lambda x: -x[1])
    print(f"\nTop 20 per out_degree tra questi:")
    for ego_id, od in suspicious[:20]:
        print(f"  {ego_id}: out_degree={od}")

    # Distribuzione dettagliata nella fascia bassa (0-0.1), per capire
    # se il salto naturale nella distribuzione e' esattamente a ratio=0
    # o leggermente piu' in la' -- prima di fissare una soglia definitiva.
    print(f"\nDistribuzione dettagliata del rapporto nella fascia 0-0.1 "
          f"(solo tra gli ego con out_degree >= {threshold}):")
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
            print(f"  ratio = {lo}: {count} ego")
        else:
            count = sum(1 for r in ratios_above_threshold if lo < r <= hi)
            print(f"  {lo} < ratio <= {hi}: {count} ego")


if __name__ == '__main__':
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        sys.exit(1)
    threshold = int(sys.argv[2]) if len(sys.argv) == 3 else 50
    check_overlap(sys.argv[1], threshold)
