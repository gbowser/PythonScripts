# Spitzer library versus Euclid Q1: overlap check

Checked 29 October 2026.

The 182 galaxies in the S4G/Spitzer library actually used in this project have
zero positional matches to the current 2,777-galaxy Euclid Q1 working selection.
The nearest pair is NGC1493 and Euclid -598524774465432590, separated by
1,704.04 arcsec (28.40 arcmin). There are zero matches within either 10 or 60 arcsec.
Spitzer centres are transferred through the original FITS WCS, rather than using
an image reference-pixel position as the galaxy centre. Exact Euclid IDs are strings.

A fresh public ESA archive query checked all 182 centres against Q1_R1 VIS
background-subtracted SCIENCE mosaic footprints. It found zero covered centres.
The same query included a known Q1 working-sample target as a positive control;
that target matched one mosaic, verifying the query was working. This concerns
these 182 used galaxies, not the complete Spitzer/S4G survey.

Three existing local two-survey comparison targets remain available:

| Galaxy | Spitzer 3.6 micron image | Euclid VIS observed cutout |
|---|---|---|
| NGC1255 | Present | Present; transferred centre inside image, local pixels finite |
| NGC1436 | Present | Present; transferred centre inside image, local pixels finite |
| NGC1512 | Present | Present; transferred centre inside image, local pixels finite |

These are not in the Q1 working selection and their source FITS headers do not
record a Euclid release identifier. Do not call them Q1 data without separate
provenance. Exact source and observed-cutout paths are in
`existing_spitzer_euclid_comparison_targets.csv`. Existing sampling is approximately
0.75 arcsec/pixel for Spitzer and 0.1 arcsec/pixel for Euclid; pixel scale is not PSF
resolution.

The earlier Euclid aligned cutouts used the Spitzer/S4G geometry. They are useful
for fixed-geometry profile comparisons, but cannot independently validate matching
PAs/inclinations. For an independent geometry comparison, refit each observed image.
For profile comparisons, use matched PSF resolution, common physical or angular
apertures, and normalized profile shapes rather than uncalibrated raw counts.

Files retained here:

- `nearest_current_q1.csv`: nearest selected Q1 target for every Spitzer galaxy.
- `matches_current_q1.csv`: header only, because no matches were found.
- `public_q1_mosaic_centre_matches.csv`: header only, zero footprint matches.
- `q1_positive_control.csv`: successful control target match.
- `q1_mosaic_footprint_query.sql`: exact ADQL query.
- `summary.json`: results, UTC query time, source hashes and existing image details.

Reproduce with `Euclid/compare_spitzer_q1_overlap.py --check-footprint` using the
project's scientific Python environment. This script downloads metadata only.
Public release context: https://www.euclid-ec.org/science/q1/
