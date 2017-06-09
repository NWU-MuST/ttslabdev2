#!/usr/bin/python

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

# For CGI support
import cgi
# For debugging support
#import cgitb; cgitb.enable()

# import needed libraries:
import os, sys,random,time

import ttslab_demo_client

HTMLTEMPLATE = \
"""
<html>
<head>
<meta content="text/html; charset=UTF-8" http-equiv="content-type">
<meta name="author" content="Daniel R. van Niekerk" />
<style>
.figure {
    width: 100%%;
    height: 500px;
}
</style>
</head>
<body>

<h1>Text-to-speech demo</h1>

<p>
Please press the browser's <strong>back</strong> button to synthesize
another sample...
</p>

<hr>
<h1>SAMPLE:</h1>
<audio preload="auto" controls="controls">
<source src="%(wavfname)s" type="audio/wav" />
Please try the latest Firefox! :-(
</audio>
<object class="figure" data="%(sylfname)s" type="text/html">
Please try the latest Firefox! :-(
</object>
<object class="figure" data="%(pitchfname)s" type="text/html">
Please try the latest Firefox! :-(
</object>
<object class="figure" data="%(wavefname)s" type="text/html">
Please try the latest Firefox! :-(
</object>
</body>
</html>
"""

form = cgi.FieldStorage(keep_blank_values=True)
#DEMITASSE: change this later to use md5 and don't redo if exists...
basename = "_".join([str(int(time.mktime(time.localtime()))),
                     str(random.randint(0, 100)).zfill(3)])
voicename = str(form.getvalue("voice"))
text = unicode(form.getvalue("textinput"), encoding="utf-8")

client = ttslab_demo_client.TTSClient(ttslab_demo_client.DEF_HOST, ttslab_demo_client.DEF_PORT)
synthd = client.request("synth", voicename, text)

wavfname = os.path.join("../output/", basename + ".wav")
outfh = open(wavfname, "wb")
outfh.write(synthd["wav"])
outfh.close()

sylfname = os.path.join("../output/", basename + "_syl.html")
outfh = open(sylfname, "wb")
outfh.write(synthd["syl_html"])
outfh.close()

pitchfname = os.path.join("../output/", basename + "_pitch.html")
outfh = open(pitchfname, "wb")
outfh.write(synthd["pitch_html"])
outfh.close()

wavefname = os.path.join("../output/", basename + "_wave.html")
outfh = open(wavefname, "wb")
outfh.write(synthd["wave_html"])
outfh.close()

# This needs to be here first.
print "Content-Type: text/html"     # Just set the standard html content type.
print                               # Blank line signifies the end of the header info.
print HTMLTEMPLATE % {"wavfname": wavfname,
                      "sylfname": sylfname,
                      "pitchfname": pitchfname,
                      "wavefname": wavefname}
