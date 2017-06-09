#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Simple client to make TTS requests for demo website...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os
import sys
import socket
import time
import cPickle as pickle
import codecs
from optparse import OptionParser


NAME = "client.py"
DEF_HOST = "localhost"
DEF_PORT = 22223

class TTSClient(object):
    END_OF_MESSAGE_STRING = b"<EoM>"

    def __init__(self, host=DEF_HOST, port=DEF_PORT, recv_size=1024):
        self.host = host
        self.port = port
        self.recv_size = recv_size

    def request(self, requesttype, voicename=None, text=None):
        #create message
        message = {"type": requesttype,
                   "voicename": voicename,
                   "text": text}
        fulls = pickle.dumps(message)
        #create a socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #connect to server
        s.connect((self.host, self.port))
        #send..
        s.sendall(fulls)
        s.sendall(TTSClient.END_OF_MESSAGE_STRING)
        #read confirmation..
        msgfull = b""
        while True:
            msgpart = s.recv(self.recv_size)
            if msgpart:
                msgfull += msgpart
            else:
                break
        #close connection..
        s.close()
        #recover reply..
        reply = pickle.loads(msgfull)
        return reply


    def listvoices(self):
        return self.request("listvoices")


def setopts():
    """ Setup all possible command line options....
    """
    usage = 'USAGE: %s [options] VOICENAME ["Input text."]' % (NAME)
    parser = OptionParser(usage=usage)
    parser.add_option("-p",
                      "--port",
                      type="int",
                      dest="port",
                      default=DEF_PORT,
                      help="Specify the port number to connect to. [%default]",
                      metavar="PORTNUM")
    parser.add_option("-a",
                      "--address",
                      dest="host",
                      default=DEF_HOST,
                      help="Specify the host address to connect to. [%default]",
                      metavar="HOSTADDRESS")
    parser.add_option("-l",
                      "--listvoices",
                      action="store_true",
                      dest="listvoices",
                      help="Request a list of loaded voices from the server.")
    return parser


#only lists voices:
if __name__ == "__main__":
    #set CLI options..
    parser = setopts()
    opts, args = parser.parse_args()

    host = opts.host
    port = opts.port
    
    client = TTSClient(host, port)
    
    if opts.listvoices:
        voicelist = client.listvoices()
        print("\n".join(voicelist))
    else:
        pass
