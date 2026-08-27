"""
personalnetwork/clustering/__init__.py

Adapted from the CDR-based implementation (Zignani et al.). The five
clustering functions and the adaptive-interval logic are copied over
essentially unchanged -- confirmed data-agnostic, operating purely on
numeric tie-strength arrays. Only signature()/relevance() needed
generalizing away from hardcoded 'call'/'sms' keys.

MeanShift and Head/Tail Breaks are kept for completeness (matching the
original comparison table) but are NOT part of the adaptive method --
the papers explicitly exclude them from the final approach, and HTB's
own implementation looks buggy (see head_tail_break() docstring).
"""

# PATCH, applied here (not in calling scripts): pyclustering (for
# x-means) uses `numpy.warnings` internally, an alias removed in NumPy
# 2.0. This MUST live here, before `import pyclustering`, rather than
# in any calling script -- joblib's process-based parallelism (loky,
# using 'spawn' on macOS) launches separate OS processes that each
# reimport this module fresh, so a patch applied only in a calling
# script's global scope never reaches the worker processes. Patching
# here guarantees it re-runs in every process that imports this module.
import numpy as np
import warnings as _warnings
if not hasattr(np, 'warnings'):
    np.warnings = _warnings

from sklearn.cluster import MeanShift
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture
from pyclustering.cluster.xmeans import xmeans
from pyclustering.cluster.center_initializer import kmeans_plusplus_initializer
import jenkspy
import sys

from personalnetwork import INTERACTION_TYPES


def frequency_tie_strength(alter_data, ego_total, interaction_type):
    """
    Frequency-based tie strength: fraction of the ego's total
    interactions (of this specific type) that went to this alter.

    Replaces the earlier signature()/relevance() pair -- the advisor
    instructed using frequency only, for all three interaction types
    (vote, comment, transfer), so no hour/day-binning is needed at all.

    interaction_type: a SINGLE type (e.g. 'vote'), not a list -- per
    the decision to study interaction types separately (see PIPELINE.md,
    Stage 6). Call this once per type, building a separate tie-strength
    dict each time, then cluster each one independently.
    """
    return alter_data.counts[interaction_type] / ego_total


def get_ring_interval(degree):
    """
    Adaptive cluster-count constraint, exactly matching the Support
    Information PDF's rule. Fully data-agnostic -- no changes needed.

    TODO: discuss with advisor whether to keep these exact thresholds
    (50/100/300) for direct comparability with the CDR papers, or
    re-derive them from your own Steemit/Hive out-degree distribution.
    """
    if degree >= 50 and degree < 100:
        return (3, 4)
    elif degree >= 100 and degree < 300:
        return (4, 5)
    else:
        return (5, 6)


def rings_identification(ego, ego_data, cluster_functions):
    """Orchestrator: runs every clustering function in cluster_functions
    on one ego's tie-strength data. Unchanged from original."""
    alters, metric = map(np.array, zip(*ego_data.items()))
    output = {}
    try:
        data = metric.reshape(-1, 1)
        interval_ring = get_ring_interval(len(data))
        for func_name, clustering in cluster_functions.items():
            output[func_name] = clustering(data, alters, interval_ring)
        return (ego, output)
    except ValueError:
        print('Clustering error for node: {}'.format(ego))
        return ego
    except Exception:
        print("Unexpected error:", sys.exc_info()[0])
        raise


###########################################
#    Clustering functions                #
###########################################
# NOTE: all functions below are unchanged from the original CDR
# implementation -- confirmed fully data-agnostic, operating purely on
# the numeric tie-strength array (`data`) and the adaptive interval.
# The ring-relabeling convention (argsort centroids so ring 0 = highest
# tie strength = innermost circle) MUST be preserved exactly in any
# further modification -- getting this backwards silently swaps inner
# and outer circles in every result.

def mean_shift_clustering(data, alters, interval_ring):
    mean_shift_cl = MeanShift().fit(data.reshape(-1, 1))
    data_out = {}
    data_out['silhouette'] = silhouette_score(data.reshape(-1, 1), mean_shift_cl.labels_)
    data_out['num_rings'] = len(mean_shift_cl.cluster_centers_[:, 0])
    label_conversion = dict(zip(np.argsort(mean_shift_cl.cluster_centers_[:, 0]),
                                 reversed(range(0, data_out['num_rings']))))
    data_out['alter2ring'] = {a: label_conversion[mean_shift_cl.labels_[i]] for i, a in enumerate(alters)}
    return data_out


def xmeans_clustering(data, alters, interval_ring):
    data_out = {}
    k_initial = interval_ring[0]
    initial_centers = kmeans_plusplus_initializer(data.reshape(-1, 1), k_initial).initialize()
    # ccore=False: la libreria C++ precompilata di pyclustering e'
    # inclusa solo per x86_64, incompatibile con Apple Silicon (arm64).
    # Forziamo l'uso della sua implementazione pura Python, piu' lenta
    # ma funzionante su qualunque architettura.
    xmeans_cl = xmeans(data.reshape(-1, 1), initial_centers, interval_ring[1], ccore=False)
    xmeans_cl.process()
    clusters = xmeans_cl.get_clusters()
    classes = np.zeros((len(data), 1))
    for i, e in enumerate(clusters):
        classes[e] = i
    classes = np.array([e[0] for e in classes])
    centroids = np.array([x[0] for x in xmeans_cl.get_centers()])
    data_out['silhouette'] = silhouette_score(data.reshape(-1, 1), classes)
    data_out['num_rings'] = len(clusters)
    label_conversion = dict(zip(np.argsort(centroids), reversed(range(0, len(clusters)))))
    data_out['alter2ring'] = {a: label_conversion[classes[i]] for i, a in enumerate(alters)}
    return data_out


def gaussian_mm_clustering(data, alters, interval_ring):
    data_out = {}
    n_components_range = range(interval_ring[0], interval_ring[1] + 1)
    lowest_bic = np.inf  # NOTE: original used np.infty, removed in NumPy 2.0 -- fixed here
    best_gmm = None
    for k in n_components_range:
        gmm = GaussianMixture(n_components=k)
        gmm.fit(data.reshape(-1, 1))
        bic = gmm.bic(data.reshape(-1, 1))
        if bic < lowest_bic:
            lowest_bic = bic
            best_gmm = gmm
    classes = best_gmm.predict(data.reshape(-1, 1))
    centroids = np.array([x[0] for x in best_gmm.means_])
    data_out['silhouette'] = silhouette_score(data.reshape(-1, 1), classes)
    data_out['num_rings'] = len(centroids)
    label_conversion = dict(zip(np.argsort(centroids), reversed(range(0, len(centroids)))))
    data_out['alter2ring'] = {a: label_conversion[classes[i]] for i, a in enumerate(alters)}
    return data_out


def _gov(data, intervals):
    """Goodness-of-variance-fit, used by Jenks to pick the smallest k
    that adequately explains the variance in the data."""
    classes = np.ravel(np.searchsorted(intervals[1:], data, side='left'))
    centroids = [np.mean(data[classes == i]) for i in np.arange(np.max(classes) + 1)]
    centers = [centroids[i] for i in classes]
    sdam = np.sum((data - np.mean(data)) ** 2)
    sdcm = np.sum((data - centers) ** 2)
    return (sdam - sdcm) / sdam, classes, centroids


def jenks_clustering(data, alters, interval_ring, gov_threshold=0.85):
    """
    NOTE: original code used 0.8 here, though the paper text states
    0.85 -- worth deciding which to use for your own thesis rather
    than assuming they're interchangeable. Exposed as a parameter here
    so it's easy to test both.
    """
    data_out = {}
    breaks, classes, centroids, num_rings = None, None, None, None
    for k in range(interval_ring[0], interval_ring[1] + 1):
        # NOTA: il parametro si chiamava 'nb_class' nella versione della
        # libreria usata dal relatore; e' stato rinominato in 'n_classes'
        # in una versione successiva (per allinearsi a scikit-learn).
        breaks = jenkspy.jenks_breaks(data.ravel(), n_classes=k)
        gov, classes, centroids = _gov(data, breaks)
        num_rings = k
        if gov >= gov_threshold:
            break
    data_out['silhouette'] = silhouette_score(data.reshape(-1, 1), classes)
    data_out['num_rings'] = num_rings
    label_conversion = dict(zip(np.argsort(centroids), reversed(range(0, len(centroids)))))
    data_out['alter2ring'] = {a: label_conversion[classes[i]] for i, a in enumerate(alters)}
    data_out['breaks'] = breaks
    return data_out


def head_tail_break(data, threshold=0.4):
    """
    NOT part of the adaptive method -- excluded in the original papers
    (returns too few rings for all egos) and this implementation looks
    buggy (the while-loop's filtering step wraps a boolean mask in a
    list instead of indexing with it, likely breaking after one
    iteration). Kept only for completeness/reference; skip using this
    in your actual thesis pipeline.
    """
    intervals = []
    length = len(data)
    mean = np.mean(data)
    intervals.append(mean)
    head = data[data > mean]
    while len(head) > 1 and len(head) / length < threshold:
        length = len(head)
        mean = np.mean(head)
        intervals.append(mean)
        head = head[head > mean]  # fixed: was `[head>mean]` in the original
    intervals.append(np.max(data) + 1)
    classes = np.searchsorted(intervals, data, side='left')
    centroids = [np.mean(data[classes == i]) for i in np.arange(len(intervals)) if np.any(classes == i)]
    return classes, centroids, intervals
