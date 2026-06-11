# S4G Image Downloader

Downloads S4G 3.6 micron FITS images from IRSA for the galaxies listed in the
bar-profiles `scrambled_map.txt` file.

## Install

```powershell
cd "D:\Dropbox\Public Documents\PythonScripts\s4g_image_downloader"
python -m pip install -r requirements.txt
```

## Test Without Downloading

```powershell
python download_s4g_images.py --dry-run --limit 5
```

## Download One Image

```powershell
python download_s4g_images.py --limit 1
```

## Download All Images

```powershell
python download_s4g_images.py
```

Downloaded FITS files are written to `s4g_images_36um`. That folder is ignored
by Git so the code stays tracked without committing large image files.

## Build Image/Geometry Manifest

```powershell
python build_s4g_geometry_manifest.py
```

This writes:

```text
geometry_output\s4g_image_geometry_manifest.csv
```

The manifest links each galaxy in `scrambled_map.txt` to its downloaded FITS
file, FITS image metadata, and geometry-related fields from:

* Herrera-Endoqui et al. 2015, VizieR `J/A+A/582/A86/table2`: bar semi-major
  axis, bar PA, and bar ellipticity
* Salo et al. 2015, VizieR `J/ApJS/219/4/galaxies`: galaxy centre, disc PA, and
  disc ellipticity
* Diaz-Garcia et al. 2016, VizieR `J/A+A/587/A160/tablea3`: deprojected bar
  ellipticity and Fourier bar-strength values
* local `s4gbars_table.dat`: inclination, deprojected bar sizes, stellar mass,
  distance, and other values already used by the converted paper scripts

The main deprojected bar-size column in the output is `bar_sma_deproj_kpc`.
This is taken from local `s4gbars_table.dat` column `sma_dp_kpc2`, which the
source table documents as using the Herrera-Endoqui bar size/PA with
Munoz-Mateos galaxy inclination/PA. The older local `sma_dp_kpc` values are kept
only as `bar_sma_deproj_legacy_kpc`; non-positive legacy values are treated as
missing because some rows contain invalid negative sizes.

The VizieR catalogues are cached in `geometry_catalog_cache`, which is ignored by
Git. To rebuild using only local files, run:

```powershell
python build_s4g_geometry_manifest.py --no-vizier
```

To force fresh VizieR downloads, run:

```powershell
python build_s4g_geometry_manifest.py --refresh-cache
```

Note that Erwin et al. mention manual revisions to 26 bar PAs, 35 galaxy centres,
and one disc PA. Those revisions are not directly available in the VizieR source
catalogues, so the manifest uses catalogue values unless the local project data
already provide an adjusted value.

## Plot Isophote Axes

```powershell
python plot_s4g_isophote_axes.py
```

This creates Figure-1-style diagnostic PDFs in:

```text
isophote_output\
```

The script writes one combined multi-page PDF plus individual per-galaxy PDFs.
Each plot shows S4G 3.6 micron log-isophotes, the observed bar major axis, the
projected bar minor axis, and major/minor-axis intensity cuts. For quick tests:

```powershell
python plot_s4g_isophote_axes.py --limit 3
python plot_s4g_isophote_axes.py --names NGC1879 IC0600
```
