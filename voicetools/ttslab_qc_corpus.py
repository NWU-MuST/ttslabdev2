#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys, os
import copy
from glob import glob
import pylab as pl
#sometimes the limit needs to be increased to pickle large utts...
sys.setrecursionlimit(10000) #default is generally 1000

import ttslab
from ttslab.hrg import Utterance
ttslab.extend(Utterance, "ufuncs_analysis")

import speechlabels as sl

UTTDIR = "build/utts"
UTTDIR2 = "build/qc_utts"
RECDIR = "build/halign/labels"


def parse_logl_from_recs(u, ul, closure_phone, phonemap, absl=False):
    frameperiod = 50000
    
    assert u["file_id"] == ul.name
    temp = None
    segs = []
    for seg in ul.segments:
        if seg["name"] == closure_phone:
            temp = [seg["duration"] / frameperiod, seg["score"]]
        else:
            if temp:
                duration = temp[0] + seg["duration"] / frameperiod
                score = (temp[0] * temp[1] + seg["duration"] / frameperiod * seg["score"]) / duration
                segs.append([seg["name"], duration, score])
            else:
                segs.append([seg["name"], seg["duration"] / frameperiod, seg["score"]])
    usegs = u.get_relation("Segment").as_list()
    assert len(segs) == len(usegs)
    #add log likelihood scores to segments:
    for s1, s2 in zip(usegs, segs):
        try:
            assert phonemap[s1["name"]] == s2[0]
        except AssertionError:
            print("WARNING:", s1["name"], s2[0])
        if absl:
            s1["alignlogl"] = abs(s2[2])
        else:
            s1["alignlogl"] = s2[2]
        s1["alignnumframes"] = s2[1]

    #add log likelihood scores to words:
    for w in u.get_relation("Word"):
        numframes = 0
        scores = []
        #get segs belonging to word:
        wsegs = []
        for syl in w.get_item_in_relation("SylStructure").get_daughters():
            wsegs.extend(syl.get_daughters())
        #calc word logl:
        for s in wsegs:
            scores.append(s["alignlogl"] * s["alignnumframes"])
            numframes += s["alignnumframes"]
        if absl:
            w["alignlogl"] = abs(sum(scores) / numframes)
        else:
            w["alignlogl"] = sum(scores) / numframes
        w["alignnumframes"] = numframes
    return u

def uttlindistcalc(args):
    vfname, ufname = args
    voice = ttslab.fromfile(vfname)
    u = ttslab.fromfile(ufname)
    print(u["file_id"], end=" ")
    u2 = copy.deepcopy(u)
    u2 = voice.synthesizer(u2, ("feats", None))                        #redo label from utt (includes alignments if found)
    u2 = voice.synthesizer(u2, ("synth", ["use_labalignments"]))       #synthparms to use label alignments during synthesis
    t = u.utt_distance(u2, method="linear")
    t.name = u["file_id"]
    u["lindists"] = {"utt": u2, "track": t}
    ttslab.tofile(u, os.path.join(UTTDIR2, u["file_id"] + ".utt.pickle"))

def uttdtwdistcalc(args):
    vfname, ufname = args
    voice = ttslab.fromfile(vfname)
    u = ttslab.fromfile(ufname)
    print(u["file_id"], end=" ")
    u2 = voice.synthesize(u["text"], "text-to-wave")
    t = u.utt_distance(u2)
    t.name = u["file_id"]
    u["dtwdists"] = {"utt": u2, "track": t}
    ttslab.tofile(u, os.path.join(UTTDIR2, u["file_id"] + ".utt.pickle"))

def scores(vfname, method="dtw"):
    try:
        os.makedirs(UTTDIR2)
        indirname = UTTDIR
        print("Using utts in %s as input..." % UTTDIR)
    except OSError:
        indirname = UTTDIR2
        print("Using utts in %s as input..." % UTTDIR2)
    if method == "linear":
        map(uttlindistcalc, [[vfname, ufname] for ufname in sorted(glob(os.path.join(indirname, "*")))])
    elif method == "dtw":
        map(uttdtwdistcalc, [[vfname, ufname] for ufname in sorted(glob(os.path.join(indirname, "*")))])
    elif method == "alignlogl":
        for uttfn in sorted(glob(os.path.join(indirname, "*"))):
            print(uttfn)
            u = ttslab.fromfile(uttfn)
            ul = sl.Utterance(os.path.join(RECDIR, u["file_id"] + ".rec"))
            u = parse_logl_from_recs(u, ul, v.pronun["main"]["phoneset"].features["closure_phone"], v.phonemap)
            ttslab.tofile(u, os.path.join(UTTDIR2, u["file_id"] + ".utt.pickle"))

if __name__ == "__main__":
    try:
        import multiprocessing
        POOL = multiprocessing.Pool(processes=multiprocessing.cpu_count())
        def map(f, i):
            return POOL.map(f, i, chunksize=1)
    except ImportError:
        pass

    vfname = sys.argv[1]
    procname = sys.argv[2]

    if procname == "lindists":
        scores(vfname, "linear")
    elif procname == "dtwdists":
        scores(vfname, "dtw")
    elif procname == "alignlogl":
        scores(vfname, "alignlogl")
    else:
        raise NotImplementedError
