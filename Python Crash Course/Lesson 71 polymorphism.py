# -*- coding: utf-8 -*-
"""
Created on Sun Jul 14 17:58:56 2024

@author: gordo
"""


class Dog():

    def __init__(self, name):
        self.name = name

    def speak(self):
        return self.name + " says woof!"


class Cat:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return self.name + " says meow!"


niko = Dog("niko")
felix = Cat("felix")

print(niko.speak())
print(felix.speak())

for pet in [niko, felix]:
    print(type(pet))
    print(pet.speak())


def pet_speak(pet):
    print(pet.speak())


pet_speak(niko)
pet_speak(felix)


class Animal():
    def __init__(self, name):
        self.name = name

    def speak(self):
        raise NotImplementedError(
            "Subclass must implement this abstract method")


myanimal = Animal("fred")


class Dog(Animal):

    def speak(self):
        return self.name + " says woof!"


class Cat(Animal):

    def speak(self):
        return self.name + " says meow!"


fido = Dog("Fido")
isis = Cat("Isis")
print(fido.speak())
print(isis.speak())
