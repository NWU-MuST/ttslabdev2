# -*- coding: utf-8 -*-
""" Generates number sequences in English/Afrikaans...
"""
### PYTHON2 ###
from __future__ import unicode_literals, division, print_function
### PYTHON2 ###

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys

def make_num_combinations(expandf):
    sentences = []
    for i in range(100):
        for j in range(100):
            for k in range(100):
                print(" ".join([expandf(i), expandf(j), expandf(k)]))

def make_digit_combinations(expandf):
    sentences = []
    for i in range(10):
        for j in range(10):
            for k in range(10):
                print(" ".join([expandf(i), expandf(j), expandf(k)]))


if __name__ == "__main__":
    
    if sys.argv[1] == "afr":
        from ttslab.lang.afrikaans_numexp import expand as expandf
    else:
        from ttslab.lang.english_numexp import expand as expandf

    if sys.argv[2] == "num":
        make_num_combinations(expandf)
    elif sys.argv[2] == "digit":
        make_digit_combinations(expandf)
