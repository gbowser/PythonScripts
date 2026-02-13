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