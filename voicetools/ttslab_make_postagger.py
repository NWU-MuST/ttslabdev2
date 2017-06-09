#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This script makes trains a postagger instance from tagged text and
   saves it for later use.

   It looks for specific files and location and should thus be run
   from the appropriate location.

"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import codecs

import ttslab
import ttslab.postagger

R_SEED = 42 #Seed for data shuffling in training
N_ITER = 10 #DEMITASSE: specify number of iterations for training (implementation doesn't use dev set)

TRAINDATA_INFN = "data/pos/train.csv"
TESTDATA_INFN = "data/pos/test.csv"
POSTAGGER_FILE = "postagger.pickle"

if __name__ == "__main__":
    trainsents = ttslab.postagger.load_csv(codecs.open(TRAINDATA_INFN, encoding="utf-8").read())
    tagger = ttslab.postagger.PerceptronTagger()
    tagger.train(trainsents, N_ITER, R_SEED)
    ttslab.tofile(tagger, POSTAGGER_FILE)
    testsents = ttslab.postagger.load_csv(codecs.open(TESTDATA_INFN, encoding="utf-8").read())
    correct, total = ttslab.postagger.test(testsents, tagger)
    print("Correct(%):", correct/total*100.0)
