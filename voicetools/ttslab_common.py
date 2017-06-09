# -*- coding: utf-8 -*-
""" Collects some common functions...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

#### some functions collected from various experimental setups:
def partition(lst, n): 
    """ Partitions 'lst' into 'n' sublists approximately equal
        length...
    """
    division = len(lst) / float(n) 
    return [ lst[int(round(division * i)): int(round(division * (i + 1)))] for i in xrange(n) ]



#### from demitstats:
import math
import numpy as np
import scipy.stats as stats

def stderr(data):
    """ The standard error of the mean (SEM) is the standard deviation
    of the sample-means estimate of a population mean. (It can also be
    viewed as the standard deviation of the error in the sample mean
    relative to the true mean, since the sample mean is an unbiased
    estimator.) SEM is usually estimated by the sample estimate of the
    population standard deviation (sample standard deviation) divided
    by the square root of the sample size (assuming statistical
    independence of the values in the sample)
    """
    return np.std(data, ddof=1) / math.sqrt(len(data))


def mean_confidence_interval(data, confidence=0.95):
    """DEMIT: uses the t-distribution to compensate for small
       samples...
    """
    a = np.array(data).astype(np.float)
    n = len(a)
    m, se = np.mean(a), stderr(a)
    h = se * stats.t.ppf((1 + confidence) / 2, n-1)
    return m, m - h, m + h


def test_mean_confidence_interval():
    testdata = [9.206343, 9.299992, 9.277895, 9.305795, 9.275351, 9.288729, 9.287239, 9.260973,
                9.303111, 9.275674, 9.272561, 9.288454, 9.255672, 9.252141, 9.297670, 9.266534,
                9.256689, 9.277542, 9.248205, 9.252107, 9.276345, 9.278694, 9.267144, 9.246132,
                9.238479, 9.269058, 9.248239, 9.257439, 9.268481, 9.288454, 9.258452, 9.286130,
                9.251479, 9.257405, 9.268343, 9.291302, 9.219460, 9.270386, 9.218808, 9.241185,
                9.269989, 9.226585, 9.258556, 9.286184, 9.320067, 9.327973, 9.262963, 9.248181,
                9.238644, 9.225073, 9.220878, 9.271318, 9.252072, 9.281186, 9.270624, 9.294771,
                9.301821, 9.278849, 9.236680, 9.233988, 9.244687, 9.221601, 9.207325, 9.258776,
                9.275708, 9.268955, 9.257269, 9.264979, 9.295500, 9.292883, 9.264188, 9.280731,
                9.267336, 9.300566, 9.253089, 9.261376, 9.238409, 9.225073, 9.235526, 9.239510,
                9.264487, 9.244242, 9.277542, 9.310506, 9.261594, 9.259791, 9.253089, 9.245735,
                9.284058, 9.251122, 9.275385, 9.254619, 9.279526, 9.275065, 9.261952, 9.275351,
                9.252433, 9.230263, 9.255150, 9.268780, 9.290389, 9.274161, 9.255707, 9.261663,
                9.250455, 9.261952, 9.264041, 9.264509, 9.242114, 9.239674, 9.221553, 9.241935,
                9.215265, 9.285930, 9.271559, 9.266046, 9.285299, 9.268989, 9.267987, 9.246166,
                9.231304, 9.240768, 9.260506, 9.274355, 9.292376, 9.271170, 9.267018, 9.308838,
                9.264153, 9.278822, 9.255244, 9.229221, 9.253158, 9.256292, 9.262602, 9.219793,
                9.258452, 9.267987, 9.267987, 9.248903, 9.235153, 9.242933, 9.253453, 9.262671,
                9.242536, 9.260803, 9.259825, 9.253123, 9.240803, 9.238712, 9.263676, 9.243002,
                9.246826, 9.252107, 9.261663, 9.247311, 9.306055, 9.237646, 9.248937, 9.256689,
                9.265777, 9.299047, 9.244814, 9.287205, 9.300566, 9.256621, 9.271318, 9.275154,
                9.281834, 9.253158, 9.269024, 9.282077, 9.277507, 9.284910, 9.239840, 9.268344,
                9.247778, 9.225039, 9.230750, 9.270024, 9.265095, 9.284308, 9.280697, 9.263032,
                9.291851, 9.252072, 9.244031, 9.283269, 9.196848, 9.231372, 9.232963, 9.234956,
                9.216746, 9.274107, 9.273776]
    print(mean_confidence_interval(testdata, confidence=0.95))
    #data from:
    #http://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm
    #confidence interval should be:
    #(9.258242, 9.264679)

if __name__ == "__main__":
    test_mean_confidence_interval()

