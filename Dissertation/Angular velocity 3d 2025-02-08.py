import pandas as pd
import numpy as np
import os

# File path
file_path = r"D:\Dropbox\Public Documents\UCLAN\AA3050 Dissertation\Kinematics"
input_file = os.path.join(file_path, "particles.xlsx")
output_file = os.path.join(file_path, "results.xlsx")

# Load particle data
df = pd.read_excel(input_file)

# Extract values
x, y, z = df['x'].values, df['y'].values, df['z'].values
vx, vy, vz = df['vx'].values, df['vy'].values, df['vz'].values
m = np.ones(len(x))  # Assuming equal mass for all particles

# Compute r and v vectors
r = np.column_stack((x, y, z))
v = np.column_stack((vx, vy, vz))

# Compute angular momentum L (sum of r_i x v_i weighted by mass)
L = np.sum(np.cross(r, v) * m[:, None], axis=0)

# Compute moment of inertia I (sum of m_i * |r_i|^2)
I = np.sum(m * (x**2 + y**2 + z**2))

# Compute angular velocity vector omega
omega = L / I if I != 0 else np.array([0, 0, 0])

# Compute unit rotation axis
omega_magnitude = np.linalg.norm(omega)
rotation_axis = omega / omega_magnitude if omega_magnitude != 0 else np.array([0, 0, 0])

# Compute tangential velocities
tangential_speeds = np.linalg.norm(np.cross(r, v), axis=1) / np.linalg.norm(r, axis=1)

# Compute average tangential velocity
average_tangential_velocity = np.sum(m * tangential_speeds) / np.sum(m)

# Print results
print("Collective Angular Velocity Vector (rad/s):", omega)
print("Collective Rotation Axis (unit vector):", rotation_axis)
print("Average Tangential Velocity (km/s):", average_tangential_velocity)

# Save results to file
results_df = pd.DataFrame({
    "Parameter": ["Angular Velocity X", "Angular Velocity Y", "Angular Velocity Z", 
                  "Rotation Axis X", "Rotation Axis Y", "Rotation Axis Z", "Average Tangential Velocity"],
    "Value": [omega[0], omega[1], omega[2], 
               rotation_axis[0], rotation_axis[1], rotation_axis[2], average_tangential_velocity]
})

results_df.to_excel(output_file, index=False)

print("Results saved to:", output_file)
