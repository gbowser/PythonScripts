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


Pl_dir_import = (
    "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/Pleaides Membership/"
)
Pl_file_import = "Brandner 2023 vizier_votable.vot"

Hy_dir_import = (
    "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/Hyades Membership/"
)
Hy_file_import = "Brandner 2023.vot"


if thiscluster == "Pl":
    file_import = Pl_file_import
    dir_import = Pl_dir_import
else:
    file_import = Hy_file_import
    dir_import = Hy_dir_import


def Centre_of_Mass(t):
    arr_mass = np.array([t["Mass"]])
    total_c_mass = np.sum(arr_mass)
    wtd_x = (np.sum(np.multiply(np.array([t["x"]]), arr_mass))) / total_c_mass
    wtd_y = (np.sum(np.multiply(np.array([t["y"]]), arr_mass))) / total_c_mass
    wtd_z = (np.sum(np.multiply(np.array([t["z"]]), arr_mass))) / total_c_mass
    CoM = (wtd_x, wtd_y, wtd_z)
    print(CoM)
    return CoM


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

# convert Mass to Float64 required for clustertools
t["Mass"] = t["Mass"].astype(np.float64)
# ============================================================================================================'


CoM = Centre_of_Mass(t)
print("Centre of Mass using GB calc = ", CoM)

cluster = ctools.StarCluster(units="pckms", origin="galaxy")
for i in range(0, len(t) - 1):
    cluster.add_stars(
        x=t["x"][i],
        y=t["y"][i],
        z=t["z"][i],
        vx=t["vx"][i],
        vy=t["vy"][i],
        vz=t["vz"][i],
        m=t["Mass"][i],
        id=i,
        m0=None,
        npop=None,
    )

cluster.analyse()

print("ClusterTools Results")
print("Mean radius with numpy = ", np.mean(cluster.r))
print("Mean radius = ", cluster.rmean)
print("Half mass radius =", cluster.rm)
print("Cluster Centre of Mass = ", cluster.find_centre())

ctools.skyplot(cluster)
plt.show()


# It is also possible to easily measure the mass function and its slope within a given mass range
m_mean, m_hist, dm, alpha, ealpha, yalpha, eyalpha = ctools.mass_function(
    cluster, mmin=0.0001, mmax=4.0, plot=True
)
plt.show()

#  globular cluster’s density profile, with rho_prof returning the radial bin locations, the density within each bin, and the number of stars
rprof, pprof, nprof = ctools.rho_prof(cluster, plot=True)
plt.show()


print("completed")


print(t)
# export this table

t.write(dir_import + "values_hyades.dat", format="ascii", overwrite=True)
arr = np.array(t)
print(arr)
# Now start building the cluster

# C:\Users\gordo\anaconda3\Lib\site-packages\clustertools

# m,x,y,z,vx,vy,vz=np.loadtxt(dir_import+'values2.csv',delimiter=',', unpack=True)
# cm = {"m": "Mass", "x": "x", "y": "y", "z": "z", "vx": "vx", "xy": "vy", "vz": "vz"}
# cluster = ctools.load_cluster(ctype="astropy_table", particles=t, units="pckms", origin="galaxy", column_mapper=cm,ofile=None)
