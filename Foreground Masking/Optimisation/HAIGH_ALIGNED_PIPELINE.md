# Haigh-aligned S4G source-injection pipeline

This version preserves the visually selected 22 clean S4G galaxies and replaces
the legacy Gaussian toy population. Version 2 also follows the empty-field
principle: inserted contaminants and their complete truth footprints are kept
away from observed target-galaxy structure and pre-existing compact objects.
It does not overwrite or reinterpret any earlier result.

## Source population

- Foreground stars use an IRAC 3.6-micron PSF approximation with 1.66 arcsec
  FWHM (2.213 pixels for a 0.75 arcsec/pixel S4G mosaic).
- Background galaxies use PSF-convolved Sersic profiles with the Haigh et al.
  ranges: effective radius 0.5--3.5 arcsec, Sersic index 2--4, and axis ratio
  0.3--1.0.
- Large Fornax cluster galaxies and the legacy artificial star-cluster model are
  excluded from the primary optimisation.
- Source count scales with the eligible quiet area: one source per 5000 quiet
  placement pixels, rounded and clipped to 1--5.
- The default draw is 75% foreground stars and 25% background galaxies. A
  frame with three or more sources is guaranteed at least one background
  galaxy; the remaining classes retain their seeded random draw.
- Sources are generated and inserted in observed sky pixels. Deprojection is a
  display/analysis transform and is not used to distort the injected source.

## Empty-field placement

The placement map is measured independently for every clean galaxy. It removes
smooth target-galaxy light above 1.5 robust background sigma, positive compact
residuals above 3 sigma, and the central target region. A 5-arcsec safety buffer
is then applied. The complete truth footprint, not merely the source centre,
must remain outside those exclusions. This is analogous to placing sources in
deliberately quiet FDS cutouts and prevents target/source blending from being
mistaken for a masking failure.

## Truth

Truth is tied to the local robust noise estimate rather than a fixed percentage
of peak brightness. Galaxy truth contains model pixels at or above 1 sigma.
Star truth uses that threshold intersected with the footprint containing 95% of
the PSF-model flux. Every payload stores the source-only delta, Boolean truth,
integer source labels, complete parameters, hashes, and seeds.

## Training and validation

Three immutable training arrangements are scored together in every Optuna
trial. Two separately seeded validation arrangements are withheld from fitting
and used for fold assessment and winner selection. Cross-validation leaves one
physical galaxy out per fold; repeated seeds for that galaxy remain together.

## Generate the immutable manifest

Run in WSL2:

```bash
python "Foreground Masking/Optimisation/generate_haigh_aligned_multiseed_manifest.py" \
  --clean-list "Foreground Masking/Optimisation/clean_galaxies_revised22.txt" \
  --source-manifest "Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv" \
  --output-dir "/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_haigh_aligned_empty_field_optimisation/paired_injections" \
  --pc Desktop
```

The generator refuses to overwrite an existing immutable manifest. A preflight
audit of version 2 found 6.5--40.4% eligible quiet area per displayed frame and
38 contaminants per seed arrangement, or 190 across all five arrangements.
All requested sources were placed in the preflight test without fallback.

## Review exact sources interactively

Run from PowerShell:

```powershell
wsl.exe -d Ubuntu-24.04 -u root -- /root/venvs/pythonscripts/bin/python "/mnt/c/Users/gordo/Documents/Github/PythonScripts/Foreground Masking/Interactive tools/interactive_haigh_aligned_SEP_MTObjects.py" --mtobjects-root /root/mtobjects-linux-final20
```

Choose Training 1--3 or Validation 1--2. The saved payload loads automatically.
Use Calculate to obtain paired incremental metrics, and Toys IN/OUT to compare
the injected scene with the clean baseline. Manual legacy toys are disabled in
this reviewer. Once the revised optimisation has completed, startup and the
Reload optimum control both select its SEP and MTObjects winner files from this
experiment's output folder; historical winners are not silently substituted.

The reviewer states the combined number of contaminants in the selected frame
and lists every source's parameters. Bright-green outlines and labels S1, S2,
... identify IRAC-PSF stars. Magenta outlines and labels G1, G2, ... identify
PSF-convolved Sersic background galaxies. The same class outlines appear on the
original and Gaussian-residual panels so their appearance in both spaces can be
compared before calculating either mask.

## Run optimisation

No 182-galaxy deployment is started by this command:

```bash
python "Foreground Masking/Optimisation/run_haigh_aligned_clean22_cross_validation.py" \
  --manifest "Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv" \
  --clean-list "Foreground Masking/Optimisation/clean_galaxies_revised22.txt" \
  --injection-manifest "/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_haigh_aligned_empty_field_optimisation/paired_injections/paired_toy_injection_manifest.json" \
  --output-root "/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_haigh_aligned_empty_field_optimisation" \
  --mtobjects-root /root/mtobjects-linux-final20 \
  --workers 8
```

The default budget is 80 trials per fold (8 initial plus 72 adaptive), with
convergence controls beginning after 40 trials and a patience of 20 trials.
