s=set([1,1,4,3,2,2,3,4,1,3,'surprise'])
print(s)
for item in s:
    print(item)
s.add(5)
print(s)
s.remove('surprise')

print(s)
s.discard('surprise')
print(s)

t=set([6,7,8,1,4,5])

#Union
print(f"Union s|t = {s|t}")
#Intersection
print(f"Intersection s&t = {s&t}")
#Difference
print(f"Difference s-t = {s-t}")
