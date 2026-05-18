     #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SHOULDER DETECTION ALGORITHM CALLING PROCEDURE
"""

import os
import numpy as np

os.chdir('/Users/stuartanderson/Documents/Astronomy/General/Code/Libraries')
#Shoulder algo
#import SRA_test as SRA_test
import SRA as SRA
# import SRA_by as SRA_by
# import SRA_temp as SRA_temp

#import SRA_normalise_x as SRA2
#import SRA_708_Plot_Lim as SRA_708_Plot_Lim

import model_params as modp

models = modp.all_models()
models.sort()

models = ['D2', 'D5', 'D6', 'D7', 'D8', 'T1', 'T4', '758', '758b', '758c',  \
          'HD1', 'HD2','761', '762MR', '764', '765', '766LR', '767CS', '767G10',
          '768MR', '768MRS', 'D6S', '708']

models = ['774Gas07v2']
models = ['774Gas07v2SF2', '768Gas07']
models = ['774Gas07v2SF2']

slices = [(round(val, 2), round(val + 0.25, 2)) for val in np.arange(0, 2., 0.25)]

slices.append( (0, np.inf) )

# slices =[(0, np.inf), (0, 0.75), (0.75, np.inf)]

for model in models:
    #Run the shoulder recognition algorithm for the model and spit out the animation, returning the array
    run_S = SRA.run_SRA(model, 0, modp.model_age(model), generate_shoulders_file=True,
                        do_animation=True, by_z_layers=False, plot_derivs=True, do_plots=True)

    # Temp for Models1,2,3
    # run_S = SRA_temp.run_SRA(model, 0, modp.model_age(model), generate_shoulders_file=True,
    #                     do_animation=True, by_z_layers=False, plot_derivs=True, do_plots=True,
    #                     timestamp= [str(x) for x in np.arange(15, 135, 5)])

    # run_S = SRA.run_SRA(model, 0, modp.model_age(model), generate_shoulders_file=True,
    #                     do_animation=True, by_z_layers='Relative', plot_derivs=False, do_plots=True)

    # run_S = SRA.run_SRA(model, 0, modp.model_age(model), generate_shoulders_file=True,
    #                     do_animation=True, by_z_layers='Absolute', plot_derivs=False, do_plots=True)

    # run_S = SRA.run_SRA(model, 0, modp.model_age(model), generate_shoulders_file=True,
    #                     do_animation=True, by_z_layers=False, plot_derivs=False, do_plots=True)

    #Now by z
    # run_S = SRA.run_SRA(model, 0, modp.model_age(model), generate_shoulders_file=True,
    #                     do_animation=True, by_z_layers=True, plot_derivs=False, do_plots=True)

    # run_S = SRA.run_SRA(model, 0, modp.model_age(model), generate_shoulders_file=True,
    #                     do_animation=True, by_z_layers=True, plot_derivs=False, 
    #                     do_plots=False, z_slices=slices)

    #Try the new shoulder algorithm slicing in z and see if it works
    # run_S = SRA_by.run_SRA(model, 0, modp.model_age(model), generate_shoulders_file=False,
    #                     do_animation=True, by_variable=None, plot_derivs=True, do_plots=True)

    # run_S = SRA_by.run_SRA(model, 50, 55, generate_shoulders_file=False,
    #                     do_animation=True, by_variable=None, plot_derivs=True, do_plots=True)

    # z_slices = [(round(val, 2), round(val + 0.25, 2)) for val in np.arange(0, 1.5, 0.25)]
    # z_slices.append( (0, np.inf) )

    # tforms = [(val, val + 1) for val in np.arange(0, 10, 1)]
    # tforms.append( (0, np.inf) )

    # Full profile
    # run_S = SRA_by.run_SRA(model, 80, 85, generate_shoulders_file=False,
    #                     do_animation=True, by_variable_name=None, plot_derivs=True, do_plots=True)

    #By z
    # run_S = SRA_by.run_SRA(model, 80, 85, generate_shoulders_file=False,
    #                     do_animation=True, by_variable_name='z_slices',
    #                     by_variable_slices=z_slices, plot_derivs=False, do_plots=True, plot_lines=False)

    #By age
    # run_S = SRA_by.run_SRA(model, 0, modp.model_age(model), generate_shoulders_file=True,
    #                     do_animation=True, by_variable_name='tform',
    #                     by_variable_slices=tforms, plot_derivs=False, do_plots=True, plot_lines=False)


    # master_folder = os.path.join(modp.model_root(model),'Astronomy/Projects/Action_Space')
    # data_folder = os.path.join(master_folder, 'Data')
    # os.chdir(master_folder)
    # model_folder = os.path.join(data_folder,model)
    # shoulders_fname = '{}_shoulders_roc_z_slices_hz.npy'.format(model)

    # sh = np.load(model_folder + '/' + shoulders_fname)
    
    