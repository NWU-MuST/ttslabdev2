#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generates a list of pronunciations and utterances that changed
   during a speechbrowser session by retokenising the fixed
   orthography.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os
import sys
import codecs
import re
import argparse
from collections import defaultdict
from glob import glob
import unicodedata
import json

import ttslab

SPECIALWORD_CHAR = "_"

SYLBOUND_CHAR = "."
def getpronun(word, voice):
    if word["lang"] is None or word["lang"] == "main":
        langprefix = ""
        phset = voice.pronun["main"]["phoneset"]
    else:
        langprefix = word["lang"] + "_"
        phset = voice.pronun[word["lang"]]["phoneset"]
    pronun = []
    for syl in word.get_daughters():
        try:
            stress = int(syl["tone"])
        except ValueError:
            stress = 0
        for ph in syl.get_daughters():
            pronun.append(phset.map[ph["name"][len(langprefix):]])
            if phset.is_vowel(ph["name"][len(langprefix):]) and stress in [1, 2]:
                pronun.append(str(stress))
        pronun.append(SYLBOUND_CHAR)
    pronun.pop()
    return pronun

def utt2wordsprons(u, voice):
    wordsprons = []
    for w in u.gr("SylStructure"):
        if w["lang"] and w["lang"] != "main":
            wname = "|"+w["name"]
        else:
            wname = w["name"]
        wordsprons.append((wname, getpronun(w, voice)))
    return wordsprons

PUNCTUATION = '!"#$%&()*+,-./:;<=>?@[\\]^`{}~_'.replace(SPECIALWORD_CHAR, "") #don't include APOSTROPHY, PIPE or "SPECIALWORD_CHAR"
def normtokenise(text):
    text = re.sub("([a-z])\|", "\\1 |", text)
    text = re.sub("([a-z])([A-Z])", "\\1 \\2", text)
    text = re.sub("-", " ", text)
    text = re.sub("[{}]+".format(re.escape(PUNCTUATION)), " ", text)
    text = re.sub("\s+", " ", text)
    return text.lower().split()

def add_if_not_in(d, w, p):
    if w in d:
        if not p in d[w]:
            d[w].append(p)
    else:
        d[w].append(p)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('voicefn', metavar='VOICE', type=str, help="Associated voice file (used for access to phone map).")
    parser.add_argument('corpuspath', metavar='CORPUSPATH', type=str, help="Path to utterance files.")
    parser.add_argument('speechbfn', metavar='SPEECHBROWSERSTATE', type=str, help="Speechbrowser state dump file.")
    parser.add_argument('pronunoutfn', metavar='PRONUNOUT', type=str, help="Pronunciation addendum output file.")
    parser.add_argument('transcroutfn', metavar='TRANSCROUT', type=str, help="Transcription addendum output file.")
    parser.add_argument('commentoutfn', metavar='COMMENTOUT', type=str, help="Comments output file.")
    args = parser.parse_args()

    voice = ttslab.fromfile(args.voicefn)
    with codecs.open(args.speechbfn, encoding="utf-8") as infh:
        transcrs, pronuns, comments = json.load(infh)

    #get all current pronuns
    prevpronundict = {}
    print("COLLECTING PREVIOUS PRONUNCIATIONS FROM CORPUS...", file=sys.stderr)
    for i, uttfn in enumerate(sorted(glob(os.path.join(args.corpuspath, "*.utt.pickle")))):
        u = ttslab.fromfile(uttfn)
        print(u["file_id"].encode("utf-8"), end=(" " * 80)+"\r")
        for w in u.gr("SylStructure"):
            prevpronundict[w["name"]] = getpronun(w, voice)
    print()

    transcraddendum = {}
    pronunaddendum = defaultdict(list)
    specialwords = defaultdict(int)
    for uttfn in sorted(pronuns):
        u = ttslab.fromfile(os.path.join(args.corpuspath, os.path.basename(uttfn)))
        orig_wordsprons = utt2wordsprons(u, voice)
        transcr = transcrs[uttfn]
        new_words = normtokenise(transcr)
        new_pronuns = pronuns[uttfn]
        try:
            assert len(orig_wordsprons) == len(new_words)
            assert len(new_pronuns) == len(new_words)
        except AssertionError:
            print("================================================================================", file=sys.stderr)
            print("FATAL: Missmatch found in words in utterance: {}".format(uttfn).encode("utf-8"), file=sys.stderr)
            print("ORIGINAL:", " ".join([e[0] for e in orig_wordsprons]), file=sys.stderr)
            print("NEW     :", " ".join(new_words), file=sys.stderr)
            print("================================================================================", file=sys.stderr)
            raise
        new_transcr = ""
        for origwordpron, newword, newpron in zip(orig_wordsprons, new_words, new_pronuns):
            newpron = newpron.split()
            origword, origpron = origwordpron
            #print("DEMIT:", origword, newword)
            token = re.search(re.escape(newword), transcr, re.IGNORECASE)
            new_transcr += transcr[:token.end()]
            #print(origword, origpron, newword, newpron, token.group(), token.span(), transcr)
            if origword != newword:
                if newword.endswith(SPECIALWORD_CHAR):
                    idx = specialwords[newword]
                    newwordname = newword+str(idx).zfill(2)
                    specialwords[newword] += 1
                    print("ADDING SPECIAL WORD <{}> AS <{}>".format(newword, newwordname).encode("utf-8"), file=sys.stderr)
                    add_if_not_in(pronunaddendum, newwordname, newpron)
                    new_transcr += str(idx).zfill(2)
                elif newword in prevpronundict and newpron != prevpronundict[newword]:
                    print("NEW PRONUNCIATION FOUND FOR REGULAR WORD <{}>".format(newword), file=sys.stderr)
                    add_if_not_in(pronunaddendum, newword, newpron)
                else:
                    print("NEW REGULAR WORD FOUND <{}>".format(newword), file=sys.stderr)
                    add_if_not_in(pronunaddendum, newword, newpron)
            elif origpron != newpron:
                print("NEW PRONUNCIATION FOUND FOR REGULAR WORD <{}>".format(newword), file=sys.stderr)
                add_if_not_in(pronunaddendum, newword, newpron)
            transcr = transcr[token.end():]
        new_transcr += transcr
        if new_transcr != u["inputtext"]:
            transcraddendum[u["file_id"]] = new_transcr
        #print("DEMITOLD: {}".format(transcrs[uttfn]).encode("utf-8"))
        #print("DEMITNEW: {}".format(new_transcr).encode("utf-8"))

    pronunaddendum = dict(pronunaddendum)
    words = list(pronunaddendum.keys())
    words.sort(key=lambda x:x.strip("{}"))
    with codecs.open(args.pronunoutfn, "w", encoding="utf-8") as outfh:
        for word in words:
            for pron in pronunaddendum[word]:
                outfh.write("\t".join([word, " ".join(pron)]) + "\n")

    with codecs.open(args.transcroutfn, "w", encoding="utf-8") as outfh:
        for uttid in sorted(transcraddendum):
            outfh.write('( {} "{}" )\n'.format(uttid, unicodedata.normalize("NFC", transcraddendum[uttid])))

    with codecs.open(args.commentoutfn, "w", encoding="utf-8") as outfh:
        for uttid in sorted(comments):
            if comments[uttid]:
                outfh.write('{}\t{}\n'.format(uttid, comments[uttid]))

