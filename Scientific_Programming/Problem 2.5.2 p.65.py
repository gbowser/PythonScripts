# P2.5.2
#
# The iterative weak acid approximation determines the hydrogen ion
# concentration [H+] of an acid solution from the acid dissociation
# constant Ka and the acid concentration c by successive application
# of the formula
#
#     [H+]_(n+1) = sqrt( Ka * ( c - [H+]_n ) )
#
# starting with
#
#     [H+]_0 = 0
#
# The iterations are continued until [H+] changes by less than some
# predetermined small tolerance value.
# Use this method to determine the hydrogen ion concentration and
# hence the pH:
#     pH = -log10([H+])
# for a solution with:
#     c  = 0.01 M          (acetic acid concentration)
#     Ka = 1.78e-5         (acid dissociation constant)
# Use the tolerance:
#     TOL = 1e-10
# Your program should iterate until:
#     |H_new - H_old| < TOL
# Then compute the final pH.

import math

def iterative_weak_acid_approximation(c, Ka, tol=1e-10):
    H_old = 0.0
    H_new = math.sqrt(Ka * (c - H_old))
    
    while abs(H_new - H_old) >= tol:
        H_old = H_new
        H_new = math.sqrt(Ka * (c - H_old))
    
    return H_new

print(f"Hydrogen ion concentration: {iterative_weak_acid_approximation(0.01, 1.78e-5):.2e} M")
pH = -math.log10(iterative_weak_acid_approximation(0.01, 1.78e-5))
print(f"pH of the solution: {pH:.2f}")