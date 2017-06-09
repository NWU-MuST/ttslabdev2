#!/bin/env python
# -*- coding: utf-8 -*-
"""
    This module provides functionality to manipulate speech labels
    Currently supports limited functionality for reading/writing ESPS,
    HTK and Praat TextGrid formats.

    This is old code with horrible code duplication (and possibly also
    object state consistency issues)... Needs refactoring/rewriting...

    Also not using Unicode consistently...to cleanup!
"""
from __future__ import unicode_literals, division, print_function # Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys
import os

import math
import re
import copy
import codecs
from collections import defaultdict, OrderedDict
from math import sqrt
from pprint import pprint

### FUNCTONS ###
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

def float_to_htk_int(string):
    """ Converts a string representing a floating point number to an
        integer (time in 100ns units)...
    """
    return int(round(float(string)*10000000))

def htk_int_to_float(string):
    """ Converts a string representing an integer (time in 100ns units)
        to floating point value (time in seconds)...
    """
    return float(string) / 10000000.0

def triphone_2_monophone(string):
    """ Converts a triphone representation string in LC-P+RC form to
        monophone representation..
    """
    phone = string.split("+")[0]
    phone = phone.split("-")[-1]
    return phone

def type_files(filelist, ext):
    """Given a list of filenames and an extension, returns a list of
       all files with specific extension...
    """

    # If last chars (case insensitive) match "."+ext
    return [filename for filename in filelist \
            if filename.lower().endswith("." + ext.lower())]

def new_updated_dict(d1, d2):
    """ returns d1.update(d2) without mutating d1...
    """
    
    newd = dict(d1)
    newd.update(d2)
    return newd

def cdname_2_cdcategory(name, mapping):
    """ Applies a mapping to a triphone representation string in LC-P+RC form,
        returning a mapped string in the same form...
    """
    
    splitr = name.split("+")
    substr = splitr[0]
    if len(splitr) == 2:
        rc = splitr[-1]
    else:
        rc = ''
    splitl = substr.split("-")
    if len(splitl) == 2:
        lc = splitl[0]
    else:
        lc = ''
    phone = splitl[-1]

    if rc != '':
        mapped = mapping[phone] + "+" + mapping[rc]
    else:
        mapped = mapping[phone]
    if lc != '':
        mapped = mapping[lc] + "-" + mapped

    return mapped


def fixutf8(s):
    replacements = [["\\" + ss, chr(int(ss.strip("\\"), base=8))] for ss in re.findall(r"\\[0-9][0-9][0-9]", s)]
    for rep in replacements:
        s = re.sub(rep[0], rep[1], s)
    return s


### CLASSES ###

class IncompleteMapError(Exception):
    pass

class FileParseError(Exception):
    """ Exceptions related to parsing input files...
    """
    pass

class UnknownLabelfileFormatError(Exception):
    """ Thrown when file extension is not recognised...
    """
    pass

class ApplesWithPearsError(Exception):
    """ Thrown when trying to compare incompatible corpora/utterances...
    """
    pass


class Utterance(object):
    """ Maintains segments, boundaries particular to a single utterance...
    """

    LAB_EXT = "lab"
    REC_EXT = "rec"
    TEXTGRID_EXT = "TextGrid"
    PHSEQ_EXT = "phseq"
    TXT_EXT = "txt"

    SUPPORTED_EXTS = [LAB_EXT, REC_EXT, TEXTGRID_EXT, TXT_EXT]


    def __init__(self, filepath, maintier="segment"):
        """ Initialises Utterance from labels in 'filepath'...

            @type  filepath: string
            @param filepath: Path to the label file to be loaded.
        """
        
        self.filepath = filepath
        self.dirname, self.filename, self.name, self.ext = parse_path(self.filepath)
        self.segment_comparisons = {}
        self.boundary_comparisons = {}
        
        #load utterance from file appropriately...
        if self.ext.lower() == Utterance.LAB_EXT.lower():
            self.tiers, self.entries = Utterance.readLab(self.filepath)
            self._loadFromEntries()
        elif self.ext.lower() == Utterance.TEXTGRID_EXT.lower():
            self.tiers, self.entries = Utterance.readTextgrid(self.filepath, maintier=maintier)
            self._loadFromEntries()
        elif self.ext.lower() == Utterance.REC_EXT.lower():
            self._loadFromRec()
        elif self.ext.lower() == Utterance.TXT_EXT.lower():
            self.tiers, self.entries = self._read_txt(self.filepath)
            self._loadFromEntries()
        else:
            raise UnknownLabelfileFormatError("Did not recognise the extension: " + self.ext)
            
    def __len__(self):
        """Returns the number of segments...
        """
        return len(self.segments)

    def _read_txt(cls, filepath, tiername='segment'):
        with open(filepath) as infh:
            phones = infh.read().split() #whitespace delimited
        entries = [[0.0, p] for p in phones]
        tiers = {tiername: entries}
        return tiers, entries

    def readLab(cls, filepath, tiername='segment'):
        """ Read a Festival (ESPS) format label file and returns a list of entries...
        """

        entries = []
        # the digits match (regex)
        p = re.compile('[0-9]+.[0-9]+')

        with open(filepath) as fh:
            try:
                for line in fh:
                    linelist = line.split()
                    if p.match(linelist[0]):          #if the first token is a real number...
                        entries.append([linelist[0], linelist[2]])
            except IndexError:
                raise FileParseError("Could not parse file: '%s'" % (filepath))

        tiers = {tiername: entries}

        return tiers, entries
    readLab = classmethod(readLab)


    def readTextgrid(cls, filepath, maintier='segment', discard_empty=False):
        """ Read a Praat format TextGrid file and return a list of
            tiers...  Written by: Aby Louw (jalouw@csir.co.za)
        """
        
        fh = codecs.open(filepath, encoding="utf-8")
        try:
            textgridfile = fh.readlines()
        except UnicodeDecodeError:
            print(filepath)
            raise
        fh.close()
        x = len(textgridfile)
        counter = 0

        tiers = OrderedDict()
        tiername = ""
        entries = []

        expected_nintervals = {}

        # setup some regex's
        size_regex = re.compile('size = ([0-9]+)')
        name_regex = re.compile('name = \"(\w+)\"')
        intervals_regex = re.compile('intervals \[([0-9]+)\]:')
        time_regex = re.compile('xmax = ([0-9]+\.*[0-9]*)')
        text_regex = re.compile('text = \"(.*)\"')
        #text_regex = re.compile('text = \"(\S*)\"')
        #text_regex = re.compile('text = \"((\w*\s*[@]*)*)\"')
        num_intervals = re.compile('intervals: size = ([0-9]+)')
        header_end_regex = re.compile('item \[\]:')
        new_tier_regex = re.compile('item \[([0-9]+)\]:')

        header = []
        for i in range(counter,x):
            lines = textgridfile[i]
            lines = lines.strip()
            header.append(lines)

            # check for size of tiers
            m = size_regex.match(lines)
            if m:
                size = int(m.group(1))

            # header ends at "item []:"
            m = header_end_regex.match(lines)
            if m:
                counter = i + 1
                break

        running = True
        end_item = False
        end_interval = False
        end_file = False

        items = 0

        watchdog = 0

        # extract each tier
        while running:
            lines = textgridfile[counter]
            lines = lines.strip()

            watchdog += 1
            if watchdog > 1000:
                print(filepath, ":", lines)

            # test for a new tier
            m = new_tier_regex.match(lines)
            if m:
                items = int(m.group(1))

                if items == size:
                    end_item = True

                if items > size:
                    raise FileParseError("Could not parse file: '%s' \
                                          (more tiers than expected...)" \
                                             % (filepath))

                else:

                    # if we have data then add to tier variable
                    if tiername != "":
                        tiers[tiername] = entries
                        entries = []

                    # read tier header
                    counter = counter + 1
                    header_end = False
                    while not(header_end):
                        lines = textgridfile[counter]
                        lines = lines.strip()

                        # check for name of tier
                        m = name_regex.match(lines)
                        if m:
                            tiername = m.group(1)

                        # check for number of intervals in tier
                        m = num_intervals.match(lines)
                        if m:
                            n_intervals = int(m.group(1))
                            expected_nintervals[tiername] = n_intervals
                            header_end = True

                        counter = counter + 1


            # check for interval number
            m = intervals_regex.match(lines)
            if m:
                i_number = int(m.group(1))

                if i_number > n_intervals:
                    raise FileParseError("Could not parse file: '%s' \
                                          (more intervals than expected...)" \
                                             % (filepath))

                # read interval data
                counter = counter + 1
                end_interval = False
                interval = []
                while not(end_interval):
                    lines = textgridfile[counter]
                    lines = lines.strip()
                    interval.append(lines)

                    if counter == x-1:
                        end_file = True

                    # check for new interval
                    m = intervals_regex.match(lines)
                    p = new_tier_regex.match(lines)

                    if m or p:
                        end_interval = True

                    if end_interval or end_file:
                        # ok, reached end, extract data
                        #interval_data = ""
                        interval_data = "".join(interval)

                        # check for time
                        m = time_regex.search(interval_data)
                        if m:
                            time = m.group(1)

                        # check for text
                        m = text_regex.search(interval_data)
                        if m:
                            text = m.group(1)
                            text = text.strip()
                            if not discard_empty:
                                entries.append([time,text])
                            else:
                                if text != "":
                                    entries.append([time,text])

                            if end_file:
                                running = False
                                tiers[tiername] = entries
                        break
                    else:
                        counter = counter + 1

            

        counter = counter + 1
        if end_interval and end_item:
            running = False

        for tiername in tiers:
            if len(tiers[tiername]) != expected_nintervals[tiername]:
                print("WARNING: some intervals in '%s' tier were discarded..." % (tiername))

        return tiers, tiers[maintier]
    readTextgrid = classmethod(readTextgrid)


    def readRec(cls, filepath):
        """ This method reads information from an HTK style label file
            (Output from HVite with '-o N -f -m' switches) into simple
            'entries' and 'tiers' structures (to be used when using
            'Utterance' for simple format conversion...

            e.g. of format:
                0 50000 s2 -60.699875 SIL -56.921608 SILENCE
                50000 11650000 s4 -56.905319
                11650000 12350000 s2 -72.028297 j+a -57.982513 ya
                12350000 13250000 s3 -47.886478
                13250000 13500000 s4 -55.000084
                13500000 14000000 s2 -55.834679 j-a -53.787731
                14000000 14600000 s3 -49.196854
                14600000 14650000 s4 -88.408783
                14650000 14800000 s2 -88.622017 r+e -88.647713 re
                14800000 15150000 s3 -94.026115
                15150000 15300000 s4 -76.123833
                15300000 15400000 s2 -65.198868 r-e -64.968521
                15400000 16050000 s3 -62.706352
                16050000 16200000 s4 -74.617661
        """

        with open(filepath) as infh:
            recfile = infh.readlines()

        states = []
        segments = []
        words = []

        endpos = 0

        currentword = ""
        currentsegment = ""


        for line in recfile:
            #parse
            line = fixutf8(line)
            linelist = line.split()

            # #check time continuity...
            # startpos = int(linelist[0])
            # if startpos != endpos:                 #DEMITASSE: Eish (autofix off by 1)!
            #     print(startpos - endpos)
            #     if (startpos + 1) == endpos:
            #         startpos += 1
            #     elif (startpos - 1) == endpos:
            #         startpos -= 1
            #     else:
            #         raise FileParseError("discontinuity in times in file '%s'." % (self.filepath))

            #     endpos = int(linelist[1])
            # else:
            startpos = int(linelist[0])
            endpos = int(linelist[1])

            if len(linelist) == 7:    #new word, segment, state...
                if currentword != "":
                    words.append([str(htk_int_to_float(startpos)), currentword])
                if currentsegment != "":
                    segments.append([str(htk_int_to_float(startpos)), currentsegment])
                    #print(currentsegment)

                currentword = unicode(linelist[6], "utf-8")
                currentsegment = unicode(linelist[4], "utf-8")
                states.append([str(htk_int_to_float(endpos)), "_".join([currentsegment, linelist[2]])])

            elif len(linelist) == 6:  #new segment, state...
                if currentsegment != "":
                    segments.append([str(htk_int_to_float(startpos)), currentsegment])
                    #print(currentsegment)

                currentsegment = unicode(linelist[4], "utf-8")
                states.append([str(htk_int_to_float(endpos)), "_".join([currentsegment, linelist[2]])])

            elif len(linelist) == 4:  #new state...
                states.append([str(htk_int_to_float(endpos)), "_".join([currentsegment, linelist[2]])])

            else:
                raise FileParseError("cannot parse line:\n\t%s\nin file '%s'." % (line, filepath))

            if line is recfile[-1]:
                words.append([str(htk_int_to_float(endpos)), currentword])
                segments.append([str(htk_int_to_float(endpos)), currentsegment])
                #print(currentsegment)


        tiers = OrderedDict({"state" : states, "segment" : segments, "word" : words})

        return tiers, segments
    readRec = classmethod(readRec)


    def _loadFromEntries(self):
        """ This method uses information in self.entries to setup basic required (non-optional)
            structures (i.e. 'self.segments' and 'self.boundaries')...

            TODO: later this function should instead use all segments in 'self.tiers', currently
            this is unimplemented...
        """
        
        self.segments = []
        self.boundaries = []

        currentpos = 0.0
        for i in range(len(self.entries)):
            # get all segment info...
            segname = self.entries[i][1]
            segstarttime = float_to_htk_int(currentpos)
            segstoptime = float_to_htk_int(self.entries[i][0])
            segduration = segstoptime - segstarttime
            #make cdname...
            segcdname = segname
            if i != 0:
                segcdname = self.entries[i-1][1] + "-" + segcdname
            try:
                segcdname = segcdname + "+" + self.entries[i+1][1]
            except:
                pass
            #append segment info...
            self.segments.append({"name" : segname,
                                  "starttime" : segstarttime,
                                  "stoptime" : segstoptime,
                                  "duration" : segduration,
                                  "cdname" : segcdname})

            if i < len(self.entries) - 1:
                # get all boundary info...
                boundname = self.entries[i][1]+"_"+self.entries[i+1][1]
                boundtime = float_to_htk_int(self.entries[i][0])
                #append boundary info
                self.boundaries.append({"name" : boundname,
                                        "time" : boundtime})

            currentpos = float(self.entries[i][0])
    


    def _loadFromRec(self):
        """ This method uses information from an HTK style label file
            (Output from HVite with '-o N -f -m' switches) to setup basic
            structures (i.e. 'self.segments' and 'self.boundaries' and now
            also 'self.states' and 'self.words')...

            e.g. of format:
                0 50000 s2 -60.699875 SIL -56.921608 SILENCE
                50000 11650000 s4 -56.905319
                11650000 12350000 s2 -72.028297 j+a -57.982513 ya
                12350000 13250000 s3 -47.886478
                13250000 13500000 s4 -55.000084
                13500000 14000000 s2 -55.834679 j-a -53.787731
                14000000 14600000 s3 -49.196854
                14600000 14650000 s4 -88.408783
                14650000 14800000 s2 -88.622017 r+e -88.647713 re
                14800000 15150000 s3 -94.026115
                15150000 15300000 s4 -76.123833
                15300000 15400000 s2 -65.198868 r-e -64.968521
                15400000 16050000 s3 -62.706352
                16050000 16200000 s4 -74.617661
        """

        self.entries = []
        self.segments = []
        self.boundaries = []
        self.states = []
        self.words = []

        with open(self.filepath) as infh:
            recfile = infh.readlines()

        endpos = 0
        currentword = ""
        currentwordstarttime = 0
        previoussegment = ""
        currentsegment = ""
        currentsegmentscore = 0.0
        currentsegmentstarttime = 0


        for i, line in enumerate(recfile):
            line = fixutf8(line)
            #parse
            linelist = line.split()

            # #check time continuity...
            # startpos = int(linelist[0])
            # if startpos != endpos:                 #DEMITASSE: Eish!
            #     print(startpos - endpos)
            #     if (startpos + 1) == endpos:
            #         startpos += 1
            #     elif (startpos - 1) == endpos:
            #         startpos -= 1
            #     else:
            #         raise FileParseError("discontinuity in times in file '%s' at line: %s" % (self.filepath, i+1))

            #     endpos = int(linelist[1])
            # else:
            startpos = int(linelist[0])
            endpos = int(linelist[1])

            if len(linelist) == 7:    #new word, segment, state...
                if currentword != "":
                    self.words.append({"name" : currentword,
                                       "starttime" : currentwordstarttime,
                                       "stoptime" : startpos,
                                       "duration" : startpos - currentwordstarttime})

                if currentsegment != "":
                    segcdname = triphone_2_monophone(currentsegment)
                    if previoussegment: segcdname = triphone_2_monophone(previoussegment) + "-" + segcdname
                    segcdname = segcdname + "+" + triphone_2_monophone(linelist[4])
                    self.segments.append({"name" : triphone_2_monophone(currentsegment),
                                          "cdname" : segcdname,
                                          "modelname" : currentsegment,
                                          "starttime" : currentsegmentstarttime,
                                          "stoptime" : startpos,
                                          "duration" : startpos - currentsegmentstarttime,
                                          "score" : currentsegmentscore,
                                          "states" : currentstates})

                    self.boundaries.append({"name" : triphone_2_monophone(currentsegment) + "_" + \
                                                     triphone_2_monophone(linelist[4]),
                                            "time" : startpos,
                                            "simplescore" : (currentsegmentscore + float(linelist[5])) / 2.0})

                currentword = unicode(linelist[6], "utf-8")
                currentwordstarttime = startpos
                previoussegment = currentsegment
                currentsegment = unicode(linelist[4], "utf-8")
                currentsegmentscore = float(linelist[5])
                currentsegmentstarttime = startpos
                currentstates = []
                #print(linelist)
                #print(len(self.segments))
                currentstates.append({"name" : "_".join([currentsegment, linelist[2]]),
                                      "starttime" : startpos,
                                      "stoptime" : endpos,
                                      "duration" : endpos - startpos,
                                      "score" : float(linelist[3])})

            elif len(linelist) == 6:  #new segment, state...
                if currentsegment != "":
                    segcdname = triphone_2_monophone(currentsegment)
                    if previoussegment: segcdname = triphone_2_monophone(previoussegment) + "-" + segcdname
                    segcdname = segcdname + "+" + triphone_2_monophone(linelist[4])
                    self.segments.append({"name" : triphone_2_monophone(currentsegment),
                                          "modelname" : currentsegment,
                                          "starttime" : currentsegmentstarttime,
                                          "stoptime" : startpos,
                                          "duration" : startpos - currentsegmentstarttime,
                                          "score" : currentsegmentscore,
                                          "states" : currentstates})
                    
                    self.boundaries.append({"name" : triphone_2_monophone(currentsegment) + "_" + \
                                                triphone_2_monophone(linelist[4]),
                                            "time" : startpos,
                                            "simplescore" : (currentsegmentscore + float(linelist[5])) / 2.0})


                previoussegment = currentsegment
                currentsegment = linelist[4]
                currentsegmentscore = float(linelist[5])
                currentsegmentstarttime = startpos
                currentstates = []

                currentstates.append({"name" : "_".join([currentsegment, linelist[2]]),
                                      "starttime" : startpos,
                                      "stoptime" : endpos,
                                      "duration" : endpos - startpos,
                                      "score" : float(linelist[3])})

            elif len(linelist) == 4:  #new state...
                currentstates.append({"name" : "_".join([currentsegment, linelist[2]]),
                                      "starttime" : startpos,
                                      "stoptime" : endpos,
                                      "duration" : endpos - startpos,
                                      "score" : float(linelist[3])})

            else:
                raise FileParseError("cannot parse line:\n\t%s\nin file '%s'." % (line, self.filepath))

            if line is recfile[-1]:
                self.words.append({"name" : currentword,
                                   "starttime" : currentwordstarttime,
                                   "stoptime" : endpos,
                                   "duration" : endpos - currentwordstarttime})
                segcdname = triphone_2_monophone(currentsegment)
                segcdname = triphone_2_monophone(previoussegment) + "-" + segcdname
                self.segments.append({"name" : triphone_2_monophone(currentsegment),
                                      "cdname" : segcdname,
                                      "modelname" : currentsegment,
                                      "starttime" : currentsegmentstarttime,
                                      "stoptime" : endpos,
                                      "duration" : endpos - currentsegmentstarttime,
                                      "score" : currentsegmentscore,
                                      "states": currentstates})

        self.tiers, self.entries = Utterance.readRec(self.filepath)
    
    
    def saveLab(self, filepath=None):
        """ Save local segment data to a Festival format (ESPS)
            label file.
            Author: Aby Louw (jalouw@csir.co.za)
        """

        entries = self.entries

        if filepath is None:
            fh = open(self.name + "." + Utterance.LAB_EXT, "w")
        else:
            fh = open(filepath, "w")

        # write header
        string = 'signal ' + self.name + '\n'
        fh.writelines(string.encode("utf-8"))

        string = 'nfields 1\n'
        fh.writelines(string.encode("utf-8"))

        string = '#\n'
        fh.writelines(string.encode("utf-8"))

        # now write the data
        x = len(entries)

        for i in range(0,x):
            string = "\t%f\t100\t%s\n" %(float(entries[i][0]),entries[i][1])
            fh.writelines(string.encode("utf-8"))

        fh.close()

    def saveTextgrid(self, filepath=None):
        """ Save local segment data to a Praat TextGrid format
            label file.
            Author: Aby Louw (jalouw@csir.co.za)
        """
        
        tiers = self.tiers
    
        if filepath is None:
            f = open(self.name + "." + Utterance.TEXTGRID_EXT, "w")
        else:
            f = open(filepath, "w")

        # header first
        string = "File type = \"ooTextFile\"\n"
        f.writelines(string.encode("utf-8"))

        string = "Object class = \"TextGrid\"\n\n"
        f.writelines(string.encode("utf-8"))


        string = "xmin = 0\n"
        f.writelines(string.encode("utf-8"))

        xmax = 0

        # loop through tiers and look for max x
        for k, v in tiers.items():
            entries = v
            x = len(entries)
            if xmax < float(entries[x-1][0]):
                xmax = float(entries[x-1][0])

        string = "xmax = %f\n" % (xmax,)
        f.writelines(string.encode("utf-8"))

        string = "tiers? <exists>\n"
        f.writelines(string.encode("utf-8"))

        # check tier size
        size = len(tiers)
        string = "size = %d\n" %(size,)
        f.writelines(string.encode("utf-8"))

        string = "item []:\n"
        f.writelines(string.encode("utf-8"))


        tierkeys = list(tiers.keys())
#        tierkeys.sort()

        # # if "segment" exists, then write it first
        # if "segment" in tierkeys:
        #     tierkeys.remove("segment")
        #     tierkeys.insert(0,"segment")


        # loop through tiers and write to file
        items = 0
        for i in tierkeys:
            items = items + 1

            # item header
            string = "\titem [%d]:\n" % (items,)
            f.writelines(string.encode("utf-8"))

            string = "\t\tclass = \"IntervalTier\"\n"
            f.writelines(string.encode("utf-8"))

            string = "\t\tname = \"%s\"\n" % (i,)
            f.writelines(string.encode("utf-8"))

            string = "\t\txmin = 0\n"
            f.writelines(string.encode("utf-8"))

            entries = tiers[i]
            x = len(entries)

            xmax = float(entries[x-1][0])
            string = "\t\txmax = %f\n" % (xmax,)
            f.writelines(string.encode("utf-8"))

            string = "\t\tintervals: size = %d\n" % (x,)
            f.writelines(string.encode("utf-8"))

            prev_x = 0

            # now for the entries
            for c in range(0,x):
                string = "\t\tintervals [%d]:\n" % (c+1,)
                f.writelines(string.encode("utf-8"))

                string = "\t\t\txmin = %f\n" % (prev_x,)
                f.writelines(string.encode("utf-8"))

                xmax = float(entries[c][0])
                string = "\t\t\txmax = %f\n" % (xmax,)
                f.writelines(string.encode("utf-8"))

                string = "\t\t\ttext = \"%s\"\n" % (entries[c][1])
                f.writelines(string.encode("utf-8"))

                prev_x = xmax


        f.close()


    def dumpPhoneSequence(self, delim="\n", destdir=None, destfilename=None):
        """ Dump phone sequence to a text file (phones delimited by "delim")...
        """

        if destdir is None:
            destdir = self.dirname
        if destfilename is None:
            destfilename = self.name + "." + Utterance.PHSEQ_EXT

        outstr = delim.join([entry[1] for entry in self.entries])

        with open(os.path.join(destdir, destfilename), "w") as outfh:
            outfh.write(outstr)
    

    def writeTextgrid(cls, filepath, tiers):
        """ Write segment data in 'tiers' to a Praat TextGrid format
            label file.
            Author: Aby Louw (jalouw@csir.co.za)
        """
        
        f = open(filepath, "w")

        # header first
        string = "File type = \"ooTextFile\"\n"
        f.writelines(string.encode("utf-8"))

        string = "Object class = \"TextGrid\"\n\n"
        f.writelines(string.encode("utf-8"))


        string = "xmin = 0\n"
        f.writelines(string.encode("utf-8"))

        xmax = 0

        # loop through tiers and look for max x
        for k, v in tiers.items():
            entries = v
            x = len(entries)
            if xmax < float(entries[x-1][0]):
                xmax = float(entries[x-1][0])

        string = "xmax = %f\n" % (xmax,)
        f.writelines(string.encode("utf-8"))

        string = "tiers? <exists>\n"
        f.writelines(string.encode("utf-8"))

        # check tier size
        size = len(tiers)
        string = "size = %d\n" %(size,)
        f.writelines(string.encode("utf-8"))

        string = "item []:\n"
        f.writelines(string.encode("utf-8"))


        tierkeys = list(tiers.keys())
#        tierkeys.sort()

        # # if "segment" exists, then write it first
        # if "segment" in tierkeys:
        #     tierkeys.remove("segment")
        #     tierkeys.insert(0,"segment")


        # loop through tiers and write to file
        items = 0
        for i in tierkeys:
            items = items + 1

            # item header
            string = "\titem [%d]:\n" % (items,)
            f.writelines(string.encode("utf-8"))

            string = "\t\tclass = \"IntervalTier\"\n"
            f.writelines(string.encode("utf-8"))

            string = "\t\tname = \"%s\"\n" % (i,)
            f.writelines(string.encode("utf-8"))

            string = "\t\txmin = 0\n"
            f.writelines(string.encode("utf-8"))

            entries = tiers[i]
            x = len(entries)

            xmax = float(entries[x-1][0])
            string = "\t\txmax = %f\n" % (xmax,)
            f.writelines(string.encode("utf-8"))

            string = "\t\tintervals: size = %d\n" % (x,)
            f.writelines(string.encode("utf-8"))

            prev_x = 0

            # now for the entries
            for c in range(0,x):
                string = "\t\tintervals [%d]:\n" % (c+1,)
                f.writelines(string.encode("utf-8"))

                string = "\t\t\txmin = %f\n" % (prev_x,)
                f.writelines(string.encode("utf-8"))

                xmax = float(entries[c][0])
                string = "\t\t\txmax = %f\n" % (xmax,)
                f.writelines(string.encode("utf-8"))

                string = "\t\t\ttext = \"%s\"\n" % (entries[c][1])
                f.writelines(string.encode("utf-8"))

                prev_x = xmax


        f.close()
    writeTextgrid = classmethod(writeTextgrid)
        
    def writeLab(cls, filepath, entries):
        """ Write segment data in 'entries' to a Festival format (ESPS)
            label file.
            Author: Aby Louw (jalouw@csir.co.za)
        """
        fh = open(filepath, "w")

        # write header
        string = '#\n'
        fh.writelines(string.encode("utf-8"))

        # now write the data
        x = len(entries)

        for i in range(0,x):
            string = "\t%f\t100\t%s\n" %(float(entries[i][0]), entries[i][1])
            fh.writelines(string.encode("utf-8"))

        fh.close()
    writeLab = classmethod(writeLab)
        
                            
    def compareWith(self, utterance, name="default"):
        """ Facilitates comparison of self with another utterance...
        """
        
        if Utterance.isComparable(self, utterance):
            seg_ovrs = Utterance.segmentOVRs(self, utterance)
            bound_diffs = Utterance.boundaryDifferences(self, utterance)
        
            self.segment_comparisons[name] = [{"ovr" : x} for x in seg_ovrs]
            self.boundary_comparisons[name] = [{"timediff" : x} for x in bound_diffs]
        else:
            raise ApplesWithPearsError("Utterances are not comparable...")

    def isComparable(cls, utt_a, utt_b):
        """ Determines whether two utterances can be compared...
        """
        #check segments
        if len(utt_a.segments) != len(utt_b.segments):
            print("Number of segments differ between: '%s' and '%s'" \
                  % (utt_a.name, utt_b.name))
            return False
        else:
            for seg_a, seg_b in zip(utt_a.segments, utt_b.segments):
                if seg_a["name"] != seg_b["name"]:
                    print("Segments differ in: '%s' and '%s'" \
                          % (utt_a.name, utt_b.name))
                    return False
        #check boundaries
        if len(utt_a.boundaries) != len(utt_b.boundaries):
            print("Number of boundaries differ between: '%s' and '%s'" \
                  % (utt_a.name, utt_b.name))
            return False
        else:
            for bound_a, bound_b in zip(utt_a.boundaries, utt_b.boundaries):
                if bound_a["name"] != bound_b["name"]:
                    print("Boundaries differ in: '%s' and '%s'" \
                          % (utt_a.name, utt_b.name))
                    return False

        return True
    isComparable = classmethod(isComparable)


    def segmentOVRs(cls, utt_a, utt_b):
        """ returns a list of OVRs...
        """

        ovrs = []

        for seg_a, seg_b in zip(utt_a.segments, utt_b.segments):
            maxstartval = 0
            minstopval = 0
            if seg_a["starttime"] > seg_b["starttime"]:
                maxstartval = seg_a["starttime"]
            else:
                maxstartval = seg_b["starttime"]
            if seg_a["stoptime"] < seg_b["stoptime"]:
                minstopval = seg_a["stoptime"]
            else:
                minstopval = seg_b["stoptime"]

            common_duration = minstopval - maxstartval
            if common_duration < 0: common_duration = 0
            
            try:
                ovr = float(common_duration) / float(seg_a["duration"] + seg_b["duration"] - common_duration) * 100.0
            except ZeroDivisionError:
                print("WARNING: Zero duration detected in '%s/%s'" % (utt_a.name, utt_b.name))
                ovr = 0.0
            ovrs.append(ovr)
        
        return ovrs
    segmentOVRs = classmethod(segmentOVRs)


    def boundaryDifferences(cls, base_utt, ref_utt):
        """ returns list of differences in time...
            Negative differences signify that the 'base_utt' boundary
            occurred before the 'ref_utt' boundary...
        """

        return [x[0] - x[1] for x in list(zip([x["time"] for x in base_utt.boundaries],
                                              [x["time"] for x in ref_utt.boundaries]))]
    boundaryDifferences = classmethod(boundaryDifferences)
        
    def getSegmentsWithComparison(self, refname=None):
        """ Return segments information with comparison fields appended...
        """
        
        if len(self.segment_comparisons) == 0:
            #print "No comparisons have been made..."
            return copy.deepcopy(self.segments)

        if refname is None:
            refname = list(self.segment_comparisons.keys())[0]
            #print "using comparison with: '%s' corpus" % (refname)

        return [new_updated_dict(x[0], x[1]) for x in list(zip(self.segments,
                       self.segment_comparisons[refname]))]

    def getBoundariesWithComparison(self, refname=None):
        """ Return boundaries information with comparison fields appended...
        """
        
        if len(self.boundary_comparisons) == 0:
            #print "No comparisons have been made..."
            return copy.deepcopy(self.boundaries)

        if refname is None:
            refname = list(self.boundary_comparisons.keys())[0]
            #print "using comparison with: '%s' corpus" % (refname)
            
        return [new_updated_dict(x[0], x[1]) for x in list(zip(self.boundaries,
                       self.boundary_comparisons[refname]))]


class Corpus(object):
    """ Manages sets of Utterances...
    """

    def __init__(self, dirpath, name=None, maintier="segment"):
        """ Initialises a Corpus (set of Utterances) from a path containing
            files representing Utterances...
        """
        
        if name is not None:
            self.name = name
        else:
            self.name = dirpath
        self.dirpath = dirpath
        self.utterances = []
        self.segment_frequencies = defaultdict(int)
        self.comparisons = {}
        self.mappings = {}

        self.wavpath = None
        self.dictionarylocation = None
        self.pronunconflicts = None
        self.pronunaddendum = None

        self._loadUtterances(maintier=maintier)


    def __len__(self):
        """ This returns the number of utterances...
        """
        return len(self.utterances)

    def __iter__(self):
        return self.utterances.__iter__()


    def _loadUtterances(self, maintier="segment"):
        """ Scans 'self.dirpath' and loads all supported files in order to
            initialise 'self.utterances' and 'self.segment_frequencies'...
        """

        filenames = []
        try:
            for ext in Utterance.SUPPORTED_EXTS:
                filenames.extend(type_files(os.listdir(self.dirpath), ext))
        except OSError:
            raise

        filenames.sort()   # Essential (when we test comparability...)
        
        for filename in filenames:
            sys.stdout.write("Loading: " + filename + "\r")
            self.utterances.append(Utterance(os.path.join(self.dirpath, filename), maintier=maintier))
        sys.stdout.write("\nDONE!\n")

        for utt in self.utterances:
            segmentlist = utt.segments
            for segment in segmentlist:
                self.segment_frequencies[segment["name"]] += 1

    def addMapping(self, filepath, name=None):
        """ Loads a simple text file with segment name mappings...
        """

        if name is None:
            dn, fn, n, e = parse_path(filepath)
            name = fn

        cat_dict = {}
        
        with open(filepath) as fh:
            for line in fh:
                if not line.startswith("#"):                 #DEMITASSE....
                    linelist = line.split()
                    try:
                        cat_dict[linelist[0]] = linelist[1]
                    except IndexError:
                        pass
        
        for key in self.segment_frequencies:
            if key not in cat_dict:
                raise IncompleteMapError("Mapping does not cover all segments... (%s)" % (key))
            else:
                self.mappings[name] = cat_dict


    def isComparable(cls, corpus_a, corpus_b):
        """ Determines whether two corpora can be compared...
        """
        
        if len(corpus_a) != len(corpus_b):
            print("Number of utterances differ...")
            return False
        else:
            for utt_a, utt_b in zip(corpus_a.utterances, corpus_b.utterances):
                if not Utterance.isComparable(utt_a, utt_b):
                    return False
        return True       
    isComparable = classmethod(isComparable)


    def compareWith(self, corpus):
        """ Facilitates comparison of self with another corpus...
        """
        
        if Corpus.isComparable(self, corpus):
            #do comparison....
            if corpus.name is not None:
                self.comparisons[corpus.name] = corpus
            else:
                self.comparisons[corpus.dirpath] = corpus
            
            for base_utt, ref_utt in zip(self.utterances, corpus.utterances):
                base_utt.compareWith(ref_utt, name=corpus.name)
                
            
        else:
            raise ApplesWithPearsError("Corpora are not comparable...")

    def boundaryRMSE(self, refname=None):
        """ calculate the boundary RMSE...
        """

        if len(self.comparisons) == 0:
            print("No comparisons have been made (use compareWith() method first)...")
            return

        if refname is None:
            refname = list(self.comparisons.keys())[0]
            #print "using comparison with: '%s' corpus" % (refname)

        SE_sum = 0.0
        count = 0
        for utt in self.utterances:
            diffs = [x["timediff"] for x in utt.boundary_comparisons[refname]]
            fdiffs = [htk_int_to_float(x) for x in diffs]
            SE_sum += sum([x**2 for x in fdiffs])
            count += len(fdiffs)

        return sqrt(SE_sum / count)

    def boundaryAccuracy(self, threshold=0.020, refname=None):  #threshold in seconds...
        """ calculates the boundary accuracy (i.e. percentage of 'correct' boundaries
            (i.e. boundaries that fall within threshold of reference boundary))...
        """

        if len(self.comparisons) == 0:
            print("No comparisons have been made (use compareWith() method first)...")
            return

        if refname is None:
            refname = list(self.comparisons.keys())[0]
            #print "using comparison with: '%s' corpus" % (refname)

        correct_count = 0
        count = 0

        for utt in self.utterances:
            diffs = [x["timediff"] for x in utt.boundary_comparisons[refname]]
            fdiffs = [htk_int_to_float(x) for x in diffs]
            correct_count += sum([int(abs(x) < threshold) for x in fdiffs])
            count += len(fdiffs)

        return float(correct_count) / float(count) * 100.0
        
    def meanOVR(self, refname=None):
        """ calculate the average segment OVR...
        """

        if len(self.comparisons) == 0:
            print("No comparisons have been made (use compareWith() method first)...")
            return

        if refname is None:
            refname = list(self.comparisons.keys())[0]
            #print "using comparison with: '%s' corpus" % (refname)

        OVR_sum = 0.0
        count = 0
        for utt in self.utterances:
           ovrs = map(lambda x: x["ovr"], utt.segment_comparisons[refname])
           OVR_sum += sum(ovrs)
           count += len(ovrs)
           
        return OVR_sum / count

        # allOVRs = []
        # for utt in self.utterances:
        #     allOVRs.extend([x["ovr"] for x in utt.segment_comparisons[refname]])
        
        # return numpy.mean(allOVRs), numpy.std(allOVRs)
    
    def getFullUttSegmentInfo(self, num, refname=None, mapname=None):
        """ Return as much info as possible about 'self.utterances[num].segments'...
        """

        segments = self.utterances[num].getSegmentsWithComparison(refname)
        
        if len(self.mappings) == 0:
            #print "No mappings have been loaded..."
            return segments

        if mapname is None:
            mapname = list(self.mappings.keys())[0]
            #print "using mapping: '%s'" % (mapname)

        
        for segment in segments:
            segment["category"] = self.mappings[mapname][segment["name"]]
            segment["cdcategory"] = cdname_2_cdcategory(segment["cdname"], self.mappings[mapname])
            segment["uttname"] = self.utterances[num].name

        return segments


    def getFullUttBoundaryInfo(self, num, refname=None, mapname=None):
        """ Return as much info as possible about 'self.utterances[num].boundaries'...
        """
        
        boundaries = self.utterances[num].getBoundariesWithComparison(refname)

        if len(self.mappings) == 0:
            #print "No mappings have been loaded..."
            return boundaries

        if mapname is None:
            mapname = list(self.mappings.keys())[0]
            #print "using mapping: '%s'" % (mapname)

        for boundary in boundaries:
            ls, rs = boundary["name"].split("_")
            boundary["category"] = self.mappings[mapname][ls] + "_" + self.mappings[mapname][rs]
            boundary["uttname"] = self.utterances[num].name

        return boundaries
        
    
    def writeOrthographicTranscriptionFile(self, outputfilelocation, stripword=False):
        """ Write orthography in "word" tiers to 'utts.data' style transcription file
            which can be read by Festival... If stripword is True, then omit the initial
            and final word in the 'word' tier (this is often a 'SILENCE' word which is
            not needed in Festival transcription file)....
        """

        uttindex = {}
        for i, utt in enumerate(self.utterances):
            uttindex[utt.name] = i
        self.pronunaddendum = {}

        with open(outputfilelocation, "w") as outfh:
            for uttname in sorted(uttindex.keys()):
                try:
                    if stripword:
                        wordlist = [entry[1].strip().strip("\x7f") for entry in self.utterances[uttindex[uttname]].tiers["word"]][1:-1]
                    else:
                        wordlist = [entry[1].strip().strip("\x7f") for entry in self.utterances[uttindex[uttname]].tiers["word"]]
                    outfh.write('( ' + uttname + ' "%s")\n' % (" ".join(wordlist)))
                except KeyError:
                    print("WARNING: '%s' does not have 'word' tier..." % (uttname))



def test(filepath):
    """ Test stuff...
    """
    
    # Conversion without instantiation...
    ########################################
    #t, e = Utterance.readRec(filepath)
    #os.system("cp " + filepath + " hello.rec")
    #Utterance.writeTextgrid("hello.TextGrid", t)
    #Utterance.writeLab("hello.lab", e)
    
    # Instantiation and saving...
    ########################################
    #u = Utterance(filepath)
    #u.saveLab()
    #u.saveTextgrid()
    pass
    

if __name__ == "__main__":
    #test(sys.argv[1])
    pass
