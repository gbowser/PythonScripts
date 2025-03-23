# -*- coding: utf-8 -*-
"""
Created on Sun Jul 14 14:56:52 2024

@author: gordo
"""


class Animal():

    def __init__(self):
        print("ANIMAL CREATED")

    def who_am_i(self):
        print("I am an animal")

    def eat(self):
        print("I am eating")


# DERIVED CLASS
class Dog(Animal):
    def __init__(self):
        Animal.__init__(self)
        print("Dog Created")

    def who_am_i(self):
        print("I am a dog!")

    def bark(self):
        print("Bark")

    def eat(self):
        print("Dog eating!")


myanimal = Animal()
myanimal.eat()
myanimal.who_am_i()
mydog = Dog()
mydog.eat()
mydog.who_am_i()
mydog.bark()
