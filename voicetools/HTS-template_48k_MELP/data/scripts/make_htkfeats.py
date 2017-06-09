#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function #Py2
###
"""Not used at the moment.... to be updated to include voicing strength stream...
"""

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys, os
import multiprocessing
from glob import glob
import subprocess
from tempfile import mkstemp


def make_htkfeats(parms):

    fd1, mgc_file = mkstemp(prefix="ttslab_", suffix=".mgc")
    fd2, lf0_file = mkstemp(prefix="ttslab_", suffix=".lf0")
    fd3, cmp_file = mkstemp(prefix="ttslab_", suffix=".cmp")

    cmds = "%(perl)s scripts/window.pl %(mgcdim)s %(mgcfn)s %(mgcwins)s > " + mgc_file
    subprocess.call(cmds % parms, shell=True)
    cmds = "%(perl)s scripts/window.pl %(lf0dim)s %(lf0fn)s %(lf0wins)s > " + lf0_file
    subprocess.call(cmds % parms, shell=True)
    cmds = "%(merge)s +f -s 0 -l %(lf0windim)s -L %(mgcwindim)s " + mgc_file + " < " + lf0_file + " > " + cmp_file
    subprocess.call(cmds % parms, shell=True)
    cmds = "%(perl)s scripts/addhtkheader.pl %(sampfreq)s %(frameshift)s %(byteperframe)s 9 " + cmp_file + " > %(outfn)s"
    subprocess.call(cmds % parms, shell=True)

    os.close(fd1)
    os.close(fd2)
    os.close(fd3)
    os.remove(mgc_file)
    os.remove(lf0_file)
    os.remove(cmp_file)


if __name__ == "__main__":

    try:
        import multiprocessing
        POOL = multiprocessing.Pool(processes=multiprocessing.cpu_count())
        def map(f, i):
            return POOL.map(f, i, chunksize=1)
    except ImportError:
        pass

    argnames = ["mgcorder", "mgcdim", "lf0dim", "nmgcwin", "nlf0win", "mgcwin", "lf0win",
                "perl", "merge", "sampfreq", "frameshift", "byteperframe",
                "mgcwindim", "lf0windim"]
    assert len(argnames) == len(sys.argv[1:])
    args = dict(zip(argnames, sys.argv[1:]))
    #make parms:
    args["mgcwins"] = " ".join([args["mgcwin"] + str(i) for i in range(1, int(args["nmgcwin"]) + 1)])
    args["lf0wins"] = " ".join([args["lf0win"] + str(i) for i in range(1, int(args["nlf0win"]) + 1)])
    del args["mgcwin"]
    del args["nmgcwin"]
    del args["lf0win"]
    del args["nlf0win"]
    parms = []
    for mgcfn, lf0fn in zip(sorted(glob(os.path.join("mgc", "*.mgc"))),
                            sorted(glob(os.path.join("lf0", "*.lf0")))):
        base = os.path.basename(mgcfn)[:-4]
        assert base == os.path.basename(lf0fn)[:-4]
        tempd = dict(args)
        tempd["mgcfn"] = mgcfn
        tempd["lf0fn"] = lf0fn
        tempd["outfn"] = os.path.join("cmp", base + ".cmp")
        parms.append(tempd)
    #run:
    map(make_htkfeats, parms)
