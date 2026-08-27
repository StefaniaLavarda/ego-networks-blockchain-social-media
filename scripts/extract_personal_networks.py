"""
extract_personal_networks.py

Legge il CSV Steemit (source,target,weight,date,type) e costruisce le
personal network (EgoInteractions) per ogni ego, usando solo la
frequenza (weight e date vengono ignorati, come da indicazione del
relatore).

Usa un lookup a dizionario (non assume che il file sia ordinato per
source) -- scelta deliberata: con 31M righe (molte meno delle ~90M+
viste in precedenza con SteemOps) possiamo permetterci la maggiore
robustezza senza problemi di performance.

FILTRAGGIO BOT (opzionale, terzo argomento): se viene passato un file
di ID sospetti (prodotto da compute_bot_ids.py, eseguito PRIMA di
questo script sullo stesso CSV grezzo), gli account presenti in quella
lista vengono esclusi qui, durante la lettura -- non viene costruita
alcuna EgoInteractions per loro. Questo e' il nuovo ordine della
pipeline: filtra prima, costruisci dopo (in linea con l'handoff
document e il ToC aggiornato del Cap. 3). Non serve ripulire
separatamente le reti degli altri ego: dato che ratio=0 implica
in_degree=0 per definizione, un account escluso qui non compare mai
come target (alter) nelle interazioni di nessun altro ego.

Se il terzo argomento viene omesso, lo script si comporta come prima
(estrae tutti gli ego, nessun filtro) -- utile ad es. per costruire la
baseline "prima del filtraggio" richiesta in §4.1.1.

Uso:
    python3 extract_personal_networks.py <input_csv> <output_pickle> [exclude_ids_file]

Esempio (nuovo ordine, con filtro bot applicato in estrazione):
    python3 compute_bot_ids.py data/raw/steem_....csv output/bot_ids.txt
    python3 extract_personal_networks.py data/raw/steem_....csv data/processed/personal_networks_filtered.pkl output/bot_ids.txt

Esempio (senza filtro, per confronto prima/dopo):
    python3 extract_personal_networks.py data/raw/steem_....csv data/processed/personal_networks_unfiltered.pkl
"""

import sys
import os
import csv
import pickle
from collections import defaultdict

# Aggiunge esplicitamente la root del progetto (cartella superiore a
# 'scripts/', dove si trova il package 'personalnetwork') al path di
# ricerca dei moduli. Necessario perché quando si esegue
# `python3 scripts/nome_script.py`, Python aggiunge automaticamente
# solo la cartella 'scripts/' stessa, non la root del progetto -- da
# qui il ModuleNotFoundError, indipendentemente dalla cartella da cui
# si lancia il comando.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from personalnetwork import EgoInteractions, INTERACTION_TYPES


def load_excluded_ids(exclude_ids_file):
    with open(exclude_ids_file, 'r') as f:
        return set(line.strip() for line in f if line.strip())


def extract(input_csv, output_pickle, exclude_ids_file=None):
    excluded_ids = load_excluded_ids(exclude_ids_file) if exclude_ids_file else set()
    if exclude_ids_file:
        print(f"Account esclusi in ingresso (bot, da {exclude_ids_file}): {len(excluded_ids)}")

    personal_networks = {}
    n_total = 0
    n_skipped_invalid = 0
    n_self_loop = defaultdict(int)
    n_excluded = 0

    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # salta l'header
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

            # Self-loop (source == target, es. un self-vote su Steemit)
            # scartati qui ESATTAMENTE come in build_graph.py, cosi' che
            # i due script operino sulla stessa identica popolazione di
            # righe. Contati SEPARATAMENTE dagli scarti tecnici e per
            # tipo di interazione: non e' uno scarto "sporco", e' un
            # self-loop non e' una relazione ego-alter per definizione
            # (Sezione 3.3.1) -- il conteggio preciso e' una statistica
            # descrittiva per il Cap. 4 (es. il self-vote come strategia
            # di reward, gia' documentata in letteratura).
            if source == target:
                n_self_loop[interaction_type] += 1
                continue

            # Filtraggio bot ORA, prima della costruzione della
            # personal network: se la source e' un account gia'
            # identificato come sospetto, la riga viene scartata e non
            # si crea nessuna EgoInteractions per lui.
            if source in excluded_ids:
                n_excluded += 1
                continue

            if source not in personal_networks:
                personal_networks[source] = EgoInteractions(source)

            personal_networks[source].process_interaction(target, interaction_type)

            if n_total % 5000000 == 0:
                print(f"  ...{n_total} righe processate, {len(personal_networks)} ego trovati finora")

    n_self_loop_total = sum(n_self_loop.values())
    print(f"\nFatto. Righe totali: {n_total}, "
          f"scartate (malformate/tipo non valido): {n_skipped_invalid}")
    print(f"Self-loop esclusi (source == target), per tipo:")
    for itype in INTERACTION_TYPES:
        print(f"  {itype}: {n_self_loop.get(itype, 0)}")
    print(f"  totale self-loop: {n_self_loop_total}")
    print(f"Escluse (bot): {n_excluded}, ego unici: {len(personal_networks)}")

    with open(output_pickle, 'wb') as f:
        pickle.dump(personal_networks, f)
    print(f"Salvato in {output_pickle}")


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        sys.exit(1)
    exclude_ids_file = sys.argv[3] if len(sys.argv) == 4 else None
    extract(sys.argv[1], sys.argv[2], exclude_ids_file)
