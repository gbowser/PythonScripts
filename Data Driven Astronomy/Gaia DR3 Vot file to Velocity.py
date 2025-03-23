# https://docs.astropy.org/en/stable/io/votable/index.html
#  https://docs.astropy.org/en/stable/table/mixin_columns.html


# https://clustertools.readthedocs.io/en/latest/
# https://clustertools.readthedocs.io/en/latest/cluster.html#the-starcluster-class


import clustertools as ctools
import matplotlib.pyplot as plt
import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import QTable, Table

thiscluster = "Pl"


dir_export = "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/Kinematics/"

Pl_dir_import = (
    "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/Pleaides Membership/"
)
Pl_file_import = "Pleiades-2025-02-17.vot.gz"

Hy_dir_import = "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/Kinematics/"
Hy_file_import = "Hyades Velocity Colour Position.vot.gz"


if thiscluster == "Pl":
    file_import = Pl_file_import
    dir_import = Pl_dir_import
else:
    file_import = Hy_file_import
    dir_import = Hy_dir_import


qt = QTable.read(dir_import + file_import)

# put in zero values for x,y,z, vx,vy, vz
qt.add_column(0.0 * u.pc, name="py_x")
qt.add_column(0.0 * u.pc, name="py_y")
qt.add_column(0.0 * u.pc, name="py_z")

qt.add_column(0.0 * u.pc, name="distance")

# Add column of all zero km/s to end of table

qt.add_column(0.0 * u.km / u.second, name="py_vx")
qt.add_column(0.0 * u.km / u.second, name="py_vy")
qt.add_column(0.0 * u.km / u.second, name="py_vz")

qt["distance"] = qt["parallax"].to(u.parsec, equivalencies=u.parallax())


sc = SkyCoord(
    ra=qt["ra"],
    dec=qt["dec"],
    distance=qt["distance"],
    pm_ra_cosdec=qt["pmra"],
    pm_dec=qt["pmdec"],
    radial_velocity=(qt["radial_velocity"]),
    frame="icrs")

 
# compute cartesian co-ords and put in table

qt["py_x"] = sc.cartesian.x
qt["py_y"] = sc.cartesian.y
qt["py_z"] = sc.cartesian.z

# now velocities

qt["py_vx"] = sc.velocity.d_x.to(u.km / u.s)
qt["py_vy"] = sc.velocity.d_y.to(u.km / u.s)
qt["py_vz"] = sc.velocity.d_z.to(u.km / u.s)


if thiscluster == "Pl":
    file_export = "Pleiades_Veloc_2025-02-17.csv"
else:
    file_export = "Hyades_Veloc.csv"


qt.write(dir_export + file_export, overwrite=True)
arr = np.array(qt)
print(arr)


print(qt)
