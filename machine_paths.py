"""Machine-specific local path defaults used by project scripts."""

from __future__ import annotations

from pathlib import Path
import os


PC_RESEARCH_FOLDERS = {
    "Laptop": Path(r"C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research"),
    "Desktop": Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research"),
}

PC_HOSTNAMES = {
    "gb-study": "Desktop",
}


def _path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def detect_pc(reference_path: str | Path | None = None) -> str:
    """Return the configured device for local research/output paths.

    ``FOREGROUND_MASKING_PC`` remains available as an explicit environment
    override.  If the supplied path is already inside one of the configured
    research folders that folder wins; otherwise the host name and visible
    Dropbox roots are used.  Desktop is the tie-breaker because it is the main
    working machine.
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
        if root.exists() and _path_is_within(reference, root.resolve()):
            return pc_name

    available = [name for name, root in PC_RESEARCH_FOLDERS.items() if root.exists()]
    if len(available) == 1:
        return available[0]
    if "Desktop" in available:
        return "Desktop"
    if "Laptop" in available:
        return "Laptop"
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
