mylist=[]
for i in range (1,30,3):
    mylist.append(i)
print(f"1st 3 items are {mylist[1:4]}")
middle = int(len(mylist)/2)
print(f"Middle 3 items are {mylist[middle-1:middle+2]}")
print(f"Last 3 items are {mylist[-4:-1]}")

pizzas=["Hawain","MeatFeast","Veggie","Mushroom"]
print (f"Pizza List {pizzas}")
pizzas.append("HotSpicy")

#TUPLES
buffet=("prawns","ham","lettuce")
print (buffet)
for i in buffet:
    print(f"Food item...{i}")
buffet[2]=("pork")