# Pipeline Documentation

## Overview 
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

## Stage-by-stage detail

### [1] Build the communication graph
**Script:** `build_graph.py`.

Builds a single `networkx.DiGraph` from the raw CSV. A row is
discarded if it does not have five fields, its type is not one of the
three valid types, or it is a self-loop. An edge `(source, target)` is
created or updated, incrementing the counter `c_{type}` for that edge.

| Column | Meaning | Used? |
|---|---|---|
| `source` | ego | yes |
| `target` | alter | yes |
| `weight` | voting weight (-10000 to 10000) for `vote`; constant `1.0` for `comment`; transfer amount for `transfer` | no |
| `date` | timestamp | no |
| `type` | `vote` / `comment` / `transfer` | yes |

### [2] Identify suspicious/bot accounts
**Script:** `compute_bot_ids.py`.

Computes in-degree and out-degree directly on the graph via
`G.out_degree()` / `G.in_degree()`, for every account with a positive
out-degree. An account is flagged as suspicious if its in/out-degree
ratio is 0. `compute_bot_scores.py` and `check_bot_overlap.py` are
diagnostic scripts used to validate this threshold and are not part of
the main run.

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

`transfer` reaches 50 alters for very few egos; a decision on how to
treat this interaction type in the final analysis is pending.

### [4] Compute tie strength
`frequency_tie_strength(alter_data, ego_total, interaction_type)` in
`personalnetwork/clustering/__init__.py`. Computed independently per
interaction type.

### [5] Adaptive clustering
**Script:** `run_clustering.py`, parallelized via `joblib`.

Three algorithms: Gaussian Mixture Models, X-means, Jenks natural
breaks, each constrained to a size-dependent range of admissible
cluster counts via `get_ring_interval()`. Mean Shift and Head/Tail
Breaks are not used, since neither accepts a direct constraint on the
number of clusters.

Ring-relabeling convention: `argsort` on cluster centroids, so ring 0
always corresponds to the highest tie strength (innermost circle),
consistent across all algorithms and interaction types.

### [6] Validation against Dunbar's hypothesis
**Script:** `summarize_rings.py`.

Produces circle-count distributions and a size/standard-deviation
table per algorithm, per interaction type. Cross-interaction-type
comparison (Jaccard overlap of alters between vote and comment, then
Normalized Mutual Information on the shared alters' circle assignment)
is not yet implemented.
