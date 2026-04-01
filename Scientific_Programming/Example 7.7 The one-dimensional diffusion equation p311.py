import matplotlib.pyplot as plt
import numpy as np

# Cross sectional area of bar in m3, heat added at x=0 in J
A, H = 1.0e-4, 1.0e3
# Temperature in K at t=0
theta0 = 300

# Metal element symbol, specific heat capacities per unit volume (J.m-3.K-1),
# Thermal diffusivities (m2.s-1) for Cu and Fe
metals = np.array(
    [("Cu", 3.45e7, 1.11e-4), ("Fe", 3.50e7, 2.3e-5)],
    dtype=[("symbol", "U2"), ("cp", "f8"), ("D", "f8")],
)

# The metal bar extends from -xlim to xlim (m)
xlim, nx = 0.05, 1000
x = np.linspace(-xlim, xlim, nx)

# Calculate the temperature distribution at these three times
times = (1e-2, 0.1, 1)
# Create our subplots: three rows of times, one column for each metal
fig, axes = plt.subplots(nrows=3, ncols=2, figsize=(7, 8))
for j, t in enumerate(times):
    for i, metal in enumerate(metals):
        symbol, cp, D = metal
        ax = axes[j, i]
        # The solution to the diffusion equation
        theta = theta0 + H / cp / A / np.sqrt(D * t * 4 * np.pi) * np.exp(
            -(x**2) / 4 / D / t
        )
        # Plot, converting distances to cm and add some labelling
        ax.plot(x * 100, theta, "k")
        ax.set_title(f"{symbol}, $t={t}$ s")

        ax.set_xlim(-4, 4)
        ax.set_xlabel(r"$x\;/\mathrm{cm}$")
        ax.set_ylabel(r"$\Theta\;/\mathrm{K}$")

# Set up the y axis so that each metal has the same scale at the same t
for j in (0, 1, 2):
    ymax = max(axes[j, 0].get_ylim()[1], axes[j, 1].get_ylim()[1])
    print(axes[j, 0].get_ylim(), axes[j, 1].get_ylim())
    for i in (0, 1):
        ax = axes[j, i]
        ax.set_ylim(theta0, ymax)
        # Ensure there are only three y-tick marks
        ax.set_yticks([theta0, (ymax + theta0) / 2, ymax])
# We don't want the subplots to bash into each other: tight_layout() fixes this
fig.tight_layout()
plt.show()
