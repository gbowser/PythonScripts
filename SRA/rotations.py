#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotate the model theta_z about z and theta_x about z
"""
import numpy as np

def rotate_model(Data, theta_z, theta_x):
    """
    Rotates the data containing x, y, z and vx, vy, vz
    Firstly about the z axis theta_z radians
    Then about the x axis theta_x radians
    Simulates a different viewing angle
    Rotates the velocities also
    """  
    #Rotate theta_z about the z axis
    rot = np.array([[np.cos(theta_z), -np.sin(theta_z), 0],
                    [np.sin(theta_z),  np.cos(theta_z), 0],
                    [              0,                0, 1]])
    #Put x y z vx vy vz together            
    pos = np.column_stack( (Data['x'], Data['y'], Data['z']) )
    vel = np.column_stack( (Data['vx'], Data['vy'], Data['vz']) )
    #Execute the rotation
    #If we were analysing velocities we would need to do the same with those
    pos_r = rot.dot(pos.T).T
    vel_r = rot.dot(vel.T).T
    
    #Now rotate theta_x about the x axis
    rot = np.array([[1,               0,               0],
                    [0, np.cos(theta_x), -np.sin(theta_x)],
                    [0, np.sin(theta_x), np.cos(theta_x)]])
    #Put x y z together            
    #pos = np.column_stack( (pos_r[:,0], pos_r[:,1], pos_r[:,2]) )
    #Execute the rotation and reset x, y, z
    #If we were analysing velocities we would need to do the same with those
    pos_r2 = rot.dot(pos_r.T).T
    vel_r2 = rot.dot(vel_r.T).T

    x, y, z = pos_r2[:,0], pos_r2[:,1], pos_r2[:,2]
    vx, vy, vz = vel_r2[:,0], vel_r2[:,1], vel_r2[:,2]

    m = Data['m']
    
    #SPH simulation with tform?
    if 'tform' in Data.dtype.names:
        tform = Data['tform']

        Data2 = np.column_stack( (x, y, z, vx, vy, vz, m, tform) )
        Data2.dtype = Data.dtype
    else:
        Data2 = np.column_stack( (x, y, z, vx, vy, vz, m) )
        Data2.dtype = Data.dtype
   
    return Data2


def bar_along_x(Data, I_radius):
    """
    Rotate the model so the bar is along x
    Do using the inertia tensor only for I_radius to capture
    Just the bar; I use 3 (kpc)
    Returns the rotated Dataset (positions and velocites)
    and the angle through which the rotation occurred
    """
   
    x1, y1 = Data['x'], Data['y']   
        
    #Restrict the range of R over which we calculate the tensor so we get the bar only
    r2 = np.hypot(x1, y1)
    xlt = x1[r2 < I_radius]
    ylt = y1[r2 < I_radius]
    
    #Calculate the inertia tensor
    I_yy, I_xx, I_xy = np.sum(ylt**2), np.sum(xlt**2), np.sum(xlt*ylt)
    I = np.array([[I_yy, -I_xy], [-I_xy, I_xx]])
    
    #Calculate the eigenvalues and eigenvectors
    eigenvalues, eigenvectors = np.linalg.eig(I)
    lowest = eigenvalues.argmin()
    maj_axis = eigenvectors[:, lowest]
    
    #Get the angle we need to rotate by
    theta_z = -np.arctan2(maj_axis[1], maj_axis[0])
    
    #This analytical calculation is the same so print out just to check
    #Might be 180 degrees off
#    r_angle2 = np.degrees(0.5 * np.arctan2(2*I_xy, I_xx-I_yy))
    
    #Now rotate the galaxy so that the bar lies along the x axis
    #Rotate about z
#    if rotate_model == True:
#        sn.rotate_z(-r_angle1)    

    #Rotate theta_z about the z axis
    rot = np.array([[np.cos(theta_z), -np.sin(theta_z), 0],
                    [np.sin(theta_z),  np.cos(theta_z), 0],
                    [              0,                0, 1]])
    #Put x y z vx vy vz together            
    pos = np.column_stack( (Data['x'], Data['y'], Data['z']) )
    vel = np.column_stack( (Data['vx'], Data['vy'], Data['vz']) )
    
    #Execute the rotation
    #If we were analysing velocities we would need to do the same with those
    pos_r = rot.dot(pos.T).T
    vel_r = rot.dot(vel.T).T

    x, y, z = pos_r[:,0], pos_r[:,1], pos_r[:,2]
    vx, vy, vz = vel_r[:,0], vel_r[:,1], vel_r[:,2]
    m = Data['m']
    
    Data2 = np.column_stack( (x, y, z, vx, vy, vz, m) )
    Data2.dtype = Data.dtype
   
    return Data2, theta_z

    