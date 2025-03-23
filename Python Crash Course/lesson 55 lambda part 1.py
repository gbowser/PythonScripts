# -*- coding: utf-8 -*-
"""
Created on Sat Jul  6 11:45:32 2024.

@author: gordo
"""


def square(num):
    """Square function."""
    return num**2


mynums = [1, 2, 3, 4, 5, 6]

print(list(map(lambda num: num ** 2, mynums)))
