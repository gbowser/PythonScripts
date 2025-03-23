# -*- coding: utf-8 -*-
"""
Created on Wed Jan 24 17:00:33 2024

@author: gordo
"""


class Car:
    def __init__(self):
        self.wheels = 4
        self.seats = 5

    def drive(self):
        print("driving a car.....")


class SportsCar(Car):
    def __init__(self):
        super().__init__()
        self.engine_power = '400 HP'
        self.seats = 2

    def drive(self):
        print("driving a sports car")


mySportsCar = SportsCar()
mySportsCar.drive()
