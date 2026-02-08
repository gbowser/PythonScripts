import numpy as np
import pandas as pd
import os


def find_rotation_axis_and_velocity_in_shells(
    input_dir, input_filename, output_filename
):
    """
    Compute the best-fitting axis of rotation and rotational velocity for particles in increasing radius shells.
    Include all particles inside each radius and save the results to an Excel file.

    Parameters:
        input_dir (str): Directory containing the input Excel file.
        input_filename (str): Name of the input Excel file.
        output_filename (str): Name of the output Excel file.
    """
    file_path = os.path.join(input_dir, input_filename)

    # Load data
    data = pd.read_excel(file_path)
    positions = data[["x", "y", "z"]].values
    velocities = data[["vx", "vy", "vz"]].values

    # Compute distances from the origin
    radii = np.linalg.norm(positions, axis=1)
    max_radius = np.max(radii)

    results = []

    # Loop over increasing radius shells, including all particles inside each radius
    for r in range(1, int(np.ceil(max_radius)) + 1):
        mask = radii < r + 1  # Include all particles inside this radius
        shell_positions = positions[mask]
        shell_velocities = velocities[mask]

        num_particles = len(shell_positions)
        if num_particles == 0:
            continue

        A = np.zeros((num_particles, 3))

        for i in range(num_particles):
            x, y, z = shell_positions[i]
            vx, vy, vz = shell_velocities[i]

            # Compute the cross-product matrix
            A[i] = np.cross([x, y, z], [vx, vy, vz])

        # Solve using Singular Value Decomposition (SVD)
        _, S, Vt = np.linalg.svd(A)

        # Choose the eigenvector corresponding to the largest singular value
        rotation_axis = Vt[np.argmax(S)]

        # Normalize the axis
        rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)

        # Compute rotational velocity magnitude correctly
        r_magnitudes_sq = np.sum(shell_positions**2, axis=1)  # Squared norm
        r_magnitudes = np.sum(shell_positions, axis=1)  # Non-Squared norm

        rotational_velocities = (
            np.linalg.norm(np.cross(shell_positions, shell_velocities), axis=1)
            / r_magnitudes_sq
        )  # squared version rad/s
        rotational_velocity = np.mean(rotational_velocities)

        tangential_velocities = (
            np.linalg.norm(np.cross(shell_positions, shell_velocities), axis=1)
            / r_magnitudes
        )  # lineear version km/s
        tangential_velocity = np.mean(tangential_velocities)

        results.append(
            [r, num_particles, *rotation_axis, tangential_velocity, rotational_velocity]
        )

    # Convert results to DataFrame
    results_df = pd.DataFrame(
        results,
        columns=[
            "Radius",
            "#_Particles",
            "Axis_x",
            "Axis_y",
            "Axis_z",
            "Tan_Vel",
            "Rot_Vel",
        ],
    )

    # Save results to Excel
    output_path = os.path.join(input_dir, output_filename)
    results_df.to_excel(output_path, index=False)

    print(f"Results saved to {output_path}")
    print(results_df)


# Example usage:
input_dir = r"D:\Dropbox\Public Documents\UCLAN\AA3050 Dissertation\Kinematics"  # Directory path
input_filename = "particles.xlsx"  # Input file name
output_filename = "results.xlsx"  # Output file name

find_rotation_axis_and_velocity_in_shells(input_dir, input_filename, output_filename)
