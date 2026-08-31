#!/usr/bin/env python3
"""Generate immutable displayed-frame toy sets for multi-seed optimisation."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import generate_paired_toy_manifest as generator


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean-list", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pc", default="Desktop")
    parser.add_argument("--training-seeds", type=int, nargs=3, required=True)
    parser.add_argument("--validation-seeds", type=int, nargs=2, required=True)
    parser.add_argument("--toys-per-image", type=int, default=5)
    parser.add_argument("--truth-dilation", type=int, default=1)
    parser.add_argument("--toy-peak-sigma-min", type=float, default=6.0)
    parser.add_argument("--toy-peak-sigma-max", type=float, default=30.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "paired_toy_injection_manifest.json"
    all_seeds = list(args.training_seeds) + list(args.validation_seeds)
    if manifest_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("all_seeds") != all_seeds:
            raise ValueError("Existing immutable manifest uses different seeds; choose a new output directory.")
        print(f"Reusing immutable multi-seed manifest: {manifest_path}", flush=True)
        return 0

    names = generator.read_names(args.clean_list)
    build_args = SimpleNamespace(
        source_manifest=args.source_manifest,
        pc=args.pc,
        toys_per_image=args.toys_per_image,
        truth_dilation=args.truth_dilation,
        toy_peak_sigma_min=args.toy_peak_sigma_min,
        toy_peak_sigma_max=args.toy_peak_sigma_max,
    )
    manifest: dict[str, object] = {
        "schema_version": "paired-toy-injections-displayed-frame-v2",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "immutable_after_generation": True,
        "purpose": "Multi-seed MTObjects optimisation pilot with untouched validation positions",
        "source_manifest": str(args.source_manifest.resolve()),
        "clean_list": str(args.clean_list.resolve()),
        "training_seeds": list(args.training_seeds),
        "validation_seeds": list(args.validation_seeds),
        "all_seeds": all_seeds,
        "toy_configuration": {
            "toys_per_image": args.toys_per_image,
            "truth_dilation": args.truth_dilation,
            "peak_sigma_min": args.toy_peak_sigma_min,
            "peak_sigma_max": args.toy_peak_sigma_max,
            "placement_area": "finite pixels in the displayed deprojected centred square",
        },
        "injection_sets": {},
    }
    sets = manifest["injection_sets"]
    assert isinstance(sets, dict)
    for index, seed in enumerate(args.training_seeds, start=1):
        set_name = f"training_seed_{index}"
        sets[set_name] = generator.build_set(build_args, set_name, seed, names, args.output_dir)
    for index, seed in enumerate(args.validation_seeds, start=1):
        set_name = f"validation_seed_{index}"
        sets[set_name] = generator.build_set(build_args, set_name, seed, names, args.output_dir)

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    checksum_path = args.output_dir / "paired_toy_injection_manifest.sha256"
    checksum_path.write_text(f"{sha256_file(manifest_path)}  {manifest_path.name}\n", encoding="ascii")
    manifest_path.chmod(0o444)
    print(f"Immutable multi-seed manifest: {manifest_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
