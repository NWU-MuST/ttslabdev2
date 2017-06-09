#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This script takes an annotated utterance (where qTA parameters have
been extracted) and dumps training data for regression models -- one
sample per syllable. It uses the PitchModel implementation attached to
the voice.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os, sys

import ttslab

def process_utt(voice, utt):
    vectors = voice.pitchmodel(utt, ("feats", None))["sylpitchfeats"]
    for vector, syl in zip(vectors, utt.gr("Syllable")):
        vector.extend([syl["qta_endheight"], syl["qta_slope"]])
    return vectors

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('voicefn', metavar='VOICEFN', type=str, help="Voice containing PitchModel implementation (.voice.pickle)")
    parser.add_argument('uttfn', metavar='UTTFN', type=str, help="annotated Utterance file, i.e. containing qTA parameters (.utt.pickle)")
    args = parser.parse_args()

    voice = ttslab.fromfile(args.voicefn)
    utt = ttslab.fromfile(args.uttfn)
    
    for vector in process_utt(voice, utt):
        print(" ".join(map(str, vector)))
