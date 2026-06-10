#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run shoulder quantification for the single D650_stars.npy dataset.
"""

import importlib.util
from pathlib import Path


DATA_DIR = Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Data')
STARS_FILE = 'D650_stars.npy'
MODEL = 'D'
TIMESTEP = 650


def load_sra_module():
    sra_path = Path(__file__).with_name('SRA - 650stars.py')
    spec = importlib.util.spec_from_file_location('sra_650stars', sra_path)
    sra_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sra_module)
    return sra_module


def main():
    input_file = DATA_DIR / STARS_FILE
    if not input_file.is_file():
        raise FileNotFoundError('Could not find {0}'.format(input_file))

    SRA = load_sra_module()
    return SRA.run_SRA(
        model=MODEL,
        t_start=TIMESTEP,
        t_end=TIMESTEP,
        override_folders=[str(DATA_DIR), str(DATA_DIR)],
        generate_shoulders_file=True,
        do_animation=True,
        by_z_layers=False,
        plot_derivs=True,
        do_plots=True,
    )


if __name__ == '__main__':
    run_S = main()
