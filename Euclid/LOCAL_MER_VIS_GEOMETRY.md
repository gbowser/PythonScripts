# Calculate local MER VIS galaxy geometry

From C:\Users\gordo\Documents\Github\PythonScripts, run:

```powershell
& '.\.venv\Scripts\python.exe' '.\Euclid\calculate_local_MER_VIS_geometry.py'
```

This processes all remaining galaxies using two independent worker processes.
It reads the verified FITS cutouts in:

D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_cutouts

Default output folder:

D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry

## Outputs

- MER_VIS_local_geometry_manifest.csv: one row for every one of the 2777 targets,
  including unsuccessful and pending fits, preserving input catalogue order.
- profiles/: ellipse profiles and diagnostic overlay/review PNGs.
- logs/: per-object fitting output and errors.
- MER_VIS_local_geometry_summary.json: status counts and elapsed time.
- MER_VIS_local_geometry_run.json: algorithm and catalogue fingerprints for resuming.

The first five real objects have been tested locally: four provisional fits and
one fit_failed due to insufficient reliable ellipses in the automatically
selected bar/disc ranges. The rest are initially not_processed_local.

## Manifest interpretation

codex_bar_pa_sky_deg and codex_disc_pa_sky_deg are degrees east of north,
modulo 180. codex_inclination_deg is tilt from face-on, in degrees. These are
provisional Photutils measurements using the earlier algorithm, with fixed
catalogue centres, inner ellipticity/bar ranges and outer disc ranges.
The q0=0 thin circular-disc assumption is used consistently for comparisons.
Quality flags and radial PA scatter are retained; convergence is not a final
scientific confirmation. Missing or failed estimates remain blank, never zero.

Euclid detection POSITION_ANGLE is an image-pixel direction, not a bar PA. Its
conversion to the same sky-angle convention uses the actual native cutout WCS,
assuming the shared detection/science MER tile grid. The relevant converted
column is euclid_detection_pa_sky_deg. It is a whole-object shape direction,
not an independently measured outer-disc PA.

Euclid detection and Sersic axis ratios supply inclination proxy columns,
using i=acos(q). The detection q is 1-ELLIPTICITY. Their differences from the
calculated inclination are diagnostics of different shape measurements.
Euclid Q1 supplies no bar PA in the queried morphology tables; that comparison
column is intentionally blank. Separate disc-fit axis ratios are also blank
for this sample. Raw Sersic PA is retained in degrees but is not silently
converted under an unverified angle convention or used as a bar angle.

The Euclid morphology snapshot was retrieved on 16 October 2026. The program
uses this cached exact-object-ID catalogue; it does not make 2777 remote queries
or download images. Existing Euclid raw errors/flags, normalized Zoobot bar
fractions, Zenodo bar fractions and Zenodo version-specific provenance remain
in the manifest. See datalabs_MER_VIS/GEOMETRY_COMPARISON_README.md for the
complete catalogue definitions and scientific limitations.

## Rerun and options

Rerun the same command to resume. Completed fits with unchanged input file
size and modification time are skipped. Recorded failures are skipped unless
--retry-failures is used. Every five completed fits and at normal shutdown,
the parent process checkpoints the full manifest. A forcibly stopped run can
need to repeat up to four completed fits not yet checkpointed. Close the CSV
in Excel during processing, so Windows can replace its checkpoint safely.

```powershell
# Run just the first 20 catalogue targets
& '.\.venv\Scripts\python.exe' '.\Euclid\calculate_local_MER_VIS_geometry.py' --limit 20

# Choose worker count; start with two to keep memory/CPU use reasonable
& '.\.venv\Scripts\python.exe' '.\Euclid\calculate_local_MER_VIS_geometry.py' --workers 4

# Retry failed fits
& '.\.venv\Scripts\python.exe' '.\Euclid\calculate_local_MER_VIS_geometry.py' --retry-failures
```

--input-dir, --output-dir and --catalogue-csv override the locations. If the
catalogue, fitter or radial ranges change, use a new output directory to
preserve the original run and avoid mixing incompatible results.

Optional --ranges-csv accepts one row per object with columns:
object_id,bar_min_arcsec,bar_max_arcsec,disc_min_arcsec,disc_max_arcsec.
Specify positive, increasing, non-overlapping bar and disc ranges. Examine
the profiles before choosing them. Use a new --output-dir for a reviewed run.

This command calculates geometry and diagnostics only. It does not create
rotated/deprojected images or modify the native cutouts. Applying reviewed
geometry to science images remains a separate step.
