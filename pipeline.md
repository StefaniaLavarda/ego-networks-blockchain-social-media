# Pipeline Documentation

## Overview

Two datasets are processed through the same pipeline, independently:
vote/comment/transfer (Jan-Jun 2017) and a transfer-only dataset
(Nov 2018-May 2019), used because very few accounts reach the
clustering threshold on transfer within the first period. Steps 1-3
below are run once per dataset; steps 4-6 are run once per
interaction type; step 7 is post-processing, run once the relevant
clustering results already exist.

```
raw CSV (source, target, weight, date, type)
        |
        v
[1] build a directed graph, one edge per (source, target), with
    weight attributes c_vote / c_comment / c_transfer on the same
    edge; self-loops and malformed rows excluded
        |
        v
[2] identify suspicious/bot accounts from the graph (in/out-degree
    ratio, applied to every account with out-degree > 0)
        |
        v
[3] extract personal networks from the raw CSV (dictionary lookup),
    excluding bots and self-loops, then filter by size (>= 50 alters
    per interaction type)
        |
        v
[4] compute tie strength (frequency-based, per interaction type)
        |
        v
[5] adaptive clustering (GMM / X-means / Jenks, constrained by ego
    size)
        |
        v
[6] validation against Dunbar's predicted circle sizes
        |
        v
[7] post-processing: tie strength by ring, comparison across
    interaction types, clustering failure diagnostics, figures
```

## Stage-by-stage detail

### [1] Build the communication graph
**Script:** `build_graph.py`.

Builds a single `networkx.DiGraph` from a raw CSV. A row is discarded
if it does not have five fields, its type is not one of the three
valid types, or it is a self-loop. An edge `(source, target)` is
created or updated, incrementing the counter `c_{type}` for that edge.

Run once per dataset:
```bash
python3 build_graph.py data/raw/steem_vote_comment_transfer_01012017_30062017.csv data/processed/communication_graph.pkl
python3 build_graph.py data/raw/steem_transfer_01112018_31052019.csv data/processed/communication_graph_transfer.pkl
```

| Column | Meaning | Used? |
|---|---|---|
| `source` | ego | yes |
| `target` | alter | yes |
| `weight` | voting weight (-10000 to 10000, negative = downvote) for `vote`; transfer amount for `transfer`; constant `1.0` (no information) for `comment` | no |
| `date` | timestamp | no |
| `type` | `vote` / `comment` / `transfer` | yes |

### [2] Identify suspicious/bot accounts
**Script:** `compute_bot_ids.py`.

Computes in-degree and out-degree directly on the graph via
`G.out_degree()` / `G.in_degree()`, for every account with a positive
out-degree. An account is flagged as suspicious if its in/out-degree
ratio is 0. Applied separately to each of the two graphs, since they
come from different datasets; the resulting share of suspicious
accounts differs between them (around 35% for vote/comment, around
29% for transfer). `compute_bot_scores.py` and `check_bot_overlap.py`
are diagnostic scripts used to validate this threshold and are not
part of the main run.

### [3] Extract personal networks + filter by size
**Script:** `extract_personal_networks.py` + `check_threshold.py`.

Builds `EgoInteractions` objects from the raw CSV via a dictionary
lookup, excluding bot accounts and self-loop rows. Egos are filtered
by personal network size separately for each interaction type: only
egos with at least 50 alters for a given type are retained for
clustering on that type.

`filter_suspicious_accounts.py` filters bots from an already-built
pickle instead of during extraction; used to produce the
unfiltered/filtered pair for the before/after comparison in Section
4.1.1.

`transfer` reaches 50 alters for very few egos within the first
dataset's period. This is why a second, transfer-only dataset covering
a later and longer period is used for this interaction type.

### [4] Compute tie strength
`frequency_tie_strength(alter_data, ego_total, interaction_type)` in
`personalnetwork/clustering/__init__.py`. Computed independently per
interaction type.

### [5] Adaptive clustering
**Script:** `run_clustering.py`, parallelized via `joblib`.

Three algorithms: Gaussian Mixture Models, X-means, Jenks natural
breaks, each constrained to a size-dependent range of admissible
cluster counts via `get_ring_interval()`. The Jenks goodness-of-fit
threshold is set to 0.85. Mean Shift and Head/Tail Breaks are not
used, since neither accepts a direct constraint on the number of
clusters.

Ring-relabeling convention: `argsort` on cluster centroids, so ring 0
always corresponds to the highest tie strength (innermost circle),
consistent across all algorithms and interaction types.

A small share of egos fail to produce a valid result for a given
algorithm, due to degenerate clustering: forming $k$ circles requires
at least $k$ distinct tie strength values, and some egos, especially
on transfer, do not have enough. See Stage 7 for the diagnostic
scripts that quantify and explain this.

### [6] Validation against Dunbar's hypothesis
**Script:** `summarize_rings.py`.

Produces circle-count distributions and a size/standard-deviation
table per algorithm, per interaction type.

### [7] Post-processing

**Tie strength by ring.** `tie_strength_by_ring.py` groups alters by
their assigned ring, across all egos sharing the same algorithm and
circle count, and reports the mean, median, and standard deviation of
tie strength per ring, plus a check that these values decrease
monotonically from ring 0 outward. Optionally also produces a KDE
plot per algorithm/circle-count combination.

**Comparison across interaction types.** `compare_vote_comment.py`
computes, for each ego qualifying on both vote and comment, the
Jaccard overlap between the two alter sets, then the Normalized
Mutual Information between the two circle assignments, restricted to
the alters common to both. This comparison is limited to vote and
comment, since these are the only two interaction types that come
from the same dataset and time period; transfer is excluded.

**Clustering failure diagnostics.** `check_distinct_values_vs_kmin.py`
checks, for each ego, whether the number of distinct tie strength
values is enough to structurally support the minimum number of
circles required for its personal network size; an ego with fewer
distinct values than this minimum cannot succeed regardless of the
clustering algorithm used. `check_failure_correlates.py` compares
personal network size and tie-strength variability between egos whose
clustering succeeded and those whose clustering failed.

**Figures.** `plot_circle_count_distribution.py` produces a grouped
bar chart of the circle-count distribution by interaction type, one
per algorithm. `plot_nmi_distribution.py` produces a CDF plot of the
NMI distribution from `compare_vote_comment.py`'s output.
