# -*- coding: utf-8 -*-
"""
Created on Sat Jul  6 17:30:15 2024

@author: gordo
"""


def pal(s):
    new_s = s.replace(" ", "")
    new_s1 = new_s[::-1]

    return new_s == new_s


pal('nurses run')
