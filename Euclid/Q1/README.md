# Euclid Q1 programs

These programs use Q1 data, not DR1. Run the Windows commands from the
PythonScripts repository root unless a program's own guide says otherwise.

| Program or folder | Purpose |
| --- | --- |
| `compile_q1_VIS_barred_spirals.py` | Build a bounded Q1 barred-spiral shortlist. |
| `build_mer_vis_cutout_links.py` | Generate Q1 MER VIS cutout URLs from catalogue metadata. |
| `compare_spitzer_q1_overlap.py` | Compare the Spitzer library with the Q1 selection and footprint. |
| [q1_barred_spirals](q1_barred_spirals/README.md) | Existing shortlist and calibrated-frame metadata. |
| [q1_mer_vis_cutouts](q1_mer_vis_cutouts/README.md) | Existing cutout links and manifests. |
| [datalabs_MER_VIS](datalabs_MER_VIS/START_HERE_MER_VIS.md) | Portable Q1 cutout and geometry workflow for ESA. |
| `datalabs_MER_VIS/source_extraction_pilot` | SEP and MTObjects pilot for the existing Q1 cutouts. |

Install metadata-program dependencies into the existing uv environment:

```powershell
uv pip install -r .\Euclid\Q1\requirements.txt
.\.venv\Scripts\python.exe .\Euclid\Q1\compile_q1_VIS_barred_spirals.py --help
.\.venv\Scripts\python.exe .\Euclid\Q1\build_mer_vis_cutout_links.py --help
.\.venv\Scripts\python.exe .\Euclid\Q1\compare_spitzer_q1_overlap.py --help
```

The shared frame-query helper remains at
`Euclid/build_euclid_VIS_NISP_frame_query.py`. The comparison's existing report
remains at `Euclid/comparisons/spitzer_q1_20261029`.

Moving the local scripts does not move files inside your separate ESA account.
The established ESA workspace `/media/user/Euclid_MER_VIS` stays unchanged.
The source-extraction installer manages its separate Linux dependencies; see
the [pilot guide](../Codex%20Documentation/ESA_Source_Extraction_Pilot_Guide.md).
