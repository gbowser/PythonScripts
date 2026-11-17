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

- [100-galaxy gallery](barred_galaxy_pilot/gallery.html).
- [Pilot guide](barred_galaxy_pilot/DR1_Barred_Galaxy_Pilot_Guide.md).
- [Pilot requirements](barred_galaxy_pilot/requirements.txt).
- [Full-manifest guide](barred_galaxy_pilot/full_manifest/DR1_Full_Manifest_Guide.md).
- [Full-manifest requirements](barred_galaxy_pilot/full_manifest/requirements.txt).

The pilot's existing evidence, PNGs and manifests remain together inside
`barred_galaxy_pilot`, except the full-catalogue generated data and its query
evidence, now under the matching Dropbox research path. Full-manifest source
and guides remain here. See [the storage guide](../Codex%20Documentation/Git_Storage_Guide.md).
The former root copies were identical duplicates and
have been removed after SHA256 comparison. New PC runs should use output
folders under `D:\Dropbox\Public Documents\UCLAN\MSc Research`; the notebook's relative folders are for ESA Datalabs.
