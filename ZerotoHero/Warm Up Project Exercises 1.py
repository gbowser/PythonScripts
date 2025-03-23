# -*- coding: utf-8 -*-
"""
Created on Sun Jul  7 09:42:07 2024.

@author: gordo
"""


def display(row1, row2, row3):
    """Display."""
    print(row1)
    print(row2)
    print(row3)


row1 = [' ', ' ', ' ']
row2 = [' ', ' ', ' ']
row3 = [' ', ' ', ' ']


display(row1, row2, row3)

row2[1] = 'X'
display(row1, row2, row3)

result = int(input("Please enter a value: "))
