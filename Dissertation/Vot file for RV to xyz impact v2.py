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
file_import = "Hyades-2025-02-17.vot.gz"



# Use QTable

qt = QTable.read(dir_import + file_import)

# put in zero values for x,y,z, vx,vy, vz
qt.add_column(0.0 * u.pc, name="distance")
qt.add_column(0.0 * u.pc, name="x")
qt.add_column(0.0 * u.pc, name="y")
qt.add_column(0.0 * u.pc, name="z")

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
    pm_ra_cosdec=0*u.mas/u.yr * np.cos(2*np.pi*qt["dec"]/360),
    distance=qt["distance"],
    pm_dec=1*u.mas/u.yr,
    radial_velocity=0.0 * u.km / u.second,
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
qt.write(dir_import + "values.dat", format="ascii", overwrite=True)


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




