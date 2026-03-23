#use list comprehension to generate the Trace of a Matrix  (sum of the diagonal elements)

A=[[1,2,3],[4,5,6],[7,8,9]]
trace=sum(A[i][i] for i in range(len(A)))
print(f"Trace of A is {trace}")
