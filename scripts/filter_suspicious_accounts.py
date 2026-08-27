"""
filter_suspicious_accounts.py

Rimuove gli account sospetti (bot) da un personal_networks.pkl gia'
costruito, usando il criterio validato: out_degree combinato >=
size_threshold E ratio in/out-degree = 0.0 (nessuna reciprocita'
osservata).

RUOLO NELLA PIPELINE (aggiornato): questo NON e' piu' lo step di
filtraggio principale. Il percorso di produzione ora filtra i bot
PRIMA di costruire le personal network, direttamente dal CSV grezzo
(vedi compute_bot_ids.py + il parametro exclude_ids_file di
extract_personal_networks.py) -- in linea con l'handoff document e il
ToC aggiornato del Cap. 3.

Questo script resta utile per un caso specifico: generare la coppia
"prima/dopo" richiesta in §4.1.1 (effetto del bot filtering sulla
struttura della rete) a partire da un pickle NON filtrato gia'
esistente, senza dover ripassare i 31M di righe del CSV grezzo.

Questa soglia non e' stata scelta arbitrariamente -- e' stata verificata
guardando la distribuzione reale (vedi PIPELINE.md, Fase 2): c'e' un
salto di oltre 12x tra ratio=0 (2739 ego) e la fascia immediatamente
successiva (225 ego), un pattern statisticamente netto, non rumore.

NOTA: dato che ratio=0 implica per definizione in_degree=0, questi
account non compaiono MAI come alter nelle interazioni di altri ego --
rimuoverli come voci proprie del dizionario e' quindi sufficiente,
senza bisogno di ripulire le reti degli altri utenti. Per questo
motivo il risultato di questo script e' matematicamente equivalente a
quello del nuovo percorso "filtra-poi-costruisci": cambia solo QUANDO
il filtro viene applicato, non il risultato finale.

Uso:
    python3 filter_suspicious_accounts.py <personal_networks.pkl> <output_pickle> [size_threshold]

Esempio:
    python3 filter_suspicious_accounts.py data/processed/personal_networks_unfiltered.pkl data/processed/personal_networks_filtered.pkl
"""

import sys
import os
import pickle

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from personalnetwork import INTERACTION_TYPES


def compute_degrees(personal_networks):
    """Stessa logica di compute_bot_scores.py -- degree combinato su tutti i tipi."""
    from collections import defaultdict
    out_degree = {}
    in_degree_sources = defaultdict(set)

    for ego_id, ego in personal_networks.items():
        alters_reached = set()
        for alter_id, alter_data in ego.interactions.items():
            if any(alter_data.counts[t] > 0 for t in INTERACTION_TYPES):
                alters_reached.add(alter_id)
                in_degree_sources[alter_id].add(ego_id)
        out_degree[ego_id] = len(alters_reached)

    in_degree = {ego_id: len(in_degree_sources.get(ego_id, set())) for ego_id in personal_networks.keys()}
    return out_degree, in_degree


def filter_suspicious(input_pickle, output_pickle, size_threshold=50):
    with open(input_pickle, 'rb') as f:
        personal_networks = pickle.load(f)

    print(f"Ego totali prima del filtraggio: {len(personal_networks)}")
    print("Calcolo in/out-degree per identificare account sospetti...")

    out_degree, in_degree = compute_degrees(personal_networks)

    suspicious_ids = set()
    for ego_id in personal_networks.keys():
        od = out_degree[ego_id]
        idg = in_degree[ego_id]
        if od >= size_threshold and idg == 0:
            suspicious_ids.add(ego_id)

    print(f"Account sospetti identificati (out_degree >= {size_threshold}, ratio = 0.0): {len(suspicious_ids)}")

    filtered_networks = {
        ego_id: ego for ego_id, ego in personal_networks.items()
        if ego_id not in suspicious_ids
    }

    print(f"Ego rimanenti dopo il filtraggio: {len(filtered_networks)}")

    with open(output_pickle, 'wb') as f:
        pickle.dump(filtered_networks, f)
    print(f"Salvato in {output_pickle}")

    # Salva anche la lista degli esclusi, utile per la sezione di
    # preprocessing/limitazioni della tesi (es. per citare esempi concreti)
    excluded_path = output_pickle.replace('.pkl', '_excluded_ids.txt')
    with open(excluded_path, 'w') as f:
        for ego_id in sorted(suspicious_ids, key=lambda x: -out_degree[x]):
            f.write(f"{ego_id}\t{out_degree[ego_id]}\n")
    print(f"Lista degli account esclusi salvata in {excluded_path}")


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        sys.exit(1)
    size_threshold = int(sys.argv[3]) if len(sys.argv) == 4 else 50
    filter_suspicious(sys.argv[1], sys.argv[2], size_threshold)
