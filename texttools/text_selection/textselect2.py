#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Implements text selection for TTS based on a simple greedy
    algorithm suggested in: "Methods for Optimal Text Selection" by
    Van Santen & Buchsbaum, 1997.
    Main reason for writing this is so that we may integrate the use
    of the TTS front-end for phonetisation and easily modify/overwrite
    the "score_utt" methods according to our requirements and define
    additional selection strategies.

    Potential issues:
        - Relies on RAM to contain all text and stats, might have to
          adapt this if you want to work with über-large corpora on
          your laptop.

    DEMITASSE: Implementation is overly complicated: simplify!
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"
__date__ = "Oct. 2010"

import os, sys
import copy
import codecs
from collections import defaultdict
from itertools import izip

import ttslab

def natural_numbers():
    i = 1
    while True:
        yield i
        i += 1

class TextCorpus(object):
    """ Contains a set of utterances and has a notion of whether an
        utterance has been selected or not, which influences the
        statistics...
    """
    
    def __init__(self, textfname=None, unitsfname=None, unit_seperator=None):
        self.utts = {}
        self.unselected_unitfreqs = defaultdict(int)
        self.selected = set()
        self.unselected = set()

        if textfname is not None and unitsfname is not None:
            tfile = codecs.open(textfname, "r", encoding="utf-8")
            ufile = codecs.open(unitsfname, "r", encoding="utf-8")
            for textline, unitsline in izip(tfile, ufile):
                #read:
                text = textline.strip()
                units = unitsline.split(unit_seperator)
                #count units:
                unitfreqs = defaultdict(int)
                for unit in units:
                    unitfreqs[unit] += 1
                #append utt with stats:
                self.append_utt(text, unitfreqs)
            tfile.close()
            ufile.close()
        
    def __len__(self):
        return len(self.utts)

    def __iter__(self):
        return self.utts.__iter__()

    def __getitem__(self, key):
        return self.utts.__getitem__(key)


    def append_utt(self, text, unitfreqs):
        self.utts[text] = {"numunits": sum([unitfreqs[unit] for unit in unitfreqs]),
                           "unitfreqs": unitfreqs}
        self.set_unselected(text)

            
    def set_selected(self, text):
        if text in self.utts:
            self.selected.add(text)
            self.unselected.remove(text)
        else:
            raise Exception("Utterance not in corpus:\n%s\n" % (text))

        for unit in self.utts[text]["unitfreqs"]:
            self.unselected_unitfreqs[unit] -= self.utts[text]["unitfreqs"][unit]


    def set_unselected(self, text):
        if text in self.utts:
            self.unselected.add(text)
            try:
                self.selected.remove(text)
            except:
                pass
        else:
            raise Exception("Utterance not in corpus:\n%s\n" % (text))

        for unit in self.utts[text]["unitfreqs"]:
            self.unselected_unitfreqs[unit] += self.utts[text]["unitfreqs"][unit]


class TextSelector(object):
    """ This class performs text selection by handling two TextCorpus
        instances: the "sourcecorpus" and "selectedcorpus", a simple
        selection strategy is implemented: "select_minimal" and two
        utterance scoring methods.
    """

    def __init__(self, sourcecorpus, units, unit_threshold, ref_unitfreqs=None):
        self.sourcecorpus = sourcecorpus
        self.wanted_units = set(units)
        self.unit_threshold = int(unit_threshold)
        if ref_unitfreqs is not None:
            self.ref_unitfreqs = ref_unitfreqs
        else:
            self.ref_unitfreqs = copy.deepcopy(self.sourcecorpus.unselected_unitfreqs)


    def select_minimal(self):
        """ Select utterances to cover at least unit_threshold
            occurrences of wanted_units...
        """
        self.selected_corpus = TextCorpus()

        for i in natural_numbers():
            bestscore = 0.0
            bestutttext = None
            for utttext in self.sourcecorpus.unselected:
                score = self.score_utt(utttext)
                if score == bestscore and score != 0.0:
                    if self.score_utt2(utttext) > self.score_utt2(bestutttext):
                        bestscore = score
                elif score > bestscore:
                    bestutttext = utttext
                    bestscore = score
            if bestscore == 0.0:
                #we are unable to find sentences that contribute to
                #wanted_units
                break
            #add utt to new corpus and set selected:
            self.selected_corpus.append_utt(bestutttext, self.sourcecorpus[bestutttext]["unitfreqs"])
            self.selected_corpus.utts[bestutttext].update({"rank": i, "score": bestscore})
            self.sourcecorpus.set_selected(bestutttext)
            #update wanted units
            to_remove = [unit for unit in self.wanted_units
                         if unit in self.selected_corpus.unselected_unitfreqs and
                         self.selected_corpus.unselected_unitfreqs[unit] >= self.unit_threshold]
            for unit in to_remove:
                self.wanted_units.remove(unit)

            #feedback on current selection:
            print("UTTERANCES SELECTED: %s" % (i))
            print("CURRENT SELECTION:")
            print("\tTEXT: %s" % bestutttext)
            print("\tSCORE: %s" % bestscore)
            print("------------------------------")
#            print("UNITS: %s" % self.sourcecorpus[bestutttext]["unitfreqs"])
#            print("WANTED_UNITS: %s" % self.wanted_units)

            #have we achieved complete coverage?
            if len(self.wanted_units) == 0:
                break
        
        return self.selected_corpus


    def score_utt(self, utt):
        """ scores utterances based on remaining wanted_units scaled
            with the inverse of the frequency of occurrence in the
            original reference corpus...
        """
        return sum([self.sourcecorpus[utt]["unitfreqs"][unit] / self.ref_unitfreqs[unit]
                    for unit in self.sourcecorpus[utt]["unitfreqs"] if unit in self.wanted_units])


    def score_utt2(self, utt):
        """ secondary score calculated when primary scores are
            equal...
        """
        #if scores are equal choose longest utterance:
        #return self.sourcecorpus[utt]["numunits"]
        #if scores are equal choose utterance to diversify units (adding units with low freq in selected):
        sigma = 0.0
        for unit in self.sourcecorpus[utt]["unitfreqs"]:
            if unit in self.selected_corpus.unselected_unitfreqs:
                sigma += self.sourcecorpus[utt]["unitfreqs"][unit] / self.selected_corpus.unselected_unitfreqs[unit]
        return sigma


class TextSelectorWordLimit(TextSelector):
    def __init__(self, sourcecorpus, units, unit_threshold, wordlimit, ref_unitfreqs=None):
        TextSelector.__init__(self,
                              sourcecorpus=sourcecorpus,
                              units=units,
                              unit_threshold=unit_threshold,
                              ref_unitfreqs=ref_unitfreqs)
        self.wordlimit = wordlimit


    def select_minimal(self):
        """ Select utterances to cover at least unit_threshold
            occurrences of wanted_units...
        """
        self.selected_corpus = TextCorpus()
        nwordsselected = 0 #DEMITASSE: this is a hack

        for i in natural_numbers():
            bestscore = 0.0
            bestutttext = None
            for utttext in self.sourcecorpus.unselected:
                score = self.score_utt(utttext)
                if score == bestscore and score != 0.0:
                    if self.score_utt2(utttext) > self.score_utt2(bestutttext):
                        bestscore = score
                elif score > bestscore:
                    bestutttext = utttext
                    bestscore = score
            if bestscore == 0.0:
                #we are unable to find sentences that contribute to
                #wanted_units
                break
            #add utt to new corpus and set selected:
            nwordsselected += len(bestutttext.split())
            self.selected_corpus.append_utt(bestutttext, self.sourcecorpus[bestutttext]["unitfreqs"])
            self.selected_corpus.utts[bestutttext].update({"rank": i, "score": bestscore})
            self.sourcecorpus.set_selected(bestutttext)
            #update wanted units
            to_remove = [unit for unit in self.wanted_units
                         if unit in self.selected_corpus.unselected_unitfreqs and
                         self.selected_corpus.unselected_unitfreqs[unit] >= self.unit_threshold]
            for unit in to_remove:
                self.wanted_units.remove(unit)

            #feedback on current selection:
            print("UTTERANCES SELECTED: %s" % (i))
            print("WORDS SELECTED: %s" % (nwordsselected))
            print("CURRENT SELECTION:")
            print("\tTEXT: %s" % bestutttext)
            print("\tSCORE: %s" % bestscore)
            print("------------------------------")
#            print("UNITS: %s" % self.sourcecorpus[bestutttext]["unitfreqs"])
#            print("WANTED_UNITS: %s" % self.wanted_units)

            #have we achieved complete coverage or reached wordlimit?
            if len(self.wanted_units) == 0 or nwordsselected > self.wordlimit:
                break
        
        return self.selected_corpus


def get_triphones(voice, sentences):
    psentences = []
    units = defaultdict(int)
    for i, sentence in enumerate(sentences):
        print("SYNTHESIZING: %s/%s" % (i+1, len(sentences)))
        u = voice.synthesize(sentence, "text-to-segments")
        phseq = [ph["name"] for ph in u.get_relation("Segment")]
        triphseq = ["-".join([ph1, ph2, ph3]) for ph1, ph2, ph3 in zip(phseq, phseq[1:], phseq[2:])]
        psentences.append(" ".join(triphseq))
        for unit in triphseq:
            units[unit] += 1
    return psentences, units

def get_diphones(voice, sentences):
    psentences = []
    units = defaultdict(int)
    for i, sentence in enumerate(sentences):
        print("SYNTHESIZING: %s/%s" % (i+1, len(sentences)))
        u = voice.synthesize(sentence, "text-to-segments")
        phseq = [ph["name"] for ph in u.get_relation("Segment")]
        diphseq = ["-".join([ph1, ph2]) for ph1, ph2 in zip(phseq, phseq[1:])]
        psentences.append(" ".join(diphseq))
        for unit in diphseq:
            units[unit] += 1
    return psentences, units

def get_tritones(voice, sentences):
    psentences = []
    units = defaultdict(int)
    for i, sentence in enumerate(sentences):
        print("SYNTHESIZING: %s/%s" % (i+1, len(sentences)))
        u = voice.synthesize(sentence, "text-to-segments")
        syls = [str(syl["tone"]) for syl in u.get_relation("Syllable")]
        tritones = ["-".join([t1, t2, t3]) for t1, t2, t3 in zip(syls, syls[1:], syls[2:])]
        psentences.append(" ".join(tritones))
        for unit in tritones:
            units[unit] += 1
    return psentences, units


def phonetize(args, unittype="diphones"):
    """ Procedure to use ttslab as TTS frontend in order to phonetize
        text before selection.
    """
    #load voice:
    voice = ttslab.fromfile(args.voicefile)

    #load text:
    sentences = []
    with codecs.open(args.sourcetextfile, "r", encoding="utf-8") as infh:
        for line in infh:
            line = line.strip()
            if line != "":
                sentences.append(line)
            else:
                print("WARNING: Empty line in source text file...")

    #phonetize:
    if unittype == "diphones":
        psentences, units = get_diphones(voice, sentences)
    elif unittype == "triphones":
        psentences, units = get_triphones(voice, sentences)
    elif unittype == "tritones":
        psentences, units = get_tritones(voice, sentences)
    else:
        raise NotImplementedError

    #save:
    with codecs.open(args.unitsfile, "w", encoding="utf-8") as outfh:
        outfh.write("\n".join(psentences) + "\n")
    unitfreqs = units.items()
    unitfreqs.sort(key=lambda x:x[1])
    with codecs.open(args.unitfreqsfile, "w", encoding="utf-8") as outfh:
        outfh.write("\n".join(["%s %s" % e for e in unitfreqs]) + "\n")


def phonetize_triphones(args):
    phonetize(args, unittype="triphones")

def phonetize_diphones(args):
    phonetize(args, unittype="diphones")

def phonetize_tritones(args):
    phonetize(args, unittype="tritones")


def select_simple(args):
    """ To set up and run the "select_minimal" method from the CLI...
    """

    #load:
    sourcecorpus = TextCorpus(args.sourcetextfile, args.unitsfile)
    with codecs.open(args.wantedunitsfile, "r", encoding="utf-8") as infh:
        wantedunits = [line.split()[0] for line in infh if line.strip() != ""]

    #select:
    ts = TextSelector(sourcecorpus, wantedunits, args.minwanted)
    selectedcorpus = ts.select_minimal()
    
    #save:
    selected = [(selectedcorpus[text]["rank"], text) for text in selectedcorpus]
    selected.sort(key=lambda x:x[0])
    
    with codecs.open(args.selectedtextfile, "w", encoding="utf-8") as outfh:
        outfh.write("\n".join([e[1] for e in selected]) + "\n")

    unitfreqs = selectedcorpus.unselected_unitfreqs.items()
    unitfreqs.sort(key=lambda x:x[1])
    with codecs.open(args.selectedunitfreqsfile, "w", encoding="utf-8") as outfh:
        outfh.write("\n".join(["%s %s" % e for e in unitfreqs]) + "\n")
    
    with codecs.open(args.uncoveredunitsfile, "w", encoding="utf-8") as outfh:
        outfh.write("\n".join(sorted(ts.wanted_units)) + "\n")


def select_simple_wordlimit(args):
    """ To set up and run the "select_minimal" method from the CLI...
    """

    #load:
    sourcecorpus = TextCorpus(args.sourcetextfile, args.unitsfile)
    with codecs.open(args.wantedunitsfile, "r", encoding="utf-8") as infh:
        wantedunits = [line.split()[0] for line in infh if line.strip() != ""]

    #select:
    ts = TextSelectorWordLimit(sourcecorpus, wantedunits, args.minwanted, args.wordlimit)
    selectedcorpus = ts.select_minimal()
    
    #save:
    selected = [(selectedcorpus[text]["rank"], text) for text in selectedcorpus]
    selected.sort(key=lambda x:x[0])
    
    with codecs.open(args.selectedtextfile, "w", encoding="utf-8") as outfh:
        outfh.write("\n".join([e[1] for e in selected]) + "\n")

    unitfreqs = selectedcorpus.unselected_unitfreqs.items()
    unitfreqs.sort(key=lambda x:x[1])
    with codecs.open(args.selectedunitfreqsfile, "w", encoding="utf-8") as outfh:
        outfh.write("\n".join(["%s %s" % e for e in unitfreqs]) + "\n")
    
    with codecs.open(args.uncoveredunitsfile, "w", encoding="utf-8") as outfh:
        outfh.write("\n".join(sorted(ts.wanted_units)) + "\n")


########################################
## SCRIPT ADMIN

def setup_arguments():
    """ Setup all possible command line arguments....
    """
    
    from argparse import ArgumentParser

    #defaults:
    NAME = "textselect2.py"
    DEF_SOURCETEXTFILE = "source.txt"
    DEF_UNITSFILE = "units.txt"
    DEF_UNITFREQSFILE = "unitfreqs.txt"
    DEF_MINWANTED = 3
    DEF_WORDLIMIT = 6000 #based on estimate for about 60 minutes of Xitsonga audio...?
    DEF_SELECTEDTEXTFILE = "selected.txt"
    DEF_SELECTEDUNITFREQSFILE = "selectedunitfreqs.txt"
    DEF_UNCOVEREDUNITSFILE = "unitsnotcovered.txt"

    #create top-level parser
    parser = ArgumentParser(description="Used to either phonetize text or perform text selection given previously phonetized text...",
                            prog=NAME)
    subparsers = parser.add_subparsers()
    
    #create parser for the "phonetize_triphones" command:
    parser_a = subparsers.add_parser("phonetize_triphones",
                                     help="phonetize_triphones help")
    parser_a.add_argument("voicefile",
                          help="voice file location",
                          metavar="VOICEFILE")
    parser_a.add_argument("sourcetextfile",
                          help="input text file location (one utterance per line)",
                          metavar="SOURCETEXTFILE",
                          default=DEF_SOURCETEXTFILE)
    parser_a.add_argument("unitsfile",
                          help="output phonetized text file location (corresponds line by line to input file)",
                          metavar="UNITSFILE",
                          default=DEF_UNITSFILE)
    parser_a.add_argument("unitfreqsfile",
                          help="output text file with unit frequencies",
                          metavar="UNITFREQSFILE",
                          default=DEF_UNITFREQSFILE)
    parser_a.set_defaults(function=phonetize_triphones)

    #create parser for the "phonetize_tritones" command:
    parser_a = subparsers.add_parser("phonetize_tritones",
                                     help="phonetize_tritones help")
    parser_a.add_argument("voicefile",
                          help="voice file location",
                          metavar="VOICEFILE")
    parser_a.add_argument("sourcetextfile",
                          help="input text file location (one utterance per line)",
                          metavar="SOURCETEXTFILE",
                          default=DEF_SOURCETEXTFILE)
    parser_a.add_argument("unitsfile",
                          help="output phonetized text file location (corresponds line by line to input file)",
                          metavar="UNITSFILE",
                          default=DEF_UNITSFILE)
    parser_a.add_argument("unitfreqsfile",
                          help="output text file with unit frequencies",
                          metavar="UNITFREQSFILE",
                          default=DEF_UNITFREQSFILE)
    parser_a.set_defaults(function=phonetize_tritones)

    #create parser for the "phonetize_diphones" command:
    parser_a = subparsers.add_parser("phonetize_diphones",
                                     help="phonetize_diphones help")
    parser_a.add_argument("voicefile",
                          help="voice file location",
                          metavar="VOICEFILE")
    parser_a.add_argument("sourcetextfile",
                          help="input text file location (one utterance per line)",
                          metavar="SOURCETEXTFILE",
                          default=DEF_SOURCETEXTFILE)
    parser_a.add_argument("unitsfile",
                          help="output phonetized text file location (corresponds line by line to input file)",
                          metavar="UNITSFILE",
                          default=DEF_UNITSFILE)
    parser_a.add_argument("unitfreqsfile",
                          help="output text file with unit frequencies",
                          metavar="UNITFREQSFILE",
                          default=DEF_UNITFREQSFILE)
    parser_a.set_defaults(function=phonetize_diphones)


    #create parser for the "select_simple" command:
    parser_b = subparsers.add_parser("select_simple",
                                     help="select_simple help")
    parser_b.add_argument("sourcetextfile",
                          help="input text file location (one utterance per line)",
                          metavar="SOURCETEXTFILE",
                          default=DEF_SOURCETEXTFILE)
    parser_b.add_argument("unitsfile",
                          help="input phonetized text file location (corresponds line by line to text file)",
                          metavar="UNITSFILE",
                          default=DEF_UNITSFILE)
    parser_b.add_argument("wantedunitsfile",
                          help="input text containing list of units to select for (one per line, may use 'unitfreqsfile')",
                          metavar="WANTEDUNITSFILE",
                          default=DEF_UNITFREQSFILE)
    parser_b.add_argument("minwanted",
                          help="if 'minwanted' of all wanted units have been selected, terminate selection",
                          metavar="MINWANTED",
                          type=int,
                          default=DEF_MINWANTED)
    parser_b.add_argument("selectedtextfile",
                          help="output selected text file location",
                          metavar="SELECTEDTEXTFILE",
                          default=DEF_SELECTEDTEXTFILE)
    parser_b.add_argument("selectedunitfreqsfile",
                          help="output text file with selected unit frequencies",
                          metavar="SELECTEDUNITFREQSFILE",
                          default=DEF_SELECTEDUNITFREQSFILE)
    parser_b.add_argument("uncoveredunitsfile",
                          help="output text file containing list of wanted units for which we could not select/find 'minwanted'",
                          metavar="UNCOVEREDUNITSFILE",
                          default=DEF_UNCOVEREDUNITSFILE)
    parser_b.set_defaults(function=select_simple)
    
    #create parser for the "select_simple_wordlimit" command:
    parser_c = subparsers.add_parser("select_simple_wordlimit",
                                     help="select_simple_wordlimit help")
    parser_c.add_argument("sourcetextfile",
                          help="input text file location (one utterance per line)",
                          metavar="SOURCETEXTFILE",
                          default=DEF_SOURCETEXTFILE)
    parser_c.add_argument("unitsfile",
                          help="input phonetized text file location (corresponds line by line to text file)",
                          metavar="UNITSFILE",
                          default=DEF_UNITSFILE)
    parser_c.add_argument("wantedunitsfile",
                          help="input text containing list of units to select for (one per line, may use 'unitfreqsfile')",
                          metavar="WANTEDUNITSFILE",
                          default=DEF_UNITFREQSFILE)
    parser_c.add_argument("minwanted",
                          help="if 'minwanted' of all wanted units have been selected, terminate selection",
                          metavar="MINWANTED",
                          type=int,
                          default=DEF_MINWANTED)
    parser_c.add_argument("wordlimit",
                          help="terminate selection when at least 'wordlimit' words have been selected",
                          metavar="WORDLIMIT",
                          type=int,
                          default=DEF_WORDLIMIT)
    parser_c.add_argument("selectedtextfile",
                          help="output selected text file location",
                          metavar="SELECTEDTEXTFILE",
                          default=DEF_SELECTEDTEXTFILE)
    parser_c.add_argument("selectedunitfreqsfile",
                          help="output text file with selected unit frequencies",
                          metavar="SELECTEDUNITFREQSFILE",
                          default=DEF_SELECTEDUNITFREQSFILE)
    parser_c.add_argument("uncoveredunitsfile",
                          help="output text file containing list of wanted units for which we could not select/find 'minwanted'",
                          metavar="UNCOVEREDUNITSFILE",
                          default=DEF_UNCOVEREDUNITSFILE)
    parser_c.set_defaults(function=select_simple_wordlimit)


    return parser


if __name__ == "__main__":
    
    cli_parser = setup_arguments()
    args = cli_parser.parse_args()
    args.function(args)

