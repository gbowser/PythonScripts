# -*- coding: utf-8 -*-
"""
Created on Tue Jul 16 08:06:40 2024

@author: gordo
"""
for i in [2, 'b', 3]:
    try:
        print(f"{i} squared is {i**2}")
    except TypeError:
        print(f"{i} is not a number")


x = 5
y = 1

try:
    z = x/y
    print(f"{x} divided by {y} = {z}")
except ZeroDivisionError:
    print(f"cannot divide {x} by zero")
finally:
    print("All done")


def ask():
    while True:
        try:
            y = int(input("Type an integer:..."))

            break
        except:
            print("Invalid input, try again\n")
            continue
        else:
            break
    print(f"Your number squared is ...{y**2}")


ask()
