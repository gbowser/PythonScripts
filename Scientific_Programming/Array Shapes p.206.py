import numpy as np

a = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) # these are lists so mutable   , this is preferred
b = np.array(((1, 2, 3), (4, 5, 6), (7, 8, 9))) # these are tupes, so immutable

c=a.flatten()   ##creates and independent flattened copy of a
d=b.flatten()   ##creates and independent flattened copy of b
print(f"a (lists) and flattened version of a\n{a}\n{c}\n")
print(f"b (tuples) and flattened version of a\n{b}\n{d}\n")

a=np.linspace(1.,4.,4)
b=a.reshape(2,2)
print(f"linspace(1,4,4) \n{a}\n")
print(f"reshaped to 2x2 \n{b}\n")

print(f"\ntransposed \n{b.transpose()}")
