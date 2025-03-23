# -*- coding: utf-8 -*-
"""
Created on Thu May 30 15:56:48 2024

@author: gordo
"""


def square(num):
    return (num**2)


my_nums = [1, 2, 3, 4, 5]
for item in map(square, my_nums):
    print(item)


def splicer(mystring):
    if len(mystring) % 2 == 0:
        return "EVEN"
    else:
        return mystring[0]


names = ['Andy', 'Eve', 'Sally']
print(names)
print(list(map(splicer, names)))
