# -*- coding: utf-8 -*-
"""
Created on Sat Jul  6 17:06:07 2024

@author: gordo
"""


def get_unique_elements(input_list):
    """
    This function takes a list and returns a new list with unique elements.

    Parameters:
    input_list (list): The list from which to extract unique elements.

    Returns:
    list: A new list containing only unique elements.
    """
    # Using a set to store unique elements
    unique_elements = set()
    unique_list = []

    for item in input_list:
        if item not in unique_elements:
            unique_elements.add(item)
            unique_list.append(item)

    return unique_list


# Example usage
original_list = [0, 1, 7, 1, 2, 2, 3, 3, 3, 3, 4, 5]
unique_list = get_unique_elements(original_list)
print("Original List:", original_list)
print("Unique List:", unique_list)


def unique_list(lst):
    # Also possible to use list(set())
    x = []
    for a in lst:
        if a not in x:
            x.append(a)
    return x
