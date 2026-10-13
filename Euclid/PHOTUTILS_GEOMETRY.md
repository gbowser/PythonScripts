# Photutils geometry fitting

From the PythonScripts folder:

```powershell
& '.\.venv\Scripts\python.exe' '.\Euclid\extract_calibrated_galaxies.py' --overwrite
& '.\.venv\Scripts\python.exe' '.\Euclid\fit_euclid_geometry.py' --previews
```

Both commands default to the existing Dropbox download/single-galaxy folders.
The extractor searches all downloaded frames for the 25 shortlisted galaxy
centres. It preserves native SCI, RMS, FLG and celestial WCS. PARTIAL means
the requested sky box was trimmed at a quadrant boundary, not necessarily
that the galaxy is incomplete.

The fitter uses Photutils 3 isophotes (Jedrzejewski algorithm), fixes the centre
at the Q1 catalogue position, averages 2x2 valid pixels for fitting only,
estimates a clipped local background, masks VIS quality bits and disconnected
neighbour sources, and clips outliers on each ellipse. Multiple starting
ellipses are tried. It retains converged, adequately sampled positive-S/N
isophotes. Angles are mapped through the actual WCS to degrees east of north,
modulo 180 degrees. It does not refine the catalogue centre.

VIS masking rejects bits 0–19, 21 and 22; OBJECTS, STITCHBLOCK and
CTICORRECTION are retained. Informational OBJECTS pixels must not be rejected
simply because their FLG value is nonzero. Masks are conservative; connected
companions are not deblended. Windows application control blocked a Photutils
segmentation DLL, so neighbour masking uses SciPy connected components;
the ellipse fitting itself uses Photutils.

Files in the single-galaxy folder:

- `*_ellipse_profile.csv`: radial ellipticity, detector/sky PA, formal errors,
  intensity, sampling coverage and fit stop codes.
- `*_ellipse_overlay.png`: diagnostics including failed geometry selections.
- `*_geometry_review.png`: candidate bar/disc radial ranges and profiles.
- `photutils_geometry_manifest.csv`: candidate values, ranges, scatter,
  assumptions, quality flags and output paths.
- `photutils_fit_errors.csv`: failed objects and reasons.
- `*_provisional_bar_aligned.fits`: previews only for candidates passing the
  numerical checks. FITS GEOMSTAT is PROVISIONAL. SCI, propagated RMS, FLG and
  COVERAGE are retained. Output coordinates are deprojected arcsecond offsets.

Automatic bar selection finds an inner ellipticity maximum; the disc is
selected farther out. These selections are hypotheses: spiral arms, bulges,
rings, companions or an unresolved bar can fool them. Review the images and
profiles before adopting these values. Numerical stability alone is not
physical validation. Scatter fields describe radial variation, not calibrated
uncertainties. Individual formal fit errors are in the profiles. PSF modelling
and systematic error propagation are not implemented.

Default inclination assumes an infinitely thin circular disc: i=acos(b/a).
`--q0 0.2` instead adopts cos²(i)=(q²-q0²)/(1-q0²). Choose and record q0 for
the science application; 0.2 is an example, not a universal recommendation.

To select reviewed radial ranges, create a CSV with columns
`object_id,bar_min_arcsec,bar_max_arcsec,disc_min_arcsec,disc_max_arcsec`, then:

```powershell
& '.\.venv\Scripts\python.exe' '.\Euclid\fit_euclid_geometry.py' --ranges-csv '.\Euclid\my_ranges.csv'
```

Require 0 < bar_min < bar_max < disc_min < disc_max. This recomputes estimates;
it does not automatically promote them to final scientific measurements.
To use adopted geometry with the existing deprojector, pass the geometry
manifest with `--geometry-csv` and `--deproject-existing` to the extractor.
Review all quality flags and ensure every extracted object has valid adopted
geometry first. The view radius max(3*bar_max,45 arcsec) uses the selected
bar-range upper bound as an approximate bar size; it is not a measured bar edge.

References:
- https://photutils.readthedocs.io/en/latest/user_guide/isophote.html
- https://euclid.esac.esa.int/msp/dpdd/v1.1/visdpd/dpcards/vis_flagmap.html
