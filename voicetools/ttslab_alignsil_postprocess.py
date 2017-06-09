#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Postprocess utts with dangling pauses - adding words to separate
    "phrases" if pause length above threshold, otherwise remove
    inserted pause...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os
import sys

import ttslab
from ttslab.hrg import Utterance
ttslab.extend(Utterance, "ufuncs_analysis")

#sometimes the limit needs to be increased to pickle large utts...
sys.setrecursionlimit(10000) #default is generally 1000

PAUSE_REM_LEN_THRESH = 0.100 #seconds: if less than this, remove inserted pause
PAUSE_BB_LEN_THRESH = 0.300 #seconds: if more than this, split into separate breathgroups

def remphraserel(u):
    for phrase in u.gr("Phrase").as_list():
        phrase.remove()
    del u.relations["Phrase"]
    return u

def phraserelfrompauses(u, remthresh, bbthresh):
    phraserel = u.new_relation("Phrase")
    for word in u.gr("Word"):
        if word is u.gr("Word").head_item:
            currentphrase = phraserel.append_item()
            currentphrase["name"] = "BB"
            currentphrase.add_daughter(word)
            continue
        prevseg = word.gir("SylStructure").first_daughter.first_daughter.gir("Segment").prev_item
        if prevseg["name"] == "pau" and (prevseg["end"] - prevseg["start"]) >= bbthresh:
            currentphrase = phraserel.append_item()
            currentphrase["name"] = "BB"
            currentphrase.add_daughter(word)
        elif prevseg["name"] == "pau" and (prevseg["end"] - prevseg["start"]) < remthresh:
            prevseg.remove_content()
            currentphrase.add_daughter(word)
        else:
            currentphrase.add_daughter(word)
    for phrase in phraserel:
        phrase["start"] = phrase.first_daughter["start"]
        phrase["end"] = phrase.last_daughter["end"]
    return u

if __name__ == "__main__":
    uttin = sys.argv[1]
    try:
        remthresh = float(sys.argv[2]) #in seconds
        bbthresh = float(sys.argv[3])
    except IndexError:
        remthresh = PAUSE_REM_LEN_THRESH
        bbthresh = PAUSE_BB_LEN_THRESH
    try:
        uttoutdir = sys.argv[4]
    except IndexError:
        uttoutdir = os.getcwd()

    u = ttslab.fromfile(uttin)
    u.fill_startendtimes()
    u = remphraserel(u)
    u = phraserelfrompauses(u, remthresh, bbthresh)
        
    ttslab.tofile(u, os.path.join(uttoutdir, u["file_id"] + ".utt.pickle"))
