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


def init_models(parms):

    print("=============== %(phone)s ================" % parms)
    cmds = parms["hinitstr"] % parms
    subprocess.call(cmds, shell=True)
    cmds = parms["hreststr"] % parms
    subprocess.call(cmds, shell=True)


if __name__ == "__main__":

    try:
        import multiprocessing
        POOL = multiprocessing.Pool(processes=multiprocessing.cpu_count())
        def map(f, i):
            return POOL.map(f, i, chunksize=1)
    except ImportError:
        pass

    phonelstfn, hinitstr, hreststr = sys.argv[1:]
    
    with open(phonelstfn) as infh:
        phonelst = [ph for ph in infh.read().split() if ph != ""]
    parms = [{"hinitstr": hinitstr, "hreststr": hreststr, "phone": phone} for phone in phonelst]

    map(init_models, parms)
