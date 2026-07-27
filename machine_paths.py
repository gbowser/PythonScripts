"""Machine-specific local path defaults used by project scripts."""

from __future__ import annotations

from pathlib import Path
import os


PC_RESEARCH_FOLDERS = {
    "Laptop": Path(r"C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research"),
    "Desktop": Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research"),
}

PC_HOSTNAMES = {
    "gb-study": "Laptop",
}


def detect_pc(reference_path: str | Path | None = None) -> str:
    """Return the configured device whose drive contains the running code.

    ``FOREGROUND_MASKING_PC`` remains available as an explicit environment
    override.  Matching the code/cwd drive makes detection deterministic when
    both Dropbox trees are visible on the same machine.
    """
    override = os.environ.get("FOREGROUND_MASKING_PC")
    if override:
        if override not in PC_RESEARCH_FOLDERS:
            choices = ", ".join(sorted(PC_RESEARCH_FOLDERS))
            raise ValueError(f"FOREGROUND_MASKING_PC must be one of: {choices}")
        return override

    hostname = os.environ.get("COMPUTERNAME", "").casefold()
    if hostname in PC_HOSTNAMES:
        return PC_HOSTNAMES[hostname]
    if "laptop" in hostname:
        return "Laptop"
    if "desktop" in hostname:
        return "Desktop"

    reference = Path(reference_path or Path.cwd()).resolve()
    for pc_name, root in PC_RESEARCH_FOLDERS.items():
        if reference.drive.casefold() == root.drive.casefold():
            return pc_name

    available = [name for name, root in PC_RESEARCH_FOLDERS.items() if root.exists()]
    if len(available) == 1:
        return available[0]
    raise RuntimeError(
        "Could not auto-detect this device; pass --pc or set FOREGROUND_MASKING_PC."
    )


def research_folder(pc_name: str) -> Path:
    return PC_RESEARCH_FOLDERS[pc_name]


def erwin_folder(pc_name: str) -> Path:
    return research_folder(pc_name) / "Erwin"


def shoulder_folder(pc_name: str) -> Path:
    return research_folder(pc_name) / "Shoulder_Recognition_Erwin"


def remove_foreground_folder(pc_name: str) -> Path:
    return research_folder(pc_name) / "Remove foreground objects"
