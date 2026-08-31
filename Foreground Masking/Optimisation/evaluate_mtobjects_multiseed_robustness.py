#!/usr/bin/env python3
"""Evaluate completed MTObjects fold winners on three new displayed-frame toy seeds."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import multiprocessing as mp
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
for path in (PROJECT_ROOT, FOREGROUND_ROOT, SCRIPT_DIR, FOREGROUND_ROOT / "Shared"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import generate_paired_toy_manifest as generator  # noqa: E402
import optimise_toy_objects_MTObjects as mto_opt  # noqa: E402
from paired_toy_common import SCHEMA_VERSION, sha256_file  # noqa: E402


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_validation_manifest(args: argparse.Namespace, names: list[str]) -> Path:
    output = args.output_dir / "paired_validation_injections"
    manifest_path = output / "paired_toy_injection_manifest.json"
    if manifest_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if sorted(existing.get("validation_seeds", [])) != sorted(args.seeds):
            raise ValueError("Existing validation manifest uses different seeds; choose a new output directory.")
        print(f"Reusing immutable validation manifest: {manifest_path}", flush=True)
        return manifest_path

    output.mkdir(parents=True, exist_ok=True)
    build_args = SimpleNamespace(
        source_manifest=args.manifest,
        pc=args.pc,
        toys_per_image=args.toys_per_image,
        truth_dilation=args.truth_dilation,
        toy_peak_sigma_min=args.toy_peak_sigma_min,
        toy_peak_sigma_max=args.toy_peak_sigma_max,
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "immutable_after_generation": True,
        "purpose": "Three-seed robustness validation of completed MTObjects fold winners",
        "source_manifest": str(args.manifest.resolve()),
        "clean_list": str(args.clean_list.resolve()),
        "validation_seeds": list(args.seeds),
        "toy_configuration": {
            "toys_per_image": args.toys_per_image,
            "truth_dilation": args.truth_dilation,
            "peak_sigma_min": args.toy_peak_sigma_min,
            "peak_sigma_max": args.toy_peak_sigma_max,
            "placement_area": "finite pixels in the displayed deprojected centred square",
        },
        "injection_sets": {},
    }
    for index, seed in enumerate(args.seeds, start=1):
        set_name = f"validation_seed_{index}"
        manifest["injection_sets"][set_name] = generator.build_set(build_args, set_name, seed, names, output)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    checksum = output / "paired_toy_injection_manifest.sha256"
    checksum.write_text(f"{sha256_file(manifest_path)}  {manifest_path.name}\n", encoding="ascii")
    manifest_path.chmod(0o444)
    checksum.chmod(0o444)
    print(f"Immutable validation manifest: {manifest_path}", flush=True)
    return manifest_path


def build_cases(args: argparse.Namespace, names: list[str], manifest: Path, set_name: str):
    case_args = SimpleNamespace(
        manifest=args.manifest, pc=args.pc, mtobjects_root=args.mtobjects_root,
        names=names, max_images=len(names), seed=0, detect_on="original",
        toys_per_image=args.toys_per_image, truth_dilation=args.truth_dilation,
        toy_peak_sigma_min=args.toy_peak_sigma_min, toy_peak_sigma_max=args.toy_peak_sigma_max,
        injection_manifest=manifest, injection_set=set_name,
    )
    return mto_opt.build_cases(case_args)


def score_candidate(cases, params: dict[str, object], args: argparse.Namespace):
    root = mto_opt.mto.find_mtobjects_root(args.mtobjects_root)
    worker_count = min(args.workers, len(cases))
    if worker_count == 1:
        rows = [mto_opt.score_case(case, params, root) for case in cases]
    else:
        context = mp.get_context("spawn")
        with context.Pool(worker_count, initializer=mto_opt.initialise_score_worker, initargs=(cases, root)) as pool:
            rows = pool.map(mto_opt.score_case_worker, [(i, params) for i in range(len(cases))])
    metrics = mto_opt.aggregate_score(
        rows, max_masked_fraction=args.max_masked_fraction,
        data_loss_penalty=args.data_loss_penalty,
        false_positive_penalty=args.false_positive_penalty,
        min_toy_detection_rate=0.25, min_mean_toy_recall=0.20,
        max_mask_exceedance_fraction=getattr(args, "max_mask_exceedance_fraction", 0.20),
        catastrophic_masked_fraction=getattr(args, "catastrophic_masked_fraction", 0.30),
        excess_masking_penalty=getattr(args, "excess_masking_penalty", 1.0),
    )
    return metrics, rows


def per_toy_rows(cases, params: dict[str, object], seed_label: str, fold: int, args: argparse.Namespace):
    root = mto_opt.mto.find_mtobjects_root(args.mtobjects_root)
    result: list[dict[str, object]] = []
    for case in cases:
        products = mto_opt.mto.mtobjects_products(case.injected, params, case.geometry, root)
        mask = np.asarray(products["mask"], dtype=bool) & np.asarray(case.analysis_region, dtype=bool)
        baseline = np.asarray(case.baseline_mask, dtype=bool) & np.asarray(case.analysis_region, dtype=bool)
        incremental = mask & ~baseline
        for toy in case.toys:
            truth = np.asarray(case.truth_labels) == int(toy.toy_id)
            pixels = int(np.count_nonzero(truth))
            recall = int(np.count_nonzero(incremental & truth)) / pixels if pixels else 0.0
            result.append({
                "seed_set": seed_label, "fold": fold, "image": case.name,
                "toy_id": toy.toy_id, "object_type": toy.object_type,
                "peak_sigma": toy.peak_sigma, "fwhm_pixels": toy.fwhm_pixels,
                "toy_recall": recall, "detected": int(recall >= 0.5),
            })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean-list", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--rejection-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mtobjects-root", type=Path, required=True)
    parser.add_argument("--pc", default="Desktop")
    parser.add_argument("--seeds", type=int, nargs=3, default=[202608501, 202608601, 202608701])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--toys-per-image", type=int, default=5)
    parser.add_argument("--truth-dilation", type=int, default=1)
    parser.add_argument("--toy-peak-sigma-min", type=float, default=6.0)
    parser.add_argument("--toy-peak-sigma-max", type=float, default=30.0)
    parser.add_argument("--max-masked-fraction", type=float, default=0.15)
    parser.add_argument("--max-mask-exceedance-fraction", type=float, default=0.20)
    parser.add_argument("--catastrophic-masked-fraction", type=float, default=0.30)
    parser.add_argument("--excess-masking-penalty", type=float, default=1.0)
    parser.add_argument("--data-loss-penalty", type=float, default=0.5)
    parser.add_argument("--false-positive-penalty", type=float, default=0.1)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    names = generator.read_names(args.clean_list)
    rejection = json.loads(args.rejection_json.read_text(encoding="utf-8"))
    candidates = rejection["candidates"]
    manifest = build_validation_manifest(args, names)
    seed_cases = {
        f"validation_seed_{index}": build_cases(args, names, manifest, f"validation_seed_{index}")
        for index in range(1, 4)
    }

    seed_rows: list[dict[str, object]] = []
    pooled_rows: list[dict[str, object]] = []
    pooled_details: dict[int, list[dict[str, object]]] = {}
    for candidate_index, candidate in enumerate(candidates, start=1):
        fold = int(candidate["fold"])
        params = json.loads(candidate["parameter_set_json"])
        all_case_rows: list[dict[str, object]] = []
        per_seed_detection: list[float] = []
        for set_name, cases in seed_cases.items():
            metrics, details = score_candidate(cases, params, args)
            all_case_rows.extend(details)
            per_seed_detection.append(float(metrics["toy_detection_rate"]))
            seed_rows.append({"fold": fold, "seed_set": set_name, **metrics})
            print(
                f"candidate {candidate_index:02d}/{len(candidates)} fold={fold:02d} {set_name}: "
                f"detection={metrics['toy_detection_rate']:.1%}, recall={metrics['mean_toy_recall']:.1%}, "
                f"max_masked={metrics['max_masked_fraction']:.1%}", flush=True,
            )
        pooled = mto_opt.aggregate_score(
            all_case_rows, max_masked_fraction=args.max_masked_fraction,
            data_loss_penalty=args.data_loss_penalty, false_positive_penalty=args.false_positive_penalty,
            min_toy_detection_rate=0.25, min_mean_toy_recall=0.20,
            max_mask_exceedance_fraction=args.max_mask_exceedance_fraction,
            catastrophic_masked_fraction=args.catastrophic_masked_fraction,
            excess_masking_penalty=args.excess_masking_penalty,
        )
        successful_cases = sum(int(row["recovered_toys"]) > 0 for row in all_case_rows)
        passed = (
            float(pooled["toy_detection_rate"]) >= 0.50
            and float(pooled["mean_toy_recall"]) >= 0.30
            and bool(float(pooled["masking_feasible"]))
            and successful_cases >= 54
        )
        pooled_rows.append({
            "fold": fold, **pooled,
            "minimum_seed_detection_rate": min(per_seed_detection),
            "maximum_seed_detection_rate": max(per_seed_detection),
            "successful_galaxy_seed_cases": successful_cases,
            "required_successful_galaxy_seed_cases": 54,
            "robustness_pass": int(passed),
            "parameter_set_json": candidate["parameter_set_json"],
            "best_json": candidate["best_json"],
        })
        pooled_details[fold] = all_case_rows
        write_csv(args.output_dir / "multiseed_candidate_by_seed.csv", seed_rows)
        write_csv(args.output_dir / "multiseed_candidate_pooled.csv", pooled_rows)

    best = max(pooled_rows, key=lambda row: (float(row["toy_detection_rate"]), float(row["mean_toy_recall"])))
    best_fold = int(best["fold"])
    best_params = json.loads(best["parameter_set_json"])
    toy_rows: list[dict[str, object]] = []
    for set_name, cases in seed_cases.items():
        toy_rows.extend(per_toy_rows(cases, best_params, set_name, best_fold, args))
    write_csv(args.output_dir / "best_candidate_per_toy.csv", toy_rows)

    type_summary = []
    for toy_type in sorted({str(row["object_type"]) for row in toy_rows}):
        selected = [row for row in toy_rows if row["object_type"] == toy_type]
        type_summary.append({
            "object_type": toy_type, "toys": len(selected),
            "detection_rate": sum(int(row["detected"]) for row in selected) / len(selected),
            "mean_toy_recall": float(np.mean([float(row["toy_recall"]) for row in selected])),
        })
    write_csv(args.output_dir / "best_candidate_by_toy_type.csv", type_summary)
    report = {
        "status": "pass" if any(int(row["robustness_pass"]) for row in pooled_rows) else "fail",
        "criteria": {
            "pooled_toy_detection_rate": 0.50, "pooled_mean_toy_recall": 0.30,
            "galaxy_masking_threshold": args.max_masked_fraction,
            "maximum_fraction_of_galaxies_above_threshold": args.max_mask_exceedance_fraction,
            "catastrophic_individual_masked_fraction": args.catastrophic_masked_fraction,
            "successful_galaxy_seed_cases": 54,
        },
        "seeds": args.seeds, "toys_evaluated_per_candidate": 3 * 22 * args.toys_per_image,
        "best_candidate": best, "by_toy_type": type_summary,
    }
    (args.output_dir / "mtobjects_multiseed_robustness.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Robustness result: {report['status'].upper()}; best fold={best_fold}; output={args.output_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
