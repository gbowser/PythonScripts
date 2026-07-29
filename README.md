# PythonScripts

This repository uses [uv](https://docs.astral.sh/uv/) to manage Python 3.13 and its Python dependencies.

## First-time setup on another Windows PC

From PowerShell:

```powershell
winget install --id astral-sh.uv -e
git clone <repository-url>
cd PythonScripts
uv python install
uv sync --frozen
```

If the repository is already cloned, replace `git clone` with `git pull` and run the remaining commands from the repository root.

## Running scripts

Run a script in the managed environment without manually activating it:

```powershell
uv run python "path\to\script.py"
```

Alternatively, activate the environment for the current PowerShell session:

```powershell
.\.venv\Scripts\Activate.ps1
python "path\to\script.py"
```

## Changing dependencies

Use uv so that `pyproject.toml`, `uv.lock`, and `.venv` remain synchronized:

```powershell
uv add package-name
uv remove package-name
uv sync
```

Commit `pyproject.toml`, `uv.lock`, and `.python-version`. Do not commit `.venv`.

Machine-specific data paths and external applications are not managed by uv.
