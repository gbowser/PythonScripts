import matplotlib.pyplot as plt
import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord, Distance
from astropy.table import QTable
from astroquery.gaia import Gaia
import astropy.units as u
from astropy.constants import G, h, k_B
from astropy.visualization import quantity_support


Gaia.ROW_LIMIT = 10000  # Set the row limit for returned data

ngc188_center = SkyCoord(12.11 * u.deg, 85.26 * u.deg)
print(f"NGC 188 Center: {ngc188_center}")

Reff = 29 * u.pc

print(f"Half light radius value: {Reff.value} unit: {Reff.unit}")
print(f"{Reff.to(u.m):.3g}")

vmean = 206
sigin = 4.3
v = np.random.normal(vmean, sigin, 500) * u.km / u.s

print(f"First 10 radial velocity measurements: \n{v[:10]}\n{v.to(u.m / u.s)[:10]}")

plt.figure()
plt.hist(v, bins="auto", histtype="step")
plt.ylabel("N")
plt.xlabel("Radial Velocity (km/s)")
plt.show()


d = 250 * u.pc
Tex = 25 * u.K
# Cloud's center
cen_ra = 52.25 * u.deg
cen_dec = 0.25 * u.deg
cen_v = 15 * u.km / u.s

# Cloud's size
sig_ra = 3 * u.arcmin
sig_dec = 4 * u.arcmin
sig_v = 3 * u.km / u.s

# 1D coordinate quantities
ra = np.linspace(52, 52.5, 100) * u.deg
dec = np.linspace(0, 0.5, 100) * u.deg
v = np.linspace(0, 30, 300) * u.km / u.s

# this creates data cubes of size for each coordinate based on the dimensions of the other coordinates
ra_cube, dec_cube, v_cube = np.meshgrid(ra, dec, v)

data_gauss = np.exp(
    -0.5 * ((ra_cube - cen_ra) / sig_ra) ** 2
    + -0.5 * ((dec_cube - cen_dec) / sig_dec) ** 2
    + -0.5 * ((v_cube - cen_v) / sig_v) ** 2
)
data = data_gauss * u.K
# Average pixel size
# This is only right if dec ~ 0, because of the cos(dec) factor.
dra = (ra.max() - ra.min()) / len(ra)
ddec = (dec.max() - dec.min()) / len(dec)

# Average velocity bin width
dv = (v.max() - v.min()) / len(v)
print(
    """dra = {0}
ddec = {1}
dv = {2}""".format(dra.to(u.arcsec), ddec.to(u.arcsec), dv)
)
intcloud = np.sum(data * dv, axis=2)
intcloud.unit

# Note that we display RA in the convential way by going from max to min
plt.imshow(
    intcloud.value,
    origin="lower",
    extent=[ra.value.max(), ra.value.min(), dec.value.min(), dec.value.max()],
    cmap="hot",
    interpolation="nearest",
    aspect="equal",
)
plt.colorbar().set_label("Intensity ({})".format(intcloud.unit))
plt.xlabel("RA (deg)")
plt.ylabel("Dec (deg)")
plt.show()
