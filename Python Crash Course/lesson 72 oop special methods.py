# -*- coding: utf-8 -*-
"""
Created on Mon Jul 15 10:11:38 2024.

@author: gordo
"""
mylist = [1, 2, 3]
print(len(mylist))


class Sample():
    pass


class Book():

    def __init__(self, title, author, pages):
        self.title = title
        self.author = author
        self.pages = pages

    def __str__(self):
        return f"{self.title.title()} by {self.author}"

    def __len__(self):
        return self.pages

    def __del__(self):
        print("A book has been deleted")


b = Book('Python rocks', 'Jose', 200)
print(b)
print(len(b))
del (b)
