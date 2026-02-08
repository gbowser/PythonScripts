import numpy as np
import pandas as pd

def find_rotation_axis_and_velocity_from_xlsx(file_path):
    """
    Compute the best-fitting axis of rotation and rotational velocity from an Excel file.
    
    Parameters:
        file_path (str): Path to the Excel file containing x, y, z, vx, vy, vz data.
    
    Returns:
        tuple: (Unit vector along the best-fitting axis of rotation (3,), rotational velocity magnitude)
    """
    # Load data
    data = pd.read_excel(file_path)
    positions = data[['x', 'y', 'z']].values
    velocities = data[['vx', 'vy', 'vz']].values
    
    N = positions.shape[0]
    A = np.zeros((N, 3))
    
    for i in range(N):
        x, y, z = positions[i]
        vx, vy, vz = velocities[i]
        
        # Compute the cross-product matrix
        A[i] = np.cross([x, y, z], [vx, vy, vz])
    
    # Solve using Singular Value Decomposition (SVD)
    _, _, Vt = np.linalg.svd(A)
    rotation_axis = Vt[-1]  # Last row of Vt corresponds to the smallest singular value
    
    # Normalize the axis
    rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)
    
    # Compute rotational velocity magnitude
    angular_velocities = np.linalg.norm(np.cross(positions, velocities), axis=1) / np.linalg.norm(positions, axis=1)
    rotational_velocity = np.mean(angular_velocities)
    
    return rotation_axis, rotational_velocity

# Example usage:
file_path = "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/Kinematics/particles.xlsx"  # Path to Excel file
axis, omega = find_rotation_axis_and_velocity_from_xlsx(file_path)
print("Best-fitting Axis of Rotation:", axis)
print("Rotational Velocity Magnitude:", omega)