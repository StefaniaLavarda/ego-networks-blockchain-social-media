"""
compute_bot_ids.py

Identifica gli account sospetti (bot) a partire dal grafo di
comunicazione gia' costruito (build_graph.py), replicando l'approccio
del relatore: calcola in/out-degree DIRETTAMENTE SUL GRAFO (non dal
CSV grezzo), su TUTTI gli account con out-degree > 0 (nessuna soglia
minima di dimensione), e applica il criterio ratio = 0.0 (validato in
Fase 2, si veda PIPELINE.md: salto di oltre 12x tra ratio=0 e la
fascia immediatamente successiva).

POPOLAZIONE: allineata al relatore. Nel suo notebook, il criterio
in/out-degree e' applicato sull'intero grafo appena costruito, PRIMA
di qualunque soglia dimensionale; la soglia minima per il clustering
(50 nel suo caso, si veda MIN_THRESHOLD_PN_SIZE) viene applicata SOLO
in un secondo momento, su un grafo gia' ripulito dai bot. Qui replica
lo stesso ordine: nessuna soglia di dimensione in questo script, la
soglia per il clustering vive altrove (run_clustering.py).

Uso:
    python3 compute_bot_ids.py <input_graph_pickle> <output_bot_ids.txt> [output_degrees.csv]

Esempio:
    python3 compute_bot_ids.py data/processed/communication_graph.pkl output/bot_ids.txt output/degrees.csv
"""

import sys
import os
import csv
import pickle

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def compute_bot_ids(input_graph_pickle, output_bot_ids, output_degrees_csv=None):
    with open(input_graph_pickle, 'rb') as f:
        G = pickle.load(f)

    print(f"Grafo caricato: {G.number_of_nodes()} nodi, {G.number_of_edges()} archi")

    out_degree = dict(G.out_degree())
    in_degree = dict(G.in_degree())

    suspicious = []
    degrees = {}
    for node in G.nodes():
        od = out_degree.get(node, 0)
        idg = in_degree.get(node, 0)
        ratio = idg / od if od > 0 else 0.0
        degrees[node] = (od, idg, ratio)
        if od > 0 and ratio == 0.0:
            suspicious.append((node, od, idg, ratio))

    suspicious.sort(key=lambda r: -r[1])

    n_with_out_degree = sum(1 for od, _, _ in degrees.values() if od > 0)
    print(f"Account con out_degree > 0 (popolazione controllata per il criterio bot): {n_with_out_degree}")
    print(f"Account sospetti (out_degree > 0, ratio = 0.0): {len(suspicious)}"
          + (f" ({100 * len(suspicious) / n_with_out_degree:.2f}% della popolazione con out_degree > 0)"
             if n_with_out_degree else ""))

    with open(output_bot_ids, 'w') as f:
        for node, _, _, _ in suspicious:
            f.write(f"{node}\n")
    print(f"Lista ID sospetti salvata in {output_bot_ids}")

    if output_degrees_csv:
        with open(output_degrees_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['account_id', 'out_degree', 'in_degree', 'ratio'])
            for node, (od, idg, ratio) in sorted(degrees.items(), key=lambda kv: kv[1][2]):
                writer.writerow([node, od, idg, ratio])
        print(f"Gradi completi salvati in {output_degrees_csv}")


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        sys.exit(1)
    output_degrees_csv = sys.argv[3] if len(sys.argv) == 4 else None
    compute_bot_ids(sys.argv[1], sys.argv[2], output_degrees_csv)
