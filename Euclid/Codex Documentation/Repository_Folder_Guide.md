# PythonScripts Euclid folder guide

Updated 17 November 2026. Release-specific programs now live under
`Euclid/DR1` and `Euclid/Q1`. Shared analysis and local-image tools remain under
`Euclid`. Commands below run from the PythonScripts repository root.

The full-catalogue outputs and the 100-object pilot gallery, PNGs, manifests and
query evidence now live in the matching Dropbox research folder. The pilot source
and `full_manifest` builders, notebooks and guides remain in Git. The pilot
relocation and four-ZIP reconciliation were verified on 23 November 2026.
Other large-data relocations and dependency handling are listed in
[Git storage](Git_Storage_Guide.md). Earlier Word exports show the prior layout.

```text
PythonScripts/
  pyproject.toml, uv.lock, .venv/     Project Python environment
  AGENTS.md, PROJECT_HANDOVER.md    Instructions and cross-computer status
  Euclid/
    DR1/
      galaxy_cutouts/              Remote named-galaxy FITS and two PNG previews
        Galaxy_image_remote.py
        requirements.txt
        README.md
      barred_galaxy_pilot/          100-object pilot source, notebook and guide
        archive_imports/           Historical guides from ZIP exports
        full_manifest/             Metadata builders; generated catalogue in Dropbox
    Q1/
      compile_q1_VIS_barred_spirals.py
      build_mer_vis_cutout_links.py
      compare_spitzer_q1_overlap.py
      requirements.txt
      q1_barred_spirals/            Shortlist and frame metadata
      q1_mer_vis_cutouts/           Cutout URL manifests
      datalabs_MER_VIS/             ESA Q1 cutout and geometry workflow
        source_extraction_pilot/    SEP and MTObjects pilot
    masking_review/                Shared foreground-mask and bar-analysis app
    adaptive_MER_VIS/              Local geometry fitting
    review_MER_VIS/                Existing geometry review workflow
    comparisons/, reports/         Existing reports and results
    Codex Documentation/           Finished guides and catalogues
```

## Remote DR1 galaxy example in VS Code

```powershell
uv pip install -r .\Euclid\DR1\galaxy_cutouts\requirements.txt
.\.venv\Scripts\python.exe .\Euclid\DR1\galaxy_cutouts\Galaxy_image_remote.py
```

Select `.venv\Scripts\python.exe` with VS Code's **Python: Select Interpreter**.
The script's settings and detailed comments remain near its top. Outputs still
go to `D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\DR1\galaxy_cutouts`; moving the program does not change that location.
Keep the unstretched FITS for science and use the two PNGs for viewing.

## Output storage policy

The current research archive is
`D:\Dropbox\Public Documents\UCLAN\MSc Research`. New substantial data and
working outputs belong in project folders there, mirroring the source layout
where useful. Do not use H: for new output. Maintained source, guides and small
companion examples remain in PythonScripts.

The existing NGC 1365 FITS, both PNGs and validation files were moved from H:
to `D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\DR1\galaxy_cutouts`,
with matching SHA256 hashes before the old copy was removed. Other unrelated
existing results and archives have not been relocated automatically.

The research folder `foreground_mask_examples` was renamed to
`Foreground_mask_examples` (capital F); all 24 files were hash-verified unchanged.

## Other root programs and associated results

| Item | Current location relative to PythonScripts |
| --- | --- |
| Ping logger | `Diagnostics/PingTest/PingTest.ps1` |
| Shared desktop/laptop paths | `machine_paths.py` — explicitly retained at root |
| Existing laptop launchers | `laptop_setup/launchers` |
| Desktop dependency snapshot | `laptop_setup/requirements-pc1-freeze.txt` |
| Word rendering helper | `tools/document_rendering/render_docx_windows.ps1` |
| WSL optimisation wrappers | `Foreground Masking/Optimisation/launchers` |
| Smoothing example source | `SRA/adaptive_gaussian_smoothing_example.py` |
| Existing smoothing example PNG | `SRA/example_outputs/adaptive_gaussian_smoothing_example.png` |
| Existing toy comparison CSVs | `Foreground Masking/results/toy_comparison_2026-08-20` |
| NGC 0986 figure preview | `Erwin_s4g_image_downloader/geometry_output/previews` |
| Imported Erwin reference table | `Erwin_barprofiles_paper_GB_working_copy/data/reference_imports` |

Dates were used as supporting evidence, not proof of authorship. The small
result folders have README files distinguishing exact source matches from
workflow associations and unidentified creation commands. The smoothing
program's exact save command identifies the old root PNG; new runs now save
to the research archive's `SRA/example_outputs` folder rather than the terminal's
working directory.

The obsolete `LAPTOP_MER_MTO_SETUP.md` and `LAPTOP_SETUP_REPORT.md` transfer
notes were deleted, along with the stale root `debug.log`. `PROJECT_HANDOVER.md`
remains because the user's latest AGENTS instructions explicitly require it.

## DR1 pilot previews in Dropbox

Below the Dropbox research root, open:

- Gallery: `Euclid/DR1/barred_galaxy_pilot/gallery.html`.
- Contact sheets: `Euclid/DR1/barred_galaxy_pilot/preview_results/contact_sheet_01.png`
  through `contact_sheet_04.png`.
- Individual images: `Euclid/DR1/barred_galaxy_pilot/preview_results/png`.

The laptop research root is
`C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research`;
the desktop root is `D:\Dropbox\Public Documents\UCLAN\MSc Research`.

Install pilot dependencies from
`Euclid/DR1/barred_galaxy_pilot/requirements.txt`, or full-manifest dependencies
from `Euclid/DR1/barred_galaxy_pilot/full_manifest/requirements.txt`.
Existing benchmark files, catalogue values, query responses and original
checksum records are retained. New PC outputs belong in the Dropbox research archive, for example:

```powershell
uv pip install -r .\Euclid\DR1\barred_galaxy_pilot\requirements.txt
.\.venv\Scripts\python.exe .\Euclid\DR1\barred_galaxy_pilot\build_dr1_manifest.py --output-dir "D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\DR1\barred_galaxy_pilot\new_query" --disc-policy provisional-two-answer --limit 100
.\.venv\Scripts\python.exe .\Euclid\DR1\barred_galaxy_pilot\dr1_preview_pilot.py --manifest "D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\DR1\barred_galaxy_pilot\new_query\DR1_first100_manifest.csv" --output "D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\DR1\barred_galaxy_pilot\new_previews" --limit 100
```

## Q1 programs

See [Q1 README](../Q1/README.md). Its metadata tools use
`Euclid/Q1/requirements.txt`. Existing local Q1 FITS locations on Dropbox and
the ESA workspace `/media/user/Euclid_MER_VIS` have not changed. Local source
relocation does not automatically change a separate uploaded ESA workspace.

## Old and current locations

| Previous location relative to PythonScripts | Current location |
| --- | --- |
| Root `Galaxy_image_remote.py` | `Euclid/DR1/galaxy_cutouts/Galaxy_image_remote.py` |
| Root `Galaxy_image_remote_requirements.txt` | `Euclid/DR1/galaxy_cutouts/requirements.txt` |
| `Euclid/dr1_barred_pilot` | `Euclid/DR1/barred_galaxy_pilot` |
| `Euclid/datalabs_MER_VIS` | `Euclid/Q1/datalabs_MER_VIS` |
| `Euclid/q1_barred_spirals` | `Euclid/Q1/q1_barred_spirals` |
| `Euclid/q1_mer_vis_cutouts` | `Euclid/Q1/q1_mer_vis_cutouts` |
| `Euclid/compile_q1_VIS_barred_spirals.py` | `Euclid/Q1/compile_q1_VIS_barred_spirals.py` |
| `Euclid/build_mer_vis_cutout_links.py` | `Euclid/Q1/build_mer_vis_cutout_links.py` |
| `Euclid/compare_spitzer_q1_overlap.py` | `Euclid/Q1/compare_spitzer_q1_overlap.py` |

Seven root DR1 pilot files were identical to their maintained copies and were
removed after SHA256 comparison. The empty root `preview_results`,
`query_evidence` and `output` folders were removed too.

## Documentation and historical evidence

Active source, Markdown guides and affected Word guides have their references
updated. Archived code backups and saved-review provenance remain historical
snapshots; their embedded old paths are not current launch instructions.
Raw scientific tables and execution evidence are not rewritten simply to
change historical recorded paths. This guide is the current location index.
Source hashes printed in the older astronomy catalogues describe their
original dated audit, before the path/import edits made in this reorganisation.

The reorganisation inventory, validation record and pre-edit Word copies are
under `D:\Dropbox\Public Documents\UCLAN\MSc Research\Repository_maintenance\2026-11-17`.

## Cleanup limits

Generated Python caches were removed where accessible. The root `.pytest_cache`
could not be read or removed with the available permissions.

The root `tmp` folder and all its contents were deleted on 17 November 2026
following explicit user approval: 79 files, 22,849,292 bytes. Its absence was
verified. The deletion record is saved as
`D:\Dropbox\Public Documents\UCLAN\MSc Research\Repository_maintenance\2026-11-17\tmp_deletion.json`.

A pre-deletion file-by-file review list is saved as
`D:\Dropbox\Public Documents\UCLAN\MSc Research\Repository_maintenance\2026-11-17\tmp_review.csv`.
