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
R_kpc = np.linspace(0.5, 30.0, 400)  # avoid R=0
z_kpc = 0.0

# ============================================================
# OPTION A: galpy (MWPotential2014)
# ============================================================
try:
    from galpy.potential import MWPotential2014, evaluatePotentials
    from galpy.util import bovy_conversion

    # galpy works in dimensionless units (R in units of ro, velocities in vo)
    ro = 8.2   # kpc (set this to what you use)
    vo = 232.0 # km/s (set this to what you use)

    R_galpy = R_kpc / ro
    z_galpy = np.zeros_like(R_galpy) + (z_kpc / ro)

    # Dimensionless Φ (per unit mass) in units of vo^2
    Phi_dimless = np.array([evaluatePotentials(MWPotential2014, R, z)
                            for R, z in zip(R_galpy, z_galpy)])

    # Convert to physical units: (km/s)^2
    Phi_kms2 = Phi_dimless * vo**2

    # You can also convert to SI J/kg by multiplying by (1000 m/s)^2:
    Phi_Jperkg = Phi_kms2 * (1000.0**2)

    plt.figure()
    plt.plot(R_kpc, Phi_kms2)
    plt.xlabel("Galactocentric radius R [kpc]")
    plt.ylabel(r"Gravitational potential $\Phi(R, z=0)$ [$(\mathrm{km/s})^2$]")
    plt.title(r"Milky Way potential (galpy MWPotential2014) at $z=0$")
    plt.grid(True)
    plt.show()

    # If you prefer J/kg:
    plt.figure()
    plt.plot(R_kpc, Phi_Jperkg)
    plt.xlabel("Galactocentric radius R [kpc]")
    plt.ylabel(r"Gravitational potential $\Phi(R, z=0)$ [J/kg]")
    plt.title(r"Milky Way potential (galpy MWPotential2014) at $z=0$")
    plt.grid(True)
    plt.show()

except ImportError as e:
    print("galpy not installed (or import failed). Error:", e)
    print("Try OPTION B (gala) below, or install galpy: pip install galpy")

# ============================================================
# OPTION B: gala (MilkyWayPotential)
# ============================================================
# Uncomment this block if you prefer gala and have it installed.
"""
import astropy.units as u
from gala.potential import MilkyWayPotential

pot = MilkyWayPotential()

R = R_kpc * u.kpc
z = np.zeros_like(R_kpc) * u.kpc

# gala returns potential energy per unit mass; usually in (km/s)^2
Phi = pot.energy([R, z, 0*R])  # 3D positions (R, z, phi-like), but gala expects Cartesian in many contexts
# If the above line errors, use Cartesian positions instead:
# x = R; y = 0; z = 0
# Phi = pot.energy([x, 0*x, 0*x])

plt.figure()
plt.plot(R_kpc, Phi.to((u.km/u.s)**2).value)
plt.xlabel("Galactocentric radius R [kpc]")
plt.ylabel(r"Gravitational potential $\Phi(R, z=0)$ [$(\mathrm{km/s})^2$]")
plt.title(r"Milky Way potential (gala) at $z=0$")
plt.grid(True)
plt.show()
"""
