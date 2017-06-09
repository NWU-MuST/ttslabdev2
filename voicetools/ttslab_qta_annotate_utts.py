#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Do batch qTA analysis (feature extraction) given dirs of aligned
   Utterances and F0 tracks. Annotate utts in-place.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os, sys
import json
from glob import glob

import numpy as np

import ttslab
from ttslab.qta import qta_annotate_utt
from ttslab.hrg import Utterance
ttslab.extend(Utterance, "ufuncs_analysis")


def annotate_utt(args):
    uttfn, f0fn, qtaspecs = args
    basename = os.path.basename(uttfn).split(".")[0]
    print("PROCESSING: " + basename)

    utt = ttslab.fromfile(uttfn)
    f0 = ttslab.fromfile(f0fn)
    utt.fill_startendtimes()

    if qtaspecs:
        utt = qta_annotate_utt(utt, f0, qtaspecs)
    else:
        utt = qta_annotate_utt(utt, f0)
    ttslab.tofile(utt, uttfn)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('uttdir', metavar='UTTDIR', type=str, help="directory containing aligned Utterance files (.utt.pickle)")
    parser.add_argument('f0dir', metavar='F0DIR', type=str, help="directory with corresponding F0 files -- basenames matching (.track.pickle)")
    parser.add_argument('--qtaspecsfn', metavar='QTASPECSFN', type=str, help="qTA parameter search config: ranges and quantisation (.json)")
    args = parser.parse_args()

    try:
        import multiprocessing
        POOL = multiprocessing.Pool(processes=multiprocessing.cpu_count())
        def map(f, i):
            return POOL.map(f, i, chunksize=1)
    except ImportError:
        pass

    if args.qtaspecsfn:
        with open(args.qtaspecsfn) as infh:
            qtaspecs = json.load(infh)
    else:
        qtaspecs = None

    uttfns = sorted(glob(os.path.join(args.uttdir, "*.utt.pickle")))
    f0fns = sorted(glob(os.path.join(args.f0dir, "*.track.pickle")))

    assert len(uttfns) == len(f0fns)
    for uttfn, f0fn in zip(uttfns, f0fns):
        assert os.path.basename(f0fn).startswith(os.path.basename(uttfn)[:-len(".utt.pickle")])

    map(annotate_utt, [(uttfn, f0fn, qtaspecs) for uttfn, f0fn in zip(uttfns, f0fns)])
