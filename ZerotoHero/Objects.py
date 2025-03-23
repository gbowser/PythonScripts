# -*- coding: utf-8 -*-
"""
Created on Wed Jan 24 16:40:58 2024

@author: gordo
"""
# OOP = Classes and Objects


class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def getName(self):
        return self.name

    def getAge(self):
        return self.age


p1 = Person("Bob", 22)
print(p1.getName())
print(p1.getAge())
