# New PC Python and VS Code setup briefing

Inventory captured on 10 August 2026 from Windows 11 x64.

## Objective for Codex

Recreate this PC's Python development setup on a new Windows 11 x64 PC as closely as practical. Execute the work, verify every stage, and report any substitution or failure. Do not copy credentials, authentication tokens, caches, absolute old-user paths, or stale registry entries.

Use `uv` as the primary Python version, virtual-environment, dependency, and package manager on the new machine. For repositories, prefer `uv sync`, `uv add`, `uv remove`, and `uv run`; do not install project libraries globally. Use pip only where this briefing explicitly calls for reproducing the optional legacy global package snapshot.

Use current user-level installs unless administrator access is genuinely required. Prefer the exact versions below. If an exact application or extension version is no longer obtainable, install the newest compatible version and record the difference. For Python itself, remain on the Python 3.13 line rather than silently moving the main environment to 3.14.

## Baseline software

- Main Python: CPython 3.13.14, 64-bit, installed per-user from python.org/WinGet.
- Python launcher: installed and `py` works.
- pip: 26.1.2.
- uv: 0.11.32, installed through WinGet (`astral-sh.uv`).
- Secondary runtime: uv-managed CPython 3.14.3 x64. It has no installed packages and is not the default. Recreate it only after the main 3.13 setup.
- VS Code: 1.132.0 x64, user install.
- Git: 2.53.0.windows.1.
- No active Conda, Poetry, or pipx installation/environment was found.
- Registry entries referring to `C:\Users\gordo\anaconda3` and `D:\anaconda3` are stale; do not install Anaconda because of them.
- No Jupyter kernels were registered at inventory time.

Suggested application installation sequence (adjust only if the package source has moved):

```powershell
winget install --exact --id Python.Python.3.13
winget install --exact --id astral-sh.uv
winget install --exact --id Microsoft.VisualStudioCode
winget install --exact --id Git.Git
```

Immediately verify the uv installation:

```powershell
uv --version
uv python install 3.13
uv python install 3.14.3
uv python list
```

Python 3.13 is the default project version. The uv-managed 3.14.3 runtime is secondary and should not replace it.

After Python installation, confirm that `python`, `py -3.13`, and `pip` resolve to the new user's CPython 3.13 installation. Do not hard-code the old username `gordo`.

## Download the PythonScripts code from GitHub

The repository is `https://github.com/gbowser/PythonScripts.git`; its default branch is `main`. After Git is installed, clone it into the new user's Documents/GitHub directory:

```powershell
$githubRoot = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Github'
New-Item -ItemType Directory -Path $githubRoot -Force | Out-Null
Set-Location $githubRoot
git clone --recurse-submodules https://github.com/gbowser/PythonScripts.git
Set-Location (Join-Path $githubRoot 'PythonScripts')
git fetch --all --prune
git switch main
git pull --ff-only
```

This brings down the repository and all remote branch history. The known remote branches at inventory time were `main`, `agent/azure-all-optimisers`, `agent/azure-mtobjects-linux`, and `agent/configure-uv-environment`. Do not switch to an agent branch unless the user requests it.

If GitHub prompts for authentication, use the user's GitHub sign-in or Git Credential Manager. Do not place a token in this briefing, the clone URL, or a repository file.

After cloning, verify:

```powershell
git remote -v
git branch --remotes
git status --short
```

Important: this briefing file must itself be committed and pushed to GitHub, or transferred separately, before it will be available from the clone.

## Repository environment (preferred)

The repository contains `.python-version` with `3.13`, plus `pyproject.toml` and `uv.lock`. After cloning/copying the repository, use the lockfile as the authoritative reproducible environment:

```powershell
Set-Location <new-path-to-PythonScripts>
uv python install 3.13
uv sync --frozen
```

If `uv sync --frozen` reports that the lock is stale or incompatible, stop and report the problem before changing the lock. Do not replace the repository environment with the global freeze below.

At inventory time the existing `.venv` used Python 3.13.14, contained 87 uv-managed packages, had no standalone pip module, and `uv sync --frozen --dry-run` reported that no changes were needed. Do not copy the old `.venv`; recreate it from `uv.lock` on the new PC. A pip-less uv environment is normal here.

The declared top-level dependencies are: astropy, astroquery, debugpy, ffmpeg (Python package), galpy, imageio, matplotlib, numpy, openpyxl, optuna, pandas, photutils, pvextractor, pywin32 on Windows, python-docx, requests, scikit-image, scipy, selenium, sep, and spectral-cube.

## Global CPython 3.13 package snapshot

This is the exact `python -m pip freeze --all` output from the active global interpreter. Recreate it only if global compatibility is wanted; project work should use the uv environment above. Save these lines as a temporary requirements file and run `py -3.13 -m pip install -r <file>`.

```text
alembic==1.18.5
astropy==7.2.0
astropy-iers-data==0.2026.6.8.17.49.5
astroquery==0.4.11
beautifulsoup4==4.15.0
certifi==2026.5.20
charset-normalizer==3.4.7
colorama==0.4.6
colorlog==6.11.0
contourpy==1.3.3
cycler==0.12.1
defusedxml==0.7.1
et_xmlfile==2.0.0
fonttools==4.63.0
GPyOpt==1.2.6
greenlet==3.5.3
html5lib==1.1
idna==3.18
ImageIO==2.37.3
jaraco.classes==3.4.0
jaraco.context==6.1.2
jaraco.functools==4.5.0
keyring==25.7.0
kiwisolver==1.5.0
lazy-loader==0.5
lxml==6.1.1
Mako==1.3.12
MarkupSafe==3.0.3
matplotlib==3.10.9
more-itertools==11.1.0
networkx==3.6.1
numpy==2.4.6
openpyxl==3.1.5
optuna==4.9.0
packaging==26.2
pandas==3.0.3
patsy==1.0.2
pdf2image==1.17.0
photutils==3.0.0
pillow==12.2.0
pip==26.1.2
pyerfa==2.0.1.5
pyparsing==3.3.2
python-dateutil==2.9.0.post0
python-docx==1.2.0
python-pptx==1.0.2
pyvo==1.9.0
pywin32==312
pywin32-ctypes==0.2.3
PyYAML==6.0.3
reportlab==5.0.0
requests==2.34.2
scikit-image==0.26.0
scipy==1.17.1
sep==1.4.1
six==1.17.0
soupsieve==2.8.4
SQLAlchemy==2.0.51
statsmodels==0.14.6
tifffile==2026.6.1
tqdm==4.69.0
typing_extensions==4.15.0
tzdata==2026.2
urllib3==2.7.0
webencodings==0.5.1
xlsxwriter==3.2.9
```

Note: some repository-declared packages are not in this global snapshot; that is expected because the repository's uv environment and the global interpreter serve different purposes.

## VS Code extensions

Install this union of the default profile and the profile named `Python Beginner Layout`. Exact versions are recorded for fidelity:

```text
anthropic.claude-code@2.1.226
charliermarsh.ruff@2026.70.0
github.codespaces@1.18.13
mathematic.vscode-pdf@0.1.11
mechatroner.rainbow-csv@3.24.1
ms-python.autopep8@2026.4.0
ms-python.debugpy@2026.6.0
ms-python.python@2026.4.0
ms-python.vscode-pylance@2026.3.1
ms-python.vscode-python-envs@1.36.0
ms-toolsai.jupyter@2025.9.1
ms-toolsai.jupyter-keymap@1.1.2
ms-toolsai.jupyter-renderers@1.3.0
ms-toolsai.vscode-jupyter-cell-tags@0.1.9
ms-toolsai.vscode-jupyter-slideshow@0.1.6
ms-vscode.cmake-tools@1.23.52
ms-vscode.cpp-devtools@0.5.13
ms-vscode.cpptools@1.32.2
ms-vscode.cpptools-extension-pack@1.5.1
ms-vscode.cpptools-themes@2.0.0
ms-vscode.powershell@2025.4.0
openai.chatgpt@26.803.41515
optuna.optuna-dashboard@0.3.0
reditorsupport.r@2.8.8
reditorsupport.r-syntax@0.1.4
tomoki1207.pdf@1.2.2
```

For each line, Codex may run `code --install-extension <line> --force`. If an exact version cannot be retrieved, retry with the extension ID alone and record the installed version.

## VS Code user settings

Create/select a profile named `Python Beginner Layout`. Apply the settings below. Resolve the interpreter path dynamically on the new PC (for example with `py -3.13 -c "import sys; print(sys.executable)"`) and replace `<PYTHON_313_EXE>` with that result.

```json
{
  "update.showReleaseNotes": false,
  "workbench.colorTheme": "Light Modern",
  "security.workspace.trust.untrustedFiles": "open",
  "diffEditor.codeLens": true,
  "editor.minimap.autohide": "mouseover",
  "editor.fontSize": 16,
  "editor.formatOnSave": true,
  "python.defaultInterpreterPath": "<PYTHON_313_EXE>",
  "files.autoSave": "afterDelay",
  "editor.wordWrapColumn": 1000,
  "editor.detectIndentation": false,
  "workbench.settings.applyToAllProfiles": ["editor.wordWrapColumn"],
  "diffEditor.wordWrap": "off",
  "jupyter.themeMatplotlibPlots": true,
  "git.autofetch": true,
  "git.enableSmartCommit": true,
  "terminal.integrated.initialHint": false,
  "workbench.startupEditor": "none",
  "workbench.editor.empty.hint": "hidden",
  "git.confirmSync": false,
  "workbench.editor.enablePreview": false,
  "python.terminal.executeInFileDir": true,
  "chat.viewSessions.orientation": "stacked",
  "window.newWindowProfile": "Python Beginner Layout",
  "powershell.promptToUpdatePowerShell": false,
  "python.createEnvironment.trigger": "off"
}
```

Do not migrate the old profile's Claude setting that bypasses permissions; it is a security preference, not a Python requirement.

The `Scientific_Programming/PythonScripts.code-workspace` file additionally sets `python.terminal.activateEnvironment` to `false` and opens the OpenAI/Codex extension on startup. Retain repository workspace files as committed rather than recreating them globally.

## Verification checklist

Run these checks and provide their output summary:

```powershell
python --version
py -0p
py -3.13 -m pip check
uv --version
uv python list
code --version
code --list-extensions --show-versions
git --version
```

Then, inside the repository:

```powershell
uv sync --frozen
uv run python --version
uv run python -c "import astropy, astroquery, numpy, pandas, scipy, matplotlib, photutils, sep; print('core imports OK')"
git status --short
```

Success means Python 3.13 is the default, the locked repository environment synchronizes, core imports work, VS Code has the requested extensions/settings, and setup did not modify tracked repository files unexpectedly.
