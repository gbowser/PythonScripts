#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SHOULDER RECOGNITION ALGORITHM (SRA) USING RADIUS OF CURVATURE
STUART ANDERSON
MAY 2020 PYTHON 3.7

TAKE A NBODY SIMULATION DATASET AND HUNTS FOR SHOULDER-LIKE PROFILE
ALONG THE BAR MAJOR AXIS

SIMULATIONS MUST BE ORIENTED WITH THE BAR ALONG X

GENERAL FLOW

1. CALCULATE LOG DENSITY IN BINS 0.1KPC ALONG X
2. NORMALISE THE RESULTING PROFILE
3. NORMALISE THE X AXIS BINS TO THE BAR RADIUS
4. SMOOTH USING A BUTTERWORTH N=2 FILTER
5. FIND 1ST AND 2ND DERIVATIVES OF THE SMOOTHED PROFILE
6. CALCULATE RADIUS OF CURVATURE R_C
7. USE R_C TO QUANTIFY THE EXTENT OF THE SHOULDER AND CLAVICLE
8. CALCULATE PARAMETERS FOR SHOULDERS FOR X<0 AND X>0
9. SAVE INTO AN ARRAY AND THEN AN OUTPUT FILE 
10. RUN FOR ALL TIMESTEPS SENT AS A PARAMETER INTO THE ALGORITHM

MAY 2022: AMEND FOR RELATIVE HEIGHTS VS hz
THIS MEANS THAT THE PARAMETER by_z_layers CAN BE
'Absolute' OR 'Relative'

"""

import os
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats
from scipy.signal import find_peaks
from scipy import signal
import imageio
import plot_settings as pltset
import model_params as modp
import rotations as rot

DATA_DIR = r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Data'
SINGLE_STARS_FILE = 'D650_stars.npy'
SINGLE_MODEL = 'D'
SINGLE_TIMESTEP = 650
TEMP_OUTPUT_DIR = os.path.join(DATA_DIR, 'Temp')

#Set standard plot settings
pltset.plt_settings()

def find_nearest(array, value):
    #Find the value nearest to 'value' in the array
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return array[idx]        

def convert_pngs_to_animated_gif(filenames, f_out, duration):
    images = []
    for filename in filenames:
        images.append(imageio.imread(filename))
    
    imageio.mimsave(f_out, images, duration = duration, loop = 0)
    
def nan_helper(y):
    """Helper to handle indices and logical indices of NaNs.

    Input:
        - y, 1d numpy array with possible NaNs
    Output:
        - nans, logical indices of NaNs
        - index, a function, with signature indices= index(logical_indices),
          to convert logical indices of NaNs to 'equivalent' indices
    Example:
        >>> # linear interpolation of NaNs
        >>> nans, x= nan_helper(y)
        >>> y[nans]= np.interp(x(nans), x(~nans), y[~nans])
    """
    return np.isnan(y), lambda z: z.nonzero()[0]


def inf_helper(y):
    """Helper to handle indices and logical indices of infs.

    Input:
        - y, 1d numpy array with possible infs
    Output:
        - infs, logical indices of infs
        - index, a function, with signature indices= index(logical_indices),
          to convert logical indices of infs to 'equivalent' indices
    Example:
        >>> # linear interpolation of infs
        >>> infs, x= inf_helper(y)
        >>> y[infs]= np.interp(x(infs), x(~infs), y[~infs])
    """
    return np.isinf(y), lambda z: z.nonzero()[0]


def generate_mask_arrays(data, pctiles, data_name, label_type):
    # The mask will have one less entry than the p array as the mask
    # will cover the spaces between the borders, so same as the qtile names
    # label_type = '%' means labels are % limits
    # label_type = anything else means use the actual limits used
    # Take out any nans in the data
#    p = np.percentile(data, pctiles, axis=0, keepdims=True)
    p = np.percentile(data[~np.isnan(data)], pctiles, axis=0, keepdims=True)
 
    masks = []
    pctile_labels = []
    last_border_label = ''
   
    last_border = 0
    for i, pctile in enumerate(p):
        if i!= 0:
            if i == len(p) - 1:
                # Last bucket is inclusive of upper limit
                masks.append( (data >= last_border) & (data <= pctile[0]) )
                
                if label_type == '%':
                    pctile_labels.append('{0:0.1f}% <= {1} <= {2:0.1f}%'.format(last_border_label, data_name, pctiles[i]))
                else:
                    pctile_labels.append('{0:0.2e} <= {1} <= {2:0.2e}'.format(last_border, data_name, pctile[0]))
                    
            else:
                masks.append( (data >= last_border) & (data < pctile[0]) )
                if label_type == '%':
                    pctile_labels.append('{0:0.1f}% <= {1} <= {2:0.1f}%'.format(last_border_label, data_name, pctiles[i]))
                else:
                    pctile_labels.append('{0:0.2e} <= {1} < {2:0.2e}'.format(last_border, data_name, pctile[0]))
                
        last_border = pctile[0]
        last_border_label = pctiles[i]
 
    # Mask contains the mask for the particles at each pctlile level
    # Labels is the name of the pctile group
    return masks, pctile_labels


def generate_mask_arrays_from_limits(data, limits, data_name, percentiles, pctile_label_type):
    # In this case, mask limits are provided rather than the percentiles
    # it is anticipated that this will be used to generate action percentiles
    # based on the entire stellar population not just in the slice
    # So, limits is the output of the np.percentile function generated from 
    # the entire dataset
 
    masks = []
    pctile_labels = []
    last_border_label= ''
   
    last_border = 0
    for i, limit in enumerate(limits):
        if i!= 0:
            if i == len(limit) - 1:
                # Last bucket is inclusive of upper limit
                masks.append( (data >= last_border) & (data <= limit[0]) )
 
                if pctile_label_type == '%':
                    pctile_labels.append('{0:0.1f}% <= {1} <= {2:0.1f}%'.format(last_border_label, data_name, percentiles[i]))
                else:
                    pctile_labels.append('{0:0.2e} <= {1} <= {2:0.2e}'.format(last_border, data_name, limit[0]))              
#                print(last_border, limit[0], sep=', ')
            else:
                masks.append( (data >= last_border) & (data < limit[0]) )

                if pctile_label_type == '%':
                    pctile_labels.append('{0:0.1f}% <= {1} <= {2:0.1f}%'.format(last_border_label, data_name, percentiles[i]))
                else:
                    pctile_labels.append('{0:0.2e} <= {1} <= {2:0.2e}'.format(last_border, data_name, limit[0]))

#                print(last_border, limit[0], sep=', ')
       
        last_border = limit[0]
        last_border_label = percentiles[i]

    
    # Mask contains the mask for the particles at each pctlile level
    return masks, pctile_labels


"""
THE SHOULDER RECOGNITION ALGORITHM ITSELF
"""
def run_SRA(model=SINGLE_MODEL, t_start=SINGLE_TIMESTEP, t_end=SINGLE_TIMESTEP, plot_derivs=True, generate_shoulders_file=False, 
        by_z_layers=False, override_Data=None, override_bar_extent=None,
        z_slices=None, theta_z=0, theta_x=0, override_folders=None,
        do_animation=True, slice_actions=False, do_plots=True, slope_cutoff=0.4,
        Bin_by_action='JR', Bin_by_label='%', percentiles=np.arange(0, 101, 25),
        y_cut=1., bin_size=0.1, fixed_num_bins=True, Butterworth=0.09, test_extrema=False,
        max_extrema=15):
    """
    RUN THE SHOULDER RECOGNITION ALGORITHM
    PARAMETERS:
        model: model name
        t_start: start of sh run in labelled time stamp not Gyr
        t_end: end of sh run in labelled time not Gyr
        plot_derivs: do we plot the derivatives on the plots or not?
        generate_shoulders_file: do we save off the file containing the shoulder parameters?
        by_z_layers: are we examining shoulders by z layers?
        return_fields: list of fields to return as an array for the times/models chosen
        theta_z, theta_x: rotations so with face on project rotate about z first then x
        to mimic an observation
        override_Data: supply N-body data or let the algo assume standard folder structure
    """

    #SWITCHES AND FLAGS
    
    #Slope cutoff above which no shoulder is detected default is 0.4
#    slope_cutoff = 0.4
    
    #Base factor for the Butterworth filter
    #The higher the number, the more faithful the fit
    #Now held as a parameter and 0.09 is a good one
    #Butterworth = 0.09
    
    #The algo will always find a minimum but we reject shoulders whose clav width is too small
    #How small is too small? Set as a fraction of the bar radial extent
    thin_be_gone = 0.05
    
    #Reject any shoulders whose clavicle centre is within this % of bre near to x=0
    #Set to 0.2 from Erwin & Debattista 2016
    too_close_to_x0 = 0.2
    
    #Extent of the x axis cutoff vs bar radial extent
    x_cutoff_vs_bre = 1.8
    
    #What is the cut in x and y we need? Max and min
    cut_in_y_min, cut_in_y_max = -y_cut, y_cut

    #cuts are used solely to calculation the number of bins
    #the default is 240 bins (+/- 12kpc, 0.1kpc bin width)
    #The actual data cut is +/-L_bar * 1.8 but this parameter is used
    #if we have no bar
    cut_in_x_min, cut_in_x_max = -12., 12.
        
    smoothed_offset = 0.015
#    smoothed_offset = 0
    
    #For the y axis min
    min_y = np.nan
    
    if override_Data is None:
        model_folder = DATA_DIR
        output_folder = DATA_DIR
    
    if override_folders is not None:
        model_folder = override_folders[0]
        output_folder = override_folders[1]

    output_temp = os.path.join(output_folder, 'Temp')
    os.makedirs(output_temp, exist_ok=True)


    if theta_x !=0 or theta_z !=0:
        suffix_rot = '_{0}-{1}'.format(theta_z, theta_x)
    else:
        suffix_rot = ''
    
    #Are we slicing the model by z layer?
    #by_z_layers: False = no z slices
    #by_z_layers: Absolute = z slices by standard layers
    #by_z_layers: Relative = z slices by proportion of h_z
    if by_z_layers is False or by_z_layers == 'None':
        z_slices = [(0, np.inf)]
        shoulders_fname = 'shoulders_roc{0}.npy'.format(suffix_rot)
        descriptor = 'All particles'
    elif by_z_layers == 'Absolute':
        #Add in full profile by a massive range in |z| if z_slices is None else honor what is sent
        if z_slices is None:
            z_slices=[(round(val,2), round(val + 0.25, 2)) for val in np.arange(0, 1.5, 0.25)]
            z_slices.append( (0, np.inf) )
        shoulders_fname = 'shoulders_roc_z_slices{0}.npy'.format(suffix_rot)
        descriptor = 'By z slice' #This will be replaced in the code

    if slice_actions:
        raise ValueError('slice_actions requires an actions file, but this script is configured to use only D650_stars.npy')

    Data_actions = None

    timestamp = [str(SINGLE_TIMESTEP)]
    profiles_for_animation = []

    
    fs = (16, 9)

    #Cuts
    y_cut_min, y_cut_max = cut_in_y_min, cut_in_y_max
    
    #x_cut_min and max are used solely to calculation the number of bins
    #the default is 240 bins (+/- 12kpc, 0.1kpc bin width)
    x_cut_min, x_cut_max = cut_in_x_min, cut_in_x_max
        
    #We require surface density so divisor for pc^-2 is width times x bin
    density_div = (y_cut_max - y_cut_min) * 1000 * bin_size * 1000

        
    # If we have a bar radial extent file, bring that data in
    if override_bar_extent is None:
        bre = []
    else:
        bre = []

    shoulders = []
    
    
    for t in timestamp:
        
        if do_plots:
            fig, axes = plt.subplots(1, 1, figsize=fs)
            ax = axes 

        # If we have the bar radial extent then grab it because we only wish to seek
        # shoulders within the bar so |x| must be less than the max of these two
        if len(bre) > 0:
            bar_ends_phi2 =  bre[(bre['t'] == int(t))]['bar_radial_extent_phi2'][0]
            bar_ends_a2 =  bre[(bre['t'] == int(t))]['bar_radial_extent_a2'][0]

            # Bar extent set to avg of these two
            bar_extent = (bar_ends_phi2 + bar_ends_a2)/2
#            bar_extent = max(bar_ends_phi2, bar_ends_a2)
            
        else:
            if override_bar_extent is not None:
                bar_ends_phi2 = override_bar_extent
                bar_ends_a2 = override_bar_extent
                bar_extent = override_bar_extent
            else:
                bar_ends_phi2 = 0
                bar_ends_a2 = 0
                bar_extent = 0

        if np.isnan(bar_extent):
            bar_extent = 0

        fname = SINGLE_STARS_FILE
        print('\nProcessing {0}'.format(fname))
        
        #We can override the data but only for one timestep
        #This would be used for example in processing a projected profile
        #rather than face on. Ideally the algo would be amended so the data
        #processing were in its own function but that would be a lot of work
        #The override_Data must have all columns needed
        #Need to supply the bar radiant extent also
        if override_Data is not None:
            if t_start == t_end:
                if 'm' not in override_Data.dtype.names:
                    print('To use override data, mass column m must be present')
                    return None
                else:
                    if override_bar_extent is not None:
                        Data = override_Data
                        bar_extent = override_bar_extent
                    else:
                        print('To use override data, override_bre (bar radial extent) must be used also')
                        return None
            else:
                print('To use override data, both timesteps must be the same')
                return None
        else:
            if theta_z != 0 or theta_x !=0:
                #Load the core model data from a .npy file
                Data0 = np.load(os.path.join(model_folder, fname))
                #Does mass exist in the data? Else set to what is in the config and add the column
                Data0 = modp.append_mass_to_data(model, Data0)

                #We rotate about z by deltaPA and then inclination i about the x axis
                theta_zr, theta_xr = np.radians(theta_z), np.radians(-theta_x)
                Data = rot.rotate_model(Data0, theta_zr, theta_xr)
            
                #Put the bar along the x axis for shoulder calculations
                #Don't use inertia tensor! Get angle by algebra then rotate about z
                #Angle in atan(alpha) with alpha = [sin(theta_z) cosi / cos(theta_z)]
                #angle i is theta_x here
                #Apply this to the model and present with the projected bar along x
                #Put into the Data_rot dataset
                angle = np.arctan2(np.sin(theta_zr) * np.cos(theta_xr), np.cos(theta_zr))
                Data_rot = rot.rotate_model(Data, -angle, 0)
                
                #We must also deproject the bar extent

                #We also need to rotate the bre, treat as a point and rotate
                Data_bre_phi2_x1 = np.array( [(-bar_ends_phi2, 0, 0, 0, 0, 0, 0)], dtype=Data_rot.dtype )
                Data_bre_phi2_x1 = rot.rotate_model(Data_bre_phi2_x1, theta_zr, theta_xr)
                
                Data_bre_a2_x1 = np.array( [(-bar_ends_a2, 0, 0, 0, 0, 0, 0)], dtype=Data_rot.dtype )
                Data_bre_a2_x1 = rot.rotate_model(Data_bre_a2_x1, theta_zr, theta_xr)
                
                #At this point we can now get the bar radial extent - equivalent to the other technique
                #Get radial extent as hypot(x', y')
                R_bar_phi = np.hypot(Data_bre_phi2_x1['x'],Data_bre_phi2_x1['y'])[0][0]
                R_bar_a = np.hypot(Data_bre_a2_x1['x'],Data_bre_a2_x1['y'])[0][0]        

                #Now extract the projected bar extent which will be used in the algo
                bar_ends_phi2 = R_bar_phi
                bar_ends_a2 = R_bar_a
                bar_extent = (R_bar_phi + R_bar_a)/2
                
                Data = Data_rot.copy()
                Data_rot = None
            else:
                #Load the core model data from a .npy file
                Data = np.load(os.path.join(model_folder, fname))
                #Does mass exist in the data? Else set to what is in the config and add the column
                Data = modp.append_mass_to_data(model, Data)
            
        if override_Data is None:
            div = modp.model_time_divisor(model)
        else:
            div = 1
        
        t_ann = int(t)/div

        # Bins in x: usually we fix to 240 (+/- 12 / 0.1) but can be changed
        if fixed_num_bins:
            bins = int((x_cut_max - x_cut_min) / bin_size)
        else:
            if bar_extent > 0:
                #If we have a bar and not fixed bins, fix their number from the bar extent * 1.8
                bins = ((2 * bar_extent * x_cutoff_vs_bre) / bin_size)
            else:
                #No bar then use the default
                bins = int((x_cut_max - x_cut_min) / bin_size)

        #Data crunching begins here
        #Extract phase space data for the model
        y, x, z = Data['y'], Data['x'], Data['z']
        vy, vx, vz = Data['vy'], Data['vx'], Data['vz']
        m = Data['m']

        #Only at this point can we get the z layers in relative sense as we need z
        if by_z_layers == 'Relative':
            hz = np.nanstd(Data['z'])
            
            #Range of z slices relative to hz: go up in half hz slices from 0 to 3 sigma, so 6 slices in all
            hz_multiples = [[round(val,2), round(val + 0.5, 2)] for val in np.arange(0, 3, 0.5)]
            z_values = [[round(val,2), round(val + 0.5, 2)] for val in np.arange(0, 3, 0.5)]
            
            for hi in z_values:
                hi[0] *= hz
                hi[1] *= hz
            
            z_slices = [(i[0], i[1]) for i in z_values]
            z_slices.append( (0., np.inf) )
            hz_multiples.append( (0., np.inf) )
                
            shoulders_fname = 'shoulders_roc_z_slices_hz{0}.npy'.format(suffix_rot)
            descriptor = 'By z slice' #This will be replaced in the code
            print('z_slices: {}'.format(z_slices))


        colors = plt.cm.YlOrRd_r(np.linspace(0.3, 1, len(z_slices)))
        colors = plt.cm.copper_r(np.linspace(0.3, 1, len(z_slices)))

        xlab = r'$x$ [kpc]'
        ylab = r'$[\log\Sigma(x,t)]_N$'
        
        #cut in y
        y_keep = (y > y_cut_min) & (y < y_cut_max)

        #Cut in x depends on whether we have a bar or not 
        #We do this because the smoothing changes based on how far out we go
        #so like the observations we go out to a number times the bar radial extent
        #to keep the smoothing consistent between models
        if bar_extent > 0:
            x_keep = (x > -bar_extent * x_cutoff_vs_bre) & (x < bar_extent * x_cutoff_vs_bre)
        else:
            x_keep = (x > x_cut_min) & (x < x_cut_max)
    
        #For the normalisation
        global_keep = (x_keep) & (y_keep)
    
        #Get the density max and min for all layers - and normalise to that for any
        #Subsequent layer analysis
        p_glob_den_bins = stats.binned_statistic(x[global_keep], m[global_keep], 'sum', 
                                             bins=bins)
        density_glob = np.log10(p_glob_den_bins.statistic.T/density_div)
        denmin = np.nanmin(density_glob[~np.isinf(density_glob)])
        denmax = np.nanmax(density_glob[~np.isinf(density_glob)])
    
        ###########################################################
        #Process all the z layers (for the while galaxy use 0 -1e6)
        ###########################################################
        shoulders_found = ''
        for i, slice_ in enumerate(z_slices):
            z_cut_min, z_cut_max = slice_[0], slice_[1]
            z_keep = (abs(z) >= z_cut_min) & (abs(z) <= z_cut_max)
            
            #If we are using relative to hz label as such
            if by_z_layers == 'Relative':
                z_layer_label = r'${0}\leq|z|/hz\leq\enspace{1}$ $({2:1.3f}\leq|z|\leq{3:1.3f}$ kpc$)$'.format(np.min(hz_multiples[i]), 
                        np.max(hz_multiples[i]), z_cut_min, z_cut_max)
            else:
                z_layer_label = r'${0}\leq|z|\leq{1}$ kpc'.format(z_cut_min, z_cut_max)

            descriptor = z_layer_label
        
            ########################
            #Process by action %-ile
            ########################
            if slice_actions and Data_actions is not None:
                #IF we are slicing by actions then do so...
                # We take %-iles from all particles in the galaxy
                # For this mode the percentiles applied are those from ALL particles
                # and not just those in our slice
                bin_by = Data_actions[Bin_by_action]
                p = np.percentile(bin_by[~np.isnan(bin_by)], percentiles, axis=0, keepdims=True)
        
                # Generate the masking arrays based on the limits for ALL particles
                # which have been derived in the np.percentile statement above
                maskst, labels = generate_mask_arrays_from_limits(bin_by, p, 
                                    Bin_by_label, percentiles, Bin_by_label)
                
            else:
                maskst = [True]
    
            # Now plot the actions data based on the percentile masks
            # or, if not doing by action just run for one entry in maskst
            for mk, mask in enumerate(maskst):
                # Cut the data so we only analyse those in the pctile being analysed
                keep1 = (x_keep) & (y_keep) & (z_keep)
                keep = keep1 & mask
    
                x_plot = x[keep]
                m_plot = m[keep]
                
                #We must check we have particles to analyse
                if len(x_plot)==0:
                    print('Zero particle count for {0} at t={1} slice {2}/{3}'.format(model, t, i, mk))
                    break
    
                #Descriptor goes into the shoulder file to aid subsequent plotting
                if slice_actions:
                    descriptor = labels[mk].replace(' % ', ' ' + Bin_by_action + ' ')
                    
                y_plot = y[keep]
                z_plot = z[keep]
                vy_plot = vy[keep]
                vx_plot = vx[keep]
                vz_plot = vz[keep]
                vR = (x * vx + y * vy) / np.hypot(x, y)
        
                R_plot = np.hypot(x_plot, y_plot)
                vR_plot = (x_plot * vx_plot + y_plot * vy_plot) / R_plot  

                #We now need to scale to the bar radial extent so x=1 is the bar radius
                if bar_extent > 0:
                    x_plot /= bar_extent
                else:
                    x_plot /= x_cut_max
                    
                #Capture the mass, and its normalised equivalent
                p_den_bins = stats.binned_statistic(x_plot, m_plot, 'sum', bins=bins)
                density = np.log10(p_den_bins.statistic.T/density_div)
    
                #Capture the peak log density in the model (which will be at x=0)
                peak_den = density.max()
            
                #Normalise the profile so it lies between 0 and 1 (now done for global)
                density_N = (density - denmin)/(denmax - denmin)
                
                #If there is an INF or NAN in here, we need to linearly interpolate
                #otherwise the smoothing will fail
                #NaNs first
                dN2 = density_N.copy()
                nans, temp = nan_helper(dN2)
                dN2[nans]= np.interp(temp(nans), temp(~nans), dN2[~nans])

                #Now infs
                dN3 = dN2.copy()
                infs, temp = inf_helper(dN3)
                dN3[infs]= np.interp(temp(infs), temp(~infs), dN3[~infs])
                
                #Reset the new density profile
                density_N = dN3

                # Get centre of bins
                X0 = p_den_bins.bin_edges[:-1] + np.diff(p_den_bins.bin_edges)/2
                bin_middles = p_den_bins.bin_edges[:-1] + np.diff(p_den_bins.bin_edges)/2
        
                #Use this one if we normalise the density; Lower Wn = more smoothing                
                #Scale the degree of smoothing D6 @ 50 = 1 (8.25kpc)
                #Wn is never less than the baseline
                #No bar?
#                    Wn_scaling = (1. if bar_extent > 8.25 else 8.25/bar_extent)
#                    Wn = Butterworth

                #We will calculate the maximum number of exrema in the derivs
                #If the flag is set we will reject the profile if we have too many
                d_extrema = 1000    

                N = 2
                bb, aa = signal.butter(N, Butterworth, 'lowpass', analog=False)
                
                #Now produce the smoothed signal
                smoothed = signal.filtfilt(bb, aa, density_N)
    
                # Plot the 1st deriv of this smoothed function
                deriv = np.gradient(smoothed, np.diff(X0)[0])
                deriv2 = np.gradient(deriv, np.diff(X0)[0])
                
                #Count number of extrema of the slope of the smoothed profile within the bar
                failed_extrema = False
                d_extrema = len(find_peaks(abs(deriv[abs(bin_middles)<=1]))[0]) + \
                            len(find_peaks(-abs(deriv[abs(bin_middles)<=1]))[0])

                #Too many extrema?
                if d_extrema > max_extrema and test_extrema:
                    failed_extrema = True

                #Radius of curvature
                roc = ((1 + deriv**2)**1.5) / abs(deriv2)
                
                #Capture total mass in the model in solar masses
                #Without gas this will remain constant
                mass_G = Data['m'].sum()
                
                #Now that we have calculated the derivatives we can re-expand the
                #x axis to the actual (non normalised) values for the plots and data
                if bar_extent != 0:
                    bin_middles *= bar_extent
                    x_plot *= bar_extent
                else:
                    bin_middles *= x_cut_max
                    x_plot *= x_cut_max

                #When we do the plot we expand once more to kpc on the x axis
                if do_plots:
                    #Without a bar the analysis will have been done out to +/- the limits
                    #with a bar we go out to +/- 1.8 times the bar extent
                    if z_cut_min == 0 and np.isinf(z_cut_max):
                        #Only need to do the full profile in black
                        ax.plot(bin_middles, density_N, c='k', lw=3, alpha=1, label=r'All $|z|$ layers')
                    else:
                        ax.plot(bin_middles, density_N, c=colors[i], lw=2, label=z_layer_label)
                    
                    #Full profile show thicker and no need for the colours
                    if z_cut_min == 0 and np.isinf(z_cut_max):
                        ax.plot(bin_middles, smoothed + smoothed_offset, lw=2, c='b')
                    else:
                        ax.plot(bin_middles, smoothed + smoothed_offset, c=colors[i], linestyle='--')
            
                    if plot_derivs:
                        ax2  = ax.twinx()
                        ax2.plot(bin_middles, deriv, c='green', label=r'd$ log \Sigma(x)/$d$x$', alpha=0.5)               
                        ax2.plot(bin_middles, deriv2, c='purple', linestyle=':',
                                 label=r'd$^2 log \Sigma(x)/$d$x^2$', alpha=0.5)
                        #Scale down the ROC so it fits on ax2's scale and is visible
                        ax2.plot(bin_middles, roc/2, c='orange', 
                                 label=r'Radius of Curvature', alpha=0.5)
                        ax2.set_ylabel(r'Derivatives and $\mathcal{R}_c$')
                        ax2.legend(loc = 1, fontsize=12)
        
                        ax2.set_ylim(-3, 3)

                    ax.set_ylabel(ylab)
                    
                    min_y = np.nanmin( (np.nanmin(density_N), min_y) )
                    
                    #Although we smooth using the fraction of the bar, extent we plot always the same limit
                    #ax.set_xlim(x_cut_min, x_cut_max)
                    if bar_extent > 0:
                        ax.set_xlim(-bar_extent * x_cutoff_vs_bre, bar_extent * x_cutoff_vs_bre)
                    else:
                        ax.set_xlim(-x_cut_min, x_cut_min)

                    ax.set_xlabel(xlab)
        
                    #Insert the bar extent
                    ax.axvline(-bar_extent, c='k', ls='--', lw=3)
                    ax.axvline(bar_extent, c='k', ls='--', lw=3)
        
        
                    if override_Data is None:
                        annotation = r'{0} $t=${1} Gyr'.format(modp.model_name(model), t_ann)
                    else:
                        annotation = r'{0} $t=${1} Gyr'.format(model, t_ann)
                        
            
                    ax.legend(loc = 2, fontsize=12)
        
                # Now find the peaks of the first deriv - on the left shoulder using -deriv
                # and on the right shoulder using deriv as LH has minimum
                # and RH has maximum
                # We need this as a startng point from where we will derive the shoulder
                # width. We start by searching to the left and right of x=0       
        
                # We must only search for shoulders after first maximum on left
                # or the first minimum on the right. This is important in the early timesteps
                # when there is hardly any shape and these indicators are a little flimsy
                peaksMax, _ = find_peaks(deriv)       
                peaksMin, _ = find_peaks(-deriv)
        
                peaks2Max, _ = find_peaks(deriv2)       
                peaks2Min, _ = find_peaks(-deriv2)
                
                #Find the min and max of the roc
                #Clavicle widths = first minima around clavicle
                #borders of shoulder = first maxima after that
                peaksrocMax, _ = find_peaks(roc)
                peaksrocMin, _ = find_peaks(-roc)
        
                #Peaks and troughs of first and second derivatives
                dmin, dmax = deriv[peaksMin], deriv[peaksMax]
                dminx, dmaxx = bin_middles[peaksMin], bin_middles[peaksMax]
        
                #Peaks and troughs of radius of curvature
                rocminx, rocmaxx = bin_middles[peaksrocMin], bin_middles[peaksrocMax]
        
           
                # For x < 0, each 1st deriv minimum is a potential shoulder
                # Collect these and then we will examine them to determine the sh
                
                #Search areas for x<0 is between the maxima of 1st deriv
                #Hunt for the minimum which lies within the bar
                #np.partition(a, 0)[0] gets the lowest entry
                #np.partition(a, 1)[1] gets the second lowest entry etc.
                
                clav_left, clav_right = np.nan, np.nan
                counter = 0
                
                #ORDER IS CRITICAL WE CHECK SLOPES CLOSEST TO 0
                dminleft = np.flip(dmin[dminx < 0])
                dminxleft = np.flip(dminx[dminx < 0])

                #Sort the minima by absolute value ascending
                #Then grab the corresponding x values themselves
                dmin_s = sorted(dminleft, key=abs)
                dminx_s = []
                for dd in dmin_s:
                    dminx_s.append(dminxleft[dminleft.tolist().index(dd)])
                
                print ('Left slope maxima at x={0} (L_bar = {1}) kpc\nSlopes are {2}'.format(np.round(dminx_s,2), np.round(bar_extent), np.round(dmin_s,2)))

                #Loop through the minima by absolute slope ascending so we process those closest to zero first
                for idx, d in enumerate(dmin_s):
                    left_outer = np.nan
                    left_inner = np.nan
                    left_inner_slope = np.nan
                    left_outer_slope = np.nan
        
                    
                    #Run through each minimum in order of distance from x=0
                    left_slope = d
#                    clav_left = dminx[np.where(abs(dmin) == left_slope)][0]
                    clav_left = dminx_s[idx]
        
                    #Clavicle widths = first minima around clavicle
                    if len(rocminx[rocminx > clav_left]) > 0 and len(rocminx[rocminx < clav_left]) > 0:
                        left_clav_inner = rocminx[rocminx == find_nearest(rocminx[rocminx > clav_left], clav_left)][0]
                        left_clav_outer = rocminx[rocminx == find_nearest(rocminx[rocminx < clav_left], clav_left)][0]
            
                        #After Skype with Peter Erwin 19/Dec/2019 we will set the
                        #inner shouldr border = inner clavicle border
                        left_inner = left_clav_inner
            
                        #Borders of the shoulder = first ROC maximum after that
                        if len(rocmaxx[rocmaxx > left_clav_inner]) > 0 and len(rocmaxx[rocmaxx < left_clav_outer]) > 0:
                            left_outer = rocmaxx[rocmaxx == find_nearest(rocmaxx[rocmaxx < left_clav_outer], left_clav_outer)][0]
                            #Test outer border is the next roc min
                            if len(rocminx[rocminx < left_clav_outer]) > 0:
                                left_outer = rocminx[rocminx == find_nearest(rocminx[rocminx < left_clav_outer], left_clav_outer)][0]

                            #If outer or inner are still not defined then we have no shoulder
                            if np.isnan(left_inner) or np.isnan(left_outer):
                                clav_left, left_inner, left_outer = np.nan, np.nan, np.nan

                        else:
                            #Cannot find a maximum in the ROC outside the clavicle outer border so ditch the shoulder
                            #Could be the cut in x is too small of course
                            clav_left, left_inner, left_outer = np.nan, np.nan, np.nan
                            
                    else:
                        #No minima of ROC around the clavicle - reject the shoulder
                        #FIX 7/12/2020
                        left_clav_inner, left_clav_outer = np.nan, np.nan
                        clav_left, left_inner, left_outer = np.nan, np.nan, np.nan
        
                    left_inner_slope = deriv[np.where(bin_middles == find_nearest(bin_middles, left_inner))[0][0]]
                    left_outer_slope = deriv[np.where(bin_middles == find_nearest(bin_middles, left_outer))[0][0]]
        
                    #Discard this shoulder if clavicle part of the shoulder is outside the bar
                    #Discard also if the shoulder edge and middle are the same
                    #CHANGE FOR SHRUGGED SHOULDERS - SLOPE IS FLAT OR SHRUGGED SO CONDITION NO LONGER USES ABS
                    #NEGATIVE SLOPE ON THE LEFT MEANS SHRUGGED SHOULDER, 7/May/2020
                    if np.round(clav_left, 1) > -np.round(bar_extent, 1) and \
                        (clav_left != left_inner and clav_left != left_outer) and \
                        left_slope < slope_cutoff and not failed_extrema:
                        
                        #Too thin? Reject
#                        if abs(left_outer - left_inner)/bar_extent <= thin_be_gone:
                        if abs(left_clav_outer - left_clav_inner)/bar_extent <= thin_be_gone:
                            clav_left = np.nan
                            print('Shoulder (left) rejected - too thin slice {0}/{1}'.format(i, mk))
                        elif abs(clav_left)/bar_extent <= too_close_to_x0:
                            clav_left = np.nan
                            print('Shoulder (left) rejected - too close to x=0 slice {0}/{1}'.format(i, mk))
                        else:
                            print('LEFT SHOULDER RECOGNISED {0}: x={1}kpc at timestep {2} slice {3}/{4} extrema {5} model {6}{7}'.format(counter, 
                                  round(clav_left, 2), t, i, mk, d_extrema, model, '\n'))

                            counter += 1
                            #We have found a left shoulder so break
                            break
                    elif failed_extrema:
                        print('Potential shoulder (left) rejected - too many extrema {0} in the first derivative'.format(d_extrema))
                        clav_left = np.nan
                    elif not(left_slope < slope_cutoff):
                        clav_left = np.nan
                        print('Shoulder (left) rejected - slope too positive slice {0}/{1}'.format(i, mk))
                    else:
                        clav_left = np.nan
                        print('Shoulder (left) rejected - outside the bar slice {0}/{1}'.format(i, mk))
                    
        
                #Same idea but this time for x > 0
                #Search areas for x>0 is between the minima of 1st deriv
                #For x>0 we search the maxima; no need to flip this as the order
                #will naturally be from x = 0 outwards, unlike x<0
                counter = 0
                dmaxxright = dmaxx[dmaxx > 0]
                dmaxright = dmax[dmaxx > 0]

                #Sort the maxima by absolute value ascending so we process those closest to 0 first
                #Then grab the corresponding x values themselves
                dmax_s = sorted(dmaxright, key=abs)
                dmaxx_s = []
                for dd in dmax_s:
                    dmaxx_s.append(dmaxxright[dmaxright.tolist().index(dd)])
                
                print ('Right slope maxima at x={0} (L_bar = {1}) kpc\nSlopes are {2}'.format(np.round(dmaxx_s,2), np.round(bar_extent), np.round(dmax_s,2)))


#                for idx, d in enumerate(dmax[dmaxx > 0]):
                for idx, d in enumerate(dmax_s):
                    right_outer = np.nan
                    right_inner = np.nan
                    right_outer_slope = np.nan
                    right_inner_slope = np.nan
        
                    #Find the idx'th minimum (rev sign as we want max)
#                    right_slope = -np.partition(-dmax[dmaxx > 0], idx)[idx]
                    
                    #Run through each maximum in order of distance from x=0
                    right_slope = d
#                    clav_right = dmaxx[np.where(dmax == right_slope)][0]
#                    clav_right = dmaxxright[idx]
                    clav_right = dmaxx_s[idx]
      
                    #Shoulder border = first ROC minimum around clavicle
                    if len(rocminx[rocminx > clav_right]) > 0 and len(rocminx[rocminx < clav_right]) > 0:
                        right_clav_inner = rocminx[rocminx == find_nearest(rocminx[rocminx < clav_right], clav_right)][0]
                        right_clav_outer = rocminx[rocminx == find_nearest(rocminx[rocminx > clav_right], clav_right)][0]
            
                        #After Skype with Peter Erwin 19/Dec/2019 we will set the
                        #inner shouldr border = inner clavicle border
                        right_inner = right_clav_inner
    
                        #Borders of shoulder = first maxima after the outer border of the clavicle
                        if len(rocmaxx[rocmaxx > right_clav_outer]) > 0 and len(rocmaxx[rocmaxx < right_clav_inner]) > 0:
    #                            right_inner = rocmaxx[rocmaxx == find_nearest(rocmaxx[rocmaxx < right_clav_inner], right_clav_inner)][0]
                            right_outer = rocmaxx[rocmaxx == find_nearest(rocmaxx[rocmaxx > right_clav_outer], right_clav_outer)][0]
                            #Test outer border is the next roc min
                            if len(rocminx[rocminx > right_clav_outer]) > 0:
                                right_outer = rocminx[rocminx == find_nearest(rocminx[rocminx > right_clav_outer], right_clav_outer)][0]
                                
                            #If outer or inner are still not defined then we have no shoulder
                            if np.isnan(right_inner) or np.isnan(right_outer):
                                clav_right, right_inner, right_outer = np.nan, np.nan, np.nan
                            
                        else:
                            #Cannot find a maximum in the ROC outside the clavicle outer border so ditch the shoulder
                            #Could be the cut in x is too small of course
                            clav_right, right_inner, right_outer = np.nan, np.nan, np.nan
                            
                    else:
                        #No minima of ROC around the clavicle - reject the shoulder
                        #FIX 7/12/2020
                        right_clav_inner, right_clav_outer = np.nan, np.nan
                        clav_right, right_inner, right_outer = np.nan, np.nan, np.nan
                        
                    #We calculate the inner border as being symmetrical to the outer one so we need
                    #to find the slope at that point (will not match a bin centre exactly)
                    right_inner_slope = deriv[np.where(bin_middles == find_nearest(bin_middles, right_inner))[0][0]]
                    right_outer_slope = deriv[np.where(bin_middles == find_nearest(bin_middles, right_outer))[0][0]]
        
                    #Discard this one if clavicle part of the shoulder is outside the bar
                    #or if the right outer extent is the same as the centre (clavicle)
                    #CHANGE FOR SHRUGGED SHOULDERS - SLOPE IS FLAT OR SHRUGGED SO CONDITION NO LONGER USES ABS, 7/May/2020
                    #POSITIVE SLOPE ON THE RIGHT MEANS SHRUGGED SHOULDER. SO NOT ABS(SLOPE) < CUTOFF BUT SLOPE > -CUTOFF
                    if np.round(clav_right, 1) < np.round(bar_extent, 1) and \
                        (clav_right != right_inner and clav_right != right_outer) and \
                        right_slope > -slope_cutoff and not failed_extrema:
                            
                        #Too thin? Reject
#                        if abs(right_outer - right_inner)/bar_extent <= thin_be_gone:
                        if abs(right_clav_outer - right_clav_inner)/bar_extent <= thin_be_gone:
                            clav_right = np.nan
                            print('Shoulder (right) rejected - too thin slice {0}/{1}'.format(i, mk))
                        elif abs(clav_right)/bar_extent <= too_close_to_x0:
                            clav_right = np.nan
                            print('Shoulder (right) rejected - too close to x=0 slice {0}/{1}'.format(i, mk))
                        else:
                            print('RIGHT SHOULDER RECOGNISED {0}: x={1}kpc at timestep {2} slice {3}/{4} extrema {5} model {6}{7}'.format(counter, 
                                  round(clav_right,2), t, i, mk, d_extrema, model, '\n'))
        
                            counter += 1
                            break
                    elif failed_extrema:
                        print('Potential shoulder (right) rejected - too many extrema {0} in the first derivative'.format(d_extrema))
                        clav_right = np.nan
                    elif not(right_slope > -slope_cutoff):
                        clav_right = np.nan
                        print('Shoulder (right) rejected - slope too negative slice {0}/{1}'.format(i, mk))
                    else:
                        clav_right = np.nan
                        print('Shoulder (right) rejected - outside the bar slice {0}/{1}'.format(i, mk))
                            
        
        #        fig2.savefig(plot_file_2)
        #        derivs_for_animation.append(plot_file_2 + '.png')
                #Do we have a ** pair ** of shoulders?
                if ~np.isnan(clav_left) and ~np.isnan(clav_right):
                    #We must reject shoulders if they overlap which can happen at
                    #the start of the simulations
                    #We also reject if the shoulders are within 20% of the bar length of x=0 based on Erwin & Debattista (2016)
                    #Do not set peak_den or mass_G which we will record regardless of whether
                    #we have shoulders or not for further analysis
                    if clav_left >= right_inner or \
                        clav_right <= left_inner or \
                        abs(clav_left) <= too_close_to_x0 or abs(clav_right) <= too_close_to_x0:
    

                        #Set variables to nan as no shoulders here
                        clav_left, left_inner, left_outer, left_slope, left_inner_slope, \
                        left_outer_slope, left_excess_1, left_excess_2, \
                        left_clav_inner, left_clav_outer, \
                        clav_right, right_inner, right_outer, right_slope, right_inner_slope, \
                        right_outer_slope, right_excess_1, right_excess_2, \
                        right_clav_inner, right_clav_outer, \
                        mass_bar_cut_l, mass_bar_cut_r, mass_clav_l, \
                        mass_clav_r, mass_sh_l, mass_sh_r, \
                        mass_centre_l, mass_centre_r, \
                        sigz_clav, sigz_sh, sigR_clav, sigR_sh, hz_clav, hz_sh, hR_clav, hR_sh, \
                        med_abs_z_G, med_abs_z_x_cut, med_abs_z_clav, \
                        med_abs_z_sh, med_abs_z_centre, L_G, L_x_cut, L_sh, L_clav, \
                        med_abs_vz_G, med_abs_vz_x_cut, med_abs_vz_sh, med_abs_vz_clav, \
                        med_abs_vR_G, med_abs_vR_x_cut, med_abs_vR_sh, med_abs_vR_clav, \
                        med_vR_G, med_vR_x_cut, med_vR_sh, med_vR_clav, \
                        mass_bar_cut, mass_clav, mass_sh, mass_centre, \
                        left_excess, right_excess, excess, left_excess_max, right_excess_max, \
                        left_excess_den, right_excess_den, left_clav_den, right_clav_den, \
                        sigz_clav_l, sigz_sh_l, sigR_clav_l, sigR_sh_l, hz_clav_l, \
                        hz_sh_l, hR_clav_l, hR_sh_l, sigz_clav_r, sigz_sh_r, sigR_clav_r, \
                        sigR_sh_r, hz_clav_r, hz_sh_r, hR_clav_r, hR_sh_r, \
                        med_abs_vz_sh_l, med_abs_vz_clav_l, med_abs_vz_sh_r, med_abs_vz_clav_r, \
                        med_abs_z_clav_l, med_abs_z_sh_l, med_abs_z_clav_r, med_abs_z_sh_r, \
                        med_abs_vR_sh_l, med_abs_vR_clav_l, med_abs_vR_sh_r, med_abs_vR_clav_r, \
                        med_vR_sh_l, med_vR_clav_l, med_vR_sh_r, med_vR_clav_r, \
                        L_sh_l, L_clav_l, L_sh_r, L_clav_r, \
                        strength_left, strength_right, strength_total, \
                        sh_width_left, sh_width_right,\
                        clav_width_left, clav_width_right = (np.nan,) * 113
                        
                        print('OVERLAPPING OR CLOSE TO x=0 SHOULDERS AT t={0} slice {1}'.format(t, i))
                    else:
                        #################
                        # SHOUDLERS FOUND
                        #################
                        #Plot the shoulders and the clavicle
                        if do_plots:
                            
                            shoulders_found += r'{0} ${1:1.3f}\leq|z|\leq {2:1.3f}$ kpc shoulders'.format('\n', z_cut_min, z_cut_max)

                            if override_Data is None:
                                annotation = r'{0} $t=${1} Gyr{2}Slope L: {3}{4}Slope R:{5}'.format(modp.model_name(model), \
                                 t_ann, '\n', round(left_slope,3),'\n', round(right_slope,3))
                            else:
                                annotation = r'{0} $t=${1} Gyr{2}Slope L: {3}{4}Slope R:{5}'.format(model, \
                                 t_ann, '\n', round(left_slope,3),'\n', round(right_slope,3))
                                

                            ax.axvline(x=left_inner, c = 'red', linewidth=2)
                            ax.axvline(x=left_outer, c = 'red', linewidth=2)
                            ax.axvline(x=clav_left, c = 'red', linewidth=3, ls='-.')
#                            ax.axvline(x=clav_left, linewidth=2, ls='-.')
                
                            ax.axvline(x=right_inner, c = 'red', linewidth=2)
                            ax.axvline(x=right_outer, c = 'red', linewidth=2)
                            ax.axvline(x=clav_right, c = 'red', linewidth=3, ls='-.')
#                            ax.axvline(x=clav_right, linewidth=2, ls='-.')
            
                            #Plot the clavicles
#                            yrange = ax2.get_ylim()[1] - ax2.get_ylim()[0]
#                            ax2.axvline(x=left_clav_inner, ymin = 0.3, ymax = 0.7, c = 'purple', linewidth=2, ls='-.')
#                            ax2.axvline(x=left_clav_outer, ymin = 0.3, ymax= 0.7, c = 'purple', linewidth=2, ls='-.')
#                
#                            ax2.axvline(x=right_clav_inner, ymin = 0.3, ymax = 0.7, c = 'purple', linewidth=2, ls='-.')
#                            ax2.axvline(x=right_clav_outer, ymin = 0.3, ymax = 0.7, c = 'purple', linewidth=2, ls='-.')
         
                            yrange = ax.get_ylim()[1] - ax.get_ylim()[0]
                            ax.axvline(x=left_clav_inner, ymin = 0.3, ymax = 0.7, c = 'purple', linewidth=2, ls='-.')
                            ax.axvline(x=left_clav_outer, ymin = 0.3, ymax= 0.7, c = 'purple', linewidth=2, ls='-.')
                
                            ax.axvline(x=right_clav_inner, ymin = 0.3, ymax = 0.7, c = 'purple', linewidth=2, ls='-.')
                            ax.axvline(x=right_clav_outer, ymin = 0.3, ymax = 0.7, c = 'purple', linewidth=2, ls='-.')
        
                        #Miscellaneous calculations pertinent only to the sims and models
                        #These will be captured as part of the correlation studies and others
                                                
                        #Clav densities
                        left_clav_den = density[bin_middles == find_nearest(bin_middles, clav_left)][0]
                        right_clav_den = density[bin_middles == find_nearest(bin_middles, clav_right)][0]
                
                        #Capture mass in the bar (crudely defined)
                        mass_bar_cut_l = m_plot[(x_plot <= 0) & (x_plot >= -bar_extent)].sum()
                        mass_bar_cut_r = m_plot[(x_plot > 0) & (x_plot <= bar_extent)].sum()
                        mass_bar_cut = mass_bar_cut_l + mass_bar_cut_r
        
                        #Capture mass in the clavicle
                        mass_clav_l = (m_plot[(x_plot <= left_clav_inner) & (x_plot >= left_clav_outer)]).sum()
                        mass_clav_r = (m_plot[(x_plot >= right_clav_inner) & (x_plot <= right_clav_outer)]).sum()
                        mass_clav = mass_clav_l + mass_clav_r
        
                        #Capture mass in the shoulder
                        mass_sh_l = (m_plot[(x_plot <= left_inner) & (x_plot >= left_outer)]).sum()
                        mass_sh_r = (m_plot[(x_plot >= right_inner) & (x_plot <= right_outer)]).sum()
                        mass_sh = mass_sh_l + mass_sh_r
        
                        #Capture mass in the central area, i.e. between the two inner shoulder borders
                        mass_centre_l = (m_plot[(x_plot >= left_inner) & (x_plot <=0)]).sum()
                        mass_centre_r = (m_plot[(x_plot >= 0) & (x_plot <= right_inner)]).sum()
                        mass_centre = mass_centre_l + mass_centre_r
        
                        keep_clav = (x_plot <= left_clav_inner) & (x_plot >= left_clav_outer) | \
                                    (x_plot >= right_clav_inner) & (x_plot <= right_clav_outer)
                        keep_sh = (x_plot <= left_inner) & (x_plot >= left_outer) | \
                                    (x_plot >= right_inner) & (x_plot <= right_outer)
                        keep_centre = (x_plot >= left_inner) & (x_plot <= right_inner)
                        
                        keep_clav_l = (x_plot <= left_clav_inner) & (x_plot >= left_clav_outer)
                        keep_sh_l = (x_plot <= left_inner) & (x_plot >= left_outer)
                        keep_clav_r = (x_plot >= right_clav_inner) & (x_plot <= right_clav_outer)
                        keep_sh_r = (x_plot >= right_inner) & (x_plot <= right_outer)
                        
                        keep_centre = (x_plot >= left_inner) & (x_plot <= right_inner)
     
    
                        #Anisotropy parameters
                        sigz_clav = np.std(vz_plot[keep_clav])
                        sigz_sh = np.std(vz_plot[keep_sh])
                        sigR_clav = np.std(vR_plot[keep_clav])
                        sigR_sh = np.std(vR_plot[keep_sh])
                        hz_clav = np.std(z_plot[keep_clav])
                        hz_sh = np.std(z_plot[keep_sh])
                        hR_clav = np.std(R_plot[keep_clav])
                        hR_sh = np.std(R_plot[keep_sh])
                        
                        #**
                        sigz_clav_l = np.std(vz_plot[keep_clav_l])
                        sigz_sh_l = np.std(vz_plot[keep_clav_l])
                        sigR_clav_l = np.std(vR_plot[keep_clav_l])
                        sigR_sh_l = np.std(vR_plot[keep_clav_l])
                        hz_clav_l = np.std(z_plot[keep_clav_l])
                        hz_sh_l = np.std(z_plot[keep_clav_l])
                        hR_clav_l = np.std(R_plot[keep_clav_l])
                        hR_sh_l = np.std(R_plot[keep_clav_l])
                        
                        #**
                        sigz_clav_r = np.std(vz_plot[keep_clav_r])
                        sigz_sh_r = np.std(vz_plot[keep_clav_r])
                        sigR_clav_r = np.std(vR_plot[keep_clav_r])
                        sigR_sh_r = np.std(vR_plot[keep_clav_r])
                        hz_clav_r = np.std(z_plot[keep_clav_r])
                        hz_sh_r = np.std(z_plot[keep_clav_r])
                        hR_clav_r = np.std(R_plot[keep_clav_r])
                        hR_sh_r = np.std(R_plot[keep_clav_r])
    
                        #Median abs height
                        med_abs_z_G = np.median(abs(z))
                        med_abs_z_x_cut = np.median(abs(z_plot))
                        med_abs_z_clav = np.median(abs(z_plot[keep_clav]))
                        med_abs_z_sh = np.median(abs(z_plot[keep_sh]))
                        med_abs_z_centre = np.median(abs(z_plot[keep_centre]))
    
                        #**
                        med_abs_z_clav_l = np.median(abs(z_plot[keep_clav_l]))
                        med_abs_z_sh_l = np.median(abs(z_plot[keep_sh_l]))
                        med_abs_z_clav_r = np.median(abs(z_plot[keep_clav_r]))
                        med_abs_z_sh_r = np.median(abs(z_plot[keep_sh_r]))
                       
                        #Angular momentum in the cuts and globally
                        L_G = (m * (x * vy - y * vx)).sum()
                        L_x_cut = (m_plot * (x_plot * vy_plot - y_plot * vx_plot)).sum()
                        L_sh = (m_plot[keep_sh] *(x_plot[keep_sh] * vy_plot[keep_sh] - y_plot[keep_sh] * vx_plot[keep_sh])).sum()
                        L_clav = (m_plot[keep_clav] * (x_plot[keep_clav] * vy_plot[keep_clav] - y_plot[keep_clav] * vx_plot[keep_clav])).sum()
    
                        #**
                        L_sh_l = (m_plot[keep_sh_l] * (x_plot[keep_sh_l] * vy_plot[keep_sh_l] - \
                                      y_plot[keep_sh_l] * vx_plot[keep_sh_l])).sum()
                        L_clav_l = (m_plot[keep_clav_l] * (x_plot[keep_clav_l] * vy_plot[keep_clav_l] - \
                                    y_plot[keep_clav_l] * vx_plot[keep_clav_l])).sum()
                        L_sh_r = (m_plot[keep_sh_r] * (x_plot[keep_sh_r] * vy_plot[keep_sh_r] - \
                                      y_plot[keep_sh_r] * vx_plot[keep_sh_r])).sum()
                        L_clav_r = (m_plot[keep_clav_r] * (x_plot[keep_clav_r] * vy_plot[keep_clav_r] - \
                                    y_plot[keep_clav_r] * vx_plot[keep_clav_r])).sum()
        
                        #Median abs vz
                        med_abs_vz_G = np.median(abs(vz))
                        med_abs_vz_x_cut = np.median(abs(vz_plot))
    
                        med_abs_vz_sh = np.median(abs(vz_plot[keep_sh]))
                        med_abs_vz_clav = np.median(abs(vz_plot[keep_clav]))
    
                        #**
                        med_abs_vz_sh_l = np.median(abs(vz_plot[keep_sh_l]))
                        med_abs_vz_clav_l = np.median(abs(vz_plot[keep_clav_l]))
                        med_abs_vz_sh_r = np.median(abs(vz_plot[keep_sh_r]))
                        med_abs_vz_clav_r = np.median(abs(vz_plot[keep_clav_r]))
    
                        
                        #Median abs vR
                        med_abs_vR_G = np.median(abs(vR))
                        med_abs_vR_x_cut = np.median(abs(vR_plot))
    
                        med_abs_vR_sh = np.median(abs(vR_plot[keep_sh]))
                        med_abs_vR_clav = np.median(abs(vR_plot[keep_clav]))
        
                        #**
                        med_abs_vR_sh_l = np.median(abs(vR_plot[keep_sh_l]))
                        med_abs_vR_clav_l = np.median(abs(vR_plot[keep_clav_l]))
                        med_abs_vR_sh_r = np.median(abs(vR_plot[keep_sh_r]))
                        med_abs_vR_clav_r = np.median(abs(vR_plot[keep_clav_r]))
    
                        #Median vR
                        med_vR_G = np.median(vR)
                        med_vR_x_cut = np.median(vR_plot)
                        med_vR_sh = np.median(vR_plot[keep_sh])
                        med_vR_clav = np.median(vR_plot[keep_clav])
        
                        #**
                        med_vR_sh_l = np.median(vR_plot[keep_sh_l])
                        med_vR_clav_l = np.median(vR_plot[keep_clav_l])
                        med_vR_sh_r = np.median(vR_plot[keep_sh_r])
                        med_vR_clav_r = np.median(vR_plot[keep_clav_r])
    
                        #Output left and right strength parameters
#                        ls = left_slope
#                        rs = right_slope
#                        lis = left_inner_slope
#                        los = left_outer_slope
#                        ris = right_inner_slope
#                        ros = right_outer_slope
#                        
#                        strength_left = (abs((lis - ls)) + abs((los - ls)))/2
#                        strength_right = (abs((ris - rs)) + abs((ros - rs)))/2
#                        strength = (strength_left + strength_right)/2
# 
                        #Shoulder and clavicle widths
                        sh_width_left = abs(abs(left_outer) - abs(left_inner))
                        sh_width_right = abs(abs(right_outer) - abs(right_inner))
                        
                        clav_width_left = abs(abs(left_clav_outer) - abs(left_clav_inner))
                        clav_width_right = abs(abs(right_clav_outer) - abs(right_clav_inner))

    
                        #We now have a shoulder so do the excess mass calculation
                        #Draw the line for visual aid
                        #For the slope, ****** INSERT HERE ***** is left_inner_slope (x<0)
                        #and right_inner_slope (x>0)
                        #We need the value of density at point left_inner
                        #Constant c is y - mx; plot line from x = where left_outer meets the profile
                        #to left_inner
                        #Where does left_outer meet the profile?
    #                        lower_density = smoothed[bin_middles == left_outer][0]
    
#                        lower_density = smoothed[bin_middles >= left_outer][0]
#                        higher_density = smoothed[bin_middles >= left_inner][0]
                        lower_density = smoothed[bin_middles >= left_outer][0]
                        higher_density = smoothed[bin_middles >= left_inner][0]
                        
                        linear_slope = (higher_density - lower_density) / abs((left_outer - left_inner))
    
                        const = smoothed[bin_middles == left_inner][0] - \
                            (linear_slope * left_inner)
    
                        x_values = np.linspace(left_outer, left_inner, 100)
    #                        y_values = left_inner_slope * x_values + const
                        y_values = linear_slope * x_values + const
                        
                        if do_plots:
                            ax.plot(x_values, y_values, c='sienna', linewidth = 1.5)
                        
                        ################################################################################
                        #EXCESS MASS CALCULATION
                        ################################################################################
                        #Calculate the particles along the line and the profile (not the smoothed) curve
                        #Use the same bin size so we can convert from density to solar mass consistently
                        x_values = np.arange(np.round(left_outer, 2), 
                                             np.round(left_inner, 2), bin_size)
                        
                        mass_actual, mass_line, delta, deltax = 0., 0., [], []
                        for xv in x_values:
                            #Multiply by density divisor otherwise we get a density not an excess mass in M_sol
                            mass_actual_i = 10 ** (density[bin_middles == find_nearest(bin_middles, xv)][0]) * density_div
                            
                            #Recall that we are normalising the density => need to get the un-normalise
                            #Normalisation is density_N = (density - denmin)/(denmax - denmin)
                            #So actual density is density_N * (denmax - denmin) + denmin
                            #For the plot stick with normalised values of course
                            p_c_line_N = (linear_slope * xv + const)
                            #De-normalise to get the mass aling the line in this bin
                            p_c_line = p_c_line_N * (denmax - denmin) + denmin
                            mass_line_i = 10 ** p_c_line  * density_div
                            
                            #The line must have continued past where the shoulders end
                            #Good illustration of this in D6 slice 0 - 250pc, t = 5Gyr                           
                            #If this is not the case ignore this point
                            if mass_line_i <= mass_actual_i:
                                mass_line += mass_line_i
                                mass_actual += mass_actual_i
    
                                #Capture the delta between the smoothed profile and the line so we can find the turning point
                                #The turning point is where the density starts to return to baseline and for this we need
                                #to use the smoothed not the actual profile to get a reasonable indicator location
                                p_c_smoothed_N = smoothed[bin_middles == find_nearest(bin_middles, xv)][0]
                                p_c_smoothed = p_c_smoothed_N * (denmax - denmin) + denmin
                                part_smoothed_i = 10 ** p_c_smoothed * density_div
    
                                deltax.append(xv)
                                delta.append(part_smoothed_i - mass_line_i)
                            else:
                                print('Excess calc: skipping left bin {0}kpc'.format(round(xv, 2)))
                        
                        #Where along this line is the maximum excess? Record this position
                        if len(delta) > 0:
                            left_excess_max = deltax[delta.index(max(delta))]
        
                            #Excess density at the location of the maximum
                            left_excess_den = density[bin_middles == find_nearest(bin_middles, left_excess_max)][0]
                        else:
                            left_excess_max, left_excess_den = np.nan, np.nan
                       
        
                        print('LEFT Smoothed: {0:6.0f}; Line: {1:6.0f}; Excess {2:6.0f} slice {3}'.format(mass_actual, \
                              mass_line, mass_actual - mass_line, i))
        
                        #Any excess less than 0 is set to 0
                        #The shoulder strength is then (excess_1-excess_2)/excess_1
                        #the fractional excess mass S
                        if mass_actual - mass_line < 0:
                            left_excess_1, left_excess_2 = mass_actual, mass_actual
                        else:
                            left_excess_1, left_excess_2 = mass_actual, mass_line
                        
                        if left_excess_1 != 0.:
                            strength_left = (left_excess_1 - left_excess_2)/left_excess_1
                        else:
                            strength_left = np.nan
                        
                        ####################################
                        #EXCESS MASS CALCULATION RIGHT SIDE
                        ####################################
                        
                        #Construct line
#                        lower_density = smoothed[bin_middles >= right_outer][0]
#                        higher_density = smoothed[bin_middles >= right_inner][0]
                        lower_density = smoothed[bin_middles >= right_outer][0]
                        higher_density = smoothed[bin_middles >= right_inner][0]
    
                        linear_slope = -(higher_density - lower_density) / abs((right_outer - right_inner))
    
    #                        const = density[bin_middles == right_inner][0] - \
    #                            (right_inner_slope * right_inner)
                        const = smoothed[bin_middles == right_inner][0] - \
                            (linear_slope * right_inner)
                        x_values = np.linspace(right_inner, right_outer, 100)
    #                        y_values = right_inner_slope * x_values + const
                        y_values = linear_slope * x_values + const

                        if do_plots:
                            ax.plot(x_values, y_values, c='sienna', linewidth = 1.5)
        
                        #Calculate the particles along the line and the smoothed curve
                        #Use the same bin size so we can convert from density to solar mass consistently
                        x_values = np.arange(np.round(right_inner, 2), 
                                             np.round(right_outer, 2), bin_size)
        
                        mass_actual, mass_line, delta, deltax = 0., 0., [], []
                        for xv in x_values:
                            #Multiply by density divisor otherwise we get a density not an excess mass in M_sol
                            mass_actual_i = 10 ** (density[bin_middles == find_nearest(bin_middles, xv)][0]) * density_div
                            
                            #Recall that we are normalising the density => need to get the un-normalise
                            #Normalisation is density_N = (density - denmin)/(denmax - denmin)
                            #So actual density is density_N * (denmax - denmin) + denmin
                            #For the plot stick with normalised values of course
                            p_c_line_N = (linear_slope * xv + const)
                            #De-normalise
                            p_c_line = p_c_line_N * (denmax - denmin) + denmin
                            mass_line_i = 10 ** p_c_line * density_div
                            
                            #The line must have continued past where the shoulders end
                            #Good illustration of this in D6 slice 0 - 250pc, t = 5Gyr                           
                            #If this is not the case ignore this one
                            if mass_line_i <= mass_actual_i:
                                mass_line += mass_line_i
                                mass_actual += mass_actual_i
    
                                #Capture the delta between the smoothed profile and the line so we can find the turning point
                                #The turning point is where the density starts to return to baseline and for this we need
                                #to use the smoothed not the actual profile to get a reasonable indicator location
                                p_c_smoothed_N = smoothed[bin_middles == find_nearest(bin_middles, xv)][0]
                                p_c_smoothed = p_c_smoothed_N * (denmax - denmin) + denmin
                                part_smoothed_i = 10 ** p_c_smoothed * density_div
    
                                deltax.append(xv)
                                delta.append(part_smoothed_i - mass_line_i)
                            else:
                                print('Excess calc: skipping right bin {0}kpc'.format(round(xv, 2)))
                                
                        #Where along this line is the maximum excess? Record this position
                        if len(delta) > 0:
                            right_excess_max = deltax[delta.index(max(delta))]
        
                            #Excess density at the location of the maximum
                            right_excess_den = density[bin_middles == find_nearest(bin_middles, right_excess_max)][0]
                        else:
                            right_excess_max, right_excess_den = np.nan, np.nan
    
                        print('RIGHT Smoothed: {0:6.0f}; Line: {1:6.0f}; Excess {2:6.0f} slice {3}'.format(mass_actual, \
                              mass_line, mass_actual - mass_line, i))
        
                        #Any excess less than 0 is set to 0
                        #The shoulder strength is then (excess_1-excess_2)/excess_1
                        #the fractional excess mass S
                        if mass_actual - mass_line < 0:
                            right_excess_1, right_excess_2 = mass_actual, mass_actual
                        else:
                            right_excess_1, right_excess_2 = mass_actual, mass_line
                        
                        if right_excess_1 != 0.:
                            strength_right = (right_excess_1 - right_excess_2)/right_excess_1
                        else:
                            strength_right = np.nan

                        left_excess = left_excess_1 - left_excess_2
                        right_excess = right_excess_1 - right_excess_2
                        excess = left_excess + right_excess
  
                        #Now work out the total strength on the same basis as the left and right strengths
                        if right_excess_1 + left_excess_1 != 0.:
                            strength_total = ((right_excess_1 + left_excess_1) - (right_excess_2 + left_excess_2))/(right_excess_1 + left_excess_1)
    
    
                        #Plot the locations of the maximum excess
                        if do_plots:
#                            yrange = ax2.get_ylim()[1] - ax2.get_ylim()[0]
#                            ax2.axvline(x=left_excess_max, ymin = 0.3, ymax = 0.7, c = 'blue', linewidth=1, ls='-.')
#                            ax2.axvline(x=right_excess_max, ymin = 0.3, ymax= 0.7, c = 'blue', linewidth=1, ls='-.')

                            yrange = ax.get_ylim()[1] - ax.get_ylim()[0]
                            ax.axvline(x=left_excess_max, ymin = 0.3, ymax = 0.7, c = 'blue', linewidth=1, ls='-.')
                            ax.axvline(x=right_excess_max, ymin = 0.3, ymax= 0.7, c = 'blue', linewidth=1, ls='-.')
    
                    
                else:
                    #Set variables to nan except central density and mass
                    clav_left, left_inner, left_outer, left_slope, left_inner_slope, \
                    left_outer_slope, left_excess_1, left_excess_2, \
                    left_clav_inner, left_clav_outer, \
                    clav_right, right_inner, right_outer, right_slope, right_inner_slope, \
                    right_outer_slope, right_excess_1, right_excess_2, \
                    right_clav_inner, right_clav_outer, \
                    mass_bar_cut_l, mass_bar_cut_r, mass_clav_l, \
                    mass_clav_r, mass_sh_l, mass_sh_r, \
                    mass_centre_l, mass_centre_r, \
                    sigz_clav, sigz_sh, sigR_clav, sigR_sh, hz_clav, hz_sh, hR_clav, hR_sh, \
                    med_abs_z_G, med_abs_z_x_cut, med_abs_z_clav, \
                    med_abs_z_sh, med_abs_z_centre, L_G, L_x_cut, L_sh, L_clav, \
                    med_abs_vz_G, med_abs_vz_x_cut, med_abs_vz_sh, med_abs_vz_clav, \
                    med_abs_vR_G, med_abs_vR_x_cut, med_abs_vR_sh, med_abs_vR_clav, \
                    med_vR_G, med_vR_x_cut, med_vR_sh, med_vR_clav, \
                    mass_bar_cut, mass_clav, mass_sh, mass_centre, \
                    left_excess, right_excess, excess, left_excess_max, right_excess_max, \
                    left_excess_den, right_excess_den, left_clav_den, right_clav_den, \
                    sigz_clav_l, sigz_sh_l, sigR_clav_l, sigR_sh_l, hz_clav_l, \
                    hz_sh_l, hR_clav_l, hR_sh_l, sigz_clav_r, sigz_sh_r, sigR_clav_r, \
                    sigR_sh_r, hz_clav_r, hz_sh_r, hR_clav_r, hR_sh_r, \
                    med_abs_vz_sh_l, med_abs_vz_clav_l, med_abs_vz_sh_r, med_abs_vz_clav_r, \
                    med_abs_z_clav_l, med_abs_z_sh_l, med_abs_z_clav_r, med_abs_z_sh_r, \
                    med_abs_vR_sh_l, med_abs_vR_clav_l, med_abs_vR_sh_r, med_abs_vR_clav_r, \
                    med_vR_sh_l, med_vR_clav_l, med_vR_sh_r, med_vR_clav_r, \
                    L_sh_l, L_clav_l, L_sh_r, L_clav_r, \
                    strength_left, strength_right, strength_total,\
                    sh_width_left, sh_width_right,\
                    clav_width_left, clav_width_right = (np.nan,) * 113
                    
                    print('NO SHOULDERS AT t={0} slice {1}'.format(t, i))
        
                bar_radial_extent = (bar_ends_a2 + bar_ends_phi2) / 2
                
                #Save the winning parameters
                if by_z_layers is False:
                    zcmin, zcmax = np.nan, np.nan
                else:               
                    zcmin, zcmax = z_cut_min, z_cut_max
    
                shoulders.append((model, descriptor, zcmin, zcmax, int(t), clav_left, clav_right, left_inner, left_outer,
                        left_slope, right_inner, right_outer, right_slope, 
                        left_inner_slope, left_outer_slope,
                        right_inner_slope, right_outer_slope,
                        left_excess_1, left_excess_2,
                        right_excess_1, right_excess_2,
                        left_clav_inner, left_clav_outer,
                        right_clav_inner, right_clav_outer,
         
                        #Measurements
                        mass_G, mass_bar_cut_l, mass_bar_cut_r, mass_clav_l,
                        mass_clav_r, mass_sh_l, mass_sh_r,
                        mass_centre_l, mass_centre_r,
                        sigz_clav, sigz_sh, sigR_clav, sigR_sh, hz_clav, hz_sh, hR_clav, hR_sh,
                        med_abs_z_G, med_abs_z_x_cut, med_abs_z_clav, med_abs_z_sh, med_abs_z_centre,
        
                        L_G, L_x_cut, L_sh, L_clav,
        
                        med_abs_vz_G, med_abs_vz_x_cut, med_abs_vz_sh, med_abs_vz_clav,
                        med_abs_vR_G, med_abs_vR_x_cut, med_abs_vR_sh, med_abs_vR_clav,
                        med_vR_G, med_vR_x_cut, med_vR_sh, med_vR_clav, 
        
                        mass_bar_cut, mass_clav, mass_sh, mass_centre,
                        left_excess, right_excess, excess,
        
                        bar_ends_a2, bar_ends_phi2, bar_radial_extent,
                        left_excess_max, right_excess_max,
                         
                        left_excess_den, right_excess_den,
                        left_clav_den, right_clav_den, peak_den,
                        
                        sigz_clav_l, sigz_sh_l, sigR_clav_l, sigR_sh_l, hz_clav_l,
                        hz_sh_l, hR_clav_l, hR_sh_l, sigz_clav_r, sigz_sh_r, sigR_clav_r,
                        sigR_sh_r, hz_clav_r, hz_sh_r, hR_clav_r, hR_sh_r,
                        med_abs_vz_sh_l, med_abs_vz_clav_l, med_abs_vz_sh_r, med_abs_vz_clav_r,
                        med_abs_z_clav_l, med_abs_z_sh_l, med_abs_z_clav_r, med_abs_z_sh_r,
                        med_abs_vR_sh_l, med_abs_vR_clav_l, med_abs_vR_sh_r, med_abs_vR_clav_r,
                        med_vR_sh_l, med_vR_clav_l, med_vR_sh_r, med_vR_clav_r,
                        L_sh_l, L_clav_l, L_sh_r, L_clav_r,
                        
                        #Excess ratios = shoulder strength
                        strength_left, strength_right, strength_total,
                         
                        sh_width_left, sh_width_right,
                        clav_width_left, clav_width_right
                       
                        ))
        
        
                # Now show the bar radial extent
                if do_plots:
                    l_o = min(-bar_ends_phi2, -bar_ends_a2)
                    l_i = max(-bar_ends_phi2, -bar_ends_a2)
                    r_o = max(bar_ends_phi2, bar_ends_a2)
                    r_i = min(bar_ends_phi2, bar_ends_a2)
            
                    if l_o == l_i:
                         ax.axvspan(l_o, l_i, color='k', linewidth=2)
                    else:
                         ax.axvspan(l_o, l_i, alpha=0.25, color='grey')
            
                    if r_o == r_i:
                         ax.axvspan(r_o, r_i, color='k', linewidth=2)
                    else:
                         ax.axvspan(r_o, r_i, alpha=0.25, color='grey')  
            
                    #Plot a derivative = 0 line
                    if plot_derivs:
                        ax2.axhline(y=0, c='r')
                    

        #END OF z-LAYERS LOOP
        #Output plot(s) filename root
        if do_plots:
            ax.set_ylim(min_y, 1.1)

            annotation += '\n{0} full-profile particles'.format(global_keep.sum())
            annotation += shoulders_found
            xrange = ax.get_xlim()[1] - ax.get_xlim()[0]
            yrange = ax.get_ylim()[1] - ax.get_ylim()[0]
            ax.annotate(annotation, xy=(ax.get_xlim()[0], ax.get_ylim()[0]),  xycoords='data',
                    xytext=(ax.get_xlim()[0] + xrange * 0.4, 
                            ax.get_ylim()[0] + (yrange * 0.15)), fontsize=12,
                            bbox=dict(facecolor='white', edgecolor='k'))


            suffixz = '_z_slices' if by_z_layers else ''
            plot_file = (os.path.join(output_temp,
                        'Model{0}_t{1}_sh_quant{2}{3}')).format(model, t, suffixz, suffix_rot)
    
            fig.tight_layout()
            fig.savefig(plot_file)
    
            # We close the plot to save memory especially when we're doing
            # 50 plots for an animation
            plt.close()
        
            # Run the analysis and output the file to the output folder   
            profiles_for_animation.append(plot_file + '.png')

    #END OF TIMESTAMP LOOP
    if do_plots:
        plt.close()

    # Create the array and save to the output folder
    shoulders_array = np.array(shoulders, dtype=[('model', 'U30'), 
        ('descriptor', 'U80'),
        ('z_cut_min', float), ('z_cut_max', float),
        ('t', int),
        ('clav_left', float), ('clav_right', float), ('left_inner', float),
        ('left_outer', float), ('left_slope', float), ('right_inner', float),
        ('right_outer', float), ('right_slope', float),
        ('left_inner_slope', float), ('left_outer_slope', float),
        ('right_inner_slope', float), ('right_outer_slope', float),
        ('left_excess_1', float), ('left_excess_2', float),
        ('right_excess_1', float), ('right_excess_2', float),
        ('left_clav_inner', float), ('left_clav_outer', float),
        ('right_clav_inner', float), ('right_clav_outer', float),

        #Measurements
        ('mass_G',float), ('mass_bar_cut_l',float), ('mass_bar_cut_r',float),
        ('mass_clav_l',float),('mass_clav_r',float), ('mass_sh_l',float),
        ('mass_sh_r',float), ('mass_centre_l',float), ('mass_centre_r',float),
        ('sigz_clav',float), ('sigz_sh',float), ('sigR_clav',float),
        ('sigR_sh',float), ('hz_clav',float), ('hz_sh',float),
        ('hR_clav',float), ('hR_sh',float), ('med_abs_z_G',float), ('med_abs_z_x_cut',float),
        ('med_abs_z_clav',float), ('med_abs_z_sh',float), ('med_abs_z_centre',float),

        ('L_G',float), ('L_x_cut',float), ('L_sh',float), ('L_clav',float),

        ('med_abs_vz_G' ,float), ('med_abs_vz_x_cut' ,float), ('med_abs_vz_sh' ,float), 
        ('med_abs_vz_clav' ,float),
        ('med_abs_vR_G' ,float), ('med_abs_vR_x_cut' ,float), ('med_abs_vR_sh' ,float), 
        ('med_abs_vR_clav' ,float),
        ('med_vR_G' ,float), ('med_vR_x_cut' ,float), ('med_vR_sh' ,float), 
        ('med_vR_clav', float), 

        ('mass_bar_cut' ,float), ('mass_clav' ,float), ('mass_sh' ,float),
        ('mass_centre' ,float),
        ('left_excess' ,float), ('right_excess' ,float), ('excess' ,float),

        ('bar_ends_a2', float), ('bar_ends_phi2', float), ('bar_radial_extent', float),
        
        ('left_excess_max', float), ('right_excess_max', float),    
        ('left_excess_den', float), ('right_excess_den', float),    
        ('left_clav_den', float), ('right_clav_den', float), 
        ('peak_den', float),

        ('sigz_clav_l', float), ('sigz_sh_l', float), ('sigR_clav_l', float),
        ('sigR_sh_l', float), ('hz_clav_l', float),
        ('hz_sh_l', float), ('hR_clav_l', float), ('hR_sh_l', float), 
        ('sigz_clav_r', float), ('sigz_sh_r', float), ('sigR_clav_r', float),
        ('sigR_sh_r', float), ('hz_clav_r', float), ('hz_sh_r', float),
        ('hR_clav_r', float), ('hR_sh_r', float),
        ('med_abs_vz_sh_l', float), ('med_abs_vz_clav_l', float),
        ('med_abs_vz_sh_r', float), ('med_abs_vz_clav_r', float),
        ('med_abs_z_clav_l', float), ('med_abs_z_sh_l', float), ('med_abs_z_clav_r', float),
        ('med_abs_z_sh_r', float), ('med_abs_vR_sh_l', float), ('med_abs_vR_clav_l', float),
        ('med_abs_vR_sh_r', float), ('med_abs_vR_clav_r', float),
        ('med_vR_sh_l', float), ('med_vR_clav_l', float), ('med_vR_sh_r', float), ('med_vR_clav_r', float),
        ('L_sh_l', float), ('L_clav_l', float), ('L_sh_r', float), ('L_clav_r', float),

        ('strength_left', float), ('strength_right', float), ('strength_total', float),
        
        ('sh_width_left',float), ('sh_width_right', float),
        ('clav_width_left', float), ('clav_width_right', float)

        ])

    if generate_shoulders_file:            
        f_shoulders = os.path.join(model_folder, '{0}_{1}'.format(model, shoulders_fname))
        np.save(f_shoulders, shoulders_array)

    #Make an animation with 0.2s gap between frames
    if do_animation and do_plots:
        if by_z_layers is True:
            fname = os.path.join(output_folder, '{0}-sh_quant_anim{1}{2}.gif'.format(model, suffixz, suffix_rot))
        else:
            fname = os.path.join(output_folder, '{0}-sh_quant_anim{1}.gif'.format(model, suffix_rot))
        convert_pngs_to_animated_gif(profiles_for_animation, fname , 0.3)
    
        if len(timestamp) > 0:
            for file in profiles_for_animation:
                os.remove(file)

    return shoulders_array
