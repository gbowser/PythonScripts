list2 = [5,6,7,'eight',9.0] 
list1=[1,'two',3.0,[4,5,6],list2]

print (list1)
print (list2)
print(list1[3][2])  #should return 6   
print(list1[4][2])  #should return 7
print(list1[4][3][2])   #should return g

list2[3] = 'eighty'
print (list2)
list1[4][3]='ninety'
print (list2)

q1=[1,2,3]
q2=q1
q1[2]="oops"
print(q1)
print(q2)

a=3
q=[1,2,a]
a=4
print(q)
print (list1)
print (list1[::-1])

list1.append('ten')
list1.reverse()
print (list1)   
list1.remove(1)
print (list1)   
list1.pop()
print (list1)
list3=[3,5,1,7,4,8,3,9,2,6  ]

list4=sorted(list3,reverse=True)
print (list4)

list3.sort()
print (list3)

s='Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec'
print(s.split(', '))

print(list ('hello'))  #should return ['h', 'e', 'l', 'l', 'o']

a=[5,4,3,2,1]
b=a
print (b is a)
print (b == a)
