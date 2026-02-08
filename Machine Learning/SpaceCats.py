# Write your import_bss function here.
from pathlib import Path

import numpy as np


def hms2dec(h_in, m_in, s_in):
    return 15 * (h_in + (m_in / 60) + (s_in / 60**2))


def dms2dec(d_in, m_in, s_in):
    sign = d_in / abs(d_in)
    return sign * (abs(d_in) + (m_in / 60) + (s_in / (60**2)))


def angular_dist(ra1, dec1, ra2, dec2):
    ra1 = np.radians(ra1)
    dec1 = np.radians(dec1)
    ra2 = np.radians(ra2)
    dec2 = np.radians(dec2)
    b = np.cos(dec1) * np.cos(dec2) * np.sin(np.abs(ra1 - ra2) / 2) ** 2
    a = (np.sin(np.abs(dec1 - dec2) / 2)) ** 2
    d = 2 * np.arcsin(np.sqrt(a + b))
    return np.degrees(d)


def import_bss():
    res = []
    data = np.loadtxt("Data Driven Astronomy/bss2.dat", usecols=range(1, 7))
    # print(data.shape[0])
    # iterate on rows
    for i in range(0, data.shape[0]):
        res.append(
            (
                i + 1,
                hms2dec(data[i, 0], data[i, 1], data[i, 2]),
                dms2dec(data[i, 3], data[i, 4], data[i, 5]),
            )
        )
    return res


def import_super():
    res = []
    data = np.loadtxt(
        "Data Driven Astronomy/super.csv", delimiter=",", skiprows=1, usecols=[0, 1]
    )
    # print(data.shape[0])
    for i in range(0, data.shape[0]):
        # collect 3 data items
        # print(data[i, 0])
        # print(data[i, 1])
        res.append((i + 1, data[i, 0], data[i, 1]))

    return res


def find_closest(cat, ra_in, dec_in):
    res = (0, 2000)
    for star in cat:
        ang_dist = angular_dist(star[1], star[2], ra_in, dec_in)
        #        print(star,ang_dist)
        if ang_dist < res[1]:
            res = (star[0], ang_dist)
    return res


def crossmatch_model(cat1, cat2, max_radius):
    matches = []
    no_matches = []
    for id1, ra1, dec1 in cat1:
        closest_dist = np.inf
        closest_id2 = None
        for id2, ra2, dec2 in cat2:
            dist = angular_dist(ra1, dec1, ra2, dec2)
            if dist < closest_dist:
                closest_id2 = id2
                closest_dist = dist

        # Ignore match if it's outside the maximum radius
        if closest_dist > max_radius:
            no_matches.append(id1)
        else:
            matches.append((id1, closest_id2, closest_dist))

    return matches, no_matches


def crossmatch(bss_cat, super_cat, max_dist):
    # initialise empty lists
    matches = []
    no_matches = []

    for bss_star in bss_cat:
        lowest_so_far = np.inf
        new_item = ()
        for super_star in super_cat:
            ang_dist = angular_dist(
                bss_star[1], bss_star[2], super_star[1], super_star[2]
            )
            if ang_dist < max_dist and ang_dist < lowest_so_far:
                lowest_so_far = ang_dist
                new_item = (bss_star[0], super_star[0], lowest_so_far)
        if new_item:
            matches.append(new_item)

        if not (new_item):
            no_matches.append(bss_star[0])

    return (matches, no_matches)


# You can use this to test your function.
# Any code inside this `if` statement will be ignored by the automarker.
if __name__ == "__main__":
    # Output of the import_bss and import_super functions

    matches_file = Path("Matches.txt")
    no_matches_file = Path("No_Matches.txt")

    bss_cat = import_bss()
    super_cat = import_super()

    # First example in the question
    max_dist = 40 / 3600
    matches, no_matches = crossmatch(bss_cat, super_cat, max_dist)
    print(matches[:3])
    print(no_matches[:3])
    print(len(no_matches))

    # Second example in the question
    # max_dist = 5 / 3600
    # matches, no_matches = crossmatch(bss_cat, super_cat, max_dist)
    # print(matches[:3])
    # print(no_matches[:3])
    # print(len(no_matches))

    # # now find closest
    # cat = import_bss()
    # print(find_closest(cat, 175.3, -32.5))
    # print(find_closest(cat, 32.2, 40.7))
    print("Writing file now...\n")
    contents = "Matches\n"
    for index1, index2, distance in matches:
        contents += str(index1) + "\t" + str(index2) + "\t" + str(distance) + "\n"
    matches_file.write_text(contents)

    contents = "No Matches\n"
    for index1 in no_matches:
        contents += str(index1) + "\n"
    no_matches_file.write_text(contents)
