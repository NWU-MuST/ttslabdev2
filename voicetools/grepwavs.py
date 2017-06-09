#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Slice potentially large wave files given a TextGrid...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"
__date__ = "2011-10"

import sys
import os
import wave

import speechlabels as sl

NONE_ENTRY = "NONE"

def tg2labelsampleranges(tg, tier, samplerate, bname, none=NONE_ENTRY):
    chunks = {}
    starttime = 0.0
    i = 0
    for entry in tg.tiers[tier]:
        if entry[1] != none: #nonempty
            print(entry[1])
            chunks["_".join([str(i), entry[1], bname])] = (int(starttime*samplerate), int(float(entry[0])*samplerate))
            i += 1
        starttime = float(entry[0])
    return chunks

if __name__ == "__main__":
    tier = sys.argv[1]
    searchtokens = sys.argv[2].lower().split()
    outprefix = sys.argv[3]
    wavfns = sys.argv[4:]
    
    for wavfn in wavfns:
        if not wavfn.endswith(".wav"):
            print("WARNING:", wavfn, "does not have .wav extention... SKIPPING!")
            continue
        bname = os.path.basename(wavfn)[:-len(".wav")]
        #open textgrid
        tgfn = wavfn[:-len(".wav")] + ".TextGrid"
        try:
            print(tgfn)
            tg = sl.Utterance(tgfn, tier)
        except:
            print("WARNING: Could not find TextGrid for", wavfn, "SKIPPING!")
            continue
        utttokens = [entry[1].lower() for entry in tg.tiers[tier] if entry[1] != NONE_ENTRY]
        idxmap = [i for i, entry in enumerate(tg.tiers[tier]) if entry[1] != NONE_ENTRY]
        matches = [(i, i+len(searchtokens)) for i in range(len(utttokens)) if utttokens[i:i+len(searchtokens)] == searchtokens]
        if matches:
            #open wavfile
            wavfh = wave.open(wavfn)
            wavparms = wavfh.getparams()
            samplerate = wavparms[2]
        for i, match in enumerate(matches):
            label = "_".join([str(i).zfill(2), bname])
            idxa = idxmap[match[0]] - 1
            idxb = idxmap[match[1] - 1]
            if idxa >= 0:
                starttime = float(tg.tiers[tier][idxa][0])
            else:
                starttime = 0.0
            endtime = float(tg.tiers[tier][idxb][0])
            startsample = int(starttime*samplerate)
            endsample = int(endtime*samplerate)
            fname = outprefix + str(label) + ".wav"
            print("SAVING:", fname)
            wavfh.setpos(startsample)
            chunk = wavfh.readframes(endsample - startsample)
            outwavfh = wave.open(fname, "w")
            outwavfh.setparams(wavparms)
            outwavfh.writeframes(chunk)
            outwavfh.close()
