#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Convert dictionary formats.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os, sys, codecs, json, argparse, itertools

SYLBOUNDCHAR = "."
STRESSMARKERS = set("012")
DEFSTRESSTONE = "0"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--phonemapfn', metavar='PHMAPFN', type=str, help="phone map filename (tsv)")
    parser.add_argument('--mapreverse', action='store_true', help="apply phone mapping in reverse.")
    parser.add_argument('--defstresstone', metavar='DEFSTRESSTONE', default=DEFSTRESSTONE, help="default stress/tone")
    args = parser.parse_args()

    # phonemap = None
    # if args.phonemapfn is not None:
    #     with codecs.open(args.phonemapfn, encoding="utf-8") as infh:
    #         phonemap = json.load(infh)
    phonemap = None
    if args.phonemapfn is not None:
        phonemap = {}
        with codecs.open(args.phonemapfn, encoding="utf-8") as infh:
            for line in infh:
                a, b = line.split()
                if args.mapreverse:
                    a, b = (b, a)
                phonemap[a] = b
    defstresstone = args.defstresstone

    for line in sys.stdin:
        fields = unicode(line, encoding="utf-8").split()
        word = fields[0]
        syms = fields[1:]
        syls = [[]]
        for sym in syms:
            if sym != SYLBOUNDCHAR:
                syls[-1].append(sym)
            else:
                syls.append([])
        stresspat = []
        for i in range(len(syls)):
            stress = STRESSMARKERS.intersection(syls[i])
            assert len(stress) < 2
            if stress:
                stresspat.append(list(stress)[0])
            else:
                stresspat.append(defstresstone)
            syls[i] = [ph for ph in syls[i] if ph not in STRESSMARKERS]
        sylspec = [str(len(syl)) for syl in syls]
        if phonemap:
            phones = [phonemap[ph] for ph in itertools.chain(*syls)]
        else:
            phones = itertools.chain(*syls)
        print(word.encode("utf-8"), "None", "".join(stresspat), "".join(sylspec), " ".join(phones).encode("utf-8"))
