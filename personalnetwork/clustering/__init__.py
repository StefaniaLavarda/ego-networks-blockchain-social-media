"""
personalnetwork/clustering/__init__.py

Adaptive clustering functions for identifying Dunbar circles from
one-dimensional tie-strength arrays: Gaussian Mixture Models, X-means,
and Jenks natural breaks, each constrained to a size-dependent range
of admissible cluster counts. Mean Shift and Head/Tail Breaks are also
included but are not part of the adaptive method.
"""

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

    interaction_type is a single type (e.g. 'vote'), not a list, since
    interaction types are studied separately: call this once per type,
    building a separate tie-strength dict each time, then cluster each
    one independently.
    """
    return alter_data.counts[interaction_type] / ego_total


def get_ring_interval(degree):
    """
    Adaptive cluster-count constraint: the admissible range for the
    number of circles, based on personal network size.
    """
    if degree >= 50 and degree < 100:
        return (3, 4)
    elif degree >= 100 and degree < 300:
        return (4, 5)
    else:
        return (5, 6)


def rings_identification(ego, ego_data, cluster_functions):
    """Runs every clustering function in cluster_functions on one
    ego's tie-strength data."""
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
# All functions below operate purely on the numeric tie-strength array
# (`data`) and the adaptive interval. The ring-relabeling convention
# (argsort centroids so ring 0 = highest tie strength = innermost
# circle) must be preserved exactly in any modification -- getting
# this backwards silently swaps inner and outer circles in every
# result.

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
    # ccore=False: pyclustering's precompiled C++ core is x86_64-only,
    # incompatible with Apple Silicon (arm64). This forces the pure
    # Python implementation instead, slower but portable across
    # architectures.
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
    lowest_bic = np.inf
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
    Increases the number of classes one at a time until the
    goodness-of-variance-fit score reaches gov_threshold.
    """
    data_out = {}
    breaks, classes, centroids, num_rings = None, None, None, None
    for k in range(interval_ring[0], interval_ring[1] + 1):
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
    Not part of the adaptive method: not compatible with a size-
    dependent constraint on the number of clusters. This
    implementation also has a known bug in the while-loop's filtering
    step, which wraps a boolean mask in a list instead of indexing
    with it, likely breaking after one iteration. Kept for reference
    only; not used in the clustering pipeline.
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
        head = head[head > mean]
    intervals.append(np.max(data) + 1)
    classes = np.searchsorted(intervals, data, side='left')
    centroids = [np.mean(data[classes == i]) for i in np.arange(len(intervals)) if np.any(classes == i)]
    return classes, centroids, intervals
