# Write your find_closest function here
import numpy as np


def hms2dec(hr, m, s):
    dec = hr + m / 60 + s / 3600
    return dec * 15


def dms2dec(d, m, s):
    sign = d / abs(d)
    dec = abs(d) + m / 60 + s / 3600
    return sign * dec


def import_bss():
    res = []
    data = np.loadtxt("Data Driven Astronomy/bss2.dat", usecols=range(1, 7))
    for i, row in enumerate(data, 1):
        res.append(
            (i, hms2dec(row[0], row[1], row[2]), dms2dec(row[3], row[4], row[5]))
        )
    return res


def import_super():
    data = np.loadtxt(
        "Data Driven Astronomy/super.csv", delimiter=",", skiprows=1, usecols=[0, 1]
    )
    res = []
    for i, row in enumerate(data, 1):
        res.append((i, row[0], row[1]))
    return res


def angular_dist(ra1, dec1, ra2, dec2):
    # Convert to radians
    r1 = np.radians(ra1)
    d1 = np.radians(dec1)
    r2 = np.radians(ra2)
    d2 = np.radians(dec2)

    a = np.sin(np.abs(d1 - d2) / 2) ** 2
    b = np.cos(d1) * np.cos(d2) * np.sin(np.abs(r1 - r2) / 2) ** 2

    angle = 2 * np.arcsin(np.sqrt(a + b))

    # Convert back to degrees
    return np.degrees(angle)


def find_closest(cat, ra, dec):
    min_dist = np.inf
    min_id = None
    for id1, ra1, dec1 in cat:
        dist = angular_dist(ra1, dec1, ra, dec)
        if dist < min_dist:
            min_id = id1
            min_dist = dist

    return min_id, min_dist


cat = import_bss()
print(find_closest(cat, 175.3, -32.5))
print(find_closest(cat, 32.2, 40.7))
