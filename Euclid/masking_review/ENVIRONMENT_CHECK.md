# Masking reviewer verification — 12 November 2026

The required runtime components are installed and working. The default launch
and validation commands need local path overrides on this computer. Automated
checks passed after supplying the actual FITS directory. This is not a complete
manual visual acceptance review of every README interaction.

## Python requirements

Checked `requirements.txt` against the project `.venv`, and imported all seven
packages successfully. Interpreter: `../../.venv/Scripts/python.exe`, Python
3.13.14, Windows AMD64.

| Package | Required | Installed | Result |
| --- | --- | --- | --- |
| numpy | >=1.26 | 2.5.1 | Pass |
| scipy | >=1.11 | 1.18.0 | Pass |
| astropy | >=6 | 8.0.2 | Pass |
| photutils | >=2.2 | 3.1.1 | Pass |
| matplotlib | >=3.8 | 3.11.1 | Pass |
| Pillow | >=10 | 12.3.0 | Pass |
| scikit-image | >=0.22 | 0.26.0 | Pass |

The environment has no pip module. The installed uv wrapper returned "Access is
denied" when used for a consistency check. An independent installed-distribution
metadata check evaluated 134 active dependency requirements and found no missing
or incompatible dependencies. No installation was required.

## Other components and data

- Windows PowerShell is available and was used for verification.
- The launcher's managed-dependency directory is absent, so its default Python
  selection falls back to the working project `.venv`.
- Bare `python` resolves to the WindowsApps alias; use the explicit interpreter.
- Node v24.22.1 works at
  `C:\Users\gordo\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe`.
  Node is absent from PATH, so the README's bare `node` command needs this path.
  Node is used for the UI test, not to serve the reviewer.
- The separate `../../mtobjects` checkout and all four native libraries exist.
  Their executable headers identify Windows binaries despite their `.so` names.
  A synthetic processing call and all pilot detections successfully exercised
  the native engine and its runtime dependencies. A compiler is unnecessary to
  run these already built libraries.
- The default manifest contains stale `D:\Dropbox` science paths. All six pilot
  FITS files are present and readable at
  `C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_cutouts`.
  All six loaded successfully, including their WCS and review geometry.
- PixInsight itself is unnecessary: the README describes an implemented stretch,
  not a call to the PixInsight application.

## Validation results

| Check | Result |
| --- | --- |
| Python unittest discovery | All 20 tests passed |
| Node `test_ui.cjs` | Passed using the explicit Node executable |
| Native synthetic MTO detection | Passed on a 64 x 64 image |
| Local server | `/api/health` and `/` returned HTTP 200; temporary server stopped |
| Real pilot data | All six native FITS images loaded and all six MTO detections completed |
| Review persistence and refit | Automated mask save/restore and masked Photutils refit passed |
| Move comparison | All five values, 0.1/0.3/0.5/0.7/0.9, completed |
| Real-data deprojection | Passed using the exact validation mask and matching refit |

The tests cover processing-crop mapping, exclusion of unprocessed pixels,
unrestricted centre-label masking, residual sublabels, source preservation,
AutoStretch, known-ellipse recovery, geometry provenance, mask-safe resampling,
signed profiles, coverage gaps and generated deprojection products. The Node
test uses a mocked DOM/canvas. Browser rendering, physical foreground membership
and human visual confirmation have not been independently validated.

The documented unmodified `validate_integration.py` command initially fails
because it uses the stale catalogue paths. Its namespace and parent-process
source lookup were overridden in memory for the successful local run; source
files and catalogue paths were not changed. The script has no `--fits-dir` CLI
option, and its source-hash assertion also omits a FITS-directory argument.

Successful integration evidence:
`validation_output/77f25761538c460f8e4afda3b2629189/validation.json`.
The additional deprojection evidence is `deprojection_validation.json` in that
folder. All six documented deprojection products were created under
`deprojections/a61fc95fc2c949c7b7359f5d0bbcc7e6/`.

Validation outputs are automated test artifacts, not adopted scientific reviews.
The refit remains provisional and requires visual review, as documented. Earlier
failed attempts also left separate artifacts under `validation_output/`.

## Working launch command

Run from `Euclid/masking_review`:

```powershell
.\Start_Euclid_Masking.ps1 -FitsDir 'C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_cutouts'
```

The equivalent explicit Python launch is:

```powershell
& ..\..\.venv\Scripts\python.exe reviewer.py --fits-dir 'C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_cutouts' --no-browser
```

The server invocation was verified with a separate temporary output directory.
The PowerShell launcher's double-click behavior was inspected, not exercised.
Double-clicking its default `.cmd` does not supply the required local FITS path.

No packages, launchers, source science files, catalogues or adopted reviews were
modified by this check. Only this report and isolated validation artifacts were
created; no verification server remains running.
