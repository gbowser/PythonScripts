#!/usr/bin/env python3
"""Create the final cleanest-20 CSV from blind contamination-severity scores."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


GROUP_PRIORITY = {"Clean": 0, "Ambiguous": 1, "Polluted-shortlist": 2}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=20)
    args = parser.parse_args()
    with args.decisions.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if any(row.get("severity", "") == "" for row in rows):
        raise ValueError("Every shortlist field must have a severity score")

    def key(row: dict[str, str]) -> tuple[float, int, float, str]:
        margin = float(row["clean_similarity_margin"]) if row.get("clean_similarity_margin") else float("-inf")
        return (
            float(row["severity"]),
            GROUP_PRIORITY.get(row["input_group"], 99),
            -margin,
            row["name"],
        )

    ranked = sorted(rows, key=key)
    boundary_severity = int(ranked[args.count - 1]["severity"])
    fields = [
        "final_rank", "name", "severity", "prior_blind_group", "selected_top20",
        "selection_basis", "clean_similarity_margin", "notes",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for rank, row in enumerate(ranked, start=1):
            if int(row["severity"]) < boundary_severity:
                basis = "lower visual severity"
            elif int(row["severity"]) == boundary_severity:
                basis = "boundary tie: prior blind group, then clean-reference similarity"
            else:
                basis = "outside top 20"
            writer.writerow({
                "final_rank": rank,
                "name": row["name"],
                "severity": row["severity"],
                "prior_blind_group": row["input_group"],
                "selected_top20": "yes" if rank <= args.count else "no",
                "selection_basis": basis,
                "clean_similarity_margin": row.get("clean_similarity_margin", ""),
                "notes": row.get("notes", ""),
            })
    print(f"Wrote {len(ranked)} ranked rows; selected {args.count}: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
