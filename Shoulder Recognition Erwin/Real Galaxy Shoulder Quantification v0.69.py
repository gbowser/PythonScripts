#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RUN THE SHOULDER QUANTIFICATION ALGORITHM IN OBSERVED GALAXY MAJOR AXIS PROFILES
THE PROFILE REQUIRE TWO COLUMNS
1. THE MAJOR AXIS COORDINATE, IDEALLY AS A FRACTION OF THE BAR RADIUS
2. LOG FLUX OR MAGNITUDE

ASSUMES THREE ROWS AS HEADERS TO IGNORE

"""

import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy import signal
import pandas as pd

def find_nearest(array, value):
    #Find the value nearest to 'value' in the array
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return array[idx]        


allow_1_sided_shoulders = False

# Where are the profiles?
data_folder = '/Users/stuartanderson/Documents/Astronomy/Projects/Action_Space/Data'

# Where do the plots land?
output_folder = '/Users/stuartanderson/Documents/Astronomy/Projects/Density_Shoulder/Output/Erwin Galaxies'

os.chdir(data_folder)
  
# Which subfolder are the galaxy profiles held in?
# gal_folder = 'Erwin_Sep2020'
# gal_folder = 'Erwin_S0_low_i'
# gal_folder = 'Erwin_S0'
# gal_folder = 'Erwin_final'
# gal_folder = 'Erwin_2020-11-16'
gal_folder = 'Yasmin'

galaxy_folder = os.path.join(data_folder, gal_folder)
#Output plot(s) filename root
plot_file_1 = (os.path.join(output_folder, '{0}_shoulders'.format(gal_folder)))


# Use this to record all galaxy profiles in a folder
galaxies = []
for f in os.listdir(galaxy_folder):
    if f.endswith('.dat') and '_bar-major-axis_profile' in f:
         galaxy_name = f.rsplit('.' ,1)[0]
         galaxy_name = galaxy_name.replace('_bar-major-axis_profile','')
         galaxies.append(galaxy_name)

# Three fixed galaxies from Yasmin
galaxies = np.array(['IC1067', 'NGC3681', 'ESO340-017'])
bar_radii = np.array([18.7, 11.9, 29.7])

galaxies_to_plot = galaxies

# Reject shoulders whose clavicle lengths are too small; what is this length
# Zero means keep all shoulders
thin_be_gone = 0.05

Tot = len(galaxies_to_plot)
Cols = 6

# Compute Rows required if we are analysing multiple galaxies
Rows = Tot // Cols 
Rows += Tot % Cols

# Create a plot_position index
plot_position = range(1, Tot + 1)

# ====================================================
# These paramaters are what we sometimes need to tweak
# ====================================================
peaks_max = 12 # 10 seems decent

d_extrema, d2_extrema = 1000, 1000    

# How close to x=0 is too close for a shoulder?
too_close = 0.2

# Run the analysis within a range of x to ensure that our smoothing algorithm is equivalent
x_cutoff_vs_bre = 1.8

# Test for Peter Erwin 25th Sept - more liberal definition
slope_cutoff = 0.35

# ====================================================
# End parameter block
# ====================================================



#Catch all key shoulders parameters
shoulders = []

fs = (10, 10/1.618)
num_sh_found, sh_galaxies = 0, []
for ki, galaxy in enumerate(galaxies_to_plot):
    print(galaxy)
    fig = plt.figure(figsize=fs)

    has_shoulders = False

    grid = fig.add_gridspec(nrows = 2, ncols = 1, 
              hspace = 0.07,  
              height_ratios = [4, 1])
    ax = fig.add_subplot(grid[0,0])
    ax_resid = fig.add_subplot(grid[1,0])

    fname = '{0}_bar-major-axis_profile.dat'.format(galaxy)        
        
    # Load the galaxy's profile
    dtype = {'names': ('x', 'mu'), 'formats': (float, float)}
    Data = np.loadtxt(os.path.join(galaxy_folder, fname),
                      dtype=dtype, skiprows = 3)
    
    # Normalise by the bar radius
    Data['x'] /= bar_radii[ki]
    
    # We're only interested in the area within the bar so go out to 1.8 R_bar
    x = Data['x'][abs(Data['x']) < x_cutoff_vs_bre]
    
    # mu is the SB
    mu = -Data['mu'][abs(Data['x']) < x_cutoff_vs_bre]

    # Some might have nans at the start
    if np.isnan(mu[0]):
        first_non_nan_idx = np.where(~np.isnan(mu))[0][0]
        mu[:first_non_nan_idx] = mu[first_non_nan_idx]

    # Linearly interpolate nans - NEED TO DISCUSS WITH YASMIN
    mu = np.array(pd.DataFrame(mu).interpolate().values.ravel().tolist())
    
    # Normalise mu before we calculate the S_N
    mu_N = (mu - mu.min())/(mu.max() - mu.min())
    
    # Gap between measurements is needed for the derivative calc
    bin_size = np.diff(x)[0]
    bar_extent = 1

    annotation = r'{0}'.format(galaxy)

    # Form a Butterworth low bandpass filter then apply to mu
    x_span = x.max() + abs(x.min())
    
    # Lower Wn = more smoothing
    Wn = 2 / (len(mu)/x_span/2)
    
    # Second order Butterworth smoothing
    N = 2
    
    # Modify for 7424 temp


    failed_extrema = False
    Wn = ( 2 / (len(mu)/x_span/2) )

    # Wn = .042
    # Butterworth = 0.09 is what is used in the simulations but we cannot use it in the real galaxies
    # We cannot use a fixed one here though, as we have a variable number of data points, i.e. a variable
    # number of 'bins'
    Butterworth = ( 2 / (len(mu)/x_span/2) )

    # Butterworth paramaters
    b, a = signal.butter(N, Butterworth, 'lowpass', analog=False)
    
    # Smooth the normalised mu
    smoothed = signal.filtfilt(b, a, mu_N)            

    # The 1st deriv of this smoothed function
    deriv = np.gradient(smoothed, np.diff(x)[0])
    deriv_mu = np.gradient(mu, np.diff(x)[0])
    
    # The second derivative
    deriv2 = np.gradient(deriv, np.diff(x)[0])
    deriv2_mu = np.gradient(mu, np.diff(x)[0])
        
    # Count number of extrema of the slope of the smoothed profile within the bar
    d_extrema = len(find_peaks(abs(deriv[abs(x)<=1]))[0]) + \
                len(find_peaks(-abs(deriv[abs(x)<=1]))[0])
    d2_extrema = len(find_peaks(abs(deriv2[abs(x)<=1]))[0]) + \
                len(find_peaks(-abs(deriv2[abs(x)<=1]))[0])


    if d_extrema > peaks_max:
        failed_extrema = True

    # Normalise the smoothed signal
    smoothed_N = smoothed[abs(x) <= 1]

    smoothed_N = (smoothed - smoothed.min())/(smoothed.max() - smoothed.min())

    # Calculate the roughness parameter from the normalised profile
    S_N_out = np.round(np.sqrt(abs(smoothed)).mean()/np.mean(abs(smoothed)),3)


    # Plot original profile
    ax.plot(x, mu_N, c='k', linewidth=1)

    ax.plot(x, smoothed + 0.03, c='blue', linestyle='--', linewidth=0.75)
    ax.tick_params(labelbottom=False) 
    
    # Plot the residual
    ax_resid.plot(x, smoothed - mu_N, c='r', linewidth=0.75)
    ax_resid.set_ylabel(r'Resid', fontsize=12)
    ax_resid.set_xlabel(r'$x/R_{bar}$', fontsize=12)
    ax_resid.set_ylim(-0.25, 0.25)


    for label in ax_resid.yaxis.get_majorticklabels():
        label.set_fontsize(12)        
    for label in ax_resid.xaxis.get_majorticklabels():
        label.set_fontsize(12)        

    ax2 = ax.twinx()
    ax2.plot(x, deriv, c='green', label=r'd$\mu/$d$x$', linewidth=0.4)


    # Radius of curvature
    roc = ((1 + deriv**2)**1.5) / abs(deriv2)
    roc_mu = ((1 + deriv_mu**2)**1.5) / abs(deriv2_mu)

    # How many minima in roc do we have?
    roc_minima = len(find_peaks(-abs(roc[abs(x)<=1]))[0])


    ax2.plot(x, deriv2, c='r', linestyle=':', label=r'd$^2\mu/$d$x^2$', lw=0.8)
    ax2.set_ylabel('Derivatives', fontsize=12)
    ax2.set_ylim(-3., 3.) # Guess
    ax2.plot(x, roc, c='orange', label=r'Radius of Curvature', lw=0.5)

    #Search for the shoulders
    peaksMax, _ = find_peaks(deriv)       
    peaksMin, _ = find_peaks(-deriv)

    peaks2Max, _ = find_peaks(deriv2)       
    peaks2Min, _ = find_peaks(-deriv2)

    #Find the min and max of the roc
    #Clavicle widths = first minima around clavicle
    #borders of shoulder = first maxima after that
    peaksrocMax, _ = find_peaks(roc)
    peaksrocMin, _ = find_peaks(-roc)


    dmin, dmax = deriv[peaksMin], deriv[peaksMax]
    dminx, dmaxx = x[peaksMin], x[peaksMax]
    d2min, d2max = deriv2[peaks2Min], deriv2[peaks2Max]
    d2minx, d2maxx = x[peaks2Min], x[peaks2Max]

    #Peaks and troughs of radius of curvature
    rocmin, rocmax = roc[peaksrocMin], roc[peaksrocMax]
    rocminx, rocmaxx = x[peaksrocMin], x[peaksrocMax]

    #Find where the second derivative = 0
    d2_zero_idx = np.argwhere(np.diff(np.sign(0 - deriv2))).flatten()
    d2_zero = x[d2_zero_idx]

    # For x < 0, each 1st deriv minimum is a potential shoulder
    # Collect these and then we will examine them to determine the sh

    # Check minima in reverse order, so go from x=0 outwards
    clav_left, clav_right = np.nan, np.nan
    left_outer, left_inner = np.nan, np.nan
    left_inner_slope, left_outer_slope = np.nan, np.nan
    right_outer, right_inner = np.nan, np.nan
    right_outer_slope, right_outer_slope = np.nan, np.nan

    counter = 0
                
    # ORDER IS CRITICAL WE CHECK SLOPES CLOSEST TO 0
    dminleft = np.flip(dmin[dminx < 0])
    dminxleft = np.flip(dminx[dminx < 0])

    # Sort the minima by absolute value ascending
    # Then grab the corresponding x values themselves
    dmin_s = sorted(dminleft, key=abs)
    dminx_s = []
    for dd in dmin_s:
        dminx_s.append(dminxleft[dminleft.tolist().index(dd)])

    print('**** ANALYSING GALAXY {0} ****'.format(galaxy))
    print('ANALYSING LEFT SIDE OF {0}'.format(galaxy))
    
    #Loop through the minima by absolute slope ascending
    for idx, d in enumerate(dmin_s):
        left_outer = np.nan
        left_inner = np.nan
        left_inner_slope = np.nan
        left_outer_slope = np.nan

        #Run through each minimum in order of distance from x=0
        left_slope = d
        clav_left = dminx_s[idx]

        #Clavicle widths = first minima around clavicle
        if len(rocminx[rocminx > clav_left]) > 0 and len(rocminx[rocminx < clav_left]) > 0:
            left_clav_inner = rocminx[rocminx == find_nearest(rocminx[rocminx > clav_left], clav_left)][0]
            left_clav_outer = rocminx[rocminx == find_nearest(rocminx[rocminx < clav_left], clav_left)][0]

            #After skyping with Peter Erwin we concluded that the inner shoulder
            #is marked by the inner clavicle
            left_inner = left_clav_inner
            
            if len(rocmaxx[rocmaxx > left_clav_inner]) > 0 and len(rocmaxx[rocmaxx < left_clav_outer]) > 0:
#                left_inner = rocmaxx[rocmaxx == find_nearest(rocmaxx[rocmaxx > left_clav_inner], left_clav_inner)][0]
                left_outer = rocmaxx[rocmaxx == find_nearest(rocmaxx[rocmaxx < left_clav_outer], left_clav_outer)][0]
                #Test outer border is the next roc min
                if len(rocminx[rocminx < left_clav_outer]) > 0:
                    left_outer = rocminx[rocminx == find_nearest(rocminx[rocminx < left_clav_outer], left_clav_outer)][0]
            else:
                left_inner, left_outer = np.nan, np.nan
                
        else:
            left_clav_inner, left_clav_outer = np.nan, np.nan
            left_inner, left_outer = np.nan, np.nan

        left_inner_slope = deriv[np.where(x == find_nearest(x, left_inner))[0][0]]
        left_outer_slope = deriv[np.where(x == find_nearest(x, left_outer))[0][0]]

        #Discard this shoulder if clavicle part of the shoulder is outside the bar
        #Include the bin size in this calculation
        #Discard also if the shoulder edge and middle are the same
        if clav_left - bin_size > -bar_extent and \
            (clav_left != left_inner and clav_left != left_outer) and \
            abs(left_slope) < slope_cutoff and abs(clav_left) > too_close and \
            failed_extrema == False:
            
            #Too thin? Reject
            if abs(left_outer - left_inner) > thin_be_gone:
                print('Galaxy {0} FOUND LEFT SHOULDER {1}: {2}'.format(galaxy, counter, clav_left))
                
                counter += 1
                #We have found a left shoulder so break
                break
            else:
                clav_left = np.nan
                print('Galaxy {0} potential shoulder (left) rejected - too thin'.format(galaxy))
        elif clav_left - bin_size <= -bar_extent:
            print('Galaxy {0} potential shoulder (left) rejected - outside the bar at {1}'.format(galaxy, clav_left - bin_size))
            clav_left = np.nan
        elif failed_extrema == True:
            print('Galaxy {0} potential shoulder (left) rejected - too many extrema'.format(galaxy))
            clav_left = np.nan
        else:
            print('Galaxy {0} potential shoulder (left) rejected - too weak slope {1}'.format(galaxy, left_slope))
            clav_left = np.nan

    print('\nGalaxy {0} left clav loc {1} with slope {2:1.2f} cutoff {3}\n'.format(galaxy, clav_left, left_slope, slope_cutoff))

    print('ANALYSING RIGHT SIDE OF {0}'.format(galaxy))

    #Same idea but this time for x > 0
    #Search areas for x>0 is between the minima of 1st deriv
    #For x>0 we search the maxima; no need to flip this as the order
    #will naturally be from x = 0 outwards, unlike x<0
    counter = 0
    dmaxxright = dmaxx[dmaxx > 0]
    dmaxright = dmax[dmaxx > 0]

    #Sort the maxima by absolute value ascending
    #Then grab the corresponding x values themselves
    dmax_s = sorted(dmaxright, key=abs)
    dmaxx_s = []
    for dd in dmax_s:
        dmaxx_s.append(dmaxxright[dmaxright.tolist().index(dd)])
    
    for idx, d in enumerate(dmax_s):
        right_outer = np.nan
        right_inner = np.nan
        right_outer_slope = np.nan
        right_inner_slope = np.nan

        #Run through each maximum in order of distance from x=0
        right_slope = d
        clav_right = dmaxx_s[idx]


        #Clavicle widths = first minima around clavicle
        if len(rocminx[rocminx > clav_right]) > 0 and len(rocminx[rocminx < clav_right]) > 0:
            right_clav_inner = rocminx[rocminx == find_nearest(rocminx[rocminx < clav_right], clav_right)][0]
            right_clav_outer = rocminx[rocminx == find_nearest(rocminx[rocminx > clav_right], clav_right)][0]

            #After skyping with Peter Erwin we concluded that the inner shoulder
            #is marked by the inner clavicle
            right_inner = right_clav_inner

            #Borders of shoulder = first maxima after that
            if len(rocmaxx[rocmaxx > right_clav_outer]) > 0 and len(rocmaxx[rocmaxx < right_clav_inner]) > 0:
#                right_inner = rocmaxx[rocmaxx == find_nearest(rocmaxx[rocmaxx < right_clav_inner], right_clav_inner)][0]
                right_outer = rocmaxx[rocmaxx == find_nearest(rocmaxx[rocmaxx > right_clav_outer], right_clav_outer)][0]
                #Test outer border is the next roc min
                if len(rocminx[rocminx > right_clav_outer]) > 0:
                    right_outer = rocminx[rocminx == find_nearest(rocminx[rocminx > right_clav_outer], right_clav_outer)][0]
            else:
                right_inner, right_outer = np.nan, np.nan
                
        else:
            right_clav_inner, right_clav_outer = np.nan, np.nan
            right_inner, right_outer = np.nan, np.nan
            
        #We calculate the inner border as being symmetrical to the outer one so we need
        #to find the slope at that point (will not match a bin centre exactly)
        right_inner_slope = deriv[np.where(x == find_nearest(x, right_inner))[0][0]]
        right_outer_slope = deriv[np.where(x == find_nearest(x, right_outer))[0][0]]

        #Discard this one if clavicle part of the shoulder is outside the bar
        #or if the right outer extent is the same as the centre (clavicle)
        if clav_right + bin_size < bar_extent and \
            (clav_right != right_inner and clav_right != right_outer) and \
            abs(right_slope) < slope_cutoff and abs(clav_right) > too_close and \
            failed_extrema == False:
                
            #Too thin? Reject
            if abs(right_outer - right_inner) > thin_be_gone:
                print('Galaxy {0} FOUND RIGHT SHOULDER {1}: {2}'.format(galaxy, counter, clav_right))

                counter += 1
                break
            else:
                clav_right = np.nan
                print('Galaxy {0} potential shoulder (right) rejected - too thin'.format(galaxy))
        elif clav_right + bin_size >= bar_extent:
            print('Galaxy {0} potential shoulder (right) rejected - outside the bar at {1}'.format(galaxy, clav_right + bin_size))
            clav_right = np.nan
        elif failed_extrema == True:
            print('Galaxy {0} potential shoulder (right) rejected - too many extrema'.format(galaxy))
            clav_right = np.nan
        else:
            print('Galaxy {0} potential shoulder (right) rejected - too weak slope {1}'.format(galaxy, right_slope))
            clav_right = np.nan
                    
    print('\nGalaxy {0} right clav loc {1} with slope {2:1.2f} cutoff {3}\n'.format(galaxy, clav_right, right_slope, slope_cutoff))

#    plt.close()
    

    #Modify the condition according to whether we are allowing 1 sided
    #shoulders or not
    if allow_1_sided_shoulders == False:
        cond = ~np.isnan(clav_left) and ~np.isnan(clav_right)
        cond2 = clav_left >= right_inner or \
            clav_right <= left_inner or \
            abs(clav_left) <= bin_size or abs(clav_right) <= bin_size
    else:
        cond = ~np.isnan(clav_left) or ~np.isnan(clav_right)
        cond2l = (~np.isnan(clav_left) & (clav_left >= right_inner)) or \
                (~np.isnan(clav_left) & (abs(clav_left) <= bin_size)) 
        cond2r = (~np.isnan(clav_right) & (clav_right <= left_inner)) or \
                (~np.isnan(clav_right) & (abs(clav_right) <= bin_size)) 
        cond2 = (cond2l or cond2r)

    #Do we have a ** pair ** of shoulders?
    if cond == True:
        #We must reject shoulders if they overlap which can happen at
        #the start of the simulations
        #We also reject if the shoulders are within bin size of x=0
        if cond2 == True:

            clav_left, left_inner, left_outer, left_slope, left_inner_slope, \
             left_outer_slope, left_excess_1, left_excess_2, \
             left_clav_inner, left_clav_outer = \
             np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, \
             np.nan, np.nan

            clav_right, right_inner, right_outer, right_slope, right_inner_slope, \
             right_outer_slope, right_excess_1, right_excess_2, \
             right_clav_inner, right_clav_outer = \
             np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, \
             np.nan, np.nan

            print('OVERLAPPING OR CLOSE TO x=0 SHOULDERS FOR {0}\n\n'.format(galaxy))
        else:
            has_shoulders = True
            ax.axvline(x=left_inner, c = 'red', linewidth=1)
            ax.axvline(x=left_outer, c = 'red', linewidth=1)
            ax.axvline(x=clav_left, c = 'red', linewidth=2, ls='-.')

            ax.axvline(x=right_inner, c = 'red', linewidth=1)
            ax.axvline(x=right_outer, c = 'red', linewidth=1)
            ax.axvline(x=clav_right, c = 'red', linewidth=2, ls='-.')

            #Plot the clavicles
            yrange = ax2.get_ylim()[1] - ax2.get_ylim()[0]
            ax2.axvline(x=left_clav_inner, ymin = 0.3, ymax = 0.7, c = 'purple', linewidth=2, ls='--')
            ax2.axvline(x=left_clav_outer, ymin = 0.3, ymax = 0.7, c = 'purple', linewidth=2, ls='--')

            ax2.axvline(x=right_clav_inner, ymin = 0.3, ymax = 0.7, c = 'purple', linewidth=2, ls='--')
            ax2.axvline(x=right_clav_outer, ymin = 0.3, ymax = 0.7, c = 'purple', linewidth=2, ls='--')
        
    else:
        clav_left, left_inner, left_outer, left_slope, left_inner_slope, \
         left_outer_slope, left_excess_1, left_excess_2, \
         left_clav_inner, left_clav_outer = \
         np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan

        clav_right, right_inner, right_outer, right_slope, right_inner_slope, \
         right_outer_slope, right_excess_1, right_excess_2, \
         right_clav_inner, right_clav_outer = \
         np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
    
        print('NO SHOULDERS FOR {0}\n\n'.format(galaxy))


    #Save the winning parameters into a numpy file
    shoulders.append((galaxy, clav_left, clav_right, left_inner, left_outer,
            left_slope, right_inner, right_outer, right_slope,
            left_clav_inner, left_clav_outer, right_clav_inner, right_clav_outer)) 

    ax.set_ylabel(r'$\mu_N$', fontsize=12)
    ax.set_ylim(0, 1.1)

    dir_suffix = 'sh_false'
    dir_suffix = ''
    if has_shoulders == False:
        if failed_extrema == True:
            annotation = r'{0}: TOO NOISY{1}$peaks_d$ {2} ;$peaks_{{d2}}$ {3}; roc$_{{min}}$ {4}'.format(galaxy,'\n', d_extrema, d2_extrema, roc_minima)
            fc = 'orange'
        else:
            annotation = r'{0}: NO SHOULDERS{1}$peaks_d$ {2} ;$peaks_{{d2}}$ {3}; roc$_{{min}}$ {4}'.format(galaxy,'\n', d_extrema, d2_extrema, roc_minima)
            annotation = r'{0}: NO SHOULDERS'.format(galaxy)
            fc = 'red'
    else:
        annotation = r'{0}: SHOULDERS{1}$peaks_d$ {2} ;$peaks_{{d2}}$ {3}; roc$_{{min}}$ {4}'.format(galaxy,'\n', d_extrema, d2_extrema, roc_minima)
        annotation = r'{0}: SHOULDERS'.format(galaxy)
        fc='green'
        num_sh_found += 1
        sh_galaxies.append(galaxy)
        dir_suffix= ''

    xrange = ax.get_xlim()[1] - ax.get_xlim()[0]
    yrange = ax.get_ylim()[1] - ax.get_ylim()[0]
    bbox_props = dict(fc = fc, ec = 'k', alpha=0.75)
    ax.text(ax.get_xlim()[0] + xrange * 0.05, 
                    ax.get_ylim()[1] - (yrange * 0.15), annotation, fontsize=8,
                    bbox=bbox_props, c = 'white', weight='bold')        

    ax.tick_params(axis='both', which='major', labelsize=12)
    ax.tick_params(axis='both', which='minor', labelsize=12)
    ax2.tick_params(axis='both', which='major', labelsize=12)
    ax2.tick_params(axis='both', which='minor', labelsize=12)

    #Plot a derivative = 0 line
    ax2.axhline(y=0, c='r', linestyle='--', linewidth = 0.75)

    #Plot a bar (x=1) = 0 line
    ax.axvline(x=1, c='k', linestyle='-.', linewidth = 3)
    ax.axvline(x=-1, c='k', linestyle='-.', linewidth = 3)
    

    #Residual within the bar based on normalised curves  
    rms_i = (smoothed_N[abs(x) <=1] - mu_N[abs(x) <= 1])
    rms = np.sqrt((rms_i**2).sum())
    std = np.round(np.std(rms_i), 2)
    mean = abs(np.mean(mu[abs(x)<1]))

    annotation = r'$peaks_d$ ' + str(d_extrema) + r'; $peaks_{d2}$' + str(d2_extrema)
    xrange = ax_resid.get_xlim()[1] - ax_resid.get_xlim()[0]
    yrange = ax_resid.get_ylim()[1] - ax_resid.get_ylim()[0]
    bbox_props = dict(fc = fc, ec = 'k')

    plot_file_1 = (os.path.join(output_folder, '{0}')).format(galaxies_to_plot[ki])
        
    fig.savefig(plot_file_1, dpi = 100, bbox_inches = 'tight', pad_inches = 0.1)
    print('Plot saved in {}'.format(plot_file_1))
    
    plt.show()
    plt.close()
    fig.clf()


shoulders.append((galaxy, clav_left, clav_right, left_inner, left_outer,
        left_slope, right_inner, right_outer, right_slope,
        left_clav_inner, left_clav_outer, right_clav_inner, right_clav_outer)) 

dt = np.dtype([('galaxy', 'U30'), ('clav_left', float), ('clav_right', float),
               ('left_inner', float), ('left_outer', float), ('left_slope', float),
               ('right_inner', float), ('right_outer', float), ('right_slope', float),
               ('left_clav_inner', float), ('left_clav_outer', float), ('right_clav_inner', float),
               ('right_clav_outer', float)
               ])
shoulders = np.array(shoulders, dtype=dt)

print('Found {0} shoulder systems out of {1}'.format(num_sh_found, len(galaxies)))
print('These are {0}'.format(sh_galaxies))

