import numpy as np
a=np.array( (100,101,102,103) )
print(f"{a}")

b=np.array ([[1.,2.],[3.,4.]] )
print(f"\n{b}")

print(b[0,1])

# move all to floating point
c=np.array([[1.1,2],[1,1.0112e2]])
print(c)

d= np.array([0+4j,1-2j], dtype=complex)
print(f"\ncomplex number : {d}")

e=np.empty((2,2))
print(f"empty array : {e}")

e=np.zeros((3,2))
print(f"zero array : \n{e}")

a=np.arange(7)
print(f"\narange params 7 {a}")

b= np.arange(1.5,4,0.3)
print(
    "\nnp range with params start = 1.5, end = 5, step = 0.3 "
    f"{np.array2string(b, formatter={'float_kind': lambda x: f'{x:.1f}'})}\n"
)
print(f"previous version: {b}\n")

x,dx=np.linspace(0,2*np.pi,20,retstep=True)
print(f"linspace array {x}, step {dx}")


def f(i,j):
        return 2*i*j

b=np.fromfunction(f,(4,3))
print(f"from function array \n{b}")

#page 200
c=np.array(((1,0,1),(0,1,0)))
print(f"shape of array {c.shape}")
print(f"count of elements of array {c.size}")
