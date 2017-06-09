#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This script makes a voice object by loading sub modules and data
    and initialising the appropriate class...

    It looks for specific files and location and should thus be run
    from the appropriate location.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys, os

import ttslab

PHONESET_FILESUFFIX = "_phoneset.pickle"
PRONUNDICT_FILESUFFIX = "_pronundict.pickle"
PRONUNADDENDUM_FILESUFFIX = "_pronunaddendum.pickle"
G2P_FILESUFFIX = "_g2p.pickle"


def make_voice(langs, synthfile="frontend"):
    pronun = {}
    for i, lang in enumerate(langs):
        if i == 0:
            exec("from ttslab.lang.%(lang)s import Voice" % {"lang": lang})
            langpref = "main"
        else:
            langpref = lang
        pronun[langpref] = {}
        pronun[langpref]["phoneset"] = ttslab.fromfile(langpref + PHONESET_FILESUFFIX)
        pronun[langpref]["pronundict"] = ttslab.fromfile(langpref + PRONUNDICT_FILESUFFIX)
        pronun[langpref]["pronunaddendum"] = ttslab.fromfile(langpref + PRONUNADDENDUM_FILESUFFIX)
        pronun[langpref]["g2p"] = ttslab.fromfile(langpref + G2P_FILESUFFIX)
    if synthfile == "frontend":
        voice = Voice(pronun=pronun, synthesizer=None)
        ttslab.tofile(voice, "frontend.voice.pickle")
    else:
        synthesizer = ttslab.fromfile(synthfile)
        voice = Voice(pronun=pronun, synthesizer=synthesizer)
        ttslab.tofile(voice, "voice.pickle")


if __name__ == "__main__":
    try:
        synthesizerfile = sys.argv[1]
        langs = sys.argv[2:]
        assert len(langs) <= 2
        make_voice(langs, synthesizerfile)
    except (IndexError):
        print("USAGE: ttslab_make_voice.py frontend|SYNTHFILE lang1 [lang2]")
        sys.exit(1)
