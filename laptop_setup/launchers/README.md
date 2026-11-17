# Existing laptop program launchers

These are executable launchers, retained separately from the obsolete transfer
instructions that the user requested be deleted. From PythonScripts root:

```powershell
powershell.exe -NoProfile -File .\laptop_setup\launchers\Start_Laptop_MER.ps1
powershell.exe -NoProfile -File .\laptop_setup\launchers\Start_Laptop_SEP_MTO.ps1
```

Their repository-root calculation was adjusted for this folder. Their existing
laptop-specific data paths, parameters and outputs remain unchanged. Use them
only on a machine with the required laptop data/configuration. They were syntax
checked after moving, not used to start servers or scientific processing.

The old desktop package snapshot is retained at
`laptop_setup/requirements-pc1-freeze.txt`; it is a dated reference, not a new
recommendation to replace the current uv environment. Shared machine detection
remains in the root `machine_paths.py` as explicitly requested.
