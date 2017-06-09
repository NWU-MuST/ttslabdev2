#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This module contains all that will be necessary to initialise and
    train HMM models for the purpose of phonetic alignment...
"""
from __future__ import unicode_literals, division, print_function # Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import codecs
import os
import sys
import re
import logging
import subprocess
import shutil
from tempfile import NamedTemporaryFile, mkdtemp
import tarfile
from ConfigParser import ConfigParser

from speechlabels import parse_path, type_files, triphone_2_monophone

#EXTs
WAVE_EXT = "wav"
MFCC_EXT = "mfc"

#BINs
HINIT_BIN = "HInit"
HREST_BIN = "HRest"
HEREST_BIN = "HERest"
HVITE_BIN = "HVite"
HCOMPV_BIN = "HCompV"
HHED_BIN = "HHEd"

#DIRs
HMM_DIR = "hmm"

#VALs
VFLOOR_VAL = "0.01"
RO_THRESHOLD = "100.0"
TB_THRESHOLD = "350.0"
HEREST_PRUNING_PARM1 = "250.0"
HEREST_PRUNING_PARM2 = "150.0"
HEREST_PRUNING_PARM3 = "1000.0"

#FILENAMES
VFLOORS_FN = "vFloors"
MACROS_FN = "macros"
HMMDEFS_FN = "hmmdefs"


log = logging.getLogger("HAlign.Models")


class HMMSet(object):
    """ Manages HMM models...
    """

    def __init__(self,
                 targetlocation,
                 phonelist,
                 silphone,
                 protofilelocation,
                 featsconflocation,
                 featslocation):
        """ Initialise...
        """

        if not os.path.isdir(targetlocation):
            raise Exception("Target location does not exist...")
        if not os.path.isfile(protofilelocation):
            raise Exception("Invalid protofilelocation '%s'" % protofilelocation)

        log.debug(unicode(self) + " initialising with protofile at '%s'." % (protofilelocation))
        self.targetlocation = targetlocation
        self.phonelist = sorted(set(phonelist + [silphone]))
        self.silphone = silphone
        self.featslocation = featslocation
        self.featfilelist = type_files(os.listdir(self.featslocation), MFCC_EXT)
        self.protofilelocation = protofilelocation
        self.numstates = self._getNumStatesFromProtofile()
        self.iteration = 0
        self.hvite_hcompv_parms = self._loadFeatConf(featsconflocation)


    def _getNumStatesFromProtofile(self):
        """Get the number of states specified in the protofile...
           Determines mix-splitting and triphone tying commands...
        """

        with codecs.open(self.protofilelocation, encoding="utf-8") as infh:
            for line in infh:
                linelist = line.lower().split()
                try:
                    if linelist[0] == "<numstates>":
                        numstates = int(linelist[1])
                        log.debug(unicode(self) + " Number of HMM states from protofile: %s" % (numstates))
                        return numstates
                except IndexError:
                    pass    


    def _loadFeatConf(self, location):
        """ Load configuration needed for feature interpretation...
        """
        log.debug(unicode(self) + " loading config file at '%s'." % (location))

        with codecs.open(location, encoding="utf-8") as fh:
            featcfp = ConfigParser()
            featcfp.readfp(fh)

        return list(featcfp.items("HCOMPV_HVITE")) + list(featcfp.items("GLOBAL"))


    def getModelSet(self):
        """Return the list of model names...
        """
        return self.phonelist[:]


    def dumpFeatConf(self, f):
        """ Dump configuration to file...
        """
        try:
            for k, v in self.hvite_hcompv_parms:
                f.write(k.upper() + " = " + v + "\n")
            f.flush()
        except AttributeError:
            with codecs.open(f, "w", encoding="utf-8") as outfh:
                for k, v in self.hvite_hcompv_parms:
                    outfh.write(k.upper() + " = " + v + "\n")


    def dumpFeatList(self, f):
        """ Dump featlist (SCP) to file...
        """
        try:
            for filename in self.featfilelist:
                f.write(os.path.join(self.featslocation, filename) + "\n")
            f.flush()
        except:
            with codecs.open(f, "w", encoding="utf-8") as outfh:
                for filename in self.featfilelist:
                    outfh.write(os.path.join(self.featslocation, filename) + "\n")


    def dumpPhoneList(self, f):
        """ Dump phonelist (list of models) to file...
        """
        try:
            for phone in self.phonelist:
                f.write(phone + "\n")
            f.flush()
        except:
            with codecs.open(f, "w", encoding="utf-8") as outfh:
                for phone in self.phonelist:
                    outfh.write(phone + "\n")

    def copyBootmodels(self, bootmodels_location, mapnames, transcriptionset=False):
        assert self.iteration == 0, "Can only do this as first training iteration..."
        tempdir = mkdtemp(prefix="halign_")
        t = tarfile.open(bootmodels_location, "r:*")
        t.extractall(tempdir)
        hmmdir = os.path.join(self.targetlocation, HMM_DIR + unicode(self.iteration + 1)) #hmm1
        os.makedirs(hmmdir)
        if mapnames == False:
            for fn in glob(os.path.join(tempdir, "*")):
                shutil.copy(fn, hmmdir)
        else:
            for phone in self.phonelist:
                with open(os.path.join(tempdir, transcriptionset.phonemap[phone])) as infh:
                    modeldef = infh.read()
                modeldef = re.sub('"%s"' % (transcriptionset.phonemap[phone]), '"%s"' % (phone), modeldef)
                with open(os.path.join(hmmdir, phone), "w") as outfh:
                    outfh.write(modeldef)
            shutil.copy(os.path.join(tempdir, MACROS_FN), os.path.join(hmmdir, MACROS_FN))
        with open(os.path.join(hmmdir, MACROS_FN)) as infh:
            macropart = infh.readlines()
        with codecs.open(os.path.join(hmmdir, HMMDEFS_FN), "w", encoding="utf-8") as outfh:
            outfh.writelines(macropart)
            for phone in self.phonelist:
                inhmm = False
                with codecs.open(os.path.join(hmmdir, phone), encoding="utf-8") as infh:
                    for line in infh:
                        if line.strip().upper().startswith("~H"):
                            outfh.write(line)
                            inhmm = True
                            continue
                        if inhmm:
                            outfh.write(line)
        #done!
        shutil.rmtree(tempdir)
        self.iteration += 1


    def mappedBootstrapAll(self, bootmlf_location, bootfeats_location, transcriptionset):
        """ calls doBootstrapAll for mapped bootstrapping...
        """
        self.doBootstrapAll(bootmlf_location, bootfeats_location, transcriptionset)


    def doBootstrapAll(self, bootmlf_location, bootfeats_location, transcriptionset=None):
        """ Initialise HMMs using 'bootstrap' method...
            If transcriptionset is not None, then do mapped bootstrap...
        """
        assert self.iteration == 0, "Can only do this as first training iteration..."

        bootfeatlist = type_files(os.listdir(bootfeats_location), MFCC_EXT)
        bootfeatfilelist = [os.path.join(bootfeats_location, featfname) + "\n" for featfname in bootfeatlist]

        #write SCP...
        tempscpfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        tempscpfh.writelines(bootfeatfilelist)
        tempscpfh.flush()

        #make dir...
        hinit_output_dir = os.path.join(self.targetlocation,
                                  HMM_DIR + unicode(self.iteration))
        hrest_output_dir = os.path.join(self.targetlocation,
                                  HMM_DIR + unicode(self.iteration + 1))
        os.makedirs(os.path.join(hinit_output_dir))
        os.makedirs(os.path.join(hrest_output_dir))
        

        for phone in self.phonelist:
            #hinit
            if transcriptionset is not None:
                tempmlf = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
                transcriptionset.unmapMLF(bootmlf_location, tempmlf.name, phone)
                tempmlf.flush()
                mlf_location = tempmlf.name
            else:
                mlf_location = bootmlf_location
                
            p = subprocess.Popen(" ".join([HINIT_BIN,
                                           "-A",
                                           "-D",
                                           "-V",
                                           "-T",
                                           "1",
                                           "-l",
                                           '"'+phone+'"',
                                           "-o",
                                           '"'+phone+'"',
                                           "-I",
                                           mlf_location,
                                           "-M",
                                           hinit_output_dir,
                                           "-S",
                                           tempscpfh.name,
                                           self.protofilelocation]),
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE,
                                 close_fds = True,
                                 shell = True)
            so, se = p.communicate()
            log.info("doBootstrapAll:\n" +
                     "================================================================================\n" +
                     unicode(so, encoding="utf-8") + 
                     "================================================================================\n")
            if bool(se):
                log.warning("doBootstrapAll:\n" +
                            "================================================================================\n" +
                            unicode(se, encoding="utf-8") +
                            "================================================================================\n")
            returnval = p.returncode
            if returnval != 0:
                raise Exception(HINIT_BIN + " failed with code: " + unicode(returnval))
            #hrest
            p = subprocess.Popen(" ".join([HREST_BIN,
                                           "-A",
                                           "-D",
                                           "-V",
                                           "-T",
                                           "1",
                                           "-l",
                                           '"'+phone+'"',
                                           "-I",
                                           mlf_location,
                                           "-M",
                                           hrest_output_dir,
                                           "-S",
                                           tempscpfh.name,
                                           os.path.join(hinit_output_dir, phone)]),
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE,
                                 close_fds = True,
                                 shell = True)
            so, se = p.communicate()
            log.info("doBootstrapAll:\n" +
                     "================================================================================\n" +
                     unicode(so, encoding="utf-8") + 
                     "================================================================================\n")
            if bool(se):
                log.warning("doBootstrapAll:\n" +
                            "================================================================================\n" +
                            unicode(se, encoding="utf-8") +
                            "================================================================================\n")
            returnval = p.returncode
            if returnval != 0:
                raise Exception(HREST_BIN + " failed with code: " + unicode(returnval))

            if transcriptionset is not None:
                tempmlf.close()
            
        tempscpfh.close()

        ##create "macros" file
        macropart = []
        with codecs.open(os.path.join(hrest_output_dir, self.phonelist[0]), encoding="utf-8") as infh:
            for line in infh:
                if line.strip()[:2].upper() == "~H":
                    break
                else:
                    macropart.append(line)

        with codecs.open(os.path.join(hrest_output_dir, MACROS_FN), "w", encoding="utf-8") as outfh:
            outfh.writelines(macropart)

        ##Concatenate single HMM files into MMF...
        with codecs.open(os.path.join(hrest_output_dir, HMMDEFS_FN), "w", encoding="utf-8") as outfh:
            outfh.writelines(macropart)
            
            for phone in self.phonelist:
                inhmm = False
                with codecs.open(os.path.join(hrest_output_dir, phone), encoding="utf-8") as infh:
                    for line in infh:
                        if line.strip().upper().startswith("~H"):
                            outfh.write(line)
                            inhmm = True
                            continue
                        if inhmm:
                            outfh.write(line)

        #done!
        self.iteration += 1


    def doFlatStart(self):
        """ Initialise HMMs using 'flatstart' method...
        """        
        assert self.iteration == 0, "Can only do this as first training iteration..."

        #write featconf..
        tempconffh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpFeatConf(tempconffh)

        #write SCP...
        tempscpfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpFeatList(tempscpfh)
        
        #make dir...
        output_dir = os.path.join(self.targetlocation,
                                  HMM_DIR + unicode(self.iteration))
        os.makedirs(os.path.join(output_dir))

        #execute HCompV...
        p = subprocess.Popen(" ".join([HCOMPV_BIN,
                                       "-A",
                                       "-D",
                                       "-V",
                                       "-T",
                                       "1",
                                       "-C",
                                       tempconffh.name,
                                       "-f",
                                       VFLOOR_VAL,
                                       "-m",
                                       "-S",
                                       tempscpfh.name,
                                       "-M",
                                       output_dir,
                                       self.protofilelocation]),
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             close_fds = True,
                             shell = True)
        so, se = p.communicate()
        log.info("doFlatStart:\n" +
                 "================================================================================\n" +
                 unicode(so, encoding="utf-8") + 
                 "================================================================================\n")
        if bool(se):
            log.warning("doFlatStart:\n" +
                        "================================================================================\n" +
                        unicode(se, encoding="utf-8") +
                        "================================================================================\n")
        returnval = p.returncode
        tempscpfh.close()
        tempconffh.close()

        if returnval != 0:
            raise Exception(HCOMPV_BIN + " failed with code: " + unicode(returnval))
        
        ##create "macros" file
        protofh = codecs.open(os.path.join(
                output_dir, parse_path(self.protofilelocation)[1]), encoding="utf-8")
        vfloorsfh = codecs.open(os.path.join(output_dir, VFLOORS_FN), encoding="utf-8")
        macrosfh = codecs.open(os.path.join(output_dir, MACROS_FN), "w", encoding="utf-8")
        
        #copy first part from proto...
        for line in protofh:
            if line.strip()[:2].upper() == "~H":
                break
            else:
                macrosfh.write(line)

        #Copy last part from vFloors
        for line in vfloorsfh:
            macrosfh.write(line)
        macrosfh.close()
        vfloorsfh.close()
        
        ## Now create MMF file...
        protocopy = []
        for line in protofh:
            protocopy.append(line)
        protofh.close()
        
        mmffh = codecs.open(os.path.join(output_dir, HMMDEFS_FN), 'w', encoding="utf-8")
	
        for phone in self.phonelist:
            mmffh.write("~h \"%s\"\n" % (phone))
            for line in protocopy:
                mmffh.write(line)
        mmffh.close()

        #done!

        return returnval        
    

    def doEmbeddedRest(self, mlflocation, statslocation=None):
        """HERest...
        """

        #write featconf
        tempconffh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpFeatConf(tempconffh)

        #write SCP...
        tempscpfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpFeatList(tempscpfh)

        #write phonelist...
        tempphonesfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpPhoneList(tempphonesfh)
        
        #make dirs
        prev_dir = os.path.join(self.targetlocation,
                                  HMM_DIR + unicode(self.iteration))
        output_dir = os.path.join(self.targetlocation,
                                  HMM_DIR + unicode(self.iteration + 1))
        os.makedirs(os.path.join(output_dir))

        #execute HERest...
        if statslocation is None:
            p = subprocess.Popen(" ".join([HEREST_BIN,
                                           "-A",
                                           "-D",
                                           "-V",
                                           "-T",
                                           "1",
                                           "-C",
                                           tempconffh.name,
                                           "-I",
                                           mlflocation,
                                           "-t",
                                           HEREST_PRUNING_PARM1,
                                           HEREST_PRUNING_PARM2,
                                           HEREST_PRUNING_PARM3,
                                           "-S",
                                           tempscpfh.name,
                                           "-H",
                                           os.path.join(prev_dir, MACROS_FN),
                                           "-H",
                                           os.path.join(prev_dir, HMMDEFS_FN),
                                           "-M",
                                           output_dir,
                                           tempphonesfh.name]),
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE,
                                 close_fds = True,
                                 shell = True)
        else:
            p = subprocess.Popen(" ".join([HEREST_BIN,
                                           "-A",
                                           "-D",
                                           "-V",
                                           "-T",
                                           "1",
                                           "-C",
                                           tempconffh.name,
                                           "-I",
                                           mlflocation,
                                           "-t",
                                           HEREST_PRUNING_PARM1,
                                           HEREST_PRUNING_PARM2,
                                           HEREST_PRUNING_PARM3,
                                           "-s",
                                           statslocation,
                                           "-S",
                                           tempscpfh.name,
                                           "-H",
                                           os.path.join(prev_dir, MACROS_FN),
                                           "-H",
                                           os.path.join(prev_dir, HMMDEFS_FN),
                                           "-M",
                                           output_dir,
                                           tempphonesfh.name]),
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE,
                                 close_fds = True,
                                 shell = True)
        so, se = p.communicate()
        log.info("doEmbeddedRest:\n" +
                 "================================================================================\n" +
                 unicode(so, encoding="utf-8") + 
                 "================================================================================\n")
        if bool(se):
            log.warning("doEmbeddedRest:\n" +
                        "================================================================================\n" +
                        unicode(se, encoding="utf-8") +
                        "================================================================================\n")
        returnval = p.returncode
        tempscpfh.close()
        tempconffh.close()
        tempphonesfh.close()

        if returnval != 0:
            raise Exception(HEREST_BIN + " failed with code: " + unicode(returnval))
        
        #done!
        self.iteration += 1

        avglogprob_perframe = float(re.findall(b"Reestimation complete.*", so)[0].split()[-1])
        
        return avglogprob_perframe
        
    
    def addStandardSilTransitions(self):
        """ Just an extra function for the lazy...
        """
        log.debug(unicode(self) + " adding extra 'silence' transitions.")

        lastrealstate = self.numstates - 1
        firstrealstate = 2
        
        commands = []
        for i in range(2, lastrealstate - 1):     #add transitions from all states (excluding second last) to last state...
            commands.append("AT %s %s 0.2 {%s.transP}" % (i, lastrealstate, self.silphone))
        if firstrealstate != lastrealstate:
            commands.append("AT %s %s 0.2 {%s.transP}" % (lastrealstate, firstrealstate, self.silphone))

#5state case....
#         commands = ["AT 2 4 0.2 {%s.transP}" % (self.silphone),
#                     "AT 4 2 0.2 {%s.transP}" % (self.silphone)]

        log.debug(unicode(self) + "HHEd commands:\n" + unicode(commands))
        
        if commands:               #1-state hmms will result in nothing to be done...
            self.doHHEd(commands)


    def cloneTriphones(self, triphonelistfile):
        """ clones triphones from monophone models and ties transition matrices...
        """
        log.debug(unicode(self) + " cloning triphones from monophones (triphonelistfile='%s')." % (triphonelistfile))

        commands = []
        commands.append("CL %s" % (triphonelistfile))
        for phone in self.phonelist:
            if phone != self.silphone:
                commands.append("TI T_%s {(*-%s+*,%s+*,*-%s).transP}\n" % (phone, phone, phone, phone))

        self.doHHEd(commands)

        #update phonelist (models now represent triphones...)
        with codecs.open(triphonelistfile, encoding="utf-8") as infh:
            self.phonelist = sorted([line.strip() for line in infh.readlines()])


    def tieStates(self, hereststatslocation, triphonelistfile, questhedlocation=""):
        """ Use decision tree to cluster states...
        """
        log.debug(unicode(self) + " tying triphone states (questhedlocation='%s')." % (questhedlocation))

        firstrealstate = 2
        lastrealstate = self.numstates - 1

        commands = []

        if bool(questhedlocation):
            with codecs.open(questhedlocation, encoding="utf-8") as infh:
                commands = infh.readlines()
        else:
            monophonelist = sorted(set([triphone_2_monophone(phone) for phone in self.phonelist]))
            commands.append("RO " + RO_THRESHOLD + " " + hereststatslocation + "\n")
            commands.append("TR 0\n")
            for phone in monophonelist:
                rcqname = "\"R_" + phone + "\""
                lcqname = "\"L_" + phone + "\""
                commands.append("%s%-10s%s%s%s" % ("QS ", rcqname, "{ *+", phone, " }\n"))
                commands.append("%s%-10s%s%s%s" % ("QS ", lcqname, "{ ", phone, "-* }\n"))
            commands.append("TR 2\n")

            for i in range(firstrealstate, self.numstates):    #firstrealstate to lastrealstate:
                for phone in monophonelist:
                    commands.append("TB " + TB_THRESHOLD + " \"ST_" + phone + "_" + unicode(i) + "_\" {(" +
                                    phone + ",*-" + phone + "+*," + phone + "+*,*-" + phone + ").state[" + unicode(i) + "]}\n")
            commands.append("TR 1\n")
            commands.append("AU \"%s\"\n" % (triphonelistfile))

            #DEMITASSE: omitting this will only make hmmdefs larger (we're doing falignment..)
            #commands.append("CO \"%s\"\n" % (tiedlistfile))
            
        self.doHHEd(commands)

        log.debug(unicode(self) + "HHEd commands:\n" + unicode(commands))

        #update phonelist (models now represent tiedtriphones...)
        #with codecs.open(tiedlistfile, encoding="utf-8") as infh:
        #    self.phonelist = [line.strip() for line in infh.readlines()]


    def doIncrementMixtures(self):
        """Increments the number of Gaussian mixtures per state by 1...
        """
        log.debug(unicode(self) + " incrementing mixtures.")

        firstrealstate = 2
        lastrealstate = self.numstates - 1

        commands = []

        if firstrealstate != lastrealstate:
            commands.append("MU +1 {*.state[%s-%s].mix}\n" % (firstrealstate, lastrealstate))
        else:
            commands.append("MU +1 {*.state[%s].mix}\n" % (firstrealstate))

        log.debug(unicode(self) + "HHEd commands:\n" + unicode(commands))

        self.doHHEd(commands)


    def doHHEd(self, commands):
        """ HHEd...
        """

        #write commands (hed file)
        tempcmdfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        tempcmdfh.write("\n".join([cmd.strip() for cmd in commands]))
        tempcmdfh.flush()

        #write phonelist...
        tempphonesfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpPhoneList(tempphonesfh)
        
        #make dirs
        prev_dir = os.path.join(self.targetlocation,
                                  HMM_DIR + unicode(self.iteration))
        output_dir = os.path.join(self.targetlocation,
                                  HMM_DIR + unicode(self.iteration + 1))
        os.makedirs(os.path.join(output_dir))

        #execute HHEd...
        p = subprocess.Popen(" ".join([HHED_BIN,
                                       "-A",
                                       "-D",
                                       "-V",
                                       "-T",
                                       "1",
                                       "-H",
                                       os.path.join(prev_dir, MACROS_FN),
                                       "-H",
                                       os.path.join(prev_dir, HMMDEFS_FN),
                                       "-M",
                                       output_dir,
                                       tempcmdfh.name,
                                       tempphonesfh.name]),
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             close_fds = True,
                             shell = True)
        so, se = p.communicate()
        log.info("doHHEd:\n" +
                 "================================================================================\n" +
                 unicode(so, encoding="utf-8") + 
                 "================================================================================\n")
        if bool(se):
            log.warning("doHHEd:\n" +
                        "================================================================================\n" +
                        unicode(se, encoding="utf-8") +
                        "================================================================================\n")
        returnval = p.returncode
        tempcmdfh.close()
        tempphonesfh.close()

        if returnval != 0:
            raise Exception(HHED_BIN + " failed with code: " + unicode(returnval))
        
        #done!
        self.iteration += 1

        return returnval


    def reAlignment(self, mlflocation, dictlocation, outmlflocation):
        """ Do realignment given dictionary with multiple entries...
        """
        
        #write featconf
        #tempconffh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        #self.dumpFeatConf(tempconffh)

        #write SCP...
        tempscpfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpFeatList(tempscpfh)

        #write phonelist...
        tempphonesfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpPhoneList(tempphonesfh)

        #make dirs
        latestmodels_dir = os.path.join(self.targetlocation,
                                        HMM_DIR + unicode(self.iteration))

        #execute HVite...
        p = subprocess.Popen(" ".join([HVITE_BIN,
                                       "-A",
                                       "-D",
                                       "-V",
                                       "-T",
                                       "1",
                                       "-a",
                                       "-y lab",
                                       "-o",
                                       "SWT",
#                                       "-b",
#                                       silword,
                                       "-m",
                                       "-l",
                                       '"*"',
                                       "-I",
                                       mlflocation,
                                       "-i",
                                       outmlflocation,
                                       "-S",
                                       tempscpfh.name,
                                       "-H",
                                       os.path.join(latestmodels_dir, MACROS_FN),
                                       "-H",
                                       os.path.join(latestmodels_dir, HMMDEFS_FN),
                                       dictlocation,
                                       tempphonesfh.name]),
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             close_fds = True,
                             shell = True)
        so, se = p.communicate()
        log.info("reAlignment:\n" +
                 "================================================================================\n" +
                 unicode(so, encoding="utf-8") + 
                 "================================================================================\n")
        if bool(se):
            log.warning("reAlignment:\n" +
                        "================================================================================\n" +
                        unicode(se, encoding="utf-8") +
                        "================================================================================\n")
        returnval = p.returncode
        tempscpfh.close()
        #tempconffh.close()
        tempphonesfh.close()

        if returnval != 0:
            raise Exception(HVITE_BIN + " failed with code: " + unicode(returnval))

        return returnval


    def forcedAlignment(self, mlflocation, dictlocation, outputlocation):
        """ Apply forced alignment towards labeling...
        """
        
        #write featconf
        #tempconffh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        #self.dumpFeatConf(tempconffh)

        #write SCP...
        tempscpfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpFeatList(tempscpfh)

        #write phonelist...
        tempphonesfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpPhoneList(tempphonesfh)

        #make dirs
        latestmodels_dir = os.path.join(self.targetlocation,
                                        HMM_DIR + unicode(self.iteration))

        #execute HVite...
        p = subprocess.Popen(" ".join([HVITE_BIN,
                                       "-A",
                                       "-D",
                                       "-V",
                                       "-T",
                                       "1",
                                       "-a",
                                       "-o",
                                       "N",
                                       "-f",
                                       "-m",
                                       "-l",
                                       outputlocation,
                                       "-I",
                                       mlflocation,
                                       "-S",
                                       tempscpfh.name,
                                       "-H",
                                       os.path.join(latestmodels_dir, HMMDEFS_FN),
                                       dictlocation,
                                       tempphonesfh.name]),
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             close_fds = True,
                             shell = True)
        so, se = p.communicate()
        log.info("forcedAlignment:\n" +
                 "================================================================================\n" +
                 unicode(so, encoding="utf-8") + 
                 "================================================================================\n")
        if bool(se):
            log.warning("forcedAlignment:\n" +
                        "================================================================================\n" +
                        unicode(se, encoding="utf-8") +
                        "================================================================================\n")
        returnval = p.returncode
        tempscpfh.close()
        #tempconffh.close()
        tempphonesfh.close()

        if returnval != 0:
            raise Exception(HVITE_BIN + " failed with code: " + unicode(returnval))

        return returnval



class ASRHMMSet(object):
    """ Manages ASR oriented HMM models...
        
        Duplicating code here now, later: analyse to improve design
        and minimise duplication...
    """

    def __init__(self,
                 targetlocation,
                 phonelist,
                 silphone,
                 spphone,
                 protofilelocation,
                 featsconflocation,
                 featslocation):
        """ Initialise...
        """

        if not os.path.isdir(targetlocation):
            raise Exception("Target location does not exist...")
        if not os.path.isfile(protofilelocation):
            raise Exception("Invalid protofilelocation '%s'" % protofilelocation)

        log.debug(unicode(self) + " initialising with protofile at '%s'." % (protofilelocation))
        self.targetlocation = targetlocation
        self.silphone = silphone
        self.spphone = spphone
        self.phonelist0 = sorted(set(phonelist + [silphone]))
        self.phonelist1 = sorted(set(phonelist + [silphone, spphone]))
        self.featslocation = featslocation
        self.featfilelist = type_files(os.listdir(self.featslocation), MFCC_EXT)
        self.protofilelocation = protofilelocation
        self.numstates = self._getNumStatesFromProtofile()
        self.iteration = 0
        self.hvite_hcompv_parms = self._loadFeatConf(featsconflocation)


    def _getNumStatesFromProtofile(self):
        """Get the number of states specified in the protofile...
           Determines mix-splitting and triphone tying commands...
        """
        
        with codecs.open(self.protofilelocation, encoding="utf-8") as infh:
            for line in infh:
                linelist = line.lower().split()
                try:
                    if linelist[0] == "<numstates>":
                        return int(linelist[1])
                except IndexError:
                    pass    



    def _loadFeatConf(self, location):
        """ Load configuration needed for feature interpretation...
        """
        log.debug(unicode(self) + " loading config file at '%s'." % (location))

        with codecs.open(location, encoding="utf-8") as fh:
            featcfp = ConfigParser()
            featcfp.readfp(fh)

        return list(featcfp.items("HCOMPV_HVITE")) + list(featcfp.items("GLOBAL"))


    def getModelSet(self):
        """Return the list of model names...
        """
        return self.phonelist1[:]


    def dumpFeatConf(self, f):
        """ Dump configuration to file...
        """
        try:
            for k, v in self.hvite_hcompv_parms:
                f.write(k.upper() + " = " + v + "\n")
            f.flush()
        except AttributeError:
            with codecs.open(f, "w", encoding="utf-8") as outfh:
                for k, v in self.hvite_hcompv_parms:
                    outfh.write(k.upper() + " = " + v + "\n")


    def dumpFeatList(self, f):
        """ Dump featlist (SCP) to file...
        """
        try:
            for filename in self.featfilelist:
                f.write(os.path.join(self.featslocation, filename) + "\n")
            f.flush()
        except:
            with codecs.open(f, "w", encoding="utf-8") as outfh:
                for filename in self.featfilelist:
                    outfh.write(os.path.join(self.featslocation, filename) + "\n")


    def dumpPhoneList(self, f, withsp=False):
        """ Dump phonelist (list of models) to file...
        """
        if withsp:
            phonelist = self.phonelist1
        else:
            phonelist = self.phonelist0

        try:
            for phone in phonelist:
                f.write(phone + "\n")
            f.flush()
        except:
            with codecs.open(f, "w", encoding="utf-8") as outfh:
                for phone in phonelist:
                    outfh.write(phone + "\n")


    def mappedBootstrapAll(self, bootmlf_location, bootfeats_location, transcriptionset):
        """ calls doBootstrapAll for mapped bootstrapping...
        """
        
        self.doBootstrapAll(bootmlf_location, bootfeats_location, transcriptionset)


    def doBootstrapAll(self, bootmlf_location, bootfeats_location, transcriptionset=None):
        """ Initialise HMMs using 'bootstrap' method...
            If transcriptionset is not None, then do mapped bootstrap...
        """
        assert self.iteration == 0, "Can only do this as first training iteration..."

        bootfeatlist = type_files(os.listdir(bootfeats_location), MFCC_EXT)
        bootfeatfilelist = [os.path.join(bootfeats_location, featfname) + "\n" for featfname in bootfeatlist]

        #write SCP...
        tempscpfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        tempscpfh.writelines(bootfeatfilelist)
        tempscpfh.flush()

        #make dir...
        hinit_output_dir = os.path.join(self.targetlocation,
                                  HMM_DIR + unicode(self.iteration))
        hrest_output_dir = os.path.join(self.targetlocation,
                                  HMM_DIR + unicode(self.iteration + 1))
        os.makedirs(os.path.join(hinit_output_dir))
        os.makedirs(os.path.join(hrest_output_dir))
        

        for phone in self.phonelist0:
            #hinit
            if transcriptionset is not None:
                tempmlf = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
                transcriptionset.unmapMLF(bootmlf_location, tempmlf.name, phone)
                tempmlf.flush()
                mlf_location = tempmlf.name
            else:
                mlf_location = bootmlf_location
                
            p = subprocess.Popen(" ".join([HINIT_BIN,
                                           "-A",
                                           "-D",
                                           "-V",
                                           "-T",
                                           "1",
                                           "-l",
                                           '"'+phone+'"',
                                           "-o",
                                           '"'+phone+'"',
                                           "-I",
                                           mlf_location,
                                           "-M",
                                           hinit_output_dir,
                                           "-S",
                                           tempscpfh.name,
                                           self.protofilelocation]),
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE,
                                 close_fds = True,
                                 shell = True)
            so, se = p.communicate()
            log.info("doBootstrapAll:\n" +
                     "================================================================================\n" +
                     unicode(so, encoding="utf-8") + 
                     "================================================================================\n")
            if bool(se):
                log.warning("doBootstrapAll:\n" +
                            "================================================================================\n" +
                            unicode(se, encoding="utf-8") +
                            "================================================================================\n")
            returnval = p.returncode
            if returnval != 0:
                raise Exception(HINIT_BIN + " failed with code: " + unicode(returnval))
            #hrest
            p = subprocess.Popen(" ".join([HREST_BIN,
                                           "-A",
                                           "-D",
                                           "-V",
                                           "-T",
                                           "1",
                                           "-l",
                                           '"'+phone+'"',
                                           "-I",
                                           mlf_location,
                                           "-M",
                                           hrest_output_dir,
                                           "-S",
                                           tempscpfh.name,
                                           os.path.join(hinit_output_dir, phone)]),
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE,
                                 close_fds = True,
                                 shell = True)
            so, se = p.communicate()
            log.info("doBootstrapAll:\n" +
                     "================================================================================\n" +
                     unicode(so, encoding="utf-8") + 
                     "================================================================================\n")
            if bool(se):
                log.warning("doBootstrapAll:\n" +
                            "================================================================================\n" +
                            unicode(se, encoding="utf-8") +
                            "================================================================================\n")
            returnval = p.returncode
            if returnval != 0:
                raise Exception(HREST_BIN + " failed with code: " + unicode(returnval))

            if transcriptionset is not None:
                tempmlf.close()
            
        tempscpfh.close()

        ##create "macros" file
        macropart = []
        with codecs.open(os.path.join(hrest_output_dir, self.phonelist0[0]), encoding="utf-8") as infh:
            for line in infh:
                if line.strip()[:2].upper() == "~H":
                    break
                else:
                    macropart.append(line)

        with codecs.open(os.path.join(hrest_output_dir, MACROS_FN), "w", encoding="utf-8") as outfh:
            outfh.writelines(macropart)

        ##Concatenate single HMM files into MMF...
        with codecs.open(os.path.join(hrest_output_dir, HMMDEFS_FN), "w", encoding="utf-8") as outfh:
            outfh.writelines(macropart)
            
            for phone in self.phonelist0:
                inhmm = False
                with codecs.open(os.path.join(hrest_output_dir, phone), encoding="utf-8") as infh:
                    for line in infh:
                        if line.strip().upper().startswith("~H"):
                            outfh.write(line)
                            inhmm = True
                            continue
                        if inhmm:
                            outfh.write(line)

        #done!
        self.iteration += 1


    def doFlatStart(self):
        """ Initialise HMMs using 'flatstart' method...
        """        
        assert self.iteration == 0, "Can only do this as first training iteration..."

        #write featconf..
        tempconffh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpFeatConf(tempconffh)

        #write SCP...
        tempscpfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpFeatList(tempscpfh)
        
        #make dir...
        output_dir = os.path.join(self.targetlocation,
                                  HMM_DIR + unicode(self.iteration))
        os.makedirs(os.path.join(output_dir))

        #execute HCompV...
        p = subprocess.Popen(" ".join([HCOMPV_BIN,
                                       "-A",
                                       "-D",
                                       "-V",
                                       "-T",
                                       "1",
                                       "-C",
                                       tempconffh.name,
                                       "-f",
                                       VFLOOR_VAL,
                                       "-m",
                                       "-S",
                                       tempscpfh.name,
                                       "-M",
                                       output_dir,
                                       self.protofilelocation]),
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             close_fds = True,
                             shell = True)
        so, se = p.communicate()
        log.info("doFlatStart:\n" +
                 "================================================================================\n" +
                 unicode(so, encoding="utf-8") + 
                 "================================================================================\n")
        if bool(se):
            log.warning("doFlatStart:\n" +
                        "================================================================================\n" +
                        unicode(se, encoding="utf-8") +
                        "================================================================================\n")
        returnval = p.returncode
        tempscpfh.close()
        tempconffh.close()

        if returnval != 0:
            raise Exception(HCOMPV_BIN + " failed with code: " + unicode(returnval))
        
        ##create "macros" file
        protofh = codecs.open(os.path.join(
                output_dir, parse_path(self.protofilelocation)[1]), encoding="utf-8")
        vfloorsfh = codecs.open(os.path.join(output_dir, VFLOORS_FN), encoding="utf-8")
        macrosfh = codecs.open(os.path.join(output_dir, MACROS_FN), "w", encoding="utf-8")
        
        #copy first part from proto...
        for line in protofh:
            if line.strip()[:2].upper() == "~H":
                break
            else:
                macrosfh.write(line)

        #Copy last part from vFloors
        for line in vfloorsfh:
            macrosfh.write(line)
        macrosfh.close()
        vfloorsfh.close()
        
        ## Now create MMF file...
        protocopy = []
        for line in protofh:
            protocopy.append(line)
        protofh.close()
        
        mmffh = codecs.open(os.path.join(output_dir, HMMDEFS_FN), 'w', encoding="utf-8")
	
        for phone in self.phonelist0:
            mmffh.write("~h \"%s\"\n" % (phone))
            for line in protocopy:
                mmffh.write(line)
        mmffh.close()

        #done!

        return returnval        
    

    def doEmbeddedRest(self, mlflocation, statslocation=None, withsp=False):
        """HERest...
        """

        #write featconf
        tempconffh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpFeatConf(tempconffh)

        #write SCP...
        tempscpfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpFeatList(tempscpfh)

        #write phonelist...
        tempphonesfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpPhoneList(tempphonesfh, withsp)
        
        #make dirs
        prev_dir = os.path.join(self.targetlocation,
                                  HMM_DIR + unicode(self.iteration))
        output_dir = os.path.join(self.targetlocation,
                                  HMM_DIR + unicode(self.iteration + 1))
        os.makedirs(os.path.join(output_dir))

        #execute HERest...
        if statslocation is None:
            p = subprocess.Popen(" ".join([HEREST_BIN,
                                           "-A",
                                           "-D",
                                           "-V",
                                           "-T",
                                           "1",
                                           "-C",
                                           tempconffh.name,
                                           "-I",
                                           mlflocation,
                                           "-t",
                                           HEREST_PRUNING_PARM1,
                                           HEREST_PRUNING_PARM2,
                                           HEREST_PRUNING_PARM3,
                                           "-S",
                                           tempscpfh.name,
                                           "-H",
                                           os.path.join(prev_dir, MACROS_FN),
                                           "-H",
                                           os.path.join(prev_dir, HMMDEFS_FN),
                                           "-M",
                                           output_dir,
                                           tempphonesfh.name]),
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE,
                                 close_fds = True,
                                 shell = True)
        else:
            p = subprocess.Popen(" ".join([HEREST_BIN,
                                           "-A",
                                           "-D",
                                           "-V",
                                           "-T",
                                           "1",
                                           "-C",
                                           tempconffh.name,
                                           "-I",
                                           mlflocation,
                                           "-t",
                                           HEREST_PRUNING_PARM1,
                                           HEREST_PRUNING_PARM2,
                                           HEREST_PRUNING_PARM3,
                                           "-s",
                                           statslocation,
                                           "-S",
                                           tempscpfh.name,
                                           "-H",
                                           os.path.join(prev_dir, MACROS_FN),
                                           "-H",
                                           os.path.join(prev_dir, HMMDEFS_FN),
                                           "-M",
                                           output_dir,
                                           tempphonesfh.name]),
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE,
                                 close_fds = True,
                                 shell = True)
        so, se = p.communicate()
        log.info("doEmbeddedRest:\n" +
                 "================================================================================\n" +
                 unicode(so, encoding="utf-8") + 
                 "================================================================================\n")
        if bool(se):
            log.warning("doEmbeddedRest:\n" +
                        "================================================================================\n" +
                        unicode(se, encoding="utf-8") +
                        "================================================================================\n")
        returnval = p.returncode
        tempscpfh.close()
        tempconffh.close()
        tempphonesfh.close()

        if returnval != 0:
            raise Exception(HEREST_BIN + " failed with code: " + unicode(returnval))
        
        #done!
        self.iteration += 1

        avglogprob_perframe = float(re.findall(b"Reestimation complete.*", so)[0].split()[-1])
        
        return avglogprob_perframe
        
    
    def fixSilModels(self):
        """ creates ShortSil model and adds extra transitions to SIL
            model...
        """
        log.debug(unicode(self) + " adding extra 'silence' transitions.")

        lastrealstate = self.numstates - 1
        firstrealstate = 2

        middelstate = (firstrealstate + lastrealstate) // 2

        #create ShortSil ("tee model"):
        input_dir = os.path.join(self.targetlocation,
                                  HMM_DIR + unicode(self.iteration))
        output_dir = os.path.join(self.targetlocation,
                                  HMM_DIR + unicode(self.iteration + 1))
        os.makedirs(output_dir)
        shutil.copy(os.path.join(input_dir, MACROS_FN), output_dir)
        
        with codecs.open(os.path.join(input_dir, HMMDEFS_FN), "r", encoding="utf-8") as infh:
            hmmdefstext = infh.read()
        
        pat = re.compile('~h \"pau\"(.*?)<ENDHMM>', flags=re.DOTALL)
        mo = pat.search(hmmdefstext)
        silmodeltext = mo.groups()[0]

        pat = re.compile('<STATE> %s(.*?)<STATE>' % (middelstate), flags=re.DOTALL)
        mo = pat.search(silmodeltext)
        silstatetext = mo.groups()[0]

        with codecs.open(os.path.join(output_dir, HMMDEFS_FN), "w", encoding="utf-8") as outfh:
            outfh.write(hmmdefstext)
            outfh.write("~h \"%s\"\n<BEGINHMM>\n<NUMSTATES> 3\n<STATE> 2%s<TRANSP> 3\n0.000000e+00 1.000000e+00 0.000000e+00\n0.000000e+00 6.000000e-01 4.000000e-01\n0.000000e+00 0.000000e+00 0.000000e+00\n<ENDHMM>\n" % (self.spphone, silstatetext))
        

        self.iteration += 1

        #add transitions to SIL model and tie central state to ShortSil state:
        commands = []
        for i in range(firstrealstate, lastrealstate - 1): #add transitions from all states (excluding second last) to last state...
            commands.append("AT %s %s 0.2 {%s.transP}" % (i, lastrealstate, self.silphone))
        if firstrealstate != lastrealstate:
            commands.append("AT %s %s 0.2 {%s.transP}" % (lastrealstate, firstrealstate, self.silphone))

#5state case....
#         commands = ["AT 2 4 0.2 {%s.transP}" % (self.silphone),
#                     "AT 4 2 0.2 {%s.transP}" % (self.silphone)]


        commands.append("AT 1 3 0.3 {%s.transP}" % (self.spphone))
        commands.append("TI %sst {%s.state[%s],%s.state[2]}" % (self.silphone, self.silphone, middelstate, self.spphone))

        log.debug(unicode(self) + "HHEd commands:\n" + unicode(commands))
        
        if commands:               #1-state hmms will result in nothing to be done...
            self.doHHEd(commands, withsp=True)


    def cloneTriphones(self, triphonelistfile):
        """ clones triphones from monophone models and ties transition matrices...
        """
        log.debug(unicode(self) + " cloning triphones from monophones (triphonelistfile='%s')." % (triphonelistfile))

        commands = []
        commands.append("CL %s" % (triphonelistfile))
        for phone in self.phonelist0:
            if phone != self.silphone:
                commands.append("TI T_%s {(*-%s+*,%s+*,*-%s).transP}\n" % (phone, phone, phone, phone))

        self.doHHEd(commands)

        #update phonelist (models now represent triphones...)
        with codecs.open(triphonelistfile, encoding="utf-8") as infh:
            self.phonelist0 = sorted([line.strip() for line in infh.readlines()])
            self.phonelist1 = self.phonelist0 + [self.spphone]


    def tieStates(self, hereststatslocation, triphonelistfile, tiedlistfile, questhedlocation=""):
        """ Use decision tree to cluster states...
        """
        log.debug(unicode(self) + " tying triphone states (questhedlocation='%s')." % (questhedlocation))

        firstrealstate = 2
        lastrealstate = self.numstates - 1

        commands = []

        if bool(questhedlocation):
            with codecs.open(questhedlocation, encoding="utf-8") as infh:
                commands = infh.readlines()
        else:
            monophonelist = sorted(set([triphone_2_monophone(phone) for phone in self.phonelist0]))
            commands.append("RO " + RO_THRESHOLD + " " + hereststatslocation + "\n")
            commands.append("TR 0\n")
            for phone in monophonelist:
                rcqname = "\"R_" + phone + "\""
                lcqname = "\"L_" + phone + "\""
                commands.append("%s%-10s%s%s%s" % ("QS ", rcqname, "{ *+", phone, " }\n"))
                commands.append("%s%-10s%s%s%s" % ("QS ", lcqname, "{ ", phone, "-* }\n"))
            commands.append("TR 2\n")

            for i in range(firstrealstate, self.numstates):    #firstrealstate to lastrealstate:
                for phone in monophonelist:
                    commands.append("TB " + TB_THRESHOLD + " \"ST_" + phone + "_" + unicode(i) + "_\" {(" +
                                    phone + ",*-" + phone + "+*," + phone + "+*,*-" + phone + ").state[" + unicode(i) + "]}\n")
            commands.append("TR 1\n")
            commands.append("AU \"%s\"\n" % (triphonelistfile))
            #commands.append("CO \"%s\"\n" % (tiedlistfile))
            
        self.doHHEd(commands)

        log.debug(unicode(self) + "HHEd commands:\n" + unicode(commands))

        # #update phonelist (models now represent tied triphones...)
        # with codecs.open(tiedlistfile, encoding="utf-8") as infh:
        #     self.phonelist = sorted([line.strip() for line in infh.readlines()])


    def doIncrementMixtures(self):
        """Increments the number of Gaussian mixtures per state by 1...
        """
        log.debug(unicode(self) + " incrementing mixtures.")

        firstrealstate = 2
        lastrealstate = self.numstates - 1

        commands = []

        if firstrealstate != lastrealstate:
            commands.append("MU +1 {*.state[%s-%s].mix}\n" % (firstrealstate, lastrealstate))
        else:
            commands.append("MU +1 {*.state[%s].mix}\n" % (firstrealstate))

        log.debug(unicode(self) + "HHEd commands:\n" + unicode(commands))

        self.doHHEd(commands)


    def doHHEd(self, commands, withsp=False):
        """ HHEd...
        """

        #write commands (hed file)
        tempcmdfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        tempcmdfh.write("\n".join([cmd.strip() for cmd in commands]))
        tempcmdfh.flush()

        #write phonelist...
        tempphonesfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpPhoneList(tempphonesfh, withsp)
        
        #make dirs
        prev_dir = os.path.join(self.targetlocation,
                                  HMM_DIR + unicode(self.iteration))
        output_dir = os.path.join(self.targetlocation,
                                  HMM_DIR + unicode(self.iteration + 1))
        os.makedirs(os.path.join(output_dir))

        #execute HHEd...
        p = subprocess.Popen(" ".join([HHED_BIN,
                                       "-A",
                                       "-D",
                                       "-V",
                                       "-T",
                                       "1",
                                       "-H",
                                       os.path.join(prev_dir, MACROS_FN),
                                       "-H",
                                       os.path.join(prev_dir, HMMDEFS_FN),
                                       "-M",
                                       output_dir,
                                       tempcmdfh.name,
                                       tempphonesfh.name]),
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             close_fds = True,
                             shell = True)
        so, se = p.communicate()
        log.info("doHHEd:\n" +
                 "================================================================================\n" +
                 unicode(so, encoding="utf-8") + 
                 "================================================================================\n")
        if bool(se):
            log.warning("doHHEd:\n" +
                        "================================================================================\n" +
                        unicode(se, encoding="utf-8") +
                        "================================================================================\n")
        returnval = p.returncode
        tempcmdfh.close()
        tempphonesfh.close()

        if returnval != 0:
            raise Exception(HHED_BIN + " failed with code: " + unicode(returnval))
        
        #done!
        self.iteration += 1

        return returnval


    def forcedAlignment(self, mlflocation, dictlocation, outputlocation, withsp=False):
        """ Apply forced alignment towards labeling...
        """
        
        #write featconf
        #tempconffh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        #self.dumpFeatConf(tempconffh)

        #write SCP...
        tempscpfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpFeatList(tempscpfh)

        #write phonelist...
        tempphonesfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpPhoneList(tempphonesfh, withsp)

        #make dirs
        latestmodels_dir = os.path.join(self.targetlocation,
                                        HMM_DIR + unicode(self.iteration))

        #execute HVite...
        p = subprocess.Popen(" ".join([HVITE_BIN,
                                       "-A",
                                       "-D",
                                       "-V",
                                       "-T",
                                       "1",
                                       "-a",
                                       "-o",
                                       "N",
                                       "-f",
                                       "-m",
                                       "-l",
                                       outputlocation,
                                       "-I",
                                       mlflocation,
                                       "-S",
                                       tempscpfh.name,
                                       "-H",
                                       os.path.join(latestmodels_dir, HMMDEFS_FN),
                                       dictlocation,
                                       tempphonesfh.name]),
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             close_fds = True,
                             shell = True)
        so, se = p.communicate()
        log.info("forcedAlignment:\n" +
                 "================================================================================\n" +
                 unicode(so, encoding="utf-8") + 
                 "================================================================================\n")
        if bool(se):
            log.warning("forcedAlignment:\n" +
                        "================================================================================\n" +
                        unicode(se, encoding="utf-8") +
                        "================================================================================\n")
        returnval = p.returncode
        tempscpfh.close()
        #tempconffh.close()
        tempphonesfh.close()

        if returnval != 0:
            raise Exception(HVITE_BIN + " failed with code: " + unicode(returnval))

        return returnval


    def reAlignment(self, mlflocation, dictlocation, silword, outmlflocation, withsp=False):
        """ Do realignment given dictionary with multiple entries...
        """
        
        #write featconf
        #tempconffh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        #self.dumpFeatConf(tempconffh)

        #write SCP...
        tempscpfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpFeatList(tempscpfh)

        #write phonelist...
        tempphonesfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        self.dumpPhoneList(tempphonesfh, withsp)

        #make dirs
        latestmodels_dir = os.path.join(self.targetlocation,
                                        HMM_DIR + unicode(self.iteration))

        #execute HVite...
        p = subprocess.Popen(" ".join([HVITE_BIN,
                                       "-A",
                                       "-D",
                                       "-V",
                                       "-T",
                                       "1",
                                       "-a",
                                       "-y lab",
                                       "-o",
                                       "SWT",
                                       "-b",
                                       silword,
                                       "-m",
                                       "-l",
                                       '"*"',
                                       "-I",
                                       mlflocation,
                                       "-i",
                                       outmlflocation,
                                       "-S",
                                       tempscpfh.name,
                                       "-H",
                                       os.path.join(latestmodels_dir, MACROS_FN),
                                       "-H",
                                       os.path.join(latestmodels_dir, HMMDEFS_FN),
                                       dictlocation,
                                       tempphonesfh.name]),
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             close_fds = True,
                             shell = True)
        so, se = p.communicate()
        log.info("reAlignment:\n" +
                 "================================================================================\n" +
                 unicode(so, encoding="utf-8") + 
                 "================================================================================\n")
        if bool(se):
            log.warning("reAlignment:\n" +
                        "================================================================================\n" +
                        unicode(se, encoding="utf-8") +
                        "================================================================================\n")
        returnval = p.returncode
        tempscpfh.close()
        #tempconffh.close()
        tempphonesfh.close()

        if returnval != 0:
            raise Exception(HVITE_BIN + " failed with code: " + unicode(returnval))

        return returnval
