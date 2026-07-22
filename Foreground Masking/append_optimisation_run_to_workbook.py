#!/usr/bin/env python3
"""Append one completed optimisation run to the shared results workbook."""

from __future__ import annotations

import argparse
from pathlib import Path

from optimisation_results_workbook import append_run_to_workbook


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--algorithm", required=True, choices=["SEP", "MTObjects"])
    parser.add_argument("--method", required=True, choices=["Spike Gate", "Toy Object"])
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--workbook", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workbook_path = append_run_to_workbook(
        algorithm=args.algorithm,
        method=args.method,
        run_dir=args.run_dir,
        prefix=args.prefix,
        workbook_path=args.workbook,
    )
    print(f"Updated optimisation workbook: {workbook_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
