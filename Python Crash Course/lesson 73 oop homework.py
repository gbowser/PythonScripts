# -*- coding: utf-8 -*-
"""
Created on Mon Jul 15 13:20:49 2024.

@author: gordo
"""


class Line:

    def __init__(self, coor1, coor2):
        self.coor1 = coor1
        self.coor2 = coor2

    def distance(self, coor1, coor2):
        return 1


coordinate1 = (3, 2)
coordinate2 = (8, 10)

li = Line(coordinate1, coordinate2)

# print(li.distance)



