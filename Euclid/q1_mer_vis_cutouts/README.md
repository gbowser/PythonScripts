# Q1 MER VIS galaxy cutouts

The manifest identifies DpdMerBksMosaic, VIS, SCIENCE, Q1_R1 products from
sedm.mosaic_product and generates URLs using the documented ESA cutout service.
It uses actual archive paths, not inferred filenames. Each centre is inside
the selected footprint. Prefer the catalogue tile; otherwise choose the lowest
mosaic product ID. All alternatives are retained in all_mosaic_matches.csv.

Open MER_VIS_CUTOUT_LINKS.md in VS Code and press Ctrl+Shift+V, then click
individual links for manual download. The response can be a ZIP containing a
FITS cutout: extract it and use suggested_output_file from the manifest to
identify the galaxy. The link asks for a CIRCLE with radius equal to half the
catalogue display width, in degrees; the service returns an image cutout, not
a circularly masked galaxy. Inspect actual size, WCS and coverage after download.

One cutout request per galaxy differs from downloading whole mosaics: shared
mosaics still generate separate centred cutout files. No bulk images are
downloaded by this generator. Centre coverage is metadata evidence, not a
complete-pixel or full-galaxy guarantee. Mosaics are already combined and
background-subtracted but are not face-on or bar-aligned. The catalogue width
is a display size, not a scientific aperture. Check background treatment before
measuring faint outer-disc light. Use native celestial WCS when fitting geometry.

Regenerate from PythonScripts:

```powershell
& '.\.venv\Scripts\python.exe' '.\Euclid\build_mer_vis_cutout_links.py' `
  --targets-csv '.\Foreground Masking\q1_full_candidate_audit\morphology_candidates.csv' `
  --overwrite
```

The SQL uses TAP_UPLOAD.targets, so it requires an uploaded coordinate table;
it is not a standalone query to paste into a console without that upload.

Sources:
- https://astroquery.readthedocs.io/en/latest/esa/euclid/euclid.html
- https://euclid.esac.esa.int/dr/q1/dpdd/merdpd/dpcards/mer_bksmosaic.html
