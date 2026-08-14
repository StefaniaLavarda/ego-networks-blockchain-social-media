# Thesis Analysis Repository
Ego-network circle identification on Steemit, testing Dunbar's theory of
concentric ego-network circles using adaptive clustering on
interaction-based tie-strength metrics.

**Scope note:** the thesis originally considered both Steemit and Hive;
the advisor's dataset covers **Steemit only** (Jan-Jun 2017), so the
scope has been narrowed accordingly. See Chapter 2 for the corrections
this required.

## Dataset
- Source: advisor-provided CSV, `steem_vote_comment_transfer_01012017_30062017.csv`
- 31,170,789 rows, Jan 1 - Jun 30 2017
- Schema: `source, target, weight, date, type`
- Three interaction types: `vote`, `comment`, `transfer` (financial
  transaction) 
- **tie strength uses frequency only**, for
  all three interaction types. `weight` and `date` are read but
  deliberately unused

## Structure

```
.
|-- PIPELINE.md              <- full pipeline documentation
|-- README.md                 
|-- requirements.txt
|-- .gitignore
|-- data/
|   |-- raw/                  <- raw CSV goes here (gitignored)
|   `-- processed/            <- personal_networks.pkl, rings_*.pkl
|                                 (gitignored)
|-- personalnetwork/           <- core package
|   |-- __init__.py            <- AlterData, EgoInteractions
|   |                            
|   `-- clustering/
|       `-- __init__.py        <- frequency_tie_strength(), adaptive
|                                  clustering (GMM/X-means/Jenks)
|-- scripts/
|   |-- extract_personal_networks.py   <- CSV -> EgoInteractions dict
|   |-- check_threshold.py             <- reports ego counts >= threshold,
|   |                                      per interaction type
|   |-- run_clustering.py              <- tie-strength + adaptive
|   |                                      clustering, one interaction
|   |                                      type at a time, parallelized
|   `-- summarize_rings.py             <- circle-count distributions +
|                                          size tables (post-clustering)
|-- output/                    <- result tables (gitignored)
`-- figures/                   <- generated plots
```

## Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage
```bash
# 1. Extract personal networks from raw CSV (one-time, ~31M rows)
python3 scripts/extract_personal_networks.py data/raw/steem_vote_comment_transfer_01012017_30062017.csv data/processed/personal_networks.pkl

# 2. Check how many egos qualify (>= threshold alters) per interaction type
python3 scripts/check_threshold.py data/processed/personal_networks.pkl

# 3. Run adaptive clustering, once per interaction type
python3 scripts/run_clustering.py data/processed/personal_networks.pkl vote data/processed/rings_vote.pkl
python3 scripts/run_clustering.py data/processed/personal_networks.pkl comment data/processed/rings_comment.pkl

# 4. Summarize results
python3 scripts/summarize_rings.py data/processed/rings_vote.pkl output/tabella_vote.csv
python3 scripts/summarize_rings.py data/processed/rings_comment.pkl output/tabella_comment.csv
```
