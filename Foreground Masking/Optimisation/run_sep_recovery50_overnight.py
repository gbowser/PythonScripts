#!/usr/bin/env python3
"""Queue, resume and post-audit the recovery-constrained SEP experiment."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import time


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
RUN_ROOT = Path(
    "/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/"
    "clean22_haigh_aligned_source_optimisation"
)
OUTPUT = RUN_ROOT / "SEP_recovery50_cross_validation"
STUDIES = Path("/root/haigh-aligned-v1-optuna-studies/SEP_recovery50")
LOG = RUN_ROOT / "sep_recovery50_overnight.log"
STATUS = RUN_ROOT / "sep_recovery50_overnight_status.json"
CURRENT_MTO_WINNER = RUN_ROOT / "MTObjects_cross_validation/mtobjects_toy_cross_validation_best.json"
CURRENT_MTO_REJECTED = RUN_ROOT / "MTObjects_cross_validation/mtobjects_toy_cross_validation_rejected.json"
SEP_WINNER = OUTPUT / "sep_toy_cross_validation_best.json"
SEP_REJECTED = OUTPUT / "sep_toy_cross_validation_rejected.json"


def log(message: str) -> None:
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    line = f"[{stamp}] {message}"
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line, flush=True)


def current_batch_running() -> bool:
    marker = "run_haigh_aligned_clean22_cross_validation.py"
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except (OSError, PermissionError):
            continue
        if marker in command:
            return True
    return False


def write_status(status: str, **extra: object) -> None:
    STATUS.write_text(json.dumps({
        "status": status,
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        **extra,
    }, indent=2), encoding="utf-8")


def run_logged(command: list[str]) -> int:
    with LOG.open("a", encoding="utf-8") as handle:
        completed = subprocess.run(command, cwd=PROJECT_ROOT, stdout=handle, stderr=subprocess.STDOUT, check=False)
    return completed.returncode


def postprocess(result_json: Path) -> None:
    audit_dir = OUTPUT / "parameter_stability_audit"
    run_logged([
        sys.executable, str(SCRIPT_DIR / "audit_optuna_parameter_stability.py"),
        "--study-root", str(STUDIES), "--output-dir", str(audit_dir),
        "--minimum-trials", "40", "--patience", "20",
    ])
    run_logged([
        sys.executable, str(SCRIPT_DIR / "evaluate_sep_source_type_recovery.py"),
        "--manifest", "Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv",
        "--clean-list", "Foreground Masking/Optimisation/clean_galaxies_revised22.txt",
        "--injection-manifest", str(RUN_ROOT / "paired_injections/paired_toy_injection_manifest.json"),
        "--result-json", str(result_json), "--output-dir", str(OUTPUT / "source_type_audit"),
    ])


def main() -> int:
    log("Queued recovery-constrained SEP run; waiting for the active SEP/MTObjects batch to end.")
    write_status("waiting_for_current_batch")
    while current_batch_running() or not (CURRENT_MTO_WINNER.exists() or CURRENT_MTO_REJECTED.exists()):
        time.sleep(60)

    command = [
        sys.executable, str(SCRIPT_DIR / "cross_validate_toy_objects_SEP.py"),
        "--clean-list", "Foreground Masking/Optimisation/clean_galaxies_revised22.txt",
        "--manifest", "Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv",
        "--pc", "Desktop",
        "--injection-manifest", str(RUN_ROOT / "paired_injections/paired_toy_injection_manifest.json"),
        "--cv-injection-sets", "training_seed_1", "training_seed_2", "training_seed_3",
        "--evaluation-injection-sets", "validation_seed_1", "validation_seed_2",
        "--workers", "16", "--initial-points", "8", "--max-iter", "72",
        "--toys-per-image", "5",
        "--convergence-min-trials", "40", "--convergence-patience", "20",
        "--convergence-relative-tolerance", "0.001", "--convergence-absolute-tolerance", "1e-5",
        "--output-dir", str(OUTPUT), "--study-storage-dir", str(STUDIES),
        "--min-toy-detection-rate", "0.50", "--min-mean-toy-recall", "0.30",
        "--pixel-recall-weight", "0.25", "--f-score-weight", "0.30",
        "--toy-recall-weight", "0.25", "--toy-detection-weight", "0.20",
        "--data-loss-penalty", "0.50", "--false-positive-penalty", "0.25",
        "--max-masked-fraction", "0.15", "--require-final-feasible",
    ]
    for attempt in range(1, 6):
        log(f"Starting/resuming recovery-constrained SEP cross-validation (attempt {attempt}/5).")
        write_status("running", attempt=attempt)
        returncode = run_logged(command)
        if SEP_WINNER.exists():
            log("Recovery-constrained SEP produced an accepted winner; running stability and source-type audits.")
            postprocess(SEP_WINNER)
            write_status("complete", result=str(SEP_WINNER))
            log("SEP recovery50 experiment complete and accepted.")
            return 0
        if SEP_REJECTED.exists():
            log("SEP completed but no candidate met the recovery constraints; auditing the best rejected candidate.")
            postprocess(SEP_REJECTED)
            write_status("rejected", result=str(SEP_REJECTED))
            return 2
        log(f"SEP process stopped with exit code {returncode}; studies are resumable. Retrying in 60 seconds.")
        time.sleep(60)
    write_status("restart_limit")
    log("SEP recovery50 restart limit reached; manual diagnosis required.")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
