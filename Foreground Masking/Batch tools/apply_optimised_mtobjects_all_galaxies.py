#!/usr/bin/env python3
"""Apply optimised MTObjects foreground removal to S4G galaxies.

This batch runner loads an Optuna/MTObjects best-parameter JSON from either
the Spike Gate or toy-object optimiser, applies the global MTObjects mask to
each usable galaxy, and writes one PNG report per galaxy with:

1. galaxy-centred original image,
2. MTObjects mask,
3. original isophotes,
4. MTObjects processed isophotes,
5. original bar-major profile,
6. MTObjects processed bar-major profile.
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

import mtobjects_spike_gate_processing as mto  # noqa: E402
import optimise_toy_objects_MTObjects as mto_toy_opt  # noqa: E402
from machine_paths import PC_RESEARCH_FOLDERS, remove_foreground_folder  # noqa: E402


DEFAULT_OUTPUT_SUBDIR = "mtobjects optimised foreground removal"
DEFAULT_DPI = 180
DEFAULT_SOURCE = "spike-gate"
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
        candidates.extend((root / "mtobjects spike optimisation").glob("*/mtobjects_spike_optimisation_best.json"))
    if source in {"latest", "toy-object"}:
        candidates.extend((root / "mtobjects toy optimisation").glob("*/mtobjects_parameter_optimisation_best.json"))
    candidates = sorted([path for path in candidates if path.is_file()], key=lambda path: path.stat().st_mtime)
    return candidates[-1] if candidates else None


def load_best_params(path: Path) -> dict[str, float | int | str]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    params = payload.get("params", payload)
    if not isinstance(params, dict):
        raise ValueError(f"Best-parameter JSON does not contain a parameter dictionary: {path}")

    defaults = {
        "detect_on": "original",
        "spike_gate_detect_on": "residual",
        "alpha": mto.DEFAULT_ALPHA,
        "move_factor": mto.DEFAULT_MOVE_FACTOR,
        "min_distance": mto.DEFAULT_MIN_DISTANCE,
        "gaussian_fwhm": mto.DEFAULT_GAUSSIAN_FWHM,
        "soft_bias": mto.DEFAULT_SOFT_BIAS,
        "gain": mto.DEFAULT_GAIN,
        "bg_mean": mto.DEFAULT_BG_MEAN,
        "bg_variance": mto.DEFAULT_BG_VARIANCE,
        "minarea": mto.DEFAULT_MINAREA,
        "dilation_radius": mto.DEFAULT_DILATION_RADIUS,
        "max_area": mto.DEFAULT_MAX_AREA,
        "max_elongation": mto.DEFAULT_MAX_ELONGATION,
        "exclude_center_pixels": mto.DEFAULT_EXCLUDE_CENTER_PIXELS,
        "spike_gate_move_factor": mto.SPIKE_GATE_MOVE_FACTOR,
        "spike_excess_fraction": mto.DEFAULT_SPIKE_EXCESS_FRACTION,
        "spike_neighbour_inner_arcsec": mto.DEFAULT_SPIKE_NEIGHBOUR_INNER_ARCSEC,
        "spike_neighbour_outer_arcsec": mto.DEFAULT_SPIKE_NEIGHBOUR_OUTER_ARCSEC,
        "spike_side_offset_samples": mto.DEFAULT_SPIKE_SIDE_OFFSET_SAMPLES,
        "spike_side_drop_fraction": mto.DEFAULT_SPIKE_SIDE_DROP_FRACTION,
        "spike_window_samples": mto.DEFAULT_SPIKE_WINDOW_SAMPLES,
    }
    loaded = dict(defaults)
    for key, value in params.items():
        loaded[key] = math.nan if value == "NaN" else value
    return loaded


def selected_rows(manifest: Path, pc_name: str, names: list[str] | None, max_images: int | None) -> list[dict[str, str]]:
    rows = mto.display.rows_with_images_for_pc(mto.display.read_manifest(manifest), pc_name)
    if names:
        wanted = {name.casefold() for name in names}
        rows = [row for row in rows if row["name"].casefold() in wanted]

    selected = []
    for row in rows:
        if mto.display.required_geometry(row) is None:
            continue
        selected.append(row)
        if max_images is not None and len(selected) >= max_images:
            break
    if not selected:
        raise ValueError("No usable galaxies found for the requested PC/name selection.")
    return selected


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
        color="#b59b00",
        linestyle="--",
        linewidth=1.2,
        alpha=0.9,
    )


def draw_isophote(ax, image, x_axis, y_axis, extent, title, half_width, bar_sma, central_exclusion_arcsec) -> None:
    log_image, levels = mto.display.robust_log_image(image)
    ax.imshow(log_image, origin="lower", extent=extent, cmap="Greys", vmin=levels[0], vmax=levels[-1])
    ax.contour(x_axis, y_axis, log_image, levels=levels[1:-1], colors="0.25", linewidths=0.45)
    draw_bar_guides(ax, half_width, bar_sma)
    draw_central_exclusion(ax, central_exclusion_arcsec)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("deprojected arcsec")
    ax.set_ylabel("deprojected arcsec")
    ax.set_title(title)


def profile_y_limits(values: list[np.ndarray]) -> tuple[float, float]:
    positive = np.concatenate([item[np.isfinite(item) & (item > 0)] for item in values])
    if positive.size == 0:
        return 1.0, 10.0
    ymin = max(float(np.nanpercentile(positive, 2)) * 0.8, np.finfo(float).tiny)
    ymax = float(np.nanmax(positive)) * 1.25
    if not math.isfinite(ymin) or not math.isfinite(ymax) or ymax <= ymin:
        return 1.0, 10.0
    return ymin, ymax


def draw_profile(
    ax,
    image,
    x_axis,
    y_axis,
    half_width,
    bar_sma,
    central_exclusion_arcsec,
    title,
    *,
    mask_profile: np.ndarray | None = None,
    toy_mask_profile: np.ndarray | None = None,
    y_limits: tuple[float, float] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    radii, intensity = mto.display.bar_major_axis_profile(image, x_axis, y_axis, half_width)
    displayed_intensity = np.array(intensity, copy=True)
    bridged_intensity = None
    bridged_samples = np.zeros(intensity.size, dtype=bool)

    if mask_profile is not None:
        bridged_intensity, bridged_samples = mto.fill_profile_with_log_linear_bridges(intensity, mask_profile)
        displayed_intensity[bridged_samples] = np.nan

    ax.semilogy(radii, displayed_intensity, color="#1f77b4", linewidth=1.4)
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
            for start, stop in mto.contiguous_true_runs(styled_samples):
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
        ax.axvline(central_exclusion_arcsec, color="#b59b00", linestyle="--", linewidth=1.0, alpha=0.9)
        ax.axvline(-central_exclusion_arcsec, color="#b59b00", linestyle="--", linewidth=1.0, alpha=0.9)
    ax.axvline(0.0, color="0.6", linewidth=0.7)
    ax.set_xlim(float(x_axis[0]), float(x_axis[-1]))
    if y_limits is not None:
        ax.set_ylim(*y_limits)
    ax.set_xlabel("deprojected bar-major radius [arcsec]")
    ax.set_ylabel("intensity")
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.2)
    if mask_profile is not None and np.any(bridged_samples):
        ax.legend(loc="best", fontsize=8)
    return intensity, bridged_intensity if bridged_intensity is not None else intensity


def draw_mask_outlines(ax, mask_view: np.ndarray, truth_view: np.ndarray, x_axis: np.ndarray, y_axis: np.ndarray) -> None:
    labels, count = label_components(mask_view, structure=np.ones((3, 3), dtype=np.uint8))
    for component_id in range(1, count + 1):
        component = labels == component_id
        colour = "#00a000" if np.any(component & truth_view) else "red"
        ax.contour(x_axis, y_axis, component.astype(float), levels=[0.5], colors=[colour], linewidths=1.2)


def draw_report(
    name: str,
    original: np.ndarray,
    injected: np.ndarray,
    truth_mask: np.ndarray,
    products: dict,
    params: dict[str, float | int | str],
    geometry: dict[str, float],
) -> Figure:
    cleaned = np.asarray(products["cleaned"], dtype=float)
    mask = np.asarray(products["mask"], dtype=bool)

    radius_arcsec = mto.display.profile_radius_pixels(original, geometry) * geometry["pixel_scale"]
    original_view, x_axis, y_axis = mto.display.deproject_bar_aligned_cutout(original, geometry, radius_arcsec)
    injected_view, _, _ = mto.display.deproject_bar_aligned_cutout(injected, geometry, radius_arcsec)
    cleaned_view, _, _ = mto.display.deproject_bar_aligned_cutout(cleaned, geometry, radius_arcsec)
    mask_view, _, _ = mto.display.deproject_bar_aligned_cutout(mask.astype(float), geometry, radius_arcsec, order=0)
    mask_view = np.isfinite(mask_view) & (mask_view > 0.5)
    truth_view, _, _ = mto.display.deproject_bar_aligned_cutout(truth_mask.astype(float), geometry, radius_arcsec, order=0)
    truth_view = np.isfinite(truth_view) & (truth_view > 0.5)

    extent = [x_axis[0], x_axis[-1], y_axis[0], y_axis[-1]]
    half_width = 0.5 * mto.DEFAULT_PROFILE_WIDTH_PIXELS * geometry["pixel_scale"]
    mask_profile = mto.profile_mask_at_bar_major(mask_view, y_axis, half_width)
    toy_mask_profile = mto.profile_mask_at_bar_major(mask_view & truth_view, y_axis, half_width)
    bar_sma = mto.display.bar_sma_deprojected_arcsec(geometry)
    central_exclusion_arcsec = float(params["exclude_center_pixels"]) * geometry["pixel_scale"]
    radii, original_profile = mto.display.bar_major_axis_profile(original_view, x_axis, y_axis, half_width)
    processed_profile, _replaced = mto.fill_profile_with_log_linear_bridges(original_profile, mask_profile)
    y_limits = profile_y_limits([original_profile, processed_profile])

    figure = Figure(figsize=(11.5, 17.0), dpi=100, constrained_layout=False)
    FigureCanvasAgg(figure)
    figure.subplots_adjust(left=0.075, right=0.965, top=0.925, bottom=0.055, wspace=0.28, hspace=0.38)
    grid = figure.add_gridspec(4, 2, height_ratios=[1.0, 1.0, 1.0, 0.76])
    ax_original = figure.add_subplot(grid[0, 0])
    ax_injected = figure.add_subplot(grid[0, 1])
    ax_mask = figure.add_subplot(grid[1, 0])
    ax_recovered = figure.add_subplot(grid[1, 1])
    ax_original_isophote = figure.add_subplot(grid[2, 0])
    ax_processed_isophote = figure.add_subplot(grid[2, 1])
    ax_original_profile = figure.add_subplot(grid[3, 0])
    ax_processed_profile = figure.add_subplot(grid[3, 1])

    vmin, vmax = mto.display.robust_limits(injected_view)
    ax_original.imshow(original_view, origin="lower", cmap="gist_gray_r", vmin=vmin, vmax=vmax, extent=extent)
    draw_bar_guides(ax_original, half_width, bar_sma)
    draw_central_exclusion(ax_original, central_exclusion_arcsec)
    ax_original.set_aspect("equal", adjustable="box")
    ax_original.set_xlabel("deprojected arcsec")
    ax_original.set_ylabel("deprojected arcsec")
    masked_fraction = np.count_nonzero(mask) / mask.size
    ax_original.set_title("Galaxy Centered Original")

    ax_injected.imshow(injected_view, origin="lower", cmap="gist_gray_r", vmin=vmin, vmax=vmax, extent=extent)
    draw_bar_guides(ax_injected, half_width, bar_sma)
    draw_central_exclusion(ax_injected, central_exclusion_arcsec)
    ax_injected.set_aspect("equal", adjustable="box")
    ax_injected.set_xlabel("deprojected arcsec")
    ax_injected.set_ylabel("deprojected arcsec")
    ax_injected.set_title("Original + Toys")

    ax_mask.imshow(mask_view.astype(float), origin="lower", cmap="Reds", vmin=0.0, vmax=1.0, extent=extent, alpha=0.86)
    draw_bar_guides(ax_mask, half_width, bar_sma)
    draw_central_exclusion(ax_mask, central_exclusion_arcsec)
    ax_mask.set_aspect("equal", adjustable="box")
    ax_mask.set_xlabel("deprojected arcsec")
    ax_mask.set_ylabel("deprojected arcsec")
    ax_mask.set_title(f"Mask | masked {masked_fraction:.2%}")

    ax_recovered.imshow(cleaned_view, origin="lower", cmap="gist_gray_r", vmin=vmin, vmax=vmax, extent=extent)
    draw_mask_outlines(ax_recovered, mask_view, truth_view, x_axis, y_axis)
    draw_bar_guides(ax_recovered, half_width, bar_sma)
    draw_central_exclusion(ax_recovered, central_exclusion_arcsec)
    ax_recovered.set_aspect("equal", adjustable="box")
    ax_recovered.set_xlabel("deprojected arcsec")
    ax_recovered.set_ylabel("deprojected arcsec")
    ax_recovered.set_title("Recovered Image | green=correct, red=incorrect")

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
        ax_processed_isophote,
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
        y_limits=y_limits,
    )
    draw_profile(
        ax_processed_profile,
        cleaned_view,
        x_axis,
        y_axis,
        half_width,
        bar_sma,
        central_exclusion_arcsec,
        "Processed Bar Major Profile",
        mask_profile=mask_profile,
        toy_mask_profile=toy_mask_profile,
        y_limits=y_limits,
    )

    image_axes = [ax_original, ax_injected, ax_mask, ax_recovered, ax_original_isophote, ax_processed_isophote]
    for ax in image_axes:
        ax.set_xlim(float(x_axis[0]), float(x_axis[-1]))
        ax.set_ylim(float(y_axis[0]), float(y_axis[-1]))
        ax.set_box_aspect(1.0)
    ax_original_profile.set_xlim(float(extent[0]), float(extent[1]))
    ax_processed_profile.set_xlim(float(extent[0]), float(extent[1]))

    kept = sum(1 for row in products["rows"] if row.get("kept"))
    source_label = str(params.get("_source_label", "optimised MTObjects parameters"))
    if len(source_label) > 58:
        source_label = source_label[:55] + "..."
    figure.suptitle(
        f"{name} | MTObjects Toy Objects | segments={kept}/{len(products['rows'])}",
        fontsize=10.5,
        fontweight="bold",
        y=0.982,
    )
    FigureCanvasAgg(figure).draw()
    left = ax_original.get_position()
    right = ax_injected.get_position()
    left_profile = ax_original_profile.get_position()
    right_profile = ax_processed_profile.get_position()
    ax_original_profile.set_position([left.x0, left_profile.y0, left.width, left_profile.height])
    ax_processed_profile.set_position([right.x0, right_profile.y0, right.width, right_profile.height])
    return figure


def write_cleaned_fits(path: Path, data: np.ndarray, header: fits.Header, mask: np.ndarray, params: dict) -> None:
    output_header = header.copy()
    output_header["FGMASK"] = ("MTOBJECT", "Foreground removal method")
    output_header["MTMOVE"] = (float(params["move_factor"]), "MTObjects move_factor")
    output_header["MTMIND"] = (float(params["min_distance"]), "MTObjects min_distance")
    output_header["MTFWHM"] = (float(params["gaussian_fwhm"]), "MTObjects gaussian_fwhm")
    output_header["MTMINA"] = (int(params["minarea"]), "MTObjects minimum area")
    output_header["MTDIL"] = (int(params["dilation_radius"]), "MTObjects dilation radius")
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


def load_clean_galaxy_names(path: Path, expected_count: int = EXPECTED_CLEAN_GALAXIES) -> set[str]:
    if not path.is_file():
        raise FileNotFoundError(f"Clean-galaxy list not found: {path}")
    names = {line.strip().casefold() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()}
    if len(names) != expected_count:
        raise ValueError(f"Expected {expected_count} unique clean galaxies in {path}; found {len(names)}.")
    return names


def process_one(
    row: dict[str, str],
    args: argparse.Namespace,
    params: dict[str, float | int | str],
    mtobjects_root: Path | None,
    report_dir: Path,
    fits_dir: Path,
    clean_galaxy_names: set[str],
) -> dict[str, object]:
    name = row["name"]
    geometry = mto.display.required_geometry(row)
    if geometry is None:
        raise ValueError(f"{name} has incomplete geometry.")
    data, header = mto.load_fits(mto.display.image_path_for_pc(row, args.pc))
    if args.toy_diagnostics:
        galaxy_seed = int(args.toy_seed) + zlib.crc32(name.casefold().encode("utf-8"))
        injected, truth_mask, _truth_labels, _toys = mto_toy_opt.inject_toys(
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
    products = mto.mtobjects_products(injected, params, geometry, mtobjects_root)

    clean_suffix = "_clean" if name.casefold() in clean_galaxy_names else ""
    report_path = report_dir / f"{mto.display.safe_filename(name)}_mtobjects_optimised_report{clean_suffix}.png"
    figure = draw_report(name, data, injected, truth_mask, products, params, geometry)
    figure.savefig(report_path, dpi=int(args.dpi))

    cleaned_fits_path = ""
    if args.save_cleaned_fits:
        cleaned_fits = fits_dir / f"{mto.display.safe_filename(name)}_mtobjects_optimised_cleaned.fits"
        write_cleaned_fits(cleaned_fits, np.asarray(products["cleaned"], dtype=float), header, products["mask"], params)
        cleaned_fits_path = str(cleaned_fits)

    mask = np.asarray(products["mask"], dtype=bool)
    kept = sum(1 for item in products["rows"] if item.get("kept"))
    return {
        "name": name,
        "status": "ok",
        "segments_kept": kept,
        "segments_raw": len(products["rows"]),
        "masked_pixels": int(np.count_nonzero(mask)),
        "masked_fraction": float(np.count_nonzero(mask) / mask.size),
        "report_png": str(report_path),
        "cleaned_fits": cleaned_fits_path,
        "error": "",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=mto.DEFAULT_MANIFEST)
    parser.add_argument("--pc", choices=sorted(PC_RESEARCH_FOLDERS), default=mto.DEFAULT_PC)
    parser.add_argument("--mtobjects-root", type=Path, default=Path(mto.DEFAULT_MTOBJECTS_ROOT) if mto.DEFAULT_MTOBJECTS_ROOT else None)
    parser.add_argument(
        "--best-json",
        type=Path,
        help="Path to mtobjects_spike_optimisation_best.json. Defaults to the latest Spike Gate best JSON.",
    )
    parser.add_argument(
        "--params-json",
        type=Path,
        help="Alias for --best-json, useful when the best-parameter file has been copied or renamed.",
    )
    parser.add_argument(
        "--source",
        choices=["latest", "spike-gate", "toy-object"],
        default=DEFAULT_SOURCE,
        help="Which optimiser family to search when --best-json is not supplied.",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--resume-output-dir",
        type=Path,
        default=None,
        help="Continue a stopped batch folder, skipping galaxies already marked ok in the summary CSV.",
    )
    parser.add_argument(
        "--run-label",
        default=None,
        help="Short label shown in report titles and used in the default output folder name.",
    )
    parser.add_argument("--names", nargs="*", help="Optional explicit galaxy names. Defaults to all usable galaxies.")
    parser.add_argument("--max-images", type=int, help="Optional limit for smoke tests.")
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    clean_galaxies_file = args.clean_galaxies_file or (remove_foreground_folder(args.pc) / "CleanGalaxies.txt")
    clean_galaxy_names = load_clean_galaxy_names(clean_galaxies_file)
    log(f"Filename calibration list: {clean_galaxies_file} ({len(clean_galaxy_names)} galaxies; suffix=_clean)")
    best_json = args.best_json or args.params_json or latest_best_json(args.pc, args.source)
    if best_json is None:
        raise FileNotFoundError(
            "No best-parameter JSON found. Pass --best-json, or use --source spike-gate/toy-object after that optimiser has a best JSON."
        )
    params = load_best_params(best_json)
    params["_source_label"] = args.run_label or best_json.parent.name
    mtobjects_root = mto.find_mtobjects_root(args.mtobjects_root)
    if mtobjects_root is None:
        raise ModuleNotFoundError(mto.mtobjects_setup_message(args.mtobjects_root))

    if args.resume_output_dir is not None and args.output_dir is not None:
        raise ValueError("Use either --resume-output-dir or --output-dir, not both.")

    timestamp_dir = datetime.now().strftime("%Y%m%d_%H%M%S")
    label_slug = mto.display.safe_filename(args.run_label or args.source)
    output_dir = args.resume_output_dir or args.output_dir or (
        remove_foreground_folder(args.pc) / DEFAULT_OUTPUT_SUBDIR / label_slug / timestamp_dir
    )
    report_dir = output_dir
    fits_dir = output_dir / "cleaned_fits"
    report_dir.mkdir(parents=True, exist_ok=True)
    if args.save_cleaned_fits:
        fits_dir.mkdir(parents=True, exist_ok=True)

    config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    config["best_json"] = str(best_json)
    config["mtobjects_root"] = str(mtobjects_root)
    config["params"] = {key: ("NaN" if isinstance(value, float) and math.isnan(value) else value) for key, value in params.items()}
    (output_dir / "mtobjects_optimised_apply_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    rows = selected_rows(args.manifest, args.pc, args.names, args.max_images)
    log(f"Applying optimised MTObjects parameters from {best_json}")
    log(f"Prepared {len(rows)} galaxies. Output: {output_dir}")

    summary_path = output_dir / "mtobjects_optimised_apply_summary.csv"
    completed_names = completed_names_from_summary(summary_path) if args.resume_output_dir is not None else set()
    if completed_names:
        rows = [row for row in rows if row["name"] not in completed_names]
        log(f"Resume mode: skipping {len(completed_names)} galaxies already marked ok; {len(rows)} remain.")

    fieldnames = [
        "name",
        "status",
        "segments_kept",
        "segments_raw",
        "masked_pixels",
        "masked_fraction",
        "report_png",
        "cleaned_fits",
        "elapsed_seconds",
        "error",
    ]
    made = 0
    failed = 0
    run_started = time.perf_counter()
    for index, row in enumerate(rows, start=1):
        name = row["name"]
        started = time.perf_counter()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                summary = process_one(row, args, params, mtobjects_root, report_dir, fits_dir, clean_galaxy_names)
            made += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            summary = {
                "name": name,
                "status": "error",
                "segments_kept": "",
                "segments_raw": "",
                "masked_pixels": "",
                "masked_fraction": "",
                "report_png": "",
                "cleaned_fits": "",
                "error": "".join(traceback.format_exception_only(type(exc), exc)).strip(),
            }
        elapsed = time.perf_counter() - started
        summary["elapsed_seconds"] = elapsed
        append_csv(summary_path, [summary], fieldnames)
        remaining = len(rows) - index
        average = (time.perf_counter() - run_started) / index
        seconds_remaining = remaining * average
        log(
            f"{index}/{len(rows)} {name}: {summary['status']} "
            f"masked={summary.get('masked_fraction', '')} elapsed={format_duration(elapsed)} "
            f"remaining={remaining} rough_eta={format_duration(seconds_remaining)} "
            f"expected_completion={expected_completion_text(seconds_remaining)}"
        )

    log(f"Finished. Reports made={made}, failed={failed}. Summary: {summary_path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
