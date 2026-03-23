#1 line program to determine if a string is a panagram no lambda functions
def is_panagram(s):
    alphabet = set('abcdefghijklmnopqrstuvwxyz')   # Define the alphabet as a set
    return set(s.lower()) >= alphabet   #set >= is a superset test

print(is_panagram("The quick brown fox jumps over the "))


#Exercise 4.2.2 123
#remove duplicates from an ordered list using sets

def remove_duplicates(lst):
    seen = set()  # Create an empty set to track seen elements
    result = []   # Create an empty list to store unique elements
    for item in lst:
        if item not in seen:  # Check if the item has not been seen before
            seen.add(item)     # Add the item to the seen set
            result.append(item)  # Append the unique item to the result list
    return result

print(remove_duplicates([1, 2, 3, 2, 4, 1, 5]))  # Example usage