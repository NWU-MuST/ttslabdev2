#!/bin/env python
# -*- coding: utf-8 -*-
"""
    Uses "praat" and "sig2fv" to  extract features pitch synchronously
    saving the results in HTK format file...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__      = "Daniel van Niekerk"
__email__       = "dvn.demitasse@gmail.com"

import os
import sys
import math

import subprocess
import struct
from tempfile import NamedTemporaryFile

PRAAT_BIN = "praat"
SIG2FV_BIN = "/home/demitasse/LOCAL/bin/sig2fv"
PRAAT_GET_PM = \
"""#
form Fill attributes
   text input_wav_file_name
endform

Read from file... 'input_wav_file_name$'
endtime = Get end time
printline 'endtime'

To PointProcess (periodic, cc)... %(min_pitch)s %(max_pitch)s
num_pmarks = Get number of points
#printline 'num_pmarks'
for i from 1 to num_pmarks
        time = Get time from index... i
        printline 'time:7'
endfor
"""


class PMExtractor():
    """ Facilitates pitchmark extraction using "praat" and filling of
        non-periodic parts with default stepsize marks...
    """

    PRAAT_BIN = PRAAT_BIN
    PRAAT_GET_PM = PRAAT_GET_PM

    def __init__(self, min_pitch=50.0, max_pitch=200.0, def_stepsize=0.005):
        """Initialise...
        """
        self.pitchmarks = []
        self.min_pitch = min_pitch
        self.max_pitch = max_pitch
        self.def_stepsize = def_stepsize


    def pm_fill(self, new_end):
        """ This function is basically a port of the same named function in speechtools/sigpr/pitchmark.cc
            by Gerrit Botha.
        """

        new_pm = []
        min = float(1.0/self.max_pitch)
        max = float(1.0/self.min_pitch)
        default = self.def_stepsize

        npm = 0
        last = 0.0
        dropped=0
        added=0

        for j in range(0,len(self.pitchmarks)):
            current = float(self.pitchmarks[j])

            if (current > new_end):
                break

            if ((current - last) < min):
                # drop current pitchmark
                dropped = dropped + 1
            elif ((current-last) > max):
                # interpolate
                num = int(math.floor((current - last)/float(default)))
                size = float(current-last)/float(num)
                for i in range(1,num + 1):
                    new_pm.append(float(last + i * float(size)))
                    npm = npm + 1
                    added = added + 1
            else:
                new_pm.append(self.pitchmarks[j])
                npm = npm + 1

            last=current


        if ((new_end - last) > max):
            # interpolate
            num = int(math.floor((new_end - last)/float(default)))
            size = float(float(new_end -last)/float(num))
            for i in range(1,num + 1):
                new_pm.append(float(last + i * float(size)))
                npm = npm + 1
                added = added + 1

        self.pitchmarks = new_pm


    def write_est_file(self, pitchmark_file):
        """Writes the self.pitchmarks sequence to an ASCII EST file...
           Author: Gerrit Botha
        """
        number_of_frames  = len(self.pitchmarks); 

        if not isinstance(pitchmark_file, file):
            outfile = open(pitchmark_file, "wb")
        else: #open file passed in...
            outfile = pitchmark_file
        outfile.write("EST_File Track\n")
        outfile.write("DataType ascii\n")
        outfile.write("NumFrames " + str(number_of_frames) + "\n")
        outfile.write("NumChannels 0\n")
        outfile.write("NumAuxChannels 0\n")
        outfile.write("EqualSpace 0\n")
        outfile.write("BreaksPresent true\n")
        outfile.write("EST_Header_End\n")
        for i in range(0,len(self.pitchmarks)):
            outfile.write(str(self.pitchmarks[i]))
            for i in range(len((str(self.pitchmarks[i])))-1,7):
                outfile.write('0')
            outfile.write("\t1\n")
        if not isinstance(pitchmark_file, file):
            outfile.close()
        #otherwise we assume the caller will close the file...


    def get_pmarks(self, wavfilelocation):
        """Use "praat" to extract pmarks for periodic parts...
        """
        
        #write temp file - Praat script
        tempfh = NamedTemporaryFile()
        tempfh.write(PMExtractor.PRAAT_GET_PM % {"min_pitch" : self.min_pitch,
                                                 "max_pitch" : self.max_pitch})
        tempfh.flush()

        p = subprocess.Popen(" ".join([PMExtractor.PRAAT_BIN,
                                       tempfh.name,
                                       wavfilelocation]),
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             close_fds = True,
                             shell = True)
        stdout_text = p.communicate()[0]
        tempfh.close()

        values = stdout_text.split()
        
        self.pitchmarks = map(float, values[1:])
        
        endtime = float(values[0])

        self.pm_fill(endtime)
        self.pm_fill(endtime)   # [sic]



class FeatExtractor():
    """Facilitates pitch synchronous feature extraction to HTK file format...
    """

    SIG2FV_BIN = SIG2FV_BIN
    HTK_BYTES_PER_VAL = 4  #Use 32bit floating point values....
    HTK_USER_KIND = 9

    def __init__(self,
                 min_pitch=50.0,
                 max_pitch=200.0,
                 def_stepsize=0.005,
                 preemph_coef=0.97,
                 windowfactor=2.0,
                 fbank_order=26,
                 melcep_order=12,
                 lifter_coef=22,
                 window_type="hamming",
                 coefs_type="melcep energy",
                 delta_type="melcep energy",
                 acc_type="melcep energy"):
        """ Initialise parms...
        """

        self.def_stepsize = def_stepsize
        self.min_pitch = min_pitch
        self.max_pitch = max_pitch
        self.preemph_coef = preemph_coef
        self.windowfactor = windowfactor
        self.fbank_order = fbank_order
        self.melcep_order = melcep_order
        self.lifter_coef = lifter_coef
        self.window_type = window_type
        self.coefs_type = coefs_type
        self.delta_type = delta_type
        self.acc_type = acc_type
        self.featvectors = []
        self.numchannels = 0

        
    def _read_ascii_est_featfile(self, estfilename):
        """ Very specialised reading of EST file...
        """
        
        header = {}
        featvectors = {}

        in_header = True
        with open(estfilename) as infh:
            for line in infh:
                if line.strip() == "EST_Header_End":
                    #sanity checks
                    if (header["EST_File"] != "Track" or
                        header["DataType"] != "ascii" or
                        header["BreaksPresent"] != "true"):
                        raise Exception("Incompatible feature file...")
                    in_header = False
                    continue
                if in_header:
                    linelist = line.split()
                    header[linelist[0]] = linelist[1]
                else:
                    linelist = map(float, line.split())
                    featvectors[linelist[0]] = linelist[2:]     #ignoring "Breaks" field...

        #more sanity checks...
        if len(featvectors) != int(header["NumFrames"]):
            raise Exception("'NumFrames' does not match number of frames read...")
        self.numchannels = int(header["NumChannels"])
        for t in featvectors:
            if len(featvectors[t]) != self.numchannels:
                raise Exception("Channels/Feature-components missing at '%s'" % t)

        return featvectors
    
            
    def write_htk_featfile(self, featfilelocation):
        """ Writes features to HTK feature file...
        """

        if len(self.featvectors) == 0:
            raise Exception("No features loaded... Cowardly refusing to write empty file...")

        with open(featfilelocation, "wb") as outfh:
        
            # write header
            header = struct.pack(">IIHH",
                                 len(self.featvectors),
                                 int(self.def_stepsize * 10000000),
                                 self.numchannels * FeatExtractor.HTK_BYTES_PER_VAL,
                                 FeatExtractor.HTK_USER_KIND)
            outfh.write(header)

            #write frames
            for frame_time in sorted(self.featvectors):
                framestring = ""
                for value in self.featvectors[frame_time]:
                    framestring += struct.pack(">f", value)
                outfh.write(framestring)

    
    def write_times(self, timesfilelocation):
        """ Writes the time instants of feature extraction...
        """

        with open(timesfilelocation, "w") as outfh:
            outfh.write("\n".join(map(str, sorted(self.featvectors))))
        


    def get_feats(self, wavfilelocation):
        """ Use 'praat' and 'sig2fv' to get features...
        """

        pme = PMExtractor(self.min_pitch, self.max_pitch, self.def_stepsize)
        pme.get_pmarks(wavfilelocation)
        
        temp_pm_fh = NamedTemporaryFile()
        pme.write_est_file(temp_pm_fh.name)
        temp_pm_fh.flush()
        
        temp_feat_fh = NamedTemporaryFile()

        p = subprocess.Popen([FeatExtractor.SIG2FV_BIN,
                              wavfilelocation,
                              "-pm",
                              temp_pm_fh.name,
                              "-o",
                              temp_feat_fh.name,
                              "-otype",
                              "est",
                              "-preemph",
                              str(self.preemph_coef),
                              "-factor",
                              str(self.windowfactor),
                              "-fbank_order",
                              str(self.fbank_order),
                              "-melcep_order",
                              str(self.melcep_order),
                              "-lifter",
                              str(self.lifter_coef),
                              "-window_type",
                              str(self.window_type),
                              "-coefs",
                              str(self.coefs_type),
                              "-delta",
                              str(self.delta_type),
                              "-acc",
                              str(self.acc_type)])
        p.communicate()
        temp_pm_fh.close()

        self.featvectors = self._read_ascii_est_featfile(temp_feat_fh.name)
        temp_feat_fh.close()        


def test_pme():
    #PITCHMARKS EXTRACTION
    pme = PMExtractor()
    pme.get_pmarks("/home/demitasse/TRUNK/htkparmfiles/data_001.wav")
    #for pm in pme.pitchmarks:
    #    print pm
    pme.write_est_file("/home/demitasse/TRUNK/htkparmfiles/data_001.pm")


def test_fe():
    fe = FeatExtractor()
    fe.get_feats("/home/demitasse/TRUNK/htkparmfiles/data_001.wav")
    print(len(fe.featvectors))
    #for t in sorted(fe.featvectors):
    #    print fe.featvectors[t]
    fe.write_htk_featfile("pitchsynch_data_001.mfc")
    fe.write_times("pitchsynch_data_001.times")

def test():
    #test_pme()
    test_fe()


if __name__ == "__main__":

    test()
    
