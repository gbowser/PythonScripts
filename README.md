# PythonScripts

[![Env check](https://github.com/OWNER/REPO/actions/workflows/env-check.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/env-check.yml)

Replace `OWNER/REPO` in the badge URLs above with your GitHub repository path to enable the Actions badge.

## Setup (Windows)

Prerequisites: install Python 3.11 or newer and add it to PATH.

Open PowerShell in the repository root and run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\scripts\setup_env.ps1
```

This script will create a local virtual environment in `.venv`, install the pinned requirements, and write a `requirements-locked.txt` (useful to commit for exact reproducibility).

If you prefer to manually create the venv and install:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r s4g_image_downloader\requirements.txt
python -m pip freeze > requirements-locked.txt
```

Commit `requirements-locked.txt` to ensure both PCs install the exact same package versions.
