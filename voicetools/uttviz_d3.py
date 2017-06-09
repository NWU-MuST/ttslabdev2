#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Visualize the syllable structure aligned to the waveform and pitch...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os
import shutil
import sys
import unicodedata

import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt, mpld3
import numpy as np
from tempfile import mkdtemp
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO #Py3
import scipy.signal as ss

import ttslab
from ttslab import hrg
from ttslab.trackfile import Track
ttslab.extend(hrg.Utterance, "ufuncs_analysis")
ttslab.extend(Track, "ttslab.trackfile.funcs.tfuncs_praat")


def itemrepr(item):
    if "tone" in item:
        tone = item["tone"].encode('ascii', 'ignore')
        name = unicodedata.normalize("NFKD", item["name"]).encode('ascii', 'ignore')
        if tone is not None and name == "syl":
            return tone
        else:
            return name
    else:
        return unicodedata.normalize("NFKD", item["name"]).encode('ascii', 'ignore')
setattr(hrg.Item, "__str__", itemrepr)    

def getsylsegstr(syl):
    syl = syl.gir("SylStructure")
    s = "".join([d["name"] for d in syl.get_daughters()])
    return s


def draw_sylstruct_graph_pitch_waveform(u):
    #use seg end times to calculate start and end times for all
    #items...
    u.fill_startendtimes()

    g = nx.Graph()

    posdict = {}
    nodelist = []
    nodesizelist = []
    for word in u.get_relation("SylStructure"):
        nodelist.append(word)
        nodesizelist.append(300*len(str(word)))
        posdict[word] = [word["end"] + word["start"] / 2, 3]
        if word.prev_item:
            g.add_edge(word.prev_item, word)
        if word.next_item:
            g.add_edge(word.next_item, word)
        g.add_edge(word.first_daughter, word)
        g.add_edge(word.last_daughter, word)
        for syl in word.get_daughters():
            nodelist.append(syl)
            nodesizelist.append(400)
            posdict[syl] = [syl["end"] + syl["start"] / 2, 2]
            if syl.prev_item:
                g.add_edge(syl.prev_item, syl)
            if syl.next_item:
                g.add_edge(syl.next_item, syl)
            g.add_edge(syl.first_daughter, syl)
            g.add_edge(syl.last_daughter, syl)
            for seg in syl.get_daughters():
                nodelist.append(seg)
                nodesizelist.append(350)
                posdict[seg] = [seg["end"] + seg["start"] / 2, 1]
                if seg.prev_item:
                    g.add_edge(seg.prev_item, seg)
                if seg.next_item:
                    g.add_edge(seg.next_item, seg)

    uttendtime = u.get_relation("Segment").tail_item["end"]
    bounds = np.array([word["end"] for word in u.get_relation("Word")])
    
    #get the pitch:
    d = mkdtemp()
    u["waveform"].write(os.path.join(d, "utt.wav"))
    f0t = Track()
    f0t.get_f0(os.path.join(d, "utt.wav"), semitones=True)
    shutil.rmtree(d)

    fig1 = plt.figure()#edgecolor=(0.921568627451, 0.921568627451, 0.921568627451))
    ax = fig1.add_subplot(111)
    ax.set_title("Utterance")
    # ax.set_ylim(0, 5)
    nx.draw(g, pos=posdict, ax=ax, nodelist=nodelist, node_size=nodesizelist)
    plt.xticks([],[])
    plt.yticks([1.0, 2.0, 3.0],["segment", "syllable", "word"])


    fig2 = plt.figure()
    ax1 = fig2.add_subplot(111)
    ax1.set_title("Pitch")
    ax1.set_ylabel("Semitones (relative to 1 Hz)")
    ax1.set_xlabel("Syllables")
    plt.plot(f0t.times, f0t.values, color='green')
    ax1.set_ylim(bottom=75.0)
    plt.xticks([syl["end"] for syl in u.gr("Syllable")], [getsylsegstr(syl) for syl in u.gr("Syllable")])
    ax1.grid()

    fig3 = plt.figure()
    ax2 = fig3.add_subplot(111)
    decimate_factor = 10
    ax2.set_title("Waveform (decimation factor: %s)" % decimate_factor)
    ax2.set_ylabel("Amplitude")
    ax2.set_xlabel("Syllables")
    waveform = ss.decimate(u["waveform"].samples, decimate_factor)
    plt.plot(np.arange(len(waveform)) * (1.0/u["waveform"].samplerate * decimate_factor), waveform, color='b')
    #ax2.set_xticks(bounds*u["waveform"].samplerate, [''] * len(bounds))
    plt.xticks([syl["end"] for syl in u.gr("Syllable")], [getsylsegstr(syl) for syl in u.gr("Syllable")])
#    fig3.set_facecolor((0.921568627451, 0.921568627451, 0.921568627451))
    ax2.grid()

    #plt.show()

    return fig1, fig2, fig3

def draw_sylstruct_graph_pitch_waveform_html(utt):
    fig1, fig2, fig3 = draw_sylstruct_graph_pitch_waveform(utt)
    output = StringIO()
    mpld3.save_html(fig1, output)
    syl_html = output.getvalue()
    output.close()
    output = StringIO()
    mpld3.save_html(fig2, output)
    pitch_html = output.getvalue()
    output.close()
    output = StringIO()
    mpld3.save_html(fig3, output)
    wave_html = output.getvalue()
    output.close()
    plt.close(fig1)
    plt.close(fig2)
    plt.close(fig3)
    return syl_html, pitch_html, wave_html


if __name__ == '__main__':

    try:
        uttfname = sys.argv[1]
    except IndexError:
        print("USAGE: uttviz_d3.py UTTFNAME")
        sys.exit()

    utt = ttslab.fromfile(uttfname)
    fig1, fig2, fig3 = draw_sylstruct_graph_pitch_waveform(utt)
    mpld3.save_html(fig1, open(os.path.basename(uttfname) + "_sylstructure.html", "w"))
    mpld3.save_html(fig2, open(os.path.basename(uttfname) + "_pitch.html", "w"))
    mpld3.save_html(fig3, open(os.path.basename(uttfname) + "_wave.html", "w"))
