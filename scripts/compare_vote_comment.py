"""
compare_vote_comment.py

For each ego that qualifies for circle identification on both vote and
comment, compares the alter sets reached through the two interaction
types using the Jaccard coefficient, then, restricted to alters common
to both, compares the circle assignment obtained from vote against the
one obtained from comment, using Normalized Mutual Information. Done
separately for each clustering algorithm.

Usage:
    python3 compare_vote_comment.py <rings_vote_pickle> <rings_comment_pickle> <output_csv> [min_common_alters]

Example:
    python3 compare_vote_comment.py data/processed/rings_vote.pkl data/processed/rings_comment.pkl output/vote_comment_comparison.csv
"""

import sys
import os
import pickle
import csv
import statistics

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from sklearn.metrics import normalized_mutual_info_score


def compare(rings_vote_pickle, rings_comment_pickle, output_csv, min_common_alters=2):
    with open(rings_vote_pickle, 'rb') as f:
        rings_vote = pickle.load(f)
    with open(rings_comment_pickle, 'rb') as f:
        rings_comment = pickle.load(f)

    common_egos = set(rings_vote.keys()) & set(rings_comment.keys())
    print(f"Egos qualifying for both vote and comment: {len(common_egos)}")

    algorithms = ['gmm', 'jenks', 'xmeans']
    rows = []
    n_too_few_common = {algo: 0 for algo in algorithms}
    n_nmi_failed = {algo: 0 for algo in algorithms}

    for ego_id in common_egos:
        vote_data = rings_vote[ego_id]
        comment_data = rings_comment[ego_id]

        # The alter set is the same across algorithms for a given
        # ego/interaction type, so it only needs to be computed once,
        # from any algorithm present.
        any_algo_vote = next(iter(vote_data))
        any_algo_comment = next(iter(comment_data))
        alters_vote = set(vote_data[any_algo_vote]['alter2ring'].keys())
        alters_comment = set(comment_data[any_algo_comment]['alter2ring'].keys())

        union = alters_vote | alters_comment
        intersection = alters_vote & alters_comment
        jaccard = len(intersection) / len(union) if union else 0.0

        for algo in algorithms:
            if algo not in vote_data or algo not in comment_data:
                continue
            alter2ring_vote = vote_data[algo]['alter2ring']
            alter2ring_comment = comment_data[algo]['alter2ring']

            common_alters = sorted(intersection)

            if len(common_alters) < min_common_alters:
                n_too_few_common[algo] += 1
                continue

            labels_vote = [alter2ring_vote[a] for a in common_alters]
            labels_comment = [alter2ring_comment[a] for a in common_alters]

            try:
                nmi = normalized_mutual_info_score(labels_vote, labels_comment)
            except Exception:
                n_nmi_failed[algo] += 1
                continue

            rows.append({
                'ego_id': ego_id,
                'algorithm': algo,
                'n_alters_vote': len(alters_vote),
                'n_alters_comment': len(alters_comment),
                'jaccard': jaccard,
                'n_common_alters': len(common_alters),
                'nmi': nmi,
            })

    with open(output_csv, 'w', newline='') as f:
        writer = csv.DictWriter(
            f, fieldnames=['ego_id', 'algorithm', 'n_alters_vote', 'n_alters_comment',
                           'jaccard', 'n_common_alters', 'nmi']
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved to {output_csv}")

    print(f"\nEgos excluded per algorithm (fewer than {min_common_alters} common alters):")
    for algo in algorithms:
        print(f"  {algo}: {n_too_few_common[algo]}")
    if any(n_nmi_failed.values()):
        print(f"\nEgos excluded per algorithm (NMI computation failed):")
        for algo in algorithms:
            if n_nmi_failed[algo]:
                print(f"  {algo}: {n_nmi_failed[algo]}")

    seen_egos = set()
    all_jaccards = []
    for r in rows:
        if r['ego_id'] not in seen_egos:
            all_jaccards.append(r['jaccard'])
            seen_egos.add(r['ego_id'])
    print(f"\nJaccard summary (n={len(all_jaccards)} egos with at least one usable algorithm):")
    if all_jaccards:
        print(f"  mean={statistics.mean(all_jaccards):.4f}, median={statistics.median(all_jaccards):.4f}")

    print("\nNMI summary, by algorithm:")
    for algo in algorithms:
        nmi_values = [r['nmi'] for r in rows if r['algorithm'] == algo]
        if nmi_values:
            print(f"  {algo}: n={len(nmi_values)}, mean={statistics.mean(nmi_values):.4f}, "
                  f"median={statistics.median(nmi_values):.4f}")
        else:
            print(f"  {algo}: no egos with enough common alters")


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5):
        print(__doc__)
        sys.exit(1)
    min_common_alters = int(sys.argv[4]) if len(sys.argv) == 5 else 2
    compare(sys.argv[1], sys.argv[2], sys.argv[3], min_common_alters)
