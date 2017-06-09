#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Script to create an hts_engine compatible "full-context label"
    file from an Utterance...

    Included here (and in hts_labels.py) is a mechanism where the
    central symbol is changed based on value and presence of a
    'hts_symbol' feature in the segment item. This was implemented to
    allow us to experiment with ignoring certain segments during
    training.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys
import time

import ttslab
from ttslab.synthesizers.hts_labels import float_to_htk_int

def utt2lab_full(voice, utt):
    try:
        utt = voice.synthesizer(utt, ("feats", None))
    except:
        print("Failed to run utt2lab_full(), does your voice implementation have an appropriate synthesizer uttprocessor?")
        raise
    return utt["hts_label"]

def utt2lab_mono(voice, utt):  #This duplication/(separate implementation) is not ideal -- should find a place for this in synthesizer implementation.
    phmap = voice.phonemap
    lab = []
    starttime = 0
    for phone_item in utt.get_relation("Segment"):
        if "end" in phone_item:
            endtime = float_to_htk_int(phone_item["end"])
        else:
            endtime = None
        #here we allow for symbols to be overridden based on "hts_symbol":
        if "hts_symbol" in phone_item:
            phonename = phone_item["hts_symbol"]
        else:
            phonename = phmap[phone_item["name"]]

        if endtime is not None:
            lab.append("%s %s " % (unicode(starttime).rjust(10), unicode(endtime).rjust(10)) + phonename)
        else:
            lab.append(phonename + "\n")
        starttime = endtime

    return lab


if __name__ == "__main__":
    try:
        switch = sys.argv[1]
        voicefile = sys.argv[2]
        infilename = sys.argv[3]
    except IndexError:
        print("usage: utt2lab.py [mono|full] [VOICEFILE] [INFILENAME]")
        sys.exit(1)
        
    #Load voice and utt and link...
    voice = ttslab.fromfile(voicefile)
    utt = ttslab.fromfile(infilename)

    if switch == "mono":
        #t1 = time.time()
        lab = utt2lab_mono(voice, utt)
        #print("Time: " + str(time.time() - t1))
    elif switch == "full":
        #t1 = time.time()        
        lab = utt2lab_full(voice, utt)
        #print("Time: " + str(time.time() - t1))
    else:
        print("Invalid switch: %s" % (switch))
        sys.exit(1)

    print("\n".join(lab))
