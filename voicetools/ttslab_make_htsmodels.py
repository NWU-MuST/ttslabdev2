#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Unpacks and sets the HTS training scripts going...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os
import shutil
from glob import glob
import tarfile

import ttslab

NAME = "ttslab_make_htsmodels.py"

WAV_EXT = "wav"
RAW_EXT = "raw"
UTT_EXT = "utt.pickle"
LAB_EXT = "lab"
FEAT_EXT = "mcep"
HTSME_ENGINE_EXT = "htsme_engine"


#Default options:
DEF_WORKING_DIR = "hts"
DEF_UTTS_DIR = "utts"
DEF_QUESTIONS_FILE = "etc/questions_qst001.hed"
DEF_UTTQUESTIONS_FILE = "etc/questions_utt_qst001.hed"

#HTS Training script vars...
DATASET = "dataset"
SPEAKER = "speaker"
UTT_SUBDIR = "data/utts"
RAW_SUBDIR = "data/raw"
WAV_SUBDIR = "data/wav"
QUESTIONS_SUBDIR = "data/questions"
COMPARE_TMP_SUBDIR = "data/tempcmp"
FILTERS_SUBDIR = "data/filters"
OUTWAV_SUBDIR = "gen/qst001/ver1/hts_engine"
MODELS_SUBDIR = "voices/qst001/ver1"
WITH_SPTK_SEARCH_PATH = os.environ.get("SPTK_BIN")
WITH_HTS_SEARCH_PATH = os.environ.get("HTS_BIN")
WITH_HTS_ENGINE_SEARCH_PATH = os.environ.get("HTS_ENGINE_BIN")
CONFIGURE = "./configure --with-sptk-search-path=%s --with-hts-search-path=%s --with-hts-engine-search-path=%s SPEAKER=%s DATASET=%s LOWERF0=%s UPPERF0=%s SYNVP=False VOICE=%s"
MAKE = "make all"


def train_standard(parms):

    #setup dirs...
    os.makedirs(parms["workingdir"])
    t = tarfile.open(parms["template"], "r:*")
    t.extractall(parms["workingdir"])

    #SETUP FILES
    shutil.copy(parms["questionsfile"], os.path.join(parms["workingdir"], QUESTIONS_SUBDIR))
    shutil.copy(parms["uttquestionsfile"], os.path.join(parms["workingdir"], QUESTIONS_SUBDIR))
    print(os.getcwd())
    for fn in sorted(glob(os.path.join(parms["utts"], "*." + UTT_EXT))):
        print("PROCESSING: %s" % (fn))
        #copy utt with DATASET_SPEAKER_bname to HTS tree:
        shutil.copy(fn, os.path.join(parms["workingdir"], UTT_SUBDIR, "_".join([DATASET, SPEAKER, os.path.basename(fn)])))
        #get raw audio files from utts:
        u = ttslab.fromfile(fn)
        waveform = u["waveform"]
        waveform.write(os.path.join(parms["workingdir"],
                                    RAW_SUBDIR,
                                    "_".join([DATASET, SPEAKER, os.path.basename(fn)])[:-len(UTT_EXT)] + RAW_EXT))
        waveform.write(os.path.join(parms["workingdir"],
                                    WAV_SUBDIR,
                                    "_".join([DATASET, SPEAKER, os.path.basename(fn)])[:-len(UTT_EXT)] + WAV_EXT))
        
    #TRAIN...
    os.chdir(parms["workingdir"])
    os.system(CONFIGURE % (WITH_SPTK_SEARCH_PATH,
                           WITH_HTS_SEARCH_PATH,
                           WITH_HTS_ENGINE_SEARCH_PATH,
                           SPEAKER, DATASET, parms["pitchmin"], parms["pitchmax"],
                           parms["voice"]))
    os.system(MAKE)

    #COPY FILTERS FOR HTSME_ENGINE...
    print("COPYING FILTERS")
    for fn in glob(os.path.join(FILTERS_SUBDIR, ".".join(["*", HTSME_ENGINE_EXT]))):
        destfn = os.path.join(MODELS_SUBDIR, os.path.basename(fn)[:-len(HTSME_ENGINE_EXT) - 1])
        print(fn, destfn)
        shutil.copy(fn, destfn)


########################################
## SCRIPT ADMIN

def parse_arguments():
    """ Setup all possible command line arguments....
    """
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Sets up and performs HTS training...", prog=NAME)
    parser.add_argument("voice",
                        help="specify location of voice file.",
                        metavar="VOICE_FILE")
    parser.add_argument("template",
                        help="specify location of HTS training template script.",
                        metavar="HTS_TEMPLATE")
    parser.add_argument("pitchmin",
                        help="minimum F0 value.",
                        metavar="PITCHMIN",
                        type=int)
    parser.add_argument("pitchmax",
                        help="maximum F0 value.",
                        metavar="PITCHMAX",
                        type=int)
    parser.add_argument("-o", "--workingdir",
                        help="specify location to create HTS training tree.",
                        metavar="WORKING_DIR",
                        default=DEF_WORKING_DIR)
    parser.add_argument("-u", "--utts",
                        help="specify location of training utt files.",
                        metavar="UTTS_DIR",
                        default=DEF_UTTS_DIR)
    parser.add_argument("-q", "--questionsfile",
                        help="specify location of the tree questions file.",
                        metavar="QUESTIONS_FILE",
                        default=DEF_QUESTIONS_FILE)
    parser.add_argument("-Q", "--uttquestionsfile",
                        help="specify location of utterance level tree questions file.",
                        metavar="UTTQUESTIONS_FILE",
                        default=DEF_UTTQUESTIONS_FILE)
    
    return parser.parse_args()


if __name__ == "__main__":
    parms = parse_arguments().__dict__ 
    train_standard(parms)
