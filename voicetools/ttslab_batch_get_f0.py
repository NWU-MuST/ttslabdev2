#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Get f0 values from Praat at a high constant sample rate, with zeros
   in unvoiced sections... Will create the output directory and use
   input basenames.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os, sys
from glob import glob

import numpy as np

import ttslab
from ttslab.trackfile import Track
ttslab.extend(Track, "ttslab.trackfile.funcs.tfuncs_praat")

WAV_EXT = "wav"
TRACK_EXT = "track.pickle"

DEF_OUTDIR = "f0"
DEF_F0MIN = 60.0  #Hz
DEF_F0MAX = 600.0 #Hz
DEF_TSTEP = 0.001

def get_f0(args):
    fn, f0_path, f0min, f0max, tstep, semitones, outf0dir = args
    basename = os.path.basename(fn).split(".")[0]
    print("PROCESSING: " + basename)
    t = Track()
    t.name = basename
    t.get_f0(fn, f0min, f0max, timestep=tstep, semitones=semitones)
    ttslab.tofile(t, os.path.join(outf0dir, basename + "." + TRACK_EXT))

def get_f0s(wav_path, f0_path, f0min, f0max, tstep, semitones, outf0dir):
    map(get_f0, [(fn, f0_path, f0min, f0max, tstep, semitones, outf0dir) for fn in sorted(glob(os.path.join(wav_path, "*")))])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('inwavdir', metavar='INWAVDIR', type=str, help="input directory containing .wav files")
    parser.add_argument('outf0dir', metavar='OUTF0DIR', type=str, default=DEF_OUTDIR, help="output directory for F0 files, will be created.")
    parser.add_argument('--min', metavar='F0MIN', type=float, dest="f0min", default=DEF_F0MIN, help="minimum F0 used during Praat analysis -- default in Hz.")
    parser.add_argument('--max', metavar='F0MAX', type=float, dest="f0max", default=DEF_F0MAX, help="maximum F0 used during Praat analysis -- default in Hz.")
    parser.add_argument('--tstep', metavar='TSTEP', type=float, dest="tstep", default=DEF_TSTEP, help="time interval (seconds) used during Praat analysis.")
    parser.add_argument('--semitones', action="store_true", help="output semitones relative to 1 Hz (note: given min and max should then in semitones, not Hz).")
    args = parser.parse_args()

    try:
        import multiprocessing
        POOL = multiprocessing.Pool(processes=multiprocessing.cpu_count())
        def map(f, i):
            return POOL.map(f, i, chunksize=1)
    except ImportError:
        pass

    if args.semitones:
        f0min, f0max = 2**(args.f0min / 12.0), 2**(args.f0max / 12.0)
    else:
        f0min, f0max = args.f0min, args.f0max

    os.makedirs(args.outf0dir)
    get_f0s("wavs", "f0", f0min, f0max, args.tstep, args.semitones, args.outf0dir)
