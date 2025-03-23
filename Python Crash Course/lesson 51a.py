# -*- coding: utf-8 -*-
"""
Created on Thu May 30 10:08:51 2024

@author: gordo
"""


def animal_crackers(text):
    wordlist = text.lower().split()
    return wordlist[0][0] == wordlist[1][0]


print(animal_crackers("level Llama"))
