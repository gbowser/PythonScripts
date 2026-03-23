# section 6.1.8 Min and Max p216
import numpy as np

a=np.array([[3,5,1,-4],[4,3,6,-9],[-7,3,1,0]])

print(f"{a}")

print(f"max of a is {a.max()} and min of a is {a.min()}")

print(f"\nmax of each column is {a.max(axis=0)} and min of each column is {a.min(axis=0)}")
print(f"\nmax of each row is {a.max(axis=1)} and min of each row is {a.min(axis=1)}")
print(f"\nmax of 1st row is {a[0].max()} and min of 1st row is {a[0].min()}")
print(f"\nmax of 2nd column is {a[:,1].max()} and min of 2nd column is {a[:,1].min()}")