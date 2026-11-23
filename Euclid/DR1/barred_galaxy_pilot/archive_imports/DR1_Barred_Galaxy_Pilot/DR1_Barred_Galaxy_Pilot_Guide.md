# DR1 barred-galaxy preview pilot — 16 November 2026

Open **gallery.html** to review all 100 galaxies. DR1_first100_review.csv is the concise review manifest; query_evidence/DR1_first100_manifest.csv retains full input metadata and cutout URLs. Import object_id as TEXT in Excel: these signed 64-bit identifiers lose precision if treated as spreadsheet numbers.

## Selection and total

Live ESA TAP release DR1_R2: **166,553 qualifying catalogue IDs**, comprising Wide 165,251 and Deep 1,302, with zero shared qualifying IDs. These are model-selected candidates before population-wide image coverage checks or physical-source deduplication. Different IDs may describe the same physical galaxy.

This is the user-approved **provisional selection**, not an exact repeat of Q1. All four normalized fractions must be >=0.8:

- featured / (featured + smooth), provisionally omitting the unavailable third answer;
- not-edge-on / (not-edge-on + edge-on);
- spiral-yes / (spiral-yes + spiral-no);
- (strong-bar + weak-bar) / (strong-bar + weak-bar + no-bar).

The morphology values are Dirichlet concentrations, not already normalized probabilities. Each denominator must be positive and finite; malformed concentrations are rejected. The DR1 artifact/star/zoom answer has zero populated rows in both survey tables. Strict three-answer selection therefore cannot reproduce Q1 on these data. The Q1 training-warning exclusion has no equivalent available field here and is not applied. Missing information is not evidence that the excluded class is absent. The builder defaults to strict selection; provisional selection requires the explicit option below.

The first 100 IDs in signed integer order across Wide and Deep are used, all Wide in this pilot. This is deterministic, not random or representative of the full population. Repeated visit/mode catalogues are excluded. Exact executed ADQL, response CSVs, query hashes and elapsed times are in query_evidence. Selection is joined to catalogue positions and cutout corners by ID and release, then to R2 VIS science background-subtracted mosaics by tile. No new morphology classifier was run.

## Coordinates, size and previews

Positions are ICRS RA/Dec in degrees. Requested square width is 1.2 times the catalogue-corner extent about the centre, with a 30 arcsec minimum and 300 arcsec cap. These 100 requested widths span 30.00–81.66 arcsec. This is an extraction/display size, not a measured bar length. Native semimajor-axis values are pixels; they should not be mistaken for angular radii. All 100 returned FITS cutouts were decoded and their WCS checked to place the catalogue centre inside the image. WCS JSON sidecars retain native coordinates and the PNG vertical-flip convention. PNGs are display products, not calibrated science arrays.

AutoStretch reproduces the existing Euclid/masking_review/masking_core.preview AutoSTF calculation: median/MAD, shadow parameter -2.8, target background 0.25, gamma 1.0. It is a Python implementation of the existing PixInsight-style stretch, not a call to the PixInsight application. Synthetic comparisons against the existing function passed exactly. No masking, sky modelling, deblending, geometry fitting or bar-profile measurement was performed.

Visual review of all four contact sheets shows centred galaxy candidates, but also bright-star diffraction spikes, neighbouring/interacting galaxies and some triangular mosaic-edge regions. A high bar-model fraction does not ensure a clean or visually obvious bar. These images still need scientific review and contamination/coverage quality flags before profile measurements; a finite-pixel check alone does not identify finite-valued mosaic padding.

## Measured time on this Windows machine

100/100 PNGs succeeded. Mean total **4.064 seconds/object**, median 3.864, p90 4.809; range 0.428–39.931. Mean service/download 4.044s; FITS/WCS 0.0037s; AutoStretch 0.0036s; PNG writing 0.0091s. Per-object totals include small bookkeeping costs; startup, manifest queries and contact-sheet generation are excluded. The pilot was run sequentially with an initial three-object test retained, then resumed to 100.

At this observed mean, 166,553 previews would take approximately **188.0 hours (7.8 days)** sequentially. This is only a sizing estimate: HTTP caches, service load/throttling, larger galaxies, image coverage and the nonrepresentative sample can change it. AutoStretch alone is inexpensive; remote delivery dominates. This is not an ESA Datalabs timing or an estimate for the full scientific pipeline. No large-scale download was launched.

## Repeat the pilot

Use Python with numpy, Pillow and astropy (see requirements.txt). From this package folder:

```powershell
python build_dr1_manifest.py --output-dir new_query --disc-policy provisional-two-answer --limit 100
python dr1_preview_pilot.py --manifest new_query/DR1_first100_manifest.csv --output new_previews --limit 100 --population-total 166553
```

Use a new output folder when changing the manifest or source mode. Query reuse is available with --reuse; omit it for a fresh catalogue count. The population total passed to the preview command is only for extrapolation: replace it with the newly returned count if it changes. The builder currently limits exported manifests to 100 and counts the entire selection; it does not download the full population. Input files are not changed. FITS responses are held in memory and discarded unless --keep-fits is supplied. Each response and science payload is hashed. PNG/WCS/timing files remain.

For an ESA Datalabs comparison, open DR1_Pilot.ipynb, or use --source-mode datalabs on the preview command with a new output directory. That mode reads bounded image sections from the catalogue's datalabs_source_file instead of downloading cutouts. It has not been verified on the user's ESA account: mount paths, permissions and installed libraries must be checked there. Do not assume this machine's download timing transfers to ESA. The downloaded-cutout mode was verified here on all 100 objects.

The exact benchmark input is benchmark_manifest.csv. The reusable master manifest contains the same 100 IDs and positions but additional provenance fields. Script metadata additions after the run add Astropy version/header recording; the stretch and timing algorithm are unchanged. Existing benchmark sidecars may contain selected WCS cards rather than a complete FITS header.

Primary references: [ESA morphology cookbook](https://euclid.esac.esa.int/dr/dr1/dpdd/merdpd/mermorphologycookbook.html), [ESA final catalogue](https://euclid.esac.esa.int/dr/dr1/dpdd/merdpd/dpcards/mer_finalcatalog.html). Live query endpoint: https://eas.esac.esa.int/tap-server/tap/sync . Availability and counts reflect the recorded query time, not a guarantee of future service state.
