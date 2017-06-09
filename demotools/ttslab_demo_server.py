#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Simple server to load voices and serve TTS requests..
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os, sys
import ConfigParser as configparser
import socket
import cPickle as pickle
import threading
import tempfile
import logging

import ttslab
import uttviz_d3 as uttviz

NAME = "ttslab_demo_server.py"
DEF_LOG = os.path.join(os.environ.get("HOME"), ".ttslab/demo_server.log")
DEF_LOGLEVEL = 20

END_OF_MESSAGE_STRING = b"<EoM>"
DEFAULT_PORT = 22223

class TTSServer(object):
    
    def __init__(self, voicename=None, lport=DEFAULT_PORT):

        self.voices = {}
        if voicename is not None:
            self.loadvoice(voicename)
        self._socksetup(lport)
        self.threads = []
        log.info("Server initialised.")

    def loadvoice(self, name, voice_location):
        log.info("Loading voice from file '%s'" % (voice_location))
        self.voices[name] = ttslab.fromfile(voice_location)
        log.info("Voice '%s' loaded." % (name))

    def getvoicelist(self):
        return self.voices.keys()

    def _socksetup(self, lport):
        self.lsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lport = lport
        self.lsocket.bind(("", self.lport))

    def run(self):
        while True:
            try:
                log.info("Waiting for connections...")
                self.lsocket.listen(5)
                c = TTSHandler(self.lsocket.accept(), self) 
                c.start() 
                self.threads.append(c)
                # print(self.threads)
            except KeyboardInterrupt:
                log.info("received SIGINT, shutting down...")
                break
        self.lsocket.close()
        for c in self.threads: 
            c.join()
        
    def synth(self, requestmsg):
        log.info("Synthesis request: %s" % requestmsg)
        try:
            utt = self.voices[requestmsg["voicename"]].synthesize(requestmsg["text"], "text-to-wave")
            #dump to files and read blobs (don't want dependencies on webserver)
            #wav:
            wavfd, wavfn = tempfile.mkstemp(suffix=".wav")
            utt["waveform"].write(wavfn)
            os.close(wavfd)
            wavf = open(wavfn, "rb")
            wavblob = wavf.read()
            wavf.close()
            os.remove(wavfn)
            #graphs:
            for seg in utt.gr("Segment"):
                seg["name"] = self.voices[requestmsg["voicename"]].phonemap[seg["name"]]
            syl_html, pitch_html, wave_html = uttviz.draw_sylstruct_graph_pitch_waveform_html(utt)
        except Exception, e:
            print(e)
            log.error("Synthesis failed: %s" % (e))
            return str(e)
        log.info("Synthesis successful.")
        return {"wav": wavblob, "syl_html": syl_html, "pitch_html": pitch_html, "wave_html": wave_html}


class TTSHandler(threading.Thread): 
    def __init__(self, sock_addr, tts_server): 
        threading.Thread.__init__(self) 
        self.csocket, self.address = sock_addr
        self.rx_size = 1024
        self.tts_server = tts_server

    def run(self):
        log.info("Connection made %s running %s to handle request" % (self.address, self))
        request = self.rx_req()
        if request["type"] == "synth":
            log.info("Synthesis request received successfully.")
            reply = self.tts_server.synth(request)
        elif request["type"] == "listvoices":
            log.info("Listvoices request received successfully.")
            reply = self.tts_server.getvoicelist()
        self.tx_reply(reply)
        log.info("Reply sent successfully.")
        #remove self from tts_server thread list...                 
        for i, t in enumerate(self.tts_server.threads):
            if t is self:
                self.tts_server.threads.pop(i)

    def tx_reply(self, reply):
        replymsg = pickle.dumps(reply)
        self.csocket.sendall(replymsg)
        self.csocket.close()

    def rx_req(self):
        fulls = bytes()
        while True:
            s = self.csocket.recv(self.rx_size)
            if s:
                fulls += s
                if fulls.endswith(END_OF_MESSAGE_STRING):
                    fulls = fulls.rstrip(END_OF_MESSAGE_STRING)
                    break
            else:
                break
        return pickle.loads(fulls) #string in utf-8


if __name__ == "__main__":
    try:
        configfilename = sys.argv[1]
    except IndexError:
        configfilename = "ttslab_demo_server.conf"

    #loadconf
    config = configparser.RawConfigParser()
    with open(configfilename) as conffh:
        config.readfp(conffh)

    #setup logging...
    try:
        fmt = "%(asctime)s [%(levelname)s] %(message)s"
        log = logging.getLogger(NAME)
        formatter = logging.Formatter(fmt)
        ofstream = logging.FileHandler(DEF_LOG, "a")
        ofstream.setFormatter(formatter)
        log.addHandler(ofstream)
        # Console output.
        console = logging.StreamHandler()
        log.setLevel(DEF_LOGLEVEL)
        console.setFormatter(formatter)
        log.addHandler(console)
    except Exception, e:
        print("ERROR: Could not create logging instance.\n\tReason: %s" %e)
        sys.exit(1)

    #start server
    tts_server = TTSServer()
    for voicename in config.sections():
        # print("Loading: " + voicename, end='')
        voice_location = config.get(voicename, "voice_location")
        tts_server.loadvoice(voicename, voice_location)
        # print("\t\tDONE!")
    tts_server.run()
