#!/usr/bin/env python3
"""Email when Photutils optimiser CSVs have reached the Desktop output folder."""

from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path

import win32com.client


EXPECTED_FILES = (
    "photutils_parameter_optimisation_summary.csv",
    "photutils_parameter_optimisation_details.csv",
)


def wait_for_files(output_dir: Path, timeout_minutes: float, poll_seconds: float) -> list[Path]:
    deadline = time.monotonic() + timeout_minutes * 60.0
    expected = [output_dir / name for name in EXPECTED_FILES]

    while time.monotonic() < deadline:
        present = [path for path in expected if path.exists() and path.stat().st_size > 0]
        if len(present) == len(expected):
            return present
        time.sleep(poll_seconds)

    missing = [str(path) for path in expected if not path.exists() or path.stat().st_size <= 0]
    raise TimeoutError(f"Timed out waiting for optimiser output files: {missing}")


def send_email(recipient: str, output_dir: Path, files: list[Path]) -> None:
    outlook = win32com.client.Dispatch("Outlook.Application")
    message = outlook.CreateItem(0)
    message.To = recipient
    message.Subject = "Photutils optimiser output transferred"
    file_lines = "\n".join(
        f"- {path.name} ({path.stat().st_size:,} bytes, modified {datetime.fromtimestamp(path.stat().st_mtime):%Y-%m-%d %H:%M:%S})"
        for path in files
    )
    message.Body = (
        "The Photutils optimiser output files have been transferred to the Desktop Dropbox output folder.\n\n"
        f"Output folder:\n{output_dir}\n\n"
        f"Files:\n{file_lines}\n"
    )
    message.Send()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send an Outlook email when optimiser outputs are present.")
    parser.add_argument("--recipient", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout-minutes", type=float, default=240.0)
    parser.add_argument("--poll-seconds", type=float, default=15.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    files = wait_for_files(args.output_dir, args.timeout_minutes, args.poll_seconds)
    send_email(args.recipient, args.output_dir, files)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
