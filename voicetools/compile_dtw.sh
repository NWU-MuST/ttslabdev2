#!/bin/bash

cython --convert-range ttslab_dtw.pyx
gcc -shared -pthread -fPIC -fwrapv -O2 -Wall -fno-strict-aliasing -I/usr/include/python2.7 -o ttslab_dtw.so ttslab_dtw.c
