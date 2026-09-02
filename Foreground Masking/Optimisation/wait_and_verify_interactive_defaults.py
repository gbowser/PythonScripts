#!/usr/bin/env python3
"""Wait for both CV winners, then verify the interactive tool's default sources."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import time


RUN_ROOT = Path(
    "/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/"
    "clean22_haigh_aligned_bright150_optimisation"
)
SEP_PATH = RUN_ROOT / "SEP_cross_validation" / "sep_toy_cross_validation_best.json"
MTO_PATH = RUN_ROOT / "MTObjects_cross_validation" / "mtobjects_toy_cross_validation_best.json"
SEP_REJECTED = RUN_ROOT / "SEP_cross_validation" / "sep_toy_cross_validation_rejected.json"
MTO_REJECTED = RUN_ROOT / "MTObjects_cross_validation" / "mtobjects_toy_cross_validation_rejected.json"
RECORD_PATH = RUN_ROOT / "interactive_default_parameter_sources.json"
LOG_PATH = RUN_ROOT / "interactive_default_parameter_sync.log"
EXPECTED_METRIC = "paired-toy-metrics-displayed-frame-v2"
SEP_KEYS = {
    "detect_on", "detect_thresh", "minarea", "deblend_nthresh", "deblend_cont",
    "back_size", "filter_size", "dilation_radius", "max_area", "max_elongation",
    "exclude_center_pixels",
}
MTO_KEYS = {
    "detect_on", "alpha", "move_factor", "min_distance", "gaussian_fwhm",
    "soft_bias", "gain", "bg_mean", "bg_variance", "minarea", "dilation_radius",
    "max_area", "max_elongation", "exclude_center_pixels",
}


def log(message: str) -> None:
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    line = f"[{stamp}] {message}"
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line, flush=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_and_validate(path: Path, algorithm: str, required: set[str]) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("metric_version") != EXPECTED_METRIC:
        raise ValueError(
            f"{algorithm} metric version is {payload.get('metric_version')!r}; "
            f"expected {EXPECTED_METRIC!r}"
        )
    params = payload.get("params")
    if not isinstance(params, dict):
        raise ValueError(f"{algorithm} winner has no parameter dictionary")
    missing = sorted(required - set(params))
    if missing:
        raise ValueError(f"{algorithm} winner is missing parameters: {', '.join(missing)}")
    if "winning_fold" not in payload:
        raise ValueError(f"{algorithm} file is not a completed cross-validation winner")
    return payload


def main() -> int:
    log("Waiting for completed SEP and MTObjects cross-validation winners.")
    while not (SEP_PATH.is_file() and MTO_PATH.is_file()):
        if SEP_REJECTED.is_file() or MTO_REJECTED.is_file():
            rejected = SEP_REJECTED if SEP_REJECTED.is_file() else MTO_REJECTED
            record = {
                "status": "not_activated",
                "reason": "A required optimisation ended in scientific feasibility rejection.",
                "rejection_file": str(rejected),
                "verified_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
            RECORD_PATH.write_text(json.dumps(record, indent=2), encoding="utf-8")
            log(f"Interactive defaults were not changed because optimisation was rejected: {rejected}")
            return 2
        time.sleep(60)

    try:
        sep = load_and_validate(SEP_PATH, "SEP", SEP_KEYS)
        mto = load_and_validate(MTO_PATH, "MTObjects", MTO_KEYS)
    except Exception as exc:  # noqa: BLE001
        log(f"Winner validation failed: {type(exc).__name__}: {exc}")
        return 2

    record = {
        "status": "ready",
        "verified_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "metric_version": EXPECTED_METRIC,
        "interactive_tool": (
            "/mnt/c/Users/gordo/Documents/Github/PythonScripts/Foreground Masking/"
            "Interactive tools/interactive_toy_objects_SEP_MTObjects.py"
        ),
        "interactive_optimisation_directory": RUN_ROOT.name,
        "SEP": {
            "winner_path": str(SEP_PATH),
            "sha256": sha256(SEP_PATH),
            "winning_fold": sep["winning_fold"],
            "params": sep["params"],
        },
        "MTObjects": {
            "winner_path": str(MTO_PATH),
            "sha256": sha256(MTO_PATH),
            "winning_fold": mto["winning_fold"],
            "params": mto["params"],
        },
        "usage": (
            "These winner files are the interactive tool defaults on its next launch. "
            "In an already-open window, use 'Reload current optimum'."
        ),
    }
    RECORD_PATH.write_text(json.dumps(record, indent=2), encoding="utf-8")
    log(
        f"Interactive defaults verified: SEP fold {sep['winning_fold']}; "
        f"MTObjects fold {mto['winning_fold']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
