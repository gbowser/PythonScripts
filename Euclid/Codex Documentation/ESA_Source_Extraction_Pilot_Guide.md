# ESA SEP and MTObjects pilot

Prepared 16 November 2026.

## What has previously been used in ESA

The user-supplied ESA_MER_VIS_review_20261116_111952.zip contains no SEP,
SExtractor or MTObjects references in the five Python scripts or in notebook
source/text execution outputs. Its geometry code uses Photutils ellipse fitting
and SciPy connected-region detection. This establishes no evidence of either
extractor in the exported workflow; it does not rule out other notebooks or
previous ESA sessions absent from that export. Local repository MTObjects work
is separate and does not establish ESA use.

SEP implements Source Extractor algorithms through Python functions; it is not
the full standalone SExtractor application. MTObjects is a different detector
using a max tree. This pilot exercises both as segmentation tools, not as final
foreground masking or calibrated photometry.

## Transfer and run

1. Download ESA_Source_Extraction_Pilot.zip and extract it on Windows.
2. In ESA, open my_workspace > Euclid_MER_VIS. Upload the four files from the ZIP
   directly into this folder, alongside the existing manifests and cutouts:
   ESA_Source_Extraction_Pilot.ipynb, install_pilot.py, run_pilot.py, mto_worker.py.
   Do not leave them inside an extra nested folder.
3. Open the new notebook and select the Euclid scientific Python kernel.
4. Run the workspace cell with Shift+Enter. WORK uses the notebook working
   directory and should resolve to /media/user/Euclid_MER_VIS. ROOT is its
   source_extraction_pilot subfolder. Assertions check manifest/cutout presence.
5. Run the install cell. A private environment is created under ROOT/environment
   with access to the existing scientific stack; its core package versions are
   constrained while SEP and scikit-image are installed. The shared kernel is
   not upgraded. Setup needs internet, git and gcc; no sudo is used.
6. MTObjects is cloned from CarolineHaigh/mtobjects and the four native Linux
   libraries are compiled in ROOT/mtobjects/mtolib/lib. Existing source checkouts
   are retained and not automatically pulled/reset. installation.json records
   source commit, package versions, and whether native import succeeded.
7. Run the three-image cell. It starts the private environment's Python in a
   subprocess. METHODS=['sep','mto'] runs both; use ['sep'] if the MTO compiler or
   native build is unavailable. The console log is printed after completion.
8. Run the display cell to inspect summary.csv and comparison PNGs.
9. Run the final archive cell, then download the printed results ZIP through the
   file browser and return it for review. Original full cutouts are not archived.

The setup may take several minutes. A successful installation is not a completed
image trial. Read summary.csv: success/failure is recorded separately per method
and object, so the subprocess may finish normally even if a method failed.
MTObjects has a five-minute timeout per image. If the kernel is restarted, rerun
the configuration and installation cells before continuing. Do not run concurrent
setup cells against the same ROOT folder.

## Sample and settings

Default selection is the first three suitable targets in manifest order with
an existing GALID-matching native cutout, PARTIAL=False, and a fully finite crop.
Image windows are centred on stored CENX/CENY and limited to 1024 pixels per axis,
without binning/resampling. Window edges may trim to source boundaries. Thus a
pilot image can exclude galaxy outskirts even though the original cutout is
complete. Red crosses show the catalogue centre. This is a speed/memory bound,
not a scientifically selected fitting aperture. No full Q1 mosaics are read.

SEP uses a spatial background/RMS estimate, 1.5-sigma threshold, minimum area 5,
32 deblend levels and deblend contrast 0.005. The residual subtraction is a local
pilot operation on already background-subtracted MER pixels. It may remove
extended galaxy light and needs review before adopting production settings.

MTObjects uses upstream tree/detection routines with alpha=1e-6 and move_factor=0.3,
a clipped global background/noise estimate, and an effective gain estimated from
image values. MER mosaics have correlated noise; this gain is not an instrument
calibration. These are baseline feasibility settings, not the optimised local
foreground-masking workflow. SEP and MTO have different preprocessing/noise
models here, so this is not a controlled sensitivity or photometry benchmark.

The worker uses a modern float64 FITS reader instead of upstream's obsolete
np.float reader, and writes the segmentation FITS through modern Astropy instead
of the upstream clobber argument. It runs from the upstream source directory so
relative native-library paths resolve. Detection algorithms are not patched.
Upstream native compilation and modern-Python compatibility still need the ESA
trial; any additional failure is retained in mto.log.

## Outputs

All installed packages/source and derived results are under:
/media/user/Euclid_MER_VIS/source_extraction_pilot

Each run creates a fresh results_<UTC timestamp> folder containing:

- configuration.json and installation.json with parameters and versions.
- summary.csv with object ID, method, status, detected object count, centre label
  and error text. A centre label <=0 denotes background/unassigned, not a galaxy
  classification. Labels are not comparable numerically across methods.
- One folder per object, with pilot_input.fits, crop/WCS/source provenance and
  input SHA256, sep_segmentation.fits, sep_catalogue.csv, SEP background/RMS FITS,
  mto_segmentation.fits, mto_catalogue.csv, mto.log, and comparison.png as available.

FITS segmentations retain the crop WCS. Upstream MTO catalogues have their own
schema/conventions; they are not a matched equivalent of the SEP catalogue.
Segmentation boundaries can include foreground objects, other galaxies and
internal galaxy structure. No automatic foreground classification, adopted mask,
cleaned image, geometry refit or modification of source FITS occurs.

Every rerun makes new copies of pilot input arrays and derived maps. Even bounded
crops and environment installation consume personal quota. The default sample is
small, but check quota before enlarging it. Pilot argument bounds allow 1–5 images
and at most 1536 pixels per axis; full-sample processing is intentionally absent.

## Validation status

All three Python scripts and every code cell pass syntax parsing. An attempted
three-synthetic-image local integration test could not import Astropy WCS because
Windows Application Control blocked the existing environment's compiled cparser
DLL. The test therefore did not exercise SEP detection or MTObjects. No attempt
was made to alter that policy or replace the scientific environment. No package
installation, native compilation, remote ESA execution or MER image trial has
been completed by this task. Run the notebook in ESA and return its result ZIP
for actual validation and scientific review.

## Primary references

- SEP installation and project: https://github.com/sep-developers/sep
- SEP detection, background and FITS byte-order guidance:
  https://sep.readthedocs.io/en/stable/tutorial.html
- MTObjects upstream source/build and parameter guidance:
  https://github.com/CarolineHaigh/mtobjects

## GSL installation correction 16 November 2026

First ESA setup succeeded for SEP 1.4.1 and scientific imports. MTObjects checkout
b38a07a91a39097fdd8b7c40b530757a669533c8 cloned, but gcc failed because
gsl/gsl_cdf.h was missing. Revised install_pilot.py installs conda-forge GSL
in ROOT/gsl-runtime with package cache ROOT/conda_packages; explicitly adds its
include/library paths and links -lgsl -lgslcblas -lm with a persistent RPATH.
It records native dependency metadata and suppresses pip-list console output.
Upload replacement installer, reload module, rerun install cell. No kernel/base
upgrade, sudo, or need to reinstall the notebook. Revised syntax passes;
GSL download/build/import and image trials remain pending ESA execution.

## First ESA image trial reviewed 16 November 2026

Reviewed results_20261116T115038_525381Z.zip, including three comparison PNGs,
configuration, summary and MTO logs. MTO completed all three input objects:
-520196615291310590: 471 detections (263 nested);
-519465826287599179: 405 (202 nested);
-519246610291156594: 190 (102 nested).
SEP completed first/third with 488/195 detections. Middle failed because spatial
RMS was nonpositive at 852 of 573049 pixels. Reproduced from exported finite
757x757 input: minimum RMS -0.0086103864, global RMS 0.00354532781.
The failure was the pilot noise guard, not an installation failure. Do not infer
that the nearby bright star caused the invalid RMS without further investigation.

Revised run_pilot.py logs the spatial-noise issue and uses a constant positive
SEP global RMS for the whole affected image; no abs-value clipping or silent
pixel repair. Records sep_noise_model.json, original and effective RMS FITS.
Validated noise preparation and SEP extraction on all three actual exported
inputs locally (Astropy FITS reader and SEP load without the blocked WCS import).
Local detections 195, 485, 489 in sorted-ID order; local run is not identical to
ESA software stack and exact labels/counts are not promised. The other two inputs
retain their spatial RMS algorithm. Full runner/WCS/MTO execution was not rerun
locally. Upload replacement run_pilot.py, rerun image and display/archive cells;
no reinstall required. New run folder retains the previous results.

Visual assessment: target centre has positive labels for every successful method.
MTO boundaries often extend farther and are more irregular; the bright-star
field includes its halo/spikes and structured background. Detection totals alone
cannot rank methods, especially with MTO nested detections and different noise
models. No foreground masks adopted, no cleaned images or geometry refit.
