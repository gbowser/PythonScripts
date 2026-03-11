# compute arithmetic geometric mean AGM of 2 positive numbers a and b


import math

def agm(x, y, tol=1e-12, max_iter=1000):
    """
    Compute the arithmetic-geometric mean of two positive real numbers x and y.
    
    Parameters:
        x, y      : positive real numbers
        tol       : stopping tolerance
        max_iter  : maximum number of iterations
    
    Returns:
        The AGM of x and y
    """
    if x <= 0 or y <= 0:
        raise ValueError("x and y must both be positive real numbers")

    a = x
    b = y

    for _ in range(max_iter):
        a_next = 0.5 * (a + b)
        b_next = math.sqrt(a * b)

        if abs(a_next - b_next) < tol:
            return a_next

        a, b = a_next, b_next

    return a


# Example: Gauss's constant G = 1 / agm(1, sqrt(2))
G = 1 / agm(1, math.sqrt(2))
print("Gauss's constant G =", G)



def agm2(x, y):
    a = x
    b = y

    while abs(a - b) > 1e-12:
        a_next = (a + b) / 2
        b_next = math.sqrt(a * b)
        a = a_next
        b = b_next

    return a


# Example: Gauss's constant
G = 1 / agm2(1, math.sqrt(2))
print("Gauss constant =", G)