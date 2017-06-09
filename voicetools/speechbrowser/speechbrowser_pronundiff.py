#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Generates a list of pronunciations that changed during a
    speechbrowser session.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os
import sys
import codecs

import ttslab

def getpronun(word, phmap):
    pronun = []
    for syl in word.get_daughters():
        for ph in syl.get_daughters():
            pronun.append(phmap[ph["name"]])
    return pronun

if __name__ == "__main__":
    voice = ttslab.fromfile(sys.argv[1])
    transcrlist, pronunlist, commentlist = ttslab.fromfile(sys.argv[2])
    pronuns = {}
    for k in sorted(pronunlist):
        u = ttslab.fromfile(k)
        words = u.gr("SylStructure").as_list()
        assert len(words) == len(pronunlist[k])
        for word, newpronun in zip(words, pronunlist[k]):
            newpronun = newpronun.split()
            pronun = getpronun(word, voice.phonemap)
            if newpronun != pronun:
                if word["name"] in pronuns:
                    if newpronun != pronuns[word["name"]]:
                        print("WARNING, pronunciation conflict: %s (%s) (%s)"
                              % (word["name"], " ".join(pronun[k]), " ".join(newpronun)))
                else:
                    pronuns[word["name"]] = newpronun
    with codecs.open("newaddendum.dict", "w", encoding="utf-8") as outfh:
        for k in sorted(pronuns):
            outfh.write('%s %s\n' % (k, " ".join(pronuns[k])))
    
