#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Single-file model parameters for the SRA run on D650_stars.npy.
"""

import numpy as np

DATA_DIR = r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Data'
SINGLE_STARS_FILE = 'D650_stars.npy'
SINGLE_MODEL = 'D'
SINGLE_TIMESTEP = 650
DEFAULT_PARTICLE_MASS = 1.0

set_all_models = {SINGLE_MODEL}
set_paper_models = {SINGLE_MODEL}

model_names = {SINGLE_MODEL: 'Model D'}
model_subgroups = {SINGLE_MODEL: 'Single'}
model_ages = {SINGLE_MODEL: SINGLE_TIMESTEP}
model_roots = {SINGLE_MODEL: DATA_DIR}
model_bar_formation_times = {SINGLE_MODEL: np.nan}
model_groups = {SINGLE_MODEL: 'Single'}
model_time_divisors = {SINGLE_MODEL: 1}
model_particle_mass = {SINGLE_MODEL: DEFAULT_PARTICLE_MASS}
model_shoulders = {SINGLE_MODEL: [0, 0]}
model_pre_buck_starts = {SINGLE_MODEL: 0}
model_shoulder_starts = {SINGLE_MODEL: np.nan}
model_shoulder_starts4545 = {SINGLE_MODEL: np.nan}
model_shoulder_ends = {SINGLE_MODEL: np.nan}
model_shoulder_ends_4545 = {SINGLE_MODEL: np.nan}
model_buckling_times = {SINGLE_MODEL: np.nan}
model_2nd_buckling_times = {SINGLE_MODEL: np.nan}
model_BP_forms_dict = {SINGLE_MODEL: np.nan}
model_buckles_TF = {SINGLE_MODEL: False}
model_zds = {SINGLE_MODEL: np.nan}
model_sigR0s = {SINGLE_MODEL: np.nan}


def _validate_model(model):
    if model != SINGLE_MODEL:
        raise ValueError(
            '{0} is not configured. This setup only works with {1} from {2}.'.format(
                model, SINGLE_STARS_FILE, DATA_DIR
            )
        )


def avg_shoulder():
    return 0.66, 1.1, 0.86


def all_models():
    return list(set_all_models)


def paper_models():
    return list(set_paper_models)


def all_models_group(group):
    return [SINGLE_MODEL] if group == model_group(SINGLE_MODEL) else []


def all_models_subgroup(subgroup):
    return [SINGLE_MODEL] if subgroup == model_subgroup(SINGLE_MODEL) else []


def model_buckles(model):
    _validate_model(model)
    return model_buckles_TF[model]


def model_root(model):
    _validate_model(model)
    return model_roots[model]


def model_bar_formation_time(model):
    _validate_model(model)
    return model_bar_formation_times[model]


def model_buckling_time(model):
    _validate_model(model)
    return model_buckling_times[model]


def model_2nd_buckling_time(model):
    _validate_model(model)
    return model_2nd_buckling_times[model]


def model_age(model):
    _validate_model(model)
    return model_ages[model]


def model_name(model):
    _validate_model(model)
    return model_names[model]


def model_group(model):
    _validate_model(model)
    return model_groups[model]


def model_subgroup(model):
    _validate_model(model)
    return model_subgroups[model]


def model_shoulder(model):
    _validate_model(model)
    return model_shoulders[model]


def model_pre_buck_start(model):
    _validate_model(model)
    return model_pre_buck_starts[model]


def model_shoulders_start(model):
    _validate_model(model)
    return model_shoulder_starts[model]


def model_shoulders_end(model):
    _validate_model(model)
    return model_shoulder_ends[model]


def model_shoulders_start4545(model):
    _validate_model(model)
    return model_shoulder_starts4545[model]


def model_shoulders_end4545(model):
    _validate_model(model)
    if model_shoulder_ends_4545[model] is None:
        return model_ages[model]
    return model_shoulder_ends_4545[model]


def model_BP_forms(model):
    _validate_model(model)
    return model_BP_forms_dict[model]


def model_time_divisor(model):
    _validate_model(model)
    return model_time_divisors[model]


def list_all_models():
    return list(model_names.keys())


def model_mass(model):
    _validate_model(model)
    return model_particle_mass[model]


def model_zd(model):
    _validate_model(model)
    return model_zds[model]


def model_sigR0(model):
    _validate_model(model)
    return model_sigR0s[model]


def append_mass_to_data(model, Data):
    _validate_model(model)
    if 'm' not in Data.dtype.names:
        new_dt = np.dtype(Data.dtype.descr + [('m', float)])
        data_with_mass = np.zeros(len(Data), dtype=new_dt)

        for name in data_with_mass.dtype.names:
            if name != 'm':
                data_with_mass[name] = Data[name]

        Data = data_with_mass
        Data['m'] = model_particle_mass[model]

    return Data
