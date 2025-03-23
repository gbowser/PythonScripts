# -*- coding: utf-8 -*-
"""
Created on Fri Mar 26 17:30:38 2021

@author: gordo
"""
from astropy import constants as const
from astropy import units as u
import numpy as np
Teff = 5780*u.K
print("end of 1st cell")
#%%
R = const.R_sun
# Now the formula:
L = 4*np.pi*R**2*const.sigma_sb*Teff**4
# print the result:
print(L)