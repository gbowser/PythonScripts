# -*- coding: utf-8 -*-
"""
Created on Sun Jul  7 08:31:36 2024.

@author: gordo
"""
import string


def ispangram(str1, alphabet=string.ascii_lowercase):
    """Ispangram function."""
#
    alpha_set = list(alphabet)
    remaining = list(alphabet)
#
    str1 = str1.replace(" ", "")
    str1 = str1.lower()
    str_set = set(str1)

    for char in str_set:
        remaining.remove(char)

    return (len(remaining) == 0)


print(ispangram("The quick brown fox jumps over og"))


def ispangram2(str1, alphabet=string.ascii_lowercase):
    """Ispangram function."""
#
    alphaset = set(alphabet)
    str1 = str1.replace(" ", "")
    str1 = str1.lower()
    str1 = set(str1)

    return str1 == alphaset


print(ispangram2("The quick brown fox jumps over the lazy dog"))
