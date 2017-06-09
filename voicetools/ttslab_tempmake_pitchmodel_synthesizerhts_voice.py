#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This script makes an HTS synthesizer.

    It looks for specific files and location and should thus be run
    from the appropriate location.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys, os
import codecs
import math

from sklearn.feature_extraction import DictVectorizer 

import ttslab
from ttslab.qta.pitchmodel import PitchModel

HTS_MODELSDIR = "data/hts"
QTA_PITCHMODELSDIR = "data/qta"
QTA_HEIGHTMODELFN = os.path.join(QTA_PITCHMODELSDIR, "pitch_height_model.pickle")
QTA_SLOPEMODELFN = os.path.join(QTA_PITCHMODELSDIR, "pitch_slope_model.pickle")
SYNTH_IMPLEMENTATION = "ttslab.synthesizers.hts_qta"
SYNTHESIZER_FILE = "hts_qta_synthesizer.pickle"
PITCHMODEL_FILE = "qta_pitchmodel.pickle"


PHONESET_FILESUFFIX = "_phoneset.pickle"
PRONUNDICT_FILESUFFIX = "_pronundict.pickle"
PRONUNADDENDUM_FILESUFFIX = "_pronunaddendum.pickle"
G2P_FILESUFFIX = "_g2p.pickle"
VOICE_FILE = "hts_qta_voice.pickle"

def make_voice(synthfile=SYNTHESIZER_FILE, pitchmodelfile=PITCHMODEL_FILE):
    langs=[os.path.basename(os.getcwd())]
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
    synthesizer = ttslab.fromfile(synthfile)
    pitchmodel = ttslab.fromfile(pitchmodelfile)
    voice = Voice(pronun=pronun, synthesizer=synthesizer)
    voice.pitchmodel = pitchmodel
    ttslab.tofile(voice, VOICE_FILE)


def make_fieldencoders(descr):
    d = {}
    for i, field in enumerate(descr):
        featname, cats = field
#        print(featname)
#        print(cats)
        if cats:
            nfields = len(cats) - 1
            dd = {}
            for j, val in enumerate(cats):
                tmp = [0] * nfields
                if j == 0:
                    dd[val] = tmp
                else:
                    tmp[j-1] = 1
                    dd[val] = tmp
            d[i] = dd
    return d

if __name__ == "__main__":
    #later we can get overrides from the CLI arguments
    exec("from %s import Synthesizer" % SYNTH_IMPLEMENTATION)

    try:
        try:
            modelsdir = sys.argv[1]
            synth = Synthesizer(modelsdir=modelsdir)
        except IndexError:
            synth = Synthesizer(modelsdir=HTS_MODELSDIR)
    except IOError:
        print("WARNING: No HTS models found...")
        synth = Synthesizer(modelsdir=None)
    ttslab.tofile(synth, SYNTHESIZER_FILE)

    with open(os.path.join(QTA_PITCHMODELSDIR, "featdescr.txt")) as infh:
        descr = [(line.split()[0], [e for e in line.split()[1:] if e]) for line in infh]
    featencoder = make_fieldencoders(descr)
    with open(os.path.join(QTA_PITCHMODELSDIR, "strengthmax.txt")) as infh:
        strengthmax = float(infh.read().strip())
    
    try:
        pitchmodel = PitchModel(strengthmax, featencoder, heightmodelfn=QTA_HEIGHTMODELFN, slopemodelfn=QTA_SLOPEMODELFN)
    except IOError:
        print("WARNING: No qTA models found...")
        pitchmodel = PitchModel(strengthmax, featencoder)
    ttslab.tofile(pitchmodel, PITCHMODEL_FILE)
    
    make_voice()
