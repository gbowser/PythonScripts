import numpy as np
import matplotlib.pyplot as plt
from math import isqrt

# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

def is_prime(n: int) -> bool:
    """Return True if n is an ordinary prime number."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for k in range(3, isqrt(n) + 1, 2):
        if n % k == 0:
            return False
    return True


def is_gaussian_prime(x: int, y: int) -> bool:
    """
    Return True if x + iy is a Gaussian prime.

    A Gaussian integer x + iy is Gaussian prime if either:
      1) one of x,y is zero and abs(the other) is an ordinary prime that is 3 more than a multiple of 4
      2) both x,y are nonzero and x^2 + y^2 is an ordinary prime
    """
    # Case 1: one part is zero
    if x == 0 and y != 0:
        return is_prime(abs(y)) and abs(y) % 4 == 3
    if y == 0 and x != 0:
        return is_prime(abs(x)) and abs(x) % 4 == 3

    # Case 2: both nonzero
    if x != 0 and y != 0:
        return is_prime(x*x + y*y)

    # 0 + 0i is not prime
    return False


# ------------------------------------------------------------
# Spiral generator
# ------------------------------------------------------------

def gaussian_spiral(x0=5, y0=23, n_steps=500):
    """
    Generate the Gaussian prime spiral path.

    Starts at x0 + i y0
    Initial direction: +x
    Turn left whenever current lattice point is a Gaussian prime.
    """
    # Directions in order: right, up, left, down
    directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    direction_index = 0  # start moving in +x direction

    x, y = x0, y0
    xs = [x]
    ys = [y]

    for _ in range(n_steps):
        # If current position is Gaussian prime, turn left
        if is_gaussian_prime(x, y):
            direction_index = (direction_index + 1) % 4

        dx, dy = directions[direction_index]
        x += dx
        y += dy

        xs.append(x)
        ys.append(y)

    return np.array(xs), np.array(ys)


# ------------------------------------------------------------
# Main plot
# ------------------------------------------------------------

# Number of steps to draw
N = 1000

x_path, y_path = gaussian_spiral(x0=5, y0=23, n_steps=N)

plt.figure(figsize=(8, 8))
plt.plot(x_path, y_path, linewidth=1.2)
plt.scatter([x_path[0]], [y_path[0]], s=60, label='Start: 5 + 23i')
plt.scatter([x_path[-1]], [y_path[-1]], s=60, label='End')

plt.xlabel('Real part')
plt.ylabel('Imaginary part')
plt.title(f'Gaussian Prime Spiral ({N} steps)')
plt.axis('equal')
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()
