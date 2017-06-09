#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function #Py2
###

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys, os
import re
import multiprocessing
from glob import glob
import subprocess

N = 2 #multiprocessing.cpu_count()

def partition(lst, n): 
    division = len(lst) / float(n) 
    return [ lst[int(round(division * i)): int(round(division * (i + 1)))] for i in xrange(n) ]


def herest(hereststr):
    subprocess.call(hereststr, shell=True)


def erst(hereststr, scpfn, outdirn):
    """ EXAMPLE of hereststr:

        $HEREST -A -C $cfg{'trn'} -D -T 1 -S $scp{'trn'} -I
        $mlf{'mon'} -m 1 -u tmvwdmv -w $wf -t $beam -H $monommf{'cmp'}
        -N $monommf{'dur'} -M $model{'cmp'} -R $model{'dur'}
        $lst{'mon'} $lst{'mon'}
    """
    
    #split train scp:
    n = N
    trainlistall = open(scpfn).read().split()
    trainlists = partition(trainlistall, n)
    for i, trainlist in enumerate(trainlists):
        with open(scpfn + str(i+1), "w") as outfh:
            outfh.write("\n".join(trainlist) + "\n")

    #make cmds:
    parms = []
    for i in range(n):
        arglist = re.sub(scpfn, scpfn + str(i+1), hereststr).split()
        arglist.insert(-2, "-p")
        arglist.insert(-2, str(i+1))
        parms.append(" ".join(arglist))
    map(herest, parms)
    #remove "-S .." and "-I .." from arglist:
    arglist = hereststr.split()
    idx = arglist.index("-S")
    arglist.pop(idx); arglist.pop(idx)
    idx = arglist.index("-I")
    arglist.pop(idx); arglist.pop(idx)
    arglist.insert(-2, "-p")
    arglist.insert(-2, "0")
    #accumulator files as input:
    for i in range(n):
        arglist.append(os.path.join(outdirn, "HER%s.hmm.acc" % (i+1)))
        arglist.append(os.path.join(outdirn, "HER%s.dur.acc" % (i+1)))
    #run:
    herest(" ".join(arglist))
    #cleanup herest "dump files":
    for i in range(n):
        os.remove(os.path.join(outdirn, "HER%s.hmm.acc" % (i+1)))
        os.remove(os.path.join(outdirn, "HER%s.dur.acc" % (i+1)))


if __name__ == "__main__":

    try:
        import multiprocessing
        POOL = multiprocessing.Pool(processes=N)
        def map(f, i):
            return POOL.map(f, i, chunksize=1)
    except ImportError:
        pass

    hereststr, scpfn, outdirn = sys.argv[1:]
    
    erst(hereststr, scpfn, outdirn)
