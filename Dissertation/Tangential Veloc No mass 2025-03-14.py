import pandas as pd
import numpy as np
import os


def compute_tangential_velocity_and_axis(input_file, output_file):
    # Load data
    df = pd.read_excel(input_file)

    # Drop incomplete rows
    df = df.dropna()

    # Extract position and velocity components
    x, y, z = df["x"], df["y"], df["z"]
    vx, vy, vz = df["vx"], df["vy"], df["vz"]

    # Compute radial distances
    r = np.sqrt(x**2 + y**2 + z**2)

    # Compute angular momentum (L = r x v)
    Lx = y * vz - z * vy
    Ly = z * vx - x * vz
    Lz = x * vy - y * vx

    # Compute the overall rotational axis as the mean angular momentum direction
    L_mean = np.array([np.sum(Lx), np.sum(Ly), np.sum(Lz)])
    rotational_axis = L_mean / np.linalg.norm(L_mean)

    # Compute velocity component parallel to the rotational axis
    v_dot_L = (
        vx * rotational_axis[0] + vy * rotational_axis[1] + vz * rotational_axis[2]
    )
    v_parallel_x = v_dot_L * rotational_axis[0]
    v_parallel_y = v_dot_L * rotational_axis[1]
    v_parallel_z = v_dot_L * rotational_axis[2]

    # Compute the velocity component perpendicular to the rotational axis (tangential velocity vector)
    v_t_x = vx - v_parallel_x
    v_t_y = vy - v_parallel_y
    v_t_z = vz - v_parallel_z

    # Compute signed tangential velocity
    cross_product_x = y * rotational_axis[2] - z * rotational_axis[1]
    cross_product_y = z * rotational_axis[0] - x * rotational_axis[2]
    cross_product_z = x * rotational_axis[1] - y * rotational_axis[0]

    sign = np.sign(
        v_t_x * cross_product_x + v_t_y * cross_product_y + v_t_z * cross_product_z
    )
    v_t_magnitude = np.sqrt(v_t_x**2 + v_t_y**2 + v_t_z**2)
    v_t_signed = sign * v_t_magnitude

    # Define radial bins
    max_r = np.max(r)
    bins = np.arange(1, max_r + 1, 1)

    results = []

    for radius in bins:
        mask = r <= radius
        if not mask.any():
            continue

        vt_mean = np.mean(v_t_signed[mask])

        # Compute average rotational axis per shell
        Lx_shell = np.sum(Lx[mask])
        Ly_shell = np.sum(Ly[mask])
        Lz_shell = np.sum(Lz[mask])
        L_shell = np.array([Lx_shell, Ly_shell, Lz_shell])
        rotational_axis_shell = L_shell / np.linalg.norm(L_shell)

        # Compute cumulative particle count
        cumulative_particles = mask.sum()

        results.append(
            {
                "Radius": radius,
                "Average Tangential Velocity": vt_mean,
                "Rotational Axis X": rotational_axis_shell[0],
                "Rotational Axis Y": rotational_axis_shell[1],
                "Rotational Axis Z": rotational_axis_shell[2],
                "Cumulative Particles": cumulative_particles,
            }
        )

    # Convert results to DataFrame
    results_df = pd.DataFrame(results)

    # Display results on screen
    print("Results Table:")
    print(results_df)
    print("\nOverall Rotational Axis:", rotational_axis)

    # Write results to Excel
    with pd.ExcelWriter(output_file) as writer:
        results_df.to_excel(writer, sheet_name="Results", index=False)
        pd.DataFrame({"Overall Rotational Axis": rotational_axis}).to_excel(
            writer, sheet_name="Overall Rotational Axis", index=False
        )


# File paths
input_path = "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/Kinematics/2025-03-14/particles.xlsx"
output_path = "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/Kinematics/2025-03-14/results.xlsx"

# Execute the function
compute_tangential_velocity_and_axis(input_path, output_path)
