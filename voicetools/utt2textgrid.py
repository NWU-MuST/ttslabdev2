#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Convert aligned utterance to textgrid...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys

import ttslab
import ttslab.hrg
ttslab.extend(ttslab.hrg.Utterance, "ufuncs_analysis")

if __name__ == '__main__':
    try:
        uttfn = sys.argv[1]
    except IndexError:
        print("USAGE: utt2textgrid.py UTTFNAME [TEXTGRIDFNAME]")
        sys.exit()
    try:
        tgfn = sys.argv[2]
    except IndexError:
        tgfn = None

    utt = ttslab.fromfile(uttfn)
    utt.fill_startendtimes()
    utt.write_textgrid(tgfn)
