#!/usr/bin/env python3
"""Write per-galaxy constrained Spike Gate diagnostics for a selected model."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT, ROOT / "Optimisation", ROOT / "Shared", ROOT / "Interactive tools", ROOT / "Batch tools"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))

import optimise_spike_gate_SEP as sep_opt  # noqa: E402
import optimise_spike_gate_MTObjects as mto_opt  # noqa: E402


def config_namespace(module, names=None):
    tool = module.sep_tool if module is sep_opt else module.mto
    values = {
        "manifest": tool.DEFAULT_MANIFEST,
        "pc": "Desktop",
        "names": names,
        "max_images": 182,
        "seed": 20260719,
        "require_spikes": False,
        "spike_gate_detect_on": "residual",
        "profile_width_pixels": tool.DEFAULT_PROFILE_WIDTH_PIXELS,
        "spike_excess_fraction": tool.DEFAULT_SPIKE_EXCESS_FRACTION,
        "spike_neighbour_inner_arcsec": tool.DEFAULT_SPIKE_NEIGHBOUR_INNER_ARCSEC,
        "spike_neighbour_outer_arcsec": tool.DEFAULT_SPIKE_NEIGHBOUR_OUTER_ARCSEC,
        "spike_side_offset_samples": tool.DEFAULT_SPIKE_SIDE_OFFSET_SAMPLES,
        "spike_side_drop_fraction": tool.DEFAULT_SPIKE_SIDE_DROP_FRACTION,
        "spike_center_exclusion_arcsec": tool.DEFAULT_EXCLUDE_CENTER_PIXELS,
        "spike_window_samples": tool.DEFAULT_SPIKE_WINDOW_SAMPLES,
        "mtobjects_root": Path(tool.DEFAULT_MTOBJECTS_ROOT) if module is mto_opt and tool.DEFAULT_MTOBJECTS_ROOT else None,
    }
    return SimpleNamespace(**values)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--algorithm", choices=["SEP", "MTObjects"], required=True)
    parser.add_argument("--best-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    module = sep_opt if args.algorithm == "SEP" else mto_opt
    params = json.loads(args.best_json.read_text(encoding="utf-8"))["params"]
    ns = config_namespace(module)
    cases = module.build_cases(ns)
    rows = []
    started = time.perf_counter()
    for index, case in enumerate(cases, start=1):
        if module is sep_opt:
            row = module.score_case(case, params, 3)
        else:
            row = module.score_case(case, params, ns.mtobjects_root, 3)
        rows.append(row)
        elapsed = time.perf_counter() - started
        remaining = len(cases) - index
        eta = elapsed / index * remaining
        print(
            f"[{index}/{len(cases)}] {case.name}: masked={float(row['masked_fraction']):.3%} "
            f"gate_recovery={float(row['gate_recovery']):.3f} excess={float(row['excess_mask_fraction']):.3%} "
            f"ETA={eta/60:.1f}m",
            flush=True,
        )
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    summary = module.gate_objective.aggregate_constrained(rows)
    args.output_csv.with_suffix(".json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Diagnostics: {args.output_csv}", flush=True)


if __name__ == "__main__":
    main()
