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
## Create the Praat script that calculates the F0 values from the pitch definitions ##
## for a specific voice                                                             ##
##                                                                                  ##
######################################################################################
## $Id:: make_f0_praat_script.py 5168 2006-09-27 10:57:45Z aby                    $ ##

import os;

class script_writer:  
    def __init__(self):
        self.min_pitch = 0;
        self.max_pitch = 0;
        self.default_pitch = 0;

    def load_pitchmark_definitions(self,pitchmarks_file):
        f=open(pitchmarks_file,"r");
        r=f.readlines();
        f.close();
        for i in r:
            if (i[0] != "#"):
                a = i.strip();
                a = i.split();
                if (len(a) != 0):
                    if (a[0] == "min"):
                        self.min_pitch = int(a[1]);
                    if (a[0] == "max"):
                        self.max_pitch = int(a[1]);
                    if (a[0] == "default"):
                        self.default_pitch = int(a[1]);

        print
        print "using following pitchmark boundaries:";
        print " minimum pitch = " + str(self.min_pitch);
        print " maximum pitch = " + str(self.max_pitch);
        print " default pitch = " + str(self.default_pitch);
        print


    def create_praat_script(self,script_file):
        f=open(script_file,"w");
        f.write("#####################################################################################\n");
        f.write("##                                                                                 ##\n");
        f.write("##                            HLT Research Group                                   ##\n");
        f.write("##                Meraka Institute & University of Pretoria                        ##\n");
        f.write("##                           Copyright (c) 2006                                    ##\n");
        f.write("##                           All Rights Reserved                                   ##\n");
        f.write("##                                                                                 ##\n");
        f.write("## Permission is hereby granted, free of charge, to use and distribute this        ##\n");
        f.write("## software and its documentation without restriction, including without           ##\n");
        f.write("## limitation the rights to use, copy, modify, merge, publish, distribute,         ##\n");
        f.write("## sub license, and/or sell copies of this work, and to permit persons to          ##\n");
        f.write("## whom this work is furnished to do so, subject to the following conditions:      ##\n");
        f.write("##                                                                                 ##\n");
        f.write("##  * Redistributions of source code must retain the above copyright notice,       ##\n");
        f.write("##    this list of conditions and the following disclaimer.                        ##\n");
        f.write("##  * Any modifications must be clearly marked as such.                            ##\n");
        f.write("##  * Original authors' names are not deleted.                                     ##\n");
        f.write("##  * Neither the name of the Meraka Institute nor the name of the University      ##\n");
        f.write("##    of Pretoria nor the names of its contributors may be used to endorse or      ##\n");
        f.write("##    promote products derived from this software without specific prior           ##\n");
        f.write("##    written permission.                                                          ##\n");
        f.write("##                                                                                 ##\n");
        f.write("##  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS NAMELY     ##\n");
        f.write("##  THE MERAKA INSTITUTE, THE UNIVERSITY OF PRETORIA, AND THE CONTRIBUTORS TO      ##\n");
        f.write("##  THIS WORK \"AS IS\" AND ANY EXPRESS OR IMPLIED WARRANTIES INCLUDING, BUT NOT     ##\n");
        f.write("##  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A        ##\n");
        f.write("##  PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER       ##\n");
        f.write("##  OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,       ##\n");
        f.write("##  EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,            ##\n");
        f.write("##  PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;    ##\n");
        f.write("##  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,       ##\n");
        f.write("##  WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR        ##\n");
        f.write("##  OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF         ##\n");
        f.write("##  ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.                                     ##\n");
        f.write("##                                                                                 ##\n");
        f.write("#####################################################################################\n");
        f.write("##                                                                                 ##\n");
        f.write("## Extract F0 values with voice specific parameters                                ##\n");
        f.write("##                                                                                 ##\n");
        f.write("##                                                                                 ##\n");
        f.write("#####################################################################################\n");
        f.write("form Fill attributes\n");
        f.write("   text input_wav_file_name\n");
        f.write("   text output_praat_pitch_file_name\n");
        f.write("endform\n");
        f.write("Read from file... 'input_wav_file_name$'\n");
        f.write("To Pitch (ac)... 0.0 " + str(self.min_pitch) + " 15 yes 0.03 0.45 0.01 0.35 0.14 " + str(self.max_pitch) + "\n");
        f.write("Smooth... 10\n");
        f.write("Write to short text file... 'output_praat_pitch_file_name$'\n");
        f.write("Remove\n");
        f.close();


    
# Main
def main():
 
    from optparse import OptionParser;
    parser = OptionParser(); 
    parser.add_option("-s","--praat_script",action="store", type="string", dest="script_file", default="bin/praat_f0.psc",
                      help="praat F0 script to be created from pitchmarks definitions for voice [default directory \"bin/praat_f0.psc\"]");
    parser.add_option("-p","--pitchmark_definitions",action="store", type="string", dest="pitchmark_def", default="etc/pitchmark.defs",
                      help="file that contains pitchmark definitions for this voice [default \"etc/pitchmark.defs\"]");
    (options, args) = parser.parse_args()
    print
    if (len(args) == 0):
        print "warning, using default values. Type -h for help";
        print
    print "--input args--"
    print "pitchmarks definition file: %s" % (options.pitchmark_def);
    print "Praat script to be created: %s" % (options.script_file);
    print
  
    # first check for input file
    if (os.access(options.pitchmark_def,os.F_OK) == True):
        myscripter = script_writer();
        # load
        myscripter.load_pitchmark_definitions(options.pitchmark_def);
        # and create script
        myscripter.create_praat_script(options.script_file);
    else:
        print ("Pitchmarks definition file doesn't exist. Exit");

if __name__ == "__main__":
    main();
