import numpy as np
import matplotlib.pyplot as plt

# Parameters
mu = 0.0
sigmas = np.array([0.5, 1.0, 1.5])   # shape (3,)
x = np.linspace(-10, 10, 1000)       # shape (1000,)
h = x[1] - x[0]                      # suitable small step from the grid spacing

# Reshape for broadcasting
# x_col has shape (1000, 1)
# sig_row has shape (1, 3)
x_col = x[:, np.newaxis]
sig_row = sigmas[np.newaxis, :]

# Gaussian functions:
# result g has shape (1000, 3)
g = (1 / (sig_row * np.sqrt(2 * np.pi))) * np.exp(-((x_col - mu) ** 2) / (2 * sig_row ** 2))

# Verify normalization by direct summation
# area ≈ sum(g)*dx for each sigma
dx = x[1] - x[0]
areas = np.sum(g, axis=0) * dx

print("Approximate areas under each Gaussian:")
for s, area in zip(sigmas, areas):
    print(f"sigma = {s:.1f}, area = {area:.6f}")

# First derivative using central difference approximation
# g'(x) ≈ [g(x+h) - g(x-h)] / (2h)
# Since x is already on a uniform grid, this becomes:
g_prime = (g[2:, :] - g[:-2, :]) / (2 * h)
x_prime = x[1:-1]   # derivative values correspond to interior points

# Plot Gaussian functions
plt.figure(figsize=(9, 5))
plt.plot(x, g[:, 0], label=r'$\sigma=0.5$')
plt.plot(x, g[:, 1], label=r'$\sigma=1.0$')
plt.plot(x, g[:, 2], label=r'$\sigma=1.5$')
plt.xlabel("x")
plt.ylabel(r"$g(x)$")
plt.title("Normalized Gaussian Functions")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()

# Plot first derivatives
plt.figure(figsize=(9, 5))
plt.plot(x_prime, g_prime[:, 0], label=r"$\sigma=0.5$")
plt.plot(x_prime, g_prime[:, 1], label=r"$\sigma=1.0$")
plt.plot(x_prime, g_prime[:, 2], label=r"$\sigma=1.5$")
plt.xlabel("x")
plt.ylabel(r"$g'(x)$")
plt.title("First Derivatives of the Gaussian Functions")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()