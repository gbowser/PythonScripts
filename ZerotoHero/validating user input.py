# -*- coding: utf-8 -*-
"""
Created on Sun Jul  7 13:43:04 2024.

@author: gordo
"""


def user_choice():
    """User choice function."""
    # VARIABLES
    #
    # Initial
    #
    choice = "WRONG"
    acceptable_range = range(0, 10)
    within_range = False
    #
    #  2 conditions to check Digit or within range
    while choice.isdigit() == False or within_range == False:
        choice = input(" please enter a number (0-10) : ")
        if choice.isdigit() == False:
            print("that is not a number")
       #
       # RANGE CHECK
        if choice.isdigit() == True:
            if int(choice) in acceptable_range:
                within_range = True
            else:
                print("number out of range")
                within_range = False

    return int(choice)


user_choice()
