# https://docs.astropy.org/en/stable/io/votable/index.html
#  https://docs.astropy.org/en/stable/table/mixin_columns.html


# https://clustertools.readthedocs.io/en/latest/
# https://clustertools.readthedocs.io/en/latest/cluster.html#the-starcluster-class


# https://gea.esac.esa.int/archive/


import clustertools as ctools
import matplotlib.pyplot as plt
import numpy as np
from astropy import units as u
import astropy.coordinates as coord
from astropy.coordinates import SkyCoord
from astropy.table import QTable, Table

dir_import = "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/Kinematics/2025-03-11/"

file_import = "Pleiades-2025-02-17.vot.gz"


# Use QTable

qt = QTable.read(dir_import + file_import)

# put in zero values for x,y,z, vx,vy, vz
qt.add_column(0.0 * u.pc, name="distance")
qt.add_column(0.0 * u.pc, name="x")
qt.add_column(0.0 * u.pc, name="y")
qt.add_column(0.0 * u.pc, name="z")

qt.add_column(0.0 * u.pc, name="x0")
qt.add_column(0.0 * u.pc, name="y0")
qt.add_column(0.0 * u.pc, name="z0")

# Add column of all zero km/s to end of table
qt.add_column(0.0 * u.km / u.second, name="v_x")
qt.add_column(0.0 * u.km / u.second, name="v_y")
qt.add_column(0.0 * u.km / u.second, name="v_z")

qt["distance"] = qt["parallax"].to(u.parsec, equivalencies=u.parallax())


# https://docs.astropy.org/en/stable/coordinates/velocities.html
# https://docs.astropy.org/en/stable/generated/examples/coordinates/plot_galactocentric-frame.html


qt["radial_velocity"] = qt["radial_velocity"].filled(np.average(qt["radial_velocity"]))


c1 = SkyCoord(
    ra=qt["ra"],
    dec=qt["dec"],
    distance=qt["distance"],
    pm_ra_cosdec=0 * u.mas / u.yr,
    pm_dec=0 * u.mas/u.yr,                               
    radial_velocity=1 * u.km / u.second,
)

gc1 = c1.transform_to(coord.Galactocentric)

# compute cartesian co-ords and put in table
qt["x"] = SkyCoord(
    ra=(qt["ra"]), dec=(qt["dec"]), distance=(qt["distance"]), frame="icrs"
).cartesian.x
qt["y"] = SkyCoord(
    ra=(qt["ra"]), dec=(qt["dec"]), distance=(qt["distance"]), frame="icrs"
).cartesian.y
qt["z"] = SkyCoord(
    ra=(qt["ra"]), dec=(qt["dec"]), distance=(qt["distance"]), frame="icrs"
).cartesian.z

qt["v_x"] = gc1.v_x
qt["v_y"] = gc1.v_y
qt["v_z"] = gc1.v_z



# export file
qt.write(dir_import + "Pl_RV.dat", format="ascii", overwrite=True)


# =========================================================================================================

# Use Table (no quantities)
t = Table.read(dir_import + file_import)
# put in zero values for x,y,z, vx,vy, vz
t.add_column(0.0, name="x")
t.add_column(0.0, name="y")
t.add_column(0.0, name="z")

t.add_column(0.0, name="x0")
t.add_column(0.0, name="y0")
t.add_column(0.0, name="z0")


# Add column of all zero km/s to end of table
t.add_column(0.0, name="v_x")
t.add_column(0.0, name="v_y")
t.add_column(0.0, name="v_z")
t.add_column(1.0, name="mass1")

t["radial_velocity"] = t["radial_velocity"].filled(np.average(t["radial_velocity"]))


# compute cartesian co-ords and put in table
t["x"] = SkyCoord(
    ra=(qt["ra"]), dec=(qt["dec"]), distance=(qt["distance"]), frame="icrs"
).cartesian.x
t["y"] = SkyCoord(
    ra=(qt["ra"]), dec=(qt["dec"]), distance=(qt["distance"]), frame="icrs"
).cartesian.y
t["z"] = SkyCoord(
    ra=(qt["ra"]), dec=(qt["dec"]), distance=(qt["distance"]), frame="icrs"
).cartesian.z


# t["v_x"]=gc1.v_x
# t["v_y"]=gc1.v_y
# t["v_z"]=gc1.v_z

# t["v_x"]=t["v_x"].filled(np.average(t["v_x"]))
# t["v_y"]=t["v_y"].filled(np.average(t["v_y"]))
# t["v_z"]=t["v_z"].filled(np.average(t["v_z"]))


# convert Mass to Float64 required for clustertools
t["mass_flame"] = t["mass_flame"].astype(np.float64)
t["mass_flame"] = t["mass_flame"].filled(
    np.average(t["mass_flame"])
)  # fill in the blanks!

# ============================================================================================================'


CoM = Centre_of_Mass(t)
print(CoM)


cluster = ctools.StarCluster(units="pckms", origin="galaxy")
for i in range(0, len(t) - 1):
    cluster.add_stars(
        x=t["x"][i],
        y=t["y"][i],
        z=t["z"][i],
        vx=t["v_x"][i],
        vy=t["v_y"][i],
        vz=t["v_z"][i],
        m=t["mass_flame"][i],
        id=i,
        m0=None,
        npop=None,
    )


print("Mean radius with numpy =", np.mean(cluster.r))
print("Mean radius =", cluster.rmean)

print("Half mass radius =", cluster.rm)
ctools.skyplot(cluster)
plt.show()

print(cluster.find_centre())


m_mean, m_hist, dm, alpha, ealpha, yalpha, eyalpha = ctools.mass_function(
    cluster, mmin=0.1, mmax=0.8, plot=True
)
plt.show()

rprof, pprof, nprof = ctools.rho_prof(cluster, plot=True)
plt.show()


print("completed")
#
#

# print(t)
# export this table
# t.write(dir_import+'values.dat', format='ascii', overwrite=True)
# arr=np.array(t)
# print(arr)
# Now start building the cluster

#  C:\Users\gordo\anaconda3\Lib\site-packages\clustertools

# m,x,y,z,vx,vy,vz=np.loadtxt(dir_import+'values2.csv',delimiter=',', unpack=True)
# cm = {"m": "Mass", "x": "x", "y": "y", "z": "z", "vx": "vx", "xy": "vy", "vz": "vz"}
# cluster = ctools.load_cluster(ctype="astropy_table", particles=t, units="pckms", origin="galaxy", column_mapper=cm,ofile=None)
