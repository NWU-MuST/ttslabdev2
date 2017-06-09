#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys
import random

from ttslab_common import partition

SEED = 42

if __name__ == '__main__':
    
    infn = sys.argv[1]
    pn1 = int(sys.argv[2])
    pn2 = int(sys.argv[3])
    outfn1 = sys.argv[4]
    outfn2 = sys.argv[5]
    try:
        debugoutfn = sys.argv[6]
        dbgout = True
    except IndexError:
        pass
    
    infh = open(infn)
    lines = infh.read().splitlines()
    infh.close()

    random.seed(SEED)
    random.shuffle(lines)
    part = partition(lines, pn1 + pn2)
    
    if dbgout:
        dbgoutfh = open(debugoutfn, "w")
        for line in lines:
            dbgoutfh.write(line + "\n")
        dbgoutfh.close()
    
    outfh1 = open(outfn1, "w")
    for i in range(pn1):
        for line in part[i]:
            outfh1.write(line + "\n")
    outfh1.close()

    outfh2 = open(outfn2, "w")
    for i in range(i+1, i+1+pn2):
        for line in part[i]:
            outfh2.write(line + "\n")
    outfh2.close()
