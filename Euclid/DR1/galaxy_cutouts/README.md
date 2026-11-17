# Remote DR1 galaxy cutouts from a PC

`Galaxy_image_remote.py` is the commented Python learning example for VS Code.
It queries ESA remotely, asks ESA to cut the selected MER VIS mosaic, then
downloads only the cutout. It needs no Datalabs mount on the PC.

From the PythonScripts repository root:

```powershell
uv pip install -r .\Euclid\DR1\galaxy_cutouts\requirements.txt
.\.venv\Scripts\python.exe .\Euclid\DR1\galaxy_cutouts\Galaxy_image_remote.py
```

Select the repository `.venv\Scripts\python.exe` interpreter in VS Code.
Edit `NAME`, `RADIUS`, `OUTPUT_FOLDER` and `OPEN_PREVIEWS` near the top of the
script. The default NGC 1365 radius is 6 arcminutes, requesting approximately
a 12 arcminute square. At native VIS sampling this produced a 198.1 MiB FITS.
The download guard is 500 MiB. Existing output filenames are replaced on rerun.

Outputs are independent of the script location:

- `D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\DR1\galaxy_cutouts\NGC_1365_cutout.fits`: original returned science pixels.
- `D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\DR1\galaxy_cutouts\NGC_1365_cutout.png`: basic asinh display.
- `D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\DR1\galaxy_cutouts\NGC_1365_autostretch.png`: additional AutoSTF-style display.

The program opens both PNGs with the Windows default image viewer. A missing
Dropbox research folder stops the program rather than silently saving large files on C:.

NGC 1365 has severe polygonal discontinuities in this DR1 MER mosaic. They are
present in the FITS and basic preview; AutoSTF makes them more conspicuous.
Do not treat the finite-pixel check as scientific image-quality approval.
An ESA non-string `EXTNAME` header card also raises a verification warning;
the script preserves the original FITS and accepts usable two-dimensional data.

Windows Smart App Control previously blocked Astropy's `_np_utils.pyd` in the
PC environment. Reinstalling the same version did not resolve that policy
block. A subsequent user run succeeded; this script does not change Windows
security settings.
