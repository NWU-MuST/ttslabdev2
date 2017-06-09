#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This script takes a voice and attempts to generate questions for
    tree construction in HTS automatically based on the phone features
    defined... it also does this for secondary phonesets..

    The resulting file should be manually reviewed as not all phoneset
    features might be relevant during acoustic model tying.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys

import ttslab

VOICEFN = "voice.pickle"

ALL_CONTEXTS = {"LL": "%s^*",
                "L": "*^%s-*",
                "C": "*-%s+*",
                "R": "*+%s=*",
                "RR": "*=%s@*"}
VOWEL_CONTEXTS = {"C-Syl": "*|%s/C:*"}

if __name__ == "__main__":
    try:
        voicefn = sys.argv[1]
    except IndexError:
        voicefn = None
    try:
        voice = ttslab.fromfile(voicefn or VOICEFN)
    except IOError:
        print("Could not find file: '%s'" % (VOICEFN))
        sys.exit(1)

    for lang in ["main"] + [k for k in voice.pronun if k != "main"]:
        phset = voice.pronun[lang]["phoneset"]
        
        #get all feature categories:
        categories = set()
        for phn in phset.phones:
            categories.update(phset.phones[phn])

        #get feature categories involving vowels:
        vcategories = set()
        for phn in phset.phones:
            if "vowel" in phset.phones[phn]:
                vcategories.update(phset.phones[phn])

        #do all contexts:
        for context in ALL_CONTEXTS:
            for cat in sorted(categories):
                if cat in ["consonant", "vowel", "voiced",
                           "class_consonantal", "class_sonorant", "class_syllabic",
                           "duration_diphthong", "duration_long", "duration_short",
                           "manner_glide", "manner_strident"]:
                    continue
                ###
                if lang == "main":
                    phonelist = [phset.map[phn] for phn in phset.phones if cat in phset.phones[phn]]
                else:
                    phonelist = [voice.phonemap[lang + "_" + phn] for phn in phset.phones if cat in phset.phones[phn]]
                ###
                if lang == "main":
                    if len(phonelist) > 1:
                        print('QS "%s" {%s}' % ("-".join([context, cat]), ",".join([ALL_CONTEXTS[context] % phone for phone in phonelist])))
                else:
                    if len(phonelist) > 1:
                        print('QS "%s" {%s}' % ("-".join([context, lang[:2] + "_" + cat]), ",".join([ALL_CONTEXTS[context] % phone for phone in phonelist])))
            ###
            if lang == "main":
                for phone in [phset.map[phn] for phn in phset.phones]:
                    print('QS "%s" {%s}' % ("-".join([context, phone]), ALL_CONTEXTS[context] % phone))
            else:
                for phone in [voice.phonemap[lang + "_" + phn] for phn in phset.phones]:
                    print('QS "%s" {%s}' % ("-".join([context, lang[:2] + "_" + phone]), ALL_CONTEXTS[context] % phone))

        print()
        # do vowel contexts:
        for context in VOWEL_CONTEXTS:
            for cat in sorted(vcategories):
                ###
                if lang == "main":
                    phonelist = [phset.map[phn] for phn in phset.phones if cat in phset.phones[phn] and "vowel" in phset.phones[phn]]
                else:
                    phonelist = [voice.phonemap[lang + "_" + phn] for phn in phset.phones if cat in phset.phones[phn] and "vowel" in phset.phones[phn]]
                ###
                if lang == "main":
                    if len(phonelist) > 1:
                        print('QS "%s" {%s}' % ("_".join([context, cat]), ",".join([VOWEL_CONTEXTS[context] % phone for phone in phonelist])))
                else:
                    if len(phonelist) > 1:
                        print('QS "%s" {%s}' % ("_".join([context, lang[:2] + "_" + cat]), ",".join([VOWEL_CONTEXTS[context] % phone for phone in phonelist])))
            ###
            if lang == "main":
                for vowel in [phset.map[phn] for phn in phset.phones if "vowel" in phset.phones[phn]]:
                    print('QS "%s" {%s}' % ("_".join([context, vowel]), VOWEL_CONTEXTS[context] % vowel))
            else:
                for vowel in [voice.phonemap[lang + "_" + phn] for phn in phset.phones if "vowel" in phset.phones[phn]]:
                    print('QS "%s" {%s}' % ("_".join([context, lang[:2] + "_" + vowel]), VOWEL_CONTEXTS[context] % vowel))
        print()
