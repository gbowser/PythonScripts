# rotations.py

import numpy as np


def rotate_model(Data, theta_z=0.0, theta_x=0.0):
    """
    Rotate an N-body model about the z-axis and then the x-axis.

    Parameters
    ----------
    Data : numpy structured array
        Particle data with fields:
            x, y, z, vx, vy, vz

        Other fields, such as mass m, are preserved unchanged.

    theta_z : float
        Rotation angle about the z-axis, in radians.

    theta_x : float
        Rotation angle about the x-axis, in radians.

    Returns
    -------
    Data_rot : numpy structured array
        Copy of Data with rotated positions and velocities.
    """

    # Work on a copy so the original data is not changed
    Data_rot = Data.copy()

    # Extract positions
    x = Data["x"].copy()
    y = Data["y"].copy()
    z = Data["z"].copy()

    # Extract velocities
    vx = Data["vx"].copy()
    vy = Data["vy"].copy()
    vz = Data["vz"].copy()

    # ------------------------------------------------------------
    # 1. Rotate about the z-axis
    #
    # x' =  x cos(theta_z) - y sin(theta_z)
    # y' =  x sin(theta_z) + y cos(theta_z)
    # z' =  z
    # ------------------------------------------------------------
    cz = np.cos(theta_z)
    sz = np.sin(theta_z)

    x_z = x * cz - y * sz
    y_z = x * sz + y * cz
    z_z = z

    vx_z = vx * cz - vy * sz
    vy_z = vx * sz + vy * cz
    vz_z = vz

    # ------------------------------------------------------------
    # 2. Rotate about the x-axis
    #
    # x'' = x'
    # y'' = y' cos(theta_x) - z' sin(theta_x)
    # z'' = y' sin(theta_x) + z' cos(theta_x)
    # ------------------------------------------------------------
    cx = np.cos(theta_x)
    sx = np.sin(theta_x)

    x_final = x_z
    y_final = y_z * cx - z_z * sx
    z_final = y_z * sx + z_z * cx

    vx_final = vx_z
    vy_final = vy_z * cx - vz_z * sx
    vz_final = vy_z * sx + vz_z * cx

    # Store rotated values
    Data_rot["x"] = x_final
    Data_rot["y"] = y_final
    Data_rot["z"] = z_final

    Data_rot["vx"] = vx_final
    Data_rot["vy"] = vy_final
    Data_rot["vz"] = vz_final

    return Data_rot
