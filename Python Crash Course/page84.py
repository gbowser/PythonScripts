alien_color = "blue f"

if alien_color == "green":
    print("you earned 5 points")
elif alien_color == "blue":
    print("you earned 10 points")
else:
    print("you earned 0 points")

person = {"name": "George", "age": 30, "grade": "A", "city": "Esher"}
print(person["name"].upper())
print(person.get("age2", 36))

pythondic = {"if": "condition", "tuple": "immutable", "list": "mutable"}
for key, item in pythondic.items():
    print(f"Here is the term  \n{key.title()}  \t{item}")

for mykey in sorted(pythondic.keys()):
    print(f"\t{mykey.title()}  \t{pythondic[mykey]}")
print("\n\n")
# adding items to pythondic
pythondic["dictiony"] = "key value pairs"
for mykey in sorted(pythondic.keys()):
    print(f"\t{mykey.title()}  \t{pythondic[mykey]}")


riverslist = {"Thames": "London", "Seine": "Paris", "Danube": "Austria"}
for myriver in riverslist.keys():
    print(f"The river {myriver} runs through {riverslist[myriver]}")

person1 = {"first": "George", "last": "Bowser", "age": 21, "city": "Esher"}
person2 = {"first": "Alan", "last": "Cunliffe", "age": 51, "city": "Kingston"}
person3 = {"first": "Betty", "last": "Boothr", "age": 71, "city": "Walton"}
personlist = [person1, person2, person3]

for myperson in personlist:
    for key, value in myperson.items():
        print(f"\t{value}")
