#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Generates a list of transcriptions that changed during a
    speechbrowser session.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os
import sys
import codecs

import ttslab

if __name__ == "__main__":
    transcrlist, pronunlist, commentlist = ttslab.fromfile(sys.argv[1])
    transcr = {}
    pronun = {}
    for k in sorted(transcrlist):
        u = ttslab.fromfile(k)
        #print(u["text"], transcrlist[k])
        if u["text"] != transcrlist[k]:
            transcr[os.path.basename(k)[:-len(".utt.pickle")]] = transcrlist[k]
    with codecs.open("newutts.data", "w", encoding="utf-8") as outfh:
        for k in sorted(transcr):
            outfh.write('( %s "%s" )\n' % (k, transcr[k]))
