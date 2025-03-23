# -*- coding: utf-8 -*-
"""
Created on Sun Jan 21 17:19:24 2024

@author: gordo
"""
data = []
for xline in open('data.csv'):
    xrow = []
    for xcol in xline.strip().split(','):
        xrow.append(float(xcol))
        data.append(xrow)

print(data)
