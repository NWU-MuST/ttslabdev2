#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This script makes a US synthesizer.

    It looks for specific files and location and should thus be run
    from the appropriate location.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys
import codecs

import ttslab

CATALOGUE_FILE = "data/unitcatalogue.pickle"
SYNTH_IMPLEMENTATION = "ttslab.synthesizers.unitselection"
SYNTHESIZER_FILE = "main_synthesizer.pickle"

if __name__ == "__main__":
    try:
        catfile = sys.argv[1]
        synthfile = sys.argv[2]
    except IndexError:
        print("WARNING: CLI parameters not sufficient, using defaults...")
        catfile = CATALOGUE_FILE
        synthfile = SYNTHESIZER_FILE
        
    #later we can get overrides from the CLI arguments
    exec("from %s import Synthesizer" % SYNTH_IMPLEMENTATION)

    try:
        synth = Synthesizer(unitcataloguefile=catfile)
    except IOError:
        print("WARNING: No US catalogue found...")
        synth = Synthesizer(unitcataloguefile=None)
    
    ttslab.tofile(synth, synthfile)
