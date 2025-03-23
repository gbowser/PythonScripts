from astropy import units as u
import astropy.coordinates as coord
from astropy.coordinates import SkyCoord, ICRS


# https://docs.astropy.org/en/stable/coordinates/velocities.html
# https://docs.astropy.org/en/stable/generated/examples/coordinates/plot_galactocentric-frame.html


def radec_to_cartesian(ra, dec, distance):
    sky_coord = SkyCoord(
        ra=ra * u.deg,
        dec=dec * u.deg,
        distance=distance * u.pc,
        representation_type="spherical",
        frame=ICRS,
    )

    # Extract Right Ascension and Declination

    sky_coord.representation_type = "cartesian"
    x = sky_coord.x
    y = sky_coord.y
    z = sky_coord.z

    return x, y, z


ra, dec, distance = 67.8056	, 16.8670,46.15




x, y, z = radec_to_cartesian(ra, dec, distance)
print(f"x: {x:.3f} pc, y: {y:.3f} pc, z: {z:.3f}")
