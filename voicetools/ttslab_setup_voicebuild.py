#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Sets up environment for the voice build process...
    Essentially:
      - Create dir structure.
      - Write default configuration files.
      - Downsample and normalise audio levels.
      - Check transcription names against audio files.

    Uses the 'sox' and 'normalize-audio' utilities...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os
import codecs
import shutil
import re

NAME = "ttslab_setup_voicebuild.py"

WAV_EXT = "wav"
ETC_DIR = "etc"
WAV_DIR = "wavs"

SOX_BIN = "sox"
NORMALIZE_AUDIO_BIN = "normalize-audio"

########################################
## SIMPLE FUNCTIONS

def parse_path(fullpath):
    """ Parses "fullpath" to "dirname", "filename", "basename" and "extname"
    """

    dirname = os.path.dirname(fullpath)
    filename = os.path.basename(fullpath)
    
    namelist = filename.split(".")
    if len(namelist) == 1:
        return dirname, filename, namelist[0], ""
    
    basename = ".".join(namelist[:-1])
    extname = namelist[-1]
    
    return dirname, filename, basename, extname


def type_files(filelist, ext):
    """Given a list of filenames and an extension, returns a list of
       all files with specific extension...
    """

    # If last chars (case insensitive) match "."+ext
    return [filename for filename in filelist \
            if filename.lower().endswith("." + ext.lower())]


def write_default_halign_confs(etc_dir):
    """ Write configuration files used for the alignment process...
    """

    default_feats_config = \
"""
[GLOBAL]
TARGETKIND: MFCC_0_D_A_Z
TARGETRATE: 50000.0
SAVECOMPRESSED: T
SAVEWITHCRC: T
WINDOWSIZE: 100000.0
USEHAMMING: T
PREEMCOEF: 0.97
NUMCHANS: 26
CEPLIFTER: 22
NUMCEPS: 12
ENORMALISE: F

[HCOPY]
SOURCEFORMAT: WAVE

[HCOMPV_HVITE]
#Nothing here...
"""
    
    default_hmm_prototype = \
"""
~o <VecSize> 39 <MFCC_0_D_A_Z>
~h "halign_hmmproto"
<BeginHMM>
 <NumStates> 7
 <State> 2
    <Mean> 39
      0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0
    <Variance> 39
      1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0
 <State> 3
    <Mean> 39
      0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0
    <Variance> 39
      1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0
 <State> 4
    <Mean> 39
      0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0
    <Variance> 39
      1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0
 <State> 5
    <Mean> 39
      0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0
    <Variance> 39
      1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0
 <State> 6
    <Mean> 39
      0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0
    <Variance> 39
      1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0
 <TransP> 7
  0.0 1.0 0.0 0.0 0.0 0.0 0.0
  0.0 0.6 0.4 0.0 0.0 0.0 0.0
  0.0 0.0 0.6 0.4 0.0 0.0 0.0
  0.0 0.0 0.0 0.6 0.4 0.0 0.0
  0.0 0.0 0.0 0.0 0.6 0.4 0.0
  0.0 0.0 0.0 0.0 0.0 0.7 0.3
  0.0 0.0 0.0 0.0 0.0 0.0 0.0
<EndHMM>
"""

    default_halign_config = \
"""
[SOURCE]
#data for alignment...

ORTHOGRAPHIC_TRANSCRIPTIONS:
PRONUNCIATION_DICTIONARY:

PHONETIC_TRANSCRIPTIONS: 
PHONETIC_TRANSCRIPTIONS_MAP: 
AUDIO:

#bootstrap data
BOOT_TRANSCRIPTIONS: 
BOOT_TRANSCRIPTIONS_MAP: 
BOOT_AUDIO: 

#general
FEATS_CONFIG: %s
HMM_PROTOTYPE: %s

[PARMS]
WORKING_DIR:
SILENCE_PHONE:
SILENCE_WORD:


[SWITCHES]
NORMALISE_ORTHOGRAPHY: False

# Cross-map transcriptions before bootstrapping...
MAPPEDBOOTSTRAP: False
# Triphones?
CDHMMS: True

MIXTURES_PER_STATE:

#Specifies whether output needs to be cleaned and converted to
#'Human Readable' TextGrid format...
TEXTGRID_OUTPUT: True

#If true, deletes 'models', 'feats' and 'bootfeats' directories after labeling...
POSTCLEANUP: False
""" % ("halign_feats.conf", "halign_hmmproto")

    with codecs.open(os.path.join(etc_dir, "halign_feats.conf"), "w", encoding="utf-8") as outfh:
        outfh.write(default_feats_config)
    with codecs.open(os.path.join(etc_dir, "halign_hmmproto"), "w", encoding="utf-8") as outfh:
        outfh.write(default_hmm_prototype)
    with codecs.open(os.path.join(etc_dir, "halign.conf"), "w", encoding="utf-8") as outfh:
        outfh.write(default_halign_config)


def write_acoustic_feat_conf(etc_dir):
    """ Write configuration governing the way acoustic features are
        extracted from the wavefiles...
    """

    default_feats_config = \
"""
[PITCH]
#Hertz values used by pitchmark and f0 estimation algorithms..
MIN: 75
MAX: 600
DEFAULT: 100

[SIG2FV_MCEP]
FBANK_ORDER: 24
MELCEP_ORDER: 12
MELCEP_COEFS: 'melcep energy'
PREEMPH_COEF: 0.97
WINDOW_FACTOR: 2.5
WINDOW_TYPE: hamming

[SIG2FV_LPC]
LPC_ORDER: 16
PREEMPH_COEF: 0.95
WINDOW_FACTOR: 3
WINDOW_TYPE: hamming

"""
    with codecs.open(os.path.join(etc_dir, "feats.conf"), "w", encoding="utf-8") as outfh:
        outfh.write(default_feats_config)


    
def load_schemefile(utts_location):
    """ Load from Festival style transcriptions file...
    """

    quoted = re.compile('".*"')
    bracketed = re.compile('\(.*\)')

    wordlevel = {}

    with codecs.open(utts_location, encoding="utf-8") as infh:
        lines = infh.readlines()

    for line in lines:
        transcr = quoted.search(line).group().strip("\"")
        whatsleft = re.sub(quoted, "", line)
        key = bracketed.search(whatsleft).group().strip("(").strip(")").strip()
        if key in wordlevel:
            raise Exception("Non unique names present...")
        wordlevel[key] = transcr

    return wordlevel


########################################
## MAIN PROCEDURES


def make_dirs(opts):
    """ Setup directory structure...
    """
    
    voiceroot_dir = opts.voiceroot_dir

    os.mkdir(voiceroot_dir)
    os.mkdir(os.path.join(voiceroot_dir, ETC_DIR))
    os.mkdir(os.path.join(voiceroot_dir, WAV_DIR))


def make_confs(opts):
    """ Create default configs...
    """

    voiceroot_dir = opts.voiceroot_dir

    write_default_halign_confs(os.path.join(voiceroot_dir, ETC_DIR))

    write_acoustic_feat_conf(os.path.join(voiceroot_dir, ETC_DIR))


def import_wavefiles(wav_dir, voiceroot_dir, transcriptions, samplerate):
    """ Copies, downsamples and normalises the wavefiles...
    """

    wav_files = type_files(os.listdir(wav_dir), WAV_EXT)

    print("converting...")
    for wav_file in sorted(wav_files):
        basename = parse_path(wav_file)[2]
        if basename not in transcriptions:
            print("WARNING: '%s' not found in transcription set.." % (basename))
        cmdstring = SOX_BIN + " %s -r %s -c 1 -e signed-integer -b 16 %s" % (os.path.join(wav_dir, wav_file),
                                                                             samplerate,
                                                                             os.path.join(voiceroot_dir, WAV_DIR, wav_file))
        print(cmdstring)
        os.system(cmdstring)

    print("normalising...")
    cmdstring = NORMALIZE_AUDIO_BIN + " -m %s" % (os.path.join(voiceroot_dir, WAV_DIR, "*"))
    print(cmdstring)
    os.system(cmdstring)


def import_data(opts):
    """ Import wavefiles and orthographic transcriptions into voice
        tree...
    """
    
    voiceroot_dir = opts.voiceroot_dir
    utts_location = opts.utts_location
    wav_dir = opts.wav_dir

    transcriptions = load_schemefile(utts_location)
    shutil.copy(utts_location, os.path.join(voiceroot_dir, ETC_DIR))

    import_wavefiles(wav_dir, voiceroot_dir, transcriptions, samplerate=opts.samplerate)
    

########################################
## SCRIPT ADMIN

def parse_arguments():
    """ Setup all possible command line options....
    """
    from optparse import OptionParser

    usage = "usage: %s [OPTIONS]" % (NAME)
    parser = OptionParser(usage=usage)
    parser.add_option("-w",
                      "--wavdir",
                      dest="wav_dir",
                      help="specify location of input wave files.",
                      metavar="WAV_DIR")
    parser.add_option("-u",
                      "--utts",
                      dest="utts_location",
                      help="specify location of file containing orthographic transcriptions.",
                      metavar="UTTS_LOCATION")
    parser.add_option("-o",
                      "--voice_rootdir",
                      dest="voiceroot_dir",
                      help="specify location to create voice tree.",
                      metavar="VOICEROOT_DIR")
    parser.add_option("-r",
                      "--samplerate",
                      dest="samplerate",
                      default="16k",
                      help="specify samplerate of audio files.",
                      metavar="SAMPLERATE")
    
    opts, args = parser.parse_args()
    return opts, args


def main():
    opts, args = parse_arguments()

    make_dirs(opts)

    make_confs(opts)
    
    import_data(opts)


if __name__ == "__main__":
    main()

