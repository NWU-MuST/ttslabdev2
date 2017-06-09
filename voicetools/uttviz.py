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
import networkx as nx
import pylab as pl
import numpy as np
from tempfile import mkdtemp

import ttslab
from ttslab import hrg
from ttslab.trackfile import Track
ttslab.extend(hrg.Utterance, "ufuncs_analysis")
ttslab.extend(Track, "ttslab.trackfile.funcs.tfuncs_praat")


def itemrepr(item):
    if "tone" in item:
        tone = item["tone"]
        if type(tone) is str:
            return tone
        else:
            return item["name"]
    else:
        return item["name"]
setattr(hrg.Item, "__str__", itemrepr)    


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
    f0t.get_f0(os.path.join(d, "utt.wav"))
    shutil.rmtree(d)

    fig = pl.figure()#edgecolor=(0.921568627451, 0.921568627451, 0.921568627451))
    ax = fig.add_subplot(311)
    ax.set_title("Utterance")
#    ax.set_ylim(0, 5)
#    ax.set_xticks(bounds)
#    ax.grid()
    nx.draw(g, pos=posdict, ax=ax, nodelist=nodelist, node_size=nodesizelist)

    ax1 = fig.add_subplot(312)
    ax1.set_title("Pitch")
    ax1.set_ylim(20.0, 300.0)
    ax1.set_ylabel("Hertz")
    pl.plot(f0t.times, f0t.values, color='green')
    pl.xticks([syl["end"] for syl in u.gr("Syllable")], [syl["tone"] for syl in u.gr("Syllable")])
    ax1.grid()

    ax2 = fig.add_subplot(313)
    ax2.set_title("Waveform")
    ax2.set_xlim(0, uttendtime * u["waveform"].samplerate)
    pl.plot(u["waveform"].samples, color='b')
    ax2.set_xticks(bounds*u["waveform"].samplerate, [''] * len(bounds))
    fig.set_facecolor((0.921568627451, 0.921568627451, 0.921568627451))
#    ax2.grid()
#    pl.show()
    
#    fig.savefig("output.png")

    return fig


if __name__ == '__main__':

    try:
        uttfname = sys.argv[1]
    except IndexError:
        print("USAGE: uttviz.py UTTFNAME")
        sys.exit()

    utt = ttslab.fromfile(uttfname)
    g = draw_sylstruct_graph_pitch_waveform(utt)
    try:
        outfname = sys.argv[2]
        g.savefig(outfname)
    except IndexError:
        pl.show()
