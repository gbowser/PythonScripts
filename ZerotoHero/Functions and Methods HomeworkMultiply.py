# -*- coding: utf-8 -*-
"""
Created on Sat Jul  6 17:26:16 2024

@author: gordo
"""


def multiply(numbers):
    x = 1
    for myval in numbers:
        x *= myval
    return x


print(multiply([2, 4, 5, 6]))
