# https://docs.astropy.org/en/stable/io/votable/index.html
#  https://docs.astropy.org/en/stable/table/mixin_columns.html


# https://clustertools.readthedocs.io/en/latest/
# https://clustertools.readthedocs.io/en/latest/cluster.html#the-starcluster-class

import math
import clustertools as ctools
import matplotlib.pyplot as plt
import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.visualization import quantity_support
from astropy.table import QTable, Table

thiscluster = "Hy"
quantity_support()


Pl_dir_import = (
    "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/Pleaides Membership/"
)
Pl_file_import = "Brandner 2023 vizier_votable.vot"

Hy_dir_import = (
    "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/Hyades Membership/"
)
Hy_file_import = "Brandner 2023.vot"


if thiscluster=="Pl":
    file_import = Pl_file_import
    dir_import = Pl_dir_import
else:
    file_import = Hy_file_import
    dir_import = Hy_dir_import  


# Use QTable


qt = QTable.read(dir_import + file_import)

# put in zero values for x,y,z, vx,vy, vz
qt.add_column(0.0 * u.pc, name="x")
qt.add_column(0.0 * u.pc, name="y")
qt.add_column(0.0 * u.pc, name="z")

# Add column of all zero km/s to end of table

qt.add_column(0.0 * u.km / u.second, name="vx")
qt.add_column(0.0 * u.km / u.second, name="vy")
qt.add_column(0.0 * u.km / u.second, name="vz")
qt.add_column(0.0 * u.pc, name="dist_centre")




# compute cartesian co-ords and put in table
qt["x"] = SkyCoord(
    ra=(qt["RA_ICRS"]), dec=(qt["DE_ICRS"]), distance=(qt["dpgeo"]), frame="icrs"
).cartesian.x

qt["y"] = SkyCoord(
    ra=(qt["RA_ICRS"]), dec=(qt["DE_ICRS"]), distance=(qt["dpgeo"]), frame="icrs"
).cartesian.y

qt["z"] = SkyCoord(
    ra=(qt["RA_ICRS"]), dec=(qt["DE_ICRS"]), distance=(qt["dpgeo"]), frame="icrs"
).cartesian.z

# add column dist from centre
# qt["dist_centre"] =math.sqrt(qt["x"]**2+qt["y"]**2+qt["z"]**2)


qt["Mass"] = qt["Mass"].astype(np.float64)
# =========================================================================================================

# Use Table (no quantities)
t = Table.read(dir_import + file_import)
# put in zero values for x,y,z, vx,vy, vz
t.add_column(0.0, name="x")
t.add_column(0.0, name="y")
t.add_column(0.0, name="z")

# Add column of all zero km/s to end of table
t.add_column(0.0, name="vx")
t.add_column(0.0, name="vy")
t.add_column(0.0, name="vz")
t.add_column(0.0 * u.pc, name="dist_centre")

# compute cartesian co-ords and put in table
t["x"] = SkyCoord(
    ra=(qt["RA_ICRS"]), dec=(qt["DE_ICRS"]), distance=(qt["dpgeo"]), frame="icrs"
).cartesian.x

t["y"] = SkyCoord(
    ra=(qt["RA_ICRS"]), dec=(qt["DE_ICRS"]), distance=(qt["dpgeo"]), frame="icrs"
).cartesian.y

t["z"] = SkyCoord(
    ra=(qt["RA_ICRS"]), dec=(qt["DE_ICRS"]), distance=(qt["dpgeo"]), frame="icrs"
).cartesian.z

# add column dist from centre
t["dist_centre"] =math.sqrt(t["x"]**2+t["y"]**2+t["z"]**2)



# convert Mass to Float64 required for clustertools
t["Mass"] = t["Mass"].astype(np.float64)
# ============================================================================================================'

qt["RA_ICRS"][qt["RA_ICRS"]>180*u.deg]-=360*u.deg

plt.scatter(qt["RA_ICRS"],qt["DE_ICRS"],marker=".")

plt.show()

