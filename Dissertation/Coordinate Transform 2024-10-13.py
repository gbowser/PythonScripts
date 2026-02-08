# https://docs.astropy.org/en/latest/coordinates/index.html



from astropy import units as u
from astropy.coordinates import SkyCoord

c1 = SkyCoord(ra=10.625*u.degree, dec=41.2*u.degree, distance = 770*u.kpc, frame='icrs')

print (SkyCoord(ra=10.625*u.degree, dec=41.2*u.degree, distance = 770*u.kpc, frame='icrs').cartesian.x)

print( c1.cartesian.x  , c1.cartesian.y  , c1.cartesian.z  )

