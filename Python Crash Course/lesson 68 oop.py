# -*- coding: utf-8 -*-
"""
Created on Fri Jul 12 16:59:41 2024.

@author: gordo
"""
mylist = [1, 2, 3, 4]
myset = set()


class Dog():
    """learning about class."""

    # CLASS OBJECT ATTRIBUTE
    # SAME FOR ANY INSTANCE OF A CLASS
    species = 'mammal'

    def __init__(self, breed, name):
        # ATTRIBUTES
        # We take in the argument
        # Assign it using self.attribute_name
        self.breed = breed
        self.name = name
        # spots is boolean

# operations/actions ---> Methods
    def bark(self, number):
        print("WOOF My name is {} and the number is {}".format(self.name, number))


my_dog = Dog(breed="Lab", name="Sammy")


print("Dog breed is " + my_dog.breed)
print("Dog name is " + my_dog.name)
print("Dog species is " + my_dog.species)
my_dog.bark(3)


class Circle():

    # CLASS OBJECT ATTRIBUTE
    pi = 3.14

    def __init__(self, radius=1):
        self.radius = radius
        self.area = radius * radius * Circle.pi
    # METHOD

    def get_circumference(self):
        return self.radius * self.pi * 2


my_circle = Circle(30)
print(my_circle.pi)
print(my_circle.radius)
print(my_circle.get_circumference())
print(my_circle.area)
