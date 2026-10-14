# Individual calibrated frames: manual archive queries

From `C:\Users\gordo\Documents\Github\PythonScripts`:

```powershell
& '.\.venv\Scripts\python.exe' '.\Euclid\build_euclid_VIS_NISP_frame_query.py'
```

This writes `Euclid/queries/individual_calibrated_frames.sql` and
`Euclid/queries/galaxy_cones.csv`. It makes **no network requests** and downloads
no images. The default input is the existing extraction geometry manifest in
`D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Clean_Galaxy_Output`.

Choose galaxies and an explicit search radius in arcminutes:

```powershell
& '.\.venv\Scripts\python.exe' '.\Euclid\build_euclid_VIS_NISP_frame_query.py' --galaxies NGC1255 NGC1436 --radius-arcmin 2 --overwrite
```

Alternatively prepare a CSV containing exactly these required fields:

```csv
name,ra_deg,dec_deg,radius_arcmin
NGC1255,48.383317699421475,-25.725106667731183,1.25
```

```powershell
& '.\.venv\Scripts\python.exe' '.\Euclid\build_euclid_VIS_NISP_frame_query.py' --targets-csv '.\Euclid\my_galaxies.csv' --overwrite
```

Use `--max-images 1` through `5` to lower the total cap. Values above five are
rejected in this version. There is one combined SELECT TOP query, not five rows
per target. Frames matching multiple cones occur once in that query. The limit
does not guarantee a frame for each galaxy; several exposures of one field may
occupy all five rows. The ordering is deterministic, not an image-quality ranking.

The default instrument is VIS, product type `DpdVisCalibratedQuadFrame`, in
`sedm.calibrated_frame`. For NISP use `--instrument NISP --filter NIR_H` (or
`NIR_Y` / `NIR_J`). These select `DpdNirCalibratedFrame`. No mosaics or stacked
products are queried. Columns include the frame identifier and file metadata
needed to identify the individual science FITS in the archive.

## Radius and cone semantics

Coordinates are ICRS decimal degrees. Input radii are arcminutes and are converted
to degrees for ADQL CIRCLE. By default the existing manifest's `radius_arcsec/60`
is used: this is the previous **bar-view half-width**, not the full optical galaxy
radius or a circumscribed radius for the square view. Supply measured galaxy
radii or `--radius-arcmin` when you need a different footprint.

Default `--match footprint` uses the archive image search's
`INTERSECTS(CIRCLE('ICRS', ra, dec, radius), f.fov) = 1` syntax. It finds exposures
whose sky footprint intersects the target cone, even when the exposure centre
is outside the cone. Overlap does not guarantee full galaxy coverage or avoid
detector gaps. `--match centre` instead implements the documented generic
`CONTAINS(POINT('ICRS', f.ra, f.dec), CIRCLE(...)) = 1` cone search. With a small
galaxy radius it may miss useful frames centred elsewhere.

## Manual download

1. Open https://eas.esac.esa.int/sas/ and select Search / ADQL Form.
2. Paste the contents of `individual_calibrated_frames.sql` and run that one query.
3. Review the returned frame metadata and available coverage. If there are no
   matches, coverage may be absent from the public release; existing mosaics
   alone do not establish public availability of individual calibrated frames.
4. Identify the individual calibrated science files using the returned
   `file_name`, `product_id`, and `observation_id`; use the archive's image/data
   selection and Manual Download workflow to select no more than five science
   FITS files. A metadata export is not a FITS download. If the ADQL result view
   does not provide image download actions, use these identifiers in image search.
5. Associated background/weight/PSF products can add files to a download package;
   review the package contents before downloading. TOP 5 bounds query rows, not
   the number of optional files bundled by the manual downloader or their sizes.

Individual calibrated frames use detector/quadrant FITS extensions. The current
`extract_euclid_VIS_bars.py` expects a 2D primary HDU and **cannot yet process these
multi-extension exposures directly**. Detector selection and extension-specific
WCS handling are a separate next step.

## Sources and validation

- Archive guides: https://eas.esac.esa.int/sas/#/pages/user-guides
- Official image product overview (archive-linked PDF):
  https://eas.esac.esa.int/archive-help/attachments/DataProducts.pdf
- Astroquery Euclid table/cone examples:
  https://astroquery.readthedocs.io/en/latest/esa/euclid/euclid.html
- VIS individual-frame format:
  https://doi.org/10.1051/0004-6361/202554594
- Live schema: https://eas.esac.esa.int/tap-server/tap/tables

Calibrated-frame columns/product labels and footprint cone syntax were checked
against the public TAP service on 2026-10-13 using small metadata queries only.
The current archive web application's image-search code uses `fov` footprint
intersection. The archive-linked product PDF URL returned 404 during checking;
the product distinction and FITS format are also documented in the VIS paper.

## Check the complete galaxy library

From PythonScripts, run:

```powershell
& '.\.venv\Scripts\python.exe' '.\Euclid\build_euclid_VIS_NISP_frame_query.py' --library --check-availability --output-dir '.\Euclid\library_queries' --overwrite
```

The local library currently contains **182 galaxies**. This command transfers
all catalogue pixel centres to ICRS decimal degrees using original S4G FITS
headers, then checks each cone sequentially against public individual calibrated
VIS frames. It reads at most one metadata row per galaxy, and downloads no FITS.
The manual image limit remains five total; metadata availability checks are not
image downloads.

Outputs in `library_queries`:

- `frame_availability.csv`: one row per galaxy with `available`, `not_available`,
  or `error`, plus an example matching frame when present. Saved after every
  check so an interrupted run retains completed records. These are existence
  checks, not image counts. A query failure is never treated as no coverage.
- `galaxy_cones.csv`: coordinates and radii for every selected galaxy.
- `individual_calibrated_frames.sql`: manual-download query for confirmed
  available targets, with a single TOP 5 cap. If none match, it uses WHERE 1=0.

Library radii use max(3 × observed bar semi-major axis, 45 arcsec)/60, without
clipping to the original S4G image boundaries. This is a bar-region search, not
an optical-galaxy radius. Override with `--radius-arcmin`, select names using
`--galaxies`, or exclude names with `--exclude`. `--library-manifest` overrides
the default S4G geometry manifest. Missing source FITS or invalid coordinates
stop target preparation before archive requests start.

Use `--instrument NISP` to check NISP instead, optionally with `--filter NIR_H`.
The instrument and match mode are recorded in every report row. A no-match
result applies only to the selected product type, public archive coverage, and
search cone at that time; it does not rule out merged mosaics or private data.
The current script does not resume a scan: rerunning with --overwrite rechecks
all selected galaxies. Query errors produce a nonzero exit code after preserving
the report and SQL for the successfully checked targets.
