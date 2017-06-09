#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This script makes a pronunciation addendum and dictionary from
    simple text files. It requires a phoneset and g2p rules.

    It looks for specific files and location and should thus be run
    from the appropriate location.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import codecs

import ttslab
from ttslab.pronundict import PronunciationDictionary

PRONUNDICT_INFN = "data/pronun/main.pronundict"
DICT_INFN = "data/pronun/main.dict"

ADDENDUM_INFN = "data/pronun/addendum.pronundict"
SIMPLEADDENDUM_INFN = "data/pronun/addendum.dict"

WORDLIST_INFN = "data/pronun/words.txt"
DICT_OUTFN = "main_pronundict.pickle"
ADDENDUM_OUTFN = "main_pronunaddendum.pickle"
PHSET_FILE = "main_phoneset.pickle"
G2P_FILE = "main_g2p.pickle"


def load_simplepronundict(infn, phmap):
    pronundict = {}
    try:
        with codecs.open(infn, encoding="utf-8") as infh:
            for line in infh:
                linelist = line.split()
                pronundict[linelist[0].lower()] = [phmap[phone] for phone in linelist[1:]]
    except IOError:
        pass
    return pronundict

def prepredict(wordsfn, g2p, skipwords):
    with codecs.open(wordsfn, encoding="utf-8") as infh:
        words = [word.strip() for word in infh.readlines() if word.strip() not in skipwords]
    pronundict = {}
    numwords = len(words)
    for i, word in enumerate(words):
        print(("%s/%s: %s" % (i+1, numwords, word)).encode("utf-8"))
        pronundict[word] = g2p.predict_word(word)
    return pronundict

if __name__ == "__main__":
    phset = ttslab.fromfile(PHSET_FILE)
    phmap = dict([(v, k) for k, v in phset.map.items()])
    assert len(phmap) == len(phset.map), "mapping not one-to-one..."
    #load
    #MAIN
    try:
        pronundict = PronunciationDictionary().fromtextfile(PRONUNDICT_INFN, phonemap=phmap)
    except IOError:
        print("WARNING: Could not find '%s'" % PRONUNDICT_INFN)
        pronundict = PronunciationDictionary().fromsimpletextfile(DICT_INFN, phonemap=phmap)
    #ADDENDUM
    try:
        addendum = PronunciationDictionary().fromtextfile(ADDENDUM_INFN, phonemap=phmap)
    except IOError:
        print("WARNING: Could not find '%s'" % ADDENDUM_INFN)
        addendum = PronunciationDictionary().fromsimpletextfile(SIMPLEADDENDUM_INFN, phonemap=phmap)
        
    #pre-predict from wordlist and add to addendum
    try:
        g2p = ttslab.fromfile(G2P_FILE)
        skipwords = set(list(pronundict) + list(addendum))
        addendum.updatefromsimpledict(prepredict(WORDLIST_INFN, g2p, skipwords))
    except IOError:
        print("WARNING: Could not find g2p or word list file (skipping pre-predict)")
    #save
    ttslab.tofile(addendum, ADDENDUM_OUTFN)
    ttslab.tofile(pronundict, DICT_OUTFN)
