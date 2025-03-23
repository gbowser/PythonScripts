# -*- coding: utf-8 -*-
"""
Created on Tue Jul 16 06:23:09 2024

@author: gordo
"""
try:
    # type r = read only, so can't write to it
    f = open("testfile", "r")
    f.write("Write a test line")
except TypeError:
    print("there a TypeError")
except OSError:
    print("Hey, you have an I/O error")
finally:
    print("I always run")


def ask_for_int():
    while True:
        try:
            result = int(input("please provide number: .. "))
        except:
            print("Whoops, that is not a number")
            continue
        else:
            print("Yes, that was an integer")
            break
        finally:
            print("I'm going to ask you again\n")


ask_for_int()
