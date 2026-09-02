#!/usr/bin/env python3
"""Clone saved Haigh toys while scaling only Sérsic-galaxy size."""

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
    parser.add_argument("--science-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--galaxy-size-scale", type=float, default=1.5)
    parser.add_argument("--pc", choices=("Desktop", "Laptop"), default="Desktop")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.galaxy_size_scale <= 0:
        raise ValueError("--galaxy-size-scale must be positive")
    source_path = args.source_manifest.resolve()
    source = json.loads(source_path.read_text(encoding="utf-8-sig"))
    names = list(next(iter(source["injection_sets"].values()))["galaxies"])
    rows = sep_opt.select_rows(args.science_manifest, args.pc, names, len(names), 0)
    rows_by_name = {row["name"]: row for row in rows}
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    result = copy.deepcopy(source)
    result["created_utc"] = datetime.now(timezone.utc).isoformat()
    result["injection_model_version"] = "haigh-aligned-galaxy-size150-sensitivity-v1"
    result["purpose"] = str(source.get("purpose", "")) + f"; Sersic-galaxy size sensitivity scale {args.galaxy_size_scale:g}"
    result["derived_from_manifest"] = str(source_path)
    result["derived_from_manifest_sha256"] = sha256_file(source_path)
    result["galaxy_size_scale"] = float(args.galaxy_size_scale)
    config = result.setdefault("source_configuration", {})
    config["width_change"] = (
        "Sensitivity experiment only: Sersic-galaxy effective radius multiplied; star PSF, "
        "peak sigma, seeds, identities, positions, types and shapes retained."
    )
    config["star_psf_fwhm_arcsec"] = physical.IRAC_36_PSF_FWHM_ARCSEC
    config["physical_irac_psf_retained"] = True
    config["background_galaxy_effective_radius_arcsec_sensitivity_range"] = [0.75, 5.25]
    total_sources = 0
    outside_analysis = 0
    truncated_sources = 0
    overlaps = 0
    old_sizes: list[float] = []
    new_sizes: list[float] = []
    for set_name, injection_set in result["injection_sets"].items():
        payload_dir = output / "payloads" / set_name
        payload_dir.mkdir(parents=True, exist_ok=True)
        for name, galaxy in injection_set["galaxies"].items():
            row = rows_by_name[name]
            geometry = sep_opt.sep_tool.display.required_geometry(row)
            if geometry is None:
                raise ValueError(f"{name}: missing display geometry")
            science_path = Path(galaxy["science_image_path"])
            data, _header = sep_opt.sep_tool.load_fits(science_path)
            analysis_region = sep_opt.investigated_region_mask(data, geometry)
            noise = physical.robust_sigma(data)
            source_record = source["injection_sets"][set_name]["galaxies"][name]
            with np.load(source_record["payload_path"], allow_pickle=False) as payload:
                optional = {
                    key: np.asarray(payload[key]) for key in ("placement_region", "allowed_truth_region")
                    if key in payload.files
                }
            delta = np.zeros(data.shape, dtype=float)
            truth_mask = np.zeros(data.shape, dtype=bool)
            truth_labels = np.zeros(data.shape, dtype=np.int32)
            truths: list[np.ndarray] = []
            for toy in galaxy["toys"]:
                peak = float(toy["peak_sigma"]) * noise
                x0, y0 = float(toy["x"]), float(toy["y"])
                threshold = float(toy.get("truth_sigma_threshold", 1.0))
                old_sizes.append(float(toy["fwhm_pixels"]))
                if toy["object_type"] == "star":
                    star_psf = float(toy["psf_fwhm_pixels"])
                    model = physical.irac_star_model(data.shape, x0, y0, peak, star_psf)
                    truth = physical.noise_truth(model, noise, threshold, encircled_energy_cap=0.95)
                elif toy["object_type"] == "galaxy":
                    new_radius = float(toy["effective_radius_pixels"]) * args.galaxy_size_scale
                    model = physical.background_galaxy_model(
                        data.shape, x0, y0, peak, new_radius, float(toy["sersic_index"]),
                        float(toy["axis_ratio"]), float(toy["pa_deg"]),
                        float(toy["psf_fwhm_pixels"]),
                    )
                    truth = physical.noise_truth(model, noise, threshold)
                    toy["effective_radius_pixels"] = new_radius
                    toy["effective_radius_arcsec"] = float(toy["effective_radius_arcsec"]) * args.galaxy_size_scale
                    toy["fwhm_pixels"] = float(toy["fwhm_pixels"]) * args.galaxy_size_scale
                else:
                    raise ValueError(f"{set_name}/{name}: unsupported type {toy['object_type']!r}")
                outside = truth & ~analysis_region
                outside_pixels = int(np.count_nonzero(outside))
                outside_analysis += outside_pixels
                if outside_pixels:
                    truncated_sources += 1
                    truth = truth & analysis_region
                overlap = truth & truth_mask
                overlaps += int(np.count_nonzero(overlap))
                if np.any(overlap):
                    raise ValueError(f"{set_name}/{name}: enlarged truth footprints overlap")
                finite = np.isfinite(data)
                delta[finite] += model[finite]
                truth_mask |= truth
                truth_labels[truth] = int(toy["toy_id"])
                toy["truth_pixels"] = int(np.count_nonzero(truth))
                new_sizes.append(float(toy["fwhm_pixels"]))
                truths.append(truth)
                total_sources += 1
            payload_path = (payload_dir / f"{name}.npz").resolve()
            np.savez_compressed(
                payload_path, delta=np.asarray(delta, dtype=np.float32),
                truth_mask=truth_mask.astype(np.uint8), truth_labels=truth_labels, **optional,
            )
            galaxy["payload_path"] = str(payload_path)
            galaxy["payload_sha256"] = sha256_file(payload_path)
            galaxy["delta_sha256"] = sha256_array(np.asarray(delta, dtype=np.float32))
            galaxy["truth_mask_sha256"] = sha256_array(truth_mask.astype(np.uint8))
            galaxy["truth_pixels"] = int(np.count_nonzero(truth_mask))
            payload_path.chmod(0o444)
    manifest_path = output / "paired_toy_injection_manifest.json"
    result["fwhm_audit"] = {
        "source_count": total_sources, "overlap_pixels": overlaps,
        "outside_analysis_pixels": outside_analysis,
        "boundary_truncated_sources": truncated_sources,
        "old_mean_fwhm_pixels": float(np.mean(old_sizes)),
        "new_mean_fwhm_pixels": float(np.mean(new_sizes)),
    }
    manifest_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    checksum_path = output / "paired_toy_injection_manifest.sha256"
    checksum_path.write_text(f"{sha256_file(manifest_path)}  {manifest_path.name}\n", encoding="ascii")
    manifest_path.chmod(0o444); checksum_path.chmod(0o444)
    print(json.dumps(result["fwhm_audit"], indent=2))
    print(f"Immutable 1.5x-Sersic-galaxy-size sensitivity manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
