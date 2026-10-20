# Euclid MER VIS galaxy report review

The full collection contains one PNG per galaxy, with image, fitted ellipses, profiles, calculated geometry, Euclid counterparts and signed differences. Existing fits are reused. Euclid detection PA includes the adopted +90 degree adjustment modulo 180 degrees. Euclid bar PA is not provided. Inclination counterparts are thin-disc proxies from Euclid detection ellipticity and single-Sersic shape.

## Quality issue filenames and folders

`png_QI` contains reports ending `_QI.png`. A report belongs here if ANY of these applies:
- One or more automatic geometry quality flags.
- A failed fit (or any status other than a completed provisional fit).
- Partial coverage of the requested cutout box.

`png_NoQI` contains reports without these detected issues. This is not a scientific approval label: the physical disc and bar identification still require review. Partial requested coverage does not necessarily mean the galaxy itself is truncated.

The full sample contains 2250 QI reports and 527 NoQI reports. These categories are mutually exclusive. Geometry flags, failures and partial coverage can overlap.

## PDF review batches

`pdf_QI` contains PDFs ending `_QI.pdf` and includes only quality-issue reports. `pdf_NoQI` contains PDFs ending `_NoQI.pdf` and includes only the remaining reports. No PDF mixes the two groups. Each batch has at most 60 galaxies, displayed six per A4 page, for at most ten pages. The final batch in each group can be shorter. There are 38 QI PDFs and 9 NoQI PDFs, 47 total.

## Finding a galaxy

`MER_VIS_report_review_index.csv` lists each exact galaxy ID, status, original flag strings, partial-coverage indicator, PNG path, PDF batch, page and position on page. Positions 1 and 2 are the upper row, 3 and 4 the middle row, and 5 and 6 the bottom row. Read the long object IDs as text to preserve all digits. Paths in the index are relative to this folder.

`MER_VIS_report_manifest.json` preserves the report values and display metadata. Per-galaxy metadata enables resuming interrupted generation. `MER_VIS_report_summary.json` records the final generation counts and errors. `MER_VIS_pdf_batches.json` gives each PDF's galaxy and page count.

## Interpreting the cards

Amber highlights geometry or coverage concerns and red identifies failed fits. Missing geometry is displayed as unavailable, never zero. For failures, plotted automatic radial intervals, when available, are explicitly labelled candidate ranges only. Orange shading and ellipses identify the bar interval, green the disc interval. Profiles are limited to the reliable radial extent for readability. Sky PA is east of north modulo 180 degrees, independent of image viewer orientation; north and east arrows show native image orientation. PA deltas are wrapped signed axial differences; inclination deltas are ordinary fit minus Euclid values.

All original science FITS files and the source fitting manifest are retained unchanged. The original ten-image pilot remains available separately. This grouped full collection is the current review set.
