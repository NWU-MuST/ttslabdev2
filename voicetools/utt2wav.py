#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Save waveform embedded in utt...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys

import ttslab

WAV_EXT = "wav"

if __name__ == '__main__':
    try:
        uttfn = sys.argv[1]
    except IndexError:
        print("USAGE: utt2textgrid.py UTTFNAME [WAVEFNAME]")
        sys.exit()

    utt = ttslab.fromfile(uttfn)
    try:
        wavfn = sys.argv[2]
    except IndexError:
        wavfn = ".".join([utt["file_id"], WAV_EXT])
    
    utt["waveform"].write(wavfn)
