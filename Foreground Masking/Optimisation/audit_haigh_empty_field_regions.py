#!/usr/bin/env python3
"""Audit empty-field placement area and proposed source counts for clean galaxies."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import zlib

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
for folder in (PROJECT_ROOT, FOREGROUND_ROOT, SCRIPT_DIR, FOREGROUND_ROOT / "Shared"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import haigh_aligned_injections as physical  # noqa: E402
import optimise_toy_objects_SEP as sep_opt  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean-list", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--pc", choices=("Desktop", "Laptop"), default="Desktop")
    parser.add_argument("--pixels-per-source", type=int, default=5000)
    parser.add_argument("--maximum-sources", type=int, default=5)
    parser.add_argument("--structure-sigma", type=float, default=1.5)
    parser.add_argument("--compact-sigma", type=float, default=3.0)
    parser.add_argument("--clearance-arcsec", type=float, default=5.0)
    parser.add_argument("--placement-seed", type=int, default=202608611)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    names = [
        value.strip()
        for value in args.clean_list.read_text(encoding="utf-8-sig").splitlines()
        if value.strip() and not value.lstrip().startswith("#")
    ]
    rows = sep_opt.select_rows(args.source_manifest, args.pc, names, len(names), 1)
    fractions: list[float] = []
    counts: list[int] = []
    placed_counts: list[int] = []
    for row in sorted(rows, key=lambda value: value["name"]):
        geometry = sep_opt.sep_tool.display.required_geometry(row)
        if geometry is None:
            raise ValueError(f"{row['name']}: incomplete geometry")
        path = Path(sep_opt.sep_tool.display.image_path_for_pc(row, args.pc))
        data, _header = sep_opt.sep_tool.load_fits(path)
        displayed = sep_opt.investigated_region_mask(data, geometry)
        quiet, allowed_truth, metadata = physical.quiet_placement_region(
            data,
            displayed,
            geometry,
            structure_sigma=args.structure_sigma,
            compact_sigma=args.compact_sigma,
            clearance_arcsec=args.clearance_arcsec,
        )
        count = physical.source_count_for_region(
            int(np.count_nonzero(quiet)), args.pixels_per_source,
            maximum=args.maximum_sources,
        )
        fraction = float(metadata["eligible_fraction"])
        per_galaxy_seed = (args.placement_seed + zlib.crc32(row["name"].casefold().encode("utf-8"))) & 0xFFFFFFFF
        _injected, _truth, _labels, sources = physical.inject_sources(
            row["name"], data, geometry, displayed, np.random.default_rng(per_galaxy_seed),
            requested_count=count, pixels_per_source=args.pixels_per_source,
            maximum_sources=args.maximum_sources, placement_region=quiet,
            allowed_truth_region=allowed_truth,
        )
        fractions.append(fraction)
        counts.append(count)
        placed_counts.append(len(sources))
        print(
            f"{row['name']:<10} displayed={np.count_nonzero(displayed):>7} "
            f"quiet={np.count_nonzero(quiet):>7} ({fraction:>6.1%}) "
            f"sources={len(sources)}/{count}"
        )
    print(
        f"Summary: quiet fraction {min(fractions):.1%}--{max(fractions):.1%}; "
        f"source counts {min(counts)}--{max(counts)}; requested={sum(counts)}, "
        f"placed={sum(placed_counts)}, fallbacks={sum(a < b for a, b in zip(placed_counts, counts))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
