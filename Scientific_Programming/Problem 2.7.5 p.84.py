#range of projectile

def projectile_range(v0, theta, g=9.81):
    """Calculate the range of a projectile given initial velocity, angle, and gravity."""
    import math
    # Convert angle from degrees to radians
    theta_rad = math.radians(theta)
    
    # Calculate the range using the formula: R = (v0^2 * sin(2*theta)) / g
    max_range = (v0 ** 2 * math.sin(2 * theta_rad)) / g
    
    return max_range

print(f"Maximum range: {projectile_range(10, 45)}")
