# Euclid Research Processing Plan Within 100 GB

Gordon Bowser research programme • 16 November 2026

## Recommended approach

Use ESA Datalabs as a bounded processing workspace: read hosted MER mosaics, process one galaxy at a time, and retain compact scientific results. Keep complete image bundles for a deliberately selected reference set only. Move verified result batches to an independent archive before the local results allowance fills. This makes storage depend primarily on the reference set and current batch, rather than on the total number of DR1 galaxies.

This plan maps to Objectives 1–6 and RQ1–RQ3 in RPA_Gordon_Bowser_v13_2026-11-16.docx. It proposes software changes and operating limits; it does not implement them, change the proposal, or delete existing files.

The scientific priority is to preserve masks, profiles, uncertainties, selection decisions and provenance. Native cutouts can usually be regenerated from the mounted release; manually accepted masks and review decisions cannot safely be reconstructed from memory or a screenshot.

## Starting point and platform constraints

The exported Q1 workflow verified 2,777 native VIS cutouts occupying approximately 23.41 GiB, equivalent to 25.14 decimal GB. It saved 2,208 provisional geometry fits and 569 failures. The first ESA source-extraction trial completed MTObjects for three images and SEP for two. SEP's remaining noise-map failure has a revised fallback tested locally, but the revised ESA trial is not yet confirmed. These are feasibility results, not scientifically validated masking or shoulder measurements.

The v13 proposal says ESA processing has not yet been tested. That statement is now out of date for the limited Q1 cutout, geometry and segmentation stages above. Full masking optimisation, profile extraction, SRA reliability and production processing remain to be demonstrated together.

ESA's DR1 Datalabs documentation states a 100 GB personal workspace, 32 GB RAM and two CPU cores per Euclid instance, with Euclid release volumes mounted for direct analysis [1]. Treat shared release volumes as inputs and your personal workspace as the place where every copied or generated file consumes capacity. Verify actual mounts, quota reporting and instance resources at the start of each campaign. Two instances must not be treated as two independent personal storage allowances.

Use decimal GB throughout the controller: 1 GB = 1,000,000,000 bytes. A 100 GB allocation is approximately 93.13 GiB. Use the smaller confirmed quota if the account reports a different usable limit. Filesystem free space describes the backing filesystem and is not a reliable personal-quota measurement.

DR1-Foundation documentation is published [2], but the Q1 path /data/euclid_q1/Q1_R1 is not a DR1 configuration. Discover DR1 science, noise, flag, segmentation and PSF products from the actual mounted release and archive metadata. Test catalogue columns, quality flags, mass/redshift availability, morphology provenance and joins before admitting DR1 objects. A documentation listing does not establish every needed measurement is populated for your sample.

## Research stages and retained outputs

### Objective 1 Spitzer baseline and initial resolution threshold

Keep the full 182-galaxy Spitzer baseline and its established local images outside the ESA quota. Run the validated local SRA, with adopted Erwin geometry, parameter sensitivity tests, independent visual labels and the human agreement benchmark. Transfer only code, a compact parameter/configuration bundle and benchmark tables to ESA if the same implementation is needed there.

Retain object-level reference labels, predictions, confusion matrices, precision/recall, Cohen's kappa, SRA parameter versions and uncertainty summaries. These are small tables. Artificially degraded images are generated one at a time; preserve the parent image, degradation recipe and random seed rather than every realisation. Choose one computing site for each experiment to avoid duplicate intermediate archives.

Do not attempt to synthesize sharper information than the Spitzer input PSF contains. Degradation tests are valid only where the desired effective resolution can be reached by additional convolution/resampling. Treat Spitzer-to-VIS differences as a provisional wavelength-dependent calibration, to be tested with Euclid parents in Objective 5.

### Objective 2 Catalogue and bar sample validation

Query only relevant columns from the Q1 pipeline and dynamic catalogues. Select a seeded, stratified review subset spanning the full bar-probability range, including weak and nominally unbarred objects. A subset consisting only of high-probability bars cannot estimate missed bars across the candidate parent population.

Load dynamic-catalogue cutouts or mounted MER crops on demand. Retain lightweight review images, human labels, sampling strata/weights, uncertainty and catalogue version. Keep full images only for the fixed validation set. Record pipeline Dirichlet concentrations and their normalized fractions alongside dynamic-model fractions; do not relabel these as physical bar strength.

Produce threshold-dependent purity/completeness estimates with the sampling design and uncertainty stated. Reuse those compact labels for parameter and catalogue comparisons. Repeat the version-aware comparison for DR1 when its required morphology is usable. A review-thumbnail set must have a total size allowance, not unlimited retention by object count.

### Objective 3 Q1 and DR1 sample selection

Perform catalogue filtering and joins close to the archive where possible. Avoid downloading whole DR1 catalogues into the workspace. Request only required rows/columns and write a versioned parent/sample manifest in Parquet, with a human-readable CSV export for manageable summaries.

Include release, product identifiers, exact object ID as a string, coordinates, tile, band, source/HDU locations, catalogue/model versions, probabilities, mass/redshift values and errors, flags, and every selection criterion. Use release plus object ID as a key; do not assume identifiers or definitions are interchangeable between Q1 and DR1. Check tile-edge duplicates before population counting [5].

Use cheap catalogue screening first, then a small image pass to establish bar size, usable geometry and band-specific PSF resolution. If bar length is not already trustworthy, it cannot serve as a final catalogue-only resolution cut. Record provisional selection, measured eligibility and final frozen selection separately. Preserve every rejection reason and failed-processing status.

The output is a small, versioned job list. Group it by release, tile and band. DR1 admission requires successful source-path preflight and schema checks; Q1 can proceed while those are unresolved.

### Objective 4 Masking geometry and profiles

Read one galaxy's science and required noise/flag/segmentation/PSF information from mounted products. Crop enough area for the outer disc and sky estimate, not just the bar. The segmentation pilot's 1024-pixel cap is a feasibility setting and must not silently truncate production measurements.

On the fixed 50–100-galaxy pilot, compare SEP and MTObjects using explicit segmentation criteria and contaminant injection/recovery tests. Fit/tune on a training subset, use a separate validation subset, and freeze parameters before population application. Do not tune on all objects later used to claim independent performance. Persist all accepted manual mask edits, method settings and review decisions.

Masks can share the common MER grid only after checking the VIS/NISP WCS, shape and registration for the selected product versions. Grid sampling is not PSF resolution: NISP on a 0.1 arcsec grid still has its own broader PSF. A common mask may need a conservative union or band-dependent dilation, validated against PSFs and contamination. Per-band bad-pixel, coverage and weight masks remain distinct.

Fit outer-disc geometry on masked observed data, with bar/bulge exclusions and scientifically reviewed intervals. Save centre, bar/disc intervals, PAs, axis ratio, inclination/thickness assumption, bar length, errors and quality flags. Catalogue shape is a cross-check, not automatic replacement for independent disc fitting.

Extract the primary major-axis profile from the sky-plane image and express distance in deprojected coordinates, as the proposal specifies. Carry aperture width, usable/masked coverage, flux units, background, PSF, uncertainty and mask/geometry versions into the profile. Interpolation and exclusion are separate experiment settings; neither should silently fill an unusable bar interval.

For a selected validation subset, create a rotated/deprojected image in memory, compare the alternative profile, save the discrepancy metrics and one preview, then discard the transformed array. Do not save a full aligned FITS for every production galaxy. Correlated MER/resampling noise must be addressed through empirical or documented uncertainty methods rather than independent-pixel assumptions alone.

For each production object retain the exact adopted bit-packed binary mask, geometry/quality records, one-dimensional profile, SRA outputs and small diagnostic preview. Save segmentation labels, fitted-image models and full science/noise cutouts only for the bounded reference or exception sets. A target's own star-forming regions must not automatically become foreground masks.

### Objective 5 Recoverability and shoulder reliability

Use a small retained set of well-resolved Euclid parents across relevant mass, morphology, inclination, contamination and band conditions. For example, budget initially for 30–50 parents; determine the scientific design after the pilot rather than treating this count as adequate statistical power.

Process one parent, one degradation condition and one random seed at a time. Couple redshifting, PSF matching, resampling, dimming and noise consistently, and also run the planned resolution-only/noise-only controls. Include pixel sampling, photometric units, angular scaling, bandpass assumptions and correlated noise in the recorded recipe. Fix parent IDs and seeds so results can be regenerated.

Save compact trial rows: parent ID, band, simulated condition, seed, apparent bar size in PSF units, S/N definition/value, bar-identification label, SRA detection/strength, uncertainties and failure/coverage flags. Keep profiles/plots for representative cells and threshold failures only. Do not retain the entire synthetic-image grid.

As a scale example, 50 parents x 20 conditions x 20 seeds gives 20,000 trials. At an assumed 20 kB per compact trial record/profile, that is 0.4 GB; at 10 MB per saved image it would be 200 GB. The storage saving comes from streaming, not lossy science compression. These are planning assumptions to replace with measured pilot output sizes.

Split reliability training/validation by parent galaxy, not by noise realisation, to prevent near-duplicate parents leaking across sets. Repeat visual bar classification on the designated degraded subset and preserve review labels. Produce band-specific recovery/confusion functions with uncertainty; freeze the resolution/S/N limits and propagate them back into Objective 3.

### Objective 6 Demographics and final research outputs

Run the frozen pipeline over the final quality-selected manifest. Save profiles, adopted masks, measured shoulder properties, uncertainties and quality/selection records. Keep non-detections separate from insufficient resolution, failed geometry, excessive masking and processing errors. A failure must never become a shoulder absence.

Perform the final mass/colour/strong–weak analyses from the small derived catalogue, locally or in ESA. Join masses and Zoobot classifications with their errors/provenance; use Objective 5 recovery information and selection denominators. Report supported bins and uncertainty rather than extrapolating from an unrepresentative calibration set. Catalogue strong/weak labels remain predicted visual classes.

The final products are a versioned sample catalogue, profile/mask shards, benchmark/recovery tables, review decisions, analysis code/configuration and dissertation figures. Extensions such as minor-axis profiles should reuse retained inputs/geometry or be regenerated on demand; they must receive a storage budget before starting.

## Program and data flow

Use one controller notebook for configuration, preflight, start/resume, review and export. Scientific functions live in importable Python modules. Long computations write status to files and return paths/tables; notebooks display selected results rather than embedding thousands of plots or array dumps.

The proposed flow is:

```text
Mounted release products + queried catalogues
    -> versioned selection and tile job manifest
    -> quota and memory admission check
    -> read bounded galaxy arrays
    -> noise and data quality checks
    -> candidate segmentation -> adopted mask
    -> disc and bar geometry -> observed-plane profile
    -> SRA and uncertainty trials -> quality decision
    -> atomic compact result and provenance commit
    -> reference retention or scratch cleanup
    -> small export shard -> off-platform verification
    -> release verified local export cache
```

Proposed modules are release_adapter, selection, image_reader, masking, geometry, profiles, sra_adapter, recovery, population, storage_controller and exporter. They are design components, not files already implemented.

Refactor make_MER_VIS_datalabs_cutouts.make_one to offer an array/header return path. Refactor fit_one and comparison.run to accept in-memory arrays/header plus an adopted mask. The current geometry fitter estimates its own neighbour mask and does not consume the accepted foreground mask. Its fixed-centre, automatic radial selection remains provisional and does not yet implement all Objective 4 requirements. Add sky-plane profile and SRA adapters explicitly; the current comparison script is not the complete research pipeline.

MTObjects presently reads/writes FITS through a subprocess. Retain that integration initially, but give each job a bounded scratch folder containing only its current input/label files. Read results back and remove only that job's disposable intermediates after successful commit. This practical hybrid meets the disk constraint without requiring every third-party API to become memory-only immediately.

Use WCS-aware sections of science products; compressed/scaled FITS can defeat naive memory mapping and load a whole image. Validate actual read behaviour, auxiliary-map alignment, tile-edge handling and open-file/memory peaks on the mounted product. Cache only a bounded number of open HDUs. Do not accumulate cutouts or MTO trees across galaxies.

Keep a transactional job index, such as SQLite with one writer, and chunked Parquet scientific tables. Statuses include pending, running, committed, needs_review, scientific_reject, failed_retryable and failed_final. A completed product is keyed to the input release/product plus configuration/code/mask versions, so a parameter change cannot silently reuse stale results. An interrupted job can be recomputed; a committed row is not overwritten as a failed rerun.

## Storage budget and enforced limits

The following are proposed category caps in decimal GB, not estimates of current occupancy. They total 80 GB, leaving 20 GB outside routine allocation. All other files in the personal workspace count too; inventory them before accepting this budget.

| Workspace category | Cap GB | Retention rule |
| --- | --- | --- |
| Code environments and native dependencies | 8 | One pinned production environment and bounded build caches |
| Selection catalogues indexes and provenance | 4 | Required subsets only with versioned metadata |
| Pilot validation and degradation reference images | 18 | Fixed list admitted by measured bytes |
| Regenerable native image cache | 10 | Evictable and never required for recovery |
| Active scratch including temporary writes | 10 | Current jobs only with worst case reservation |
| Compact results masks and profiles | 15 | Sharded with periodic verified export |
| Export queue and in-progress archives | 5 | At most one small package being assembled |
| Review images logs failures and test products | 10 | Bounded references and rotating disposable diagnostics |
| Total routine allocation | 80 | Stop new work before exceeding this total |
| Unallocated safety reserve | 20 | Not an extra processing category |

The controller must reserve space for the next job's worst-case files, uncompressed temporary archive plus existing originals, atomic replacement and metadata. Add a measured overhead margin, initially 20%, to file-size estimates. Compression savings are a bonus, never a prerequisite for fitting the quota. Record both logical bytes and provider quota usage where available; investigate discrepancies.

Use soft alerts at 65 GB, stop admitting new jobs when the projected total exceeds 80 GB, and reject planned writes reaching 90 GB. These are software admission rules, not a guarantee against unrelated concurrent writes. A strict guarantee needs account-wide accounting or a filesystem quota. Use one campaign writer, periodic provider-quota checks and a clean workspace. If reliable quota information is unavailable, operate below the conservative inventory-derived limit and pause on unexplained growth.

At an illustrative 120 arcsec width and 0.1 arcsec pixels, a square float32 plane is 5.76 MB before headers. Science plus float32 RMS plus uint32 labels plus a byte mask is about 18.72 MB. A second band, residuals and transforms multiply that. At 300 arcsec, one float32 plane is 36 MB; a 600 arcsec plane is 144 MB. Actual bands, dtypes and auxiliary HDUs must be measured. Common-grid NISP can occupy VIS-like pixel counts even though its effective resolution is coarser.

A 1,200 x 1,200 bit-packed adopted mask is approximately 0.18 MB before metadata/compression. Keeping exact masks is therefore much cheaper than keeping all science and label maps, but still scales with area and sample size. Ten thousand such masks alone occupy about 1.8 GB. Budget profiles, covariance/uncertainty summaries and previews separately; variable-size outliers must not be hidden by a mean.

As an initial target, allow roughly 1 MB per object's complete compact result bundle, measured at the 95th percentile and checked for extreme cases. Ten thousand objects would then need about 10 GB. One hundred thousand need about 100 GB cumulatively, so the 100 GB workspace is workable only with rolling verified export. It is not an unlimited permanent archive. If off-platform storage or export is unavailable, pause when the local result allowance is full.

## Export and reproducibility

Produce derived-result shards of approximately 100–500 MB, reducing the shard size if the measured result sizes demand it. Keep only one archive assembly in flight. Export small scientific tables, profiles, adopted masks, configurations and selected diagnostics; avoid regenerating the old 30-ZIP full-cutout download set.

ESA distinguishes small user-derived exports from using Datalabs to download release products [1]. Obtain any needed off-platform native/reference images through the Science Archive or another approved route; do not make the Datalabs workflow a bulk raw-product export route. Check permission before automated external uploads. Manual download of a small result shard is sufficient initially.

Each shard has a manifest of relative filenames, byte counts and SHA256 hashes, plus schema, code/configuration IDs and covered objects. Transfer to a named archive location on the PC/university storage. Verify its archive checksum, extraction/file checksums and row count there, then record a receipt outside ESA and in the campaign index. Preserve a second independent backup for irreplaceable adopted masks and human labels. A ZIP sitting in Downloads is not yet a verified research archive.

Only after verification may the specifically recorded local export copy and already archived result shards be released under an approved retention policy. Never delete accepted masks, parent validation images or unarchived results merely to make a job fit. Jobs should stop safely if verification or transfer fails. Regeneration provenance includes product IDs/HDU, tile/position/size/WCS, checksums where available, software commit, package versions, seeds and mask/geometry decisions. Regeneration also depends on continued release access; retain the fixed reference set and seek a team workspace if long-term source access is uncertain.

## RAM and simulation limits

Disk and RAM need separate controllers. Start with one galaxy worker, not two MTO processes. Leave room for Jupyter, the operating system and native-library allocations. An initial worker memory ceiling of 12 GB is a planning limit to test against the documented 32 GB instance; measure actual peak RSS and native child-process memory before increasing concurrency.

For a large galaxy, first reserve bytes and run a representative measurement. If the full scientifically required aperture exceeds available resources, route it to a separate large-object queue, local/university computing or a team workspace. Do not silently shrink or bin the image to satisfy engineering limits: that changes the recoverability experiment and selection function. Record the routing and maintain consistent scientific processing.

Monte Carlo geometry, masking and noise trials should stream one draw at a time. Retain compact sufficient summaries and designated representative profiles rather than every full covariance-sized image cube. Where a full covariance is scientifically necessary, budget it explicitly or export it within the result shard. Random seeds alone do not preserve manual mask decisions.

## Transition from the current workspace

First produce a read-only inventory of all personal-workspace folders, including other projects, trash/checkpoints, environments, package caches, pilot runs, profiles and any leftover archives. The historic 25.14 GB native Q1 set is not the whole occupancy. The apparently empty download_batches folder does not establish that no ZIP copies exist elsewhere. Do not launch another complete extraction or packaging batch before this inventory.

Define and freeze the 50–100-object Q1 development/reference list, representative larger/partial cases and recoverability parents. Estimate the complete retained multi-band bundle in bytes. Pin existing reference files logically without duplicating them; either move selected files within the same workspace after path migration or use an index while existing consumers still need the old cutouts paths.

Implement streaming adapters and compare their results against the existing cutouts for a small set, including tile edges and masks. Check WCS/centres, native pixels, units, fitted geometry, profiles and status recovery. Refitting with accepted masks can legitimately change the old provisional geometry; retain that provenance rather than claiming identical science.

After a verified reference/archive plan and explicit retention approval, remove only regenerable non-reference cached cutouts and redundant intermediates. No deletion is authorised by this planning document. If the current workspace cannot temporarily accommodate the reference set plus migration scratch, process the transition in smaller steps or request external/team capacity first. Never rely on unverified deletion to make the proposed budget add up.

## Delivery sequence and acceptance checks

1. Inventory and quota dashboard. Establish current/provider usage, category caps, selected references and off-platform archive destination. Demonstrate the projected-write guard on a harmless test allocation.
2. Ten-object streaming validation. Include large images, a tile edge, a bright-star field, weak bars and a geometry failure. Compare retained science inputs and record peak disk/RAM. The SEP invalid-RMS fallback must be explicit and reviewed.
3. Fifty to one hundred object Q1 scientific pilot. Validate masking through independent injection tests, freeze reviewed geometry/profile extraction, integrate the working local SRA, and audit failed/non-detection distinctions.
4. Recovery experiment. Run parent-split trials with streamed synthetic images; test whether saved records regenerate designated cases and fit the recovery/error budget. Freeze resolution and S/N criteria.
5. DR1 admission and production. Validate product paths/schema, photometry/PSFs, duplicate handling and sample prerequisites; process one bounded tile job at a time. Export/checksum a real result shard and resume after an interrupted run before scaling.
6. Population analysis. Use frozen catalogue/profile/mask versions, recovery corrections and uncertainty. Verify denominators, quality selection and catalogue provenance. Request a team workspace only if a scientifically justified reference requirement exceeds the fixed allowance.

Success means peak personal storage stays below 80 GB during demonstrated jobs and export assembly, sources are not copied wholesale, all retained outputs are traceable, restart does not duplicate work, and off-platform verification completes before local result release. It also requires scientific validation; staying within quota alone does not validate SRA, segmentation or the demographic inference.

## Sources and evidence

Research scope: RPA_Gordon_Bowser_v13_2026-11-16.docx supplied by Gordon Bowser. Current implementation evidence: ESA_MER_VIS_review_20261116_111952.zip and results_20261116T115038_525381Z.zip, plus the matching local Q1/datalabs_MER_VIS scripts. Storage budgets and future module names above are proposed engineering allocations, not measured DR1 processing performance.

[1] ESA DR1 Datalabs overview. Personal storage, resources, mounted releases, package availability and export guidance. https://euclid.esac.esa.int/dr/dr1/expsup/Ch17.S1.html

[2] ESA DR1 Foundation Explanatory Supplement. Release scope and product documentation. https://euclid.esac.esa.int/dr/dr1/expsup/

[3] ESA PHZ data products. Check the actual accessible schema, flags and populated fields before selecting by mass/redshift. https://euclid.esac.esa.int/dr/dr1/expsup/Ch10.S2.html

[4] ESA MER release note on inconsistent worst resolution PSF assignment. Do not interpret a homogenisation/worst-band catalogue FWHM as the VIS image PSF without checking its definition. https://euclid.esac.esa.int/dr/dr1/expsup/Ch15.S3.SS4.html

[5] ESA MER release note on tile-boundary duplicate sources. https://euclid.esac.esa.int/dr/dr1/expsup/Ch15.S3.SS7.html

Web documentation checked 16 November 2026. Availability in the user's actual DR1 Datalab was not inspected. No new processing, deletion, upload, catalogue query or production controller implementation was performed for this plan.
