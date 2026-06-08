#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Sep 28 03:58:00 2019

@author: stuartanderson
"""
import numpy as np

#Key variables holding the location of the project
root1, root2, root3 = '/Users/stuartanderson/Documents', \
                      '/Volumes/Storage-1TB-1A 5', \
                      '/Volumes/Storage-4TB-1A'

set_all_models = {'D2', 'D5', 'D6', 'D7', 'D8', 'T1', 'T4', 'HD1', 'HD2', 
               '758c', '761', '765', 
               '762MR', '767CS', '767G10', '768MR', 'D6S',
               '768MRS', '768Gas15'}

set_paper_models = {'D6', 'D2', 'D7', 'D8', 'T1', 'T4', 'HD2', 
               '758c', '761', '765', 
               '762MR', '767CS', '767G10', '768MR', 'D6S',
               '768MRS'}

# Names of models are different to their technical designations
model_names = {'D6': 'Model 2', 'D2': 'Model 3', 'D5': 'Model 1',
               'D7': 'Model 5', 'D8': 'Model 4', 'T1': 'Model T1',
               'T4': 'Model T4', 'HD1': 'Model HD1', 'HD2': 'Model HD2',
               '758': 'Model 758', '758b': 'Model 758b',
               '758c': 'Model T6', '761': 'Model CB1',
               '762MR': 'Model PB1', '764':'Model 764', '765':'Model CB2',
               '766LR': 'Model 766LR', 'D6NBC':'Model D6NBC',
               'T1Ext': 'Model T1Ext', '767CS': 'Model PBG1',
               '767G10': 'Model PBG2', '518b': 'Model 518b', '634': 'Model 634',
               '768MR': 'Model SD1', '768MRNBC': 'Model 768MRNBC',
               '708': 'Model HG1', '739HF': 'Model 739HF', 
               '766LRNBC': 'Model 766LRNBC', 'R1': 'R1', 'B3': 'B3', 
               'D6S': 'Model 2S', '768MRS': 'Model SD1S',
               '738D3': 'Model 738D3', '738D4': 'Model 738D4', '768-LHD': 'Model 768-LHD',
               '708Diff4': 'Model 708Diff4', '708mainDiff': 'Model 708mainDiff',
               '768Gas30': 'D30', '768MRS33': 'Model 768MRS-33',
               '768MRS67': 'Model 768MRS-67', '768MRS80': 'Model 768MRS-80',
               '768MRS90': 'Model 768MRS-90', '768Gas15': 'D15', 
               '768Gas07': 'D07', '774Gas07v2SF2': 'Model TG07v3',
               '774Gas07': 'TG07', '774Gas07v2': 'TG07v2', 'D6HTR': 'Model D6HTR',
               'Model1': 'Model 1', 'Model2': 'Model 2','Model3': 'Model 3', 'B6': 'B6',
               '768Gasless': 'D00', '768Gas20': 'D20', '774Gasless': 'TG00'}

# Set groups A = buckles, B = no buckling
model_subgroups = {'D6': 'B1', 'D2': 'B1', 'D5': 'ZZ',
               'D7': 'B1', 'D8': 'B1', 'T1': 'B2',
               'T4': 'B2', 'HD2': 'B2', '762MR': 'NB1',
               '758c': 'B2', '761':'NB1', '765': 'NB1',
               '767CS': 'NB2', '767G10': 'NB2', '768MR': 'NB2',
               'D6S': 'B1', '768MRS': 'NB2', 'HD1': 'ZZ', '708': 'NB2'}


# Set last filename step, i.e. last number in the filename which we will process
model_ages = {'D6': 100, 'D2': 100, 'D5': 100,
               'D7': 100, 'D8': 100, 'T1': 100,
               'T4': 100, 'HD1': 100, 'HD2': 100, '762MR': 100,
               '758': 50, '758b': 50, '758c': 100, '761': 100,
               '764': 75, '765': 100, '766LR': 50, 'D6NBC': 50, 'T1Ext': 75,
               '767CS': 100, '767G10': 100, '518b': 15, '634':0, '768MR': 100,
               '768MRNBC': 100, '708': 100, '739HF': 26, '766LRNBC': 50,
               'R1':0, 'B3':0, 'D6S': 100, '768MRS': 100,
               '738D3': 25, '738D4': 50, '768-LHD': 100, '708Diff4': 50,
               '708mainDiff': 100, '768Gas30': 225, '768MRS33': 99,
               '768MRS67': 100, '768MRS80': 100, '768MRS90': 100, '768Gas15': 200,
               '774Gas07': 260, '774Gas07v2': 260, 'D6HTR': 100,
               'Model1': 260, 'Model2': 260,'Model3': 260, 'B6': 140,
               '768Gas07': 260, '774Gas07v2SF2': 260, '768Gasless': 100, '768Gas20': 260, '774Gasless': 100}

model_roots = {'D6': root3, 'D2': root3, 'D5': root3,
               'D7': root3, 'D8': root3, 'T1': root3, '762MR': root3, 
               'T4': root3, 'HD1': root3, 'HD2': root3, '761':root3, 
               '758': root3, '758b': root2, '758c': root3, 
               '764': root2, '765':root3, '766LR': root2, 'D6NBC': root2,
               'T1Ext': root2, '767CS': root3, '767G10': root3, '518b': root2,
               '634': root2, '768MR': root3,'768MRNBC': root2, '708': root3, 
               '739HF': root3, '766LRNBC': root2, 'R1': root2, 'B3': root2,
               'D6S': root3, '768MRS': root3, '738D3': root2, '738D4': root2,
               '768-LHD': root3, '708Diff4': root2, '708mainDiff': root3,
               '768Gas30': root3, '768MRS33': root3, '768MRS67': root3,
               '768MRS80': root3, '768MRS90': root3, '768Gas15': root3,
               '774Gas07': root3, '774Gas07v2': root3,'D6HTR': root3,
               'Model1': root3, 'Model2': root3,'Model3': root3,'B6': root3,
               '768Gas07': root3, '774Gas07v2SF2': root3, '768Gasless': root3,
               '768Gas20': root3, '774Gasless': root3}


#Estimated time step when log(A_bar) turns linear
model_bar_formation_times = {'D6': 7, 'D2': 21, 'D5': 3,
               'D7': 16, 'D8': 5, 'T1': 3,
               'T4': 10, 'HD1': 15, 'HD2': 26, '758': 15, '758b': 11,
               '758c': 10, '761': 32, '762MR': 10, '766LR': 6, 
               '764': 13, '765': 11, 'T1Ext': 3, '767CS': 6, '767G10': 3,
               '768MR': 8, 'D6S': 10, '768MRS': 10, '738D3': 3, '738D4': 3,
               '768-LHD': 4, '708': 35, '708Diff4': 10, '739HF': 20, '708mainDiff': 10,
               '768Gas30': 0, '768Gas15': 0, '774Gas07': 50, '774Gas07v2': 50, 'D6HTR': 7,
               'Model1': 50, 'Model2': 50,'Model3': 50,'B6': 0, '768Gasless': 0, '768Gas20': 0,
               '774Gasless': 0}

# Set groups B = buckles, NB = no buckling
#This sets the groups for the paper so discard any which we do not want
model_groups = {'D6': 'B', 'D2': 'B', 'D5': 'B',  
                        'D7': 'B', 'D8': 'B', 'T1': 'B',
               'T4': 'B', 'HD2': 'B', '762MR': 'NB',
               '758c': 'B', '761': 'NB', '765': 'NB',
               'D6NBC': 'B', '767CS': 'NB', '767G10': 'NB', '768MR': 'NB', 
               'D6S': 'NB', '768MRS': 'NB', '768MRS': 'NB', 'D6S': 'NB'}

# '758b': 'B', 
# '766LR': 'NB',
# '764': 'NB', 
# '765': 'NB', 
#, '738D4': 'NB'
#, '738D3': 'NB'
#, '768MRNBC': 'NB'
# 'T1Ext': 'B',

#'D6NBC': 'B', 'T1Ext': 'B',
#'764': 'NB1', '765': 'NB1', 
#'758b': 'B1A', 
#'768MRNBC': 'NB',


#What do we divide the time by in the filename to get to Gyr
model_time_divisors = {'D6': 10, 'D2': 10, 'D5': 10,
               'D7': 10, 'D8': 10, 'T1':10,
               'T4': 10, 'HD1': 10, 'HD2': 10, '758': 10, '758b': 10,
               '758c': 10,  '761': 10, '762MR': 10,
               '764': 10, '765': 10, '766LR': 10, 'D6NBC': 10,
               'T1Ext': 10, '767CS': 10, '767G10': 10, '518b': 1, '634':1/6,
               '768MR': 10, '768MRNBC': 10, '708': 10, '739HF': 2, '766LRNBC': 10,
               'R1': 10, 'B3': 10, 'D6S': 10, '768MRS': 10, 
               '738D3': 10, '738D4': 10, '768-LHD': 10, '708Diff4': 10,
               '708mainDiff': 10, '768Gas30': 20, '768MRS33': 10, '768MRS67': 10,
               '768MRS80': 10, '768MRS90': 10, '768Gas15': 20, '774Gas07':20,
               '774Gas07v2': 20, 'D6HTR': 10,
               'Model1': 10, 'Model2': 10, 'Model3': 10, 'B6': 10,
               '768Gas07': 20, '774Gas07v2SF2': 20, '768Gasless': 10, '768Gas20': 20,
               '774Gasless':10}


#The mass of one particle for those models without individual particle mass
model_particle_mass = {'D6': 9096.6168642, 'D2': 1.1e4, 'D5': 1.1e4,
               'D7': 1.1e4, 'D8': 1.1e4, 'T1': np.nan,
               'T4': 8717.924696, 'HD1': 1.1e4, 'HD2': 1.1e4, '762MR': 23483.9213,
               '758': 1.1e4, '758b': 1.1e4, '758c': 8728.73688, '761': 1.1e4,
               '764': 2.0e4, '765': 55305.03, '766LR': 1.2e4, 'D6NBC': 1.1e4, 'T1Ext': 1.1e4,
               '767CS': np.nan, '767G10': np.nan, '518b': 2.33e5, '634': 2.33e5,
               '768MR': 13273.87102395,'768MRNBC': 13273.87102395, 'R1': 1.1e4, 
               'B3': 1.1e4, '708Diff4': np.nan, '708': np.nan, '708mainDiff': np.nan,
               '768Gas30': np.nan, '768Gas15': np.nan, '774Gas07': np.nan, '774Gas07v2': np.nan,
               'D6HTR': 9096.6168642,
               'Model1': np.nan, 'Model2': np.nan,'Model3': np.nan,'B6': np.nan,
               '768Gas07': np.nan, '774Gas07v2SF2': np.nan, '768Gasless': np.nan, '768Gas20': np.nan,
               '774Gasless': np.nan}

#where do shoulder start and end on the x axis at their biggest extent?
model_shoulders = {'D6': [5, 7.5], 'D2': [5, 7], 'D5': [5, 7],
               'D7': [5, 8.5], 'D8': [4, 6.5], 'T1': [3, 5],
               'T4': [6, 9], 'HD1': [2, 4], 'HD2': [2, 3.5],
               '758': [6, 8], '758b': [7, 8], '758c':[7, 8.5],
               '761': [1.5, 3], '762MR': [2.5, 4.5],
               '764': [1.5, 3], '765': [1.5, 3], '766LR': [3, 5],
               'D6NBC': [5, 7.5], 'T1Ext': [3, 5], '767CS': [0,0],
               '767G10': [0, 0], '738D3': [0, 0], '738D4': [0, 0],
               '768MR': [0,0], '768MRS': [0,0], 'D6S': [0, 0], '768Gas30': [0,0], 
               '768Gas15': [0, 0], '774Gas07': [0., 0.]}

model_pre_buck_starts = {'D6': 20, 'D2': 25, 'D5': 20,
                         'D7': 20, 'D8': 25, 'T1': 10,
               'T4': 10, 'HD1': 40, 'HD2': 65, '758': 17, '758b': 17,
               '758c': 15, '761': 10, '762MR': 5,
               '764': 20, '765': 5, '766LR': 5, 'D6NBC': 20,
               'T1Ext': 51, '767CS': 8, '767G10': 8, '518b': 1, '634': 0,
               '768MR': 0, '768MRNBC': 0, '708': 0, '739HF': 1, 'R1': 0,
               'B3': 0, 'D6S': 0, '768MRS': 0,'738D3': 0, '738D4': 0,
               '768-LHD': 0, '708Diff4': 50, '708mainDiff': 60,
               '768Gas30': 0, '768MRS33': 0, '768MRS67': 0, '768MRS80': 0,
               '768MRS90': 0, '768Gas15': 0, '774Gas07': 0, '774Gas07v2': 0, 'D6HTR': 0,
               'Model1': 0, 'Model2': 0,'Model3': 0,'B6': 0,
               '768Gas07': 0, '774Gas07v2SF2': 0, '768Gasless': 0, '768Gas20': 0,
               '774Gasless': 0}

#Estimated time step persisting shoulders first form
#Put timestep in, not Gyr
model_shoulder_starts = {'D6': 35, 'D2': 31, 'D5': 70,
               'D7': 35, 'D8': 41, 'T1': 38,
               'T4': 19, 'HD1': 36, 'HD2': 63, '758': 36, '758b': 14,
               '758c': np.nan, '761': 32, '762MR': 23, '766LR': 6, 
               '764': 10, '765': np.nan, 'T1Ext': 31, '767CS': 35, '767G10': 3,
               '768MR': 40, 'D6S': np.nan, '768MRS': np.nan, '738D3': 23, 
               '738D4': 25, '708': 67, '768Gas30': np.nan, '708mainDiff': np.nan, 
               '768Gas15': np.nan, '774Gas07': np.nan, '774Gas07v2': np.nan, 'D6HTR': 48,
               'Model1': np.nan, 'Model2': np.nan,'Model3': np.nan, 'B6':np.nan,
               '768Gas07': np.nan, '774Gas07v2SF2': np.nan, '768Gasless': np.nan, '768Gas20': np.nan,
               '774Gasless': np.nan, '739HF': np.nan}

#Same but for the inclination angles 45/45
model_shoulder_starts4545 = {'D6': 34, 'D2': 30, 'D5': 72,
               'D7': 35, 'D8': 43, 'T1': 41,
               'T4': 14, 'HD1': 36, 'HD2': 62, '758': 36, '758b': 33,
               '758c': 37, '761': 40, '762MR': 27, '766LR': 41, 
               '764': 59, '765': np.nan, 'T1Ext': 41, '767CS': 24, '767G10': 29,
               '708mainDiff': np.nan}


#Estimated time step the shoudlers end; None means end of run
model_shoulder_ends = {'D6': np.nan, 'D2': np.nan, 'D5': 100,
               'D7': 73, 'D8': np.nan, 'T1': np.nan,
               'T4': np.nan, 'HD1': 46, 'HD2': 72, '758': np.nan, '758b': 36,
               '758c': np.nan, '761': np.nan, '762MR': np.nan, '766LR':np.nan, 
               '764': np.nan, '765': np.nan, 'T1Ext': 31, '767CS': np.nan, '767G10': np.nan,
               '768MR': np.nan, 'D6S': np.nan, '768MRS': np.nan, '708': 100,
               '768Gas07': np.nan, '774Gas07v2SF2': np.nan}

#Same but for inclination angles 45/45
model_shoulder_ends_4545 = {'D6': None, 'D2': None, 'D5': None,
               'D7': 71, 'D8': None, 'T1': None,
               'T4': 39, 'HD1': 78, 'HD2': 72, '758': None, '758b': None,
               '758c': None, '761': None, '762MR': None, '766LR': None, 
               '764': None, '765': None, 'T1Ext': 39, '767CS': None, '767G10': None}

#Time step when the buckling occurs
model_buckling_times = {'D6': 29, 'D2': 38, 'D5': 39,
               'D7': 29, 'D8': 38, 'T1': 16,
               'T4': 22, 'HD1': 60, 'HD2': 93, '758': 26, '758b': 24,
               '758c': 26, '761': np.nan, '762MR': np.nan, '766LR': np.nan, 
               '764': np.nan, '765': np.nan, 'T1Ext': 16, '767CS': np.nan, '767G10': np.nan,
               '768MR': np.nan, '768MRNBC': np.nan, '739HF': np.nan, 'D6S': 55,
               '768MRS': np.nan,'738D3': np.nan, '738D4': np.nan, '768-LHD': np.nan,
               '708': np.nan, '708Diff4': np.nan, '768Gas30': np.nan,
               '708mainDiff': np.nan, '768MRS33': np.nan, '768MRS67': 0, '768MRS80': 0,
               '768MRS90': np.nan, '768Gas15': np.nan, '774Gas07': np.nan, '774Gas07v2': np.nan,
               'D6HTR': np.nan,
               'Model1': np.nan, 'Model2': np.nan,'Model3': np.nan,'B6': np.nan,
               '768Gas07': np.nan, '774Gas07v2SF2': np.nan, '768Gasless': np.nan, '768Gas20': np.nan,
               '774Gasless': np.nan}

#Time step when the 2nd buckling occurs if at all
model_2nd_buckling_times = {'D6': 85, 'D2': 62, 'D5': np.nan,
               'D7': 70, 'D8': np.nan, 'T1': np.nan,
               'T4': 39, 'HD1': np.nan, 'HD2': np.nan, '758': np.nan, '758b': np.nan,
               '758c': np.nan, '761': np.nan, '762MR': np.nan, '766LR': np.nan, 
               '764': np.nan, '765': np.nan, 'T1Ext': np.nan, '767CS': np.nan, '767G10': np.nan,
               '768MR': np.nan, '768MRNBC': np.nan, '739HF': np.nan, 'D6S': 80,
               '768MRS': np.nan,'738D3': np.nan, '738D4': np.nan, '768-LHD': np.nan,
               '708': np.nan, '768Gas30': np.nan,
               '708mainDiff': np.nan, '768MRS33': np.nan, '768MRS67': np.nan,
               '768MRS80': np.nan, '768MRS90': np.nan, '768Gas15': np.nan, 
               '774Gas07': np.nan, 'D6HTR': np.nan, '774Gas07v2': np.nan,
               'Model1': np.nan, 'Model2': np.nan,'Model3': np.nan, 'B6': np.nan,
               '768Gas07': np.nan, '774Gas07v2SF2': np.nan, '768Gasless': np.nan, '768Gas20': np.nan,
               '774Gasless': np.nan}

#Time step when the BP forms from visual inspection of the xy density contours
#Need symmetric box+spurs morphology
#?D5, 758c,
model_BP_forms_dict = {'D6': 32, 'D2': 40, 'D5': 40,
               'D7': 30, 'D8': 43, 'T1': 13,
               'T4': 25, 'HD1': 40, 'HD2': 65, '758': 29, '758b': 330000,
               '758c': 30, '761': 41, '762MR': 30, '766LR': 29, 
               '764': 37, '765': 28, 'T1Ext': 16, '767CS': 23, '767G10': 25,
               '768MRS': 20, 'D6S': 35, '708': 70, '708mainDiff': np.nan,
               '768MR': 13}


model_buckles_TF = {'D6': True, 'D2': True, 'D5': True,
               'D7': True, 'D8': True, 'T1':True,
               'T4': True, 'HD1': True, 'HD2': True, '758': True, '758b': True,
               '758c': True, '761': False, '762MR': False,
               '764': False, '765': False, '766LR': True, 'D6NBC': True,
               'T1Ext': True, '767CS': False, '767G10': False, '768MR': False,
               '768MRNBC': False, 'D6S': True, '768MRS': False, '768MRS33': False,
               '768MRS67': False, '768MRS80': False, '768MRS90': False}

#Scale heights
model_zds = {'D6': 300, 'D2': 300, 'D5': 300,
               'D7': 600, 'D8': 150, 'T1': 500,
               'T4': 600, 'HD1': 300, 'HD2': 300, '758': 300, '758b': 300,
               '758c': 300,  '761': 300, '762MR': 300,
               '764': 300, '765': 300, '766LR': 300, 'D6NBC': 300,
               'T1Ext': 300, '767CS': 300, '767G10': 300}

#Initial sigR
model_sigR0s = {'D6': 128, 'D2': 165, 'D5': 90,
               'D7': 128, 'D8': 128, 'T1': 75,
               'T4': 120, 'HD1': 128, 'HD2': 128, '758': 128, '758b': 128,
               '758c': 128,  '761': 128, '762MR': 128,
               '764': 128, '765': 128, '766LR': 128, 'D6NBC': 128,
               'T1Ext': 128, '767CS': 128, '767G10': 128}

def avg_shoulder():
    #Define return inner_edge, outer_edge, clav_outer as a fraction of R_bar
    # return 0.69, 1.12, 0.88
    #Update for final revision 20/1/2021
    return 0.66, 1.1, 0.86

def all_models():
    return list(set_all_models)

def paper_models():
    return list(set_paper_models)

def all_models_group(group):
    result=[]
    for m in list(model_groups):
        if model_group(m)==group:
            result.append(m)
            
    return result

def all_models_subgroup(subgroup):
    result=[]
    for m in list(model_subgroups):
        if model_subgroup(m)==subgroup:
            result.append(m)
            
    return result

def model_buckles(model):
    return model_buckles_TF[model]

def model_root(model):
    return model_roots[model]

def model_bar_formation_time(model):
    return model_bar_formation_times[model]

def model_buckling_time(model):
    return model_buckling_times[model]

def model_2nd_buckling_time(model):
    return model_2nd_buckling_times[model]

def model_age(model):
    return model_ages[model]

def model_name(model):
    return model_names[model]

def model_group(model):
    return model_groups[model]

def model_subgroup(model):
    return model_subgroups[model]

def model_shoulder(model):
    return model_shoulders[model]

def model_pre_buck_start(model):
    return model_pre_buck_starts[model]

def model_shoulders_start(model):
    return model_shoulder_starts[model]
    
def model_shoulders_end(model):
    return model_shoulder_ends[model]

def model_shoulders_start4545(model):
    return model_shoulder_starts4545[model]

def model_shoulders_end4545(model):
    if model_shoulder_ends[model]==None:
        return model_ages[model]
    else:
        return model_shoulder_ends[model]


def model_BP_forms(model):
    return model_BP_forms_dict[model]


def model_time_divisor(model):
    return model_time_divisors[model]

def list_all_models():
    return list(model_names.keys())

def model_mass(model):
    return model_particle_mass[model]

def model_zd(model):
    return model_zds[model]

def model_sigR0(model):
    return model_sigR0s[model]

def append_mass_to_data(model, Data):
    if 'm' not in Data.dtype.names:
        new_dt = np.dtype(Data.dtype.descr + [('m', float)])
        bb = np.zeros(len(Data), dtype=new_dt)

        for name in bb.dtype.names:
            if name != 'm':
                bb[name] = Data[name]
    
        Data = bb.copy()
        bb = None
        #Set mass to 1
        Data['m'] = model_particle_mass[model]

    return Data