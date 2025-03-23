# -*- coding: utf-8 -*-
"""
Created on Sat Jul  6 10:46:49 2024

@author: gordo
"""


def count_primes(num):
    # check for 0 or 1 input
    if num < 2:
        return 0
    ##################
    # 2 or greater
    ######################

    # store our prime nubers
    primes = [2]
    # counter going up for the input num
    x = 3
    # x is going thru all numbes up to input number
    while x <= num:
        for y in range(3, x, 2):
            if x % y == 0:
                x += 2
                break
        else:
            primes.append(x)
            x += 2
    print(1)
    print(primes)

    return len(primes)


if __name__ == "__main__":
    count_primes(500)
