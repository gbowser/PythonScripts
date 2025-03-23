"""my first line.

and this is the end
"""

# -*- coding: utf-8 -*-

"""
Created on Tue Jan 23 13:55:40 2024

@author: gordo
"""

# INTRODUCTION TO FOR LOOPS
dict_students = {'bob': 12, 'rachel': 14, 'bobby': 17}
list1 = ['apples', 'pears', 'oranges', 'cherries']
tuple1 = (2, 6, 10)

# over data types
for my_item in list1:
    print(my_item)

for my_item in tuple1:
    print(my_item)

for my_item in dict_students:
    print(my_item)

for mycount in range(0, 11, 2):
    print(mycount)

for mycount in range(5, 51, 5):
    print(mycount)

# nested for loops

for i in range(0, 5):
    for j in range(0, 3):
        print(i * j)

# While loops

c = 0
while c < 5:
    c = c + 1
    if c == 3:
        break

    print(c)

c = 0
while c < 5:
    c = c + 1
    if c == 3:
        continue

    print(c)

c = 0
while c < 5:
    c = c + 1
    if c == 3:
        pass
    print(c)
