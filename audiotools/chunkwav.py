#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Slice potentially large wave files given a TextGrid...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"
__date__ = "2011-10"

import cPickle as pickle #Py2
import os, sys; sys.path.append(os.environ.get("PYTTS_PYTHONPATH"))
###

import wave

import speechlabels as sl


def tg2labelsampleranges(tg, tier, samplerate):
    
    chunks = {}
    starttime = 0.0
    for entry in tg.tiers[tier]:
        if entry[1]: #nonempty
            print(entry[1].zfill(4))
            if entry[1].zfill(4) not in chunks:
                chunks[entry[1].zfill(4)] = (int(starttime*samplerate), int(float(entry[0])*samplerate))
            else:
                print("WARNING: label already existed...")
        starttime = float(entry[0])
    return chunks


if __name__ == "__main__":
    wavfn = sys.argv[1]
    tgfn = sys.argv[2]
    outd = sys.argv[3]
    tier = sys.argv[4]
    
    #open wavfile
    wavfh = wave.open(wavfn)
    wavparms = wavfh.getparams()
    samplerate = wavparms[2]
    #open textgrid
    tg = sl.Utterance(tgfn, tier)
    
    chunks = tg2labelsampleranges(tg, tier, samplerate)

    for label in sorted(chunks):
        print("SAVING:", label)
        wavfh.setpos(chunks[label][0])
        chunk = wavfh.readframes(chunks[label][1] - chunks[label][0])
        outwavfh = wave.open(os.path.join(outd, label + ".wav"), "w")
        outwavfh.setparams(wavparms)
        outwavfh.writeframes(chunk)
        outwavfh.close()
