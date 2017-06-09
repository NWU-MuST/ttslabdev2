#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This script makes a phoneset object and saves this to be loaded by
    other modules and scripts...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys, os

import ttslab

PHONESET_FILE = "main_phoneset.pickle"

if __name__ == "__main__":
    try:
        lang = sys.argv[1]
    except IndexError:
        print("USAGE: ttslab_make_phoneset.py LANG")
        sys.exit(1)
    try:
        exec("from ttslab.lang.%s import Phoneset" % lang)
    except ImportError:
        raise Exception("Could not import ttslab.lang.%s.Phoneset" % lang)
    phoneset = Phoneset()
    ttslab.tofile(phoneset, PHONESET_FILE)
