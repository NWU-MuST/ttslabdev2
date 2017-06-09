#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Creates a ttslab word unit catalogue using aligned utterances and
    corresponding wave files...

    DEMITASSE: THIS NEEDS A SERIOUS REWRITE...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os
import sys
from collections import defaultdict
from glob import glob
import copy
from tempfile import mkstemp
from ConfigParser import ConfigParser

import numpy as np

from wav2psmfcc import PMExtractor
from make_f0_praat_script import script_writer as F0_PSCWriter
from make_f0_praat import f0filler as F0Filler
import ttslab
import ttslab.hrg as hrg
ttslab.extend(hrg.Utterance, "ufuncs_analysis")
from ttslab.trackfile import Track

SAVE_COMPLETE_UTTS = True
#sometimes the limit needs to be increased to pickle large utts...
BIGGER_RECURSION_LIMIT = 20000   #default is generally 1000

WAV_DIR = "wavs"
PM_DIR = "pm"
LPC_DIR = "lpc"
F0_DIR = "f0"
MCEP_DIR = "mcep"
JOIN_DIR = "joincoef"
UTT_DIR = "utts"
COMPLETE_UTT_DIR = "complete_utts"

WAV_EXT = "wav"
RES_EXT = "wav"
UTT_EXT = "utt.pickle"
LPC_EXT = "lpc"
MCEP_EXT = "mcep"
RES_EXT = "res"
JOIN_EXT = "join"
PM_EXT = "pm"
F0_EXT = "f0"

NAME = "ttslab_make_wordunits.py"
SIG2FV_BIN = "sig2fv"
SIGFILTER_BIN = "sigfilter"

WINDOWFACTOR = 1

########################################
## FUNCTIONS

def make_units(voice, utt_dir):
    """Run synthesizer "feats" process on Utterances to create Unit level
       to generate structure for adding acoustic features...
    """
    print("MAKING UNITS..")
    utts = []
    for uttfilename in sorted(glob(os.path.join(utt_dir, ".".join(["*", UTT_EXT])))):
        print(uttfilename)
        utt = ttslab.fromfile(uttfilename)
        utt = voice.synthesizer(utt, ("feats", None))
        utts.append(utt)
    return utts


########## ADD_FEATS
def add_feats_to_utt(args):
    u, lpc_dir, joincoef_dir, f0_dir = args

    file_id = u["file_id"]
    print("Processing:", file_id)
    u.fill_startendtimes()
    for unit, word in zip(u.gr("Unit"), u.gr("Word")):
        assert unit["name"] == word["name"]
        unit["start"] = word["start"]
        unit["end"] = word["end"]

    lpctrack = Track()
    lpctrack.load_track(".".join([os.path.join(lpc_dir, file_id), LPC_EXT]))
    restrack = Track()
    restrack.load_wave(".".join([os.path.join(lpc_dir, file_id), RES_EXT]))
    jointrack = ttslab.fromfile(".".join([os.path.join(joincoef_dir, file_id), JOIN_EXT]))
    f0track = Track()
    f0track.load_track(".".join([os.path.join(f0_dir, file_id), F0_EXT]))

    #get boundarytimes:
    boundarytimes = []
    for i, unit in enumerate(u.gr("Unit")):
        if i == 0:
            boundarytimes.append(unit["start"])
        boundarytimes.append(unit["end"])

    #convert boundtimes into sample ranges:
    lpcsampleranges = []
    f0sampleranges = []
    joinsamples = []
    for bound in boundarytimes:
        lpcsampleranges.append(lpctrack.index_at(bound))
        f0sampleranges.append(f0track.index_at(bound))
        joinsamples.append(jointrack.values[jointrack.index_at(bound)])

    #get pitchperiods at lpc indices
    lpctimes = np.concatenate(([0.0], lpctrack.times))
    pitchperiod = np.diff(lpctimes)

    units = u.get_relation("Unit").as_list()
    
    assert len(units) == len(lpcsampleranges) - 1
    for jc0, jc1, lti0, lti1, fti0, fti1, i in zip(joinsamples[:-1], joinsamples[1:],
                                                   lpcsampleranges[:-1], lpcsampleranges[1:],
                                                   f0sampleranges[:-1], f0sampleranges[1:],
                                                   units):
#        print(i["name"], "lpctrack[%s:%s]" % (lti0, lti1), "len(lpctrack)=%s" % len(lpctrack))
        i["left-joincoef"] = jc0
        i["right-joincoef"] = jc1
        i["lpc-coefs"] = lpctrack.slice(lti0, lti1, copy=True) #like python indexing/slicing
        if lti0 == 0:
            i["lpc-coefs"].starttime = 0.0
        else:
            i["lpc-coefs"].starttime = lpctrack.times[lti0 - 1]
        i["lpc-coefs"].zero_starttime()
        #For windowfactor=2 (save only samples and assume 16kHz)
        i["residuals"] = restrack.slice(restrack.index_at(lpctrack.times[lti0] - pitchperiod[lti0]),
                                        restrack.index_at(lpctrack.times[lti1] + pitchperiod[lti0])).values
    return u


def add_feats_to_units(utts):
    """ Load acoustic information and populate units...
    """
    print("ADDING FEATS...")

    lpc_dir = os.path.join(os.getcwd(), LPC_DIR)
    joincoef_dir = os.path.join(os.getcwd(), JOIN_DIR)
    f0_dir = os.path.join(os.getcwd(), F0_DIR)

    map(add_feats_to_utt,
        [(utt, lpc_dir, joincoef_dir, f0_dir) for utt in utts])

    return utts
########## ADD_FEATS


########## PITCHMARKS
def extract_pitchmarks(args):
    wavfilename, minpitch, maxpitch, defstep, pm_dir= args

    basename = os.path.splitext(os.path.basename(wavfilename))[0]
    print(basename)
        
    pme = PMExtractor(minpitch, maxpitch, defstep)
    pme.get_pmarks(wavfilename)
    pme.write_est_file(os.path.join(pm_dir, ".".join([basename, PM_EXT])))

def make_pitchmarks(featconfig, wav_dir):
    """ Make 'filled' pitchmarks for future pitch-synchronous feature
        extraction...
    """

    minpitch = int(featconfig.get("PITCH", "MIN"))
    maxpitch = int(featconfig.get("PITCH", "MAX"))
    defstep =  1 / float(featconfig.get("PITCH", "DEFAULT"))
    
    pm_dir = os.path.join(os.getcwd(), PM_DIR)
    os.mkdir(pm_dir)

    print("MAKING PITCHMARKS...")
    map(extract_pitchmarks,
        [(wavfilename, minpitch, maxpitch, defstep, pm_dir)
         for wavfilename in sorted(glob(os.path.join(wav_dir, ".".join(["*", WAV_EXT]))))])
########## PITCHMARKS

########## LPCs
def extract_lpcs(args):
    wavfilename, lpc_order, preemph_coef, window_factor, window_type, lpc_dir, pm_dir = args

    basename = os.path.splitext(os.path.basename(wavfilename))[0]
    # Extract the LPC coefficients
    cmdstring = " ".join([SIG2FV_BIN,
                          wavfilename,
                          "-o",
                          os.path.join(lpc_dir, ".".join([basename, LPC_EXT])),
                          "-otype est",
                          "-lpc_order",
                          lpc_order,
                          "-coefs lpc",
                          "-pm",
                          os.path.join(pm_dir, ".".join([basename, PM_EXT])),
                          "-preemph",
                          preemph_coef,
                          "-factor",
                          window_factor,
                          "-window_type",
                          window_type])
    print(cmdstring)
    os.system(cmdstring)

    # Extract the residual
    cmdstring = " ".join([SIGFILTER_BIN,
                          wavfilename,
                          "-o",
                          os.path.join(lpc_dir, ".".join([basename, RES_EXT])),
                          "-otype riff",
                          "-lpcfilter",
                          os.path.join(lpc_dir, ".".join([basename, LPC_EXT])),
                          "-inv_filter"])
    print(cmdstring)
    os.system(cmdstring)


def make_lpcs(featconfig, wav_dir):
    """ Make lpcs and residuals for synthesis units..
    """
    
    lpc_order = featconfig.get("SIG2FV_LPC", "LPC_ORDER")
    preemph_coef = featconfig.get("SIG2FV_LPC", "PREEMPH_COEF")
    window_factor = featconfig.get("SIG2FV_LPC", "WINDOW_FACTOR")
    window_type = featconfig.get("SIG2FV_LPC", "WINDOW_TYPE")

    lpc_dir = os.path.join(os.getcwd(), LPC_DIR)
    pm_dir = os.path.join(os.getcwd(), PM_DIR)
    os.mkdir(lpc_dir)

    print("MAKING LPCS...")
    map(extract_lpcs,
        [(wavfilename, lpc_order, preemph_coef, window_factor, window_type, lpc_dir, pm_dir)
         for wavfilename in sorted(glob(os.path.join(wav_dir, ".".join(["*", WAV_EXT]))))])

########## LPCs

########## F0s
def extract_f0s(args):
    wavfilename, praatscript, pm_dir, f0_dir = args

    basename = os.path.splitext(os.path.basename(wavfilename))[0]
    print(basename)

    pmfile = os.path.join(pm_dir, ".".join([basename, PM_EXT]))
    f0file = os.path.join(f0_dir, ".".join([basename, F0_EXT]))

    f0file_writer = F0Filler()
    f0file_writer.load_pitchmarks(pmfile)
    f0file_writer.get_praat_f0(praatscript, wavfilename)
    f0file_writer.make_festival_f0(f0file)

def make_f0s(featconfig, wav_dir):
    """ Make f0s for incorporation in join costs..
    """

    f0_dir = os.path.join(os.getcwd(), F0_DIR)
    os.mkdir(f0_dir)
    pm_dir = os.path.join(os.getcwd(), PM_DIR)

    psc_writer = F0_PSCWriter()
    psc_writer.min_pitch = int(featconfig.get("PITCH", "MIN"))
    psc_writer.max_pitch = int(featconfig.get("PITCH", "MAX"))
    psc_writer.default_pitch = int(featconfig.get("PITCH", "DEFAULT"))

    #make the Praat script...
    fd, praatscript = mkstemp()
    psc_writer.create_praat_script(praatscript)

    print("MAKING F0s...")
    map(extract_f0s,
        [(wavfilename, praatscript, pm_dir, f0_dir)
         for wavfilename in sorted(glob(os.path.join(wav_dir, ".".join(["*", WAV_EXT]))))])

    os.close(fd)
    os.remove(praatscript)
########## F0s

########## MCEPs
def extract_mceps(args):
    wavfilename, fbank_order, window_factor, preemph_coef, melcep_order, window_type, melcep_coefs, mcep_dir, pm_dir = args

    basename = os.path.splitext(os.path.basename(wavfilename))[0]
    # Extract the MELCEP coefficients
    cmdstring = " ".join([SIG2FV_BIN,
                          "-fbank_order",
                          fbank_order,
                          "-factor",
                          window_factor,
                          "-preemph",
                          preemph_coef,
                          "-melcep_order",
                          melcep_order,
                          "-window_type",
                          window_type,
                          wavfilename,
                          "-otype est",
                          "-coefs",
                          melcep_coefs,
                          "-o",
                          os.path.join(mcep_dir, ".".join([basename, MCEP_EXT])),
                          "-pm",
                          os.path.join(pm_dir, ".".join([basename, PM_EXT]))])
    print(cmdstring)
    os.system(cmdstring)


def make_joincoefs(featconfig, wav_dir):
    """ Make joincoefs...
    """
    
    mcep_dir = os.path.join(os.getcwd(), MCEP_DIR)
    os.mkdir(mcep_dir)
    join_dir = os.path.join(os.getcwd(), JOIN_DIR)
    os.mkdir(join_dir)
    pm_dir = os.path.join(os.getcwd(), PM_DIR)
    f0_dir = os.path.join(os.getcwd(), F0_DIR)

    fbank_order = featconfig.get("SIG2FV_MCEP", "FBANK_ORDER")
    melcep_order = featconfig.get("SIG2FV_MCEP", "MELCEP_ORDER")
    melcep_coefs = featconfig.get("SIG2FV_MCEP", "MELCEP_COEFS")
    preemph_coef = featconfig.get("SIG2FV_MCEP", "PREEMPH_COEF")
    window_factor = featconfig.get("SIG2FV_MCEP", "WINDOW_FACTOR")
    window_type = featconfig.get("SIG2FV_MCEP", "WINDOW_TYPE")
    
    print("MAKING JOINCOEFS...")
    map(extract_mceps,
        [(wavfilename, fbank_order, window_factor, preemph_coef, melcep_order, window_type, melcep_coefs, mcep_dir, pm_dir)
         for wavfilename in sorted(glob(os.path.join(wav_dir, ".".join(["*", WAV_EXT]))))])

    print("NORMALISING AND JOINING F0 AND MCEPS...")
    #Normalising mceps and f0s:
    upper = +1.0
    lower = -1.0

    mceptracks = {}
    for fn in glob(os.path.join(mcep_dir, ".".join(["*", MCEP_EXT]))):
        t = Track()
        t.load_track(fn)
        mceptracks[os.path.basename(fn)] = t

    allmcepvecs = np.concatenate([mceptracks[tn].values for tn in sorted(mceptracks)])
    mcepmean = allmcepvecs.mean(0)
    mcepstd = allmcepvecs.std(0)
    for k in mceptracks:
        mceptracks[k].values = (mceptracks[k].values - mcepmean) / (4 * mcepstd) * (upper - lower)

    f0tracks = {}
    for fn in glob(os.path.join(f0_dir, ".".join(["*", F0_EXT]))):
        t = Track()
        t.load_track(fn)
        f0tracks[os.path.basename(fn)] = t

    #allf0vecs = np.concatenate([f0tracks[tn].values for tn in sorted(f0tracks)])
    allf0vecs = np.concatenate([f0tracks[tn].values[f0tracks[tn].values.nonzero()] for tn in sorted(f0tracks)])
    f0mean = allf0vecs.mean(0)
    f0std = allf0vecs.std(0)
    for k in f0tracks:
        f0tracks[k].values = (f0tracks[k].values - f0mean) / (4 * f0std) * (upper - lower)

    #Add f0 to mcep track:
    for k1, k2 in zip(sorted(mceptracks), sorted(f0tracks)):
        mceptracks[k1].values = np.concatenate((mceptracks[k1].values, f0tracks[k2].values), 1)

    for fn in mceptracks:
        basename = os.path.splitext(os.path.basename(fn))[0]
        ttslab.tofile(mceptracks[fn], os.path.join(join_dir, basename + "." + JOIN_EXT))
########## MCEPs


def save_complete_utts(utts):
    """ Save Utterances to file...
    """
    complete_utt_dir = os.path.join(os.getcwd(), COMPLETE_UTT_DIR)

    try:
        print("SAVING COMPLETE UTTS...")
        try:
            os.makedirs(complete_utt_dir)
        except OSError:
            pass
        for utt in utts:
            print(utt["file_id"])
            ttslab.tofile(utt, os.path.join(complete_utt_dir, ".".join([utt["file_id"], UTT_EXT])))
    except RuntimeError:
        #check what kind of monster utt caused the recursion limit to be exceeded...
        #UTTERANCE CHUNKING IS IMPORTANT...
        print(utt)


def make_unit_catalogue(utts):
    
    print("MAKING UNITCATALOGUE...")

    unitcatalogue = defaultdict(list)

    for utt in utts:
        print(utt["file_id"])
        unit_item = utt.get_relation("Unit").head_item
        while unit_item is not None:
            if "lpc-coefs" in unit_item.content.features:     #only save unit if lpc-coefs successfully extracted...
                unitcatalogue[unit_item["name"]].append(unit_item.content.features)

            unit_item = unit_item.next_item
        
    return dict(unitcatalogue)



########################################
## MAIN PROCEDURES

def make_features(featconfig):
    """pitchmark extraction, f0 extraction, lpc and residual
       calculation as well as mcep extraction and adding of f0 to mcep
       tracks to form joincoefs.
    """
    try:
        import multiprocessing
        POOL = multiprocessing.Pool(processes=multiprocessing.cpu_count())
        def map(f, i):
            return POOL.map(f, i, chunksize=1)
    except ImportError:
        pass

    wav_dir = os.path.join(os.getcwd(), WAV_DIR)

    make_pitchmarks(featconfig, wav_dir)
    
    make_lpcs(featconfig, wav_dir)

    make_f0s(featconfig, wav_dir)

    make_joincoefs(featconfig, wav_dir)


def make_catalogue(voice):

    utt_dir = os.path.join(os.getcwd(), UTT_DIR)

    utts = make_units(voice, utt_dir)

    ##
    defaultrecursionlimit = sys.getrecursionlimit()
    sys.setrecursionlimit(BIGGER_RECURSION_LIMIT)
    
    utts = add_feats_to_units(utts)

    if SAVE_COMPLETE_UTTS:
        save_complete_utts(utts)

    sys.setrecursionlimit(defaultrecursionlimit)
    ##
  
    unitcatalogue = make_unit_catalogue(utts)

    print("SAVING UNITCATALOGUE...")
    ttslab.tofile(unitcatalogue, "word_catalogue.pickle")


def auto(featconfig, voice):
    """ Automatic construction with no interaction...
    """

    #make features...
    make_features(featconfig)
    
    #create catalogue...
    make_catalogue(voice)

class CLIException(Exception):
    pass

def main():

     try:
        voicefile = sys.argv[1]
        featconfpath = sys.argv[2]
        switch = sys.argv[3]
     except IndexError:
         print("USAGE: ttslab_make_wordunits.py VOICEFILE FEATSCONF [auto | make_features | make_catalogue]")
         sys.exit()

     voice = ttslab.fromfile(voicefile)
     with open(featconfpath) as conffh:
         featconfig = ConfigParser()
         featconfig.readfp(conffh)
     try:
         if switch == "auto":
             auto(featconfig, voice)
         elif switch == "make_features":
             make_features(featconfig)
         elif switch == "make_catalogue":
             make_catalogue(voice)
         else:
             raise CLIException
     except CLIException:
         print("USAGE: ttslab_make_wordunits.py VOICEFILE FEATSCONF [auto | make_features | make_catalogue]")
    

if __name__ == "__main__":

    main()

