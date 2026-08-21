from __future__ import annotations

import argparse
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback
import warnings
import zlib

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FG = ROOT / "Foreground Masking"
for path in (ROOT, FG, FG / "Optimisation", FG / "Interactive tools", FG / "Batch tools", FG / "Shared", FG / "Utilities"):
    if str(path) not in sys.path:
        sys.path.append(str(path))

import optimise_toy_objects_SEP as sep_opt  # noqa: E402
import optimise_toy_objects_MTObjects as mto_opt  # noqa: E402
import sep_processing as sep_tool  # noqa: E402
import mtobjects_spike_gate_processing as mto_tool  # noqa: E402


def native_path(value: str | Path) -> Path:
    """Translate a Windows drive path when the audit is running under WSL."""
    text = str(value)
    if os.name != "nt" and len(text) >= 3 and text[1] == ":" and text[2] in "\\/":
        return Path("/mnt") / text[0].lower() / text[3:].replace("\\", "/")
    return Path(text)


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def toy_metrics(mask: np.ndarray, truth_mask: np.ndarray, truth_labels: np.ndarray, toy_count: int) -> dict[str, float | int]:
    mask = np.asarray(mask, dtype=bool)
    truth = np.asarray(truth_mask, dtype=bool)
    mask_pixels = int(np.count_nonzero(mask))
    truth_pixels = int(np.count_nonzero(truth))
    overlap = int(np.count_nonzero(mask & truth))
    recalls: list[float] = []
    for toy_id in range(1, toy_count + 1):
        toy = truth_labels == toy_id
        n = int(np.count_nonzero(toy))
        recalls.append(float(np.count_nonzero(mask & toy) / n) if n else 0.0)
    recovered = sum(value >= 0.5 for value in recalls)
    recall = overlap / truth_pixels if truth_pixels else 0.0
    precision = overlap / mask_pixels if mask_pixels else 0.0
    f_score = 2 * recall * precision / (recall + precision) if recall + precision else 0.0
    false_mask_fraction = (mask_pixels - overlap) / max(1, mask.size - truth_pixels)
    return {
        "masked_pixels": mask_pixels,
        "masked_fraction": mask_pixels / mask.size if mask.size else 0.0,
        "truth_pixels": truth_pixels,
        "toy_overlap_pixels": overlap,
        "toy_pixel_recall": recall,
        "toy_associated_precision": precision,
        "toy_f_score": f_score,
        "mean_per_toy_recall": float(np.mean(recalls)) if recalls else 0.0,
        "recovered_toys": recovered,
        "toy_count": toy_count,
        "toy_detection_rate": recovered / toy_count if toy_count else 0.0,
        "false_mask_fraction": false_mask_fraction,
    }


def process_one(payload: tuple[dict[str, str], dict, dict]) -> dict[str, object]:
    row, sep_cfg, mto_cfg = payload
    name = row["name"]
    started = time.perf_counter()
    geometry = sep_tool.display.required_geometry(row)
    if geometry is None:
        raise ValueError(f"{name}: incomplete geometry")
    data, _ = sep_tool.load_fits(native_path(sep_tool.display.image_path_for_pc(row, sep_cfg["pc"])))
    seed = int(sep_cfg["toy_seed"]) + zlib.crc32(name.casefold().encode("utf-8"))
    injected, truth_mask, truth_labels, toys = sep_opt.inject_toys(
        name,
        data,
        geometry,
        toys_per_image=int(sep_cfg["toys_per_image"]),
        rng=np.random.default_rng(seed),
        truth_dilation=int(sep_cfg["truth_dilation"]),
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        t0 = time.perf_counter()
        sep_products = sep_tool.sep_products(injected, sep_cfg["params"], geometry)
        sep_seconds = time.perf_counter() - t0
        t0 = time.perf_counter()
        mto_root = mto_tool.find_mtobjects_root(native_path(mto_cfg["mtobjects_root"]))
        mto_products = mto_tool.mtobjects_products(injected, mto_cfg["params"], geometry, mto_root)
        mto_seconds = time.perf_counter() - t0
    result: dict[str, object] = {"galaxy": name, "status": "ok", "error": ""}
    for prefix, products, elapsed in (("sep", sep_products, sep_seconds), ("mto", mto_products, mto_seconds)):
        values = toy_metrics(products["mask"], truth_mask, truth_labels, len(toys))
        for key, value in values.items():
            result[f"{prefix}_{key}"] = value
        result[f"{prefix}_segments_raw"] = len(products["rows"])
        result[f"{prefix}_segments_kept"] = sum(1 for item in products["rows"] if item.get("kept"))
        result[f"{prefix}_elapsed_seconds"] = elapsed
    result["masked_fraction_difference_sep_minus_mto"] = float(result["sep_masked_fraction"]) - float(result["mto_masked_fraction"])
    result["toy_recall_difference_sep_minus_mto"] = float(result["sep_toy_pixel_recall"]) - float(result["mto_toy_pixel_recall"])
    result["f_score_difference_sep_minus_mto"] = float(result["sep_toy_f_score"]) - float(result["mto_toy_f_score"])
    result["comparison_elapsed_seconds"] = time.perf_counter() - started
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sep-config", type=Path, required=True)
    parser.add_argument("--mto-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--mtobjects-root", type=Path, default=None)
    args = parser.parse_args()
    sep_cfg = load_config(args.sep_config)
    mto_cfg = load_config(args.mto_config)
    if args.mtobjects_root is not None:
        mto_cfg["mtobjects_root"] = str(args.mtobjects_root)
    if (sep_cfg["toy_seed"], sep_cfg["toys_per_image"], sep_cfg["truth_dilation"]) != (
        mto_cfg["toy_seed"], mto_cfg["toys_per_image"], mto_cfg["truth_dilation"]
    ):
        raise ValueError("SEP and MTO toy configurations do not match")
    if (float(mto_cfg.get("toy_peak_sigma_min", 5.0)), float(mto_cfg.get("toy_peak_sigma_max", 25.0))) != (5.0, 25.0):
        raise ValueError("MTO comparison config is not the standard 5-25 sigma toy population")
    manifest_rows = sep_tool.display.read_manifest(native_path(sep_cfg["manifest"]))
    rows = sorted(
        [
            row
            for row in manifest_rows
            if native_path(sep_tool.display.image_path_for_pc(row, sep_cfg["pc"])).exists()
        ],
        key=lambda row: row["name"].casefold(),
    )
    rows = rows[: min(int(sep_cfg["max_images"]), int(mto_cfg["max_images"]))]
    if args.limit is not None:
        rows = rows[: args.limit]
    results: list[dict[str, object]] = []
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(process_one, (row, sep_cfg, mto_cfg)): row["name"] for row in rows}
        for index, future in enumerate(as_completed(futures), 1):
            name = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {"galaxy": name, "status": "failed", "error": f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"}
                if len(rows) <= 3:
                    print(result["error"], flush=True)
            results.append(result)
            elapsed = time.perf_counter() - started
            eta = elapsed / index * (len(rows) - index) if index else math.nan
            print(f"[{index}/{len(rows)}] {name}: {result['status']} elapsed={elapsed:.0f}s eta={eta:.0f}s", flush=True)
    results.sort(key=lambda item: str(item["galaxy"]).casefold())
    fieldnames: list[str] = []
    for result in results:
        for key in result:
            if key not in fieldnames:
                fieldnames.append(key)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    failures = sum(row["status"] != "ok" for row in results)
    print(f"WROTE {args.output}; rows={len(results)} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
