# -*- coding: utf-8 -*-
"""
Created on Thu May 30 10:29:31 2024

@author: gordo
"""


def makes_20(n1, n2):
    return (n1+n2 == 20 or n1 == 20 or n2 == 20)


print(makes_20(20, 10))
