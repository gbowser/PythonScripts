import numpy as np
import pandas as pd


def compute_com_from_astronomical_excel(file_path, sheet_name=0):
    df = pd.read_excel(file_path, sheet_name=sheet_name)

    ra_rad = np.deg2rad(df["ra"].values)
    dec_rad = np.deg2rad(df["dec"].values)
    sigma_ra_rad = np.deg2rad(df["sigma_ra"].values)
    sigma_dec_rad = np.deg2rad(df["sigma_dec"].values)

    d = df["distance"].values
    m = df["m"].values
    sigma_d = df["sigma_distance"].values
    sigma_m = df["sigma_m"].values

    x = d * np.cos(dec_rad) * np.cos(ra_rad)
    y = d * np.cos(dec_rad) * np.sin(ra_rad)
    z = d * np.sin(dec_rad)

    M = np.sum(m)
    sigma_M = np.sqrt(np.sum(sigma_m**2))

    x_com = np.sum(m * x) / M
    y_com = np.sum(m * y) / M
    z_com = np.sum(m * z) / M

    dx_dm = (x - x_com) / M
    dx_dd = m * np.cos(dec_rad) * np.cos(ra_rad) / M
    dx_ddec = -m * d * np.sin(dec_rad) * np.cos(ra_rad) / M
    dx_dra = -m * d * np.cos(dec_rad) * np.sin(ra_rad) / M
    dx_dM = -x_com / M
    sigma_x_com_squared = (
        np.sum(
            (dx_dm * sigma_m) ** 2
            + (dx_dd * sigma_d) ** 2
            + (dx_ddec * sigma_dec_rad) ** 2
            + (dx_dra * sigma_ra_rad) ** 2
        )
        + (dx_dM * sigma_M) ** 2
    )
    sigma_x_com = np.sqrt(sigma_x_com_squared)

    dy_dm = (y - y_com) / M
    dy_dd = m * np.cos(dec_rad) * np.sin(ra_rad) / M
    dy_ddec = -m * d * np.sin(dec_rad) * np.sin(ra_rad) / M
    dy_dra = m * d * np.cos(dec_rad) * np.cos(ra_rad) / M
    dy_dM = -y_com / M
    sigma_y_com_squared = (
        np.sum(
            (dy_dm * sigma_m) ** 2
            + (dy_dd * sigma_d) ** 2
            + (dy_ddec * sigma_dec_rad) ** 2
            + (dy_dra * sigma_ra_rad) ** 2
        )
        + (dy_dM * sigma_M) ** 2
    )
    sigma_y_com = np.sqrt(sigma_y_com_squared)

    dz_dm = (z - z_com) / M
    dz_dd = m * np.sin(dec_rad) / M
    dz_ddec = m * d * np.cos(dec_rad) / M
    dz_dM = -z_com / M
    sigma_z_com_squared = (
        np.sum(
            (dz_dm * sigma_m) ** 2
            + (dz_dd * sigma_d) ** 2
            + (dz_ddec * sigma_dec_rad) ** 2
        )
        + (dz_dM * sigma_M) ** 2
    )
    sigma_z_com = np.sqrt(sigma_z_com_squared)

    return {
        "x_com": x_com,
        "y_com": y_com,
        "z_com": z_com,
        "sigma_x_com": sigma_x_com,
        "sigma_y_com": sigma_y_com,
        "sigma_z_com": sigma_z_com,
    }


def cartesian_to_astronomical(x, y, z, sigma_x, sigma_y, sigma_z):
    d = np.sqrt(x**2 + y**2 + z**2)
    ra = np.arctan2(y, x)
    dec = np.arcsin(z / d)

    sigma_d = np.sqrt(
        (x / d * sigma_x) ** 2 + (y / d * sigma_y) ** 2 + (z / d * sigma_z) ** 2
    )
    sigma_ra = np.sqrt(
        (y / (x**2 + y**2) * sigma_x) ** 2 + (x / (x**2 + y**2) * sigma_y) ** 2
    )
    sigma_dec = np.sqrt(((sigma_z / d) ** 2 + ((z * sigma_d) / (d**2)) ** 2)) / np.sqrt(
        1 - (z / d) ** 2
    )

    ra_deg = np.rad2deg(ra) % 360
    dec_deg = np.rad2deg(dec)
    sigma_ra_deg = np.rad2deg(sigma_ra)
    sigma_dec_deg = np.rad2deg(sigma_dec)

    return {
        "ra": ra_deg,
        "dec": dec_deg,
        "distance": d,
        "sigma_ra": sigma_ra_deg,
        "sigma_dec": sigma_dec_deg,
        "sigma_distance": sigma_d,
    }


def compute_com_astronomical_with_output(file_path, sheet_name=0):
    com_cartesian = compute_com_from_astronomical_excel(file_path, sheet_name)
    com_astronomical = cartesian_to_astronomical(
        com_cartesian["x_com"],
        com_cartesian["y_com"],
        com_cartesian["z_com"],
        com_cartesian["sigma_x_com"],
        com_cartesian["sigma_y_com"],
        com_cartesian["sigma_z_com"],
    )

    print("\n📌 Center of Mass (Cartesian Coordinates):")
    print(f"  x = {com_cartesian['x_com']:.2f} ± {com_cartesian['sigma_x_com']:.2f}")
    print(f"  y = {com_cartesian['y_com']:.2f} ± {com_cartesian['sigma_y_com']:.2f}")
    print(f"  z = {com_cartesian['z_com']:.2f} ± {com_cartesian['sigma_z_com']:.2f}")

    print("\n🌌 Center of Mass (Astronomical Coordinates):")
    print(
        f"  RA        = {com_astronomical['ra']:.2f}° ± {com_astronomical['sigma_ra']:.2f}°"
    )
    print(
        f"  Dec       = {com_astronomical['dec']:.2f}° ± {com_astronomical['sigma_dec']:.2f}°"
    )
    print(
        f"  Distance  = {com_astronomical['distance']:.2f} ± {com_astronomical['sigma_distance']:.2f}"
    )

    return {"cartesian": com_cartesian, "astronomical": com_astronomical}


# Example usage (uncomment the line below and set your file path)
result = compute_com_astronomical_with_output(
    "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/CoM/Pl.xlsx"
)
