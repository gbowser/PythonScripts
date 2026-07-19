#!/usr/bin/env python3
"""Batch-run the SEP foreground-mask routine for S4G galaxies.

This uses the same SEP product generation and deprojected diagnostics as
``interactive_sep_parameter_tester.py`` but runs without opening the Tk GUI.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
import sys
import traceback

import matplotlib

matplotlib.use("Agg", force=True)

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
for path in (PROJECT_ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.append(str(path))

import interactive_galclean_parameter_tester as display  # noqa: E402
import interactive_sep_parameter_tester as sep_gui  # noqa: E402
from machine_paths import PC_RESEARCH_FOLDERS, remove_foreground_folder  # noqa: E402


DEFAULT_OUTPUT_SUBDIR = "batch_sep_parameter_tester"


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

    figure = Figure(figsize=(12.0, 15.6), dpi=100, constrained_layout=True)
    FigureCanvasAgg(figure)
    grid = figure.add_gridspec(5, 2, height_ratios=[0.26, 1.0, 1.0, 1.0, 0.72])
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
    ax_parameters.text(
        0.5,
        0.5,
        "SEP foreground detection   "
        f"units=Pixels   detect_on={params['detect_on']}   "
        f"thresh={float(params['detect_thresh']):.1f}   minarea={int(params['minarea'])}   "
        f"deblend={int(params['deblend_nthresh'])}/{float(params['deblend_cont']):.4f}   "
        f"dilation={int(params['dilation_radius'])}   "
        f"bkg={float(products['background_level']):.4g}, rms={float(products['background_rms']):.4g}   |   "
        f"segments={kept}/{raw}   masked={masked_fraction:.2%}",
        transform=ax_parameters.transAxes,
        ha="center",
        va="center",
        fontsize=9.3,
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


def output_png_path(output_dir: Path, name: str, params: dict[str, float | int | str]) -> Path:
    stem = (
        f"{display.safe_filename(name)}_sep_"
        f"thr{float(params['detect_thresh']):.1f}_"
        f"area{int(params['minarea'])}_"
        f"deb{float(params['deblend_cont']):.4f}_"
        f"dil{int(params['dilation_radius'])}"
    )
    return output_dir / f"{display.safe_filename(stem)}.png"


def selected_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows = display.rows_with_images_for_pc(display.read_manifest(args.manifest), args.pc)
    if args.names:
        wanted = {name.casefold() for name in args.names}
        rows = [row for row in rows if row["name"].casefold() in wanted]
    if args.limit is not None:
        rows = rows[: args.limit]
    return rows


def run_one(row: dict[str, str], args: argparse.Namespace, output_dir: Path) -> dict[str, str | int | float]:
    name = row["name"]
    geometry = display.required_geometry(row)
    if geometry is None:
        raise ValueError(f"{name} has incomplete geometry in {args.manifest}.")
    data, _header = sep_gui.load_fits(display.image_path_for_pc(row, args.pc))
    params = default_params(args)
    products = sep_gui.sep_products(data, params, geometry)
    figure = draw_products(name, data, products, params, geometry)
    png_path = output_png_path(output_dir, name, params)
    figure.savefig(png_path, dpi=args.dpi)

    kept = sum(1 for product_row in products["rows"] if product_row.get("kept"))
    raw = len(products["rows"])
    masked_fraction = np.count_nonzero(products["mask"]) / products["mask"].size
    return {
        "name": name,
        "status": "ok",
        "png": str(png_path),
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
    parser.add_argument("--names", nargs="*", default=[])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dpi", type=int, default=180)
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir or (remove_foreground_folder(args.pc) / DEFAULT_OUTPUT_SUBDIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = selected_rows(args)
    if not rows:
        raise RuntimeError("No matching galaxies with available FITS images were found.")

    started = datetime.now()
    print(f"Batch SEP run started {started:%Y-%m-%d %H:%M:%S}")
    print(f"Galaxies: {len(rows)}")
    print(f"Output: {output_dir}")

    summary_rows: list[dict[str, str | int | float]] = []
    for index, row in enumerate(rows, start=1):
        name = row["name"]
        print(f"[{index}/{len(rows)}] {name} ...", flush=True)
        try:
            result = run_one(row, args, output_dir)
            print(
                f"  ok: kept {result['kept_segments']}/{result['raw_segments']} segments, "
                f"masked {float(result['masked_fraction']):.2%}"
            )
        except Exception as exc:  # noqa: BLE001
            result = {
                "name": name,
                "status": "failed",
                "png": "",
                "raw_segments": "",
                "kept_segments": "",
                "masked_fraction": "",
                "background_level": "",
                "background_rms": "",
                "error": str(exc),
            }
            print(f"  failed: {exc}")
            traceback.print_exc()
        summary_rows.append(result)

    summary_path = output_dir / "sep_batch_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
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
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    ok_count = sum(1 for row in summary_rows if row["status"] == "ok")
    failed_count = len(summary_rows) - ok_count
    finished = datetime.now()
    print(f"Batch SEP run finished {finished:%Y-%m-%d %H:%M:%S}")
    print(f"Successful: {ok_count}; failed: {failed_count}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
