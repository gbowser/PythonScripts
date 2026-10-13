# Euclid bar cutouts

Run from the PythonScripts directory using Python with numpy, scipy and
astropy installed (the existing project environment supplies these):

```powershell
& '.\.venv\Scripts\python.exe' '.\Euclid\extract_euclid_bars.py' --overwrite
```

Defaults read the three FITS images in
`D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid Sample Data\bars`.
Outputs are in `D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Clean_Galaxy_Output`. Use `--overwrite` to regenerate them,
`--galaxies NGC1255` to select a galaxy, or `--input-dir`, `--output-dir` and
`--source-manifest` to override locations. A selected run writes a manifest
containing only that selection; use a separate output directory if appropriate.

For each galaxy:

- `*_observed.fits` is a detector-plane cutout with a celestial WCS. It includes
  the inverse-transformed footprint plus an interpolation margin.
- `*_bar_aligned.fits` is a square deprojected view with the bar along x.
  The centre is at `(radius_pixels + 1, radius_pixels + 1)` in FITS coordinates.
  Its axes are physical offsets in arcseconds, not RA/Dec. Values are linearly
  interpolated surface-brightness samples; no integrated-flux correction is applied.
- `euclid_geometry_manifest.csv` records the observed cutout geometry, aligned
  image path and geometry, transferred sky centre, source paths, and transform.
  All pixel centre fields are 1-based; cutout origin fields explicitly use 0-based
  coordinates. Catalogue angles and bar size retain their original sky meanings.

The Salo/S4G centre is converted through the original S4G celestial WCS into
Euclid pixels. This requires the original S4G FITS files named in the source CSV.
Undeclared SIP coefficients are removed as in the existing GUI; explicitly
declared SIP is retained. The local Euclid WCS maps detector offsets into
west/north offsets before applying the shared disc/bar transform. This includes
the small local orientation difference caused by the tangent-plane projection.

The shared radius policy is unchanged: target max(3 × observed bar semi-major
axis, 45 arcsec), bounded using original image edges, then at least 1.4 × bar
semi-major axis. A 180-degree ambiguity is resolved using the existing display
orientation policy. Missing source coverage is NaN.

The manifest describes the **observed** cutout in `image_path`; the aligned output
already has deprojection applied and must not be deprojected again. The existing
interactive GUI prefers S4G paths over manifest paths and assumes north-up pixel
geometry, so this manifest is for this standalone extraction workflow; using it
in that GUI needs changes to its image resolver and WCS handling.
