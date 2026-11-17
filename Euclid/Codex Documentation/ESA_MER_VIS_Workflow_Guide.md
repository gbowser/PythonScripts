# ESA Datalabs: Q1 MER VIS cutouts and geometry workflow

Documented 16 November 2026 from the supplied ESA_MER_VIS_review_20261116_111952.zip and the local PythonScripts/Euclid/Q1/datalabs_MER_VIS folder.

## What this workflow does

This is a three-stage workflow: read hosted Q1 MER VIS mosaics and extract galaxy cutouts; fit provisional galaxy disc/bar geometry from those saved cutouts; optionally package the native cutouts into ZIPs for browser download. The script compare_MER_VIS_datalabs_geometry.py performs the second stage. It does not retrieve the original mosaics or make the native cutouts.

The five Python scripts and two top-level input CSV manifests in the ESA export are byte-for-byte identical to the local repository copies. The notebooks differ: the ESA copies contain executed cells and saved outputs, and some run/configuration cells were changed. Untitled.ipynb is the download-packaging notebook, not an unused scratch notebook.

Local source folder:
`C:\Users\gordo\Documents\Github\PythonScripts\Euclid\Q1\datalabs_MER_VIS`

## What actually ran

These findings come from saved execution outputs and CSV reports, not from running the pipeline again:

| Evidence | Result |
| --- | --- |
| Input manifest | 2,777 galaxies using 309 distinct mosaic files |
| Saved source preflight | Zero missing mounted paths; estimated native science output 23.41 GiB |
| Exported cutout processing CSV | All 2,777 rows have status existing_verified |
| Cutout boundary coverage | 2,715 PARTIAL=False; 62 PARTIAL=True |
| Exported cutout verification timestamps | 16 October 2026, 09:46:55–09:55:39 UTC |
| Geometry result CSV | 2,208 provisional_fit; 569 fit_failed |
| Successful geometry fits without quality flags | 557 |
| Successful fits with quality flags | 1,651 |
| Alignment status | 557 not_requested; 1,651 withheld_quality_flags; 569 blank |
| Exported radial profile CSVs | 2,719 |
| Packaging notebook saved output | 2,777 native FITS files, 23.41 GiB; 30 ZIP batches created |

The cutout notebook's earlier saved summary says 2,772 created and five existing_verified. The separate processing CSV records all 2,777 as existing_verified, showing a subsequent verification pass. These are snapshots of different runs, not contradictory totals.

The exported geometry notebook ran comparison.run(..., limit=None). Its later optional make_aligned=True cell remains commented out. The result manifest records no successful alignment. This establishes the state of this exported run; it does not prove that no aligned FITS exists anywhere else.

Most geometry failures are insufficient bar/disc isophotes in selected ranges (427 objects). Other failures report too few reliable isophotes. Failure means the automatic method did not supply usable geometry; it does not invalidate the native cutout.

No FITS images or diagnostic PNGs were included in the review ZIP. Their present existence, pixels and scientific quality have not been checked. Saved notebook outputs can remain after files are deleted.

## Locations in ESA Datalabs

The screenshot shows the browser location `/my_workspace/Euclid_MER_VIS`. The executed notebook prints the actual Python filesystem location `/media/user/Euclid_MER_VIS`. The saved reports use that same filesystem path. This explains why the earlier terminal command using `/my_workspace/` failed: a file-browser path is not necessarily an operating-system path.

```text
/media/user/Euclid_MER_VIS/
    MER_VIS_Datalabs_Cutouts.ipynb
    make_MER_VIS_datalabs_cutouts.py
    MER_VIS_datalabs_manifest.csv           input target/source list
    MER_VIS_Geometry_Comparison.ipynb
    compare_MER_VIS_datalabs_geometry.py
    fit_MER_VIS_geometry_portable.py
    MER_VIS_geometry_transforms.py
    MER_VIS_geometry_comparison_manifest.csv  input template
    package_MER_VIS_downloads.py
    Untitled.ipynb                         packaging launcher
    cutouts/
        Euclid_<object_id>_MER_VIS_cutout.fits
        MER_VIS_processing_manifest.csv
        Euclid_<object_id>_MER_VIS_bar_aligned.fits  optional
    geometry_comparison/
        MER_VIS_geometry_comparison_manifest.csv  filled results
        profiles/
            Euclid_<object_id>_MER_VIS_ellipse_profile.csv
            Euclid_<object_id>_MER_VIS_ellipse_overlay.png
            Euclid_<object_id>_MER_VIS_geometry_review.png
    download_batches/
        MER_VIS_batch_001.zip ...
        MER_VIS_batch_001.json ...
        MER_VIS_zip_index.csv
        MER_VIS_file_checksums.csv
        MER_VIS_datalabs_manifest.csv
```

The comparison input and output have the same filename but different directories. Read the CSV inside geometry_comparison for calculated results. The top-level template still has all 2,777 rows marked not_run_on_Datalabs_cutout.

## How the Q1 images are retrieved

The cutout helper reads MER_VIS_datalabs_manifest.csv. Each row supplies the exact signed object_id, RA/Dec in degrees, angular cutout width, source mosaic filename, tile index, and complete datalabs_source_file.

For example, the first target has object_id -520196615291310590, RA 52.01966158444918 degrees, Dec -29.131059049852368 degrees, and requested width 93.67575279495692 arcsec. Its source is:

```text
/data/euclid_q1/Q1_R1/MER/102042913/VIS/
EUC_MER_BGSUB-MOSAIC-VIS_TILE102042913-EE5E4F_20241021T041311.751862Z_00.00.fits
```

Those two lines form one full filesystem path. The helper opens it with fits.open(source, memmap=True). This accesses the mounted ESA data volume; it does not download a complete mosaic into your personal workspace. No archive login, HTTP request, TAP query or cutout web service is made by these runtime scripts. The manifest contains cutout_url and archive metadata, but this helper does not use those URLs.

The source selection was prepared before execution: the runtime trusts the mosaic mapping in the manifest. It does not search neighbouring tiles or re-query the catalogue. It sorts selected rows by source filename, then opens a source for each galaxy. It does not keep a mosaic cache across objects.

The source is an already combined, background-subtracted Q1_R1 MER VIS science mosaic, not an individual exposure. The code selects the first two-dimensional FITS image HDU; it does not explicitly select an HDU by the name SCIENCE. The science-product mapping therefore matters.

If this Q1 mount is missing in a future instance, preflight will list missing source files. The earlier euc_ero_data_01 examples are a different dataset and cannot substitute for these Q1 mosaic paths. Establish the mounted Q1 location before processing; do not guess a replacement prefix.

## How native cutouts are made

make_MER_VIS_datalabs_cutouts.py provides preflight(), make_one() and run().

1. Convert each row's RA/Dec into an Astropy SkyCoord and read the source celestial WCS.
2. Reject lookup-table WCS distortions requiring a specialist method.
3. Derive the pixel scale separately along both axes. Divide cutout_width_arcsec by those scales and round upward to obtain image dimensions. Width comes from the prepared catalogue display size, not a newly measured bar or disc radius.
4. Use Astropy Cutout2D at the target sky coordinate, with mode='partial', NaN padding and a copied pixel array. The output stays on the native image grid: no rotation, deprojection, smoothing or pixel resampling is applied at this stage.
5. Use the selected mosaic only. A boundary-crossing cutout is padded; adjacent tiles are not stitched in. PARTIAL=True means some requested area extends beyond that mosaic, not necessarily that the galaxy itself is truncated.
6. Retain the cutout celestial WCS and science metadata. Add object identity, RA/Dec, one-based CENX/CENY, requested width, source filename, tile ID and PARTIAL.
7. Save a single float32 primary science HDU with FITS checksums. Write a temporary .partial.fits and rename it after completion.

Outputs are named Euclid_<object_id>_MER_VIS_cutout.fits inside cutouts. Negative IDs retain their minus sign. Treat these long IDs as text when opening CSVs in spreadsheet software to avoid rounding.

Only science pixels are extracted: there are no RMS, weight, segmentation or detector-quality extensions in these generated files. Source NaNs are retained. The run report records created/existing_verified/error, dimensions, PARTIAL, finite-pixel fraction, errors and a UTC check timestamp. It is checkpointed after every object via a temporary CSV and replacement.

On rerun, existing files are checked for matching GALID and valid CHECKSUM/DATASUM, then skipped. This is not a full comparison against a changed manifest or changed source data. Use a separate output folder if deliberately changing the sample, width or source version. The free-space guard leaves an estimated 1 GiB reserve, but filesystem free space does not establish your personal ESA storage quota.

## How geometry is calculated

compare_MER_VIS_datalabs_geometry.run() reads the top-level comparison template and existing cutouts. It loads previous results by exact object_id if an output CSV already exists, then preserves every template row while processing the selected subset. It checkpoints the full output after each object.

For each target it verifies GALID, reads the stored centre and WCS, and converts the catalogue detection pixel position angle to sky PA using the local WCS matrix. It also converts the detection semimajor-axis size to arcseconds. This assumes the catalogue detection and MER science images share the relevant native grid.

fit_MER_VIS_geometry_portable.fit_one() then:

- Builds a temporary 2x2 binned fitting image; native FITS pixels remain unchanged. Bins with fewer than three valid pixels are masked.
- Estimates/subtracts a background from outer image pixels using sigma clipping.
- Detects connected regions above three times the estimated noise in a smoothed image, retains the region at the fixed catalogue centre, and masks/dilates disconnected neighbours.
- Runs Photutils isophotal ellipse fitting with several starting guesses and a fixed centre. The code accommodates Photutils 2/3 argument differences.
- Retains reliable isophotes with valid fits, stop_code=0, at least 70% sampled support, and positive sufficiently significant intensity. At least ten are required.
- Automatically selects a bar range around an inner ellipticity peak and an outer-disc range. At least three reliable isophotes are needed in each selected interval.
- Calculates axial mean bar/disc sky PAs and disc axis ratio from those intervals. Inclination uses the thin circular-disc assumption q0=0, so i=acos(q).
- Saves radial CSVs and diagnostic plots, with flags for unstable PA/axis ratio, near face-on orientation, high inclination, weak bar signature or small bar size.

The runner labels successful fits provisional_fit. Numerical success or no flags does not make the automatic radial selections scientifically reviewed. Foreground sources connected to the galaxy, spiral arms, rings and PSF effects can bias geometry. Fit masks are temporary analysis masks, not new cleaned science images.

The Euclid detection PA is a whole-object shape, not a measured bar PA; catalogue inclination proxies are also not independent disc measurements. The Euclid bar PA column remains blank. PA differences use the axial interval [-90,90). Diagnostic scatter describes radial variation, not calibrated measurement uncertainty.

Successful fits are reused on rerun. Failed fits are skipped unless retry_failures=True. Do not run simultaneous writers to the same output folder. Changing fitting code or settings does not automatically invalidate saved successful fits.

## Optional face-on, bar-aligned outputs

make_aligned=True requests an additional transform for provisional fits with no quality flags. MER_VIS_geometry_transforms.py expands the disc minor axis by 1/cos(i), transforms the bar direction and rotates it onto the output x-axis. Bilinear interpolation resamples science values; it does not preserve integrated flux, and it introduces correlated noise.

The output is a square native-cutout companion named *_bar_aligned.fits in cutouts, containing primary science and a COVERAGE extension. Its coordinate axes are linear arcseconds, not celestial RA/Dec. GEOMSTAT=PROVISIONAL and Q0=0 record its provisional geometry. RMS/FLG handling exists in the transform, but the normal native cutouts here do not contain those extensions. Fitting masks are not propagated into transformed science.

This optional stage was not enabled in the supplied executed notebook. Existing aligned files are protected/checked rather than silently replaced. The runner only requests alignment for provisional_fit rows; manually assigned reviewed_ranges rows have different handling and should not be assumed to produce aligned images automatically.

## How to run using the notebook interface

You do not need a terminal. Open the notebook from my_workspace > Euclid_MER_VIS, select the Euclid Python kernel with NumPy, Astropy, SciPy, Photutils and Matplotlib, then run chosen cells with Shift+Enter (or the toolbar run button). The saved cutout execution used Python 3.12.13 and Astropy 8.0.0. No fresh environment installation was tested in this audit.

### Create or verify cutouts

Open MER_VIS_Datalabs_Cutouts.ipynb. Run the configuration cell: the ESA copy uses WORK = Path.cwd(). Confirm it prints /media/user/Euclid_MER_VIS and the expected cutouts destination. Run the source preflight; investigate missing paths and check your quota before extraction. Run the five-object cell and inspect its image/report. To process or verify every target, run:

```python
mer.run(MANIFEST, OUTPUT, limit=None)
```

The ESA copy already has this full-run line enabled. Do not use Run All without checking which expensive cells are active. Existing valid cutouts are verified; missing cutouts are recreated from the mounted source. The exported report already records successful verification of all targets, so there is no reason to regenerate them solely to inspect the results.

### Read or resume geometry results

Open MER_VIS_Geometry_Comparison.ipynb. Run its configuration cell and confirm WORK, CUTOUTS and RESULTS. Run its summary cell to read existing statuses without running fitting. Results are in geometry_comparison/MER_VIS_geometry_comparison_manifest.csv; inspect diagnostic PNGs in profiles in ESA.

For a new pilot, use:

```python
comparison.run(TEMPLATE, CUTOUTS, RESULTS, limit=5)
```

For all targets, without aligned images:

```python
comparison.run(TEMPLATE, CUTOUTS, RESULTS, limit=None)
```

The ESA notebook's first fitting cell has already been changed to limit=None, despite its nearby heading describing five objects. Check the code itself. To retry the 569 failures, explicitly use retry_failures=True; unchanged algorithms may fail again. To request optional aligned products add make_aligned=True, after reviewing scientific suitability and storage needs.

### Recreate download ZIPs only

Open Untitled.ipynb. Its saved code is:

```python
from pathlib import Path
import sys
WORK = Path('/media/user/Euclid_MER_VIS')
sys.path.insert(0, str(WORK))
import package_MER_VIS_downloads as packages
packages.package(WORK, max_files=100, max_mib=1024)
```

The packager requires a nonempty native cutout for every input row before creating any batches. It packages only the native cutouts, not aligned FITS or geometry plots. Groups contain at most 100 files and approximately 1,024 MiB of uncompressed inputs, except that one oversized input can exceed that size on its own. ZIP compression is enabled.

Each archive contains per-file SHA256 records; an adjacent JSON stores input sizes/timestamps and ZIP checksum. CSV indexes are checkpointed after each batch. Existing archives are reused only if their sidecar metadata and archive checksum agree; missing/mismatched records produce an error rather than silent replacement. The packager checks existence/size of inputs, not FITS checksums itself.

Download completed archives using the browser's right-click Download action. For notebook links, run packages.show_links(WORK) in an additional cell. The script retains original FITS files and creates ZIP copies, requiring additional quota.

The 30 saved batch-creation messages establish that packaging happened previously. An empty download_batches folder today is consistent with later cleanup, but neither this ZIP nor the saved output proves who deleted it or when. Regenerating ZIPs does not require rerunning cutout creation or geometry fitting if the native files remain. Since download_batches was excluded from this review export, its current contents cannot be independently assessed here.

## Entry points and verification limits

The notebooks import helpers and call functions. Running python compare_MER_VIS_datalabs_geometry.py, python make_MER_VIS_datalabs_cutouts.py or python package_MER_VIS_downloads.py alone does not launch processing: those files have no command-line main entry point. The standalone fit_MER_VIS_geometry_portable.py does have a CLI, but that is a separate fitting path and does not fill the comparison CSV in the same way. Prefer the named notebooks for this workflow.

This documentation is based on source inspection, SHA256 equality checks, notebook code/saved output, and report counts. No scientific processing, remote ESA access, live mount check or FITS validation was performed during this audit. The local older README describes an unexecuted workflow and points to a later adaptive MER VIS pipeline; its historical 'not run' statements do not describe the completed ESA runs found in this export. This document describes the exported Datalabs workflow specifically.
