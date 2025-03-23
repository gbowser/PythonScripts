# -*- coding: utf-8 -*-
"""
Created on Sat Jul  6 16:16:13 2024

@author: gordo
"""

import math


def vol(rad):
    return (4/3) * math.pi * rad ** 3


print(vol(2))


def ran_check(num, low, high):
    return num >= low and num <= high


print(ran_check(11, 2, 7))


def up_low(s):
    up = 0
    lo = 0
    for char in s:
        if char.islower():
            lo += 1
        if char.isupper():
            up += 1

    print(f"No. of Upper case characters : {up}")
    print(f"No. of lower case characters : {lo}")


up_low("Hello Mr. Rogers, how are you this fine Tuesday?")

unique_elements = set()
