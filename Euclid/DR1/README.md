# Euclid DR1 programs

These programs use DR1 Foundation (`dr1` schema, `DR1_R2` processing release).
Run the Windows commands from the PythonScripts repository root.

## Remote named galaxy cutouts

[galaxy_cutouts/README.md](galaxy_cutouts/README.md) explains the heavily
commented learning script. ESA creates the cutout remotely, then the PC saves
the original FITS and basic/AutoSTF PNG previews under `D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\DR1\galaxy_cutouts`.

```powershell
uv pip install -r .\Euclid\DR1\galaxy_cutouts\requirements.txt
.\.venv\Scripts\python.exe .\Euclid\DR1\galaxy_cutouts\Galaxy_image_remote.py
```

## Barred galaxy pilot and full catalogue

- 100-galaxy gallery: open `Euclid/DR1/barred_galaxy_pilot/gallery.html` under
  your Dropbox research folder (location below).
- [Pilot guide](barred_galaxy_pilot/DR1_Barred_Galaxy_Pilot_Guide.md).
- [Pilot requirements](barred_galaxy_pilot/requirements.txt).
- [Full-manifest guide](barred_galaxy_pilot/full_manifest/DR1_Full_Manifest_Guide.md).
- [Full-manifest requirements](barred_galaxy_pilot/full_manifest/requirements.txt).

The pilot's gallery, evidence, PNGs and generated manifests are together under
the matching Dropbox research path, including the full-catalogue data. Source,
notebooks, requirements and guides remain here. On this laptop the output root is:

```text
C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\DR1
```

The desktop equivalent starts with `D:\Dropbox`. Archived ZIP contents were
reconciled on 23 November 2026; differing historical source/guides are preserved
under `archive_imports` beside their active source. The ESA source-extraction
archive belongs to `Euclid/Q1/datalabs_MER_VIS/source_extraction_pilot`, not DR1.
See [the storage guide](../Codex%20Documentation/Git_Storage_Guide.md).
The former root copies were identical duplicates and
have been removed after SHA256 comparison. New PC runs should use output
folders under `D:\Dropbox\Public Documents\UCLAN\MSc Research`; the notebook's relative folders are for ESA Datalabs.
