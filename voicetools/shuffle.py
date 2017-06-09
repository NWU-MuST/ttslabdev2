#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys
import random


if __name__ == '__main__':
    
    infn = sys.argv[1]
    seed = int(sys.argv[2])
    
    infh = open(infn)
    lines = infh.read().splitlines()
    infh.close()

    random.seed(seed)
    random.shuffle(lines)

    for line in lines:
        print line
