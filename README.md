# Thesis Analysis Repository

Ego-network circle identification on Steemit, testing Dunbar's theory
of concentric ego-network circles using adaptive clustering on
interaction-based tie-strength metrics.

## Dataset
- Source: `steem_vote_comment_transfer_01012017_30062017.csv`
- 31,170,789 rows, Jan 1 - Jun 30 2017
- Schema: `source, target, weight, date, type`
- Three interaction types: `vote`, `comment`, `transfer`
- Tie strength is frequency-based, computed independently per
  interaction type. `date` and `weight` are read but not used.
- Self-loops (`source == target`) are excluded before any network is
  built.

## Structure
.
|-- PIPELINE.md
|-- README.md
|-- requirements.txt
|-- .gitignore
|-- data/
|   |-- raw/
|   `-- processed/
|-- personalnetwork/
|   |-- __init__.py            <- AlterData, EgoInteractions, INTERACTION_TYPES
|   `-- clustering/
|       `-- __init__.py        <- frequency_tie_strength(), adaptive clustering
|-- scripts/
|   |-- build_graph.py                 <- CSV -> networkx.DiGraph
|   |-- compute_bot_ids.py             <- graph -> suspicious account IDs
|   |-- extract_personal_networks.py   <- CSV + bot IDs -> EgoInteractions dict
|   |-- filter_suspicious_accounts.py  <- bot filter on an existing pickle
|   |-- compute_bot_scores.py          <- diagnostic: in/out-degree CDF
|   |-- check_bot_overlap.py           <- diagnostic: bot/threshold overlap
|   |-- check_self_loops.py            <- diagnostic: self-loop counts
|   |-- check_weight.py                <- diagnostic: raw weight values
|   |-- check_threshold.py             <- ego counts per threshold/type
|   |-- run_clustering.py              <- tie strength + adaptive clustering
|   `-- summarize_rings.py             <- circle-count and size tables
|-- output/
`-- figures/

## Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage
```bash
# 1. Build the communication graph
python3 scripts/build_graph.py data/raw/steem_vote_comment_transfer_01012017_30062017.csv data/processed/communication_graph.pkl

# 2. Identify suspicious/bot accounts
python3 scripts/compute_bot_ids.py data/processed/communication_graph.pkl output/bot_ids.txt output/degrees.csv

# 3. Extract personal networks, excluding bots
python3 scripts/extract_personal_networks.py data/raw/steem_vote_comment_transfer_01012017_30062017.csv data/processed/personal_networks_filtered.pkl output/bot_ids.txt

# 4. Check ego counts per interaction type
python3 scripts/check_threshold.py data/processed/personal_networks_filtered.pkl

# 5. Run adaptive clustering
python3 scripts/run_clustering.py data/processed/personal_networks_filtered.pkl vote data/processed/rings_vote_filtered.pkl
python3 scripts/run_clustering.py data/processed/personal_networks_filtered.pkl comment data/processed/rings_comment_filtered.pkl
python3 scripts/run_clustering.py data/processed/personal_networks_filtered.pkl transfer data/processed/rings_transfer_filtered.pkl

# 6. Summarize results
python3 scripts/summarize_rings.py data/processed/rings_vote_filtered.pkl output/tabella_vote.csv
python3 scripts/summarize_rings.py data/processed/rings_comment_filtered.pkl output/tabella_comment.csv
python3 scripts/summarize_rings.py data/processed/rings_transfer_filtered.pkl output/tabella_transfer.csv
```