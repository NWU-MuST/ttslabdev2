#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This script takes a voice and classifies phones into broad
   categories for use in bootstrapped HMM-alignment
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys

import ttslab

VOICEFN = "voice.pickle"

CONSONANT = set(["consonant", "class_consonantal"])
VOWEL = set(["vowel"])

PLOSIVE = set(["manner_plosive", "manner_click"])
FRICATIVE = set(["manner_fricative"])
AFFRICATE = set(["manner_affricate"])
NASAL = set(["manner_nasal"])
APPROXIMANT = set(["manner_approximant", "manner_trill"])

SHORT = set(["duration_short"])
LONG = set(["duration_long"])
DIPH = set(["duration_diphthong"])

VOICED = set(["vowel", "voiced"])

if __name__ == "__main__":
    try:
        voicefn = sys.argv[1]
    except IndexError:
        voicefn = None
    try:
        voice = ttslab.fromfile(voicefn or VOICEFN)
    except IOError:
        print("Could not find file: '%s'" % (VOICEFN))
        sys.exit(1)

    for lang in ["main"] + [k for k in voice.pronun if k != "main"]:
        phset = voice.pronun[lang]["phoneset"]
        
        for phn in phset.phones:
            phnfeats = phset.phones[phn]

            if lang == "main":
                p = voice.phonemap[phn]
            else:
                p = voice.phonemap[lang + "_" + phn]
            
            if CONSONANT.intersection(phnfeats):
                f1 = "c"
                if PLOSIVE.intersection(phnfeats):
                    f2 = "p"
                elif FRICATIVE.intersection(phnfeats):
                    f2 = "f"
                elif AFFRICATE.intersection(phnfeats):
                    f2 = "a"
                elif NASAL.intersection(phnfeats):
                    f2 = "n"
                elif APPROXIMANT.intersection(phnfeats):
                    f2 = "x"
                else:
                    raise Exception("Could not map determine consonant manner...")
                if VOICED.intersection(phnfeats):
                    f3 = "v"
                else:
                    f3 = "u"
            elif VOWEL.intersection(phnfeats):
                f1 = "v"
                if SHORT.intersection(phnfeats):
                    f2 = "s"
                elif LONG.intersection(phnfeats):
                    f2 = "l"
                elif DIPH.intersection(phnfeats):
                    f2 = "d"
                else:
                    raise Exception("Could not map determine vowel length/type...")
                f3 = "v"
            else:
                f1 = "p"
                if "pause" in phnfeats:
                    f2 = "l"
                else:
                    f2 = "s"
                f3 = "u"
            print("%s\t%s" % (p, f1+f2+f3))
