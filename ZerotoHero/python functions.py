# -*- coding: utf-8 -*-
"""
Created on Wed Jan 24 15:29:12 2024

@author: gordo
"""
print(abs(-23))
print(bool(0))
print(bool(1))
print(bool())
print(bool(None))
print(dir("hello"))


# help
sent = "hello"
print(help(sent.upper))


sent = "print('hi')"
eval(sent)

# convert data types
print("hello" + str(100))
print(123 + int("456"))
print(float("123.465"))
