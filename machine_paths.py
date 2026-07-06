"""Machine-specific local path defaults used by project scripts."""

from __future__ import annotations

from pathlib import Path


PC_RESEARCH_FOLDERS = {
    "Laptop": Path(r"C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research"),
    "Desktop": Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research"),
}


def research_folder(pc_name: str) -> Path:
    return PC_RESEARCH_FOLDERS[pc_name]


def erwin_folder(pc_name: str) -> Path:
    return research_folder(pc_name) / "Erwin"


def shoulder_folder(pc_name: str) -> Path:
    return research_folder(pc_name) / "Shoulder_Recognition_Erwin"


def remove_foreground_folder(pc_name: str) -> Path:
    return research_folder(pc_name) / "Remove foreground objects"
