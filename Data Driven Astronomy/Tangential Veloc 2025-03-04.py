import pandas as pd
import numpy as np
import os

def compute_tangential_velocity_and_axis(input_file, output_file):
    # Load data
    df = pd.read_excel(input_file)
    
    # Drop incomplete rows
    df = df.dropna()
    
    # Extract position, velocity, and mass components
    x, y, z = df['x'], df['y'], df['z']
    vx, vy, vz = df['vx'], df['vy'], df['vz']
    m = df['mass']
    
    # Compute radial distances
    r = np.sqrt(x**2 + y**2 + z**2)
    
    # Compute angular momentum (L = r x v * m)
    Lx = m * (y * vz - z * vy)
    Ly = m * (z * vx - x * vz)
    Lz = m * (x * vy - y * vx)
    
    # Compute the overall rotational axis as the weighted mean angular momentum direction
    L_mean = np.array([np.sum(Lx), np.sum(Ly), np.sum(Lz)])
    rotational_axis = L_mean / np.linalg.norm(L_mean)
    
    # Define radial bins
    max_r = np.max(r)
    bins = np.arange(1, max_r + 1, 1)
    
    results = []
    
    for radius in bins:
        mask = r <= radius
        if not mask.any():
            continue
        
        vt_squared = (vx[mask]**2 + vy[mask]**2 + vz[mask]**2) - (x[mask] * vx[mask] + y[mask] * vy[mask] + z[mask] * vz[mask])**2 / r[mask]**2
        vt_mean = np.sqrt(np.average(vt_squared, weights=m[mask]))
        
        # Compute mass-weighted average rotational axis per shell
        Lx_shell = np.sum(Lx[mask])
        Ly_shell = np.sum(Ly[mask])
        Lz_shell = np.sum(Lz[mask])
        L_shell = np.array([Lx_shell, Ly_shell, Lz_shell])
        rotational_axis_shell = L_shell / np.linalg.norm(L_shell)
        
        # Compute cumulative mass and particle count
        cumulative_mass = np.sum(m[mask])
        cumulative_particles = mask.sum()
        
        results.append({
            'Radius': radius, 
            'Average Tangential Velocity': vt_mean, 
            'Rotational Axis X': rotational_axis_shell[0], 
            'Rotational Axis Y': rotational_axis_shell[1], 
            'Rotational Axis Z': rotational_axis_shell[2],
            'Cumulative Mass': cumulative_mass,
            'Cumulative Particles': cumulative_particles
        })
    
    # Convert results to DataFrame
    results_df = pd.DataFrame(results)
    
    # Display results on screen
    print("Results Table:")
    print(results_df)
    print("\nOverall Rotational Axis:", rotational_axis)
    
    # Write results to Excel
    with pd.ExcelWriter(output_file) as writer:
        results_df.to_excel(writer, sheet_name='Results', index=False)
        pd.DataFrame({'Overall Rotational Axis': rotational_axis}).to_excel(writer, sheet_name='Overall Rotational Axis', index=False)

# File paths
input_path = "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/Kinematics/2025-03-14/particles.xlsx"
output_path = "D://Dropbox/Public Documents/UCLAN/AA3050 Dissertation/Kinematics/2025-03-14/results.xlsx"

# Execute the function
compute_tangential_velocity_and_axis(input_path, output_path)
