# -*- coding: utf-8 -*-
"""
Created on Tue Jul 16 06:12:57 2024

@author: gordo
"""


def add(n1, n2):
    print(n1+n2)


add(10, 20)
number1 = 10
number2 = 5
add(number1, number2)


try:
    # WANT TO ATTEMPT THIS BIT OF CODE, MAY HAVE AN ERROR
    result = 10+10
except:
    print("looks like not adding correctly")
else:
    print("add went well")
    print(result)
