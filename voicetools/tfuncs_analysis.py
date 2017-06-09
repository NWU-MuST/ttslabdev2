# -*- coding: utf-8 -*-
""" Some functions operating on Track objects for research purposes...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

from copy import deepcopy

import numpy as np
from scipy.spatial.distance import cdist
from scipy.interpolate import InterpolatedUnivariateSpline, UnivariateSpline

import ttslab
from ttslab.trackfile import Track
ttslab.extend(Track, "ttslab.trackfile.funcs.tfuncs_praat")

from ttslab_dtw import dtw_align as _dtw_align


def dtw_align(track, track2, metric="euclidean", VI=None):
    return _dtw_align(track.values, track2.values, metric, VI)


### ORIGINAL PURE PYTHON IMPLEMENTATION MAY COME IN HANDY SOMEWHERE...
######################################################################
# def dtw_align(track, track2, metric="euclidean", VI=None):
#     """DP alignment between tracks....
#        Returns: cumdist, dist, path (corresponding sample indices)

#        The functionality is based on the distance implementations
#        available in scipy.spatial.distance.cdist thus refer to
#        this documentation for explanation of function args...
#     """

#     assert track.numchannels == track2.numchannels, "Tracks don't have the same number of channels..."

#     dpp = np.zeros((track.numframes, track2.numframes), dtype=int)
#     cumdist = cdist(track.values, track2.values, metric=metric, VI=VI)
#     dist = np.array(cumdist)

#     dpp[0][0] = -1

#     for i in range(1, track.numframes):
#         cumdist[i][0] += cumdist[i-1][0]
#         dpp[i][0] = -1

#     for i in range(1, track2.numframes):
#         cumdist[0][i] += cumdist[0][i-1]
#         dpp[0][i] = 1

#     for i in range(1, track.numframes):
#         for j in range(1, track2.numframes):
#             if cumdist[i-1][j] < cumdist[i-1][j-1]:
#                 if cumdist[i][j-1] < cumdist[i-1][j]:
#                     cumdist[i][j] += cumdist[i][j-1]
#                     dpp[i][j] = 1   #hold
#                 else: #horizontal best
#                     cumdist[i][j] += cumdist[i-1][j]
#                     dpp[i][j] = -1  #jump
#             elif cumdist[i][j-1] < cumdist[i-1][j-1]:
#                 cumdist[i][j] += cumdist[i][j-1]
#                 dpp[i][j] = 1       #hold
#             else:
#                 cumdist[i][j] += cumdist[i-1][j-1]
#                 dpp[i][j] = 0       #jump

#     mapping = np.zeros(track.numframes, dtype=int)
#     cost = -1
#     j = track2.numframes - 1
#     for i in range(track.numframes - 1, -1, -1): #n-1 downto 0
#         if cost == -1:
#             cost = cumdist[i][j]
#         mapping[i] = j
#         while dpp[i][j] == 1:
#             j -= 1
#         if dpp[i][j] == 0:
#             j -= 1

#     path = []
#     for i, c in enumerate(mapping):
#         if i == 0:
#             path.append((i, c))
#             continue
#         repeating = range(path[-1][-1], c)
#         if repeating:
#             path.pop()
#             for j in repeating:
#                 path.append((i-1, j))
#         path.append((i, c))

#     return cumdist, dist, path


def _local_timediff(path, reftimes, targettimes):
    """ determine the local time difference mapped onto reftimes...
    """
    t = reftimes[:path[-1][0] + 1]
    delta = np.zeros((len(t)), dtype=np.float64)
    for rti, tti in path:
        delta[rti] = targettimes[tti] - reftimes[rti]
    ttrack = Track()
    ttrack.times = t
    ttrack.values = delta
    return ttrack

def relative_local_speechrate(reft, targett, s=0.03, realigntimes=False, debug=False):
    """ calculate the relative local speech rate between targett and
        reft by DTW aligning the tracks, fitting a smoothing spline
        to the frame time difference function (smoothing factor 's')
        and using this to calculate derivative contour.
    """
    try:
        assert (targett.times[1] - targett.times[0]) == (reft.times[1] - reft.times[0]), "constant timestep for reference and target need to be equal..."
    except AssertionError:
        print("WARNING: timesteps must be equal.... (this may be spurious if 'remove_pau' was used)")

    path = dtw_align(reft, targett)[-1]
    ltd = _local_timediff(path, reft.times, targett.times)
    if realigntimes:
        newreftimes = np.arange(1, len(ltd) +1) * (ltd.times[1] - ltd.times[0])
    else:
        newreftimes = ltd.times.copy()
    spline = UnivariateSpline(newreftimes, ltd.values, k=5, s=s)
    if debug:
        import pylab as pl
        pl.plot(ltd.times, ltd.values)
        pl.plot(ltd.times, spline(ltd.times))
    rlstrack = Track()
    rlstrack.times = newreftimes
    rlstrack.values = spline(rlstrack.times, 1).reshape((-1, 1))
    return rlstrack

def warpfunc_t(reft, targett, s, k=5):
    try:
        assert (targett.times[1] - targett.times[0]) == (reft.times[1] - reft.times[0]), "constant timestep for reference and target need to be equal..."
    except AssertionError:
        print("WARNING: timesteps must be equal.... (this may be spurious if 'remove_pau' was used)")
    path = dtw_align(reft, targett)[-1]
    delta = np.zeros((len(reft)), dtype=np.float64)
    for rti, tti in path:
        delta[rti] = targett.times[tti] - reft.times[rti]
    spline = UnivariateSpline(reft.times, delta, k=5, s=s)
    return spline
    
def relativeratefunc_x(reft, targett, s, k=5):
    path = dtw_align(reft, targett)[-1]
    delta = np.zeros((len(reft)), dtype=np.float64)
    for rti, tti in path:
        delta[rti] = targett.values[tti] - reft.values[rti]
    spline = UnivariateSpline(reft.times, delta, k=5, s=s)
    return spline


# def relative_local_speechrate2(targett, reft, N=5, resettimes=True, debug=False):
#     """ N must be odd...
#     """
#     assert N % 2 != 0
#     try:
#         assert (targett.times[1] - targett.times[0]) == (reft.times[1] - reft.times[0]), "constant timestep for reference and target need to be equal..."
#     except AssertionError:
#         print("WARNING: timesteps must be equal.... (this may be spurious if 'remove_pau' was used)")

#     path = dtw_align(targett, reft)[-1]
#     ltd = _local_timediff(path, targett.times, reft.times, resettimes=resettimes)
#     ltds = ltd.newtrack_from_sspline(ltd.times, s=0.05)
#     if debug:
#         import pylab as pl
#         pl.plot(ltd.times, ltd.values)
#         pl.plot(ltds.times, ltds.values)
#     return gradient(ltds, h=N-1)
    
def relative_local_x(reft, targett, dtwpath, s=100, debug=False):
    """Determines the rate of change of target relative to ref, using
       alignment provided by dtwpath.
    """

    t = reft.times.copy()
    delta = np.zeros((len(t)), dtype=np.float64)
    for rti, tti in dtwpath:
        delta[rti] = targett.values[tti] - reft.values[rti]
    
    spline = UnivariateSpline(t, delta, k=5, s=s)
    if debug:
        import pylab as pl
        pl.subplot(211)
        pl.plot(t, reft.values, label="ref")
        temp = np.zeros((len(t)), dtype=np.float64)
        for rti, tti in dtwpath:
            temp[rti] = targett.values[tti]
        pl.plot(t, temp, label="tgt")
        pl.legend()
        pl.subplot(212)
        pl.plot(t, delta)
        pl.plot(t, spline(t))

    rlxtrack = Track()
    rlxtrack.times = t
    rlxtrack.values = spline(rlxtrack.times, 1).reshape((-1, 1))
    return rlxtrack
    

def _show_dtw_path(dist, path):
    """Visualise dtw path...
    """
    import pylab as pl

    for coord in path:
        dist[coord[0]][coord[1]] = 0.0
    
    pl.imshow(dist, interpolation='nearest', aspect="auto")
    pl.ylabel("reference (samples)")
    pl.xlabel("target (samples)")
    pl.show()

    
    #FOR VIEWING AGAINST LABEL FILE.... TODO
    # refsegendtimes = [float(seg[0]) for seg in reflabels.entries]
    # refindices = [find_closest_index(reftrack.times, segendtime) for segendtime in refsegendtimes]
    # oindices = [map[index] for index in refindices]

    # pl.yticks([0] + refindices, [""] + [seg[1] for seg in reflabels.entries])
    # pl.xticks([0] + oindices, [""] + [seg[1] for seg in reflabels.entries])
    # pl.axis([1, oindices[-1], None, None])
    # pl.grid(True)
    # pl.xlabel("output")
    # pl.ylabel("reference")


    # pl.matshow(dpt)
    # pl.yticks([0] + refindices, [""] + [seg[1] for seg in reflabels.entries])
    # pl.xticks([0] + oindices, [""] + [seg[1] for seg in reflabels.entries])
    # pl.axis([1, oindices[-1], None, None])
    # pl.grid(True)
    # pl.xlabel("output")
    # pl.ylabel("reference")


########################################



def timenorm_tonecontour_dtw(reftrack, track):
    #normalise location:
    tmean = deepcopy(reftrack)
    tmean.values = tmean.values - tmean.values.mean()
    #normalise location:
    t1 = deepcopy(track)
    t1.values = t1.values - t1.values.mean()
    #smooth function to facilitate smoother warping:
    s = UnivariateSpline(t1.times, t1.values)
    t1.values = s(t1.times).reshape((-1, 1))
    #align:
    dtw = dtw_align(tmean, t1)
    #construct new track using mapping:
    newtrack = Track()
    newtrack.times = np.copy(tmean.times)
    values = np.zeros(len(tmean), np.float64)
    for i in range(len(tmean)):
        es = [e[1] for e in dtw[2] if e[0] == i]
        values[i] = np.mean(track.values[es])
    newtrack.values = values.reshape((-1, 1))
    smoothtrack = newtrack.newtrack_from_sspline(newtrack.times, s=len(newtrack.times)/10.0)
    return smoothtrack


def dtw_distances(track, track2, metric="euclidean", VI=None):

    cumdist, dist, path = track.dtw_align(track2, metric=str(metric), VI=VI)

    framedists = []
    frametimes = []
    for pathcoord in path:
        x, y = pathcoord
        framedists.append(dist[x][y])
        frametimes.append(track.times[x])

    t = Track()
    t.values = np.array(framedists)
    t.values = t.values.reshape(-1, 1)
    t.times = np.array(frametimes)
    
    return t


def linearpath_distances(track, track2, metric="euclidean", VI=None):

    dist = cdist(track.values, track2.values, metric=str(metric), VI=VI)
    framedists = []
    try:
        for i in range(len(track.times)):
            framedists.append(dist[i][i])
    except IndexError:
        pass
    t = Track()
    t.values = np.array(framedists)
    t.values = t.values.reshape(-1, 1)
    t.times = np.array([track.times[i] for i in range(len(t.values))])
    if track2.numframes != track.numframes:
        print("linearpath_distances: WARNING: num frames difference is %s" % (track2.numframes - track.numframes))
    return t


def distances(track, track2, method="dtw", metric="euclidean", VI=None):

    if method == "dtw":
        return track.dtw_distances(track2, metric=metric, VI=VI)
    if method == "linear":
        return track.linearpath_distances(track2, metric=metric, VI=VI)
    else:
        raise NotImplementedError("method: " + method)


def mask_indices(track, intervals):
    """ return indices falling within intervals:
        [[starttime, endtime], [starttime, endtime], ...]
    """
    indices = np.array([], dtype=int)
    for interval in intervals:
        ca = track.times >= interval[0]
        cb = track.times < interval[1]
        indices = np.append(indices, np.nonzero(ca & cb))
        #indices.extend([e[1] for e in zip(track.times, range(len(track.times))) if e[0] >= interval[0] and e[0] < interval[1]])
    return indices


def gradient(track, h=2):
    """Estimate of the gradient using a window length 'h'... must be even... number of points is h+1
    """
    assert h % 2 == 0
    n = h // 2

    #timesteps must be constant
    period = track.times[1] - track.times[0]

    times = track.times[n:-n].copy()
    values = np.zeros(len(times), dtype=track.values.dtype)

    for i in range(len(values)):
        values[i] = (track.values[i+h] - track.values[i]) / (h * period)

    t = Track()
    t.times = times
    t.values = values
    return t
    
    

