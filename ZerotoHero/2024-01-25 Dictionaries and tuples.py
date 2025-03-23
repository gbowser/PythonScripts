"""my first line.

and this is the end
"""

# -*- coding: utf-8 -*-

"""
Created on Tue Jan 23 13:55:40 2024

@author: gordo
"""
# This section is dictionaries in curly braces
students = {'bob': 12, 'rachel': 14, 'bobby': 17}
print(students)
students['rachel'] = 28
del students['rachel']
students = {'bob': 12, 'rachel': 14, 'bobby': 1, 'henry': 5, 'amanda': 54}

print(len(students))

students = {"gordon": 23, "stephen": 45, "graham": 78, "john": 76}
print(f"students and scores {students}")
student2 = students["stephen"]

print(f"the 2nd student record is {student2}")

print(students.keys())
print(students.values())
# Introduction to tuples - they are in round brackets
mytup = ("oranges", "pears", "bananas")
print(mytup)
print(f"my tuples is {mytup}")
print(f"my 1st tuple is {mytup[0]}")
print(f"my 1st & 2nd tuple is {mytup[0:2]}")
tup2 = (12, 14)
tup3 = mytup+tup2
print(f"my concatenatged tuple is {tup3[0:]}")
#
# Exercise 12
mylist = ["Bob", "Henry", "Stephen", "Dad"]
print(f"print the 2nd term {mylist[1]}")
#
mysports = ["golf", "cycling", "rugby", "polo"]
mysports[2] = "riding"
print(f"print all {mysports}")
# item
list1 = ["bob", "gordon", "steve", "graham"]
list2 = ["bowser", "kennedy", "harrison"]
list3 = list1 + list2
num_list = [1, 4, 6, 8, 12, 43, 65, 87]
del num_list[2]
print(f"max of list is {max(num_list)}")
print(f"min of list is {min(num_list)}")
print(f"length of list is {len(num_list)}")


student_ages = {"henry": 33, "gordon": 23, "stephen": 45, "graham": 78}
del student_ages["gordon"]
# now for tuples, these are in round brackets
my_movies = ("movie1", "movie2", "movie 3")
print(my_movies)
my_newtuple = ("a", "b", "c", "d", "e")
short_letters = my_newtuple[0:3]

print(f"1st to 3rd items from tuple are {short_letters}")
print(f"1st to 3rd items from tuple are {my_newtuple[0:3]}")
