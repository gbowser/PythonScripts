#!/usr/bin/env python3
"""Batch-run the SEP foreground-mask routine for S4G galaxies.

This uses the shared SEP processing and deprojected diagnostics directly,
without opening a Tk GUI.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import sys
import time
import traceback
import warnings

import matplotlib

matplotlib.use("Agg", force=True)

from astropy.io import fits
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
for path in (PROJECT_ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.append(str(path))

import foreground_display_helpers as display  # noqa: E402
import sep_processing as sep_gui  # noqa: E402
from machine_paths import PC_RESEARCH_FOLDERS, remove_foreground_folder  # noqa: E402


DEFAULT_OUTPUT_SUBDIR = "SEP all galaxy batch"
DEFAULT_DPI = 180
DEFAULT_SOURCE = "latest"


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_duration(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    hours, remainder = divmod(int(round(seconds)), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def expected_completion_text(seconds_remaining: float) -> str:
    return datetime.fromtimestamp(time.time() + max(0.0, float(seconds_remaining))).strftime("%Y-%m-%d %H:%M:%S")


def log(message: str) -> None:
    print(f"[{timestamp()}] {message}", flush=True)


def latest_best_json(pc_name: str, source: str) -> Path | None:
    root = remove_foreground_folder(pc_name)
    candidates = []
    if source in {"latest", "spike-gate"}:
        candidates.extend((root / "sep spike optimisation").glob("*/sep_spike_optimisation_best.json"))
    if source in {"latest", "toy-object"}:
        candidates.extend((root / "sep toy optimisation").glob("*/sep_toy_object_optimisation_best.json"))
    candidates = sorted([path for path in candidates if path.is_file()], key=lambda path: path.stat().st_mtime)
    return candidates[-1] if candidates else None


def load_best_params(path: Path) -> dict[str, float | int | str]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    params = payload.get("params", payload)
    if not isinstance(params, dict):
        raise ValueError(f"Best-parameter JSON does not contain a parameter dictionary: {path}")

    loaded = {
        "detect_on": "residual",
        "detect_thresh": sep_gui.DEFAULT_DETECT_THRESH,
        "minarea": sep_gui.DEFAULT_MINAREA,
        "deblend_nthresh": sep_gui.DEFAULT_DEBLEND_NTHRESH,
        "deblend_cont": sep_gui.DEFAULT_DEBLEND_CONT,
        "back_size": sep_gui.DEFAULT_BACK_SIZE,
        "filter_size": sep_gui.DEFAULT_FILTER_SIZE,
        "dilation_radius": sep_gui.DEFAULT_DILATION_RADIUS,
        "max_area": sep_gui.DEFAULT_MAX_AREA,
        "max_elongation": sep_gui.DEFAULT_MAX_ELONGATION,
        "exclude_center_pixels": sep_gui.DEFAULT_EXCLUDE_CENTER_PIXELS,
    }
    for key, value in params.items():
        if key in loaded:
            loaded[key] = math.nan if value == "NaN" else value
    return loaded


def best_json_source(path: Path) -> str:
    name = path.name.casefold()
    if "spike" in name:
        return "spike-gate"
    if "toy" in name:
        return "toy-object"
    return "best-json"


def params_from_args(args: argparse.Namespace) -> dict[str, float | int | str]:
    best_json = args.best_json or args.params_json or latest_best_json(args.pc, args.source)
    if best_json is not None:
        params = load_best_params(best_json)
        params["_source_label"] = args.run_label or best_json.parent.name
        params["_best_json"] = str(best_json)
        params["_best_json_source"] = best_json_source(best_json)
        return params
    if args.require_best_json:
        raise FileNotFoundError(
            "No SEP best-parameter JSON found. Pass --best-json, or use --source spike-gate/toy-object after that optimiser has a best JSON."
        )
    params = default_params(args)
    params["_source_label"] = args.run_label or "manual SEP parameters"
    return params


def default_params(args: argparse.Namespace) -> dict[str, float | int | str]:
    return {
        "detect_on": args.detect_on,
        "detect_thresh": args.detect_thresh,
        "minarea": args.minarea,
        "deblend_nthresh": args.deblend_nthresh,
        "deblend_cont": args.deblend_cont,
        "back_size": args.back_size,
        "filter_size": args.filter_size,
        "dilation_radius": args.dilation_radius,
        "max_area": args.max_area,
        "max_elongation": args.max_elongation,
        "exclude_center_pixels": args.exclude_center_pixels,
    }


def draw_bar_guides(ax, half_width: float, bar_sma: float) -> None:
    ax.axhline(0.0, color="#1f77b4", linewidth=1.5)
    ax.axhline(half_width, color="#1f77b4", linestyle="--", linewidth=1.0, alpha=0.9)
    ax.axhline(-half_width, color="#1f77b4", linestyle="--", linewidth=1.0, alpha=0.9)
    ax.axvline(0.0, color="#d62728", linestyle="--", linewidth=1.0, alpha=0.8)
    ax.plot([-bar_sma, bar_sma], [0.0, 0.0], "o", color="#1f77b4", ms=4)


def draw_central_exclusion(ax, radius_arcsec: float) -> None:
    if radius_arcsec <= 0:
        return
    theta = np.linspace(0.0, 2.0 * np.pi, 241)
    ax.plot(
        radius_arcsec * np.cos(theta),
        radius_arcsec * np.sin(theta),
        color="#ffd400",
        linestyle="--",
        linewidth=1.4,
        alpha=0.95,
    )


def draw_isophote(ax, image, x_axis, y_axis, extent, title, half_width, bar_sma, central_exclusion_arcsec) -> None:
    log_image, levels = display.robust_log_image(image)
    ax.imshow(log_image, origin="lower", extent=extent, cmap="Greys", vmin=levels[0], vmax=levels[-1])
    ax.contour(x_axis, y_axis, log_image, levels=levels[1:-1], colors="0.25", linewidths=0.45)
    draw_bar_guides(ax, half_width, bar_sma)
    draw_central_exclusion(ax, central_exclusion_arcsec)
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title)


def draw_profile(
    ax,
    image,
    x_axis,
    y_axis,
    half_width,
    bar_sma,
    central_exclusion_arcsec,
    title,
    mask_profile: np.ndarray | None = None,
) -> None:
    radii, intensity = display.bar_major_axis_profile(image, x_axis, y_axis, half_width)
    if mask_profile is not None:
        bridged_intensity, bridged_samples = sep_gui.fill_profile_with_log_linear_bridges(intensity, mask_profile)
        displayed_intensity = np.array(intensity, copy=True)
        displayed_intensity[bridged_samples] = np.nan
    else:
        bridged_intensity = None
        bridged_samples = np.zeros(intensity.size, dtype=bool)
        displayed_intensity = intensity

    positive = np.isfinite(intensity) & (intensity > 0)
    if bridged_intensity is not None:
        positive |= np.isfinite(bridged_intensity) & (bridged_intensity > 0)
    ymin, ymax = (1.0, 10.0)
    if np.any(positive):
        reference = bridged_intensity if bridged_intensity is not None else intensity
        ymin = max(float(np.nanpercentile(reference[positive], 2)) * 0.8, np.finfo(float).tiny)
        ymax = float(np.nanmax(reference[positive])) * 1.25

    ax.semilogy(radii, displayed_intensity, color="#1f77b4", linewidth=1.4)
    if bridged_intensity is not None:
        for start, stop in sep_gui.contiguous_true_runs(bridged_samples):
            ax.axvspan(radii[start], radii[stop], color="#f4a6b8", alpha=0.28, linewidth=0)
        bridge_label = "log-linear interpolation"
        for start, stop in sep_gui.contiguous_true_runs(bridged_samples):
            plot_start = max(0, start - 1)
            plot_stop = min(bridged_intensity.size - 1, stop + 1)
            bridge_slice = slice(plot_start, plot_stop + 1)
            bridge_good = (
                np.isfinite(radii[bridge_slice])
                & np.isfinite(bridged_intensity[bridge_slice])
                & (bridged_intensity[bridge_slice] > 0)
            )
            if np.count_nonzero(bridge_good) < 2:
                continue
            ax.semilogy(
                radii[bridge_slice][bridge_good],
                bridged_intensity[bridge_slice][bridge_good],
                color="#1f77b4",
                linestyle="--",
                linewidth=1.4,
                label=bridge_label,
            )
            bridge_label = "_nolegend_"

    ax.axvline(bar_sma, color="#1f77b4", linewidth=1.0)
    ax.axvline(-bar_sma, color="#1f77b4", linewidth=1.0)
    if central_exclusion_arcsec > 0:
        ax.axvline(central_exclusion_arcsec, color="#b59b00", linestyle="--", linewidth=1.1, alpha=0.95)
        ax.axvline(-central_exclusion_arcsec, color="#b59b00", linestyle="--", linewidth=1.1, alpha=0.95)
    ax.axvline(0.0, color="0.6", linewidth=0.7)
    ax.set_xlim(float(x_axis[0]), float(x_axis[-1]))
    ax.set_ylim(ymin, ymax)
    ax.set_xlabel("deprojected bar-major radius [arcsec]")
    ax.set_ylabel("intensity")
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.2)


def draw_products(name: str, original: np.ndarray, products: dict, params: dict, geometry: dict[str, float]) -> Figure:
    cleaned = np.asarray(products["cleaned"], dtype=float)
    residual = np.asarray(products["residual"], dtype=float)
    mask = np.asarray(products["mask"], dtype=bool)

    radius_arcsec = display.profile_radius_pixels(original, geometry) * geometry["pixel_scale"]
    original_view, x_axis, y_axis = display.deproject_bar_aligned_cutout(original, geometry, radius_arcsec)
    cleaned_view, _, _ = display.deproject_bar_aligned_cutout(cleaned, geometry, radius_arcsec)
    residual_view, _, _ = display.deproject_bar_aligned_cutout(residual, geometry, radius_arcsec)
    mask_view, _, _ = display.deproject_bar_aligned_cutout(mask.astype(float), geometry, radius_arcsec, order=0)
    mask_view = np.isfinite(mask_view) & (mask_view > 0.5)

    extent = [x_axis[0], x_axis[-1], y_axis[0], y_axis[-1]]
    half_width = 0.5 * sep_gui.DEFAULT_PROFILE_WIDTH_PIXELS * geometry["pixel_scale"]
    mask_profile = sep_gui.profile_mask_at_bar_major(mask_view, y_axis, half_width)
    bar_sma = display.bar_sma_deprojected_arcsec(geometry)
    central_exclusion_arcsec = float(params["exclude_center_pixels"]) * geometry["pixel_scale"]

    figure = Figure(figsize=(12.0, 15.8), dpi=100, constrained_layout=True)
    FigureCanvasAgg(figure)
    grid = figure.add_gridspec(5, 2, height_ratios=[0.38, 1.0, 1.0, 1.0, 0.72])
    ax_parameters = figure.add_subplot(grid[0, :])
    ax_original = figure.add_subplot(grid[1, 0])
    ax_cleaned = figure.add_subplot(grid[1, 1])
    ax_residual = figure.add_subplot(grid[2, 0])
    ax_mask = figure.add_subplot(grid[2, 1])
    ax_original_isophote = figure.add_subplot(grid[3, 0])
    ax_cleaned_isophote = figure.add_subplot(grid[3, 1])
    ax_original_profile = figure.add_subplot(grid[4, 0])
    ax_cleaned_profile = figure.add_subplot(grid[4, 1])

    kept = sum(1 for row in products["rows"] if row.get("kept"))
    raw = len(products["rows"])
    masked_fraction = np.count_nonzero(mask) / mask.size
    ax_parameters.set_axis_off()
    parameter_text = "\n".join(
        [
            f"SEP foreground detection | units=Pixels | detect_on={params['detect_on']}",
            (
                f"thresh={float(params['detect_thresh']):.1f} | minarea={int(params['minarea'])} | "
                f"deblend={int(params['deblend_nthresh'])}/{float(params['deblend_cont']):.4f} | "
                f"dilation={int(params['dilation_radius'])}"
            ),
            (
                f"bkg={float(products['background_level']):.4g} | rms={float(products['background_rms']):.4g} | "
                f"segments={kept}/{raw} | masked={masked_fraction:.2%}"
            ),
        ]
    )
    ax_parameters.text(
        0.5,
        0.5,
        parameter_text,
        transform=ax_parameters.transAxes,
        ha="center",
        va="center",
        fontsize=9.0,
        linespacing=1.28,
        color="0.12",
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "#F4F6F9", "edgecolor": "#6B7280", "linewidth": 0.8},
    )

    for ax in [
        ax_original,
        ax_cleaned,
        ax_residual,
        ax_mask,
        ax_original_isophote,
        ax_cleaned_isophote,
        ax_original_profile,
        ax_cleaned_profile,
    ]:
        ax.set_xlabel("bar-aligned arcsec")
        ax.set_ylabel("deprojected arcsec")

    vmin, vmax = display.robust_limits(original_view)
    ax_original.imshow(original_view, origin="lower", cmap="gist_gray_r", vmin=vmin, vmax=vmax, extent=extent)
    draw_bar_guides(ax_original, half_width, bar_sma)
    draw_central_exclusion(ax_original, central_exclusion_arcsec)
    ax_original.set_title(f"{name} centered original")

    ax_cleaned.imshow(cleaned_view, origin="lower", cmap="gist_gray_r", vmin=vmin, vmax=vmax, extent=extent)
    draw_bar_guides(ax_cleaned, half_width, bar_sma)
    draw_central_exclusion(ax_cleaned, central_exclusion_arcsec)
    ax_cleaned.set_title("SEP masked preview")

    rvmin, rvmax = display.robust_limits(residual_view, 1.0, 99.0)
    limit = max(abs(rvmin), abs(rvmax))
    ax_residual.imshow(residual_view, origin="lower", cmap="coolwarm", vmin=-limit, vmax=limit, extent=extent)
    draw_bar_guides(ax_residual, half_width, bar_sma)
    draw_central_exclusion(ax_residual, central_exclusion_arcsec)
    ax_residual.set_title("Residual detection image")

    ax_mask.imshow(original_view, origin="lower", cmap="gist_gray_r", vmin=vmin, vmax=vmax, extent=extent)
    ax_mask.imshow(np.ma.masked_where(~mask_view, mask_view), origin="lower", cmap="autumn", alpha=0.55, extent=extent)
    draw_bar_guides(ax_mask, half_width, bar_sma)
    draw_central_exclusion(ax_mask, central_exclusion_arcsec)
    ax_mask.set_title(f"Mask | thresh={float(params['detect_thresh']):.1f}, area={int(params['minarea'])}")

    draw_isophote(
        ax_original_isophote,
        original_view,
        x_axis,
        y_axis,
        extent,
        f"{name} original isophotes",
        half_width,
        bar_sma,
        central_exclusion_arcsec,
    )
    draw_isophote(
        ax_cleaned_isophote,
        cleaned_view,
        x_axis,
        y_axis,
        extent,
        "SEP processed isophotes",
        half_width,
        bar_sma,
        central_exclusion_arcsec,
    )
    draw_profile(
        ax_original_profile,
        original_view,
        x_axis,
        y_axis,
        half_width,
        bar_sma,
        central_exclusion_arcsec,
        f"{name} original bar-major profile",
    )
    draw_profile(
        ax_cleaned_profile,
        original_view,
        x_axis,
        y_axis,
        half_width,
        bar_sma,
        central_exclusion_arcsec,
        "SEP processed bar-major profile",
        mask_profile=mask_profile,
    )
    return figure


def output_png_path(report_dir: Path, name: str, params: dict[str, float | int | str]) -> Path:
    stem = (
        f"{display.safe_filename(name)}_sep_"
        f"thr{float(params['detect_thresh']):.1f}_"
        f"area{int(params['minarea'])}_"
        f"deb{float(params['deblend_cont']):.4f}_"
        f"dil{int(params['dilation_radius'])}"
    )
    return report_dir / f"{display.safe_filename(stem)}.png"


def selected_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows = display.rows_with_images_for_pc(display.read_manifest(args.manifest), args.pc)
    if args.names:
        wanted = {name.casefold() for name in args.names}
        rows = [row for row in rows if row["name"].casefold() in wanted]
    max_images = args.max_images if args.max_images is not None else args.limit
    if max_images is not None:
        rows = rows[: max_images]
    return rows


def write_cleaned_fits(path: Path, data: np.ndarray, header: fits.Header, mask: np.ndarray, params: dict) -> None:
    output_header = header.copy()
    output_header["FGMASK"] = ("SEP", "Foreground removal method")
    output_header["SEPTHR"] = (float(params["detect_thresh"]), "SEP detection threshold")
    output_header["SEPMINA"] = (int(params["minarea"]), "SEP minimum area")
    output_header["SEPDEBN"] = (int(params["deblend_nthresh"]), "SEP deblend thresholds")
    output_header["SEPDEBC"] = (float(params["deblend_cont"]), "SEP deblend contrast")
    output_header["SEPDIL"] = (int(params["dilation_radius"]), "SEP dilation radius")
    fits.PrimaryHDU(np.asarray(data, dtype=np.float32), header=output_header).writeto(path, overwrite=True)
    mask_path = path.with_name(path.stem + "_mask.fits")
    fits.PrimaryHDU(np.asarray(mask, dtype=np.uint8), header=header).writeto(mask_path, overwrite=True)


def append_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def completed_names_from_summary(path: Path) -> set[str]:
    if not path.exists():
        return set()
    completed: set[str] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("status") == "ok" and row.get("name"):
                completed.add(str(row["name"]))
    return completed


def run_one(
    row: dict[str, str],
    args: argparse.Namespace,
    params: dict[str, float | int | str],
    report_dir: Path,
    fits_dir: Path,
) -> dict[str, str | int | float]:
    name = row["name"]
    geometry = display.required_geometry(row)
    if geometry is None:
        raise ValueError(f"{name} has incomplete geometry in {args.manifest}.")
    data, header = sep_gui.load_fits(display.image_path_for_pc(row, args.pc))
    products = sep_gui.sep_products(data, params, geometry)
    figure = draw_products(name, data, products, params, geometry)
    png_path = output_png_path(report_dir, name, params)
    figure.savefig(png_path, dpi=args.dpi)

    cleaned_fits_path = ""
    if args.save_cleaned_fits:
        cleaned_fits_path = str(fits_dir / f"{display.safe_filename(name)}_sep_optimised_cleaned.fits")
        write_cleaned_fits(Path(cleaned_fits_path), np.asarray(products["cleaned"], dtype=float), header, products["mask"], params)

    kept = sum(1 for product_row in products["rows"] if product_row.get("kept"))
    raw = len(products["rows"])
    masked_fraction = np.count_nonzero(products["mask"]) / products["mask"].size
    return {
        "name": name,
        "status": "ok",
        "report_png": str(png_path),
        "cleaned_fits": cleaned_fits_path,
        "raw_segments": raw,
        "kept_segments": kept,
        "masked_fraction": masked_fraction,
        "background_level": float(products["background_level"]),
        "background_rms": float(products["background_rms"]),
        "error": "",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=sep_gui.DEFAULT_MANIFEST)
    parser.add_argument("--pc", choices=sorted(PC_RESEARCH_FOLDERS), default=sep_gui.DEFAULT_PC)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--resume-output-dir",
        type=Path,
        default=None,
        help="Continue a stopped batch folder, skipping galaxies already marked ok in the summary CSV.",
    )
    parser.add_argument(
        "--best-json",
        type=Path,
        help="Path to sep_spike_optimisation_best.json or sep_toy_object_optimisation_best.json.",
    )
    parser.add_argument(
        "--params-json",
        type=Path,
        help="Alias for --best-json, useful when the best-parameter file has been copied or renamed.",
    )
    parser.add_argument(
        "--source",
        choices=["latest", "spike-gate", "toy-object", "manual"],
        default=DEFAULT_SOURCE,
        help="Which SEP optimiser family to search when --best-json is not supplied.",
    )
    parser.add_argument(
        "--run-label",
        default=None,
        help="Short label shown in diagnostics and used in the default output folder name.",
    )
    parser.add_argument(
        "--require-best-json",
        action="store_true",
        help="Fail if no SEP optimiser best JSON can be found.",
    )
    parser.add_argument("--names", nargs="*", default=[])
    parser.add_argument("--limit", type=int, default=None, help="Deprecated alias for --max-images.")
    parser.add_argument("--max-images", type=int, default=None)
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    parser.add_argument(
        "--save-cleaned-fits",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Optionally write cleaned FITS products and masks. Default is reports/summary only.",
    )
    parser.add_argument("--detect-on", choices=["residual", "original"], default="residual")
    parser.add_argument("--detect-thresh", type=float, default=sep_gui.DEFAULT_DETECT_THRESH)
    parser.add_argument("--minarea", type=int, default=sep_gui.DEFAULT_MINAREA)
    parser.add_argument("--deblend-nthresh", type=int, default=sep_gui.DEFAULT_DEBLEND_NTHRESH)
    parser.add_argument("--deblend-cont", type=float, default=sep_gui.DEFAULT_DEBLEND_CONT)
    parser.add_argument("--back-size", type=int, default=sep_gui.DEFAULT_BACK_SIZE)
    parser.add_argument("--filter-size", type=int, default=sep_gui.DEFAULT_FILTER_SIZE)
    parser.add_argument("--dilation-radius", type=int, default=sep_gui.DEFAULT_DILATION_RADIUS)
    parser.add_argument("--max-area", type=int, default=sep_gui.DEFAULT_MAX_AREA)
    parser.add_argument("--max-elongation", type=float, default=sep_gui.DEFAULT_MAX_ELONGATION)
    parser.add_argument("--exclude-center-pixels", type=float, default=sep_gui.DEFAULT_EXCLUDE_CENTER_PIXELS)
    parser.add_argument(
        "--replace-summary",
        action="store_true",
        help="Replace the summary CSV files in the output folder before writing this run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.resume_output_dir is not None and args.output_dir is not None:
        raise ValueError("Use either --resume-output-dir or --output-dir, not both.")

    params = params_from_args(args)
    timestamp_dir = datetime.now().strftime("%Y%m%d_%H%M%S")
    label_source = args.run_label or params.get("_source_label", args.source)
    best_json_kind = str(params.get("_best_json_source", args.source))
    if best_json_kind == "spike-gate":
        default_label = "sep_spike_gate"
    elif best_json_kind == "toy-object":
        default_label = "sep_toy_object"
    elif args.best_json or args.params_json:
        default_label = display.safe_filename(str(label_source))
    else:
        default_label = "sep_manual"
    label_slug = display.safe_filename(default_label)
    output_dir = args.resume_output_dir or args.output_dir or (
        remove_foreground_folder(args.pc) / DEFAULT_OUTPUT_SUBDIR / f"{label_slug}_{timestamp_dir}"
    )
    report_dir = output_dir
    fits_dir = output_dir / "cleaned_fits"
    report_dir.mkdir(parents=True, exist_ok=True)
    if args.save_cleaned_fits:
        fits_dir.mkdir(parents=True, exist_ok=True)

    config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    config["params"] = {
        key: ("NaN" if isinstance(value, float) and math.isnan(value) else value)
        for key, value in params.items()
    }
    (output_dir / "sep_optimised_apply_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    rows = selected_rows(args)
    if not rows:
        raise RuntimeError("No matching galaxies with available FITS images were found.")

    summary_path = output_dir / "sep_optimised_apply_summary.csv"
    legacy_summary_path = output_dir / "sep_batch_summary.csv"
    if args.replace_summary:
        for path in (summary_path, legacy_summary_path):
            if path.exists():
                path.unlink()
    completed_names = completed_names_from_summary(summary_path) if args.resume_output_dir is not None else set()
    if completed_names:
        rows = [row for row in rows if row["name"] not in completed_names]
        log(f"Resume mode: skipping {len(completed_names)} galaxies already marked ok; {len(rows)} remain.")

    started = datetime.now()
    log(f"Batch SEP run started {started:%Y-%m-%d %H:%M:%S}")
    log(f"Galaxies: {len(rows)}")
    log(f"Output: {output_dir}")

    fieldnames = [
        "name",
        "status",
        "report_png",
        "cleaned_fits",
        "raw_segments",
        "kept_segments",
        "masked_fraction",
        "background_level",
        "background_rms",
        "elapsed_seconds",
        "error",
    ]
    ok_count = 0
    failed_count = 0
    run_started = time.perf_counter()
    for index, row in enumerate(rows, start=1):
        name = row["name"]
        item_started = time.perf_counter()
        log(f"[{index}/{len(rows)}] {name} ...")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                result = run_one(row, args, params, report_dir, fits_dir)
            ok_count += 1
        except Exception as exc:  # noqa: BLE001
            failed_count += 1
            result = {
                "name": name,
                "status": "failed",
                "report_png": "",
                "cleaned_fits": "",
                "raw_segments": "",
                "kept_segments": "",
                "masked_fraction": "",
                "background_level": "",
                "background_rms": "",
                "error": str(exc),
            }
            log(f"  failed: {exc}")
            traceback.print_exc()
        elapsed = time.perf_counter() - item_started
        result["elapsed_seconds"] = elapsed
        append_csv(summary_path, [result], fieldnames)
        remaining = len(rows) - index
        average = (time.perf_counter() - run_started) / index
        seconds_remaining = remaining * average
        if result["status"] == "ok":
            log(
                f"  ok: kept {result['kept_segments']}/{result['raw_segments']} segments, "
                f"masked {float(result['masked_fraction']):.2%} elapsed={format_duration(elapsed)} "
                f"remaining={remaining} rough_eta={format_duration(seconds_remaining)} "
                f"expected_completion={expected_completion_text(seconds_remaining)}"
            )
        else:
            log(
                f"  failed elapsed={format_duration(elapsed)} "
                f"remaining={remaining} rough_eta={format_duration(seconds_remaining)} "
                f"expected_completion={expected_completion_text(seconds_remaining)}"
            )

    finished = datetime.now()
    if not legacy_summary_path.exists() and summary_path.exists():
        with summary_path.open(newline="", encoding="utf-8") as src, legacy_summary_path.open(
            "w", newline="", encoding="utf-8"
        ) as dst:
            reader = csv.DictReader(src)
            writer = csv.DictWriter(
                dst,
                fieldnames=[
                    "name",
                    "status",
                    "png",
                    "raw_segments",
                    "kept_segments",
                    "masked_fraction",
                    "background_level",
                    "background_rms",
                    "error",
                ],
                extrasaction="ignore",
            )
            writer.writeheader()
            for row in reader:
                row["png"] = row.get("report_png", "")
                writer.writerow(row)
    log(f"Batch SEP run finished {finished:%Y-%m-%d %H:%M:%S}")
    log(f"Successful: {ok_count}; failed: {failed_count}")
    log(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
