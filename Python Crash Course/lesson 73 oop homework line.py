# -*- coding: utf-8 -*-
"""
Created on Mon Jul 15 13:20:49 2024.

@author: gordo
"""


class Line(object):

    def __init__(self, coor1, coor2):
        self.coor1 = coor1
        self.coor2 = coor2

    def distance(self):
        x1, y1 = self.coor1
        x2, y2 = self.coor2
        return ((self.coor2[0]-self.coor1[0])**2+(self.coor2[1]-self.coor1[1])**2) ** 0.5

    def slope(self):
        x1, y1 = self.coor1
        x2, y2 = self.coor2
        return (y2-y1)/(x2-x1)


coordinate1 = (3, 2)
coordinate2 = (8, 10)

li = Line(coordinate1, coordinate2)
print(li.distance())
print(li.slope())
