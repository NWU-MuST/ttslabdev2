#!/usr/bin/env python
from __future__ import division

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys

import ttslab

from qta3 import plotstuff

if __name__ == "__main__":
    prefix = sys.argv[1]
    utt = ttslab.fromfile(sys.argv[2])
    reff0 = ttslab.fromfile(sys.argv[3])
    qtaf0 = ttslab.fromfile(sys.argv[4])

    plotstuff(utt, reff0, qtaf0, prefix=prefix)

