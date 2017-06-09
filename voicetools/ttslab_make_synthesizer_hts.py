#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This script makes an HTS synthesizer.

    It looks for specific files and location and should thus be run
    from the appropriate location.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys
import codecs

import ttslab

HTS_MODELSDIR = "data/hts"
SYNTH_IMPLEMENTATION = "ttslab.synthesizers.{}"
SYNTHESIZER_FILE = "main_synthesizer.pickle"

if __name__ == "__main__":
    try:
        modelsdir = sys.argv[1]
        synthfile = sys.argv[2]
        implementation = sys.argv[3] #<hts|htstone|htsword>
    except IndexError:
        print("WARNING: CLI parameters not sufficient, using defaults...")
        modelsdir = HTS_MODELSDIR
        synthfile = SYNTHESIZER_FILE
        implementation = "hts"
        
    exec("from %s import Synthesizer" % SYNTH_IMPLEMENTATION.format(implementation))

    try:
        synth = Synthesizer(modelsdir=modelsdir)
    except IOError:
        print("WARNING: No HTS models found...")
        synth = Synthesizer(modelsdir=None)
    
    ttslab.tofile(synth, synthfile)
