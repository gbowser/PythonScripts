# eg4-astrodict.py
# Listing 4.1 Astronomical data

import math

# Mass (m) and radius (r) (in km) for some astronomical bodies
body = {
    'Sun': (1.988e30, 6.955e5),
    'Mercury': (3.302e23, 2440.),
    'Venus': (4.867e24, 6051.),
    'Earth': (5.9722e24, 6371.),
    'Mars': (6.4171e23, 3389.5),
    'Jupiter': (1.8989e27, 69911.),
    'Saturn': (5.683e26, 58232.),
    'Uranus': (8.682e25, 25362.),
    'Neptune': (1.024e26, 24622.)
}

# The Sun is not a planet!
planets = list(body.keys())
planets.remove('Sun')


def calc_density(m, r):
    """
    Returns the density of a sphere with mass m and radius r.
    """
    return m / (4/3 * math.pi * r**3)


rho = {}

for planet in planets:
    m, r = body[planet]

    # calculate the density in g/cm^3
    rho[planet] = calc_density(m * 1000., r * 1.e5)


for planet, density in sorted(rho.items()):
    print("{:s}: {:.2f} g/cm^3".format(planet, density))