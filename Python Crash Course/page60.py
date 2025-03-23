# counting to twenty
for i in range(1, 21, 1):
    print(f"Next number {i}")


sumup = 0
for i in range(1, 10000001):
    #     print(f"Next number {i}")
    sumup = sumup + i
#     print (f"Sum so far is {sumup}")

print(f"The sum is ...{sumup}")

myoddlist = []
for i in range(1, 21, 2):
    print(f"Odd numbers between 1 and 20...{i}")
    myoddlist.append(i)
print(f"Odd list ...{myoddlist}")

# cubes
cube_list = []
cube_comp_list = []
for i in range(1, 11):
    print(f"Cube of {i} is {i**3}")
    cube_list.append(i**3)
print(f"Cube list ...{cube_list}")

for i in range(1, 11):
    cube_comp_list.append(i**3)
print(f"Cube list ...{cube_comp_list}")
