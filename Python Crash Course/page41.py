mylist = ["gordon", "matthew", "daniel", "stephanie", "mark"]
while mylist:
    print(f" Guest is {mylist.pop()}")
mylist = ["gordon", "matthew", "daniel", "stephanie", "mark"]
print(type(mylist))
print(f"This guest can't attend: {(mylist[1].title())}")
mylist[1] = "Bartholomew"
print(mylist)
mylist.insert(0, "new guest zero")
print(mylist)
mylist.append("last guest zero")
print(mylist)
while mylist:
    print(f" Guest is {mylist.pop()}")

mylist = ["gordon", "matthew", "daniel", "stephanie", "mark"]
print(len(mylist))
while len(mylist) > 2:
    removed_guest = mylist.pop()
    print(f"this guest is removed {removed_guest} ")

for guest in mylist:
    print(f"you are still invited: {guest}")

del mylist[0]
del mylist[0]
print(mylist)

mylist = ["gordon", "matthew", "daniel", "stephanie", "mark"]
print(f"temporary sorted list : {sorted(mylist)} ")
