"""Digitise total bar heights from the seven source chart images.

Run with a Python environment providing Pillow/numpy. This reads the original
DOCX ZIP and writes approximate real-value reference points, never model output.
"""
import csv
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"D:\Dropbox\My Documents\Home Finances\Pension\Scenario Projections 2026-10-21.docx")
# Pixel positions of the £0 baseline and £4.5m horizontal gridline, visually
# checked against each original image. Age 65 maps to year 0; 99 to year 34.
CALIBRATION = [(776, 51), (779, 54), (790, 65), (795, 70), (781, 56), (781, 56), (788, 63)]


def extract(source=SOURCE, output=ROOT/'data'/'evelyn_reference.csv'):
    rows = []
    with ZipFile(source) as archive:
        for number, (baseline, upper) in enumerate(CALIBRATION, 1):
            rgb = np.array(Image.open(BytesIO(archive.read(f'word/media/image{number}.png'))).convert('RGB')).astype(int)
            green = (rgb[:, :, 1] > rgb[:, :, 0]+12) & (rgb[:, :, 1] > rgb[:, :, 2]+12)
            green[baseline:] = False
            green[:, :65] = False
            occupied = np.flatnonzero(green.sum(axis=0) >= 3)
            groups = np.split(occupied, np.flatnonzero(np.diff(occupied) > 1)+1)
            groups = [g for g in groups if len(g) >= 20]
            first = (groups[0][0]+groups[0][-1])/2
            spacing = (groups[1][0]+groups[1][-1])/2-first
            values = []
            for year in range(35):
                centre = round(first+year*spacing)
                # Detect using the central part of each bar, away from its
                # rounded corners, chart navigation arrows and white gaps.
                top = np.flatnonzero(green[:, max(65, centre-8):centre+9].sum(axis=1) >= 8)
                value = (baseline-int(top[0]))*4500000/(baseline-upper) if len(top) else 0.0
                value = max(0, round(value/10000)*10000)
                rows.append({'scenario': number, 'year': year, 'gordon_age': 65+year,
                             'portfolio_real_approx': value})
                values.append(value)
            print(f'S{number}: {len(groups)} visible bars; start £{values[0]:,}; end £{values[-1]:,}')
    with Path(output).open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    extract()
