#!/usr/bin/env python3
"""Generate immutable Haigh-aligned S4G source-injection seed sets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import random
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
from paired_toy_common import SCHEMA_VERSION, sha256_array, sha256_file  # noqa: E402


DEFAULT_TRAINING_SEEDS = (202608611, 202608612, 202608613)
DEFAULT_VALIDATION_SEEDS = (202608621, 202608622)


def read_names(path: Path) -> list[str]:
    names = [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines()]
    names = [name for name in names if name and not name.startswith("#")]
    if len(names) < 2 or len(names) != len(set(names)):
        raise ValueError("The clean list must contain at least two unique galaxy names.")
    return names


def galaxy_seed(global_seed: int, name: str) -> int:
    return (int(global_seed) + zlib.crc32(name.casefold().encode("utf-8"))) & 0xFFFFFFFF


def leave_one_galaxy_out_folds(names: list[str], seed: int) -> dict[str, list[str]]:
    shuffled = list(names)
    random.Random(seed).shuffle(shuffled)
    return {f"fold_{index:02d}": [name] for index, name in enumerate(shuffled, start=1)}


def build_set(args: argparse.Namespace, set_name: str, global_seed: int,
              names: list[str], output: Path) -> dict[str, object]:
    rows = sep_opt.select_rows(args.source_manifest, args.pc, names, len(names), global_seed)
    by_name = {row["name"]: row for row in rows}
    payload_dir = output / "payloads" / set_name
    payload_dir.mkdir(parents=True, exist_ok=True)
    galaxies: dict[str, object] = {}
    for index, name in enumerate(names, start=1):
        row = by_name[name]
        geometry = sep_opt.sep_tool.display.required_geometry(row)
        if geometry is None:
            raise ValueError(f"{name}: incomplete display geometry")
        science_path = Path(sep_opt.sep_tool.display.image_path_for_pc(row, args.pc)).resolve()
        data, _header = sep_opt.sep_tool.load_fits(science_path)
        region = sep_opt.investigated_region_mask(data, geometry)
        placement_region, allowed_truth_region, placement_metadata = physical.quiet_placement_region(
            data,
            region,
            geometry,
            structure_sigma=args.structure_sigma,
            compact_sigma=args.compact_sigma,
            clearance_arcsec=args.clearance_arcsec,
        )
        target_count = physical.source_count_for_region(
            int(np.count_nonzero(placement_region)), args.pixels_per_source,
            maximum=args.maximum_sources,
        )
        per_galaxy_seed = galaxy_seed(global_seed, name)
        injected, truth, labels, sources = physical.inject_sources(
            name, data, geometry, region, np.random.default_rng(per_galaxy_seed),
            requested_count=target_count, maximum_sources=args.maximum_sources,
            pixels_per_source=args.pixels_per_source, galaxy_fraction=args.background_galaxy_fraction,
            peak_sigma_min=args.peak_sigma_min, peak_sigma_max=args.peak_sigma_max,
            truth_sigma=args.truth_sigma, minimum_separation_pixels=args.minimum_separation_pixels,
            placement_region=placement_region, allowed_truth_region=allowed_truth_region,
        )
        delta = np.asarray(injected - data, dtype=np.float32)
        payload_path = (payload_dir / f"{name}.npz").resolve()
        np.savez_compressed(
            payload_path,
            delta=delta,
            truth_mask=truth.astype(np.uint8),
            truth_labels=labels.astype(np.int32),
            placement_region=placement_region.astype(np.uint8),
            allowed_truth_region=allowed_truth_region.astype(np.uint8),
        )
        summary = physical.summarise_sources(sources)
        galaxies[name] = {
            "galaxy_identifier": name,
            "science_image_path": str(science_path),
            "science_image_sha256": sha256_file(science_path),
            "global_seed": global_seed,
            "per_galaxy_seed": per_galaxy_seed,
            "requested_toy_count": target_count,
            "actual_toy_count": len(sources),
            "placement_fallback_used": len(sources) < target_count,
            "payload_path": str(payload_path),
            "payload_sha256": sha256_file(payload_path),
            "delta_sha256": sha256_array(delta),
            "truth_mask_sha256": sha256_array(truth.astype(np.uint8)),
            "truth_pixels": int(np.count_nonzero(truth)),
            "analysis_region_definition": "finite pixels in the displayed deprojected centred square",
            "analysis_region_pixels": int(np.count_nonzero(region)),
            "placement_region": placement_metadata,
            "source_summary": summary,
            "toys": [source.manifest_record() for source in sources],
        }
        payload_path.chmod(0o444)
        print(
            f"[{set_name} {index:02d}/{len(names)}] {name}: {len(sources)}/{target_count} sources "
            f"({summary['foreground_stars']} stars, {summary['background_galaxies']} galaxies)", flush=True,
        )
    return {"global_seed": global_seed, "galaxies": galaxies}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean-list", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pc", choices=("Desktop", "Laptop"), default="Desktop")
    parser.add_argument("--training-seeds", nargs=3, type=int, default=DEFAULT_TRAINING_SEEDS)
    parser.add_argument("--validation-seeds", nargs=2, type=int, default=DEFAULT_VALIDATION_SEEDS)
    parser.add_argument("--fold-seed", type=int, default=202608601)
    parser.add_argument("--maximum-sources", type=int, default=5)
    parser.add_argument("--pixels-per-source", type=int, default=5000)
    parser.add_argument("--background-galaxy-fraction", type=float, default=0.25)
    parser.add_argument("--peak-sigma-min", type=float, default=6.0)
    parser.add_argument("--peak-sigma-max", type=float, default=30.0)
    parser.add_argument("--truth-sigma", type=float, default=1.0)
    parser.add_argument("--minimum-separation-pixels", type=int, default=4)
    parser.add_argument("--structure-sigma", type=float, default=1.5)
    parser.add_argument("--compact-sigma", type=float, default=3.0)
    parser.add_argument("--clearance-arcsec", type=float, default=5.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 0.0 <= args.background_galaxy_fraction <= 1.0:
        raise ValueError("--background-galaxy-fraction must be between zero and one")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "paired_toy_injection_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"Refusing to overwrite immutable manifest: {manifest_path}")
    names = read_names(args.clean_list)
    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "injection_model_version": physical.MODEL_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "immutable_after_generation": True,
        "purpose": "Haigh-aligned S4G foreground-star and background-galaxy masking optimisation",
        "source_manifest": str(args.source_manifest.resolve()),
        "clean_list": str(args.clean_list.resolve()),
        "training_seeds": list(args.training_seeds),
        "validation_seeds": list(args.validation_seeds),
        "fold_seed": args.fold_seed,
        "folds": leave_one_galaxy_out_folds(names, args.fold_seed),
        "source_configuration": {
            "count_rule": "round(eligible quiet-placement pixels / pixels_per_source), clipped to 1..maximum_sources",
            "maximum_sources": args.maximum_sources,
            "pixels_per_source": args.pixels_per_source,
            "foreground_star_fraction": 1.0 - args.background_galaxy_fraction,
            "background_galaxy_fraction": args.background_galaxy_fraction,
            "star_model": "IRAC 3.6 micron PSF approximation: Gaussian core plus 4% broad wing",
            "psf_fwhm_arcsec": physical.IRAC_36_PSF_FWHM_ARCSEC,
            "background_galaxy_model": "PSF-convolved Sersic",
            "background_galaxy_effective_radius_arcsec": [0.5, 3.5],
            "background_galaxy_sersic_index": [2.0, 4.0],
            "background_galaxy_axis_ratio": [0.3, 1.0],
            "cluster_galaxies_in_primary_test": False,
            "peak_sigma": [args.peak_sigma_min, args.peak_sigma_max],
            "truth_sigma_threshold": args.truth_sigma,
            "star_truth": "noise threshold intersected with 95% model flux",
            "galaxy_truth": "model surface brightness >= local-noise threshold",
            "placement_area": "displayed deprojected galaxy area, injected in observed sky pixels",
            "empty_field_placement": {
                "structure_threshold_sigma": args.structure_sigma,
                "compact_source_threshold_sigma": args.compact_sigma,
                "clearance_arcsec": args.clearance_arcsec,
                "principle": (
                    "source centres are restricted to locally quiet areas away from the target galaxy "
                    "and pre-existing compact sources"
                ),
            },
        },
        "injection_sets": {},
    }
    sets = manifest["injection_sets"]
    assert isinstance(sets, dict)
    for index, seed in enumerate(args.training_seeds, start=1):
        sets[f"training_seed_{index}"] = build_set(args, f"training_seed_{index}", seed, names, output)
    for index, seed in enumerate(args.validation_seeds, start=1):
        sets[f"validation_seed_{index}"] = build_set(args, f"validation_seed_{index}", seed, names, output)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    checksum_path = output / "paired_toy_injection_manifest.sha256"
    checksum_path.write_text(f"{sha256_file(manifest_path)}  {manifest_path.name}\n", encoding="ascii")
    manifest_path.chmod(0o444)
    checksum_path.chmod(0o444)
    print(f"Immutable revised manifest: {manifest_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
