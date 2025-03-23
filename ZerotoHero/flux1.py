# -*- coding: utf-8 -*-
"""
Created on Sun Jan 21 16:48:26 2024

@author: gordo
"""

import numpy as np

fluxes = np.array([23.3, 42.1, 2.0, -3.2, 55.6])
m = np.mean(fluxes)
print(m)
print(np.size(fluxes))  # length of array
print(np.std(fluxes))  # standard deviation
