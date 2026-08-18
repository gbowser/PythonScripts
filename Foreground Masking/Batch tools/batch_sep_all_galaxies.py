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
import zlib

import matplotlib

matplotlib.use("Agg", force=True)

from astropy.io import fits
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np
from scipy.ndimage import label as label_components


SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
SUPPORT_DIRS = tuple(FOREGROUND_ROOT / name for name in ("Batch tools", "PhotUtils", "Interactive tools", "Shared", "Utilities"))
for path in (PROJECT_ROOT, FOREGROUND_ROOT, SCRIPT_DIR, *SUPPORT_DIRS):
    if str(path) not in sys.path:
        sys.path.append(str(path))
sys.path.append(str(FOREGROUND_ROOT / "Optimisation"))

import foreground_display_helpers as display  # noqa: E402
import sep_processing as sep_gui  # noqa: E402
import optimise_toy_objects_SEP as sep_toy_opt  # noqa: E402
from machine_paths import PC_RESEARCH_FOLDERS, remove_foreground_folder  # noqa: E402


DEFAULT_OUTPUT_SUBDIR = "SEP all galaxy batch"
DEFAULT_DPI = 180
DEFAULT_SOURCE = "latest"
EXPECTED_CLEAN_GALAXIES = 40


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
        "detect_on": "original",
        "spike_gate_detect_on": "residual",
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
        if key in loaded and key != "detect_on":
            loaded[key] = math.nan if value == "NaN" else value
    # SEP science detection is a pipeline invariant.  Do not allow historical
    # optimiser JSON files to restore the obsolete residual-image mode.
    loaded["detect_on"] = "original"
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
        "detect_on": "original",
        "spike_gate_detect_on": args.spike_gate_detect_on,
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
    contour_levels = np.unique(np.asarray(levels[1:-1], dtype=float))
    contour_levels = contour_levels[np.isfinite(contour_levels)]
    if contour_levels.size:
        ax.contour(x_axis, y_axis, log_image, levels=contour_levels, colors="0.25", linewidths=0.45)
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
    toy_mask_profile: np.ndarray | None = None,
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

    positive_profile = np.isfinite(displayed_intensity) & (displayed_intensity > 0)
    if np.any(positive_profile):
        ax.semilogy(radii, displayed_intensity, color="#1f77b4", linewidth=1.4)
    else:
        # An entirely non-positive profile has no logarithmic representation.
        # Keep the panel usable and avoid Matplotlib's noisy log-scale warning.
        ax.plot(radii, displayed_intensity, color="#1f77b4", linewidth=1.4)
    if bridged_intensity is not None:
        toy_samples = bridged_samples & (
            np.asarray(toy_mask_profile, dtype=bool) if toy_mask_profile is not None else np.zeros_like(bridged_samples)
        )
        other_samples = bridged_samples & ~toy_samples
        styles = [
            (toy_samples, "#00a000", "--", "toy-object mask (log-linear bridge)"),
            (other_samples, "red", ":", "other mask (log-linear bridge)"),
        ]
        for styled_samples, colour, linestyle, label in styles:
            bridge_label = label
            for start, stop in sep_gui.contiguous_true_runs(styled_samples):
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
                    color=colour,
                    linestyle=linestyle,
                    linewidth=1.8,
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
    if bridged_intensity is not None and np.any(bridged_samples):
        ax.legend(loc="best", fontsize=7)


def draw_mask_outlines(ax, mask_view: np.ndarray, truth_view: np.ndarray, x_axis: np.ndarray, y_axis: np.ndarray) -> None:
    labels, count = label_components(mask_view, structure=np.ones((3, 3), dtype=np.uint8))
    for component_id in range(1, count + 1):
        component = labels == component_id
        colour = "#00a000" if np.any(component & truth_view) else "red"
        ax.contour(x_axis, y_axis, component.astype(float), levels=[0.5], colors=[colour], linewidths=1.2)


def draw_products(
    name: str,
    original: np.ndarray,
    injected: np.ndarray,
    truth_mask: np.ndarray,
    products: dict,
    params: dict,
    geometry: dict[str, float],
) -> Figure:
    cleaned = np.asarray(products["cleaned"], dtype=float)
    mask = np.asarray(products["mask"], dtype=bool)

    radius_arcsec = display.profile_radius_pixels(original, geometry) * geometry["pixel_scale"]
    original_view, x_axis, y_axis = display.deproject_bar_aligned_cutout(original, geometry, radius_arcsec)
    injected_view, _, _ = display.deproject_bar_aligned_cutout(injected, geometry, radius_arcsec)
    cleaned_view, _, _ = display.deproject_bar_aligned_cutout(cleaned, geometry, radius_arcsec)
    mask_view, _, _ = display.deproject_bar_aligned_cutout(mask.astype(float), geometry, radius_arcsec, order=0)
    mask_view = np.isfinite(mask_view) & (mask_view > 0.5)
    truth_view, _, _ = display.deproject_bar_aligned_cutout(truth_mask.astype(float), geometry, radius_arcsec, order=0)
    truth_view = np.isfinite(truth_view) & (truth_view > 0.5)

    extent = [x_axis[0], x_axis[-1], y_axis[0], y_axis[-1]]
    half_width = 0.5 * sep_gui.DEFAULT_PROFILE_WIDTH_PIXELS * geometry["pixel_scale"]
    mask_profile = sep_gui.profile_mask_at_bar_major(mask_view, y_axis, half_width)
    toy_mask_profile = sep_gui.profile_mask_at_bar_major(mask_view & truth_view, y_axis, half_width)
    bar_sma = display.bar_sma_deprojected_arcsec(geometry)
    central_exclusion_arcsec = float(params["exclude_center_pixels"]) * geometry["pixel_scale"]

    figure = Figure(figsize=(11.5, 17.0), dpi=100, constrained_layout=False)
    FigureCanvasAgg(figure)
    figure.subplots_adjust(left=0.075, right=0.965, top=0.925, bottom=0.055, wspace=0.28, hspace=0.38)
    grid = figure.add_gridspec(4, 2, height_ratios=[1.0, 1.0, 1.0, 0.76])
    ax_original = figure.add_subplot(grid[0, 0])
    ax_injected = figure.add_subplot(grid[0, 1])
    ax_mask = figure.add_subplot(grid[1, 0])
    ax_cleaned = figure.add_subplot(grid[1, 1])
    ax_original_isophote = figure.add_subplot(grid[2, 0])
    ax_cleaned_isophote = figure.add_subplot(grid[2, 1])
    ax_original_profile = figure.add_subplot(grid[3, 0])
    ax_cleaned_profile = figure.add_subplot(grid[3, 1])

    kept = sum(1 for row in products["rows"] if row.get("kept"))
    raw = len(products["rows"])
    masked_fraction = np.count_nonzero(mask) / mask.size
    for ax in [
        ax_original,
        ax_injected,
        ax_cleaned,
        ax_mask,
        ax_original_isophote,
        ax_cleaned_isophote,
        ax_original_profile,
        ax_cleaned_profile,
    ]:
        ax.set_xlabel("bar-aligned arcsec")
        ax.set_ylabel("deprojected arcsec")

    vmin, vmax = display.robust_limits(injected_view)
    ax_original.imshow(original_view, origin="lower", cmap="gist_gray_r", vmin=vmin, vmax=vmax, extent=extent)
    draw_bar_guides(ax_original, half_width, bar_sma)
    draw_central_exclusion(ax_original, central_exclusion_arcsec)
    ax_original.set_title("Galaxy Centered Original")

    ax_injected.imshow(injected_view, origin="lower", cmap="gist_gray_r", vmin=vmin, vmax=vmax, extent=extent)
    draw_bar_guides(ax_injected, half_width, bar_sma)
    draw_central_exclusion(ax_injected, central_exclusion_arcsec)
    ax_injected.set_title("Original + Toys")

    ax_mask.imshow(original_view, origin="lower", cmap="gist_gray_r", vmin=vmin, vmax=vmax, extent=extent)
    ax_mask.imshow(np.ma.masked_where(~mask_view, mask_view), origin="lower", cmap="autumn", alpha=0.55, extent=extent)
    draw_bar_guides(ax_mask, half_width, bar_sma)
    draw_central_exclusion(ax_mask, central_exclusion_arcsec)
    ax_mask.set_title(f"Mask | masked {masked_fraction:.2%}")

    ax_cleaned.imshow(cleaned_view, origin="lower", cmap="gist_gray_r", vmin=vmin, vmax=vmax, extent=extent)
    draw_mask_outlines(ax_cleaned, mask_view, truth_view, x_axis, y_axis)
    draw_bar_guides(ax_cleaned, half_width, bar_sma)
    draw_central_exclusion(ax_cleaned, central_exclusion_arcsec)
    ax_cleaned.set_title("Recovered Image | green=correct, red=incorrect")

    draw_isophote(
        ax_original_isophote,
        original_view,
        x_axis,
        y_axis,
        extent,
        "Orig. Isophotes",
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
        "Processed Isophotes",
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
        "Orig. Bar Major Profile",
    )
    draw_profile(
        ax_cleaned_profile,
        cleaned_view,
        x_axis,
        y_axis,
        half_width,
        bar_sma,
        central_exclusion_arcsec,
        "Processed Bar Major Profile",
        mask_profile=mask_profile,
        toy_mask_profile=toy_mask_profile,
    )
    for ax in [ax_original, ax_injected, ax_mask, ax_cleaned, ax_original_isophote, ax_cleaned_isophote]:
        ax.set_xlim(float(extent[0]), float(extent[1]))
        ax.set_ylim(float(extent[2]), float(extent[3]))
        ax.set_box_aspect(1.0)
    ax_original_profile.set_xlim(float(extent[0]), float(extent[1]))
    ax_cleaned_profile.set_xlim(float(extent[0]), float(extent[1]))
    figure.suptitle(
        f"{name} | SEP Toy Objects | segments={kept}/{raw} | green=toy recovery, red=false mask",
        fontsize=11,
        fontweight="bold",
        y=0.982,
    )
    FigureCanvasAgg(figure).draw()
    left = ax_original.get_position()
    right = ax_injected.get_position()
    left_profile = ax_original_profile.get_position()
    right_profile = ax_cleaned_profile.get_position()
    ax_original_profile.set_position([left.x0, left_profile.y0, left.width, left_profile.height])
    ax_cleaned_profile.set_position([right.x0, right_profile.y0, right.width, right_profile.height])
    return figure


def load_clean_galaxy_names(path: Path, expected_count: int = EXPECTED_CLEAN_GALAXIES) -> set[str]:
    if not path.is_file():
        raise FileNotFoundError(f"Clean-galaxy list not found: {path}")
    names = {line.strip().casefold() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()}
    if len(names) != expected_count:
        raise ValueError(f"Expected {expected_count} unique clean galaxies in {path}; found {len(names)}.")
    return names


def output_png_path(
    report_dir: Path,
    name: str,
    params: dict[str, float | int | str],
    clean_galaxy_names: set[str],
) -> Path:
    stem = (
        f"{display.safe_filename(name)}_sep_"
        f"thr{float(params['detect_thresh']):.1f}_"
        f"area{int(params['minarea'])}_"
        f"deb{float(params['deblend_cont']):.4f}_"
        f"dil{int(params['dilation_radius'])}"
    )
    suffix = "_clean" if name.casefold() in clean_galaxy_names else ""
    return report_dir / f"{display.safe_filename(stem)}{suffix}.png"


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
    clean_galaxy_names: set[str],
) -> dict[str, str | int | float]:
    name = row["name"]
    geometry = display.required_geometry(row)
    if geometry is None:
        raise ValueError(f"{name} has incomplete geometry in {args.manifest}.")
    data, header = sep_gui.load_fits(display.image_path_for_pc(row, args.pc))
    if args.toy_diagnostics:
        galaxy_seed = int(args.toy_seed) + zlib.crc32(name.casefold().encode("utf-8"))
        injected, truth_mask, _truth_labels, _toys = sep_toy_opt.inject_toys(
            name,
            data,
            geometry,
            toys_per_image=int(args.toys_per_image),
            rng=np.random.default_rng(galaxy_seed),
            truth_dilation=int(args.truth_dilation),
        )
    else:
        injected = np.asarray(data, dtype=float)
        truth_mask = np.zeros(data.shape, dtype=bool)
    products = sep_gui.sep_products(injected, params, geometry)
    figure = draw_products(name, data, injected, truth_mask, products, params, geometry)
    png_path = output_png_path(report_dir, name, params, clean_galaxy_names)
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
    parser.add_argument("--toy-diagnostics", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--toys-per-image", type=int, default=6)
    parser.add_argument("--toy-seed", type=int, default=202608299)
    parser.add_argument("--truth-dilation", type=int, default=1)
    parser.add_argument(
        "--clean-galaxies-file",
        type=Path,
        default=None,
        help="Validated 40-galaxy list used to append _clean to calibration report PNGs. "
        "Defaults to CleanGalaxies.txt in the selected PC's Remove foreground objects folder.",
    )
    parser.add_argument(
        "--save-cleaned-fits",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Optionally write cleaned FITS products and masks. Default is reports/summary only.",
    )
    parser.add_argument(
        "--detect-on",
        choices=["original"],
        default="original",
        help="SEP detection is constrained to the original science image.",
    )
    parser.add_argument(
        "--spike-gate-detect-on",
        choices=["residual", "original"],
        default="residual",
        help="Provenance label for the Spike Gate source image used during optimisation.",
    )
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
    clean_galaxies_file = args.clean_galaxies_file or (remove_foreground_folder(args.pc) / "CleanGalaxies.txt")
    clean_galaxy_names = load_clean_galaxy_names(clean_galaxies_file)
    log(f"Filename calibration list: {clean_galaxies_file} ({len(clean_galaxy_names)} galaxies; suffix=_clean)")
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
                result = run_one(row, args, params, report_dir, fits_dir, clean_galaxy_names)
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
