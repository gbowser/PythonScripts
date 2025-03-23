# -*- coding: utf-8 -*-
"""
Created on Sun Jan 21 17:35:08 2024

@author: gordo
"""
import numpy as np


def calc_stats(myfile):

    data = np.loadtxt(myfile, delimiter=',')
    mymean = np.mean(data)
    mymedian = np.median(data)
    mytuple = ((round(mymean, 1)), round(mymedian, 1))
    return (mytuple)
