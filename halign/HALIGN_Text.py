#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This module contains all that will be necessary to convert the
    necessary base text resources (such as word level transcriptions
    and dictionaries) to formats which can be used by HTK and the rest
    of HAlign.
"""
from __future__ import unicode_literals, division, print_function # Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os
import sys
import codecs
import logging
import re
import string
import subprocess
from tempfile import NamedTemporaryFile

from speechlabels import parse_path, type_files, Utterance, float_to_htk_int

SCM_EXT = "scm"
LAB_EXT = "lab"
REC_EXT = "rec"
TEXTGRID_EXT = "TextGrid"
MLF_EXT = "mlf"
DICT_EXT = "dict"   # simple pronunciation dictionary format...

HLED_BIN = "HLEd"
HDMAN_BIN = "HDMan"

log = logging.getLogger("HAlign.Text")

class MultitierTranscriptionSet(object):
    """ To manage multitier transcriptions to generate [wordlevel +
        dictionary] for use with HTK process...
    """
    pass

class TranscriptionSet(object):
    """ Manages transcriptions...
    """
    #from string.punctuation except 'apostrophy' and 'dash'
    PUNCTUATION = "!\"#$%&()*+,./:;<=>?@[\\]^_`{|}~" 

    def __init__(self, location, type="WORD"):
        """ Loads transcriptions from file/path...
        """
        self.wordlevel = None
        self.phonelevel = None
        self.boundaries = None
        self.type = type    # This can be 'WORD' or 'PHONE'...

        if self.type == "WORD":
            log.debug(unicode(self) + " loading word level transcriptions from '%s'." % (location))
            if os.path.isdir(location):
                self.wordlevel = self._loadpath_word(location)
            elif os.path.isfile(location):
                if (location.lower().endswith(SCM_EXT)):
                    self.wordlevel = self._load_schemefile(location)
                elif (location.lower().endswith(MLF_EXT)):
                    self.wordlevel = self._load_mlffile(location)
                else:
                    raise Exception("Could not identify transcription source...")
            else:
                raise Exception("Could not identify transcription source...")
        elif self.type == "PHONE":
            log.debug(unicode(self) + " loading phone level transcriptions from '%s'." % (location))
            if os.path.isdir(location):
                self.phonelevel, self.boundaries = self._loadpath_phone(location)
            elif os.path.isfile(location):
                if (location.lower().endswith(MLF_EXT)):
                    self.phonelevel = self._load_mlffile(location)
            else:
                raise Exception("location must be a directory containing label files...")
        else:
            raise Exception("Transcription type unsupported use: WORD | PHONE")

    def _loadpath_word(self, path):
        """ Load from multiple files...
        """
        log.debug(unicode(self) + " loading transcriptions from multiple files.")

        wordlevel = {}

        for filename in type_files(os.listdir(path), LAB_EXT):

            with codecs.open(os.path.join(path, filename), encoding="utf-8") as infh:
                text = infh.read()

            #parsing by assuming words are whitespace delimited:
            wordlist = text.split()
            if len(wordlist) == 0:
                raise Exception("File '%s' is empty..."
                                % (os.path.join(path, filename)))
            
            #assuming unique basenames... (a reasonable assumption)
            key = parse_path(filename)[2]
            if key in wordlevel:
                raise Exception("basename '%s' is not unique..." % (key))
            wordlevel[key] = " ".join(wordlist)

        if len(wordlevel) == 0:
            raise Exception("No transcriptions found in '%s'..."
                            % (path))
        return wordlevel


    def _loadpath_phone(self, path):
        """ Load from multiple files...
        """
        log.debug(unicode(self) + " loading transcriptions from multiple files.")

        phonelevel = {}
        boundaries = {}

        filenames = []
        try:
            for ext in Utterance.SUPPORTED_EXTS:
                filenames.extend(type_files(os.listdir(path), ext))
        except OSError:
            raise

        if len(set(filenames)) != len(filenames):
            raise Exception("Non unique basenames exist....")

        filenames.sort()
        
        for filename in filenames:
            key = parse_path(filename)[2]
            utt = Utterance(os.path.join(path, filename))
            phonelevel[key] = " ".join([entry[1] for entry in utt.entries])
            b = [float_to_htk_int(entry[0]) for entry in utt.entries]
            if all(b) == False:
                boundaries[key] = None
            else:
                boundaries[key] = b

        return phonelevel, boundaries


    def _load_schemefile(self, filepath):
        """ Load from festival style transcriptions file...
        """
        log.debug(unicode(self) + " loading transcriptions from scheme file.")

        quoted = re.compile('".*"')
        bracketed = re.compile('\(.*\)')

        wordlevel = {}

        with codecs.open(filepath, encoding="utf-8") as infh:
            lines = infh.readlines()

        for line in lines:
            transcr = quoted.search(line).group().strip("\"")
            whatsleft = re.sub(quoted, "", line)
            key = bracketed.search(whatsleft).group().strip("(").strip(")").strip()
            if key in wordlevel:
                raise Exception("Non unique names present...")
            wordlevel[key] = transcr

        return wordlevel

    
    def _load_mlffile(self, filepath):
        """ Load from HTK MLF style transcriptions file...
            TODO: Also read time information...
        """
        log.debug(unicode(self) + " loading transcriptions from mlf file.")

        quoted = re.compile('".*"')
        dot = re.compile('\.\n')

        t_items = {}
        items = []

        with codecs.open(filepath, encoding="utf-8") as infh:
            for line in infh:
                if re.match(quoted, line): #new label...
                    items = []
                    key = parse_path(line.strip().strip('"'))[2]
                    if key in t_items:
                        raise Exception("Non unique names present...")
                elif re.match(dot, line):  #end of label...
                    t_items[key] = " ".join(items)
                else:                      #item on line...
                    items.append(line.split()[-1])   #ignores time information at present
        
        return t_items
    

    def loadMap(self, map_location):
        """ Load phonetic mapping from simple text file...
        """
        log.debug(unicode(self) + " loading map from '%s'." % (map_location))

        phoneset = self.getPhoneSet()
        phonemap = {}

        with codecs.open(map_location, encoding="utf-8") as infh:
            for line in infh:
                linelist = line.split()
                try:
                    phonemap[linelist[0]] = linelist[1]
                except IndexError:
                    pass
        
        for phone in phoneset:
            if phone not in phonemap:
                raise Exception("Phone /%s/ not in mapping.." % (phone))
            
        self.phonemap = phonemap


    def writeWordMLF(self, outfilepath, silword=""):
        """ Writes HTK format MLF file...
        """
        log.debug(unicode(self) + " writing word level mlf to '%s'." % (outfilepath))

        with codecs.open(outfilepath, "w", encoding="utf-8") as outfh:
            outfh.write("#!MLF!#\n")
            for key in sorted(self.wordlevel.keys()):
                outfh.write("\"*/%s.%s\"\n" % (key, LAB_EXT))
                if silword == "":
                    for word in self.wordlevel[key].split():
                        outfh.write(word + "\n")
                    outfh.write(".\n")
                else:
                    wordlist = self.wordlevel[key].split()
                    if wordlist[0] != silword:
                        wordlist = [silword] + wordlist
                    if wordlist[-1] != silword:
                        wordlist += [silword]
                    for word in wordlist:
                        outfh.write(word + "\n")
                    outfh.write(".\n")


    def writePhoneMLF(self, outfilepath, silphone=None, write_boundaries=False, map=False, append=False):
        """ Writes HTK format MLF file...
            If silphone is given then makes sure that this phone
            is present at start and end of each utterance....
        """
        log.debug(unicode(self) + " writing phone level mlf to '%s' (with options: write_boundaries=%s, map=%s)."
                  % (outfilepath, write_boundaries, map))

        if write_boundaries and silphone is not None:
            raise Exception("When writing boundaries, we cannot insert silphone...")

        if append:
            mode = "a"
        else:
            mode = "w"

        with codecs.open(outfilepath, mode, encoding="utf-8") as outfh:
            if not append:
                outfh.write("#!MLF!#\n")
            for key in sorted(self.phonelevel.keys()):
                outfh.write("\"*/%s.%s\"\n" % (key, LAB_EXT))
                if silphone is None:
                    if write_boundaries:
                        time_pos = 0
                        for phone, boundary in zip(self.phonelevel[key].split(), self.boundaries[key]):
                            if map:
                                outfh.write(unicode(time_pos) + " " + unicode(boundary) + " " + self.phonemap[phone] + "\n")
                            else:
                                outfh.write(unicode(time_pos) + " " + unicode(boundary) + " " + phone + "\n")
                            time_pos = boundary
                    else:
                        for phone in self.phonelevel[key].split():
                            if map:
                                outfh.write(self.phonemap[phone] + "\n")
                            else:
                                outfh.write(phone + "\n")
                    outfh.write(".\n")
                else:
                    phonelist = self.phonelevel[key].split()
                    if phonelist[0] != silphone:
                        phonelist = [silphone] + phonelist
                    if phonelist[-1] != silphone:
                        phonelist += [silphone]
                    for phone in phonelist:
                        if map:
                            outfh.write(self.phonemap[phone] + "\n")
                        else:
                            outfh.write(phone + "\n")
                    outfh.write(".\n")


    def removePunctuation(self):
        """ Removes all punctuation (except apostrophy and dash) from the
            transcriptions...
        """
        log.debug(unicode(self) + " punctuation removed from word level transcriptions.")

        for key in self.wordlevel:
            tempstr = self.wordlevel[key]
            tempstr = tempstr.translate(
                          string.maketrans(
                              TranscriptionSet.PUNCTUATION,
                              ' ' * len(TranscriptionSet.PUNCTUATION)))
            self.wordlevel[key] = " ".join(tempstr.split())


    def forceLower(self):
        """ Lowers the case for all characters in the transcriptions...
        """
        log.debug(unicode(self) + " word level transcriptions forced to lower case.")

        for key in self.wordlevel:
            self.wordlevel[key] = self.wordlevel[key].lower()


    def normalise(self):
        """ Does: 'removePunctuation' followed by 'forceLower'...
        """
        self.removePunctuation()
        self.forceLower()


    def getWordSet(self):
        """ Returns a sorted unique list of words contained in
            the transcriptions...
        """
        wordset = set()

        for key in self.wordlevel:
            wordset.update(self.wordlevel[key].split())

        return sorted(wordset)

    def getPhoneSet(self):
        """ Returns a sorted unique list of phones (can be triphones)
            containes in the transcriptions...
        """
        phoneset = set()
        
        for key in self.phonelevel:
            phoneset.update(self.phonelevel[key].split())
        
        return sorted(phoneset)

    def writePseudoDict(self, outfile_location):
        """ Writes a 'dictionary' based on phonelist...
        """
        log.debug(unicode(self) + " writing 'pseudo' dictionary to '%s'." % (outfile_location))

        phones = self.getPhoneSet()

        with codecs.open(outfile_location, "w", encoding="utf-8") as outfh:
            for phone in phones:
                outfh.write(phone + " " + phone + "\n")


    def unmapMLF(self, inmlf_location, outmlf_location, targetphone):
        """Reverse map to specific phone...
        """
        log.debug(unicode(self) + " unmapped mlf written to '%s' (with targetphone='%s')." % (outmlf_location, targetphone))

        fromcat = self.phonemap[targetphone]

        #write temp file - HLEd commands...
        tempfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        tempfh.write("RE %s %s\n" % (targetphone, fromcat))
        tempfh.flush()
        
        p = subprocess.Popen(" ".join([HLED_BIN,
                                       "-A",
                                       "-D",
                                       "-V",
                                       "-T",
                                       "1",
                                       "-l",
                                       "'*'",
                                       "-i",
                                       outmlf_location,
                                       tempfh.name,
                                       inmlf_location]),
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             close_fds = True,
                             shell = True)
        so, se = p.communicate()
        log.info("unmapMLF:\n" +
                 "================================================================================\n" +
                 unicode(so, encoding="utf-8") + 
                 "================================================================================\n")
        if bool(se):
            log.warning("unmapMLF:\n" +
                        "================================================================================\n" +
                        unicode(se, encoding="utf-8") +
                        "================================================================================\n")
        returnval = p.returncode

        tempfh.close()

        if returnval != 0:
            raise Exception(HLED_BIN + " failed with code: " + unicode(returnval))

        return returnval


    def wordToPhoneMLF(cls, inmlf_name, dict_name, outmlf_name):
        """ Runs HLEd to convert a word level MLF to phone level MLF...
        """
        #write temp file - HLEd commands...
        tempfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        tempfh.write("EX\n")
        tempfh.flush()
        
        p = subprocess.Popen(" ".join([HLED_BIN,
                                       "-A",
                                       "-D",
                                       "-V",
                                       "-T",
                                       "1",
                                       "-l",
                                       "'*'",
                                       "-d",
                                       dict_name,
                                       "-i",
                                       outmlf_name,
                                       tempfh.name,
                                       inmlf_name]),
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             close_fds = True,
                             shell = True)
        so, se = p.communicate()
        log.info("wordToPhoneMLF:\n" +
                 "================================================================================\n" +
                 unicode(so, encoding="utf-8") +
                 "================================================================================\n")
        if bool(se):
            log.warning("wordToPhoneMLF:\n" +
                        "================================================================================\n" +
                        unicode(se, encoding="utf-8") +
                        "================================================================================\n")
        returnval = p.returncode

        tempfh.close()

        if returnval != 0:
            raise Exception(HLED_BIN + " failed with code: " + unicode(returnval))

        return returnval
    wordToPhoneMLF = classmethod(wordToPhoneMLF)


    def monophoneToTriphoneMLF(cls, inmlf_name, outmlf_name, silphone, spphone=None):
        """ Runs HLEd to convert a monophone based MLF to a triphone based MLF...
        """
        #write temp file - HLEd commands...
        tempfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        if spphone is None:
            tempfh.write("WB %s\nTC\n" % (silphone))
        else:
            tempfh.write("WB %s\nWB %s\nNB %s\nTC\n" % (silphone, spphone, spphone))
        tempfh.flush()
        
        p = subprocess.Popen(" ".join([HLED_BIN,
                                       "-A",
                                       "-D",
                                       "-V",
                                       "-T",
                                       "1",
                                       "-l",
                                       "'*'",
                                       "-i",
                                       outmlf_name,
                                       tempfh.name,
                                       inmlf_name]),
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             close_fds = True,
                             shell = True)
        so, se = p.communicate()
        log.info("monophoneToTriphoneMLF:\n" +
                 "================================================================================\n" +
                 unicode(so, encoding="utf-8") +
                 "================================================================================\n")
        if bool(se):
            log.warning("monophoneToTriphoneMLF:\n" +
                        "================================================================================\n" +
                        unicode(se, encoding="utf-8") +
                        "================================================================================\n")
        returnval = p.returncode

        tempfh.close()

        if returnval != 0:
            raise Exception(HLED_BIN + " failed with code: " + unicode(returnval))

        return returnval
    monophoneToTriphoneMLF = classmethod(monophoneToTriphoneMLF)


    def allLabelsInTranscr(self, audiofeats):
        """ Go through filelabels in 'audiofeats', checking whether all labels
            are present in the transcriptions...
        """
        missinglabels = []
        if self.wordlevel is not None:
            translabels = list(self.wordlevel.keys())
        else:
            translabels = list(self.phonelevel.keys())
        filelabels = [parse_path(filename)[2] \
                      for filename in audiofeats.getWavFilelist()]

        if len(filelabels) != len(translabels):
            print("WARNING: %s transcriptions and %s audio files" % (len(translabels), len(filelabels)))

        for filelabel in filelabels:
            if filelabel not in translabels:
                missinglabels.append(filelabel)
        if len(missinglabels) > 0:
            print("MISSING TRANSCRIPTIONS:")
            for lin in missinglabels:
                print("\t" + lin)
            return False
        else:
            return True


    def allPhonesMatch(self, transcriptionset):
        """ Compare 'transcriptionset' with self to ensure that phone sequences are equivalent...
        """
        
        if len(self.phonelevel) != len(transcriptionset.phonelevel):
            print("WARNING: Number of transcriptions in sets differ...")

        for key in self.phonelevel:
            try:
                if self.phonelevel[key] != transcriptionset.phonelevel[key]:
                    return False
            except KeyError:
                raise Exception("Transcription sets are missmatched...")
        
        return True


class ASRTranscriptionSet(TranscriptionSet):
    
    def writeWordMLF(self, outfilepath):
        """ Writes HTK format MLF file...
        """
        log.debug(unicode(self) + " writing word level mlf to '%s'." % (outfilepath))

        with codecs.open(outfilepath, "w", encoding="utf-8") as outfh:
            outfh.write("#!MLF!#\n")
            for key in sorted(self.wordlevel.keys()):
                outfh.write("\"*/%s.%s\"\n" % (key, LAB_EXT))
                for word in self.wordlevel[key].split():
                    outfh.write(word + "\n")
                outfh.write(".\n")


    def wordToPhoneMLF(cls, inmlf_name, dict_name, outmlf_name, silphone, spphone):
        """ Runs HLEd to convert a word level MLF to phone level MLF...
        """
        #write temp file - HLEd commands...
        tempfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        tempfh.write("EX\n")
        tempfh.write("DE %s\n" % (spphone))
        tempfh.flush()
        
        p = subprocess.Popen(" ".join([HLED_BIN,
                                       "-A",
                                       "-D",
                                       "-V",
                                       "-T",
                                       "1",
                                       "-l",
                                       "'*'",
                                       "-d",
                                       dict_name,
                                       "-i",
                                       outmlf_name,
                                       tempfh.name,
                                       inmlf_name]),
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             close_fds = True,
                             shell = True)
        so, se = p.communicate()
        log.info("wordToPhoneMLF:\n" +
                 "================================================================================\n" +
                 unicode(so, encoding="utf-8") +
                 "================================================================================\n")
        if bool(se):
            log.warning("wordToPhoneMLF:\n" +
                        "================================================================================\n" +
                        unicode(se, encoding="utf-8") +
                        "================================================================================\n")
        returnval = p.returncode

        tempfh.close()

        if returnval != 0:
            raise Exception(HLED_BIN + " failed with code: " + unicode(returnval))

        return returnval
    wordToPhoneMLF = classmethod(wordToPhoneMLF)



class PronunciationDictionary(object):
    """ Manages manipulation of dictionaries (mostly for dictionary reading
        and writing...

        Implementation relies on a list of entrynames that preserves
        the ordering of items and a dictionary that maps these names
        to lists defining pronunciations.... thus ordering of
        pronunciations are also preserved...
    """
    
    ALLOWABLE_CHARS = string.ascii_letters + string.digits + '@#'

    def __init__(self, location):
        """ Loads dictionary from file...
        """

        self.entries = {}
        self.entrynames = []
        self.entrycount = 0

        if os.path.isfile(location):
            log.debug(unicode(self) + " loading dictionary from '%s'." % (location))
            if (location.lower().endswith(SCM_EXT)):
                self._load_schemefile(location)
            elif (location.lower().endswith(DICT_EXT)):
                self._load_simpledict(location)
            else:
                raise Exception("Could not identify dictionary type...")
        else:
            raise Exception("Could not find dictionary at '%s'..." % (location))
        
    def __len__(self):
        return self.entrycount #sum(len(self.entries[e]) for e in self.entrynames)

    def __getitem__(self, entryname):
        """ returns list of pronuns...
        """
        return self.entries[entryname]
    
    def __setitem__(self, entryname, phones):
        """ Add an entry to the dictionary...  'entryname' is the
            entry name and 'phones' is an iterable representing a
            phone sequence...
        """
        log.debug(unicode(self) + " adding entry to dictionary ('%s' '%s')." % (entryname, phones))
        
        if entryname in self.entrynames:
            pronun = list(phones)
            if not pronun in self.entries[entryname]:
                self.entries[entryname].append(pronun)
            else:
                log.debug(unicode(self) + " trying to add duplicate entry into dictionary ('%s' '%s')." % (entryname, phones))
                self.entrycount -= 1
        else:
            self.entrynames.append(entryname)
            self.entries[entryname] = [list(phones)]
        self.entrycount += 1


    def __delitem__(self, entryname):
        """ Deletes entryname from dictionary.
        """
        self.entrynames.remove(entryname)
        self.entrycount -= len(self.entries[entryname])
        del self.entries[entryname]


    def __contains__(self, entryname):
        """ Contains entryname?
        """
        return entryname in self.entries
    
    def __iter__(self):
        """ Iterate over words..
        """
        return self.entrynames.__iter__()


    def _load_schemefile(self, filepath):
        """ Loads dictionary from festival lexicon format (scheme/lisp)....
        """
        
        log.debug(unicode(self) + " loading dictionary from scheme file.")

        import pyparsing as P
        print("LOADING Dictionary from SCHEME file:")

        #setup parsing grammar...
        lparen = P.Literal("(").suppress()
        rparen = P.Literal(")").suppress()
        sexpr_string = P.Forward()
        sexpr_item = P.quotedString.setParseAction(P.removeQuotes) | \
                     P.Word(PronunciationDictionary.ALLOWABLE_CHARS) | \
                     P.Group(sexpr_string)
        sexpr_string << lparen + P.delimitedList(sexpr_item, P.White()) + rparen

        with codecs.open(filepath, encoding="utf-8") as infh:
            for i, entry in enumerate(infh):
                #sys.stdout.write("\r\t%s lines read..." % (i+1))
                try:
                    nested = sexpr_string.parseString(entry)
                    try:
                        entryname = nested[0]
                        phones = []
                        for stuff in [syl[0] for syl in nested[2]]:
                            phones.extend(stuff)
                        self[entryname] = phones
                    except IndexError:
                        raise "\rError parsing file at line: " + unicode(i+1)
                except P.ParseException:
                    print("\r\tSkipping line: " + unicode(i+1))
                    
        print("\t%s entries parsed from %s input lines" % (len(self), i+1))


    def _load_simpledict(self, filepath):
        """ Loads dictionary from simple HTK friendly format...
        """
        
        log.debug(unicode(self) + " loading dictionary from simple dictionary file.")

        print("LOADING Dictionary from HTK file:")

        with codecs.open(filepath, encoding="utf-8") as infh:
            for i, entry in enumerate(infh):
               #sys.stdout.write("\r\t%s lines read..." % (i+1))
               try:
                   entrylist = entry.split()
                   entryname = entrylist[0]
                   phones = entrylist[1:]
                   self[entryname] = phones
               except IndexError:
                   raise "\rError parsing file at line: " + unicode(i+1)
               
        print("\t%s entries parsed from %s input lines" % (len(self), i+1))


    def sort(self, key=None, reverse=False):
        self.entrynames.sort(key=key, reverse=reverse)


    def writeDict(self, outfilepath):
        """ Writes 'self.entries' to HTK friendly pronun. dictionary...
        """

        log.debug(unicode(self) + " writing dictionary to '%s'." % (outfilepath))

        with codecs.open(outfilepath, "w", encoding="utf-8") as outfh:
            for entryname in self.entrynames:
                for pronun in self.entries[entryname]:
                    outfh.write(entryname + " " + " ".join(pronun) + "\n")


    def getPhoneSet(self):
        """ Returns a sorted unique list of phones contained in
            the dictionary...
        """
        phoneset = set()

        for pronuns in self.entries.values():
            for pronun in pronuns:
                phoneset.update(pronun)

        return sorted(phoneset)

    def getWordSet(self):
        """ Returns a sorted unique list of words contained in
            the dictionary...
        """
        return sorted(set(self.entrynames))

    def allWordsInDict(self, transcriptionset):
        """ Go through words in transcriptions, checking whether all words
            are present in the dictionary....
        """
        missingwords = []
        dict_wordlist = self.getWordSet()
        for word in transcriptionset.getWordSet():  #this coupling is bad and unnecessary
            if word not in dict_wordlist:
                missingwords.append(word)
        if len(missingwords) > 0:
            print("MISSING WORDS:")
            for w in missingwords:
                print("\t" + w)
            return False
        else:
            return True
        
    def monophoneToTriphoneDict(cls, inputdictlocation, outputdictlocation, spphone=None):
        """ Run HDMan to create a triphone dictionary...
        """
        
        #write temp file - HDMan commands...
        tempfh = NamedTemporaryFile(mode="w+t")#, encoding="utf-8")
        tempfh.write("TC\n")
        tempfh.flush()
        
        if spphone is None:
            spoption = ""
        else:
            spoption = "-b %s" % (spphone)

        p = subprocess.Popen(" ".join([HDMAN_BIN,
                                       "-A",
                                       "-D",
                                       "-V",
                                       "-T",
                                       "1",
                                       spoption,
                                       "-g",
                                       tempfh.name,
                                       outputdictlocation,
                                       inputdictlocation]),
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             close_fds = True,
                             shell = True)
        so, se = p.communicate()
        log.info("monophoneToTriphoneDict:\n" +
                 "================================================================================\n" +
                 unicode(so, encoding="utf-8") +
                 "================================================================================\n")
        if bool(se):
            log.warning("monophoneToTriphoneDict:\n" +
                        "================================================================================\n" +
                        unicode(se, encoding="utf-8") +
                        "================================================================================\n")
        returnval = p.returncode

        tempfh.close()

        if returnval != 0:
            raise Exception(HDMAN_BIN + " failed with code: " + unicode(returnval))

        return returnval
    monophoneToTriphoneDict = classmethod(monophoneToTriphoneDict)

    
    def getUniqueEntryDictionary(self):
        """Returns a Python dictionary version of the dictionary...
           (Implications: Multiple entries of the same word will be lost...)
        """
        d = {}
        for entryname, pronuns in self.entries.items():
            d[entryname] = pronuns[0]
        return d


if __name__ == "__main__":
    print("This file is to be used by HAlign.py...")
