# Laptop MER / MTObjects setup — 29 October 2026

Verified on **XPS16**, Windows x64 (build 26300), Intel Core Ultra 9 185H,
16 cores / 22 logical CPUs, 63.46 GiB RAM. C: has approximately 1.42 TB free.

Repository: `C:\Users\gordo\Documents\GitHub\PythonScripts`.
Origin: `https://github.com/gbowser/PythonScripts.git`, branch `main`.
Initial HEAD `3027b663`; working tree clean, no local commits or untracked work.
Fetched origin/main, then fast-forwarded with `git merge --ff-only origin/main`
(equivalent fast-forward result to the requested pull). Final HEAD:
`a0be79688de7228b898e97a63f8084f81ff04eae`; upstream comparison `0 0`.
No reset, clean, stash, discarded work, push or catalogue/optimisation campaign.
Setup changes remain uncommitted for review.

## Daily use

Run from the repository root in PowerShell:

```powershell
powershell -NoProfile -File .\Start_Laptop_MER.ps1
powershell -NoProfile -File .\Start_Laptop_SEP_MTO.ps1
```

MER opens the 19-object centre-policy campaign on localhost, starting at port
8878. Its separate laptop review folder is `laptop_setup\MER_review`; this is a
fresh review workspace, not a continuation of the completed desktop decisions.
Those decisions remain in `Euclid\review_MER_VIS\saved_reviews_centre_v3` (19
assessments), with the older review preserved separately. The adopted-state
explanation is `Euclid\review_MER_VIS\REVIEW_ADOPTION_MER_VIS.md` and the newer
29 October report; `reports\MER_VIS_current` still contains an older 20 October
summary and is not the newest adoption record. Existing refit indexes, browser
state and desktop server.json were not reused.

Stop MER with **Ctrl+C in its launching terminal**. Close the SEP/MTO window to
stop it. Verification servers and GUI instances have already been closed.
No background server is intentionally left running.

Inspection modes, both tested:

```powershell
powershell -NoProfile -File .\Start_Laptop_MER.ps1 -PrepareOnly
powershell -NoProfile -File .\Start_Laptop_SEP_MTO.ps1 -PrintParameterSources
```

The comparison launcher writes only to `laptop_setup\SEP_MTO_comparisons`.
Both launchers use the explicit project interpreter and Laptop selection, clear
inherited PYTHONPATH, and set the repository working directory. They bypass the
old launcher's Codex-managed interpreter/dependency-folder preference.
Use one worker for installation checks/refits; no optimisation workers launched.

## Python and installation

Validated existing environment; no replacement or environment copy needed:
`.venv\Scripts\python.exe`, CPython 3.13.14 x64, based on this laptop's uv-managed
CPython at `C:\Users\gordo\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none`.
This is independent of Codex's private runtime. uv 0.11.32; Git 2.49.0.windows.1.

Commands executed, in order:

```powershell
uv sync --locked
uv pip install --python .venv\Scripts\python.exe -r Euclid\adaptive_MER_VIS\requirements_MER_VIS.txt -r Euclid\review_MER_VIS\requirements_MER_VIS_review.txt
uv pip check --python .venv\Scripts\python.exe
uv pip freeze --python .venv\Scripts\python.exe > laptop_setup\requirements-validated.txt
```

The tracked lock is internally consistent but locks Astropy 8.0.1 and Photutils
3.0.0, while the component requirements require 8.0.2 and 3.1.1 and add ReportLab
and pypdf. The component install reconciled this without editing pyproject/lock.
**Do not run an exact sync alone afterwards**: it can downgrade/remove component
requirements. Repeat both installation commands above, or reproduce the final
package set with:

```powershell
uv pip install --python .venv\Scripts\python.exe -r laptop_setup\requirements-validated.txt
uv pip check --python .venv\Scripts\python.exe
```

All imports verified: numpy 2.5.1, scipy 1.18.0, astropy 8.0.2, photutils 3.1.1,
matplotlib 3.11.1, pandas 3.0.5, sep 1.4.1, optuna 4.9.0, Pillow 12.3.0,
reportlab 5.1.0, pypdf 6.21.4, python-docx 1.2.0. Dependency check passed for
89 packages. Tkinter and a real TkAgg canvas rendered successfully.

VS Code 1.144.0 x64 already has Python, Pylance, Codex, Jupyter, Ruff and
PowerShell extensions. Workspace settings and launch.json already point to
`${workspaceFolder}\.venv\Scripts\python.exe`; its sibling engine analysis path
is valid. No credentials or unrelated editor settings changed.

## Data, portability and parameters

Dropbox's local info.json confirms `C:\Users\gordo\Dropbox`. Research root:
`C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research`.
Automatic machine detection returns Laptop; launchers explicitly select Laptop.
No D: alias or WSL environment was needed.

MER inventory: all 2,777 manifest FITS paths resolve locally. S4G inventory:
all 182 original images resolve. Representative MER and S4G FITS headers and
pixels were actually read and processed. This establishes representative local
readability, not a full pixel scan or proof of global Dropbox synchronisation.

MER's source manifest embeds D: paths. The minimal Store change resolves its
`fits_filename` under the explicit local data root when the file exists; it
leaves source CSV bytes, scientific columns and provenance hash untouched.
Existing saved reviews/refits and science outputs remain unchanged. Hashes of
the source manifest and saved review JSONs were checked before/after.

The GUI received a small `--output` option for isolated laptop image output and
retains explicit parameter-file overrides when reloading.
No global path replacement was performed. The audit identifies 266 JSON/CSV
files with desktop paths (historical provenance, refit indexes, configuration
and optimisation products); these originals remain intact and are not used as
live laptop server state. See `laptop_setup\verification\inventory.json`.

Important parameter distinction:

- **SEP is diagnostic only: current optimisation REJECTED, fold 20.** Its
  selected `sep_toy_object_optimisation_best.json` is copied byte-for-byte to
  `laptop_setup\config\sep-diagnostic-rejected-fold20.json`. An embedded /mnt/d
  path and Windows long path caused the unconfigured GUI to select an older
  optimisation instead. The laptop launcher explicitly selects the actual
  current diagnostic candidate. It is not an accepted production winner.
- **MTObjects uses the FINAL winner** at
  `Remove foreground objects\clean22_haigh_aligned_bright150_galaxy150_sep_sensitivity\MTObjects_cross_validation\mtobjects_toy_cross_validation_best.json`.
- No built-in defaults substituted. Exact source paths and SHA256 hashes are in
  `laptop_setup\config\provenance.json`; resolved values in
  `laptop_setup\parameter_sources.log`.

The laptop copy `config\paired-injections-laptop.json` translates 221 selected
manifest path references to the real C: research root with Windows long-path
support. Every translated reference exists, including original images, payloads
and relevant source configuration; original manifest and immutable NPZ payloads
remain untouched. The current GUI constructs its smooth Gaussian model from
the image; it does not need a separate external smooth-model FITS for this path.
`prepare_config.py` records the source checksum and can recreate these copies.
The GUI's 'Reload optimised parameters' control now honours explicit --sep-best /
--mto-best selections, preventing a reload from silently switching parameter sources.

No transfer is required for verified workflows. Two missing original campaign
profiles are expected because both are recorded `fit_failed` with zero accepted
isophotes:

- `Euclid_MER_VIS_geometry\profiles\Euclid_-586374330510251740_MER_VIS_ellipse_profile.csv`
- `Euclid_MER_VIS_geometry\profiles\Euclid_2645436353651870062_MER_VIS_ellipse_profile.csv`

If a reviewed successful profile for either exists only on GB-STUDY, transfer that
reviewed product and its matching provenance/refit directory; none was regenerated
as a substitute. Their FITS images are available and failed cases remain reviewable.

## Native MTObjects

Existing clean sibling checkout: `C:\Users\gordo\Documents\GitHub\mtobjects`.
Origin `https://github.com/CarolineHaigh/mtobjects.git`, branch master, commit
`b38a07a91a39097fdd8b7c40b530757a669533c8`. Kept the working version unchanged.
All four required .so files are actually **Windows PE AMD64 (0x8664)** libraries:
maxtree, maxtree_double, mt_objects, mt_objects_double. Each loaded via ctypes;
real double-precision processing also passed. Their hashes are in the inventory.
Existing MSYS2 UCRT64 runtime/toolchain: `C:\msys64\ucrt64\bin`, GCC 16.1.0,
GSL 2.8 including libgsl-28.dll and libgslcblas-0.dll. Shared processing registers
this DLL directory. No rebuild, toolchain installation, WSL enablement or restart.
Upstream recompile.sh and the Linux bootstrap were inspected; neither was run.
This proves this installed engine works, not binary equivalence to a modified
desktop engine or reproducibility from unmodified upstream alone.

## Verification outcomes and limits

- Six existing review-policy tests: PASS.
- Seven existing MER integration tests with explicit laptop DEFAULT_DATA: PASS.
  Scratch output and local HTTP server; source manifest hash preserved.
- Existing adaptive synthetic geometry check redirected into scratch: PASS.
  Centre (93.00085, 88.00452), PA 119.9967 degrees, inclination 53.1369 degrees.
- Current campaign prepare-only: PASS, 19 cases; launcher mode also passed.
- Actual localhost `/api/health`, `/api/galaxy`, `/api/image`: HTTP 200.
  Opened original profile and 5.35 MB image response for -663928688473758026.
- One isolated locked-centre refit: COMPLETE, job
  `6eedaafe71fe409e9f113465ab6fe413`; not adopted as a scientific decision.
- Native comparison GUI opened and processed IC1954 through SEP and MTO:
  227,925 / 55,791 full-image mask pixels; recovered finite input pixels remain
  finite. Saved comparison PNG and mask/recovered FITS in scratch.
- GUI also loaded exact `training_seed_1` saved payload for NGC4765 and processed
  both methods, including no-toy baselines: PASS. Masks 193,872 / 94,355 pixels;
  finite recovered output. This exercises laptop payload translation.
- Comparison PNG inspected: both masks/recovered panels present. Existing long
  panel titles overlap at laptop export dimensions; plot-label layout was not
  redesigned. SciPy emitted moment precision warnings on nearly constant samples;
  processing completed. SEP diagnostic visibly overmasks, consistent with its
  rejected optimisation status; installation success is not scientific approval.

Detailed local evidence: `laptop_setup\mer_tests.log`, `synthetic_tests.log`,
`gui_tests.log`, `paired_gui_tests.log`, plus `verification\mer_results.json`,
`gui_results.json`, `inventory.json` and `verification\comparison`.
Verification folders/logs are locally ignored by laptop_setup/.gitignore.
No full campaign, optimisation, global pixel scan or independent science validation
was performed. No blocking system setup remains for the tested Windows workflows.
