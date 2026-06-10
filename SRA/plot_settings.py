#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Sep 28 03:48:49 2019

@author: stuartanderson
"""

import matplotlib.pyplot as plt

def plt_settings():

    font_name = 'DejaVu Sans'
    
    # plt.style.use('seaborn-colorblind')
    plt.style.use('classic')
    # Fontsize (in general)
    plt.rcParams['font.size'] = 20
    
    
    # INSERT DAVE'S LATEX FONTS HERE STILL CANNOT FIND LATEX FOLDER
    #params = {'text.usetex': True,
    #          'font.family': 'sans-serif',
    #          'font.style': ['Helvetica'],
    #          'text.latex.preamble': [r'\usepackage{amsmath}']
    #         }
    #plt.rcParams.update(params)
    
    
    #### Fontsize (In particular)
    plt.rcParams['axes.titlesize'] = 20
    plt.rcParams['axes.labelsize'] = 20
    plt.rcParams['xtick.labelsize'] = 20
    plt.rcParams['ytick.labelsize'] = 20
    plt.rcParams['legend.fontsize'] = 20
    
    plt.rcParams['font.sans-serif'] = font_name
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.style'] = 'normal'
    plt.rcParams['font.variant'] = 'normal'
    plt.rcParams['font.weight'] = 'light'
    plt.rcParams['font.stretch'] = 'normal'
    plt.rcParams['font.cursive'] = [font_name]
    
    plt.rcParams['mathtext.fontset'] = 'dejavusans'
    
    
    plt.rcParams['xtick.top'] = True   # draw ticks on the top side
    plt.rcParams['xtick.bottom'] = True   # draw ticks on the bottom side
    plt.rcParams['xtick.major.size'] = 10     # major tick size in points
    plt.rcParams['xtick.minor.size'] = 4      # minor tick size in points
    plt.rcParams['xtick.major.width'] = 1     # major tick width in points
    plt.rcParams['xtick.direction'] = 'in'    # direction: in, out, or inout
    plt.rcParams['xtick.minor.visible'] = True  # visibility of minor ticks on x-axis
    
    plt.rcParams['ytick.left'] = True   # draw ticks on the left side
    plt.rcParams['ytick.right'] = True  # draw ticks on the right side
    plt.rcParams['ytick.major.size'] = 10     # major tick size in points
    plt.rcParams['ytick.minor.size'] = 4      # minor tick size in points
    plt.rcParams['ytick.major.width'] = 1     # major tick width in points
    
    plt.rcParams['ytick.direction'] = 'in'    # direction: in, out, or inout
    plt.rcParams['ytick.minor.visible'] = True  # visibility of minor ticks on y-axis
