# DR1 full barred-galaxy manifests

Compiled 16 November 2026 from ESA's public TAP service, queried from the Windows PC. **No FITS files or cutout images were downloaded during this export.** Catalogue CSV/VOTable metadata only. The previous 100-image benchmark remains separate.

## Open these files

All generated files below, including the complete `query_evidence` tree, now
live in `D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\DR1\barred_galaxy_pilot\full_manifest`.
Builders, requirements and this guide remain in Git. On the laptop use its
configured Dropbox research root. See [Git storage](../../../Codex%20Documentation/Git_Storage_Guide.md).

- DR1_all_qualifying_summary.csv: compact, one row per qualifying catalogue ID, including position, requested extraction size, four morphology fractions, redshift source/quality, uncertainty and distance/physical scale.
- DR1_all_qualifying_detail.csv: same IDs with raw morphology concentrations, corners, size measurements, photometric intervals/modes, spectroscopic candidates and all retrieved flags.
- DR1_population_summary.csv: three rows (Wide, Deep, combined) giving counts and metadata/redshift coverage.
- DR1_first100_detail_with_redshifts.csv and DR1_first100_summary_with_redshifts.csv: the previous pilot IDs enriched with these fields. Historical benchmark manifests are preserved.
- DR1_manifest_summary.json, validation.json and query_evidence: assumptions, validation and exact executed queries/raw returned metadata.

Import **object_id as text** in Excel. These signed 64-bit IDs exceed Excel's exact numeric precision. CSV quoting does not prevent Excel from converting them. Use Data → From Text/CSV and set object_id to Text before loading. Blank numeric values mean unavailable, not zero. The CSVs are scientific data tables, not live spreadsheet formulas.

## Selection and completeness

**166,553 distinct qualifying catalogue IDs: Wide 165,251, Deep 1,302.** Survey release DR1_R2. No IDs overlap between these two selected survey lists. Different IDs can still describe the same physical source; no sky-position deduplication or coverage/contamination rejection has been applied.

The user-approved provisional policy requires each fraction >=0.8:

1. featured/(featured+smooth);
2. not-edge-on/(not-edge-on+edge-on);
3. spiral-yes/(spiral-yes+spiral-no);
4. (strong-bar+weak-bar)/(strong-bar+weak-bar+no-bar).

Each question's Dirichlet concentrations are normalized separately. Positive, finite denominator checks exclude missing/invalid models. The missing artifact/star/zoom answer makes the first fraction provisional. The Q1 training-warning exclusion has no available equivalent and is not imposed. No new redshift/quality cut alters this qualifying population.

Large synchronous CSV joins returned incomplete responses despite successful HTTP status. Asynchronous jobs remained queued and were abandoned in favour of bounded synchronous exports. The final metadata exports are **reconciled against independent server-side COUNT queries**, with selected-ID membership verified. Incomplete tables were rebuilt using bounded direct-ID batches (positions/photo-z), or selected-ID-range joins (corners). Selected-ID exports reconcile against both row and distinct-ID counts. Do not interpret the discarded preliminary responses as coverage estimates. Batch queries and hashes are authoritative for assembled exports; reference_join.sql files record the earlier full-join formulations used to define the same metadata population.

## Coordinates and extraction size

ICRS RA/Dec in degrees; tile_index identifies the parent catalogue tile. Cutout corners are angular coordinates. Requested square width uses the corner extent about the centre, with 20% padding, minimum30 and maximum300 arcsec; width_capped and size_status expose limits/missing corners. This is a planning/display width, not a measured galaxy diameter or bar length. semimajor_axis_pix is the native catalogue pixel quantity; it is not an angular radius. Full-population image/WCS/coverage checks were not performed because images were not requested.

## Redshift and distance policy

**Photometric median is the baseline redshift for calculated distances.** A finite positive phz_median within the documented PDF range0–6 is used. Raw photometric flags and classification are retained. Flagged measurements still receive explicitly labelled estimates; they are not silently removed. Non-galaxy/ambiguous classification values trigger a review label. phz_flags=0 alone is not proof of an accurate distance.

Spectroscopic rank1 entries are retained as **candidates**, including spe_z, spe_z_err, spe_z_rel, spe_z_prob and processing/classification/galaxy warning/error flags. They do not automatically override photometric redshifts. No returned rank1 candidate had spe_z_rel>=0.9 in the inspected export; the reliability calibration/acceptance policy still requires scientific review. No invented SPE quality threshold has been used to declare a spectrum accepted. An object with only an unvalidated spectroscopic candidate has blank baseline distance fields.

TAP_SCHEMA's PHZ_CLASSIFICATION description reverses star/galaxy labels compared with published Euclid catalogue documentation and DR1 research examples. Raw codes are preserved: the working review convention uses code2 for a galaxy, with all other values flagged for review, without excluding their IDs. Sources: https://euclid.esac.esa.int/dr/q1/dpdd/phzdpd/dpcards/phz_phzpfoutputcatalog.html and the DR1 PHZ paper https://arxiv.org/abs/2611.16444 . This documentation discrepancy remains recorded, not silently rewritten in raw evidence.

Photometric uncertainty intervals are split into numeric redshift_70_lower/upper, redshift_90_lower/upper and redshift_95_lower/upper. These are the catalogue's smallest PDF intervals, not symmetric Gaussian errors and not necessarily centred on the median. Raw interval strings remain in the detail table. Missing/malformed intervals are flagged and left blank. Alternative PDF modes and their areas are retained; the full600-bin PDF was not downloaded.

Distances use **Astropy Planck18**, H0=67.66km/s/Mpc, Om0=0.30966 with its full built-in neutrino/radiation parameters. They are derived model estimates, not direct measured distances. See https://docs.astropy.org/en/stable/api/astropy.cosmology.realizations.Planck18.html .

- comoving_distance_mpc: present-day line-of-sight comoving distance.
- angular_diameter_distance_mpc: converts angular dimensions into proper physical sizes at emission.
- luminosity_distance_mpc: distance for the flux/luminosity relation.
- lookback_time_gyr: time since light emission, not simply distance divided byc.
- kpc_per_arcsec: proper physical scale. A measured 5arcsec bar has length5×kpc_per_arcsec kpc.

The detail table maps the70% redshift interval endpoints to comoving/luminosity distance and lookback-time intervals. Cosmological-parameter and peculiar-velocity uncertainties are not included. Distances for nearby galaxies can be especially sensitive to peculiar motions. No bar length or galaxy physical radius has been measured.

## Actual coverage

Combined: position matches 166,553; photometric records 158,076; valid positive photometric redshifts 158,076; photo flags zero 153,253; rank1 spectrum records 113,663; usable requested size 166,553. Inspect DR1_population_summary.csv for survey breakdown. Missing measurements remain blank with match-count/status columns. Redshift coverage is not a new population selection.

## Rebuild without images

Keep the three Python scripts together. From the PythonScripts root, install the matching requirements and write new catalogue outputs into the research archive:

```powershell
uv pip install -r .\Euclid\DR1\barred_galaxy_pilot\full_manifest\requirements.txt
.\.venv\Scripts\python.exe .\Euclid\DR1\barred_galaxy_pilot\full_manifest\build_dr1_full_manifest.py --output-dir "D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\DR1\barred_galaxy_pilot\full_manifest"
```

Existing matching query results and batches are resumed and cached response hashes checked. To request a fresh catalogue snapshot use a new output folder, or --refresh. Default concurrency3, optionally --workers1 or2. The data release and approved provisional policy are explicit constants near the top of the builder. The companion pilot builder's100-object cap does not apply to this full builder. No preview script is invoked.

The included source uses only metadata endpoints. Exact ADQL, response hashes, batch evidence and server controls are retained. These files are saved locally; no commit or push was made.
