"""
Created on Sat Jul  6 11:25:22 2024.
@author: gordo
"""


def splicer(mystring):
    """Splicer function."""
    if len(mystring) % 2 == 0:
        return ('EVEN')
    else:
        return mystring[0]


names = ['Andy', 'Eve', 'Sally']
print(list(map(splicer, names)))


def check_even(num):
    """Check numbers."""
    return num % 2 == 0


mynums = [1, 2, 3, 4, 5, 6]
print(list(filter(check_even, mynums)))


for n in filter(check_even, mynums):
    print(n)
