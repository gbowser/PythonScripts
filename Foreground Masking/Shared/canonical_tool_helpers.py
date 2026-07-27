"""Helpers for canonical foreground-masking entry-point wrappers."""

from __future__ import annotations

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from machine_paths import detect_pc, remove_foreground_folder


BEST_JSON_PATTERNS = {
    ("spike_gate", "SEP"): ("sep spike optimisation", "sep_spike_optimisation_best.json"),
    ("toy_objects", "SEP"): ("sep toy optimisation", "sep_toy_object_optimisation_best.json"),
    ("spike_gate", "MTObjects"): ("mtobjects spike optimisation", "mtobjects_spike_optimisation_best.json"),
    ("toy_objects", "MTObjects"): ("mtobjects toy optimisation", "mtobjects_parameter_optimisation_best.json"),
}


def latest_best_json(pc_name: str, method: str, technique: str) -> Path | None:
    folder, filename = BEST_JSON_PATTERNS[(method, technique)]
    root = remove_foreground_folder(pc_name)
    candidates = sorted(
        [path for path in (root / folder).glob(f"*/{filename}") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def insert_best_json_arg(argv: list[str], best_json: Path | None) -> None:
    if best_json is None or "--best-json" in argv or "--params-json" in argv:
        return
    argv[1:1] = ["--best-json", str(best_json)]


def pc_from_argv(argv: list[str]) -> str:
    for index, value in enumerate(argv):
        if value == "--pc" and index + 1 < len(argv):
            return argv[index + 1]
        if value.startswith("--pc="):
            return value.split("=", 1)[1]
    return detect_pc(FOREGROUND_ROOT)


def insert_detected_pc_arg(argv: list[str]) -> str:
    """Add the detected ``--pc`` argument unless the caller supplied one."""
    pc_name = pc_from_argv(argv)
    if not any(value == "--pc" or value.startswith("--pc=") for value in argv[1:]):
        argv[1:1] = ["--pc", pc_name]
    return pc_name
