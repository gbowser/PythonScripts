#!/usr/bin/env python3
"""Calibrate Photutils from bar spikes, then run global foreground masking."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits


SCRIPT_DIR = Path(__file__).resolve().parent
BAR_SPIKE_SCRIPT = SCRIPT_DIR / "bar_spike_gated_foreground_report.py"
DEFAULT_OUTPUT_DIR = Path(
    r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\photutils global_from_spike_calibration"
)
DEFAULT_NAMES = [
    "ESO120-012",
    "ESO357-012",
    "ESO358-020",
    "ESO359-031",
    "ESO440-044",
    "NGC1187",
    "NGC1640",
    "NGC3726",
    "ESO420-009",
]


def load_bar_spike_module():
    spec = importlib.util.spec_from_file_location("bar_spike_gated", BAR_SPIKE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


bar = load_bar_spike_module()


def detect_spike_count(data: np.ndarray, geometry: dict[str, float], args: argparse.Namespace) -> int:
    radius_pix = bar.profile_radius_pixels(data, geometry)
    rr_major_pix, intensity_major = bar.s4g_plot.profile_at_pa(
        data,
        geometry["xc"],
        geometry["yc"],
        geometry["bar_pa"],
        radius_pix,
        width=args.profile_width,
    )
    rr_major_deproj = bar.s4g_plot.deprojected_profile_radius(
        geometry["bar_pa"],
        geometry["disk_pa"],
        geometry["inclination"],
        rr_major_pix * geometry["pixel_scale"],
    )
    spike_samples = bar.detect_profile_spikes(
        rr_major_deproj,
        intensity_major,
        excess_fraction=args.spike_excess_fraction,
        neighbour_inner_arcsec=args.spike_neighbour_inner_arcsec,
        neighbour_outer_arcsec=args.spike_neighbour_outer_arcsec,
        side_offset_samples=args.spike_side_offset_samples,
        side_drop_fraction=args.spike_side_drop_fraction,
        center_exclusion_arcsec=args.spike_center_exclusion_arcsec,
    )
    spike_samples = bar._expand_boolean_mask(spike_samples, args.spike_window_samples)
    return int(np.count_nonzero(spike_samples))


def load_image_and_geometry(row: dict[str, str]):
    geometry = bar.s4g_plot.required_geometry(row)
    if geometry is None:
        raise ValueError(f"{row['name']} has incomplete geometry in the manifest.")
    data = np.squeeze(fits.getdata(Path(row["image_path"])).astype(float))
    if data.ndim != 2:
        raise ValueError(f"Expected a 2D FITS image, got shape {data.shape}.")
    return data, geometry


def calibrate_detection_thresholds(
    rows: list[dict[str, str]],
    args: argparse.Namespace,
) -> tuple[dict[str, dict[str, float | str]], float]:
    calibration: dict[str, dict[str, float | str]] = {}
    positive_nsigmas: list[float] = []

    for row in rows:
        name = row["name"]
        print(f"Calibrating {name}...", flush=True)
        data, geometry = load_image_and_geometry(row)
        smooth_model = bar.fgmask.make_smooth_galaxy_model(data, args.smooth_sigma_pixels)
        residual = bar.fgmask.make_residual_image(data, smooth_model)
        spike_count = detect_spike_count(data, geometry, args)

        if spike_count > 0:
            nsigma, evaluations = bar.choose_spike_gated_detection_nsigma(
                data,
                residual,
                geometry,
                candidate_nsigmas=args.auto_tune_nsigmas,
                profile_width=args.profile_width,
                npixels=args.npixels,
                dilation_radius_pixels=args.dilation_radius_pixels,
                max_area=args.max_area,
                max_elongation=args.max_elongation,
                exclude_center_radius_pixels=args.exclude_center_radius_pixels,
                spike_excess_fraction=args.spike_excess_fraction,
                spike_neighbour_inner_arcsec=args.spike_neighbour_inner_arcsec,
                spike_neighbour_outer_arcsec=args.spike_neighbour_outer_arcsec,
                spike_side_offset_samples=args.spike_side_offset_samples,
                spike_side_drop_fraction=args.spike_side_drop_fraction,
                spike_center_exclusion_arcsec=args.spike_center_exclusion_arcsec,
                spike_window_samples=args.spike_window_samples,
            )
            positive_nsigmas.append(float(nsigma))
            source = "bar-spike calibrated"
            best = next((item for item in evaluations if item["nsigma"] == nsigma), evaluations[-1])
            coverage = float(best["coverage"])
        else:
            nsigma = math.nan
            source = "fallback from spike-positive galaxies"
            coverage = 1.0

        calibration[name] = {
            "name": name,
            "input_fits": row["image_path"],
            "profile_spike_samples": float(spike_count),
            "calibrated_nsigma": float(nsigma),
            "threshold_source": source,
            "spike_coverage": coverage,
        }

    # No-spike galaxies provide no profile evidence for a threshold, so use the
    # most conservative threshold that still handled at least one spike-positive
    # calibration galaxy.
    fallback_nsigma = float(np.max(positive_nsigmas)) if positive_nsigmas else args.detection_nsigma
    for item in calibration.values():
        if not np.isfinite(float(item["calibrated_nsigma"])):
            item["calibrated_nsigma"] = fallback_nsigma
    return calibration, fallback_nsigma


def make_global_report_args(args: argparse.Namespace, detection_nsigma: float) -> argparse.Namespace:
    return argparse.Namespace(
        manifest=args.manifest,
        output=args.output,
        output_dir=args.output_dir,
        names=[],
        all=False,
        limit=None,
        profile_width=args.profile_width,
        smooth_sigma_pixels=args.smooth_sigma_pixels,
        detection_nsigma=detection_nsigma,
        masking_mode="global",
        auto_tune=False,
        auto_tune_nsigmas=args.auto_tune_nsigmas,
        npixels=args.npixels,
        dilation_radius_pixels=args.dilation_radius_pixels,
        max_area=args.max_area,
        max_elongation=args.max_elongation,
        exclude_center_radius_pixels=args.exclude_center_radius_pixels,
        bridge_merge_gap_samples=args.bridge_merge_gap_samples,
        spike_excess_fraction=args.spike_excess_fraction,
        spike_neighbour_inner_arcsec=args.spike_neighbour_inner_arcsec,
        spike_neighbour_outer_arcsec=args.spike_neighbour_outer_arcsec,
        spike_side_offset_samples=args.spike_side_offset_samples,
        spike_side_drop_fraction=args.spike_side_drop_fraction,
        spike_center_exclusion_arcsec=args.spike_center_exclusion_arcsec,
        spike_window_samples=args.spike_window_samples,
    )


def write_calibration_csv(
    path: Path,
    calibration: dict[str, dict[str, float | str]],
    fallback_nsigma: float,
) -> None:
    rows = []
    for item in calibration.values():
        row = dict(item)
        row["fallback_nsigma_for_no_spike_galaxies"] = fallback_nsigma
        rows.append(row)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Experimentally calibrate Photutils thresholds from bar-spike-gated examples, "
            "then run global Photutils foreground-candidate masking."
        )
    )
    parser.add_argument("--manifest", type=Path, default=bar.DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=bar.DEFAULT_OUTPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--names", nargs="*", default=DEFAULT_NAMES)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--profile-width", type=int, default=3)
    parser.add_argument("--smooth-sigma-pixels", type=float, default=15.0)
    parser.add_argument("--detection-nsigma", type=float, default=5.0)
    parser.add_argument("--auto-tune-nsigmas", type=float, nargs="*", default=[5.0, 4.5, 4.0, 3.5])
    parser.add_argument("--npixels", type=int, default=8)
    parser.add_argument("--dilation-radius-pixels", type=int, default=3)
    parser.add_argument("--max-area", type=int, default=500)
    parser.add_argument("--max-elongation", type=float, default=6.0)
    parser.add_argument("--exclude-center-radius-pixels", type=float, default=12.0)
    parser.add_argument("--bridge-merge-gap-samples", type=int, default=12)
    parser.add_argument("--spike-excess-fraction", type=float, default=0.25)
    parser.add_argument("--spike-neighbour-inner-arcsec", type=float, default=4.0)
    parser.add_argument("--spike-neighbour-outer-arcsec", type=float, default=15.0)
    parser.add_argument("--spike-side-offset-samples", type=int, default=3)
    parser.add_argument("--spike-side-drop-fraction", type=float, default=0.4)
    parser.add_argument("--spike-center-exclusion-arcsec", type=float, default=8.0)
    parser.add_argument("--spike-window-samples", type=int, default=2)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    all_rows = bar.read_rows(args.manifest)
    if args.all:
        selected = all_rows
    else:
        wanted = set(args.names)
        selected = [row for row in all_rows if row["name"] in wanted]

    if args.limit is not None:
        selected = selected[: args.limit]

    if not selected:
        print("No galaxies selected.")
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    calibration, fallback_nsigma = calibrate_detection_thresholds(selected, args)
    calibration_csv = args.output_dir / "photutils_global_calibration_from_bar_spikes.csv"
    write_calibration_csv(calibration_csv, calibration, fallback_nsigma)
    print(f"Wrote {calibration_csv}")

    made = 0
    for row in selected:
        name = row["name"]
        nsigma = float(calibration[name]["calibrated_nsigma"])
        report_args = make_global_report_args(args, nsigma)
        output = args.output_dir / f"{bar.s4g_plot.safe_filename(name)}_photutils_global_foreground_removed.pdf"
        print(f"Writing global Photutils report for {name} at nsigma={nsigma:g}...", flush=True)
        bar.make_report(report_args, row, output)
        made += 1
        print(f"Wrote {output}", flush=True)

    print(f"Made {made} global Photutils foreground-candidate reports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
