import numpy as np

def angular_velocity(r, v):
    """
    Computes the angular velocity vector given position and velocity vectors.
    
    Parameters:
        r (array-like): Position vector [x, y, z]
        v (array-like): Velocity vector [vx, vy, vz]
        
    Returns:
        numpy.ndarray: Angular velocity vector [wx, wy, wz]
    """
    r = np.array(r)
    v = np.array(v)
    r_squared = np.dot(r, r)  # Compute |r|^2
    
    if r_squared == 0:
        raise ValueError("Position vector cannot be the zero vector.")
    
    angular_velocity_vector = np.cross(r, v) / r_squared
    return angular_velocity_vector

# Example usage:
r = [1, 2, 3]  # Example position vector
v = [4, 5, 6]  # Example velocity vector

omega = angular_velocity(r, v)
print("Angular Velocity Vector:", omega)