# -*- coding: utf-8 -*-
"""
Created on Mon Jan 22 17:00:24 2024

@author: gordo
"""
import numpy as np


def mean_datasets(*args):
    #    numberfiles = len(datafiles)
    mydata = np.loadtxt(args(1), delimiter=',')
    dimensions = np.shape(mydata)
    rows, columns = dimensions
    return (dimensions)

    myresult = mean_datasets('data1.csv', 'data2.csv')
    print(myresult)
