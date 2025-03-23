import numpy as np
import pandas as pd
import os

def compute_rotational_properties(positions, velocities, masses):
    """
    Computes the average rotational velocity, tangential velocity, and rotational axis of particles around (0,0,0).

    :param positions: Nx3 array of (x, y, z) coordinates of N particles
    :param velocities: Nx3 array of (vx, vy, vz) velocities of N particles
    :param masses: N array of masses of N particles
    :return: (avg_rotational_velocity, avg_tangential_velocity, avg_rotational_axis)
    """
    
    # Convert to numpy arrays
    positions = np.array(positions)
    velocities = np.array(velocities)
    masses = np.array(masses)
    
    # Compute radial vectors and their magnitudes
    r_mag = np.linalg.norm(positions, axis=1)
    r_hat = positions / r_mag[:, None]  # Unit vector along r
    
    # Compute tangential velocity
    v_radial = np.sum(velocities * r_hat, axis=1, keepdims=True) * r_hat  # Radial component of velocity
    v_tangential = velocities - v_radial  # Tangential velocity component
    v_tangential_mag = np.linalg.norm(v_tangential, axis=1)
    
    # Compute angular momentum L = r x p
    momenta = masses[:, None] * velocities  # Linear momentum
    angular_momentum = np.cross(positions, momenta)  # Cross product r x p
    L_magnitude = np.linalg.norm(angular_momentum, axis=1)  # Magnitude of L
    
    # Compute moment of inertia I = m * r^2
    moment_of_inertia = masses * r_mag**2
    
    # Compute angular velocity omega = L / I (avoiding division by zero)
    omega = np.zeros_like(L_magnitude)
    nonzero_mask = moment_of_inertia > 1e-10  # Avoid division by zero
    omega[nonzero_mask] = L_magnitude[nonzero_mask] / moment_of_inertia[nonzero_mask]
    
    # Compute average rotational velocity and tangential velocity
    avg_rotational_velocity = np.mean(omega)
    avg_tangential_velocity = np.mean(v_tangential_mag)

    # Compute average rotational axis
    valid_L = angular_momentum[L_magnitude > 1e-10]  # Ignore zero angular momentum cases
    if len(valid_L) > 0:
        avg_rotational_axis = np.mean(valid_L / np.linalg.norm(valid_L, axis=1)[:, None], axis=0)
        avg_rotational_axis /= np.linalg.norm(avg_rotational_axis)  # Normalize to unit vector
    else:
        avg_rotational_axis = np.array([0, 0, 0])  # No valid rotation
    
    return avg_rotational_velocity, avg_tangential_velocity, avg_rotational_axis


# Define file paths
base_path = r"D:\Dropbox\Public Documents\UCLAN\AA3050 Dissertation\Kinematics\2025-03-01"
input_file = os.path.join(base_path, "particles_data.xlsx")
output_file = os.path.join(base_path, "rotational_results_by_shell.xlsx")

# Load data from an Excel file
df = pd.read_excel(input_file)

# Remove rows with missing values
initial_row_count = len(df)
df.dropna(subset=['x', 'y', 'z', 'vx', 'vy', 'vz', 'mass'], inplace=True)
removed_rows = initial_row_count - len(df)

if removed_rows > 0:
    print(f"Removed {removed_rows} rows due to missing values.")

# Extract positions, velocities, and masses
positions = df[['x', 'y', 'z']].values
velocities = df[['vx', 'vy', 'vz']].values
masses = df['mass'].values

# Compute radial distances
radii = np.linalg.norm(positions, axis=1)

# Determine shell bins (increments of 1)
max_radius = int(np.ceil(np.max(radii)))
shell_results = []

# Compute properties for each shell
for shell in range(1, max_radius + 1):
    mask = (radii > (shell - 1)) & (radii <= shell)
    if np.any(mask):  # Ensure there's data in this shell
        avg_rot_vel, avg_tan_vel, avg_rot_axis = compute_rotational_properties(
            positions[mask], velocities[mask], masses[mask]
        )
        shell_results.append({
            "Shell Radius": shell,
            "Avg Rotational Velocity": avg_rot_vel,
            "Avg Tangential Velocity": avg_tan_vel,
            "Avg Rot Axis X": avg_rot_axis[0],
            "Avg Rot Axis Y": avg_rot_axis[1],
            "Avg Rot Axis Z": avg_rot_axis[2]
        })

# Convert results to DataFrame and save to Excel
results_df = pd.DataFrame(shell_results)
results_df.to_excel(output_file, index=False)

# Print results
print("Results per shell:")
print(results_df)

print(f"\nResults saved to {output_file}")

