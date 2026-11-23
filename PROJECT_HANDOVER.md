# Project handover

Last updated: 23 November 2026.

## Working across computers

The user works in VS Code on a desktop PC and a laptop. Codex conversations are
separate on the two machines. This file is the shared project context: read it
before work and update it before finishing. Repository-level `AGENTS.md` makes
this an ongoing instruction.

Git transfers tracked files after commit, push and pull. It does not transfer
Python environments, external scientific images or ignored local results.
The handover and instruction files have been created locally; their creation
does not mean they have been committed or pushed.

## Repository maintenance ZIP reconciliation - 23 November 2026

User requested all ZIPs in laptop research `Repository_maintenance` unpacked,
with source in Git and large/generated outputs in Dropbox. Verified root:
`C:/Users/gordo/Dropbox/Public Documents/UCLAN/MSc Research`.
Desktop research equivalent remains `D:/Dropbox/Public Documents/UCLAN/MSc Research`.

- Reconciled four ZIPs in `Repository_maintenance/H_Codex_archives_2026-11-17/Archives`:
  DR1_All_Qualifying_Manifests, DR1_Manifests, DR1_Barred_Galaxy_Pilot and
  ESA_Source_Extraction_Pilot. All 437 members have exact SHA256-verified unpacked
  destinations: 420 identical existing files reused, 17 historical variants
  extracted separately. CRC/path validation passed. The four original ZIPs were
  subsequently deleted at the user's explicit request (details below).
- Current DR1 builders, notebook, requirements and guides stay in
  `Euclid/DR1/barred_galaxy_pilot` and its `full_manifest` subfolder. Full-table
  outputs/evidence were already present in the matching Dropbox location and
  byte-identical to the ZIPs; no large duplicate tables were created.
- Moved all 243 generated pilot files (14,694,822 bytes) to research
  `Euclid/DR1/barred_galaxy_pilot`: gallery, benchmark/review CSVs, original hashes,
  preview_results and query_evidence. Each destination hash matched before source
  removal; source removal and all destination hashes rechecked. All 200 gallery
  links resolve; all 100 individual PNGs retained. Ignore rules and current guides
  now reflect these locations. Git shows source-tree deletions for these moved
  outputs; this is intentional, not lost research data.
- Preserved three historical DR1 guides under source `archive_imports`; three
  older ESA Python files under
  `Euclid/Q1/datalabs_MER_VIS/source_extraction_pilot/archive_imports/ESA_Source_Extraction_Pilot`.
  Active code was not replaced; ESA pilot belongs to Q1, not DR1. Ten historical
  CSV variants (line-ending differences only) and one different checksum manifest
  stay in Dropbox `archive_imports` beside their data. READMEs mark historical code.
- Exact member/source/destination hashes and archive hashes:
  research `Repository_maintenance/2026-11-23_archive_import/import_manifest.json`.
  Maintenance audit JSONs, Word pre-edit backups and Git bundle remain in their
  original maintenance folders. Source helper `tools/import_research_archives.py`
  defaults to read-only; explicit `--research-root`, optional `--apply`.
- Validation: all 437 member hashes, 243 relocation hashes/absent old copies,
  four unchanged ZIP hashes, 200 gallery links, 100 PNGs, ten newline-only CSV
  comparisons and 13 Python syntax parses passed; `git diff --check` passed.
  No science processing, catalogue query, runtime revalidation or package install.
  No commit/push performed; Dropbox sync completion unverified. Commit/push these
  source/docs/deletion changes when authorized, then pull on the other computer.

User subsequently requested deletion of the extracted ZIPs. Rechecked all 437
saved member hashes and all four ZIP hashes, then deleted the four named archives
on 23 November 2026 (271,839,407 bytes). Verified their absence; extracted files,
other maintenance records and Git bundle retained. Deletion audit:
research `Repository_maintenance/2026-11-23_archive_import/deleted_verified_zips.json`.
The one-time ZIP importer now requires the original archives to rerun; the saved
import manifest is the inventory of the unpacked files. Dropbox sync completion
remains unverified.

This supersedes older statements below that the 100-object gallery/results
remain in the repository; the full current storage guide is
`Euclid/Codex Documentation/Git_Storage_Guide.md`.

## Active project: Euclid foreground masking and bar analysis

Code and user instructions: `Euclid/masking_review/README.md`.
Launch: `Euclid/masking_review/Start Euclid Masking.cmd`.
Main implementation: `masking_core.py`, `reviewer.py`, `deprojection.py`,
`app.js`, `index.html` and `style.css` in that folder.

The workflow is: review foreground masks, accept a mask, independently refit
disc/bar geometry using that mask, deproject the image, then inspect bar-axis
intensity profiles. Original science images and adopted measurements are preserved.

### Agreed behavior and implemented features

- MTO processes the rectangular **Fit galaxy** area at native resolution. The
  user explicitly removed the red area-boundary feature. Display zoom and pan
  do not change the processing crop.
- No galaxy/bar protection region: any segmentation label, including the centre,
  can be masked. Foreground objects can project onto the bar and disc.
- Original + galaxy residual detection adds a second MTO pass on a smoothed-model
  residual. Compact detections inside the galaxy require visual review because
  they may be intrinsic structure. Move alone did not separate the two projected
  sources in test object `-599118107493216367`.
- The projected-source preset loads parameters; Run MTO applies them. Consult the
  current README/UI/code for exact values rather than older chat settings.
- PixInsight-style AutoSTF and gamma affect display only. Bar/disc ellipse overlays
  default to Off. Zoom/pan also apply to all five Move comparison images.
- Deprojection defaults to geometry from the latest masked refit matching the
  accepted mask. Masks propagate through resampling; masked science stays missing.
- Bar major/minor profiles show both sides on signed arcsecond coordinates,
  centred at zero. Mask intersections are highlighted and missing intervals are
  not bridged. A standalone graph resembles the earlier Spitzer presentation.
- Products include `deprojected_bar_aligned.fits`, `bar_profiles.csv`,
  `bar_profile.png` and `bar_axis_profiles.png`, with provenance JSON.

### Validation and cautions

Previous development recorded 20 passing Python tests, passing Node UI tests and
native integration validation. These were not rerun during this handover update.
Node tests use mocked DOM/canvas; browser automation did not establish a full
visual browser verification.

For test object `-599118107493216367`, the chosen disc interval was inside the
bar interval. The app warns about this; the physical interval assignments still
need scientific review. Do not treat numerical fit success as scientific approval.

### Laptop setup

- Install scientific packages from `Euclid/masking_review/requirements.txt` into
  a suitable Python environment. The launcher falls back to root `.venv`.
- The desktop's root `mtobjects` checkout is not Git-tracked. Transfer/install it
  and its Windows-compatible compiled libraries separately. `MTOBJECTS_ROOT` and
  `MTOBJECTS_DLL_DIR` are supported; Windows Python cannot load WSL libraries.
- FITS images live outside Git. Supply `-FitsDir` to the PowerShell launcher if
  the laptop uses another location.
- `Euclid/masking_review/saved_reviews/` and `dependencies/` are ignored by Git.
  Transfer accepted masks/results separately if continuing existing work.
- Laptop execution has not yet been verified. Check dependencies, MTO loading,
  image access and a complete mask/refit/deprojection run there.
- The previous desktop URL was `http://127.0.0.1:57545/`; use the URL printed by
  the launcher. A localhost URL refers to the computer on which it is opened.

## Spitzer / Euclid comparison findings

The actual used Spitzer library has 182 galaxies. Crossmatching it with the
current 2,777-object Euclid selection found no matches within 60 arcsec. A public
Q1 VIS science-mosaic footprint query found no coverage of those 182 centres;
a positive control succeeded. This does not establish absence from all Euclid
releases or all Spitzer observations.

Script: `Euclid/Q1/compare_spitzer_q1_overlap.py`.
Report: `Euclid/comparisons/spitzer_q1_20261029/README.md`.

Existing local images permit comparisons for **NGC1255, NGC1436 and NGC1512**:

- Original Euclid VIS: `D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid Sample Data\bars\`
  (`NGC1255.fits`, `NGC1436.fits`, `NGC1512.fits`).
- Extracted observed/previously aligned images:
  `D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Clean_Galaxy_Output\`.
- Spitzer originals:
  `D:\Dropbox\Public Documents\UCLAN\MSc Research\Erwin\s4g_images_36um\`
  (`<name>.phot.1.fits`).
- Current Q1 cutouts:
  `D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_cutouts\`.

The release of the three local Euclid comparison images was not established.
Their existing bar-aligned outputs used Spitzer geometry, so they cannot
independently validate agreement in ellipticity or PA. Fit the observed images
independently in each band before comparing geometry; account for different PSFs,
apertures and wavelengths when comparing profiles.

## Next steps

1. Commit/push the handover and repository instructions when authorized, then
   pull them on the laptop along with the current code.
2. Verify the laptop setup and a complete reviewer workflow; record results here.
3. Scientifically review disc/bar intervals and masks before adopting measurements.
4. If proceeding with the three local Spitzer/Euclid pairs, independently fit the
   observed images in each band and compare using matched resolution/apertures.

For the latest source locations and validation, see the folder reorganisation
entry dated 17 November 2026 below.

## Astronomy source catalogue and conservative cleanup 13 November 2026

- Completed a static catalogue of the nine requested astronomy directories and
  additional astronomy source with creation/modification timestamps since 1 June
  2026. The DOCX indexes 807 source/companion files, including 621 .py files and
  754 distinct content hashes. Many August timestamps appear to reflect migration;
  actual post-June authorship is not established. Git-history access was denied.
- Catalogue: `C:\Users\gordo\Documents\Github\PythonScripts\Euclid\Codex Documentation\Astronomy_Scripts_Catalogue.docx`.
  Includes workflow relationships, per-file static evidence, CLI declarations,
  dependencies, launch forms, path checks, uncertainties and cleanup register.
- User authorised a dated archive. Moved 10 confirmed one-off text-patch helpers
  from `Foreground Masking` into `_archive/2026-11-13_catalogue_cleanup/`, preserving
  the original relative structure. `archive_manifest.json` records full hashes,
  original/destination paths and verified target markers; README explains restore.
  No science data, runtime implementations, reviews or provenance backups moved.
- All 807 inspected source hashes were verified unchanged at active/archive paths.
  The S4G manifest has 182 image paths and all exist. The current local Euclid and
  reviewed-adoption manifests have 2777 FITS paths each and all checked paths exist.
  These are existence checks, not scientific or pixel-level validation.
- On this audit host the D:\Dropbox research root exists; the configured Laptop
  C:\Users\gordo\Dropbox research root was not found. Earlier ENVIRONMENT_CHECK.md
  describes another host and its test results were not rerun.
- Found `SRA/Density Shoulder Quantification v1.1.py` dynamically imports the absent
  `SRA - 650stars.py`. `SRA - D650_simulation.py` and D650_stars.npy exist, but no
  repair/substitution was made. Empty placeholders and notebook JSON saved as .py
  are identified in the catalogue. Native .so files have Windows MZ headers;
  native loading was not exercised in this task.
- No scientific processing, package installation, GUI acceptance testing or
  remote catalogue query was performed. No commit or push was requested/performed.

### Catalogue revision requested by user

The 807-file reference was too granular. The replacement is a 17-page catalogue
of 40 top-level programs/workflows, with supporting routines, workers, QA and
maintenance scripts omitted as entries. It uses paths relative to PythonScripts
and focuses on useful CSV/PDF/PNG/FITS/workbook outputs. Revised deliverable:
`C:/Users/gordo/Documents/Github/PythonScripts/Euclid/Codex Documentation/Astronomy_Programs_Catalogue.docx`.
All 40 entry-point source paths and hashes were rechecked. The DOCX was rendered
through Word and all 17 pages checked; no new source changes or archive moves.
## Documentation relocation 16 November 2026

Completed after user confirmed ALL finished documents, including unrelated
reports, and closed the open catalogue. Eight finished files now reside in
`Euclid/Codex Documentation`: both astronomy catalogues, the RPA draft and notes,
both Peru weather reports, and both Peru map PNGs. Source/destination SHA256
checks matched for every move. No finished files remain in the Codex outputs
folders; temporary Office lock files and intermediate work/render data were
excluded. Document contents were not regenerated.

Five builders now save future DOCX files into the same destination:
`work/build_catalogue.py`, `work/build_programs.py`, the Peru weather builder,
RPA `edit_form.py`, and Euclid image-products `build.py`. Their original Codex
work folders and source data remain in place. The catalogue verification script
and handover-generator output reference were also repointed. All six relevant
Python scripts passed syntax parsing. No builder was run to overwrite documents.

## ESA Datalabs MER VIS audit 16 November 2026

Reviewed user-supplied ESA_MER_VIS_review_20261116_111952.zip. All five Python
helpers and both top-level CSV manifests match Euclid/Q1/datalabs_MER_VIS exactly
by SHA256. ESA notebooks differ and contain executed output. Actual filesystem
WORK is /media/user/Euclid_MER_VIS; browser label is /my_workspace/Euclid_MER_VIS.
Exported processing CSV records all 2777 native cutouts existing_verified
(62 partial), checked 16 October 2026. Geometry output has 2208 provisional_fit,
569 fit_failed; 557 successful fits have no quality flags. Optional aligned
run is commented out; no aligned success recorded. Untitled.ipynb is the
packaging launcher, with saved evidence of 30 ZIP batches, 23.41 GiB native FITS.
An empty download_batches today is consistent with cleanup, not proof of deletion.
Guide: C:\Users\gordo\Documents\Codex\2026-11-16\le\outputs\ESA_MER_VIS_Workflow_Guide.md.
No science processing, live ESA inspection or FITS validation performed; FITS
and PNG files were omitted from the review ZIP. Old Datalabs README 'not run'
statements predate these exported runs. No source code changed or commit/push.

## Documentation destination preference 16 November 2026

User explicitly requested all documentation from now on in
C:\Users\gordo\Documents\Github\PythonScripts\Euclid\Codex Documentation.
Save future finished documentation there unless the user specifies otherwise.
ESA_MER_VIS_Workflow_Guide.docx and its Markdown source are now saved there;
the five-page DOCX was rendered through Word and all five page images inspected.
The packaged renderer could not find LibreOffice; Word PDF export was used for QA.
Destination SHA256 checks match the generated files. No code or science data changed.

## ESA source extraction pilot 16 November 2026

No SEP/MTObjects references found in exported ESA Python or notebook source/text
outputs; existing ESA geometry uses Photutils and SciPy connected components.
This does not rule out activity outside the supplied export. Prepared a four-file
notebook pilot in Euclid/Q1/datalabs_MER_VIS/source_extraction_pilot. Upload those
files directly into ESA Euclid_MER_VIS. It installs a workspace private environment
reusing core scientific packages, clones/builds upstream Linux MTObjects, and runs
SEP plus MTO on three finite complete native-sampling crops bounded to 1024 pixels.
Source FITS unchanged; no adopted masks or calibrated photometry. Separate per-run
maps/catalogues/plots/logs, install versions/commit and status CSV are recorded.
Guide: Euclid/Codex Documentation/ESA_Source_Extraction_Pilot_Guide.md.
Transfer ZIP: C:/Users/gordo/Documents/Codex/2026-11-16/le/outputs/ESA_Source_Extraction_Pilot.zip.
All Python and notebook code syntax parsed. Synthetic integration attempt blocked
at Astropy import by Windows Application Control cparser DLL restriction, including
outside sandbox. No image smoke test, ESA install, gcc build or remote trial has
passed yet. User must run notebook and return result ZIP; native modern-Python
compatibility remains unverified. No commit or push.

### ESA pilot GSL correction 16 November 2026

User's first ESA setup confirms SEP 1.4.1 installed and scientific imports passed;
MTObjects commit b38a07a91a39097fdd8b7c40b530757a669533c8 cloned but build failed
at missing gsl/gsl_cdf.h. Installer corrected to install workspace conda-forge GSL,
add include/link/RPATH flags and record native dependencies; syntax checked only.
Replacement outputs/install_pilot.py and refreshed pilot ZIP are available.
User should upload replacement, reload install_pilot, rerun setup, then image trial.
No native MTO import or image trial success yet. Guide appended in Codex Documentation.

### First ESA source extraction image trial reviewed 16 November 2026

User returned results_20261116T115038_525381Z.zip. MTO succeeded for all three
images (471,405,190 objects); SEP succeeded for two (488,195). Middle SEP failed
pilot RMS guard; actual input reproduces 852 nonpositive spatial RMS pixels,
while global RMS is positive. Revised run_pilot.py explicitly logs and uses global
RMS fallback for affected image, saving original/effective noise maps. Local
noise/extraction validation passed all three actual pilot inputs, not full WCS
runner; local labels/counts need not reproduce ESA stack. Full details appended
to Codex Documentation/ESA_Source_Extraction_Pilot_Guide.md. User to upload new
run_pilot.py and rerun image/display/archive cells. No reinstall needed. MTO
native compilation/import and image execution in ESA are now confirmed; no adopted
masks/scientific validation. Visual boundaries alone do not rank detectors.

## Research proposal processing and storage plan 16 November 2026

Read RPA_Gordon_Bowser_v13_2026-11-16.docx from the Dropbox research proposal
folder and mapped all six objectives/RQ1–RQ3 to a proposed bounded ESA workflow.
Saved Euclid/Codex Documentation/Euclid_Research_100GB_Plan.docx and .md.
Seven-page DOCX rendered through Word; page images reviewed, destination hash
verified. Proposed routine category caps sum to 80 decimal GB with 20 GB reserve;
exact masks/profiles/provenance retained, one-galaxy streaming with bounded MTO
scratch, fixed reference images, parent-by-parent recovery trials, and small
verified result exports. Existing Q1 23.41 GiB cache is ~25.14 GB and needs an
inventory/retention transition, not another complete cutout/export batch.
Current scripts need in-memory/accepted-mask adapters, profile/SRA integration,
quota admission and provenance-aware checkpointing. These are proposals only;
no controller implementation, deletion, science processing or proposal edits.
Checked official DR1 Datalabs docs: 100 GB personal storage, 32 GB RAM, 2 cores;
DR1 paths/schema/product availability in user's instance still unverified.
The proposal's ESA-untested statement predates the completed limited Q1 trials.
No commit/push. Next practical task is read-only account inventory and a ten-object
streaming validation, followed by the proposed 50–100-object scientific pilot.

## DR1 provisional barred-galaxy pilot — 2026-11-16
Completed Euclid/DR1/barred_galaxy_pilot: reusable stdlib TAP builder, FITS/AutoSTF PNG runner,
notebook, exact query evidence, 100-object manifest, review CSV, gallery and 100 PNGs.
Guide: Euclid/Codex Documentation/DR1_Barred_Galaxy_Pilot_Guide.md.
User explicitly approved provisional featured/(featured+smooth) because DR1_R2
artifact/star/zoom concentration has zero populated rows in Wide and Deep.
Other three fractions remain >=0.8 (not edge-on, spiral, strong+weak bar).
Q1 training-warning equivalent unavailable; no substitute imposed. Strict builder
is the default; provisional requires --disc-policy provisional-two-answer.
Live counts: Wide 165251, Deep 1302, overlap IDs 0, total166553 qualifying IDs,
before population image coverage or physical-source deduplication. Export bounded
at100; globally first signed IDs, all Wide here, not a representative sample.
100/100 public VIS science cutouts succeeded, WCS centre inside each, all pixels
finite. Four contact sheets visually reviewed: star spikes, neighbours and finite
mosaic-edge padding remain; no masking, geometry, profile or source extraction.
Existing masking_core.preview AutoSTF equality tested synthetically. Mean4.0637s
per object, download4.0439s, stretch0.00360s, PNG0.00906s. Naive sequential full
preview estimate188.0h; Windows HTTP/cache timing, not ESA or full-pipeline timing.
Datalabs mounted-image section mode implemented but unverified on user's account.
Dependencies installed only in workspace task-local directory, not repo env.
Benchmark manifest retained exactly; later runner metadata adds Astropy version
and full header for future runs without changing stretch/timing algorithm.
Review gallery before scaling; validate ESA mount paths and coverage/contamination
quality policy. No population-scale images downloaded, no commit or push.

## Full DR1 barred-candidate manifests — 2026-11-16
Completed Euclid/DR1/barred_galaxy_pilot/full_manifest: detail and compact summary CSVs,
166553 distinct qualifying IDs (Wide165251, Deep1302, overlap0), unchanged approved
provisional four-fraction >=0.8 selection. All have matching ICRS positions and
catalogue corners/planned cutout sizes. No FITS or images downloaded this task.
Guide: Euclid/Codex Documentation/DR1_Full_Manifest_Guide.md.
Photometric records/positive median redshifts158076 (Wide only), missing8477;
153253 records have PHZ flags0. Deep corresponding R2 PHZ/SPE joins returned0,
confirmed by server counts. All missing/flagged objects retained, not excluded.
Rank1 SPE candidates113663 retained with errors/reliability/quality flags; none
had reliability>=0.9. Not automatically accepted over photometric medians.
Planck18 (H0=67.66, Om0=.30966, full Astropy realization) yields comoving,
angular-diameter, luminosity distances, lookback time and proper kpc/arcsec.
PHZ70/90/95 PDF intervals numeric;70% comoving/luminosity/time endpoint ranges
also retained. Distances are estimates and raw quality/classification preserved.
TAP_SCHEMA PHZ classification descriptions reverse star/galaxy labels versus
published documentation: code2 used for galaxy review status only, no ID cut.
Large sync CSV joins silently returned partial data despite HTTP success.
Independent COUNT controls detected it (e.g. photo24577 vs158076). Queued async
jobs were aborted; final incomplete exports rebuilt in bounded direct-ID/range
batches. All final metadata row counts and selected-ID membership reconciled;
never infer coverage from the discarded preliminary whole-join CSV responses.
Maintained builder build_dr1_full_manifest.py plus direct_batches.py helper and
companion build_dr1_manifest.py saved together, with requirements and full ADQL,
raw metadata/batch evidence, hashes and validation.json. Rebuild takes catalogue
metadata only. Existing batches resume; --refresh/new folder requests new data.
Validated all IDs exact signed integers, fractions, 100 pilot coordinates and
distance duality/physical-scale conversions. Original pilot benchmark preserved;
new first100 detail/summary CSVs include redshift/distance enrichment.
SciPy installed only in workspace task-local dependencies, not repo environment.
Import CSV object_id as TEXT in Excel to avoid precision loss. No physical-source
sky deduplication or population image coverage/contamination checks performed.
No commit or push.

## Historical output storage preference (superseded 17 November) — 2026-11-16
User clarified: leave all existing uncompressed results where they are. No folders
were relocated or junctions created. Extracted DR1 results remain below Euclid.
Copied four ZIP archives to H:/Codex/Archives and verified their SHA256 hashes.
All four SSD ZIP copies removed after SHA256 verification (271839407 bytes freed). The final DR1_Manifests.zip lock was released after the user closed its viewer.
Archive names: DR1_All_Qualifying_Manifests.zip, DR1_Manifests.zip,
DR1_Barred_Galaxy_Pilot.zip, ESA_Source_Extraction_Pilot.zip.
The H:/Codex default was superseded on 17 November by the Dropbox research
archive. Unrelated existing H: archives remain; its policy note now records
the new destination. See current status below.




## Folder organisation and research storage - 17 November 2026

Current guide: Euclid/Codex Documentation/Repository_Folder_Guide.md.
Root README links DR1, Q1, shared tools and the output policy. machine_paths.py
is retained unchanged at root as explicitly requested. Project uv/configuration
files and AGENTS remain. No commit or push performed.

### Current output policy

Significant new data, downloads, manifests, archives and working artifacts belong
under D:/Dropbox/Public Documents/UCLAN/MSc Research, using project subfolders
mirroring source where useful. Do not use H:/Codex for new output. Source and
small companion files stay in PythonScripts. Report unavailable research storage
rather than silently substituting another location. Saved global preference,
root README, active guides and current script defaults updated.

Five current NGC1365 files moved from H: to research Euclid/DR1/galaxy_cutouts:
original FITS, basic PNG, AutoSTF PNG and two validation artifacts. SHA256 checked
before deleting old copies. Audit records/pre-edit Word copies moved to research
Repository_maintenance/2026-11-17. Unrelated existing outputs/archives unchanged.
Research foreground_mask_examples renamed Foreground_mask_examples (capital F);
all24 files hash-verified unchanged, documentation builder updated.

### Release-specific source

- Euclid/DR1/galaxy_cutouts/Galaxy_image_remote.py, adjacent requirements.txt
  and README: commented PC/VS Code example. ESA makes cutout remotely; bounded
  ZIP/plain-FITS download; original FITS plus basic and AutoSTF PNGs.
- Euclid/DR1/barred_galaxy_pilot: complete100-object gallery, preview_results,
  query_evidence and full_manifest code/data, moved from dr1_barred_pilot.
- Euclid/Q1: shortlist, cutout-link and Spitzer-overlap scripts; q1_barred_spirals,
  q1_mer_vis_cutouts and datalabs_MER_VIS/source_extraction_pilot folders.
- Shared/local analysis stays under Euclid. Existing scientific Dropbox paths
  and separate ESA /media/user/Euclid_MER_VIS workspace were not changed.

Initial nine moves hash-verified463 files;425 science/evidence files rechecked
unchanged. Seven identical root pilot files and three empty root folders removed.
Active source, Markdown, requirements instructions and seven affected Word guides
updated. Archived code/saved-review provenance retain historical paths; printed
source hashes in old catalogues describe the original audit, not today's edits.

### Other root files and linked results

Twelve more source/result files moved with matching hashes before path edits:
- Diagnostics/PingTest/PingTest.ps1 and README; new logs in research Diagnostics/PingTest.
- laptop_setup/launchers: existing laptop launchers, root calculation adjusted;
  original data assumptions preserved. Desktop dependency snapshot moved to
  laptop_setup/requirements-pc1-freeze.txt.
- tools/document_rendering: Word renderer, matching requirements and README;
  root/installed-renderer paths adjusted; new render output goes into research
  Repository_maintenance/Document_previews.
- Foreground Masking/Optimisation/launchers: two WSL wrappers. Windows supervisor
  reference updated and path spaces quoted. No WSL/science jobs started.
- SRA/example_outputs: old smoothing PNG. Exact savefig/name/200dpi match to
  SRA/adaptive_gaussian_smoothing_example.py. Future output in research
  SRA/example_outputs rather than terminal working directory.
- Foreground Masking/results/toy_comparison_2026-08-20: two CSVs. Schema matches
  documentation/compute_toy_batch_comparison.py, dates support association;
  original command/configuration not recovered. Results not regenerated.
- Erwin_s4g_image_downloader/geometry_output/previews: NGC0986 PNG figure labels
  match plot_s4g_isophote_axes.py; exact PNG-render command unverified.
- Erwin_barprofiles_paper_GB_working_copy/data/reference_imports/parent_disc_sample_export.txt:
  preserves oddly named root table export. Content identifies Erwin parent-disc
  sample, creator unknown. Canonical s4gbars_table.dat was not replaced.

### Remote galaxy status

NGC1365 correct ICRS(53.40190833,-36.14065833)deg, DR1_R2 MER VIS SCIENCE
tile102034383. User successfully downloaded radius6arcmin:7210x7203,
207743040byte FITS(198.1MiB),100% finite. Separate169920byte10arcsec validation
FITS is not the full cutout. AutoSTF shadows-2.8,target0.25,gamma1 affects display
only. Non-string EXTNAME is an ESA header warning; FITS pixels preserved.
Severe polygonal seams are present in original FITS, basic PNG and independent
linear preview; not caused by AutoSTF. Exact upstream cause unverified; do not
adopt affected galaxy for quantitative bar photometry. Rechecked yesterday's
100 much smaller30-81.66arcsec previews: contamination/edge padding exists,
no comparable gross internal seams at contact-sheet scale, not proof all clean.

PC Astropy import initially blocked by Smart App Control(_np_utils.pyd).
Same-version official reinstall did not fix policy; subsequent user run worked.
Agent changed no Windows security settings; user's change not inspected.
ESA Euclid-dev exposes euclid_idr1; conda activate euclid-tools worked.

### Cleanup and validation

Deleted obsolete LAPTOP_MER_MTO_SETUP.md and LAPTOP_SETUP_REPORT.md and stale
Crashpad debug.log as requested. PROJECT_HANDOVER.md retained because user's
refreshed AGENTS instructions explicitly require continuity. Accessible root and
Euclid Python caches removed; root .pytest_cache access denied.
User explicitly approved deleting the whole tmp folder and contents on
17 November 2026 after reviewing the mixed-content warning. Deleted79 files,
22849292bytes; verified root tmp is absent. Research audit tmp_deletion.json
records approval/counts; tmp_review.csv retains the pre-deletion inventory.

Initial checks passed44 Python AST parses, eight CLI --help smoke checks,
key imports,200 gallery links and all new guide links. Seven Word docs rendered,
326 pages before/after; all page overviews and selected full-size path edits
visually checked. Later checks passed five PowerShell syntax checks, corrected repository-root
resolution, remote-module import and26 main-guide links. Smoothing example
ran without GUI and saved to research SRA/example_outputs. Final Word catalogue
remains281 pages; launcher/wrapper pages visually checked after path updates.
Packaged final renderer hit a Dropbox profile lock; Word PDF export/Poppler
verification succeeded. No active program references H:/Codex; machine_paths.py
is unchanged according to Git.
Temporary rendering dependencies/previews are deleted after use. No new science
processing or image download performed during this reorganisation.
## Git storage cleanup and push repair - 17 November 2026

GitHub rejected the two unpublished commits because the DR1 detail CSV blob
was 247.47 MiB, above its 100 MiB limit. Fetch showed no incoming changes.
User explicitly authorized moving large data, updating documentation, rebuilding
the unpublished commits and pushing to gbowser/PythonScripts main.

Moved 378 files (1,124,266,765 bytes), preserving relative paths beneath
D:/Dropbox/Public Documents/UCLAN/MSc Research. Includes all generated full DR1
manifest outputs/query evidence, masking validation_output, the two >20 MB
adoption JSONs, Tesla inspection dump and the course ZIP. Every destination
SHA256 matched before removal of its source copy. No data regenerated.
Audit: research Repository_maintenance/2026-11-17_git_storage/{before,after,moves}.json.
Verified Git bundle unpublished-before-cleanup.bundle in the same folder backs
up the original two commits, requiring the existing f346977 base.

Current locations, exclusions, GitHub guidance and older Word-report caveats:
Euclid/Codex Documentation/Git_Storage_Guide.md. Both full-manifest Markdown
guides, folder guide, DR1/root README and masking docs updated. Validation
scripts now use machine_paths research storage and reject unavailable storage;
adoption writer reads archived JSON. Installed dependencies/environments stay
locally; 13398 node_modules files removed from Git tracking and ignored.
Audit covered files >20,000,000 bytes except .git; .pytest_cache access denied
and five obsolete long-path render-cache entries could not be statted.
Dropbox sync completion and fresh-machine private artifact runtime unavailable
for verification. Published history is retained; older blobs remain there.

The two unpublished commits were consolidated into 6efd226, preserving all
source changes except the documented cleanup and path updates. Normal push
to gbowser/PythonScripts main succeeded (f346977 -> 6efd226); no force push.
Every new outgoing blob was below20MB (largest1,535,388bytes).
Validation completed: all 378 moved copies hash-verified, both full DR1 tables
have 166553 distinct and matching IDs, six changed Python files parse, and the
validation helper resolves the expected archive path. No science jobs rerun.
The staged tree has no blobs above20,000,000bytes and no tracked node_modules.
User subsequently authorized old ZIP deletion and confirmed Gaia coursework
data obsolete. Deleted four old ZIPs (26,572,671bytes) and five identified Gaia
course files (27,316,714bytes); hash/path records in deleted_old_zips.json and
deleted_gaia_data.json beside the move audit. Course ZIP's archived copy was
intentionally removed after its initial verified move. Kept live Tesla input
and unpacking-exercise ZIPs, source/notebooks and current research Gaia rankings.
Dissertation/DATA_README.md and Gaia/README.md explain unavailable old inputs.
