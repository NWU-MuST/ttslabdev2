#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Detect inhalation in pre-detected "silences" of a speech signal --
    Values tuned to the sample case in the "samples" directory for
    precision (slightly conservative)...assuming 16kHz audio
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys

import numpy as np
import scipy.signal as ss
from pylab import *

from ttslab.waveform import Waveform

#Plot frequency and phase response from: http://mpastell.com/2010/01/18/fir-with-scipy/
def mfreqz(b,a=1):
    w,h = ss.freqz(b,a)
    h_dB = 20 * log10 (abs(h))
    subplot(211)
    plot(w/max(w),h_dB)
    ylim(-150, 5)
    ylabel('Magnitude (db)')
    xlabel(r'Normalized Frequency (x$\pi$rad/sample)')
    title(r'Frequency response')
    subplot(212)
    h_Phase = unwrap(arctan2(imag(h),real(h)))
    plot(w/max(w),h_Phase)
    ylabel('Phase (radians)')
    xlabel(r'Normalized Frequency (x$\pi$rad/sample)')
    title(r'Phase response')
    subplots_adjust(hspace=0.5)

#Plot step and impulse response
def impz(b,a=1):
    l = len(b)
    impulse = repeat(0.,l); impulse[0] =1.
    x = arange(0,l)
    response = ss.lfilter(b,a,impulse)
    subplot(211)
    stem(x, response)
    ylabel('Amplitude')
    xlabel(r'n (samples)')
    title(r'Impulse response')
    subplot(212)
    step = cumsum(response)
    stem(x, step)
    ylabel('Amplitude')
    xlabel(r'n (samples)')
    title(r'Step response')
    subplots_adjust(hspace=0.5)

#from: http://wiki.scipy.org/Cookbook/SignalSmooth
def smooth(x,window_len=11,window='hanning'):
    """smooth the data using a window with requested size.
    
    This method is based on the convolution of a scaled window with the signal.
    The signal is prepared by introducing reflected copies of the signal 
    (with the window size) in both ends so that transient parts are minimized
    in the begining and end part of the output signal.
    
    input:
        x: the input signal 
        window_len: the dimension of the smoothing window; should be an odd integer
        window: the type of window from 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'
            flat window will produce a moving average smoothing.

    output:
        the smoothed signal
        
    example:

    t=linspace(-2,2,0.1)
    x=sin(t)+randn(len(t))*0.1
    y=smooth(x)
    
    see also: 
    
    np.hanning, np.hamming, np.bartlett, np.blackman, np.convolve
    scipy.signal.lfilter
 
    TODO: the window parameter could be the window itself if an array instead of a string
    NOTE: length(output) != length(input), to correct this: return y[(window_len/2-1):-(window_len/2)] instead of just y.
    """

    if x.ndim != 1:
        raise ValueError, "smooth only accepts 1 dimension arrays."

    if x.size < window_len:
        raise ValueError, "Input vector needs to be bigger than window size."


    if window_len<3:
        return x


    if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
        raise ValueError, "Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'"


    s=np.r_[x[window_len-1:0:-1],x,x[-1:-window_len:-1]]
    #print(len(s))
    if window == 'flat': #moving average
        w=np.ones(window_len,'d')
    else:
        w=eval('np.'+window+'(window_len)')

    y=np.convolve(w/w.sum(),s,mode='valid')
    return y


def filt(h, x):
    """ Zero-phase filter of samples (x) from impulse response (h)...
        Equiv to convolution without delay in output signal...
    """
    return ss.filtfilt(h, [1], x)


def make_lpf(cutoff_hz=1000.0, sr=16000.0, numtaps=61):
    nyqf = sr / 2.0
    lpfcoefs = ss.firwin(numtaps, cutoff=cutoff_hz, nyq=nyqf)
    return lpfcoefs

def make_hpf(cutoff_hz=800.0, sr=16000.0, numtaps=61):
    lpfcoefs = make_lpf(cutoff_hz, sr, numtaps)
    hpfcoefs = -lpfcoefs
    hpfcoefs[numtaps//2] = hpfcoefs[numtaps//2] + 1
    return hpfcoefs

def zero_startends(samples, sr=16000.0, dur=0.050): #disregard first and last few ms
    ssamples = samples.copy()
    ssamples[:int(sr*dur)] = 0.0
    ssamples[-int(sr*dur):] = 0.0
    return ssamples

def detectsimple(a, sr=16000.0, smoothn=101, thresh=0.00005, medfn=151):
    samples = smooth(np.abs(a), smoothn)
    b = np.zeros_like(a)
    b = (samples > thresh)
    return ss.medfilt(b, medfn)

#from: http://stackoverflow.com/questions/4494404/find-large-number-of-consecutive-values-fulfilling-condition-in-a-numpy-array
def find_segs(samples, threshold=1.0, min_dur=1000):
  start = -1
  segments = []
  for idx,x in enumerate(samples):
    if start < 0 and abs(x) >= threshold:
      start = idx
    elif start >= 0 and abs(x) < threshold:
      dur = idx-start
      if dur >= min_dur:
        segments.append((start,dur))
      start = -1
  return segments

def test(testfn="samples/data_001d.wav"):
    aud = Waveform(testfn)
    samples = zero_startends(aud.samples)
    hh = make_hpf()
    # mfreqz(h)
    # show()
    hpfsamples = filt(hh, samples)
    detsamples = detectsimple(hpfsamples)
    plot(samples)
    plot(np.abs(hpfsamples))
    plot(detsamples / 1000.0)
    print(find_segs(detsamples))
    show()
    
def inhaletimeinfo(audiosamples, sr=16000.0):
    samples = zero_startends(audiosamples)
    hh = make_hpf()
    hpfsamples = filt(hh, samples)
    detsamples = detectsimple(hpfsamples)
    segs = find_segs(detsamples)
    seglens = [seg[1] for seg in segs]
    try:
        bestsegcand = segs[np.argmax(seglens)]
    except ValueError:
        return None
    offsettime = bestsegcand[0] / sr
    duration = bestsegcand[1] / sr
    return offsettime, duration
    

def test2(testfn="samples/data_001d.wav"):
    aud = Waveform(testfn)
    print(inhaletimeinfo(aud.samples))
    


if __name__ == '__main__':
    test2()
