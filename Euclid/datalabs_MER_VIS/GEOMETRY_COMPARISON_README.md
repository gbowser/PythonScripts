# MER VIS geometry comparison

## What is ready

MER_VIS_geometry_comparison_manifest.csv contains all 2777 galaxies, their
expected local FITS filenames, Euclid catalogue measurements, bar classifications
and provenance. It was joined by exact signed integer object_id, not sky proximity.
All 2777 matched the main and morphology tables. The raw query results and SQL
are retained. Catalogue snapshot and provenance are from 16 October 2026.

Codex geometry is initially blank and marked not_run_on_Datalabs_cutout.
The complete images are in your ESA account, so no full-batch computation has
been performed locally. Do not read blank calculated columns as zero angles.

## Five files to upload to your existing workspace folder

1. MER_VIS_Geometry_Comparison.ipynb
2. compare_MER_VIS_datalabs_geometry.py
3. fit_MER_VIS_geometry_portable.py
4. MER_VIS_geometry_transforms.py
5. MER_VIS_geometry_comparison_manifest.csv

Use /media/user/Euclid_MER_VIS, alongside the existing cutouts folder. Open the
new notebook, select EUCLID-TOOLS, and run the configuration cell followed by the
five-object test. Inspect geometry_comparison/profiles and the output CSV.
Remove # from the full-batch cell when ready. The output manifest preserves all
2777 rows, including unprocessed and failed cases. Reruns reuse completed fits;
retry_failures=True retries failed fits. Do not run concurrent copies against the
same output directory. The notebook does not need an archive login or HTTP
image downloads. Keep the kernel running until complete.

The full-batch example includes make_aligned=True. This makes provisional
face-on, bar-aligned FITS files in cutouts for fits without numerical quality
flags. Native files are preserved. These outputs use GEOMSTAT=PROVISIONAL and
linear deprojected arcsecond coordinates. They require visual review before
scientific measurement. Remove make_aligned=True to calculate the manifest only.

## Principal columns and units

- object_id and fits_filename identify each source and its expected native cutout.
- codex_bar_pa_sky_deg is the estimated observed bar PA, east of north modulo 180.
- codex_disc_pa_sky_deg is the estimated outer-disc major-axis sky PA in the same convention.
- codex_inclination_deg is the estimated tilt, 0 face-on and 90 edge-on. This is
  the deprojection angle. Both disc PA and inclination are needed to deproject;
  bar PA is then transformed and aligned with the x-axis.
- codex_fit_status, codex_quality_flags and codex_error report results honestly.
  Values are provisional; failed fits are not replaced with invented angles.
- euclid_detection_pa_pixel_deg is POSITION_ANGLE: SExtractor THETA_IMAGE in
  degrees counterclockwise from pixel +x towards +y, not a sky bar angle.
- euclid_detection_pa_sky_deg converts that direction through the native cutout
  WCS at the galaxy centre. This assumes native MER science/detection tile grid
  alignment. Conversion occurs in Datalabs, where the actual WCS is accessible.
- euclid_detection_ellipticity and euclid_detection_semimajor_axis_pix retain the
  original detection morphology. The semi-major axis is a light-distribution
  moment size, not a measured bar semi-major axis. Its converted arcsecond
  value is added by the Datalabs runner.
- euclid_detection_inclination_proxy_deg derives q=1-ELLIPTICITY and i=acos(q).
  It describes an assumed circular disc with the whole-object detection shape;
  it is not an independently measured disc inclination.
- euclid_sersic_q_vis and euclid_sersic_inclination_proxy_deg use the fitted
  whole-galaxy VIS Sersic axis ratio. The latter also uses i=acos(q).
- euclid_sersic_angle_raw_deg and euclid_disk_sersic_angle_raw_deg retain raw
  catalogue angles. A verified sky-angle convention is not established here,
  so these are not used in sky-PA differences or silently converted.
- euclid_disk_sersic_q and euclid_disk_sersic_inclination_deg are blank for all
  2777 objects: the separate disc-fit axis ratio is unpopulated in this sample.
- euclid_bar_pa_sky_deg is blank for every object because the queried Q1
  morphology does not provide a bar position angle. POSITION_ANGLE must not
  be relabelled as bar PA.
- All inclinations use q0=0, an infinitely thin circular disc. This assumption
  is recorded in q0. Code clips no invalid catalogue q into an apparently valid
  measurement; invalid/missing values remain blank.
- disc_vs_detection_pa_difference_deg is a signed axial difference in [-90,90).
  It compares different structures and is a diagnostic, not a validation truth.

## Bar classifications and version provenance

Euclid Zoobot BAR_STRONG, BAR_WEAK and BAR_NO are Dirichlet concentrations,
not fractions. Both raw values and normalized fractions are retained. Each
fraction is its concentration divided by the sum of all three. Their strong
plus weak fraction is also supplied. There are usable values for 2767 objects;
ten have unavailable/invalid bar values and normalized columns remain blank.

Zenodo strong_bar_fraction and weak_bar_fraction used in the selection are
preserved separately as zenodo_bar_strong_fraction and zenodo_bar_weak_fraction,
along with zenodo_bar_any_fraction. These are model classification fractions,
not physical bar torque, force ratio or a measured bar PA. Euclid and Zenodo
values need not be identical; their provenance and processing may differ.

The Zenodo record is 15106473, version-specific DOI 10.5281/zenodo.15106473.
It is the fourth record in the retrieved version history. The API does not
supply a metadata.version label: zenodo_version_label is therefore blank,
while zenodo_version_ordinal is 4. Updated date and CSV MD5 are retained.
The MD5 is the checksum published by Zenodo; the historic streamed selection
was not independently validated against a downloaded complete-file checksum.

## Algorithm and limits

The portable fitter reuses the previous Photutils ellipse fitting and automatic
bar/outer-disc radial selection. Fixed catalogue centre, 2x2 fitting bins,
background estimation, disconnected-neighbour masks and ellipse sigma clipping
are retained. Science-only MER cutouts have no FLG extension; no detector flag
map is applied in that case. Connected companions, PSF effects, rings and spiral
arms can bias the fit. Scatter records radial variation, not calibrated parameter
uncertainties. Automatic convergence is not physical validation.

The portable transform reuses the earlier disc expansion and bar alignment.
Interpolation preserves surface-brightness samples, not integrated flux, and
introduces correlated noise. COVERAGE reports image support. Quality masks used
for fitting are not applied to the transformed science. No forced deprojection
is made for failed or quality-flagged fits.

## Sources

- https://euclid.esac.esa.int/dr/q1/dpdd/merdpd/mermorphologycookbook.html
- https://euclid.esac.esa.int/dr/q1/dpdd/merdpd/dpcards/mer_finalcatalog.html
- https://sextractor.readthedocs.io/en/latest/Position.html
- https://zenodo.org/records/15106473

Local verification: synthetic barred-galaxy ellipse fitting, WCS angle conversion,
bar-to-x transform, 2777 exact ID joins, normalized bar fractions and notebook
syntax/imports passed. The full Datalabs batch has not yet been executed.
