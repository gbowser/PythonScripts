#!/usr/bin/env python3
"""Conservative watchdog for the resumable 150%-brightness CV batch."""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import time


RUN_ROOT = Path("/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_haigh_aligned_bright150_optimisation")
RUN_LOG = RUN_ROOT / "haigh_aligned_bright150_cross_validation.log"
WATCH_LOG = RUN_ROOT / "haigh_aligned_bright150_watchdog.log"
WATCH_STATE = RUN_ROOT / "haigh_aligned_bright150_watchdog_state.json"
WATCH_PID = RUN_ROOT / "haigh_aligned_bright150_watchdog.pid"
LAUNCHER = Path("/mnt/c/Users/gordo/Documents/Github/PythonScripts/Foreground Masking/Optimisation/launch_haigh_aligned_bright150_16_workers.sh")
ROOT_MARKER = "run_haigh_aligned_bright150_cross_validation.py"
COMPLETE_MARKER = "150%-brightness optimisation completed;"
SEP_REJECTED = RUN_ROOT / "SEP_cross_validation/sep_toy_cross_validation_rejected.json"
MTO_REJECTED = RUN_ROOT / "MTObjects_cross_validation/mtobjects_toy_cross_validation_rejected.json"
POLL_SECONDS = 60
HALT_SECONDS = 30 * 60
MAX_RESTARTS = 5


def log(message: str) -> None:
    line = f"[{datetime.now().astimezone().isoformat(timespec='seconds')}] {message}"
    with WATCH_LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line, flush=True)


def cmdline(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
    except (OSError, PermissionError):
        return ""


def find_root_pid() -> int | None:
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit() and ROOT_MARKER in cmdline(int(entry.name)):
            return int(entry.name)
    return None


def proc_stat(pid: int) -> tuple[int, int] | None:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().split()
        return int(fields[3]), int(fields[13]) + int(fields[14])
    except (OSError, ValueError, IndexError):
        return None


def process_tree(root_pid: int) -> dict[int, int]:
    stats = {}
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit() and (stat := proc_stat(int(entry.name))) is not None:
            stats[int(entry.name)] = stat
    selected = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, (ppid, _ticks) in stats.items():
            if ppid in selected and pid not in selected:
                selected.add(pid); changed = True
    return {pid: stats[pid][1] for pid in selected if pid in stats}


def tail_contains(marker: str) -> bool:
    if not RUN_LOG.exists():
        return False
    with RUN_LOG.open("rb") as handle:
        handle.seek(max(0, RUN_LOG.stat().st_size - 16384))
        return marker in handle.read().decode(errors="replace")


def launch() -> None:
    result = subprocess.run(["bash", str(LAUNCHER)], text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    log(result.stdout.strip())


def terminate_tree(root_pid: int) -> None:
    pids = sorted(process_tree(root_pid), reverse=True)
    for pid in pids:
        try: os.kill(pid, signal.SIGTERM)
        except ProcessLookupError: pass
    time.sleep(20)
    for pid in pids:
        try: os.kill(pid, signal.SIGKILL)
        except ProcessLookupError: pass


def save(**payload: object) -> None:
    WATCH_STATE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    WATCH_PID.write_text(f"{os.getpid()}\n", encoding="utf-8")
    log("150%-brightness watchdog started; 30-minute no-log-and-no-CPU halt threshold.")
    restarts = 0
    previous_cpu: dict[int, int] = {}
    previous_mtime = RUN_LOG.stat().st_mtime_ns if RUN_LOG.exists() else 0
    last_progress = time.monotonic()
    while True:
        if tail_contains(COMPLETE_MARKER):
            save(status="complete", restarts=restarts); log("Completion marker found."); return 0
        root_pid = find_root_pid()
        if root_pid is None:
            rejection = SEP_REJECTED if SEP_REJECTED.exists() else (MTO_REJECTED if MTO_REJECTED.exists() else None)
            if rejection is not None:
                save(status="scientific_rejection", result=str(rejection), restarts=restarts)
                log(f"Scientific rejection recorded; not treating it as a crash: {rejection}"); return 2
            if restarts >= MAX_RESTARTS:
                save(status="restart_limit", restarts=restarts); return 3
            restarts += 1; log(f"Process absent; resumable restart {restarts}/{MAX_RESTARTS}.")
            try: launch()
            except Exception as exc: log(f"Restart failed: {exc}")
            previous_cpu = {}; last_progress = time.monotonic(); time.sleep(POLL_SECONDS); continue
        current_cpu = process_tree(root_pid)
        cpu_delta = sum(max(0, ticks - previous_cpu.get(pid, ticks)) for pid, ticks in current_cpu.items())
        previous_cpu = current_cpu
        mtime = RUN_LOG.stat().st_mtime_ns if RUN_LOG.exists() else 0
        if mtime != previous_mtime or cpu_delta >= 25:
            last_progress = time.monotonic()
        previous_mtime = mtime
        idle = time.monotonic() - last_progress
        save(status="running", root_pid=root_pid, process_count=len(current_cpu), cpu_tick_delta=cpu_delta,
             seconds_without_log_or_cpu_progress=round(idle, 1), restarts=restarts,
             checked_at=datetime.now().astimezone().isoformat(timespec="seconds"))
        if idle >= HALT_SECONDS:
            restarts += 1; log(f"Genuine halt suspected; restart {restarts}/{MAX_RESTARTS}.")
            terminate_tree(root_pid); time.sleep(5); launch(); previous_cpu = {}; last_progress = time.monotonic()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
