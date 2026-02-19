s,a ='hello',[4,10,2]
print(s, sep="-") # should return hello-
print(*s,sep="-") # h-e-l-l-o
print(a)   # should return [4, 10, 2]
print(*a,sep="-") # should return 4-10-2

print(f" range of unpacked a --> {range(*a)}") # should return range(4, 10, 2)
print(f"type of range(*a): {type(range(*a))}")

                                       
print(f"\n list of range of unpacked a --> {list(range(*a))}") # should return [4, 6, 8]
print(f"\n type of list of range(*a): {type(list(range(*a)))}")    

# problem 2.4.2
P=[4,5,0,2]
dPx = []
for i,c in enumerate(P):
    dPx.append(i*c)
print(f"dPx is {dPx}") # should return [0,5,0,6]
