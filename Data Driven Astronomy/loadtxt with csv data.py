# -*- coding: utf-8 -*-
"""
Created on Sun Jan 21 17:35:08 2024

@author: gordo
"""
import numpy as np
data = np.loadtxt('data.csv', delimiter=',')
mymean = np.mean(data)
mymedian = np.median(data)
print(mymean, mymedian)


