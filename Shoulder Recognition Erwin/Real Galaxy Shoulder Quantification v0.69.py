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
import argparse
import csv
import math
import sys
import warnings
import numpy as np
import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt
from astropy.io import fits
from scipy.signal import find_peaks
from scipy import signal
import pandas as pd
from skimage.measure import profile_line

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BARPROFILES_DIR = os.path.join(PROJECT_ROOT, 'Erwin_barprofiles_paper_GB_working_copy')
if BARPROFILES_DIR not in sys.path:
    sys.path.append(BARPROFILES_DIR)
S4G_PLOTTER_DIR = os.path.join(PROJECT_ROOT, 'Erwin_s4g_image_downloader')
if S4G_PLOTTER_DIR not in sys.path:
    sys.path.append(S4G_PLOTTER_DIR)

import angle_utils as angles
import plot_s4g_isophote_axes as s4g_axes

def find_nearest(array, value):
    #Find the value nearest to 'value' in the array
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return array[idx]        


allow_1_sided_shoulders = False

PC_RESEARCH_FOLDERS = {
    'Laptop': r'C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research',
    'Desktop': r'D:\Dropbox\Public Documents\UCLAN\MSc Research',
}


def parse_runtime_args():
    parser = argparse.ArgumentParser(
        description='Run real-galaxy shoulder recognition without regenerating plots by default.'
    )
    parser.add_argument(
        '--pc',
        choices=sorted(PC_RESEARCH_FOLDERS),
        default='Laptop',
        help='Select which Dropbox research-folder location to use.',
    )
    parser.add_argument(
        '--write-plots',
        action='store_true',
        help='Regenerate diagnostic plot PNGs.',
    )
    return parser.parse_args()


runtime_args = parse_runtime_args()
research_folder = PC_RESEARCH_FOLDERS[runtime_args.pc]

# Public Erwin, Debattista, & Anderson (2023) paper repository already held locally.
erwin_repo = os.path.join(research_folder, 'Erwin', 'perwin-barprofiles_paper-a7cd6f5')
erwin_data_folder = os.path.join(erwin_repo, 'data')

# All generated files from this script go here.
output_folder = os.path.join(research_folder, 'Shoulder_Recognition_Erwin')
plots_folder = os.path.join(output_folder, 'plots')
profiles_folder = os.path.join(output_folder, 'profiles')
os.makedirs(output_folder, exist_ok=True)
os.makedirs(plots_folder, exist_ok=True)
os.makedirs(profiles_folder, exist_ok=True)

# Diagnostic PNGs are rebuilt only when explicitly requested.
WRITE_PLOTS = runtime_args.write_plots

manifest_file = os.path.join(
    PROJECT_ROOT,
    'Erwin_s4g_image_downloader',
    'geometry_output',
    's4g_image_geometry_manifest.csv',
)
image_folder = os.path.join(research_folder, 'Erwin', 's4g_images_36um')
profile_width = 3


def read_s4g_table(filename):
    table = pd.read_csv(filename, comment='#', sep=r'\s+', header=None)
    columns = [
        'name', 'logmstar', 'dist', 'B_tc', 'BmV_tc', 'weight_BmVtc',
        'gmr_tc', 'gmr_sga_tc', 'm21c', 'M_HI', 'logfgas', 'w25', 'w30',
        'w40', 'sma', 'sma_kpc', 'sma_ell_kpc', 'sma_dp_kpc',
        'sma_dp_kpc2', 'sma_ell_dp_kpc2', 'bar_strength', 'A2', 'A4',
        'ell_dp', 'inclination', 'R25', 'R25_5', 'R25_kpc', 'R25_5_kpc',
        'R25c_kpc', 'Re', 'Re_kpc', 'h_kpc', 'W_gas', 'V_rot',
        't_s4g', 't_leda',
    ]
    table.columns = columns
    return table


def read_descramble_map(filename):
    mapping = {}
    with open(filename, 'r', encoding='utf-8') as handle:
        for line in handle:
            if not line.strip() or line.startswith('#'):
                continue
            parts = line.split()
            mapping[int(parts[0])] = parts[2]
    return mapping


def read_classified_galaxies(filename, descramble_map):
    galaxies = []
    with open(filename, 'r', encoding='utf-8') as handle:
        for line in handle:
            if not line.strip() or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) > 1 and parts[1] != '?':
                galaxies.append(descramble_map[int(parts[0])])
    return galaxies


def read_manifest(filename):
    with open(filename, newline='', encoding='utf-8') as handle:
        return {row['name']: row for row in csv.DictReader(handle)}


def parse_float(value):
    if value is None or value == '':
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    return number


def pa_endpoint(pa_deg, radius):
    return (
        -radius * math.sin(math.radians(pa_deg)),
        radius * math.cos(math.radians(pa_deg)),
    )


def profile_at_pa(data, xc, yc, pa_deg, radius_pix, width):
    dx, dy = pa_endpoint(pa_deg, radius_pix)
    start = (yc - dy - 1, xc - dx - 1)
    end = (yc + dy - 1, xc + dx - 1)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        values = profile_line(
            data,
            start,
            end,
            linewidth=width,
            reduce_func=np.nanmean,
            mode='constant',
            cval=np.nan,
        )
    radii_pix = np.linspace(-radius_pix, radius_pix, len(values))
    return radii_pix, values


def required_geometry(row):
    fields = {
        'xc': 'center_x_pix',
        'yc': 'center_y_pix',
        'crpix1': 'crpix1',
        'crpix2': 'crpix2',
        'disk_pa': 'disk_pa_deg',
        'inclination': 'inclination_deg',
        'bar_pa': 'bar_pa_deg',
        'bar_sma': 'bar_sma_arcsec',
        'pixel_scale': 'pixel_scale_arcsec_y',
    }
    values = {name: parse_float(row.get(column)) for name, column in fields.items()}
    required = ['xc', 'yc', 'disk_pa', 'inclination', 'bar_pa', 'bar_sma', 'pixel_scale']
    if any(values[name] is None for name in required):
        return None
    values['pixel_scale'] = abs(values['pixel_scale']) or 0.75
    values['bar_pa'] = angles.RectifyPA(values['bar_pa'], 180.0)
    values['disk_pa'] = angles.RectifyPA(values['disk_pa'], 180.0)
    return values


def construct_profile_from_manifest(galaxy, manifest_row):
    geometry = s4g_axes.required_geometry(manifest_row)
    if geometry is None:
        return None, None, None, 'missing required manifest geometry fields'

    image_path = manifest_row.get('image_path') or ''
    if not os.path.exists(image_path):
        image_path = os.path.join(image_folder, '{0}.phot.1.fits'.format(galaxy))
    if not os.path.exists(image_path):
        return None, None, None, 'missing S4G 3.6 micron FITS image'

    data = np.squeeze(fits.getdata(image_path).astype(float))
    if data.ndim != 2:
        return None, None, None, 'FITS image is not two-dimensional after squeeze'

    xc = geometry['xc']
    yc = geometry['yc']
    if not (1 <= xc <= data.shape[1] and 1 <= yc <= data.shape[0]):
        crpix1 = geometry.get('crpix1')
        crpix2 = geometry.get('crpix2')
        if crpix1 is None or crpix2 is None:
            return None, None, None, 'image centre is outside image and CRPIX fallback is missing'
        xc = crpix1
        yc = crpix2

    pixel_scale = geometry['pixel_scale']
    bar_pa = geometry['bar_pa']
    disk_pa = geometry['disk_pa']
    inclination = geometry['inclination']
    bar_sma = geometry['bar_sma']
    minor_pa = bar_pa + 90.0

    max_radius_pix = int(min(
        xc - 1,
        yc - 1,
        data.shape[1] - xc,
        data.shape[0] - yc,
    ))
    target_radius_arcsec = max(2.8 * bar_sma, 45.0)
    profile_radius_pix = min(max_radius_pix, int(math.ceil(target_radius_arcsec / pixel_scale)))
    profile_radius_pix = max(profile_radius_pix, int(math.ceil(1.4 * bar_sma / pixel_scale)))
    if profile_radius_pix < 3:
        return None, None, None, 'profile extraction radius is too small'

    radii_pix, intensity = s4g_axes.profile_at_pa(
        data,
        xc,
        yc,
        bar_pa,
        profile_radius_pix,
        width=profile_width,
    )
    radii_arcsec = radii_pix * pixel_scale
    deproject_factor = angles.deprojectr(bar_pa - disk_pa, inclination, 1.0)
    radii_deproj_arcsec = s4g_axes.deprojected_profile_radius(
        bar_pa,
        disk_pa,
        inclination,
        radii_arcsec,
    )
    bar_radius_deproj_arcsec = deproject_factor * bar_sma

    _, intensity_minor = s4g_axes.profile_at_pa(
        data,
        xc,
        yc,
        minor_pa,
        profile_radius_pix,
        width=profile_width,
    )
    finite_intensity = np.concatenate(
        [
            intensity[np.isfinite(intensity) & (intensity > 0)],
            intensity_minor[np.isfinite(intensity_minor) & (intensity_minor > 0)],
        ]
    )
    if len(finite_intensity) == 0:
        return None, None, None, 'profile has no finite positive intensity samples'
    y_min, y_max = np.nanpercentile(finite_intensity, [2, 99.5])
    if y_min > 0 and y_max > y_min:
        y_min *= 0.8
        y_max *= 1.25
    else:
        y_min = np.nanmin(finite_intensity)
        y_max = np.nanmax(finite_intensity)
    if not np.isfinite(y_min) or not np.isfinite(y_max) or y_min <= 0 or y_max <= y_min:
        return None, None, None, 'could not derive valid semilogy profile scale'

    positive = np.isfinite(intensity) & (intensity > 0)
    if np.count_nonzero(positive) < 8:
        return None, None, None, 'profile has too few finite positive intensity samples'

    profile_file = os.path.join(
        profiles_folder,
        '{0}_bar-major-axis_profile.dat'.format(galaxy),
    )
    header = [
        'Constructed from S4G FITS image and geometry manifest',
        'x = deprojected bar-major-axis radius [arcsec]',
        'intensity = S4G 3.6 micron bar-major-axis profile used by plot_s4g_isophote_axes.py',
    ]
    np.savetxt(
        profile_file,
        np.column_stack([radii_deproj_arcsec, intensity]),
        header='\n'.join(header),
        comments='# ',
        fmt='%.8g',
    )
    return profile_file, bar_radius_deproj_arcsec, (y_min, y_max), None


def write_missing_data_report(missing_rows, filename):
    with open(filename, 'w', encoding='utf-8') as handle:
        handle.write('Missing data components required for shoulder quantification\n')
        handle.write('==========================================================\n\n')
        handle.write('Profiles are constructed from the S4G FITS images and geometry manifest used by\n')
        handle.write('Erwin_s4g_image_downloader/plot_s4g_isophote_axes.py.\n\n')
        handle.write('Required components:\n')
        handle.write('  - geometry manifest: {0}\n'.format(manifest_file))
        handle.write('  - S4G FITS images: {0}\n'.format(image_folder))
        handle.write('  - Erwin catalog/classification data: {0}\n'.format(erwin_data_folder))
        handle.write('Constructed profile cache:\n')
        handle.write('  - {0}\n'.format(profiles_folder))
        handle.write('\n')
        if len(missing_rows) == 0:
            handle.write('No missing required components detected.\n')
            return
        handle.write('Missing or unusable components:\n')
        for row in missing_rows:
            handle.write('  - {0}: {1}\n'.format(row['galaxy'], row['reason']))


gal_folder = 'Erwin_2023_profile_classification_sample'

s4g_table = read_s4g_table(os.path.join(erwin_data_folder, 's4gbars_table.dat'))
descramble_map = read_descramble_map(os.path.join(erwin_data_folder, 'scrambled_map.txt'))
manifest_rows = read_manifest(manifest_file)
classified_galaxies = sorted(set(
    read_classified_galaxies(os.path.join(erwin_data_folder, 'classifications_pe.txt'), descramble_map) +
    read_classified_galaxies(os.path.join(erwin_data_folder, 'classifications_vd_revised.txt'), descramble_map)
))

available_rows = []
missing_data = []
for galaxy in classified_galaxies:
    row = s4g_table[s4g_table['name'] == galaxy]
    if row.empty:
        missing_data.append({'galaxy': galaxy, 'reason': 'missing s4gbars_table.dat row'})
        continue

    manifest_row = manifest_rows.get(galaxy)
    if manifest_row is None:
        missing_data.append({'galaxy': galaxy, 'reason': 'missing geometry manifest row'})
        continue

    profile_file, bar_radius, profile_scale, reason = construct_profile_from_manifest(galaxy, manifest_row)
    if reason is not None:
        missing_data.append({'galaxy': galaxy, 'reason': reason})
        continue
    if not np.isfinite(bar_radius) or bar_radius <= 0:
        missing_data.append({'galaxy': galaxy, 'reason': 'missing/invalid deprojected bar radius'})
        continue

    available_rows.append({
        'galaxy': galaxy,
        'bar_radius': bar_radius,
        'profile_file': profile_file,
        'profile_scale': profile_scale,
    })

write_missing_data_report(
    missing_data,
    os.path.join(output_folder, 'missing_data_components.txt'),
)

missing_csv = os.path.join(output_folder, 'missing_data_components.csv')
pd.DataFrame(missing_data, columns=['galaxy', 'reason']).to_csv(missing_csv, index=False)

galaxies = np.array([row['galaxy'] for row in available_rows])
bar_radii = np.array([row['bar_radius'] for row in available_rows])
profile_files = {row['galaxy']: row['profile_file'] for row in available_rows}
profile_scales = {row['galaxy']: row['profile_scale'] for row in available_rows}
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
classification_rows = [
    {
        'galaxy': row['galaxy'],
        'sra_classification': 'Missing Data',
        'sra_classification_detail': row['reason'],
        'left_shoulder_found': False,
        'right_shoulder_found': False,
        'failed_extrema': False,
        'd_extrema': np.nan,
        'd2_extrema': np.nan,
        'roc_minima': np.nan,
    }
    for row in missing_data
]

fs = (10, 10/1.618)
num_sh_found, sh_galaxies = 0, []
for ki, galaxy in enumerate(galaxies_to_plot):
    print(galaxy)
    fig = plt.figure(figsize=fs)

    has_shoulders = False
    rejected_for_overlap_or_centre = False

    grid = fig.add_gridspec(nrows = 2, ncols = 1, 
              hspace = 0.07,  
              height_ratios = [4, 1])
    ax = fig.add_subplot(grid[0,0])
    ax_resid = fig.add_subplot(grid[1,0])

    fname = '{0}_bar-major-axis_profile.dat'.format(galaxy)        
        
    # Load the galaxy's profile. The second column is the same raw bar-major
    # intensity plotted by plot_s4g_isophote_axes.py.
    dtype = {'names': ('x', 'intensity'), 'formats': (float, float)}
    Data = np.loadtxt(profile_files[galaxy], dtype=dtype, skiprows = 3)
    
    # Normalise by the bar radius. Keep the raw full profile for display so the
    # shoulder PNG has the same semilogy profile shape as the isophote PDF.
    x_all = Data['x'] / bar_radii[ki]
    intensity_all = Data['intensity']
    y_min, y_max = profile_scales[galaxy]
    mu_all = np.array(intensity_all, dtype=float)

    # Some might have nans at the start
    if np.isnan(mu_all[0]):
        first_non_nan_idx = np.where(~np.isnan(mu_all))[0][0]
        mu_all[:first_non_nan_idx] = mu_all[first_non_nan_idx]

    # Linearly interpolate nans - NEED TO DISCUSS WITH YASMIN
    mu_all = np.array(pd.DataFrame(mu_all).interpolate().values.ravel().tolist())
    
    # We're only interested in the area within the bar so go out to 1.8 R_bar
    analysis_mask = abs(x_all) < x_cutoff_vs_bre
    x = x_all[analysis_mask]
    
    # mu is the raw bar-major intensity profile used by the original shoulder
    # detection logic. It is normalised over the analysed bar window below.
    mu = mu_all[analysis_mask]
    
    # Match the original algorithm scale: derivatives and slope cuts are applied
    # after normalising the analysed profile to 0..1.
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


    # Plot the original bar-major profile exactly as the isophote-axis PDF does:
    # raw intensity on a logarithmic y-axis. The grey dashed curve is the
    # Butterworth-smoothed analysis profile converted back from the algorithm's
    # 0..1 normalised raw-intensity scale.
    smoothed_intensity = smoothed * (mu.max() - mu.min()) + mu.min()
    ax.semilogy(x_all, intensity_all, c='#1f77b4', linewidth=1.2)
    ax.semilogy(x_all, intensity_all, c='k', linewidth=0.65)
    ax.semilogy(x, smoothed_intensity, c='0.25', linestyle='--', linewidth=0.75)
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
    with np.errstate(divide='ignore', invalid='ignore'):
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
    left_slope, right_slope = np.nan, np.nan
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
            rejected_for_overlap_or_centre = True

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

    left_shoulder_found = bool(np.isfinite(clav_left))
    right_shoulder_found = bool(np.isfinite(clav_right))

    ax.set_ylabel('intensity', fontsize=12)
    ax.set_ylim(y_min, y_max)

    dir_suffix = 'sh_false'
    dir_suffix = ''
    if has_shoulders == False:
        if failed_extrema == True:
            annotation = r'{0}: TOO NOISY{1}$peaks_d$ {2} ;$peaks_{{d2}}$ {3}; roc$_{{min}}$ {4}'.format(galaxy,'\n', d_extrema, d2_extrema, roc_minima)
            fc = 'orange'
            sra_classification = 'Too Noisy'
            sra_classification_detail = 'too many profile derivative extrema'
        else:
            annotation = r'{0}: NO SHOULDERS{1}$peaks_d$ {2} ;$peaks_{{d2}}$ {3}; roc$_{{min}}$ {4}'.format(galaxy,'\n', d_extrema, d2_extrema, roc_minima)
            annotation = r'{0}: NO SHOULDERS'.format(galaxy)
            fc = 'red'
            sra_classification = 'No Shoulders'
            if rejected_for_overlap_or_centre:
                sra_classification_detail = 'candidate shoulders rejected because they overlap or are too close to x=0'
            elif left_shoulder_found or right_shoulder_found:
                sra_classification_detail = 'only one accepted shoulder and paired shoulders are required'
            else:
                sra_classification_detail = 'no accepted shoulder pair'
    else:
        annotation = r'{0}: SHOULDERS{1}$peaks_d$ {2} ;$peaks_{{d2}}$ {3}; roc$_{{min}}$ {4}'.format(galaxy,'\n', d_extrema, d2_extrema, roc_minima)
        annotation = r'{0}: SHOULDERS'.format(galaxy)
        fc='green'
        sra_classification = 'Shoulders'
        sra_classification_detail = 'accepted left and right shoulders'
        num_sh_found += 1
        sh_galaxies.append(str(galaxy))
        dir_suffix= ''

    classification_rows.append({
        'galaxy': str(galaxy),
        'sra_classification': sra_classification,
        'sra_classification_detail': sra_classification_detail,
        'left_shoulder_found': left_shoulder_found,
        'right_shoulder_found': right_shoulder_found,
        'failed_extrema': bool(failed_extrema),
        'd_extrema': d_extrema,
        'd2_extrema': d2_extrema,
        'roc_minima': roc_minima,
    })

    bbox_props = dict(fc = fc, ec = 'k', alpha=0.75)
    ax.text(0.05, 0.85, annotation, fontsize=8,
                    bbox=bbox_props, c = 'white', weight='bold',
                    transform=ax.transAxes)        

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

    plot_file_1 = os.path.join(plots_folder, '{0}.png'.format(galaxies_to_plot[ki]))

    if WRITE_PLOTS:
        fig.savefig(plot_file_1, dpi = 100, bbox_inches = 'tight', pad_inches = 0.1)
        print('Plot saved in {}'.format(plot_file_1))
    
    plt.close()


dt = np.dtype([('galaxy', 'U30'), ('clav_left', float), ('clav_right', float),
               ('left_inner', float), ('left_outer', float), ('left_slope', float),
               ('right_inner', float), ('right_outer', float), ('right_slope', float),
               ('left_clav_inner', float), ('left_clav_outer', float), ('right_clav_inner', float),
               ('right_clav_outer', float)
               ])
shoulders = np.array(shoulders, dtype=dt)

print('Found {0} shoulder systems out of {1}'.format(num_sh_found, len(galaxies)))
print('These are {0}'.format(sh_galaxies))

results_npy = os.path.join(output_folder, 'shoulder_measurements.npy')
results_csv = os.path.join(output_folder, 'shoulder_measurements.csv')
classifications_csv = os.path.join(output_folder, 'shoulder_classifications.csv')
np.save(results_npy, shoulders)
pd.DataFrame.from_records(shoulders).to_csv(results_csv, index=False)
pd.DataFrame(classification_rows).sort_values('galaxy').to_csv(classifications_csv, index=False)

summary_file = os.path.join(output_folder, 'run_summary.txt')
with open(summary_file, 'w', encoding='utf-8') as handle:
    handle.write('Shoulder quantification summary\n')
    handle.write('===============================\n\n')
    handle.write('Erwin data folder: {0}\n'.format(erwin_data_folder))
    handle.write('Output folder: {0}\n'.format(output_folder))
    handle.write('Paper-classified galaxies found in Erwin data: {0}\n'.format(len(classified_galaxies)))
    handle.write('Galaxies with all required components: {0}\n'.format(len(galaxies)))
    handle.write('Galaxies missing required components: {0}\n'.format(len(missing_data)))
    handle.write('Shoulder systems found: {0}\n'.format(num_sh_found))
    handle.write('Shoulder galaxies: {0}\n'.format(', '.join(sh_galaxies)))
    handle.write('\nOutput files:\n')
    handle.write('  - {0}\n'.format(results_npy))
    handle.write('  - {0}\n'.format(results_csv))
    handle.write('  - {0}\n'.format(classifications_csv))
    handle.write('  - {0}\n'.format(profiles_folder))
    handle.write('  - {0}\n'.format(os.path.join(output_folder, 'missing_data_components.txt')))
    handle.write('  - {0}\n'.format(missing_csv))
    if WRITE_PLOTS:
        handle.write('  - {0}\n'.format(plots_folder))
