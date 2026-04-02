"""
Plot Milky Way gravitational potential Φ(R, z=0) versus Galactocentric radius R.

This script gives you TWO options:
  A) galpy (recommended if you already use it)
  B) gala (also popular; depends on astropy units)

Run one option (comment the other).
"""

import numpy as np
import matplotlib.pyplot as plt

# -------------------------------
# Choose radius grid (kpc)
# -------------------------------
R_kpc = np.linspace(0.5, 10.0, 400)  # avoid R=0
z_kpc_values = [0.0, 0.5, 1.0]

# ============================================================
# OPTION A: galpy (MWPotential2014)
# ============================================================
from galpy.potential import MWPotential2014, evaluatePotentials

# galpy works in dimensionless units (R in units of ro, velocities in vo)
ro = 8.2   # kpc (set this to what you use)
vo = 232.0 # km/s (set this to what you use)

R_galpy = R_kpc / ro
fig, ax = plt.subplots(figsize=(8, 5))
for z_kpc in z_kpc_values:
    z_galpy = np.zeros_like(R_galpy) + (z_kpc / ro)

    # Dimensionless Φ (per unit mass) in units of vo^2
    Phi_dimless = np.array(
        [evaluatePotentials(MWPotential2014, R, z) for R, z in zip(R_galpy, z_galpy)]
    )

    # Convert to physical units: (km/s)^2, then scale to thousands
    Phi_kms2_thousands = (Phi_dimless * vo**2) / 1000.0
    ax.plot(R_kpc, Phi_kms2_thousands, label=f"z={z_kpc:g} kpc")

ax.set_xlabel("Galactocentric radius R [kpc]")
ax.set_ylabel("Gravitational potential [10^3 (km/s)^2]", labelpad=10)
ax.set_title("Milky Way potential (galpy MWPotential2014)")
ax.grid(True)
ax.legend()
fig.tight_layout()
plt.show()

