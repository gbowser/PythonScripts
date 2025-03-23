"""my first line.

and this is the end
"""
# -*- coding: utf-8 -*-

# FUNCTIONS


def hello_world_func():
    print("hello world")


def greeting(name):
    print("Hi " + name + "!")


def my_add(num1, num2):
    print(f"result is  {num1 + num2}")


def my_mult_return(num1, num2):
    return(num1 * num2)


hello_world_func()
greeting("Gordon")
my_add(3, 5)
print(my_mult_return(34, 56))
