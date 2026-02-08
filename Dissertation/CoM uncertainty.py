import numpy as np
import pandas as pd


def compute_com_from_astronomical_excel(file_path, sheet_name=0):
    """
    Compute the Cartesian center of mass and its uncertainty from astronomical coordinates in an Excel file.

    The Excel file should contain the following columns:
    - ra (degrees), dec (degrees), distance
    - sigma_ra (degrees), sigma_dec (degrees), sigma_distance
    - m, sigma_m

    Returns:
    - Dictionary with COM (x, y, z) and their uncertainties.
    """
    df = pd.read_excel(file_path, sheet_name=sheet_name)

    # Convert angles from degrees to radians
    ra_rad = np.deg2rad(df["ra"].values)
    dec_rad = np.deg2rad(df["dec"].values)
    sigma_ra_rad = np.deg2rad(df["sigma_ra"].values)
    sigma_dec_rad = np.deg2rad(df["sigma_dec"].values)

    d = df["distance"].values
    m = df["m"].values
    sigma_d = df["sigma_distance"].values
    sigma_m = df["sigma_m"].values

    # Cartesian coordinates
    x = d * np.cos(dec_rad) * np.cos(ra_rad)
    y = d * np.cos(dec_rad) * np.sin(ra_rad)
    z = d * np.sin(dec_rad)

    M = np.sum(m)
    sigma_M = np.sqrt(np.sum(sigma_m**2))

    x_com = np.sum(m * x) / M
    y_com = np.sum(m * y) / M
    z_com = np.sum(m * z) / M

    # Partial derivatives for uncertainty propagation

    # x
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

    # y
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

    # z
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


print(
    compute_com_from_astronomical_excel(
        "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/CoM/Hy.xlsx"
    )
)
