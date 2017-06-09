#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys
import os
import multiprocessing
from glob import glob
import subprocess


def extract_lf0(parms):
    cmds = "python scripts/wav2lf0.py %(infn)s %(outfn)s %(lowerf0)s %(upperf0)s"
    subprocess.call(cmds % parms, shell=True)

if __name__ == "__main__":
    try:
        import multiprocessing
        POOL = multiprocessing.Pool(processes=multiprocessing.cpu_count())
        def map(f, i):
            return POOL.map(f, i, chunksize=1)
    except ImportError:
        pass

    argnames = ["lowerf0", "upperf0"]
    assert len(argnames) == len(sys.argv[1:])
    args = dict(zip(argnames, sys.argv[1:]))
    #make parms:
    parms = []
    for fn in glob(os.path.join("wav", "*.wav")):
        tempd = dict(args)
        tempd["infn"] = fn
        base = os.path.basename(fn).rstrip(".wav")
        tempd["outfn"] = os.path.join("lf0", base + ".lf0")
        parms.append(tempd)
    #run:
    map(extract_lf0, parms)
