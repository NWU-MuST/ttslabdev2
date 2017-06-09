#!/usr/bin/python
######################################################################################
##                                                                                  ##
##                             HLT Research Group                                   ##
##                 Meraka Institute & University of Pretoria                        ##
##                            Copyright (c) 2006                                    ##
##                            All Rights Reserved                                   ##
##                                                                                  ##
##  Permission is hereby granted, free of charge, to use and distribute this        ##
##  software and its documentation without restriction, including without           ##
##  limitation the rights to use, copy, modify, merge, publish, distribute,         ##
##  sub license, and/or sell copies of this work, and to permit persons to          ##
##  whom this work is furnished to do so, subject to the following conditions:      ##
##                                                                                  ##
##   * Redistributions of source code must retain the above copyright notice,       ##
##     this list of conditions and the following disclaimer.                        ##
##   * Any modifications must be clearly marked as such.                            ##
##   * Original authors' names are not deleted.                                     ##
##   * Neither the name of the Meraka Institute nor the name of the University      ##
##     of Pretoria nor the names of its contributors may be used to endorse or      ##
##     promote products derived from this software without specific prior           ##
##     written permission.                                                          ##
##                                                                                  ##
##   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS NAMELY     ##
##   THE MERAKA INSTITUTE, THE UNIVERSITY OF PRETORIA, AND THE CONTRIBUTORS TO      ##
##   THIS WORK "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES INCLUDING, BUT NOT     ##
##   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A        ##
##   PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER       ##
##   OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,       ##
##   EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,            ##
##   PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;    ##
##   OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,       ##
##   WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR        ##
##   OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF         ##
##   ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.                                     ##
##                                                                                  ##
######################################################################################
##                                                                                  ##
## AUTHOR  : Aby Louw                                                               ##
## DATE    : 8 August 2006                                                          ##
##                                                                                  ##
######################################################################################
##                                                                                  ##
## Fill a Festival format F0 file with F0 values calculated by Praat at the         ##
## pitchmark positions                                                              ##
##                                                                                  ##
######################################################################################
## $Id:: make_f0_praat.py 5077 2006-09-15 10:11:09Z aby                           $ ##

import os,sys,commands,math;
from tempfile import mkstemp

class f0filler:       
    def __init__(self):
        self.pitchmarks = [];
        self.f0_praat = [];
        self.time_praat = [];
        self.interval = 0;
        self.x1 = 0;
        
    def load_pitchmarks(self,pitchmarks_file):
        f=open(pitchmarks_file,"r");
        praat_output=f.readlines();
        f.close();

        praat_output_header = praat_output[0:5];
        data = praat_output[8:len(praat_output)];

        pitchmarks = [];
        k = 0;
    
        for i in data:
            pitchmark = i.split();
            pitchmarks.append(pitchmark[0]);
            pitchmarks[k] = (float)(pitchmarks[k])*(float)(1000000);
            pitchmarks[k] = round(pitchmarks[k])
            pitchmarks[k] = (float)(pitchmarks[k])/(float)(1000000)
            k = k + 1;

        self.pitchmarks = pitchmarks;

    def get_praat_f0(self, f0script, wavefile):

        fd, tmp = mkstemp()

        command_string = "praat " + f0script + " " + wavefile + " " + tmp;
        commands.getoutput(command_string);

        f=open(tmp,"r");
        praat_output=f.readlines();
        f.close();
        os.close(fd)
        os.remove(tmp);

        praat_output_header = praat_output[0:10];
        self.interval = float(praat_output_header[6]);
        self.x1 = float(praat_output_header[7]);
        data = praat_output[10:len(praat_output)];

        f0 = [];
        k = 0;

        while (k < len(data)):
            intensity = float(data[k]);
            k= k + 1;
            nCandidates = int(data[k]);
            k= k + 1;
            
            max_strength = 0;
            max_f0 = 0;
            
            for i in range(0,nCandidates):
                frequency = float(data[k]);
                k= k + 1;
                strength = float(data[k]);
                k= k + 1;
                if (strength > max_strength):
                    max_strength = strength;
                    max_f0 = frequency;
                    

            f0.append(max_f0);

        self.f0_praat = f0;

        k = 1;
        for i in self.f0_praat:
            time = ( k - 1 ) * self.interval + self.x1;
            self.time_praat.append(time);
            k = k + 1;

    def make_festival_f0(self, f0file):
        f = open(f0file,"w");
        f.write("EST_File Track\n");
        f.write("DataType ascii\n");
        f.write("NumFrames " + str(len(self.pitchmarks)) + '\n');
        f.write("NumChannels 1\n");
        f.write("NumAuxChannels 0\n");
        f.write("EqualSpace 0\n");
        f.write("BreaksPresent true\n");
        f.write("Channel_0 F0\n");
        f.write("EST_Header_End\n");

        index = 0;
        prev_time = 0.0;
        next_time = self.time_praat[index];

        prev_f0 = 0.0;
        next_f0 = self.f0_praat[index];


        for i in self.pitchmarks:

            this_f0 = 0.0;
            breakp = 0;
            in_interval = False;

            if ((i > prev_time) and
                (i < next_time)):
                in_interval = True;

            while (not(in_interval)):
                if ((index + 1) == len(self.time_praat)):
                    in_interval = True;
                    prev_f0 = 0.0;
                    next_f0 = 0.0;
                    break;

                prev_time = self.time_praat[index];
                prev_f0 = self.f0_praat[index];
                index = index + 1;
                next_time = self.time_praat[index];
                next_f0 = self.f0_praat[index];

                if ((i > prev_time) and
                    (i < next_time)):
                    in_interval = True;

            if ((prev_f0 == 0.0) or (next_f0 == 0.0)):
                this_f0 = 0;
                breakp = 0;
            else:
                this_f0 = ((next_f0 - prev_f0)/(next_time - prev_time))*(i - prev_time) + prev_f0;
                breakp = 1;

            f.write(str(i) + '\t' + str(breakp) + '\t' + str(this_f0) + '\n');

        f.close();
    
# Main
def main():
 
    from optparse import OptionParser;
    parser = OptionParser(); 
    parser.add_option("-s","--praat_script",action="store", type="string", dest="script_file", default="bin/praat_f0.psc",
                      help="praat script used to calculate F0 for this voice [default directory \"bin/praat_pitch_extractor.praat\"]");
    parser.add_option("-w","--wavefile",action="store", type="string", dest="wave_file", 
                      help="wavefile for which f0 must be calculated");
    parser.add_option("-o","--f0file",action="store", type="string", dest="f0_file",
                      help="f0 output file that contains the extracted pitchmark values");

    (options, args) = parser.parse_args();

    # first check for input files
    if (os.access(options.wave_file,os.F_OK) == False):
        print "error, wavefile does not exist. Exit\n";
        sys.exit();

    if (os.access(options.script_file,os.F_OK) == False):
        print "error, praat F0 script does not exist. Exit\n";
        sys.exit();

    basename = options.wave_file.split("./")[1].split("/")[1].split(".")[0];
    pitchmarks_file = os.path.join(os.getcwd(),"pm_praat_filled",basename) + ".praat";
    f0script = os.path.join(os.getcwd(),options.script_file.split("./")[1]);
    wavdir = options.wave_file.split("./")[1].split("/")[0];
    f0dir = options.f0_file.split("./")[1].split("/")[0];
    wavefile = os.path.join(os.getcwd(),wavdir,basename) + ".wav";
    f0file = os.path.join(os.getcwd(),f0dir,basename) + ".f0";

    myf0 = f0filler();
    myf0.load_pitchmarks(pitchmarks_file);
    myf0.get_praat_f0(f0script, wavefile);
    myf0.make_festival_f0(f0file);  

if __name__ == "__main__":
    main();
