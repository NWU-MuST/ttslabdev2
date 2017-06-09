#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This module contains all that will be necessary to convert the
    necessary base audio resources (such as wav and feature files) to
    formats which can be used by HTK and the rest of HAlign.
"""
from __future__ import unicode_literals, division, print_function # Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import codecs
import os
import sys
import logging
import subprocess
from tempfile import NamedTemporaryFile
from ConfigParser import ConfigParser

from speechlabels import parse_path, type_files

#EXTs
WAVE_EXT = "wav"
MFCC_EXT = "mfc"
#PSMFCC_EXT = "psmfc"
TIMES_EXT = "times"

#BINs
HCOPY_BIN = "HCopy"

log = logging.getLogger("HAlign.Features")

class AudioFeatures(object):
    """ Manages audio and feature files...
    """

    def __init__(self, wavlocation, featsconflocation):
        """ Initialise...
        """
        if not os.path.isdir(wavlocation):
            raise Exception("'%s' is not an existing directory..." % wavlocation)
        
        log.debug(unicode(self) + " loading audio files at '%s'." % (wavlocation))
        self.wavlocation = wavlocation
        self.wavfilelist = type_files(os.listdir(self.wavlocation), WAVE_EXT)
        self.wavfilelist.sort()
        self.hcopy_parms = self._loadFeatConf(featsconflocation)
        

    def _loadFeatConf(self, location):
        """ Load configuration needed for feature extraction...
        """
        log.debug(unicode(self) + " loading config file at '%s'." % (location))

        with codecs.open(location, encoding="utf-8") as fh:
            featcfp = ConfigParser()
            featcfp.readfp(fh)

        return list(featcfp.items("HCOPY")) + list(featcfp.items("GLOBAL"))
      

    def getWavFilelist(self):
        return self.wavfilelist[:]


    def dumpFeatConf(self, f):
        """ Dump configuration to file...
        """
        try:
            for k, v in self.hcopy_parms:
                f.write(k.upper() + " = " + v + "\n")
            f.flush()
        except AttributeError:
            with codecs.open(f, "w", encoding="utf-8") as outfh:
                for k, v in self.hcopy_parms:
                    outfh.write(k.upper() + " = " + v + "\n")


    def dumpSCP(self, f, targetdir):
        """ Dump SCP to file...
        """
        try:
            for filename in self.wavfilelist:
                f.write(os.path.join(self.wavlocation, filename) + " " + \
                        os.path.join(targetdir, ".".join([parse_path(filename)[2], MFCC_EXT])) + "\n")
            f.flush()
        except AttributeError:
            with codecs.open(f, "w", encoding="utf-8") as outfh:
                for filename in self.wavfilelist:
                    outfh.write(os.path.join(self.wavlocation, filename) + " " + \
                                os.path.join(targetdir, ".".join([parse_path(filename)[2], MFCC_EXT])) + "\n")


    def makeFeats(self, targetdir):
        """ Run HCopy to make features...
        """
        if not os.path.isdir(targetdir):
            raise Exception("'%s' is not an existing directory..." % targetdir)
        elif len(os.listdir(targetdir)) != 0:
            print("WARNING: Directory '%s' is not empty..." % targetdir)
            #raise Exception("'%s' is not empty..." % targetdir)
        elif self.hcopy_parms is None:
            raise Exception("HCopy configuration not loaded...")

        #write SCP...
        tempscpfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpSCP(tempscpfh, targetdir)

        #write hcopy.conf
        tempconffh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpFeatConf(tempconffh)

        #execute HCopy...
        p = subprocess.Popen(" ".join([HCOPY_BIN,
                                       "-A",
                                       "-D",
                                       "-V",
                                       "-T",
                                       "1",
                                       "-C",
                                       tempconffh.name,
                                       "-S",
                                       tempscpfh.name]),
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             close_fds = True,
                             shell = True)
        so, se = p.communicate()
        log.info("makeFeats:\n" +
                 "================================================================================\n" +
                 unicode(so, encoding="utf-8") + 
                 "================================================================================\n")
        if bool(se):
            log.warning("makeFeats:\n" +
                        "================================================================================\n" +
                        unicode(se, encoding="utf-8") +
                        "================================================================================\n")
        returnval = p.returncode

        tempscpfh.close()
        tempconffh.close()

        if returnval != 0:
            raise Exception(HCOPY_BIN + " failed with code: " + unicode(returnval))

        return returnval
        

# try:
#     from wav2psmfcc import FeatExtractor
#     import numpy as np
# except ImportError:
#     print("WARNING: Could not import modules necessary to do pitch synchronous feature extraction...")

# def find_closest_index(array, value):
#     """ Returns the index in the array that has the minimum difference
#         with value...
#     """
#     return np.array([abs(avalue - value) for avalue in array]).argmin()

# class PS_AudioFeatures(AudioFeatures):
#     """ Allows pitch synchronous features to be extracted...
#     """

#     def __init__(self, wavlocation, featsconflocation):
#         """ Inherit...
#         """
#         AudioFeatures.__init__(self, wavlocation, featsconflocation)

#     def _loadFeatConf(self, location):
#         """ Load configuration needed for feature extraction...
#         """
#         log.debug(unicode(self) + " loading config file at '%s'." % (location))

#         with codecs.open(location, encoding="utf-8") as fh:
#             featcfp = ConfigParser()
#             featcfp.readfp(fh)

#         return dict(list(featcfp.items("SIG2FV")) + list(featcfp.items("PRAAT")) + list(featcfp.items("GLOBAL")))

#     def makeFeats(self, targetdir):
#         """ Use 'praat' and 'sig2fv' to make feats...
#         """

#         if not os.path.isdir(targetdir):
#             raise Exception("'%s' is not an existing directory..." % targetdir)
#         elif len(os.listdir(targetdir)) != 0:
#             raise Exception("'%s' is not empty..." % targetdir)
#         elif self.hcopy_parms is None:
#             raise Exception("HCopy configuration not loaded...")

#         self.featsdir = targetdir

#         log.info("Making PS Feats in '%s'..." % targetdir)

#         fe = FeatExtractor(min_pitch=float(self.hcopy_parms['minpitch']),
#                            max_pitch=float(self.hcopy_parms['maxpitch']),
#                            def_stepsize=float(self.hcopy_parms['targetrate']) / 10000000,
#                            preemph_coef=self.hcopy_parms['preemcoef'],
#                            windowfactor=self.hcopy_parms['windowfactor'],
#                            fbank_order=self.hcopy_parms['numchans'],
#                            melcep_order=self.hcopy_parms['numceps'],
#                            lifter_coef=self.hcopy_parms['ceplifter'],
#                            window_type=self.hcopy_parms['window_type'],
#                            coefs_type=self.hcopy_parms['coefs_type'],
#                            delta_type=self.hcopy_parms['delta_type'],
#                            acc_type=self.hcopy_parms['acc_type'])

#         for wavfilename in self.wavfilelist:
#             wavfilelocation = os.path.join(self.wavlocation, wavfilename)
#             fe.get_feats(wavfilelocation)
        
#             fe.write_htk_featfile(os.path.join(targetdir, parse_path(wavfilename)[2] + "." + MFCC_EXT))
#             fe.write_times(os.path.join(targetdir, parse_path(wavfilename)[2] + "." + TIMES_EXT))

    
#     def warpMLF(self, inmlflocation, outmlflocation):
#         """ Adjusts actual times in MLF to warped times that HTK uses because
#             of fixed stepsize assumption...
#         """

#         with codecs.open(inmlflocation, encoding="utf-8") as infh:
#             mlflines = infh.readlines()

#         if mlflines[0].strip() != "#!MLF!#":
#             raise Exception("MLF header not found in '%s'" % (inmlflocation))

#         period = int(float(self.hcopy_parms['targetrate']))
    
#         with codecs.open(outmlflocation, "w", encoding="utf-8") as outfh:
#             for line in mlflines:

#                 if line[0].isdigit():    #Then it must be a field with times...
#                     linelist = line.split()
#                     linelist[0] = unicode(find_closest_index(times, int(linelist[0])) * period)
#                     linelist[1] = unicode(find_closest_index(times, int(linelist[1])) * period)
#                     outfh.write(" ".join(linelist) + "\n")
#                 elif line.startswith('"'):
#                     current_basename = parse_path(line.strip().strip('"'))[2]
#                     with codecs.open(os.path.join(self.featsdir, current_basename + "." + TIMES_EXT), encoding="utf-8") as infh:
#                         times = [0] + [float(time.strip()) * 10000000 for time in infh.readlines()]
#                     outfh.write(line)
#                 else:                    #must be a "#!MLF!#" or "."
#                     outfh.write(line)


#     def unwarpRec(self, inreclocation, outreclocation):
#         """ Translates times in a rec file from HTK time to actual time...
#             roughly inverse procedure to what is done in 'warpMLF'
#         """

#         with codecs.open(inreclocation, encoding="utf-8") as infh:
#             reclines = infh.readlines()

#         basename = parse_path(inreclocation)[2]
#         with codecs.open(os.path.join(self.featsdir,  basename + "." + TIMES_EXT), encoding="utf-8") as infh:
#             times = [0] + [int(float(time.strip()) * 10000000) for time in infh.readlines()]

#         period = int(float(self.hcopy_parms['targetrate']))

#         with codecs.open(outreclocation, "w", encoding="utf-8") as outfh:
#             for line in reclines:
#                 if not line[0].isdigit():
#                     raise Exception("Error while parsing '%s'" % (inreclocation))
#                 else:  #all lines should have a start and end time...
#                     linelist = line.split()

#                     # DEMITASSE: Eish... Fix off by a couple errors...
#                     starttime = int(linelist[0])
#                     endtime = int(linelist[1])
#                     if starttime % 10 != 0:
#                         if starttime % 10 >= 5:
#                             print("-%s" % (10 - starttime % 10))
#                             starttime += 10 - starttime % 10
#                         else:
#                             print("+%s" % (starttime % 10))
#                             starttime -= starttime % 10
#                     if endtime % 10 != 0:
#                         if endtime % 10 >= 5:
#                             print("-%s" % (10 - endtime % 10))
#                             endtime += 10 - endtime % 10
#                         else:
#                             print("+%s" % (endtime % 10))
#                             endtime -= endtime % 10


#                     linelist[0] = unicode(times[starttime / period])
#                     linelist[1] = unicode(times[endtime / period])
#                     outfh.write(" ".join(linelist) + "\n")
