#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This script makes a g2p from rules and mappings in source text
    files. Or other models.

    It looks for specific files and location and should thus be run
    from the appropriate location.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys, codecs, pickle

import ttslab

JSM_MODEL_INFN = "data/pronun/jsm/model"

ICU_PHONES_INFN = "data/pronun/icu/phones"
ICU_RULES_INFN = "data/pronun/icu/rules"

DNR_RULES_INFN = "data/pronun/dnr/main.rules"
DNR_GNULLS_INFN = "data/pronun/dnr/main.rules.gnulls"
DNR_GRAPHMAP_INFN = "data/pronun/dnr/main.rules.graphmap"
DNR_PHONEMAP_INFN = "data/pronun/dnr/main.rules.phonemap"
G2P_FILE = "main_g2p.pickle"

if __name__ == "__main__":
    try:
        switch = sys.argv[1]
    except IndexError:
        switch = "dnr"
    assert switch in ["dnr", "icu", "jsm"]

    if switch == "dnr":
        from ttslab.g2p_rewrites import *
        #load from files:
        g2p = G2P_Rewrites_Semicolon()
        g2p.load_ruleset_semicolon(DNR_RULES_INFN)
        try:
            g2p.load_gnulls(DNR_GNULLS_INFN)
        except IOError:
            pass
        #map graphs:
        try:
            g2p.load_simple_graphmapfile(DNR_GRAPHMAP_INFN)
            g2p.map_graphs()
        except IOError:
            pass
        #map to phones from onechar to IPA:
        try:
            g2p.load_simple_phonemapfile(DNR_PHONEMAP_INFN)
            g2p.map_phones()
        except IOError:
            pass
    elif switch == "icu":
        from ttslab.g2p_icu import *
        g2p = G2P_ICURules(ICU_PHONES_INFN, ICU_RULES_INFN)
    elif switch == "jsm":
        from ttslab.g2p_jsm import *
        model = pickle.load(open(JSM_MODEL_INFN))
        g2p = G2P_JSM(model)
        
    #save:
    ttslab.tofile(g2p, G2P_FILE)
