#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Do qTA analysis given aligned Utterance and F0 track input.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os, sys
import json

import numpy as np

import ttslab
import ttslab.qta
from ttslab.hrg import Utterance
ttslab.extend(Utterance, "ufuncs_analysis")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('uttfn', metavar='UTTFN', type=str, help="aligned Utterance file (.utt.pickle)")
    parser.add_argument('f0fn', metavar='F0FN', type=str, help="corresponding F0 file (.track.pickle)")
    parser.add_argument('--qtaspecsfn', metavar='QTASPECSFN', type=str, help="qTA parameter search config: ranges and quantisation (.json)")
    parser.add_argument('--extract', action="store_true", help="extract new parameters and plot instead of using existing annotations.")
    args = parser.parse_args()

    utt = ttslab.fromfile(args.uttfn)
    f0 = ttslab.fromfile(args.f0fn)
    if args.extract:
        utt.fill_startendtimes()

    if args.qtaspecsfn:
        with open(args.qtaspecsfn) as infh:
            qtaspecs = json.load(infh)
        ttslab.pitchsynth.qta.utt_plot(utt, f0, qtaspecs, args.extract)
    else:
        ttslab.pitchsynth.qta.utt_plot(utt, f0, annotate=args.extract)
