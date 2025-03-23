# -*- coding: utf-8 -*-
"""
Created on Sat Jul  6 11:06:59 2024

@author: gordo
"""


def square(num):
    return num**2


my_nums = [1, 2, 3, 4, 5]

for item in map(square, my_nums):
    print(item)
squares = list(map(square, my_nums))
