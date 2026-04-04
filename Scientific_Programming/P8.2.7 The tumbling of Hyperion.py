import numpy as np
from matplotlib import pyplot as plt
from scipy.integrate import solve_ivp

# The orbital eccentricity, e, and (B-A)/C for Hyperion
e, BmAoC = 0.1, 0.265

# Anonymous function for calculating a/r as a function of true anomaly, phi
a_over_r = lambda phi: (1 + e * np.cos(phi)) / (1 - e**2)


def deriv(phi, z):
    """
    Given z = Omega, theta, calculate and return the derivatives,
    dOmega/dphi and dtheta/dphi.

    """

    Omega, theta = z
    aor = a_over_r(phi)
    theta_d = aor**-2 * Omega
    Omega_d = -BmAoC * 3 / 2 / (1 - e**2) * aor * np.sin(2 * (theta - phi))
    return Omega_d, theta_d


fig, axes = plt.subplots(nrows=2, ncols=1)

# Different pairs of initial conditions.
z0 = [(0, 0), (2, 0)]
phimax = [100, 400]

for i in range(2):
    soln = solve_ivp(deriv, (0, phimax[i]), z0[i], dense_output=True)
    phi = np.linspace(0, phimax[i], 1000)
    Omega, theta = soln.sol(phi)
    axes[i].plot(phi, Omega)
    axes[i].set_xlabel(r"$\phi$")
    axes[i].set_ylabel(r"$\Omega$")

fig.tight_layout()
plt.show()