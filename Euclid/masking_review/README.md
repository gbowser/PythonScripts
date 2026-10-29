# Euclid MTO masking reviewer

Double-click **Start Euclid Masking.cmd**, or open the address printed by the
launcher. The default pilot contains five reviewed-supported galaxies and the
close-pair challenge **-599118107493216367**.

## Processing area

MTO processes the rectangular **Fit galaxy** area at native resolution. The page
reports its exact native-pixel bounds. The preset uses the existing galaxy framing
(half-width at least 50 pixels, otherwise 2.6 times the outer measured semimajor
axis), clipped to the science image. This preserves the previous Fit galaxy view.
If the outer profile is unavailable it uses the existing disc geometry for framing;
an outer ellipse is no longer a prerequisite for processing.

There is no red area-boundary ellipse, margin control, radius override or elliptical
background exclusion. Background mean and variance are estimated with sigma clipping
from valid pixels **within the processing crop**. Advanced explicit overrides remain
available. Inspect the estimate if the galaxy or a companion fills much of the crop.

Zoom, pan and **Full cutout** are inspection controls. They do not change the fixed
Fit galaxy processing rectangle. Click **Fit galaxy** to return to the processing
view. Move-factor comparisons all use the same crop.

Segmentation labels are mapped back onto the original native image grid. Outside
the crop there are no detected labels. Saved FITS masks retain the original shape
and WCS; **1 means exclude**, including all unprocessed pixels outside the crop.
The mask overlay shows contaminants/invalid pixels in red and unprocessed areas in
gray. Masked fraction is reported within the Fit galaxy processing area. Refit uses
the saved mask, so unprocessed pixels cannot enter the measurement.

## Review workflow

1. Choose a target and inspect it in the Fit galaxy view.
2. Adjust **Move factor**, or use the five-value comparison. Lower move values
   include more faint outskirts; higher values reduce large-object spread. Other
   MTO parameters remain available under Advanced. Run MTO to apply changes.
   Compare runs 0.1, 0.3, 0.5, 0.7 and 0.9 with all other settings fixed. Progress
   and five mask previews appear above the main image views; the page scrolls to
   the panel when ready. Each preview reports the masked fraction. Choose **Use
   result** to inspect/edit one at full resolution. **Show last comparison**
   reopens the latest available comparison for the current galaxy, including
   after a page refresh. Starting a comparison preserves current mask decisions.
   Zoom In/Out, mouse-wheel zoom, pan, Fit galaxy and Full cutout apply to all
   five comparison images as well as the main views. This changes only the
   displayed region; it does not rerun MTO or alter the processing crop.
3. Click segmentation objects, or their table entries, to toggle Mask / Retain.
   Every label, including the centre label, can be masked; there is no galaxy
   protection region. Masking a label excludes its whole connected segment.
   There is no maximum source size cutoff. Internal target knots/arms
   still require visual review. Object decisions are specific to each segmentation.
4. Optionally pin a reference. Enter notes, tick the visual-review confirmation,
   then **Accept and save mask**. Unsaved navigation prompts prevent accidental loss.
5. Enter bar/disc radial intervals (arcsec) and **Refit using accepted mask**.
   Each interval requires 0 < minimum < maximum. Overlapping or reversed physical
   assignments produce a caution. Existing adopted measurements are not overwritten.

## Foreground sources projected on the galaxy

Choose **Original + galaxy residual** to add a second MTO pass after subtracting
a normalized Gaussian smooth model. Galaxy smoothing sigma is in native pixels.
This pass searches the whole Fit galaxy rectangle, including the bar and nucleus.
Its labels become separately selectable sublabels on the original image, while
original-source wings and companion masks remain available. Initial mask proposals
are inherited from the original segmentation by majority overlap; newly separated
compact residual labels between Minimum object area and Compact residual maximum
area (default 100 native pixels) are also proposed for masking automatically.
This is a reviewable compact-source proposal, not a physical foreground classifier.
Larger residual structures remain available for manual Mask/Retain decisions.
There is no hard-coded spatial exclusion or unmaskable centre label.

For the two marked features in -599118107493216367, isolated diagnostics separated
compact candidates near native (531,559) and (567,550) with galaxy sigma=3,
MTO smoothing FWHM=0, move=0.9, minimum area=5 and dilation=1. Use the residual
mode with Compact residual maximum area=100 and inspect the proposed small-label masks; these settings do not establish physical
foreground membership or guarantee complete source-wing coverage. Residuals can
also detect intrinsic galaxy structure. Alpha stays at the original test's 1e-6.
Detection uses temporary arrays only. Fitting and display use the unchanged science
image; the raw-image background is retained separately from residual-pass statistics.

## Display

PixInsight-style monochrome AutoStretch is the default, with gamma 0.2-3 (initially
1), shadow clipping -2.8 sigma and target background 0.25. Linear and Asinh are also
available. The implementation matches the earlier centre reviewer, rather than
calling the PixInsight application engine. It uses a fixed whole-cutout float preview,
sampled to at most 1536 pixels per side, so zooming does not change its statistics.
Display changes do not modify science pixels or MTO/fitting inputs. The image views,
pinned reference and move-comparison thumbnails share the stretch. New review saves
record display settings and apply them to the mask-review PNG.

**Bar/disc ellipses** defaults to Off, with Bar, Disc and Both options. Green disc
and blue bar ellipses use measured profile shapes within the current interval fields.
After a masked refit its accepted shapes become the overlay pool. These remain
measurement overlays, independent of the rectangular MTO processing crop.

## Saved results and refitting

Files stay in `saved_reviews/`, separately from the source FITS and adopted catalogue:

- `runs/<id>/`: request, source/code hashes, crop coordinates, parameters, background,
  segmentation, input bad pixels and logs.
- `reviews/<id>/`: native-grid `mask.fits`, `review.json`, `mask_review.png`.
- `refits/<id>/`: request, mask reference/hash, logs, `ellipse_profile.csv`,
  `result.json`, `geometry.png`.

Restore last saved review reloads the exact labels, decisions and display settings.
Previous full-cutout/ellipse-boundary runs are preserved, but require a fresh MTO
run and mask review before use with the new processing policy.

Refitting uses native masked Photutils isophotes and the reviewed fixed centre,
without additional automatic source masks. It uses the existing strict numerical
acceptance rules. At least three accepted disc/bar samples are required for numerical
angles; fewer than six disc samples are cautioned. PA is an axial mean, q is the
median axis ratio, and inclination is acos(q), q0=0. Results remain provisional;
fixed centre does not independently validate the nucleus. Adjacent isophotes are
correlated. Automated deprojection is a subsequent stage after geometry review.

## Launch and validation

The launcher reuses a running local server. It uses the managed scientific Python
environment and the existing MTO checkout, with reviewer-local dependencies where
installed; it falls back to the project .venv. Alternative options:

```powershell
.\Start_Euclid_Masking.ps1 -NoBrowser
.\Start_Euclid_Masking.ps1 -FitsDir 'D:\path\to\cutouts'
.\Start_Euclid_Masking.ps1 -AllTargets
.\Start_Euclid_Masking.ps1 -Python 'C:\path\to\python.exe'
python reviewer.py --mtobjects-root '..\..\mtobjects' --no-browser
python -m unittest discover -s . -p 'test_*.py'
node test_ui.cjs
python validate_integration.py
```

Install `requirements.txt` in another scientific environment. Windows MTO requires
Windows-compatible compiled libraries; WSL libraries cannot be loaded by Windows
Python. MTOBJECTS_ROOT and MTOBJECTS_DLL_DIR are honoured. Effective gain=1 is an
explicit MTO statistical input, not a calibrated Euclid detector gain. Other defaults
are alpha=1e-6, move=.5, minimum distance=0, FWHM=1 native pixel, minimum area=5,
dilation=2 and soft bias=0. Evaluate these trial settings before scientific batch use.

The server binds only to 127.0.0.1. Each calculation uses an isolated worker, one
at a time, with a ten-minute timeout. Stop its PID from saved_reviews/server.json
or Ctrl+C for terminal launches. Unit tests include crop-only detector input,
native coordinate mapping, exclusion of unprocessed pixels, unrestricted centre-label masking,
source immutability, AutoStretch and known-ellipse geometry recovery. The Node test
uses a mocked DOM/canvas; it is not a visual browser test. Integration outputs are
labelled automated validation and remain under validation_output, not adopted reviews.
