#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This script compiles a simple "decompounder" from the supplied word
   list.

   It looks for specific files and location and should thus be run
   from the appropriate location.

"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import codecs

import ttslab
import ttslab.decompound

DATA_INFN = "data/decompound/wordlist"
DECOMPOUNDER_FILE = "decompounder.pickle"

if __name__ == "__main__":
    with codecs.open(DATA_INFN, encoding="utf-8") as infh:
        wordlist = infh.read().split()
    csplitter = ttslab.decompound.SimpleCompoundSplitter(wordlist)
    ttslab.tofile(csplitter, DECOMPOUNDER_FILE)
