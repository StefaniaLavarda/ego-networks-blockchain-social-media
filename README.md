# The Organization of Ego-Networks in Blockchain-Based Social Media (Steemit)

Ego-network circle identification on Steemit, testing Dunbar's theory
of concentric ego-network circles using adaptive clustering on
interaction-based tie-strength metrics.

## Datasets

Two datasets are used, for different interaction types:

- **vote/comment/transfer**: `steem_vote_comment_transfer_01012017_30062017.csv`
  31,170,789 rows, Jan 1 - Jun 30 2017
- **transfer only**: `steem_transfer_01112018_31052019.csv`
  24,050,066 rows, Nov 1 2018 - May 31 2019, used because very few
  accounts reach the clustering threshold on transfer within the
  first period

Both share the same schema: `source, target, weight, date, type`.

- Three interaction types: `vote`, `comment`, `transfer`
- Tie strength is frequency-based, computed independently per
  interaction type. `date` is read but not used. `weight` is read but
  not used either, even though it carries a real value for `vote`
  (voting weight, -10000 to 10000, negative = downvote) and `transfer`
  (transfer amount); for `comment` it is a constant `1.0` with no
  information.
- Self-loops (`source == target`) are excluded before any network is
  built.

## Structure

```
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
|   |-- build_graph.py                       <- CSV -> networkx.DiGraph
|   |-- compute_bot_ids.py                   <- graph -> suspicious account IDs
|   |-- extract_personal_networks.py         <- CSV + bot IDs -> EgoInteractions dict
|   |-- filter_suspicious_accounts.py        <- bot filter on an existing pickle
|   |-- compute_bot_scores.py                <- diagnostic: in/out-degree CDF
|   |-- check_bot_overlap.py                 <- diagnostic: bot/threshold overlap
|   |-- check_self_loops.py                  <- diagnostic: self-loop counts
|   |-- check_weight.py                      <- diagnostic: raw weight values
|   |-- check_threshold.py                   <- ego counts per threshold/type
|   |-- run_clustering.py                    <- tie strength + adaptive clustering
|   |-- summarize_rings.py                   <- circle-count and size tables
|   |-- tie_strength_by_ring.py              <- tie strength by ring, monotonicity check
|   |-- compare_vote_comment.py              <- Jaccard + NMI, vote vs comment circles
|   |-- check_distinct_values_vs_kmin.py     <- structural cause of clustering failure
|   |-- check_failure_correlates.py          <- failed vs succeeded network size/CV
|   |-- plot_circle_count_distribution.py    <- bar chart: circle count by type/algorithm
|   `-- plot_nmi_distribution.py             <- CDF plot: NMI distribution
|-- output/
`-- figures/
```

## Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

Steps 1-4 are run once per dataset; steps 5-6 are run once per
interaction type. Steps 7 onward are post-processing, run once the
relevant clustering results already exist.

### Dataset 1: vote/comment/transfer (2017)
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
python3 scripts/run_clustering.py data/processed/personal_networks_filtered.pkl vote data/processed/rings_vote.pkl
python3 scripts/run_clustering.py data/processed/personal_networks_filtered.pkl comment data/processed/rings_comment.pkl

# 6. Summarize results
python3 scripts/summarize_rings.py data/processed/rings_vote.pkl output/table_vote.csv
python3 scripts/summarize_rings.py data/processed/rings_comment.pkl output/table_comment.csv
```

### Dataset 2: transfer only (2018-2019)
```bash
# 1. Build the communication graph
python3 scripts/build_graph.py data/raw/steem_transfer_01112018_31052019.csv data/processed/communication_graph_transfer.pkl

# 2. Identify suspicious/bot accounts
python3 scripts/compute_bot_ids.py data/processed/communication_graph_transfer.pkl output/bot_ids_transfer.txt output/degrees_transfer.csv

# 3. Extract personal networks, excluding bots
python3 scripts/extract_personal_networks.py data/raw/steem_transfer_01112018_31052019.csv data/processed/personal_networks_transfer_filtered.pkl output/bot_ids_transfer.txt

# 4. Check ego counts
python3 scripts/check_threshold.py data/processed/personal_networks_transfer_filtered.pkl

# 5. Run adaptive clustering
python3 scripts/run_clustering.py data/processed/personal_networks_transfer_filtered.pkl transfer data/processed/rings_transfer.pkl

# 6. Summarize results
python3 scripts/summarize_rings.py data/processed/rings_transfer.pkl output/table_transfer.csv
```

### Tie strength by ring, and monotonicity check
```bash
python3 scripts/tie_strength_by_ring.py data/processed/personal_networks_filtered.pkl data/processed/rings_vote.pkl vote output/tie_strength_vote.csv figures/
python3 scripts/tie_strength_by_ring.py data/processed/personal_networks_filtered.pkl data/processed/rings_comment.pkl comment output/tie_strength_comment.csv figures/
python3 scripts/tie_strength_by_ring.py data/processed/personal_networks_transfer_filtered.pkl data/processed/rings_transfer.pkl transfer output/tie_strength_transfer.csv figures/
```

### Comparison across interaction types (vote vs comment)
```bash
python3 scripts/compare_vote_comment.py data/processed/rings_vote.pkl data/processed/rings_comment.pkl output/vote_comment_comparison.csv
```

### Clustering failure diagnostics
```bash
python3 scripts/check_distinct_values_vs_kmin.py data/processed/personal_networks_filtered.pkl data/processed/rings_vote.pkl vote
python3 scripts/check_distinct_values_vs_kmin.py data/processed/personal_networks_filtered.pkl data/processed/rings_comment.pkl comment
python3 scripts/check_distinct_values_vs_kmin.py data/processed/personal_networks_transfer_filtered.pkl data/processed/rings_transfer.pkl transfer

python3 scripts/check_failure_correlates.py data/processed/personal_networks_filtered.pkl data/processed/rings_vote.pkl vote
python3 scripts/check_failure_correlates.py data/processed/personal_networks_filtered.pkl data/processed/rings_comment.pkl comment
python3 scripts/check_failure_correlates.py data/processed/personal_networks_transfer_filtered.pkl data/processed/rings_transfer.pkl transfer
```

### Figures
```bash
python3 scripts/plot_circle_count_distribution.py data/processed/rings_vote.pkl data/processed/rings_comment.pkl data/processed/rings_transfer.pkl gmm figures/circle_count_distribution_gmm.png
python3 scripts/plot_circle_count_distribution.py data/processed/rings_vote.pkl data/processed/rings_comment.pkl data/processed/rings_transfer.pkl jenks figures/circle_count_distribution_jenks.png
python3 scripts/plot_circle_count_distribution.py data/processed/rings_vote.pkl data/processed/rings_comment.pkl data/processed/rings_transfer.pkl xmeans figures/circle_count_distribution_xmeans.png

python3 scripts/plot_nmi_distribution.py output/vote_comment_comparison.csv figures/nmi_distribution.png
```
