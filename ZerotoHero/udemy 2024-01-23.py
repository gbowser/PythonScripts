""".
Created on Tue Jan 23 09:52:24 2024

@author: gordo
"""
x = 15
y = 30
z = 2
print(f"result is {(x+y)/2}")

print(f"modulus {x % z}")

myname = "Gordon"
name1, name2, name3 = "Gordon", "Steve", "Bob"
myhello = "hello"
print(myhello * 10)

name, age = "Gordon", 62

concat = name1 + name2
print(f" result is  {concat[0:5]}")
print(f" result is  {concat[0:]}")


shopping_list = ['apples', 'bananas', "pears", "oranges"]
print(shopping_list[1:3])
# add items to list
shopping_list.append("blueberries")
print(shopping_list)
shopping_list[0] = "cherries"
print(shopping_list)
del shopping_list[1]
shopping_list2 = ["bread", "jam", "butter", "peanuts"]
print(f"My entire shopping {shopping_list + shopping_list2}")
shopping_list2.insert(1, "knives")
list_num = [1, 5, 3, 7, 4, 6, 10]
print(max(list_num))
print(min(list_num))
print(f"Maximum is {max(list_num)}")
print(f"Max plus min imum is {max(list_num)+min(list_num)}")
