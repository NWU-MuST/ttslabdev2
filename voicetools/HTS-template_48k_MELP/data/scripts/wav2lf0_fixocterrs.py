#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Drop in replacement for lf0 extraction in the HTS training demo
    script using Praat, trying to compensate for octave errors
    especially if the voice is slightly hoarse...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys
import array
import math

import numpy as np

import ttslab
from ttslab.trackfile import Track
ttslab.extend(Track, "ttslab.trackfile.funcs.tfuncs_praat")

def friendly_log(f):
    try:
        return math.log(f)
    except ValueError:
        return float('-1e+10')

if __name__ == "__main__":
    fn = sys.argv[1]
    outfn = sys.argv[2]
    minf0 = float(sys.argv[3])
    maxf0 = float(sys.argv[4])

    t = Track()
    t.get_f0(fn, minpitch=minf0, maxpitch=maxf0, timestep=0.005, fixocterrs=True)  #timestep hardcoded here because of hack below...
    #hack aligns samples with equiv from HTS script:
    pad = np.array([0.0, 0.0]).reshape(-1, 1)
    f0hzvalues = np.concatenate([pad, t.values, pad])
    lf0 = array.array(b"f", map(friendly_log, f0hzvalues))
    with open(outfn, "wb") as outfh:
        lf0.tofile(outfh)
