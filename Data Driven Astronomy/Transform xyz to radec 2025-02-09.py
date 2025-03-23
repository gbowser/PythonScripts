
from astropy import units as u
import astropy.coordinates as coord
from astropy.coordinates import SkyCoord, ICRS


# https://docs.astropy.org/en/stable/coordinates/velocities.html
# https://docs.astropy.org/en/stable/generated/examples/coordinates/plot_galactocentric-frame.html

def cartesian_to_radec(x,y,z):
    sky_coord  = SkyCoord(x = x * u.pc, y= y* u.pc,z=z * u.pc, representation_type='cartesian', frame=ICRS)

    # Extract Right Ascension and Declination

    sky_coord.representation_type ='spherical'
    ra=sky_coord.ra.deg
    dec=sky_coord.dec.deg

    return ra, dec


x, y, z = 18.777,38.938, 16.177




ra, dec = cartesian_to_radec(x,y,z)
print(f"RA: {ra:.3f} degrees, Dec: {dec:.3f} degrees")



