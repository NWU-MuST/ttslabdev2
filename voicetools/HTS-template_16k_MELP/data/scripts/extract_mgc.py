#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function #Py2
###

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys, os
import multiprocessing
from glob import glob
import subprocess

def shell(cmd):
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).communicate()[0]

def extract_mgc(parms):

    minimum = shell("%(x2x)s +sf %(infn)s | %(minmax)s | %(x2x)s +fa | head -n 1" % parms)
    maximum = shell("%(x2x)s +sf %(infn)s | %(minmax)s | %(x2x)s +fa | tail -n 1" % parms)
    if int(minimum) <= -32768 or int(maximum) >= 32767:
        print("WARNING: Samples not in correct range in %s (SKIPPING!)" % parms["infn"])

    cmds = ("%(x2x)s +sf %(infn)s | " +
            "%(frame)s -l %(framelen)s -p %(frameshift)s | " +
            "%(window)s -l %(framelen)s -L %(fftlen)s -w %(windowtype)s -n %(normalize)s | " +
            "%(mgcep)s -a %(freqwarp)s -m %(mgcorder)s -l %(fftlen)s -e %(epsilon)s > " + 
            "%(outfn)s")
    subprocess.call(cmds % parms, shell=True)


if __name__ == "__main__":

    try:
        import multiprocessing
        POOL = multiprocessing.Pool(processes=multiprocessing.cpu_count())
        def map(f, i):
            return POOL.map(f, i, chunksize=1)
    except ImportError:
        pass

    argnames = ["x2x", "minmax", "frame", "framelen", "frameshift", "window",
                "fftlen", "windowtype", "normalize", "mgcep",
                "freqwarp", "mgcorder", "epsilon"]
    assert len(argnames) == len(sys.argv[1:])
    args = dict(zip(argnames, sys.argv[1:]))
    #make parms:
    parms = []
    for fn in glob(os.path.join("raw", "*.raw")):
        tempd = dict(args)
        tempd["infn"] = fn
        base = os.path.basename(fn).rstrip(".raw")
        tempd["outfn"] = os.path.join("mgc", base + ".mgc")
        parms.append(tempd)
    #run:
    map(extract_mgc, parms)
