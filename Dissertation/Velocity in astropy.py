# https://docs.astropy.org/en/stable/io/votable/index.html
#  https://docs.astropy.org/en/stable/table/mixin_columns.html


# https://clustertools.readthedocs.io/en/latest/
# https://clustertools.readthedocs.io/en/latest/cluster.html#the-starcluster-class

import matplotlib.pyplot as plt
import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import QTable, Table
from astropy.coordinates import (CartesianRepresentation, CartesianDifferential)


myvalue = (0.8 * u.arcsec).to(u.parsec, equivalencies=u.parallax())
print(myvalue)

sc = SkyCoord(1*u.deg, 2*u.deg, radial_velocity=20*u.km/u.s)
print(sc)
print(sc.radial_velocity)


my_ra=30*u.deg
my_dec=30*u.deg
my_dist=100*u.parsec
my_rv=20*u.km/u.s
my_pmra= 50*u.mas/u.yr
my_pmdec= 20*u.mas/u.yr

sc=SkyCoord(ra=my_ra,dec=my_dec,distance = my_dist, pm_ra_cosdec=my_pmra,pm_dec=my_pmdec, frame="icrs")


print(sc.cartesian.x )

vx, vy, vz = sc.velocity.d_x.to(u.km/u.s), sc.velocity.d_y.to(u.km/u.s), sc.velocity.d_z.to(u.km/u.s)

vx, vy, vz = sc.velocity.d_x.to(u.km/u.s), sc.velocity.d_y.to(u.km/u.s), sc.velocity.d_z.to(u.km/u.s)

print(vx,vy,vz)

sc = SkyCoord(
    ra=qt["ra"],
    dec=qt["dec"],
    distance=qt["distance"],
    pm_ra_cosdec=qt["pmra"],
    pm_dec=["pmdec"],
    radial_velocity=(qt["radial_velocity"]),
    frame="icrs",
)

