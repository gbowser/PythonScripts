#!/usr/bin/env python3
"""Generate immutable, materialised Toy Objects injections shared by SEP and MTObjects."""
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
for path in (PROJECT_ROOT, FOREGROUND_ROOT, SCRIPT_DIR, FOREGROUND_ROOT / "Shared"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import optimise_toy_objects_SEP as sep_opt  # noqa: E402
from paired_toy_common import SCHEMA_VERSION, sha256_array, sha256_file  # noqa: E402


def read_names(path: Path) -> list[str]:
    names = [x.strip() for x in path.read_text(encoding="utf-8-sig").splitlines()]
    names = [x for x in names if x and not x.startswith("#")]
    if len(names) < 2 or len(set(names)) != len(names):
        raise ValueError(f"Expected at least two unique calibration galaxies, found {len(names)} rows and {len(set(names))} unique")
    return names


def folds(names: list[str], seed: int) -> list[list[str]]:
    values = list(names); random.Random(seed).shuffle(values)
    fold_count = 4 if len(values) == 40 else len(values)
    return [sorted(values[index::fold_count]) for index in range(fold_count)]


def galaxy_seed(global_seed: int, name: str) -> int:
    return (int(global_seed) + zlib.crc32(name.casefold().encode("utf-8"))) & 0xFFFFFFFF


def inject_with_fallback(args, name: str, data: np.ndarray, geometry: dict, seed: int):
    """Place paired toys deterministically, relaxing size then count if necessary."""
    requested = int(args.toys_per_image)
    attempts: list[tuple[int, float]] = [
        (requested, 1.0),
        (requested, 0.85),
        (requested, 0.70),
    ]
    attempts.extend((count, 1.0) for count in range(requested - 1, 0, -1))
    last_error: ValueError | None = None
    for toy_count, fwhm_scale in attempts:
        try:
            result = sep_opt.inject_toys(
                name, data, geometry, toys_per_image=toy_count,
                rng=np.random.default_rng(seed), truth_dilation=args.truth_dilation,
                peak_sigma_min=args.toy_peak_sigma_min, peak_sigma_max=args.toy_peak_sigma_max,
                fwhm_scale=fwhm_scale,
            )
            return (*result, toy_count, fwhm_scale)
        except ValueError as error:
            if "could not place toy" not in str(error) and "no injection candidates" not in str(error):
                raise
            last_error = error
    raise ValueError(f"{name}: all adaptive toy-placement attempts failed") from last_error


def build_set(args, set_name: str, global_seed: int, names: list[str], output: Path) -> dict:
    rows = sep_opt.select_rows(args.source_manifest, args.pc, names, len(names), global_seed)
    by_name = {row["name"]: row for row in rows}
    galaxies = {}
    payload_dir = output / "payloads" / set_name
    payload_dir.mkdir(parents=True, exist_ok=True)
    for index, name in enumerate(names, start=1):
        row = by_name[name]
        geometry = sep_opt.sep_tool.display.required_geometry(row)
        image_path = sep_opt.sep_tool.display.image_path_for_pc(row, args.pc)
        data, _ = sep_opt.sep_tool.load_fits(image_path)
        analysis_region = sep_opt.investigated_region_mask(data, geometry)
        seed = galaxy_seed(global_seed, name)
        injected, truth_mask, truth_labels, toys, actual_toy_count, fwhm_scale = inject_with_fallback(
            args, name, data, geometry, seed
        )
        delta = np.asarray(injected - data, dtype=np.float32)
        payload_path = (payload_dir / f"{name}.npz").resolve()
        np.savez_compressed(payload_path, delta=delta, truth_mask=truth_mask.astype(np.uint8), truth_labels=truth_labels)
        sigma = sep_opt.robust_sigma(data)
        toy_rows = []
        for toy in toys:
            record = dict(toy.__dict__)
            record["amplitude_image_units"] = float(toy.peak_sigma * sigma)
            toy_rows.append(record)
        galaxies[name] = {
            "galaxy_identifier": name,
            "science_image_path": str(Path(image_path).resolve()),
            "science_image_sha256": sha256_file(Path(image_path)),
            "global_seed": global_seed,
            "per_galaxy_seed": seed,
            "requested_toy_count": int(args.toys_per_image),
            "actual_toy_count": actual_toy_count,
            "toy_fwhm_scale": fwhm_scale,
            "placement_fallback_used": actual_toy_count != int(args.toys_per_image) or fwhm_scale != 1.0,
            "payload_path": str(payload_path),
            "payload_sha256": sha256_file(payload_path),
            "delta_sha256": sha256_array(delta),
            "truth_mask_sha256": sha256_array(truth_mask.astype(np.uint8)),
            "truth_pixels": int(np.count_nonzero(truth_mask)),
            "analysis_region_definition": "finite pixels in the displayed deprojected centred square",
            "analysis_region_pixels": int(np.count_nonzero(analysis_region)),
            "toys": toy_rows,
        }
        payload_path.chmod(0o444)
        fallback = "" if actual_toy_count == int(args.toys_per_image) and fwhm_scale == 1.0 else f", fallback scale={fwhm_scale:.2f}"
        print(f"[{set_name} {index:02d}/{len(names)}] {name}: seed={seed}, toys={len(toys)}{fallback}", flush=True)
    return {"global_seed": global_seed, "galaxies": galaxies}


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--clean-list", type=Path, required=True); p.add_argument("--source-manifest", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True); p.add_argument("--pc", choices=["Desktop","Laptop"], default="Desktop")
    p.add_argument("--fold-seed", type=int, default=202608150); p.add_argument("--cv-seed", type=int, default=202608299)
    p.add_argument("--selection-seed", type=int, default=202608399); p.add_argument("--toys-per-image", type=int, default=6)
    p.add_argument("--truth-dilation", type=int, default=1); p.add_argument("--toy-peak-sigma-min", type=float, default=6.0)
    p.add_argument("--toy-peak-sigma-max", type=float, default=30.0); args=p.parse_args()
    names=read_names(args.clean_list); args.output_dir.mkdir(parents=True,exist_ok=True)
    manifest={
        "schema_version":SCHEMA_VERSION, "created_utc":datetime.now(timezone.utc).isoformat(),
        "immutable_after_generation":True, "source_manifest":str(args.source_manifest.resolve()),
        "clean_list":str(args.clean_list.resolve()), "fold_seed":args.fold_seed,
        "folds":{f"fold_{i+1}":v for i,v in enumerate(folds(names,args.fold_seed))},
        "toy_configuration":{"toys_per_image":args.toys_per_image,"truth_dilation":args.truth_dilation,
            "peak_sigma_min":args.toy_peak_sigma_min,"peak_sigma_max":args.toy_peak_sigma_max,"brightness_scale_vs_previous":1.2,
            "placement_fallback":"requested count at FWHM scales 1.0, 0.85, 0.70; then progressively fewer toys at original size"},
        "injection_sets":{},
    }
    manifest["injection_sets"]["cross_validation"]=build_set(args,"cross_validation",args.cv_seed,names,args.output_dir)
    manifest["injection_sets"]["winner_selection"]=build_set(args,"winner_selection",args.selection_seed,names,args.output_dir)
    path=args.output_dir/"paired_toy_injection_manifest.json"; path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    checksum_path=args.output_dir/"paired_toy_injection_manifest.sha256"
    checksum_path.write_text(f"{sha256_file(path)}  {path.name}\n",encoding="ascii")
    path.chmod(0o444); checksum_path.chmod(0o444)
    print(f"Immutable paired injection manifest: {path}",flush=True); return 0

if __name__=="__main__": raise SystemExit(main())
