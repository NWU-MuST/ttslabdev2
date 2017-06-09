#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This script takes simple configuration settings and a text file of
   training vectors and trains two independent regression models (for
   height and slope).
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os, sys
import json

import numpy as np
from sklearn import ensemble

import ttslab


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('configfn', metavar='CONFIGFN', type=str, help="Settings for regression model training (.json)")
    parser.add_argument('trainvecsfn', metavar='TRAINVECSFN', type=str, help="Training vectors (.txt)")
    args = parser.parse_args()

    with open(args.configfn) as infh:
        config = json.load(infh)

    trainvecs = np.loadtxt(args.trainvecsfn)
    X = trainvecs[:, :-2]
    height = trainvecs[:, -2]
    slope = trainvecs[:, -1]

    clf = ensemble.RandomForestRegressor(n_estimators=config["n_estimators"], min_samples_leaf=config["minsamples_height"])
    clf = clf.fit(X, height)
    ttslab.tofile(clf, "pitch_height_model.pickle")
    clf = ensemble.RandomForestRegressor(n_estimators=config["n_estimators"], min_samples_leaf=config["minsamples_slope"])
    clf = clf.fit(X, slope)
    ttslab.tofile(clf, "pitch_slope_model.pickle")
