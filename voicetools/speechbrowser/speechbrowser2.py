#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Quick and dirty tool to review potential transcription issues...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys
import os
import codecs
import time
import json

import pygtk
pygtk.require("2.0")
import gtk, gobject
from matplotlib.backends.backend_gtk import FigureCanvasGTK
from matplotlib.figure import Figure

import ttslab
from ttslab.hrg import Utterance
ttslab.extend(Utterance, "ufuncs_analysis")
from ttslab.waveform import Waveform


def loadworklist(fn, sep=","):
    worklist = []
    with codecs.open(fn, encoding="utf-8") as infh:
        for line in infh:
            try:
                fname, wordindex = line.strip().split(sep)
                wordindex = int(wordindex)
                worklist.append([fname, wordindex])
            except ValueError:
                pass
    return worklist

SYLBOUND_CHAR = "."
def getpronun(word, voice):
    if word["lang"] is None or word["lang"] == "main":
        langprefix = ""
        phset = voice.pronun["main"]["phoneset"]
    else:
        langprefix = word["lang"] + "_"
        phset = voice.pronun[word["lang"]]["phoneset"]
    pronun = []
    for syl in word.get_daughters():
        try:
            stress = int(syl["tone"])
        except ValueError:
            stress = 0
        for ph in syl.get_daughters():
            pronun.append(phset.map[ph["name"][len(langprefix):]])
            if phset.is_vowel(ph["name"][len(langprefix):]) and stress in [1, 2]:
                pronun.append(str(stress))
        pronun.append(SYLBOUND_CHAR)
    pronun.pop()
    return pronun


class CorpusView(object):
    def __init__(self, worklist, voice, previous):
        self.transcriptions, self.pronuns, self.comments = previous
        self.voice = voice
        self.worklist = worklist
        self.current_index = 0
        self.current_wordindex = self.worklist[self.current_index][1]
        self.current_utt = ttslab.fromfile(self.worklist[self.current_index][0])
        self.current_utt.fill_startendtimes()
        #SET STATE:
        if self.worklist[self.current_index][0] not in self.transcriptions:
            self.transcriptions[self.worklist[self.current_index][0]] = self.current_utt["inputtext"]
        if self.worklist[self.current_index][0] not in self.comments:
            self.comments[self.worklist[self.current_index][0]] = ""
        if self.worklist[self.current_index][0] not in self.pronuns:
            self.pronuns[self.worklist[self.current_index][0]] = [" ".join(getpronun(w, self.voice)) for w in self.current_utt.gr("SylStructure")]
        
    def save_data(self):
        with codecs.open("ttslab_speechbrowser_" + time.strftime("%Y%m%d%H%M%S", time.localtime(time.time())) + ".json", "w", encoding="utf-8") as outfh:
            json.dump([self.transcriptions, self.pronuns, self.comments], outfh, encoding="utf-8", ensure_ascii=False, indent=4, sort_keys=True)

    def next(self):
        self.save_data()
        if self.current_index < len(self.worklist) - 1:
            self.current_index += 1
            self.current_wordindex = self.worklist[self.current_index][1]
            self.current_utt = ttslab.fromfile(self.worklist[self.current_index][0])
            self.current_utt.fill_startendtimes()
            if self.worklist[self.current_index][0] not in self.transcriptions:
                self.transcriptions[self.worklist[self.current_index][0]] = self.current_utt["inputtext"]
            if self.worklist[self.current_index][0] not in self.comments:
                self.comments[self.worklist[self.current_index][0]] = ""
            if self.worklist[self.current_index][0] not in self.pronuns:
                self.pronuns[self.worklist[self.current_index][0]] = [" ".join(getpronun(w, self.voice)) for w in self.current_utt.gr("SylStructure")]

    def prev(self):
        self.save_data()
        if self.current_index > 0:
            self.current_index -= 1
            self.current_wordindex = self.worklist[self.current_index][1]
            self.current_utt = ttslab.fromfile(self.worklist[self.current_index][0])
            self.current_utt.fill_startendtimes()


class SpeechbrowserApp(object):       
    def __init__(self, voice, corpusview):
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(os.path.dirname(__file__), "speechbrowser.glade"))
        builder.connect_signals({"on_window1_destroy": gtk.main_quit,
                                 "on_toolbutton_open_clicked": self.on_toolbutton_open_clicked,
                                 "on_button_playutt_clicked": self.on_button_playutt_clicked,
                                 "on_button_playwordorig_clicked": self.on_button_playwordorig_clicked,
                                 "on_button_playwordsynth_clicked": self.on_button_playwordsynth_clicked,
                                 "on_button_next_clicked": self.on_button_next_clicked,
                                 "on_button_prev_clicked": self.on_button_prev_clicked})
        self.window1 = builder.get_object("window1")
        self.frame_specutt = builder.get_object("frame_specutt")
        self.button_playutt = builder.get_object("button_playutt")
        self.frame_words = builder.get_object("frame_words")
        self.entry_transcription = builder.get_object("entry_transcription")
        self.table_utt = builder.get_object("table_utt")
        self.table_words = builder.get_object("table_words")
        self.frame_wordspecorig = builder.get_object("frame_wordspecorig")
        self.frame_wordspecsynth = builder.get_object("frame_wordspecsynth")
        self.button_playwordorig = builder.get_object("button_playwordorig")
        self.button_playwordsynth = builder.get_object("button_playwordsynth")
        self.label_word1 = builder.get_object("label_word1")
        self.label_word2 = builder.get_object("label_word2")
        self.label_word3 = builder.get_object("label_word3")
        self.entry_word1 = builder.get_object("entry_word1")
        self.entry_word2 = builder.get_object("entry_word2")
        self.entry_word3 = builder.get_object("entry_word3")
        self.statusbar = builder.get_object("statusbar")
        self.entry_comment = builder.get_object("entry_comment")
        # self.combobox_comment = builder.get_object("combobox_comment")
        # liststore = gtk.ListStore(gobject.TYPE_STRING)
        # self.combobox_comment.set_model(liststore)
        # self.combobox_comment.set_entry_text_column(0)
        # self.combobox_comment.append_text("transcription error")
        # self.combobox_comment.append_text("pronunciation error")
        # self.combobox_comment.append_text("noise present")
        # self.combobox_comment.append_text("no problem")
        # cell = gtk.CellRendererText()
        # self.combobox_comment.pack_start(cell, True)
        # self.combobox_comment.add_attribute(cell, 'text', 1)

        self.window1.show()

        self.voice = voice
        self.corpusview = corpusview
        self.update_uttview()
        self.update_wordview()


    def update_wordview(self):
        u = self.corpusview.current_utt
        words = u.get_relation("SylStructure").as_list()
        word = words[self.corpusview.current_wordindex]
        try:
            prevword = word.prev_item
            prevwordname = prevword["name"]
            origstartsample = u["waveform"].samplerate * prevword["start"]
            synthstartsample = u["lindists"]["utt"]["waveform"].samplerate * prevword["start"]
            prevwordpronun = self.corpusview.pronuns[self.corpusview.worklist[self.corpusview.current_index][0]][self.corpusview.current_wordindex-1]
        except TypeError:
            prevwordname = "NONE"
            origstartsample = 0
            synthstartsample = 0
            prevwordpronun = ""
        wordname = word["name"]
        wordpronun = self.corpusview.pronuns[self.corpusview.worklist[self.corpusview.current_index][0]][self.corpusview.current_wordindex]
        try:
            nextword = word.next_item
            nextwordname = nextword["name"]
            origendsample = u["waveform"].samplerate * nextword["end"]
            synthendsample = u["lindists"]["utt"]["waveform"].samplerate * nextword["end"]
            nextwordpronun = self.corpusview.pronuns[self.corpusview.worklist[self.corpusview.current_index][0]][self.corpusview.current_wordindex+1]
        except TypeError:
            nextwordname = "NONE"
            origendsample = len(u["waveform"].samples)
            synthendsample = len(u["waveform"].samples)
            nextwordpronun = ""
            
        self.label_word1.set_label(prevwordname)
        self.label_word2.set_label(wordname)
        self.label_word3.set_label(nextwordname)

        self.entry_word1.set_text(prevwordpronun)
        self.entry_word2.set_text(wordpronun)
        self.entry_word3.set_text(nextwordpronun)

        self.origwordcontextwav = Waveform()
        self.origwordcontextwav.samplerate = u["waveform"].samplerate
        self.origwordcontextwav.samples = u["waveform"].samples[origstartsample:origendsample]
        origwordcontext_specfig = Figure(dpi=72)
        origwordcontext_specplot = origwordcontext_specfig.add_subplot(111)
        origwordcontext_specplot.specgram(self.origwordcontextwav.samples,
                                          Fs=self.origwordcontextwav.samplerate,
                                          NFFT=128, noverlap=64,
                                          xextent=(0.0, self.origwordcontextwav.samplerate*len(self.origwordcontextwav.samples)))
        origwordcontext_speccanvas = FigureCanvasGTK(origwordcontext_specfig)
        framecontents = self.frame_wordspecorig.get_children()
        if framecontents:
            self.frame_wordspecorig.remove(framecontents[0])
        self.frame_wordspecorig.add(origwordcontext_speccanvas)

        self.synthwordcontextwav = Waveform()
        self.synthwordcontextwav.samplerate = u["lindists"]["utt"]["waveform"].samplerate
        self.synthwordcontextwav.samples = u["lindists"]["utt"]["waveform"].samples[synthstartsample:synthendsample] 
        synthwordcontext_specfig = Figure(dpi=72)
        synthwordcontext_specplot = synthwordcontext_specfig.add_subplot(111)
        synthwordcontext_specplot.specgram(self.synthwordcontextwav.samples,
                                           Fs=self.synthwordcontextwav.samplerate,
                                           NFFT=128, noverlap=64,
                                           xextent=(0.0, self.synthwordcontextwav.samplerate*len(self.synthwordcontextwav.samples)))
        synthwordcontext_speccanvas = FigureCanvasGTK(synthwordcontext_specfig)
        framecontents = self.frame_wordspecsynth.get_children()
        if framecontents:
            self.frame_wordspecsynth.remove(framecontents[0])
        self.frame_wordspecsynth.add(synthwordcontext_speccanvas)
       
        self.statusbar.push(0, "Item: %s/%s (Word index: %s)" % (self.corpusview.current_index + 1, len(self.corpusview.worklist), self.corpusview.current_wordindex))
        self.table_words.show_all()


    def savepronuns(self, wordindex):
        if wordindex != 0:
            self.corpusview.pronuns[self.corpusview.worklist[self.corpusview.current_index][0]][wordindex-1] = unicode(self.entry_word1.get_text(), "utf-8")
        self.corpusview.pronuns[self.corpusview.worklist[self.corpusview.current_index][0]][wordindex] = unicode(self.entry_word2.get_text(), "utf-8")
        try:
            self.corpusview.pronuns[self.corpusview.worklist[self.corpusview.current_index][0]][wordindex+1] = unicode(self.entry_word3.get_text(), "utf-8")
        except IndexError:
            pass


    def change_wordview(self, button):
        self.savepronuns(self.corpusview.current_wordindex)
        self.corpusview.current_wordindex = button.wordindex
        self.update_wordview()

    def update_uttview(self):
        utt = self.corpusview.current_utt
        origspeech_specfig = Figure(dpi=72)
        origspeech_specplot = origspeech_specfig.add_subplot(111)
        origspeech_specplot.specgram(utt["waveform"].samples, Fs=utt["waveform"].samplerate, NFFT=128, noverlap=64)
        origspeech_speccanvas = FigureCanvasGTK(origspeech_specfig)
        framecontents = self.frame_specutt.get_children()
        if framecontents:
            self.frame_specutt.remove(framecontents[0])
        self.frame_specutt.add(origspeech_speccanvas)
        self.entry_transcription.set_text(self.corpusview.transcriptions[self.corpusview.worklist[self.corpusview.current_index][0]])
        self.entry_comment.set_text(self.corpusview.comments[self.corpusview.worklist[self.corpusview.current_index][0]])
        self.buttonbox_words = gtk.HButtonBox()
        words = utt.get_relation("Word").as_list()
        for i, word in enumerate(words):
            button = gtk.Button()
            button.wordindex = i
            button.connect("clicked", self.change_wordview)
            button.set_label(word["name"])
            self.buttonbox_words.pack_end(button)
        framecontents = self.frame_words.get_children()
        if framecontents:
            self.frame_words.remove(framecontents[0])
        self.frame_words.add(self.buttonbox_words)
        self.table_utt.show_all()
        self.update_wordview()

    def on_button_next_clicked(self, obj):
        self.corpusview.transcriptions[self.corpusview.worklist[self.corpusview.current_index][0]] = unicode(self.entry_transcription.get_text(), "utf-8")
        self.corpusview.comments[self.corpusview.worklist[self.corpusview.current_index][0]] = unicode(self.entry_comment.get_text(), "utf-8")
        self.savepronuns(self.corpusview.current_wordindex)
        self.corpusview.next()
        self.update_uttview()

    def on_button_prev_clicked(self, obj):
        self.corpusview.transcriptions[self.corpusview.worklist[self.corpusview.current_index][0]] = unicode(self.entry_transcription.get_text(), "utf-8")
        self.corpusview.comments[self.corpusview.worklist[self.corpusview.current_index][0]] = unicode(self.entry_comment.get_text(), "utf-8")
        self.savepronuns(self.corpusview.current_wordindex)
        self.corpusview.prev()
        self.update_uttview()

    def on_button_playutt_clicked(self, obj):
        self.corpusview.current_utt["waveform"].play()

    def on_button_playwordorig_clicked(self, obj):
        self.origwordcontextwav.play()

    def on_button_playwordsynth_clicked(self, obj):
        self.synthwordcontextwav.play()

    def on_toolbutton_open_clicked(self, obj):
        chooser = gtk.FileChooserDialog(title=None,
                                        action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                        buttons=(gtk.STOCK_CANCEL,
                                                 gtk.RESPONSE_CANCEL,
                                                 gtk.STOCK_OPEN,
                                                 gtk.RESPONSE_OK))
        chooser.set_current_folder(os.getcwd())
        response = chooser.run()
        if response == gtk.RESPONSE_OK:
            filename = chooser.get_filename()
            worklist = loadworklist(filename)
            self.corpusview = CorpusView(worklist, self.voice)
        elif response == gtk.RESPONSE_CANCEL:
            print('Closed, no files selected')
        chooser.destroy()
        self.update_uttview()
        self.update_wordview()

if __name__ == "__main__":
    voice = ttslab.fromfile(sys.argv[1])
    worklist = loadworklist(sys.argv[2])
    with codecs.open(sys.argv[3], encoding="utf-8") as infh:
        transcrs, pronuns, comments = json.load(infh)
    corpusview = CorpusView(worklist, voice, (transcrs, pronuns, comments))
    app = SpeechbrowserApp(voice, corpusview)
    gtk.main()
