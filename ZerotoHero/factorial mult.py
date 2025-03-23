# -*- coding: utf-8 -*-
"""
Created on Wed Jan 24 16:08:21 2024

@author: gordo
"""


def calculate_factorial(my_number):

    my_result = 1
    factor = 1
    while factor <= my_number:
        my_result = my_result * factor
        factor = factor + 1
    return(my_result)


print(calculate_factorial(5))
