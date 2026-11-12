# Project handover

Last updated: 12 November 2026.

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
