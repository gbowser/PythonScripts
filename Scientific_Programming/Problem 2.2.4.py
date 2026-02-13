def s_obl(a, c):
    import math

    e = math.sqrt(1 - (c / a) ** 2)
    s_obl = 2 * math.pi * a**2 * (1 + (1 - e**2) / e * math.atanh(e))
    return s_obl


surface_area = (s_obl(6378137.0, 6356752.31424505))
radius_sphere = (surface_area / (4 * 3.141592653589793)) ** 0.5
print(radius_sphere/1000)    