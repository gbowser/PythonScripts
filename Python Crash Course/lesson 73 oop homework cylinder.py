# -*- coding: utf-8 -*-
"""
Created on Mon Jul 15 13:58:52 2024

@author: gordo
"""


class Cylinder:

    def __init__(self, height=1, radius=1):
        self.height = height
        self.radius = radius

    def volume(self):
        return 3.14*self.radius ** 2 * self.height

    def surface(self):
        top = 3.14 * (self.radius)**2
        return (2*top) + (2*3.14*self.radius*self.height)


c = Cylinder(2, 3)
print(c.volume())
print(c.surface())
