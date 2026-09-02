#!/usr/bin/env python3
"""Conservative watchdog for the queued MTObjects galaxy-size experiment."""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path("/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_haigh_aligned_bright150_galaxy150_sep_sensitivity")
LOG = ROOT / "mto_galaxy150_cross_validation.log"
STATE = ROOT / "mto_galaxy150_watchdog_state.json"
WATCH_LOG = ROOT / "mto_galaxy150_watchdog.log"
WINNER = ROOT / "MTObjects_cross_validation/mtobjects_toy_cross_validation_best.json"
REJECTED = ROOT / "MTObjects_cross_validation/mtobjects_toy_cross_validation_rejected.json"
LAUNCHER = Path("/mnt/c/Users/gordo/Documents/Github/PythonScripts/Foreground Masking/Optimisation/launch_mto_bright150_galaxy150_16_workers.sh")
MARKERS = ("cross_validate_toy_objects_MTObjects.py", "bright150_galaxy150_sep_sensitivity")
POLL, HALT, MAX_RESTARTS = 60, 30 * 60, 5


def now() -> str: return datetime.now().astimezone().isoformat(timespec="seconds")
def note(message: str) -> None:
    line = f"[{now()}] {message}"
    with WATCH_LOG.open("a", encoding="utf-8") as handle: handle.write(line + "\n")
    print(line, flush=True)
def cmd(pid: int) -> str:
    try: return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
    except OSError: return ""
def find_pid() -> int | None:
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit() and all(marker in cmd(int(entry.name)) for marker in MARKERS): return int(entry.name)
    return None
def proc_stat(pid: int) -> tuple[int, int] | None:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().split(); return int(fields[3]), int(fields[13]) + int(fields[14])
    except (OSError, ValueError, IndexError): return None
def tree(pid: int) -> dict[int, int]:
    stats = {}
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit() and (item := proc_stat(int(entry.name))) is not None: stats[int(entry.name)] = item
    selected = {pid}; changed = True
    while changed:
        changed = False
        for child, (parent, _ticks) in stats.items():
            if parent in selected and child not in selected: selected.add(child); changed = True
    return {item: stats[item][1] for item in selected if item in stats}
def save(**payload: object) -> None: STATE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
def launch() -> None:
    result = subprocess.run(["bash", str(LAUNCHER)], text=True, capture_output=True, check=False)
    if result.returncode: raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    note(result.stdout.strip())
def stop(pid: int) -> None:
    pids = sorted(tree(pid), reverse=True)
    for item in pids:
        try: os.kill(item, signal.SIGTERM)
        except ProcessLookupError: pass
    time.sleep(20)
    for item in pids:
        try: os.kill(item, signal.SIGKILL)
        except ProcessLookupError: pass


def main() -> int:
    note("MTObjects galaxy-size watchdog started; 30-minute no-log-and-no-CPU threshold.")
    restarts = 0; previous: dict[int, int] = {}; last_progress = time.monotonic()
    previous_mtime = LOG.stat().st_mtime_ns if LOG.exists() else 0
    while True:
        if WINNER.exists() or REJECTED.exists():
            outcome = "accepted" if WINNER.exists() else "scientific_rejection"
            save(status=outcome, result=str(WINNER if WINNER.exists() else REJECTED), restarts=restarts)
            note(f"Terminal scientific outcome: {outcome}."); return 0
        pid = find_pid()
        if pid is None:
            if restarts >= MAX_RESTARTS: save(status="restart_limit", restarts=restarts); return 3
            restarts += 1; note(f"Process absent; resumable restart {restarts}/{MAX_RESTARTS}."); launch()
            previous = {}; last_progress = time.monotonic(); time.sleep(POLL); continue
        current = tree(pid); delta = sum(max(0, ticks - previous.get(item, ticks)) for item, ticks in current.items()); previous = current
        mtime = LOG.stat().st_mtime_ns if LOG.exists() else 0
        if mtime != previous_mtime or delta >= 25: last_progress = time.monotonic()
        previous_mtime = mtime; idle = time.monotonic() - last_progress
        save(status="running", root_pid=pid, process_count=len(current), cpu_tick_delta=delta,
             seconds_without_log_or_cpu_progress=round(idle, 1), restarts=restarts, checked_at=now())
        if idle >= HALT:
            restarts += 1; note(f"Halt suspected; restart {restarts}/{MAX_RESTARTS}."); stop(pid); time.sleep(5); launch(); previous = {}; last_progress = time.monotonic()
        time.sleep(POLL)


if __name__ == "__main__": raise SystemExit(main())
