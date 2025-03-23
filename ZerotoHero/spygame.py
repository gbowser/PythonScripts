# -*- coding: utf-8 -*-
"""
Created on Thu May 30 10:34:00 2024

@author: gordo
"""


def spygame(nums):
    code = [0, 0, 7, 'x']
    for num in nums:
        if num == code[0]:
            code.pop(0)

    return len(code) == 1


print(spygame([2, 3, 4, 0, 1, 7, 8]))
