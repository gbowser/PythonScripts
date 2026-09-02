#!/usr/bin/env python3
"""Clone a Haigh-aligned manifest while scaling only source peak brightness."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
for folder in (PROJECT_ROOT, FOREGROUND_ROOT, SCRIPT_DIR, FOREGROUND_ROOT / "Shared"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import haigh_aligned_injections as physical  # noqa: E402
import optimise_toy_objects_SEP as sep_opt  # noqa: E402
from paired_toy_common import sha256_array, sha256_file  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--brightness-scale", type=float, default=1.5)
    return parser.parse_args()


def model_and_truth(record: dict[str, object], shape: tuple[int, int], noise: float,
                    scale: float) -> tuple[np.ndarray, np.ndarray]:
    peak_sigma = float(record["peak_sigma"]) * scale
    x0, y0 = float(record["x"]), float(record["y"])
    threshold = float(record.get("truth_sigma_threshold", 1.0))
    object_type = str(record["object_type"])
    if object_type == "star":
        model = physical.irac_star_model(
            shape, x0, y0, peak_sigma * noise, float(record["psf_fwhm_pixels"])
        )
        truth = physical.noise_truth(model, noise, threshold, encircled_energy_cap=0.95)
    elif object_type == "galaxy":
        model = physical.background_galaxy_model(
            shape, x0, y0, peak_sigma * noise,
            float(record["effective_radius_pixels"]), float(record["sersic_index"]),
            float(record["axis_ratio"]), float(record["pa_deg"]),
            float(record["psf_fwhm_pixels"]),
        )
        truth = physical.noise_truth(model, noise, threshold)
    else:
        raise ValueError(f"Unsupported object type: {object_type!r}")
    return np.asarray(model, dtype=float), np.asarray(truth, dtype=bool)


def main() -> int:
    args = parse_args()
    if args.brightness_scale <= 0:
        raise ValueError("--brightness-scale must be positive")
    source_path = args.source_manifest.resolve()
    source = json.loads(source_path.read_text(encoding="utf-8-sig"))
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    result = copy.deepcopy(source)
    result["created_utc"] = datetime.now(timezone.utc).isoformat()
    result["purpose"] = str(source.get("purpose", "")) + f"; peak brightness scaled by {args.brightness_scale:g}"
    result["derived_from_manifest"] = str(source_path)
    result["derived_from_manifest_sha256"] = sha256_file(source_path)
    result["brightness_scale"] = float(args.brightness_scale)
    source_range = list((source.get("source_configuration") or {}).get("peak_sigma", []))
    result["source_configuration"]["peak_sigma"] = [float(value) * args.brightness_scale for value in source_range]
    result["source_configuration"]["brightness_change"] = (
        "Only peak amplitude was multiplied; seeds, source identity, position, type, size and shape were retained."
    )

    outside_allowed = 0
    records_with_allowed_region = 0
    overlaps = 0
    total_sources = 0
    for set_name, injection_set in result["injection_sets"].items():
        payload_dir = output / "payloads" / set_name
        payload_dir.mkdir(parents=True, exist_ok=True)
        for name, galaxy in injection_set["galaxies"].items():
            science_path = Path(galaxy["science_image_path"])
            data, _header = sep_opt.sep_tool.load_fits(science_path)
            noise = physical.robust_sigma(data)
            source_payload = np.load(source["injection_sets"][set_name]["galaxies"][name]["payload_path"])
            placement_region = (
                np.asarray(source_payload["placement_region"], dtype=bool)
                if "placement_region" in source_payload.files else None
            )
            allowed_truth = (
                np.asarray(source_payload["allowed_truth_region"], dtype=bool)
                if "allowed_truth_region" in source_payload.files else None
            )
            records_with_allowed_region += int(allowed_truth is not None)
            delta = np.zeros(data.shape, dtype=float)
            truth_mask = np.zeros(data.shape, dtype=bool)
            truth_labels = np.zeros(data.shape, dtype=np.int32)
            for toy in galaxy["toys"]:
                model, truth = model_and_truth(toy, data.shape, noise, args.brightness_scale)
                if allowed_truth is not None:
                    outside_allowed += int(np.count_nonzero(truth & ~allowed_truth))
                overlaps += int(np.count_nonzero(truth & truth_mask))
                if np.any(truth & truth_mask):
                    raise ValueError(f"{set_name}/{name}: scaled truth footprints overlap")
                finite = np.isfinite(data)
                delta[finite] += model[finite]
                toy_id = int(toy["toy_id"])
                truth_mask |= truth
                truth_labels[truth] = toy_id
                toy["peak_sigma"] = float(toy["peak_sigma"]) * args.brightness_scale
                toy["truth_pixels"] = int(np.count_nonzero(truth))
                total_sources += 1
            payload_path = (payload_dir / f"{name}.npz").resolve()
            payload = {
                "delta": np.asarray(delta, dtype=np.float32),
                "truth_mask": truth_mask.astype(np.uint8),
                "truth_labels": truth_labels,
            }
            if placement_region is not None:
                payload["placement_region"] = placement_region.astype(np.uint8)
            if allowed_truth is not None:
                payload["allowed_truth_region"] = allowed_truth.astype(np.uint8)
            np.savez_compressed(payload_path, **payload)
            galaxy["payload_path"] = str(payload_path)
            galaxy["payload_sha256"] = sha256_file(payload_path)
            galaxy["delta_sha256"] = sha256_array(np.asarray(delta, dtype=np.float32))
            galaxy["truth_mask_sha256"] = sha256_array(truth_mask.astype(np.uint8))
            galaxy["truth_pixels"] = int(np.count_nonzero(truth_mask))
            payload_path.chmod(0o444)
    if outside_allowed:
        raise ValueError(f"Scaled truth has {outside_allowed} pixels outside the original allowed regions")
    manifest_path = output / "paired_toy_injection_manifest.json"
    manifest_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    checksum_path = output / "paired_toy_injection_manifest.sha256"
    checksum_path.write_text(f"{sha256_file(manifest_path)}  {manifest_path.name}\n", encoding="ascii")
    manifest_path.chmod(0o444); checksum_path.chmod(0o444)
    print(
        f"Created exact brightness-scaled manifest with {total_sources} sources, {overlaps} overlaps, "
        f"and {records_with_allowed_region} legacy payloads carrying an explicit allowed-region array: {manifest_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
