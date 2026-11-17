# PythonScripts

This repository contains astronomy research programs, Python learning examples
and other personal projects. Run the commands below from this repository root.

Euclid programs are organised by release:

- [DR1 programs](Euclid/DR1/README.md): remote galaxy cutouts, the 100-galaxy
  preview pilot and full candidate catalogue manifests.
- [Q1 programs](Euclid/Q1/README.md): Q1 catalogue selection, cutout links and
  the ESA Datalabs extraction/geometry workflow.
- [Shared Euclid analysis](Euclid/README.md): local geometry, masking and other
  tools that are not restricted to one release.
- [Folder and command guide](Euclid/Codex%20Documentation/Repository_Folder_Guide.md).

The project uv environment (`.venv`), `pyproject.toml`, `uv.lock`, `AGENTS.md`,
`PROJECT_HANDOVER.md` and shared `machine_paths.py` stay at the repository root.

## Output storage

[Git storage and relocated data](Euclid/Codex%20Documentation/Git_Storage_Guide.md)
lists the 17 November large-file moves, validation locations and GitHub limits.

**Do not use `H:\Codex` for new output.** Significant scientific data,
downloads, manifests, archives and substantial working files belong under:

```text
D:\Dropbox\Public Documents\UCLAN\MSc Research
```

Use useful project subfolders that mirror the source structure where practical.
For example, the remote galaxy script writes its FITS and PNGs to:

```text
D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\DR1\galaxy_cutouts
```

Maintained source, documentation and small companion files remain in this
repository. If the research archive is unavailable, report the problem rather
than silently saving large files elsewhere. Existing unrelated data are not
automatically relocated or regenerated.

The research example folder is now named `Foreground_mask_examples` with a
capital F. The ping logger has its own folder at
[Diagnostics/PingTest](Diagnostics/PingTest/README.md).
