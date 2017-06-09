#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Print utterance structure...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys

import numpy as np

import ttslab
import ufuncs_analysis
import tfuncs_analysis

if __name__ == '__main__':
    uttfn = sys.argv[1]

    u = ttslab.fromfile(uttfn)
    t = ufuncs_analysis.utt_mceps(u, shift=0.001)
    dtwalignment = tfuncs_analysis.dtw_align(t, t)
    
    for i, e in enumerate(dtwalignment):
        np.savetxt("py.%s.out" % i, e) 
