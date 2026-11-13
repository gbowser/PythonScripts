# Project handover

Last updated: 13 November 2026.

## Working across computers

The user works in VS Code on a desktop PC and a laptop. Codex conversations are
separate on the two machines. This file is the shared project context: read it
before work and update it before finishing. Repository-level `AGENTS.md` makes
this an ongoing instruction.

Git transfers tracked files after commit, push and pull. It does not transfer
Python environments, external scientific images or ignored local results.
The handover and instruction files have been created locally; their creation
does not mean they have been committed or pushed.

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

Script: `Euclid/compare_spitzer_q1_overlap.py`.
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

No new scientific processing or laptop installation was requested in the latest
turn; the current task is establishing ongoing repository handover notes.

## Astronomy source catalogue and conservative cleanup 13 November 2026

- Completed a static catalogue of the nine requested astronomy directories and
  additional astronomy source with creation/modification timestamps since 1 June
  2026. The DOCX indexes 807 source/companion files, including 621 .py files and
  754 distinct content hashes. Many August timestamps appear to reflect migration;
  actual post-June authorship is not established. Git-history access was denied.
- Catalogue: `C:\Users\gordo\Documents\Codex\2026-11-13\referenced-chatgpt-conversation-this-is-an-2\outputs\Astronomy_Scripts_Catalogue.docx`.
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
`C:/Users/gordo/Documents/Codex/2026-11-13/referenced-chatgpt-conversation-this-is-an-2/outputs/Astronomy_Programs_Catalogue.docx`.
All 40 entry-point source paths and hashes were rechecked. The DOCX was rendered
through Word and all 17 pages checked; no new source changes or archive moves.