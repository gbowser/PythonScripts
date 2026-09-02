#!/usr/bin/env python3
"""Conservative watchdog for the resumable Haigh-aligned CV batch."""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import time


RUN_ROOT = Path(
    "/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/"
    "clean22_haigh_aligned_source_optimisation"
)
RUN_LOG = RUN_ROOT / "haigh_aligned_cross_validation.log"
WATCH_LOG = RUN_ROOT / "haigh_aligned_watchdog.log"
WATCH_STATE = RUN_ROOT / "haigh_aligned_watchdog_state.json"
WATCH_PID = RUN_ROOT / "haigh_aligned_watchdog.pid"
MTO_REJECTED = RUN_ROOT / "MTObjects_cross_validation" / "mtobjects_toy_cross_validation_rejected.json"
LAUNCHER = Path(
    "/mnt/c/Users/gordo/Documents/Github/PythonScripts/Foreground Masking/"
    "Optimisation/launch_haigh_aligned_16_workers.sh"
)
ROOT_MARKER = "run_haigh_aligned_clean22_cross_validation.py"
COMPLETE_MARKER = "Revised optimisation completed; no 182-galaxy deployment was started."
POLL_SECONDS = 60
HALT_SECONDS = 30 * 60
MAX_RESTARTS = 5


def log(message: str) -> None:
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    line = f"[{stamp}] {message}"
    with WATCH_LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line, flush=True)


def proc_cmdline(pid: int) -> str:
    try:
        data = Path(f"/proc/{pid}/cmdline").read_bytes()
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return ""
    return data.replace(b"\0", b" ").decode("utf-8", errors="replace")


def find_root_pid() -> int | None:
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid == os.getpid():
            continue
        command = proc_cmdline(pid)
        if ROOT_MARKER in command and "watch_haigh_aligned_batch.py" not in command:
            return pid
    return None


def proc_stat(pid: int) -> tuple[int, int] | None:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
        return int(fields[3]), int(fields[13]) + int(fields[14])
    except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError, IndexError):
        return None


def process_tree(root_pid: int) -> dict[int, int]:
    stats: dict[int, tuple[int, int]] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        stat = proc_stat(pid)
        if stat is not None:
            stats[pid] = stat
    selected = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, (ppid, _ticks) in stats.items():
            if ppid in selected and pid not in selected:
                selected.add(pid)
                changed = True
    return {pid: stats[pid][1] for pid in selected if pid in stats}


def completed() -> bool:
    if not RUN_LOG.exists():
        return False
    try:
        with RUN_LOG.open("rb") as handle:
            handle.seek(max(0, RUN_LOG.stat().st_size - 16_384))
            tail = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return False
    return COMPLETE_MARKER in tail


def launch() -> None:
    result = subprocess.run(
        ["bash", str(LAUNCHER)],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(
            f"Launcher failed ({result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    log(result.stdout.strip())


def terminate_tree(root_pid: int) -> None:
    tree = process_tree(root_pid)
    ordered = sorted(tree, reverse=True)
    for pid in ordered:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if find_root_pid() is None:
            return
        time.sleep(1)
    for pid in ordered:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def save_state(**payload: object) -> None:
    WATCH_STATE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    WATCH_PID.write_text(f"{os.getpid()}\n", encoding="utf-8")
    log(
        "Watchdog started: restart missing process; restart only after 30 minutes "
        "with neither log activity nor measurable process-tree CPU activity."
    )
    restarts = 0
    previous_cpu: dict[int, int] = {}
    previous_log_mtime_ns = RUN_LOG.stat().st_mtime_ns if RUN_LOG.exists() else 0
    last_progress = time.monotonic()

    while True:
        if completed():
            log("Batch completion marker found; watchdog exiting normally.")
            save_state(status="complete", restarts=restarts)
            return 0

        root_pid = find_root_pid()
        if root_pid is None:
            if MTO_REJECTED.exists():
                log("MTObjects completed with a scientific feasibility rejection; not restarting the batch.")
                save_state(status="scientific_rejection", restarts=restarts, result=str(MTO_REJECTED))
                return 0
            if restarts >= MAX_RESTARTS:
                log(f"Restart limit ({MAX_RESTARTS}) reached; manual inspection required.")
                save_state(status="restart_limit", restarts=restarts)
                return 2
            restarts += 1
            log(f"Batch process is absent; starting resumable run (restart {restarts}/{MAX_RESTARTS}).")
            try:
                launch()
            except Exception as exc:  # noqa: BLE001
                log(f"Restart failed: {type(exc).__name__}: {exc}")
            previous_cpu = {}
            last_progress = time.monotonic()
            time.sleep(POLL_SECONDS)
            continue

        current_cpu = process_tree(root_pid)
        cpu_delta = sum(
            max(0, ticks - previous_cpu.get(pid, ticks))
            for pid, ticks in current_cpu.items()
        )
        previous_cpu = current_cpu
        log_mtime_ns = RUN_LOG.stat().st_mtime_ns if RUN_LOG.exists() else 0
        log_changed = log_mtime_ns != previous_log_mtime_ns
        previous_log_mtime_ns = log_mtime_ns
        if log_changed or cpu_delta >= 25:
            last_progress = time.monotonic()

        idle_seconds = time.monotonic() - last_progress
        save_state(
            status="running",
            root_pid=root_pid,
            process_count=len(current_cpu),
            cpu_tick_delta=cpu_delta,
            seconds_without_log_or_cpu_progress=round(idle_seconds, 1),
            restarts=restarts,
            checked_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        if idle_seconds >= HALT_SECONDS:
            if restarts >= MAX_RESTARTS:
                log("Genuine halt suspected, but restart limit reached; manual inspection required.")
                save_state(status="halt_restart_limit", restarts=restarts)
                return 3
            restarts += 1
            log(
                f"No log or CPU progress for {HALT_SECONDS // 60} minutes; "
                f"restarting resumable process (restart {restarts}/{MAX_RESTARTS})."
            )
            terminate_tree(root_pid)
            time.sleep(5)
            try:
                launch()
            except Exception as exc:  # noqa: BLE001
                log(f"Restart after halt failed: {type(exc).__name__}: {exc}")
            previous_cpu = {}
            last_progress = time.monotonic()

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
