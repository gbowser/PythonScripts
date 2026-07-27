#!/usr/bin/env python3
"""Score global Photutils parameter sets using spike and no-spike controls."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits


SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
SUPPORT_DIRS = tuple(FOREGROUND_ROOT / name for name in ("Batch tools", "PhotUtils", "Interactive tools", "Shared", "Utilities"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
BAR_SCRIPT = SCRIPT_DIR / "bar_spike_gated_foreground_report.py"
from machine_paths import PC_RESEARCH_FOLDERS, remove_foreground_folder  # noqa: E402

DEFAULT_PC = "Laptop"
DEFAULT_OUTPUT = remove_foreground_folder(DEFAULT_PC) / "optimisation"
DEFAULT_SPIKE_NAMES = ["ESO120-012", "ESO357-012", "ESO358-020", "ESO359-031", "ESO440-044"]
DEFAULT_CONTROL_NAMES = ["NGC1187", "NGC1640", "NGC3726", "ESO420-009"]


def load_bar_module():
    spec = importlib.util.spec_from_file_location("bar_spike_report", BAR_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


bar = load_bar_module()


def profile_arrays(data: np.ndarray, mask: np.ndarray, geometry: dict[str, float], profile_width: int):
    radius_pix = bar.profile_radius_pixels(data, geometry)
    bar_pa = geometry["bar_pa"]
    minor_pa = bar.angles.minoraxis(bar_pa, geometry["disk_pa"], geometry["inclination"])
    rr_major_pix, major = bar.s4g_plot.profile_at_pa(
        data, geometry["xc"], geometry["yc"], bar_pa, radius_pix, width=profile_width
    )
    _, minor = bar.s4g_plot.profile_at_pa(
        data, geometry["xc"], geometry["yc"], minor_pa, radius_pix, width=profile_width
    )
    masked_data = np.where(mask, np.nan, data)
    _, major_masked = bar.s4g_plot.profile_at_pa(
        masked_data, geometry["xc"], geometry["yc"], bar_pa, radius_pix, width=profile_width
    )
    _, minor_masked = bar.s4g_plot.profile_at_pa(
        masked_data, geometry["xc"], geometry["yc"], minor_pa, radius_pix, width=profile_width
    )
    mask_major = bar.profile_mask_at_pa(mask, geometry["xc"], geometry["yc"], bar_pa, radius_pix, width=profile_width)
    rr_major = bar.s4g_plot.deprojected_profile_radius(
        bar_pa, geometry["disk_pa"], geometry["inclination"], rr_major_pix * geometry["pixel_scale"]
    )
    return rr_major, major, minor, major_masked, minor_masked, mask_major


def profile_damage(original: np.ndarray, masked_profile: np.ndarray, affected: np.ndarray) -> float:
    good = np.isfinite(original) & np.isfinite(masked_profile) & (original > 0)
    if np.count_nonzero(good) < 5:
        return 0.0
    log_delta = np.abs(np.log10(masked_profile[good]) - np.log10(original[good]))
    affected_fraction = np.count_nonzero(affected) / max(1, affected.size)
    return float(np.nanmedian(log_delta) + 5.0 * affected_fraction)


def detect_spikes(data: np.ndarray, geometry: dict[str, float], args: argparse.Namespace) -> np.ndarray:
    radius_pix = bar.profile_radius_pixels(data, geometry)
    rr_pix, major = bar.s4g_plot.profile_at_pa(
        data, geometry["xc"], geometry["yc"], geometry["bar_pa"], radius_pix, width=args.profile_width
    )
    rr = bar.s4g_plot.deprojected_profile_radius(
        geometry["bar_pa"], geometry["disk_pa"], geometry["inclination"], rr_pix * geometry["pixel_scale"]
    )
    spikes = bar.detect_profile_spikes(
        rr,
        major,
        excess_fraction=args.spike_excess_fraction,
        neighbour_inner_arcsec=args.spike_neighbour_inner_arcsec,
        neighbour_outer_arcsec=args.spike_neighbour_outer_arcsec,
        side_offset_samples=args.spike_side_offset_samples,
        side_drop_fraction=args.spike_side_drop_fraction,
        center_exclusion_arcsec=args.spike_center_exclusion_arcsec,
    )
    return bar._expand_boolean_mask(spikes, args.spike_window_samples)


def evaluate_one(row: dict[str, str], params: dict[str, float], args: argparse.Namespace):
    geometry = bar.s4g_plot.required_geometry(row)
    if geometry is None:
        raise ValueError(f"{row['name']} has incomplete geometry.")
    data = np.squeeze(fits.getdata(Path(row["image_path"])).astype(float))
    smooth = bar.fgmask.make_smooth_galaxy_model(data, params["smooth_sigma"])
    residual = bar.fgmask.make_residual_image(data, smooth)
    mask, kept_rows = bar.build_mask_from_residual(
        data,
        residual,
        geometry,
        detection_nsigma=params["nsigma"],
        npixels=int(params["npixels"]),
        dilation_radius_pixels=int(params["dilation"]),
        max_area=int(params["max_area"]),
        max_elongation=params["max_elongation"],
        exclude_center_radius_pixels=params["central_exclusion"],
    )
    rr, major, _minor, major_masked, _minor_masked, mask_major = profile_arrays(
        data, mask, geometry, args.profile_width
    )
    spikes = detect_spikes(data, geometry, args)
    spike_coverage = 1.0 if not np.any(spikes) else float(np.count_nonzero(mask_major & spikes) / np.count_nonzero(spikes))
    return {
        "name": row["name"],
        "spike_samples": int(np.count_nonzero(spikes)),
        "spike_coverage": spike_coverage,
        "segments": len(kept_rows),
        "masked_pixels": int(np.count_nonzero(mask)),
        "masked_fraction": float(np.count_nonzero(mask) / mask.size),
        "profile_affected_fraction": float(np.count_nonzero(mask_major) / mask_major.size),
        "profile_damage": profile_damage(major, major_masked, mask_major),
    }


def parameter_grid(args: argparse.Namespace):
    for nsigma in args.nsigmas:
        for dilation in args.dilations:
            for max_area in args.max_areas:
                for max_elongation in args.max_elongations:
                    yield {
                        "nsigma": float(nsigma),
                        "dilation": int(dilation),
                        "max_area": int(max_area),
                        "max_elongation": float(max_elongation),
                        "smooth_sigma": float(args.smooth_sigma_pixels),
                        "npixels": int(args.npixels),
                        "central_exclusion": float(args.exclude_center_radius_pixels),
                    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tiered optimisation for global Photutils foreground parameters.")
    parser.add_argument(
        "--pc",
        choices=sorted(PC_RESEARCH_FOLDERS),
        default=DEFAULT_PC,
        help=(
            "Select which Dropbox research-folder location to use for default paths. "
            "Use 'Desktop' for D:\\Dropbox and 'Laptop' for C:\\Users\\gordo\\Dropbox."
        ),
    )
    parser.add_argument("--manifest", type=Path, default=bar.DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--spike-names", nargs="*", default=DEFAULT_SPIKE_NAMES)
    parser.add_argument("--control-names", nargs="*", default=DEFAULT_CONTROL_NAMES)
    parser.add_argument("--nsigmas", type=float, nargs="*", default=[5.5, 5.0, 4.5, 4.0, 3.5])
    parser.add_argument("--dilations", type=int, nargs="*", default=[1, 2, 3])
    parser.add_argument("--max-areas", type=int, nargs="*", default=[150, 300, 500])
    parser.add_argument("--max-elongations", type=float, nargs="*", default=[3.0, 4.0, 6.0])
    parser.add_argument("--smooth-sigma-pixels", type=float, default=15.0)
    parser.add_argument("--npixels", type=int, default=8)
    parser.add_argument(
        "--exclude-center-radius-pixels",
        type=float,
        default=12.0,
        help="Deprojected, bar-aligned central exclusion radius, expressed in image-pixel units.",
    )
    parser.add_argument("--profile-width", type=int, default=3)
    parser.add_argument("--spike-excess-fraction", type=float, default=0.25)
    parser.add_argument("--spike-neighbour-inner-arcsec", type=float, default=4.0)
    parser.add_argument("--spike-neighbour-outer-arcsec", type=float, default=15.0)
    parser.add_argument("--spike-side-offset-samples", type=int, default=3)
    parser.add_argument("--spike-side-drop-fraction", type=float, default=0.4)
    parser.add_argument("--spike-center-exclusion-arcsec", type=float, default=8.0)
    parser.add_argument("--spike-window-samples", type=int, default=2)
    args = parser.parse_args()
    if args.output_dir is None:
        args.output_dir = remove_foreground_folder(args.pc) / "optimisation"
    return args


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = {row["name"]: row for row in bar.read_rows(args.manifest)}
    selected = [rows[name] for name in args.spike_names + args.control_names if name in rows]
    control_set = set(args.control_names)

    summary_rows = []
    detail_rows = []
    for index, params in enumerate(parameter_grid(args), start=1):
        print(f"Evaluating parameter set {index}: {params}", flush=True)
        results = [evaluate_one(row, params, args) for row in selected]
        for result in results:
            detail_rows.append({**params, **result, "group": "control" if result["name"] in control_set else "spike"})
        spike_results = [r for r in results if r["name"] not in control_set]
        control_results = [r for r in results if r["name"] in control_set]
        mean_spike_coverage = float(np.mean([r["spike_coverage"] for r in spike_results])) if spike_results else 0.0
        mean_control_damage = float(np.mean([r["profile_damage"] for r in control_results])) if control_results else 0.0
        mean_control_mask_fraction = float(np.mean([r["masked_fraction"] for r in control_results])) if control_results else 0.0
        mean_spike_mask_fraction = float(np.mean([r["masked_fraction"] for r in spike_results])) if spike_results else 0.0
        score = (1.0 - mean_spike_coverage) * 10.0 + mean_control_damage * 5.0 + mean_control_mask_fraction * 2.0 + mean_spike_mask_fraction
        summary_rows.append(
            {
                **params,
                "mean_spike_coverage": mean_spike_coverage,
                "mean_control_damage": mean_control_damage,
                "mean_control_mask_fraction": mean_control_mask_fraction,
                "mean_spike_mask_fraction": mean_spike_mask_fraction,
                "score_lower_is_better": score,
            }
        )

    summary_rows.sort(key=lambda row: row["score_lower_is_better"])
    summary_path = args.output_dir / "photutils_parameter_optimisation_summary.csv"
    detail_path = args.output_dir / "photutils_parameter_optimisation_details.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)
    with detail_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(detail_rows[0].keys()))
        writer.writeheader()
        writer.writerows(detail_rows)
    print(f"Wrote {summary_path}")
    print(f"Wrote {detail_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
