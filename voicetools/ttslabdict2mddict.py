#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Convert dictionary formats.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os, sys, codecs, json, argparse, itertools

import ttslab

SYLBOUNDCHAR = "."
STRESSMARKERS = set("012")
DEFSTRESSTONE = "0"

def vowelidx(syl, phset):
    for i in range(len(syl)):
        if phset.is_vowel(syl[i]):
            return i
    print("WARNING: Syllable does not contain a vowel...", file=sys.stderr)
    return len(syl)

def maybemap(ph, phmap=None):
    if phmap is None or ph in STRESSMARKERS:
        return ph
    else:
        return phmap[ph]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('phonesetfn', metavar='PHSETFN', type=str, help="phoneset file (pickle) -- needed for vowel definitions")
    parser.add_argument('--outphonemapfn', metavar='OUTPHMAPFN', type=str, help="output phone map filename -- from IPA (tsv)")
    parser.add_argument('--mapreverse', action='store_true', help="apply phone mapping in reverse.")
    parser.add_argument('--defstresstone', metavar='DEFSTRESSTONE', default=DEFSTRESSTONE, help="default stress/tone")
    args = parser.parse_args()

    phonemap = None
    if args.outphonemapfn is not None:
        phonemap = {}
        with codecs.open(args.outphonemapfn, encoding="utf-8") as infh:
            for line in infh:
                a, b = line.split()
                if args.mapreverse:
                    a, b = (b, a)
                phonemap[a] = b

    defstresstone = args.defstresstone
    phset = ttslab.fromfile(args.phonesetfn)
    inphmap = dict([(v, k) for k, v in phset.map.iteritems()])

    for line in sys.stdin:
        fields = unicode(line, encoding="utf-8").split()
        word, pos, stresspat, sylspec = fields[:4]
        assert len(stresspat) == len(sylspec)
        phones = map(lambda x:inphmap[x], fields[4:])
        #print(word, pos, stresspat, sylspec)
        #print(phones)
        
        i = 0
        syls = []
        for n, stress in zip([int(slen) for slen in sylspec], stresspat):
            syl = phones[i:i+n]
            i += n
            voweli = vowelidx(syl, phset)
            if stress != defstresstone:
                syl.insert(voweli+1, stress)
            syls.append(syl)
            #print(" ".join(syl))
        
        print(word.encode("utf-8"), " . ".join([" ".join(map(lambda x: maybemap(x, phonemap), syl)) for syl in syls]).encode("utf-8"), sep="\t")
