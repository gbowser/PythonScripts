# S4G Image Downloader

Downloads S4G 3.6 micron FITS images from IRSA for the galaxies listed in the
bar-profiles `scrambled_map.txt` file.

## Install

```powershell
cd "D:\Dropbox\Public Documents\PythonScripts\s4g_image_downloader"
& "..\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

## Test Without Downloading

```powershell
& "..\.venv\Scripts\python.exe" download_s4g_images.py --dry-run --limit 5
```

## Download One Image

```powershell
& "..\.venv\Scripts\python.exe" download_s4g_images.py --limit 1
```

## Download All Images

```powershell
& "..\.venv\Scripts\python.exe" download_s4g_images.py
```

Downloaded FITS files are written to `s4g_images_36um`. That folder is ignored
by Git so the code stays tracked without committing large image files.
