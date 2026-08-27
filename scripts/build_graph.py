"""
build_graph.py

Costruisce un unico grafo diretto (networkx.DiGraph) dal CSV grezzo,
seguendo l'approccio del relatore (si veda il suo notebook, celle
4-9): un solo oggetto grafo, con un arco per ogni coppia (source,
target) osservata, e un attributo di peso separato per ciascun tipo
di interazione (c_vote, c_comment, c_transfer) sullo stesso arco --
non un grafo per tipo.

Questa scelta e' motivata da due esigenze che, con tre grafi separati,
richiederebbero di ricombinare informazione sparsa su piu' oggetti:
  - il bot detection (Sezione 3.2.2) richiede il grado COMBINATO su
    tutti e tre i tipi di interazione, esattamente come nel notebook
    del relatore (che calcola il grado su call+sms insieme, mai per
    canale separato). Con un solo grafo, G.out_degree()/G.in_degree()
    restituiscono gia' questo conteggio combinato automaticamente.
  - il clustering (Sezione 3.5) richiede invece i tre tipi separati:
    per questo, quando si estrae la personal network di un ego, si
    legge solo l'attributo di peso specifico del tipo di interazione
    in analisi (es. c_vote), ignorando gli altri due.

SELF-LOOP: le righe con source == target (es. un self-vote su
Steemit) vengono scartate qui, coerentemente con
extract_personal_networks.py. Vengono contate SEPARATAMENTE dagli
altri scarti (righe malformate, tipo non valido) e per tipo di
interazione, perche' non sono uno scarto "tecnico" ma un'esclusione
motivata teoricamente (un self-loop non e' una relazione ego-alter,
si veda Sezione 3.3.1) -- il conteggio preciso per tipo serve da
statistica descrittiva per il Cap. 4 (es. il self-vote come strategia
di reward, gia' documentata in letteratura).

Uso:
    python3 build_graph.py <input_csv> <output_graph_pickle>

Esempio:
    python3 build_graph.py data/raw/steem_....csv data/processed/communication_graph.pkl
"""

import sys
import os
import csv
import pickle
import networkx as nx
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from personalnetwork import INTERACTION_TYPES


def build_graph(input_csv, output_pickle):
    communication_graph = nx.DiGraph()
    n_total = 0
    n_skipped_invalid = 0
    n_self_loop = defaultdict(int)

    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        print(f"Header: {header}")

        for row in reader:
            n_total += 1
            if len(row) != 5:
                n_skipped_invalid += 1
                continue

            source, target, weight, date, interaction_type = row

            if interaction_type not in INTERACTION_TYPES:
                n_skipped_invalid += 1
                continue

            if source == target:
                n_self_loop[interaction_type] += 1
                continue

            attr_name = f'c_{interaction_type}'
            if communication_graph.has_edge(source, target):
                communication_graph[source][target][attr_name] = \
                    communication_graph[source][target].get(attr_name, 0) + 1
            else:
                communication_graph.add_edge(source, target, **{attr_name: 1})

            if n_total % 5000000 == 0:
                print(f"  ...{n_total} righe processate, "
                      f"{communication_graph.number_of_nodes()} nodi finora")

    n_self_loop_total = sum(n_self_loop.values())
    print(f"\nFatto. Righe totali: {n_total}, scartate (malformate/tipo non valido): {n_skipped_invalid}")
    print(f"Self-loop esclusi (source == target), per tipo:")
    for itype in INTERACTION_TYPES:
        print(f"  {itype}: {n_self_loop.get(itype, 0)}")
    print(f"  totale self-loop: {n_self_loop_total}")
    print(f"Nodi: {communication_graph.number_of_nodes()}, "
          f"archi: {communication_graph.number_of_edges()}")

    with open(output_pickle, 'wb') as f:
        pickle.dump(communication_graph, f)
    print(f"Salvato in {output_pickle}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    build_graph(sys.argv[1], sys.argv[2])
