#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This script contains the process necessary for training models and
    labeling speech...

    TODO:
	relook at code writing "macros"...

    20110310 - Recent changes to PronunciationDictionary might break
    some assumptions here (especially with regards to when the
    dictionary is sorted (changed that so no implicit sorting is
    done...))
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os
import sys
import codecs
import logging
from time import time, strftime
import shutil
import pprint
from optparse import OptionParser
from ConfigParser import ConfigParser

from HALIGN_Text import *
from HALIGN_Features import *
from HALIGN_Models import *

import speechlabels as sl

#SCRIPT RELATED
NAME = "HAlign"
DEF_CONF = "halign.conf"
DEF_LOGLEVEL = 20          #'INFO'
ALLOWED_LOGLEVELS = [0, 10, 20, 30, 40, 50]
DEF_METHOD = "GenHAlign"
ALLOWED_METHODS = ["GenHAlign", "GenHAlignRealign", "GenTrainASR"]

#instantiate 'root' logger...
log = logging.getLogger(NAME)

log.setLevel(DEF_LOGLEVEL)

#HELPER FUNCS
################################################################################
def fnjoin(bname, ext):
    return ".".join([bname, ext])


class GenHAlign(object):
    """ Defines the generic process to perform HMM training and
        forced alignment...
    """

    #DIRS
    ETC_DIR = "etc"
    MODELS_DIR = "models"
    FEAT_DIR = "feats"
    BOOTFEAT_DIR = "bootfeats"
    OUTPUT_DIR = "labels"
    TEXTGRID_DIR = "textgrids"

    #EXTS
    MLF_EXT = "mlf"
    DICT_EXT = "dict"
    TEXTGRID_EXT = "TextGrid"

    #FILENAMES
    MAINDICT_BN = "main"
    TRIDICT_BN = "tri"
    WORDTRANSCR_BN = "words"
    PHONETRANSCR_BN = "phones"
    BOOTTRANSCR_BN = "boot"
    TRIPHONETRANSCR_BN = "triphones"
    HCOPY_BN = "hcopy"
    HVITE_BN = "hcompv-hvite"

    TRIPHONESET_FN = "triphoneset"
    TIEDTRIPHONESET_FN = "tiedtriphoneset"
    MONOPHONESET_FN = "phoneset"
    HERESTSTATS_FN = "hereststats"


    def __init__(self, configfile_location, overrides={}, setup_only=False):
        """Initialises process (reads from config and sets switches/variables...)...
        """
        
        self.overrides = overrides
        self.configfile_dir = os.path.dirname(configfile_location)
        with codecs.open(configfile_location, encoding="utf-8") as conffh:
            self.config = ConfigParser()
            self.config.readfp(conffh)
        

        #setup log...
        consolehandler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
        consolehandler.setFormatter(formatter)
        log.addHandler(consolehandler)

        #make dirs...
        self.makeDirs()        
        
        #setup log...
        log.removeHandler(consolehandler)
        logfilehandler = logging.FileHandler('%s.log' % (os.path.join(self.working_dir, NAME + "_" + strftime("%Y%m%d%H%M%S"))))
        logfilehandler.setFormatter(formatter)
        log.addHandler(logfilehandler)
        
        #copy configuration file for the record (if possible)...and log configuration...
        log.info("Configuration file used: '%s'" % configfile_location)
        log.info("Overrides defined:\n%s" % pprint.pformat(self.overrides))
        try:
            shutil.copy(configfile_location, self.working_dir)
        except shutil.Error:
            #if copy fails (this is probably because file might already exist here...)
            #fail silently...
            pass
        
        
        #set switches...ugly
        self.orthographic_location = self.getParm("SOURCE", "ORTHOGRAPHIC_TRANSCRIPTIONS")
        if self.orthographic_location:
            self.orthographic_location = self.getParm("SOURCE", "ORTHOGRAPHIC_TRANSCRIPTIONS", path=True)

        self.pronundict_location = self.getParm("SOURCE", "PRONUNCIATION_DICTIONARY")
        if self.pronundict_location:
            self.pronundict_location = self.getParm("SOURCE", "PRONUNCIATION_DICTIONARY", path=True)

        self.phonetic_location = self.getParm("SOURCE", "PHONETIC_TRANSCRIPTIONS")
        if self.phonetic_location:
            self.phonetic_location = self.getParm("SOURCE", "PHONETIC_TRANSCRIPTIONS", path=True)

        self.transmap_location = self.getParm("SOURCE", "PHONETIC_TRANSCRIPTIONS_MAP")
        if self.transmap_location:
            self.transmap_location = self.getParm("SOURCE", "PHONETIC_TRANSCRIPTIONS_MAP", path=True)

        self.bootmodels_location = self.getParm("SOURCE", "BOOT_MODELS")
        if self.bootmodels_location:
            self.bootmodels_location = self.getParm("SOURCE", "BOOT_MODELS", path=True)

        self.boottranscr_location = self.getParm("SOURCE", "BOOT_TRANSCRIPTIONS")
        if self.boottranscr_location:
            self.boottranscr_location = self.getParm("SOURCE", "BOOT_TRANSCRIPTIONS", path=True)

        self.bootmap_location = self.getParm("SOURCE", "BOOT_TRANSCRIPTIONS_MAP")
        if self.bootmap_location:
            self.bootmap_location = self.getParm("SOURCE", "BOOT_TRANSCRIPTIONS_MAP", path=True)

        self.bootaudio_location = self.getParm("SOURCE", "BOOT_AUDIO")
        if self.bootaudio_location:
            self.bootaudio_location = self.getParm("SOURCE", "BOOT_AUDIO", path=True)

        self.cdhmms = self.getParm("SWITCHES", "CDHMMS", boolean=True)
        self.nummixs = self.getParm("SWITCHES", "MIXTURES_PER_STATE")
        self.mappedbootstrap = self.getParm("SWITCHES", "MAPPEDBOOTSTRAP", boolean=True)
        self.textgrid_output = self.getParm("SWITCHES", "TEXTGRID_OUTPUT", boolean=True)
        self.postcleanup = self.getParm("SWITCHES", "POSTCLEANUP", boolean=True)

        if bool(self.orthographic_location) and bool(self.pronundict_location):
            self.have_ortho_and_pronundict = True
        else:
            self.have_ortho_and_pronundict = False
        if bool(self.phonetic_location):
            self.have_phonetic = True
        else:
            self.have_phonetic = False

        if bool(self.bootmodels_location):
            self.have_bootmodels = True
        else:
            self.have_bootmodels = False

        if bool(self.boottranscr_location) and bool(self.bootaudio_location):
            self.have_bootdata = True
        else:
            self.have_bootdata = False

        if bool(self.transmap_location):
            self.have_transmap = True
        else:
            self.have_transmap = False

        if bool(self.bootmap_location):
            self.have_bootmap = True
        else:
            self.have_bootmap = False        

        #break here if the procedure will be manually called...
        if setup_only: return
        
        log.info("Process: 'GenHAlign'")

        log.info("Starting Process.") 
        starttime = time()
        self.organiseTranscriptions()
        self.makeFeats()
        self.initModels()
        self.trainModels()
        self.doAlignment()
        if self.textgrid_output: self.doTextgridOutput()
        if self.postcleanup: self.doCleanup()
        endtime = time()
        log.info("Process Done (in %.0f seconds)." % (endtime - starttime))

        
    def getParm(self, sectionkey, key, boolean=False, path=False):
        """Try to get specific parameter firstly from 'self.overrides' else
           fall back to 'self.config'...
        """
        booldict = {"true" : True,
                    "false" : False,
                    "yes" : True,
                    "no" : False,
                    "y" : True,
                    "n" : False}

        overridekey = ":".join([sectionkey, key])

        if overridekey not in self.overrides:
            if boolean:
                return self.config.getboolean(sectionkey, key)
            elif path:
                s = self.config.get(sectionkey, key)
                if os.path.isabs(s):
                    return s
                else:
                    return os.path.abspath(os.path.join(self.configfile_dir, s))
            else:
                return self.config.get(sectionkey, key)
        else:
            log.info("Override used: %s" % (overridekey))
            if boolean:
                return booldict[self.overrides[overridekey].lower()]
            elif path:
                return os.path.abspath(self.overrides[overridekey])
            else:
                return self.overrides[overridekey]


    def doCleanup(self):
        """Remove 'feats', 'bootfeats' and 'models' trees...
        """
        log.info("Removing 'models' and 'feats' dirs.")

        shutil.rmtree(self.feats_dir)
        try:
            shutil.rmtree(self.bootfeats_dir)
        except OSError:
            pass
        shutil.rmtree(self.models_dir)
        

    def makeDirs(self):
        """Make 'working' directory structure...
        """
        
        self.working_dir = self.getParm("PARMS", "WORKING_DIR", path=True)
        self.etc_dir = os.path.join(self.working_dir, GenHAlign.ETC_DIR)
        self.feats_dir = os.path.join(self.working_dir, GenHAlign.FEAT_DIR)
        self.models_dir = os.path.join(self.working_dir, GenHAlign.MODELS_DIR)
        self.output_dir = os.path.join(self.working_dir, GenHAlign.OUTPUT_DIR)
        self.bootfeats_dir = os.path.join(self.working_dir, GenHAlign.BOOTFEAT_DIR)
        self.textgrid_dir = os.path.join(self.working_dir, GenHAlign.TEXTGRID_DIR)
        try:
            os.makedirs(self.working_dir)
        except OSError:
            print("WARNING: Working dir '%s' already existed..." % self.working_dir)
        os.makedirs(self.etc_dir)
        os.makedirs(self.feats_dir)
        os.makedirs(self.models_dir)
        os.makedirs(self.output_dir)
        os.makedirs(self.bootfeats_dir)
        os.makedirs(self.textgrid_dir)

    
    def doTextgridOutput(self):
        """ Clean up and convert .rec files to .TextGrid files...
        """

        c = sl.Corpus(self.output_dir)
        
        for u in c.utterances:
            del u.tiers['state']
            for i in range(len(u.tiers['segment'])):
                u.tiers['segment'][i][1] = sl.triphone_2_monophone(u.tiers['segment'][i][1])
            for i in range(len(u.tiers['word'])):
                u.tiers['word'][i][1] = u.tiers['word'][i][1].split("_")[0]
            u.saveTextgrid(os.path.join(self.textgrid_dir, ".".join([u.name, GenHAlign.TEXTGRID_EXT])))


    def organiseTranscriptions(self):
        """Prepare transcriptions into MLF and dictionaries...
        """
    
        if self.have_ortho_and_pronundict:
            self.makeFromOrthographic()
        elif self.have_phonetic:
            self.makeFromPhonetic()
        else:
            log.error("Transcriptions not sufficiently defined. Check configuration file.")
            raise Exception("Transcriptions not sufficient...")
        
        if not self.have_bootmodels and self.have_bootdata:
            self.makeBootTranscriptions()


    def makeFromOrthographic(self):
        """Prepare transcriptions from orthography, using a pronunciation dictionary...
        """
        print("WRITING DICTs AND MLFs FROM ORTHOGRAPHIC TRANSCRIPTIONS.....")
        log.info("Making transcriptions and dicts from orthgraphic transcriptions.")

        self.source_transcr_location = self.orthographic_location
        self.source_dict_location = self.pronundict_location
        self.silphone = self.getParm("PARMS", "SILENCE_PHONE")
        self.silword = self.getParm("PARMS", "SILENCE_WORD")
        self.normalise_orthography = self.getParm("SWITCHES", "NORMALISE_ORTHOGRAPHY", boolean=True)
        self.dict_location = os.path.join(self.etc_dir, fnjoin(GenHAlign.MAINDICT_BN, GenHAlign.DICT_EXT))
        self.wordmlf_location = os.path.join(self.etc_dir, fnjoin(GenHAlign.WORDTRANSCR_BN, GenHAlign.MLF_EXT))
        self.phonemlf_location = os.path.join(self.etc_dir, fnjoin(GenHAlign.PHONETRANSCR_BN, GenHAlign.MLF_EXT))
        self.monophoneset_location = os.path.join(self.etc_dir, GenHAlign.MONOPHONESET_FN)


        #load transcriptions
        self.transcr = TranscriptionSet(self.source_transcr_location, type="WORD")
        if self.normalise_orthography:
            self.transcr.normalise()                #removes all punctuation and forces lowercase...
        self.dict = PronunciationDictionary(self.source_dict_location)

        if self.silword != "":
            self.dict[self.silword] = [self.silphone]   #define entry mapping to silence...
            self.dict.sort()

        #check whether dictionary entries cover all words in transcriptions...
        if not self.dict.allWordsInDict(self.transcr):
            log.error("Pronunciation dictionary (%s) does not contain all words." % (self.source_dict_location))
            raise Exception("Some words not found in dictionary....")

        #write dict, MLFs and phoneset...
        self.dict.writeDict(self.dict_location)
        self.transcr.writeWordMLF(self.wordmlf_location, self.silword)
        TranscriptionSet.wordToPhoneMLF(self.wordmlf_location, self.dict_location, self.phonemlf_location)
        self.phonetranscr = TranscriptionSet(self.phonemlf_location, "PHONE")
        
        if self.have_transmap:
            log.info("Loading transcription map.")
            self.phonetranscr.loadMap(self.transmap_location)

        # and phoneset:
        with codecs.open(self.monophoneset_location, "w", encoding="utf-8") as outfh:
            phoneset = [phone + "\n" for phone in self.dict.getPhoneSet()]
            outfh.writelines(phoneset)

        if self.have_phonetic:
            #check that translation from words matches phonetic transcriptions...
            log.info("Cross checking phonetic sequence from orthography with directly supplied phonetic sequence.")
            correctphonetranscr = TranscriptionSet(self.phonetic_location, "PHONE")
            if not correctphonetranscr.allPhonesMatch(self.phonetranscr):
                log.error("Translated MLF (%(self.phonemlf_location)s) does not " + 
                          "correspond with transcriptions (%(self.phonetic_location))s).")
                raise Exception("Phone MLF does not match phonetic transcriptions...")


    def makeFromPhonetic(self):
        """Prepare transcriptions from phonetic sequence only...
        """
        print("WRITING DICTS AND MLFs FROM PHONETIC TRANSCRIPTIONS.....")
        log.info("Making transcriptions and dicts from phonetic sequence.")
        
        self.source_transcr_location = self.getParm("SOURCE", "PHONETIC_TRANSCRIPTIONS", path=True)
        self.silphone = self.getParm("PARMS", "SILENCE_PHONE")
        self.dict_location = os.path.join(self.etc_dir, fnjoin(GenHAlign.MAINDICT_BN, GenHAlign.DICT_EXT))
        self.phonemlf_location = os.path.join(self.etc_dir, fnjoin(GenHAlign.PHONETRANSCR_BN, GenHAlign.MLF_EXT))
        self.monophoneset_location = os.path.join(self.etc_dir, GenHAlign.MONOPHONESET_FN)

        #load transcriptions
        self.transcr = TranscriptionSet(self.source_transcr_location, type="PHONE")
        if self.have_transmap:
            log.info("Loading transcription map.")
            self.transcr.loadMap(self.transmap_location)

        #write dict, MLFs and phoneset...
        self.transcr.writePseudoDict(self.dict_location)
        self.transcr.writePhoneMLF(self.phonemlf_location)
        self.phonetranscr = self.transcr
        # and phoneset:
        with codecs.open(self.monophoneset_location, "w", encoding="utf-8") as outfh:
            phoneset = [phone + "\n" for phone in self.transcr.getPhoneSet()]
            outfh.writelines(phoneset)

        self.dict = PronunciationDictionary(self.dict_location)
        self.dict.sort()

    def makeBootTranscriptions(self):
        """Prepare bootstrap data transcriptions...
        """
        log.info("Making boot transcriptions.")

        self.boottranscr_location = self.getParm("SOURCE", "BOOT_TRANSCRIPTIONS", path=True)
        self.bootmlf_location = os.path.join(self.etc_dir, fnjoin(GenHAlign.BOOTTRANSCR_BN, GenHAlign.MLF_EXT))
        
        self.boottranscr = TranscriptionSet(self.boottranscr_location, type="PHONE")
        if self.have_bootmap:
            log.info("Loading boot-transcription map.")
            self.boottranscr.loadMap(self.bootmap_location)

        self.boottranscr.writePhoneMLF(self.bootmlf_location, write_boundaries=True, map=self.mappedbootstrap) #map if required..


    def makeFeats(self):
        """Perform feature extraction on the necessary audio files...
        """
        print("MAKING FEATS....")
        log.info("Making feats.")

        self.source_audio_location = self.getParm("SOURCE", "AUDIO", path=True)
        self.featconf_location = self.getParm("SOURCE", "FEATS_CONFIG", path=True)
        
        self.audiofeats = AudioFeatures(self.source_audio_location, self.featconf_location)
        
        #check all labels in transcriptionset...
        if not self.transcr.allLabelsInTranscr(self.audiofeats):
            log.error("Transcription set does not cover all audio files.")
            raise Exception("Transcription set does not cover all audio files....")

        #make features...
        self.audiofeats.makeFeats(self.feats_dir)

        if not self.have_bootmodels and self.have_bootdata:
            log.info("Making boot feats.")
            self.bootfeats = AudioFeatures(self.bootaudio_location, self.featconf_location)
            if not self.boottranscr.allLabelsInTranscr(self.bootfeats):
                log.error("Boot transcription set does not cover all boot audio files.")
                raise Exception("Some labels not found in boottranscriptionset....")
            self.bootfeats.makeFeats(self.bootfeats_dir)


    def initModels(self):
        """Initialise HMMs through either 'flatstart' or bootstrapping and defining
           the silence model properly...
        """

        print("INITIALISING MODELS...")

        self.protofile_location = self.getParm("SOURCE", "HMM_PROTOTYPE", path=True)

        self.models = HMMSet(self.models_dir,
                             self.dict.getPhoneSet(),
                             self.silphone,
                             self.protofile_location,
                             self.featconf_location,
                             self.feats_dir)
    
        if self.have_bootmodels:
            print("COPYING BOOTSTRAP MODELS...(NO VARIANCE FLOOR SET...)")
            if self.mappedbootstrap:
                log.info("Copying mapped bootstrap models.")
                self.models.copyBootmodels(self.bootmodels_location, True, self.phonetranscr)
            else:
                log.info("Copying bootstrap models directly.")
                self.models.copyBootmodels(self.bootmodels_location, False)
        elif self.have_bootdata:
            print("BOOTSTRAP...(NO VARIANCE FLOOR SET...)")
            if self.mappedbootstrap:
                log.info("Performing mapped-bootstrapping.")
                self.models.mappedBootstrapAll(self.bootmlf_location, self.bootfeats_dir, self.phonetranscr)
            else:
                log.info("Performing native bootstrapping.")
                #For each phone do an HInit - HRest combo to init phones...
                self.models.doBootstrapAll(self.bootmlf_location, self.bootfeats_dir)
        else:
            #do flatstart...
            print("FLATSTART....")
            log.info("Performing 'flatstart' initialisation.")
            self.models.doFlatStart()
            for i in range(3):
                self.models.doEmbeddedRest(self.phonemlf_location)
    
        #fix silence model
        self.models.addStandardSilTransitions()

    
    def trainModels(self):
        """Performs training procedure...
        """

        print("RE-ESTIMATING....")
        for i in range(5):
            self.models.doEmbeddedRest(self.phonemlf_location)

        if self.cdhmms:
            self.makeTriphones()
            
        try:
            nummixups = int(self.nummixs) - 1
            if nummixups >= 1:
                for i in range(nummixups):
                    self.doIncrementMixtures(i+2)
        except ValueError:
            pass


    def doIncrementMixtures(self, num):
        """Increments the number of Gaussian mixtures per state by 1 and reestimates...
        """

        print("INCREMENTING MIXTURES....")
        log.info("Incrementing number of mixtures to %s." % (num))
        self.models.doIncrementMixtures()
        if self.cdhmms:
            self.models.doEmbeddedRest(self.triphonemlf_location)
        else:
            self.models.doEmbeddedRest(self.phonemlf_location)


    def makeTriphones(self):
        """Perform cloning of triphones from monophones as well as triphone tying...
        """

        print("MAKING TRIPHONES....")
        log.info("Making context dependent HMMs.")

        self.triphonemlf_location = os.path.join(self.etc_dir, fnjoin(GenHAlign.TRIPHONETRANSCR_BN, MLF_EXT))
        self.hereststats_location = os.path.join(self.etc_dir, GenHAlign.HERESTSTATS_FN)
        self.triphoneset_location = os.path.join(self.etc_dir, GenHAlign.TRIPHONESET_FN)
        self.tridict_location = os.path.join(self.etc_dir, fnjoin(GenHAlign.TRIDICT_BN, GenHAlign.DICT_EXT))

        #make triphone transcriptions
        TranscriptionSet.monophoneToTriphoneMLF(self.phonemlf_location, self.triphonemlf_location, self.silphone)
        triphonetranscr = TranscriptionSet(self.triphonemlf_location, "PHONE")

        #make triphone dictionary
        if self.have_ortho_and_pronundict:
            PronunciationDictionary.monophoneToTriphoneDict(self.dict_location, self.tridict_location)
        elif self.have_phonetic:
            triphonetranscr.writePseudoDict(self.tridict_location)
        self.tridict = PronunciationDictionary(self.tridict_location)

        #make list of triphones by combining triphones in dictionary and transcriptions...
        triphoneset1 = self.tridict.getPhoneSet()
        triphoneset2 = triphonetranscr.getPhoneSet()
        triphoneset = [triphone + "\n" for triphone in sorted(set(triphoneset1 + triphoneset2))]
        #write triphoneset to file
        with codecs.open(self.triphoneset_location, "w", encoding="utf-8") as outfh:
            outfh.writelines(triphoneset)

        #clone and tie transition matrices...
        self.models.cloneTriphones(self.triphoneset_location)
        self.models.doEmbeddedRest(self.triphonemlf_location)
        self.models.doEmbeddedRest(self.triphonemlf_location, self.hereststats_location)

        #tie states via decision tree clustering...
        self.models.tieStates(self.hereststats_location, self.triphoneset_location)
        for i in range(2):
            self.models.doEmbeddedRest(self.triphonemlf_location)


    def doAlignment(self):
        """Do forced alignment using the correct resources...
        """
        
        print("LABELING....")

        if self.have_ortho_and_pronundict:
            log.info("Performing alignment (from orthography).")
            self.models.forcedAlignment(self.wordmlf_location, self.dict_location, self.output_dir)
        elif self.have_phonetic:
            if self.cdhmms:
                log.info("Performing alignment (from triphones).")
                self.models.forcedAlignment(self.triphonemlf_location, self.tridict_location, self.output_dir)
            else:
                log.info("Performing alignment (from monophones).")
                self.models.forcedAlignment(self.phonemlf_location, self.dict_location, self.output_dir)


class GenHAlignRealign(GenHAlign):
    """ Adds a realignment stage to GenHAlign which makes use of
    alternate pronunciations in the source_dictinoary and tries to
    catch unforeseen SILs between words...
    """
    def __init__(self, configfile_location, overrides={}, setup_only=False):
        """ Inherit...
        """
        
        GenHAlign.__init__(self, configfile_location, overrides=overrides, setup_only=True)

        log.info("Process: 'GenHAlignRealign'")

        #break here if the procedure will be manually called...
        if setup_only: return        

        log.info("Starting Process.") 
        starttime = time()
        self.organiseTranscriptions()
        self.makeFeats()
        self.initModels()
        self.trainModels()
        self.doAlignment()
        if self.textgrid_output: self.doTextgridOutput()
        if self.postcleanup: self.doCleanup()
        endtime = time()
        log.info("Process Done (in %.0f seconds)." % (endtime - starttime))


    def trainModels(self):
        """Performs training procedure with realignment stage...
        """

        print("RE-ESTIMATING....")
        for i in range(2):
            self.models.doEmbeddedRest(self.phonemlf_location)

        #here we add entries to the dict with SIL phones at the start
        #of all words not neigbouring or being SIL with the hope that
        #the realignment stage will so pick up unlabelled silences
        #between words... This is a bit messy, in pytts_align we will
        #detect the occurrence of SIL in words and seperate this from
        #the word itsself. 

        #There are a class of insertions we want to avoid, we should
        #change this also to not add SILs where closures are present
        #to aid with this.

        # for text in self.transcr.wordlevel.values():
        #     words = text.split()
        #     for prevword, word in zip([None] + words, words):
        #         if prevword is not None:
        #             if any(self.silphone == pronun[-1] for pronun in self.dict[prevword]): #any SIL phones as last seg of prevword?
        #                 continue
        #         if not any(self.silphone == pronun[0] for pronun in self.dict[word]):  #any SIL phones as first seg of word?
        #             pronuns = list(self.dict[word])
        #             for pronun in pronuns:
        #                 self.dict[word] = [self.silphone] + pronun
        # self.dict.writeDict(self.dict_location)
                    

        if self.have_ortho_and_pronundict:
            self.models.reAlignment(self.wordmlf_location, self.dict_location, self.phonemlf_location)
            #prune audio data that did not make it through realignment?
        else:
            print("WARNING: Realignment not possible when labelling from phonetic...")

        for i in range(2):
            self.models.doEmbeddedRest(self.phonemlf_location)


        if self.cdhmms:
            self.makeTriphones()
            
        try:
            nummixups = int(self.nummixs) - 1
            if nummixups >= 1:
                for i in range(nummixups):
                    self.doIncrementMixtures(i+2)
        except ValueError:
            pass
    

class GenTrainASR(GenHAlign):
    """ Defines a process to train HMMs for general ASR usage...
    """

    def __init__(self, configfile_location, overrides={}, setup_only=False):
        """Initialises process (reads from config and sets switches/variables...)...
        """
        
        self.overrides = overrides
        self.configfile_dir = os.path.dirname(configfile_location)
        with codecs.open(configfile_location, encoding="utf-8") as conffh:
            self.config = ConfigParser()
            self.config.readfp(conffh)
        

        #setup log...
        consolehandler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
        consolehandler.setFormatter(formatter)
        log.addHandler(consolehandler)

        #make dirs...
        self.makeDirs()        
        
        #setup log...
        log.removeHandler(consolehandler)
        logfilehandler = logging.FileHandler('%s.log' % (os.path.join(self.working_dir, NAME + "_" + strftime("%Y%m%d%H%M%S"))))
        logfilehandler.setFormatter(formatter)
        log.addHandler(logfilehandler)
        
        #copy configuration file for the record (if possible)...and log configuration...
        log.info("Configuration file used: '%s'" % configfile_location)
        log.info("Overrides defined:\n%s" % pprint.pformat(self.overrides))
        try:
            shutil.copy(configfile_location, self.working_dir)
        except shutil.Error:
            #if copy fails (this is probably because file might already exist here...)
            #fail silently...
            pass
        
        
        #set switches...
        self.orthographic_location = self.getParm("SOURCE", "ORTHOGRAPHIC_TRANSCRIPTIONS", path=True)
        self.pronundict_location = self.getParm("SOURCE", "PRONUNCIATION_DICTIONARY", path=True)
        self.phonetic_location = self.getParm("SOURCE", "PHONETIC_TRANSCRIPTIONS", path=True)
        self.transmap_location = self.getParm("SOURCE", "PHONETIC_TRANSCRIPTIONS_MAP", path=True)
        self.boottranscr_location = self.getParm("SOURCE", "BOOT_TRANSCRIPTIONS", path=True)
        self.bootmap_location = self.getParm("SOURCE", "BOOT_TRANSCRIPTIONS_MAP", path=True)
        self.bootaudio_location = self.getParm("SOURCE", "BOOT_AUDIO", path=True)

        self.cdhmms = self.getParm("SWITCHES", "CDHMMS", boolean=True)
        self.nummixs = self.getParm("SWITCHES", "MIXTURES_PER_STATE")
        self.mappedbootstrap = self.getParm("SWITCHES", "MAPPEDBOOTSTRAP", boolean=True)
        self.postcleanup = self.getParm("SWITCHES", "POSTCLEANUP", boolean=True)

        if bool(self.orthographic_location) and bool(self.pronundict_location):
            self.have_ortho_and_pronundict = True
        else:
            self.have_ortho_and_pronundict = False
        if bool(self.phonetic_location):
            self.have_phonetic = True
        else:
            self.have_phonetic = False

        if bool(self.boottranscr_location) and bool(self.bootaudio_location):
            self.have_bootdata = True
        else:
            self.have_bootdata = False

        if bool(self.transmap_location):
            self.have_transmap = True
        else:
            self.have_transmap = False

        if bool(self.bootmap_location):
            self.have_bootmap = True
        else:
            self.have_bootmap = False        

        #break here if the procedure will be manually called...
        if setup_only: return
        
        log.info("Process: 'GenTrainASR'")

        log.info("Starting Process.") 
        starttime = time()
        self.organiseTranscriptions()
        self.makeFeats()
        self.initModels()
        self.trainModels()
        self.testModels()
        if self.postcleanup: self.doCleanup()
        endtime = time()
        log.info("Process Done (in %.0f seconds)." % (endtime - starttime))


    def makeDirs(self):
        """Make 'working' directory structure...
        """
        
        self.working_dir = self.getParm("PARMS", "WORKING_DIR", path=True)
        self.etc_dir = os.path.join(self.working_dir, GenHAlign.ETC_DIR)
        self.feats_dir = os.path.join(self.working_dir, GenHAlign.FEAT_DIR)
        self.models_dir = os.path.join(self.working_dir, GenHAlign.MODELS_DIR)
        self.bootfeats_dir = os.path.join(self.working_dir, GenHAlign.BOOTFEAT_DIR)
        try:
            os.makedirs(self.working_dir)
        except OSError:
            print("WARNING: Working dir '%s' already existed..." % self.working_dir)
        os.makedirs(self.etc_dir)
        os.makedirs(self.feats_dir)
        os.makedirs(self.models_dir)
        os.makedirs(self.bootfeats_dir)



    def makeFromOrthographic(self):
        """Prepare transcriptions from orthography, using a pronunciation dictionary...
        """
        print("WRITING DICTs AND MLFs FROM ORTHOGRAPHIC TRANSCRIPTIONS.....")
        log.info("Making transcriptions and dicts from orthgraphic transcriptions.")

        self.source_transcr_location = self.orthographic_location
        self.source_dict_location = self.pronundict_location
        self.silphone = self.getParm("PARMS", "SILENCE_PHONE")
        self.silword = self.getParm("PARMS", "SILENCE_WORD")
        self.spphone = self.getParm("PARMS", "SP_PHONE")
        self.normalise_orthography = self.getParm("SWITCHES", "NORMALISE_ORTHOGRAPHY", boolean=True)
        self.dict_location = os.path.join(self.etc_dir, fnjoin(GenHAlign.MAINDICT_BN, GenHAlign.DICT_EXT))
        self.wordmlf_location = os.path.join(self.etc_dir, fnjoin(GenHAlign.WORDTRANSCR_BN, GenHAlign.MLF_EXT))
        self.phonemlf_location = os.path.join(self.etc_dir, fnjoin(GenHAlign.PHONETRANSCR_BN, GenHAlign.MLF_EXT))
        self.monophoneset_location = os.path.join(self.etc_dir, GenHAlign.MONOPHONESET_FN)


        #load transcriptions
        self.transcr = ASRTranscriptionSet(self.source_transcr_location, type="WORD")
        if self.normalise_orthography:
            self.transcr.normalise()                #removes all punctuation and forces lowercase...
        self.dict = PronunciationDictionary(self.source_dict_location)
        #add shortpause to end of each entry not ending in the silence phone:
        for entryname in self.dict:
            for pronun in self.dict[entryname]:
                if pronun[-1] != self.silphone:
                    pronun.append(self.spphone)
        #add silence word:
        if self.silword != "":
            self.dict[self.silword] = self.silphone   #define entry mapping to silence...
            self.dict.sort()

        #check whether dictionary entries cover all words in transcriptions...
        if not self.dict.allWordsInDict(self.transcr):
            log.error("Pronunciation dictionary (%s) does not contain all words." % (self.source_dict_location))
            raise Exception("Some words not found in dictionary....")

        #write dict, MLFs and phoneset...
        self.dict.writeDict(self.dict_location)
        self.transcr.writeWordMLF(self.wordmlf_location)
        ASRTranscriptionSet.wordToPhoneMLF(self.wordmlf_location, self.dict_location, self.phonemlf_location, self.silphone, self.spphone)
        self.phonetranscr = ASRTranscriptionSet(self.phonemlf_location, "PHONE")
        
        if self.have_transmap:
            log.info("Loading transcription map.")
            self.phonetranscr.loadMap(self.transmap_location)

        # and phoneset:
        with codecs.open(self.monophoneset_location, "w", encoding="utf-8") as outfh:
            phoneset = [phone + "\n" for phone in self.dict.getPhoneSet()]
            outfh.writelines(phoneset)

        if self.have_phonetic:
            #check that translation from words matches phonetic transcriptions...
            log.info("Cross checking phonetic sequence from orthography with directly supplied phonetic sequence.")
            correctphonetranscr = ASRTranscriptionSet(self.phonetic_location, "PHONE")
            if not correctphonetranscr.allPhonesMatch(self.phonetranscr):
                log.error("Translated MLF (%(self.phonemlf_location)s) does not " + 
                          "correspond with transcriptions (%(self.phonetic_location))s).")
                raise Exception("Phone MLF does not match phonetic transcriptions...")


    def initModels(self):
        """Initialise HMMs through either 'flatstart' or bootstrapping and defining
           the silence model properly...
        """

        print("INITIALISING MODELS...")

        self.protofile_location = self.getParm("SOURCE", "HMM_PROTOTYPE", path=True)

        self.models = ASRHMMSet(self.models_dir,
                                self.dict.getPhoneSet(),
                                self.silphone,
                                self.spphone,
                                self.protofile_location,
                                self.featconf_location,
                                self.feats_dir)
    
        if self.have_bootdata:
            print("BOOTSTRAP...(NO VARIANCE FLOOR SET...)")
            if self.mappedbootstrap:
                log.info("Performing mapped-bootstrapping.")
                self.models.mappedBootstrapAll(self.bootmlf_location, self.bootfeats_dir, self.phonetranscr)
            else:
                log.info("Performing native bootstrapping.")
                #For each phone do an HInit - HRest combo to init phones...
                self.models.doBootstrapAll(self.bootmlf_location, self.bootfeats_dir)
        else:
            #do flatstart...
            print("FLATSTART....")
            log.info("Performing 'flatstart' initialisation.")
            self.models.doFlatStart()
            for i in range(3):
                self.models.doEmbeddedRest(self.phonemlf_location)
    
        #fix silence model
        self.models.fixSilModels()


    def trainModels(self):
        """Performs training procedure...
        """

        print("RE-ESTIMATING....")
        for i in range(2):
            self.models.doEmbeddedRest(self.phonemlf_location, withsp=True)

        if self.have_ortho_and_pronundict:
            self.models.reAlignment(self.wordmlf_location, self.dict_location, self.silword, self.phonemlf_location, withsp=True)
            #prune audio data that did not make it through realignment:
            

        for i in range(2):
            self.models.doEmbeddedRest(self.phonemlf_location, withsp=True)


        if self.cdhmms:
            self.makeTriphones()
            
        try:
            nummixups = int(self.nummixs) - 1
            if nummixups >= 1:
                for i in range(nummixups):
                    self.doIncrementMixtures(i+2)
        except ValueError:
            pass
        


    def makeTriphones(self):
        """Perform cloning of triphones from monophones as well as triphone tying...
        """

        print("MAKING TRIPHONES....")
        log.info("Making context dependent HMMs.")

        self.triphonemlf_location = os.path.join(self.etc_dir, fnjoin(GenHAlign.TRIPHONETRANSCR_BN, MLF_EXT))
        self.hereststats_location = os.path.join(self.etc_dir, GenHAlign.HERESTSTATS_FN)
        self.triphoneset_location = os.path.join(self.etc_dir, GenHAlign.TRIPHONESET_FN)
        self.tridict_location = os.path.join(self.etc_dir, fnjoin(GenHAlign.TRIDICT_BN, GenHAlign.DICT_EXT))

        #make triphone transcriptions
        ASRTranscriptionSet.monophoneToTriphoneMLF(self.phonemlf_location, self.triphonemlf_location, self.silphone, self.spphone)
        triphonetranscr = ASRTranscriptionSet(self.triphonemlf_location, "PHONE")

        #make triphone dictionary
        if self.have_ortho_and_pronundict:
            PronunciationDictionary.monophoneToTriphoneDict(self.dict_location, self.tridict_location, self.spphone)
        elif self.have_phonetic:
            triphonetranscr.writePseudoDict(self.tridict_location)
        self.tridict = PronunciationDictionary(self.tridict_location)

        #make list of triphones by combining triphones in dictionary and transcriptions...
        triphoneset1 = self.tridict.getPhoneSet()
        triphoneset2 = triphonetranscr.getPhoneSet()
        triphoneset = [triphone + "\n" for triphone in sorted(set(triphoneset1 + triphoneset2))]
        #write triphoneset to file
        with codecs.open(self.triphoneset_location, "w", encoding="utf-8") as outfh:
            outfh.writelines(triphoneset)

        #clone and tie transition matrices...
        self.models.cloneTriphones(self.triphoneset_location)
        self.models.doEmbeddedRest(self.triphonemlf_location)
        self.models.doEmbeddedRest(self.triphonemlf_location, self.hereststats_location)

        #tie states via decision tree clustering...
        self.tiedtriphoneset_location = os.path.join(self.etc_dir, GenHAlign.TIEDTRIPHONESET_FN)
        self.models.tieStates(self.hereststats_location, self.triphoneset_location, self.tiedtriphoneset_location)
        for i in range(2):
            self.models.doEmbeddedRest(self.triphonemlf_location)


    def doIncrementMixtures(self, num):
        """Increments the number of Gaussian mixtures per state by 1 and reestimates...
        """

        print("INCREMENTING MIXTURES....")
        log.info("Incrementing number of mixtures to %s." % (num))
        self.models.doIncrementMixtures()
        if self.cdhmms:
            self.models.doEmbeddedRest(self.triphonemlf_location)
        else:
            self.models.doEmbeddedRest(self.phonemlf_location)
    


class PS_GenHAlign(GenHAlign):
    """ Defines the generic process to perform HMM training and
        forced alignment using pitch synchronous features...
    """

    def __init__(self, configfile_location, overrides={}, setup_only=False):
        """ Inherit...
        """

        GenHAlign.__init__(self, configfile_location, overrides=overrides, setup_only=True)

        log.info("Process: 'PS_GenHAlign'")

        #break here if the procedure will be manually called...
        if setup_only: return        

        log.info("Starting Process.") 
        starttime = time()
        self.makeFeats()
        self.organiseTranscriptions()
        self.crossCheckAudioTranscriptions()
        self.initModels()
        self.trainModels()
        self.doAlignment()
        self.translateAlignments()
        if self.postcleanup: self.doCleanup()
        endtime = time()
        log.info("Process Done (in %.0f seconds)." % (endtime - starttime))


    def makeBootTranscriptions(self):
        """Prepare bootstrap data transcriptions...
        """

        log.info("PS_GenHAlign: Making boot transcriptions.")

        self.boottranscr_location = self.getParm("SOURCE", "BOOT_TRANSCRIPTIONS", path=True)
        self.bootmlf_location = os.path.join(self.etc_dir, fnjoin(GenHAlign.BOOTTRANSCR_BN, GenHAlign.MLF_EXT))
        
        self.boottranscr = ASRTranscriptionSet(self.boottranscr_location, type="PHONE")
        if self.have_bootmap:
            log.info("Loading boot-transcription map.")
            self.boottranscr.loadMap(self.bootmap_location)

        tempmlf = NamedTemporaryFile(mode="w+t", encoding="utf-8")
        self.boottranscr.writePhoneMLF(tempmlf.name, write_boundaries=True, map=self.mappedbootstrap) #map if required..
        self.bootfeats.warpMLF(tempmlf.name, self.bootmlf_location)
        tempmlf.close()


    def makeFeats(self):
        """Perform feature extraction on the necessary audio files...
        """
        print("MAKING FEATS....")
        log.info("PS_GenHAlign: Making feats.")

        self.source_audio_location = self.getParm("SOURCE", "AUDIO", path=True)
        self.featconf_location = self.getParm("SOURCE", "FEATS_CONFIG", path=True)
        
        self.audiofeats = PS_AudioFeatures(self.source_audio_location, self.featconf_location)
        self.audiofeats.makeFeats(self.feats_dir)

        if self.have_bootdata:
            log.info("Making boot feats.")
            self.bootfeats = PS_AudioFeatures(self.bootaudio_location, self.featconf_location)
            self.bootfeats.makeFeats(self.bootfeats_dir)


    def crossCheckAudioTranscriptions(self):
        """ Sanity check: Transcriptions cover audio data?
        """

        #check all labels in transcriptionset...
        if not self.transcr.allLabelsInTranscr(self.audiofeats):
            log.error("Transcription set does not cover all audio files.")
            raise Exception("Transcription set does not cover all audio files....")

        if self.have_bootdata:
            if not self.boottranscr.allLabelsInTranscr(self.bootfeats):
                log.error("Boot transcription set does not cover all boot audio files.")
                raise Exception("Some labels not found in boottranscriptionset....")


    def translateAlignments(self):
        """ Translate HTK times in output labels to actual times...
        """
        
        for filename in os.listdir(self.output_dir):
            self.audiofeats.unwarpRec(os.path.join(self.output_dir, filename),
                                      os.path.join(self.output_dir, filename))   #do changes in place...
        
        


## SCRIPT ADMIN...
############################################################

def setopts():
    """ Setup all possible command line options....
    """
    usage = "usage: %s [options] CONFIG_OVERRIDES" % (NAME)
    version = NAME + " " + __version__
    parser = OptionParser(usage=usage, version=version)
    parser.add_option("-c",
                      "--config",
                      dest="configfile",
                      default=DEF_CONF,
                      help="load program configuration from CONFIGFILE [%default]",
                      metavar="CONFIGFILE")
    parser.add_option("-l",
                      "--loglevel",
                      type="int",
                      dest="loglevel",
                      default=DEF_LOGLEVEL,
                      help="specify log level (Supported levels: 0, 10, 20, 30, 40 or 50) [%default]",
                      metavar="LOGLEVEL")
    parser.add_option("-m",
                      "--method",
                      dest="method",
                      default=DEF_METHOD,
                      help="specify which method to use [%default]",
                      metavar="METHOD")
    return parser


def main():
    parser = setopts()
    opts, args = parser.parse_args()

    assert opts.loglevel in ALLOWED_LOGLEVELS, "Unsupported loglevel: %s" % (opts.loglevel)
    log.setLevel(opts.loglevel)

    assert opts.method in ALLOWED_METHODS, "Unsupported method: %s" % (opts.method)
    
    assert os.path.isfile(opts.configfile), "Could not find a configuration file [%s]" % (opts.configfile)
    
    configfile = os.path.abspath(opts.configfile)

    #make overrides dict...
    args = [arg.split(":") for arg in args]
    try:
        overrides = dict([[":".join(arg[:2]), arg[2]] for arg in args])
    except IndexError:
        raise Exception("Error parsing overrides...")

    if opts.method == "GenHAlign":
        process = GenHAlign(configfile, overrides)
    elif opts.method == "PS_GenHAlign":
        process = PS_GenHAlign(configfile, overrides)
    elif opts.method == "GenTrainASR":
        process = GenTrainASR(configfile, overrides)    
    else:
        #shouldn't get here...
        pass

if __name__ == "__main__":
    main()
