# -*- coding: utf-8 -*-
""" Implementation of the DTW algorithm between numpy arrays
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import numpy as np
cimport numpy as np
from scipy.spatial.distance import cdist

DTYPE_FLOAT = np.float
ctypedef np.float_t DTYPE_FLOAT_t
DTYPE_INT = np.int
ctypedef np.int_t DTYPE_INT_t

def dtw_align(np.ndarray[DTYPE_FLOAT_t, ndim=2] arr,
              np.ndarray[DTYPE_FLOAT_t, ndim=2] arr2,
              metric="euclidean",
              VI=None):
    """DP alignment between numpy arrays
       Returns: cumdist, dist, path (corresponding sample indices)

       The functionality is based on the distance implementations
       available in scipy.spatial.distance.cdist thus refer to
       this documentation for explanation of function args...
    """
    cdef int numframes = arr.shape[0]
    cdef int numframes2 = arr2.shape[0]
    cdef int numchannels = arr.shape[1]
    cdef int numchannels2 = arr2.shape[1]

    assert numchannels == numchannels2, "Tracks don't have the same number of channels..."

    cdef np.ndarray[DTYPE_INT_t, ndim=2] dpp = np.zeros((numframes, numframes2), dtype=DTYPE_INT)
    cdef np.ndarray[DTYPE_FLOAT_t, ndim=2] cumdist = cdist(arr, arr2, metric=metric, VI=VI)
    cdef np.ndarray[DTYPE_FLOAT_t, ndim=2] dist = np.array(cumdist, dtype=DTYPE_FLOAT)
    cdef DTYPE_INT_t i, j, k, c
    cdef DTYPE_FLOAT_t cost = -1
    cdef np.ndarray[DTYPE_INT_t, ndim=1] mapping = np.zeros(numframes, dtype=DTYPE_INT)

    dpp[0, 0] = -1

    for i in range(1, numframes):
        cumdist[i, 0] += cumdist[i-1, 0]
        dpp[i, 0] = -1

    for i in range(1, numframes2):
        cumdist[0, i] += cumdist[0, i-1]
        dpp[0, i] = 1

    for i in range(1, numframes):
        for j in range(1, numframes2):
            if cumdist[i-1, j] < cumdist[i-1, j-1]:
                if cumdist[i, j-1] < cumdist[i-1, j]:
                    cumdist[i, j] += cumdist[i, j-1]
                    dpp[i, j] = 1   #hold
                else: #horizontal best
                    cumdist[i, j] += cumdist[i-1, j]
                    dpp[i, j] = -1  #jump
            elif cumdist[i, j-1] < cumdist[i-1, j-1]:
                cumdist[i, j] += cumdist[i, j-1]
                dpp[i, j] = 1       #hold
            else:
                cumdist[i, j] += cumdist[i-1, j-1]
                dpp[i, j] = 0       #jump

    j = numframes2 - 1
    for i in range(numframes - 1, -1, -1): #n-1 downto 0
        if cost == -1:
            cost = cumdist[i, j]
        mapping[i] = j
        while dpp[i, j] == 1:
            j -= 1
        if dpp[i, j] == 0:
            j -= 1

    path = []
    for i, c in enumerate(mapping):
        if i == 0:
            path.append((i, c))
            continue
        repeating = range(path[-1][-1], c)
        if repeating:
            path.pop()
            for j in repeating:
                path.append((i-1, j))
        path.append((i, c))

    return cumdist, dist, path

