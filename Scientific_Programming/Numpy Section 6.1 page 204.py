import numpy as np

a=np.array(((1,2),(3,4)))
b=a
print(f"array elementwise multiplication\n{a*b}")
print(f"array matrix multiplication\n{a@b}")

#creating a magic square
N=5
magic_square=np.zeros(((N,N)), dtype=int)

n=1
i,j = 0,N//2   #floor division, divide by 2 and round down.

while n<=N**2:
    magic_square[i,j]=n
    n+=1
    newi, newj = (i-1)%N, (j+1)%N   # % operator is modulo, remainder after division
    if magic_square[newi,newj]:     # checks whether the next proposed square is already filled.
        i+=1
    else:
        i,j=newi,newj

print(f"The magic square is\n {magic_square}")

#transpose this
print(f"The transposed magic square is\n {magic_square.transpose()}")



