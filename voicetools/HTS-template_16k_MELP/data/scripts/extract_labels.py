#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys, os
import multiprocessing
from glob import glob
import subprocess


def extract_labels(parms):
    cmds = "python scripts/utt2lab.py mono %(voice)s %(infn)s > %(mono_outfn)s"
    subprocess.call(cmds % parms, shell=True)
    cmds = "python scripts/utt2lab.py full %(voice)s %(infn)s > %(full_outfn)s"
    subprocess.call(cmds % parms, shell=True)


if __name__ == "__main__":

    try:
        import multiprocessing
        POOL = multiprocessing.Pool(processes=multiprocessing.cpu_count())
        def map(f, i):
            return POOL.map(f, i, chunksize=1)
    except ImportError:
        pass

    argnames = ["voice"]
    assert len(argnames) == len(sys.argv[1:])
    args = dict(zip(argnames, sys.argv[1:]))
    #make parms:
    parms = []
    for fn in glob(os.path.join("utts", "*.utt.pickle")):
        tempd = dict(args)
        tempd["infn"] = fn
        base = os.path.basename(fn).rstrip(".utt.pickle")
        tempd["mono_outfn"] = os.path.join("labels/mono", base + ".lab")
        tempd["full_outfn"] = os.path.join("labels/full", base + ".lab")
        parms.append(tempd)
    #run:
    map(extract_labels, parms)
