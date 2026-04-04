# astropy imports
import astropy.coordinates as coord
from astropy.table import QTable
import astropy.units as u

# Third-party imports
import matplotlib.pyplot as plt
import numpy as np
from galpy.orbit import Orbit
from galpy.potential import MWPotential2014


# Use physical units so galpy interprets the orbit near the Sun correctly.
# These values give a mildly eccentric orbit with a little vertical motion.
orbit = Orbit(
    vxvv=[
        8.2 * u.kpc,
        35.0 * u.km / u.s,
        190.0 * u.km / u.s,
        0.15 * u.kpc,
        25.0 * u.km / u.s,
        0.0 * u.deg,
    ],
    ro=8.2,
    vo=220.0,
)

# Integrate for 2 Gyr with enough points to show the orbit clearly.
ts = np.linspace(0.0, 2.0, 1000) * u.Gyr
orbit.integrate(ts, MWPotential2014)

print("First 5 R values (kpc):", orbit.R(ts[:5]))
print("First 5 z values (kpc):", orbit.z(ts[:5]))

fig, axes = plt.subplots(1, 2, figsize=(11, 5))

axes[0].plot(orbit.x(ts), orbit.y(ts), color="tab:blue")
axes[0].set_xlabel("x / kpc")
axes[0].set_ylabel("y / kpc")
axes[0].set_title("Face-on Galactic orbit")
axes[0].set_aspect("equal")
axes[0].grid(alpha=0.3)

axes[1].plot(orbit.R(ts), orbit.z(ts), color="tab:orange")
axes[1].set_xlabel("R / kpc")
axes[1].set_ylabel("z / kpc")
axes[1].set_title("Radial and vertical motion")
axes[1].grid(alpha=0.3)

plt.show()

