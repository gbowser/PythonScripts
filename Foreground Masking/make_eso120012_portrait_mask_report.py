#!/usr/bin/env python3
"""Create a portrait ESO120-012 foreground-mask profile comparison PDF."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from matplotlib.patches import Circle
from scipy.ndimage import median_filter


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
S4G_PLOTTER_DIR = PROJECT_ROOT / "Erwin_s4g_image_downloader"
BARPROFILES_DIR = PROJECT_ROOT / "Erwin_barprofiles_paper_GB_working_copy"
for path in (SCRIPT_DIR, S4G_PLOTTER_DIR, BARPROFILES_DIR):
    if str(path) not in sys.path:
        sys.path.append(str(path))

import angle_utils as angles  # noqa: E402
import foreground_mask_photutils as fgmask  # noqa: E402
import plot_s4g_isophote_axes as s4g_plot  # noqa: E402


DEFAULT_MANIFEST = S4G_PLOTTER_DIR / "geometry_output" / "s4g_image_geometry_manifest.csv"
DEFAULT_OUTPUT = (
    SCRIPT_DIR
    / "ESO120-012_portrait_mask_report"
    / "ESO120-012_isophote_axes_portrait_mask_report.pdf"
)


def read_row(manifest: Path, galaxy_name: str) -> dict[str, str]:
    with manifest.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["name"] == galaxy_name:
                return row
    raise ValueError(f"{galaxy_name} was not found in {manifest}.")


def profile_radius_pixels(data: np.ndarray, geometry: dict[str, float]) -> int:
    xc = geometry["xc"]
    yc = geometry["yc"]
    bar_sma = geometry["bar_sma"]
    pixel_scale = geometry["pixel_scale"]
    max_radius_pix = int(
        max(
            20,
            min(
                xc - 1,
                yc - 1,
                data.shape[1] - xc,
                data.shape[0] - yc,
            ),
        )
    )
    target_radius_arcsec = max(3.0 * bar_sma, 45.0)
    radius = min(max_radius_pix, int(math.ceil(target_radius_arcsec / pixel_scale)))
    return max(radius, int(math.ceil(1.4 * bar_sma / pixel_scale)))


def build_mask_products(
    data: np.ndarray,
    geometry: dict[str, float],
    *,
    smooth_sigma_pixels: float,
    detection_nsigma: float,
    npixels: int,
    dilation_radius_pixels: int,
    max_area: int,
    max_elongation: float,
    exclude_center_radius_pixels: float,
):
    smooth = fgmask.make_smooth_galaxy_model(data, smooth_sigma_pixels)
    residual = fgmask.make_residual_image(data, smooth)
    segm = fgmask.detect_compact_sources(
        residual,
        nsigma=detection_nsigma,
        npixels=npixels,
        deblend=True,
    )
    filtered_segm, candidate_rows = fgmask.filter_segments(
        segm,
        data,
        residual,
        max_area=max_area,
        max_elongation=max_elongation,
        galaxy_center=(geometry["xc"] - 1, geometry["yc"] - 1),
        exclude_center_radius_pixels=exclude_center_radius_pixels,
    )
    raw_mask = fgmask.segmentation_to_mask(filtered_segm, data.shape)
    mask = fgmask.dilate_mask(raw_mask, dilation_radius_pixels)
    kept_rows = [row for row in candidate_rows if row["kept"]]
    return mask, kept_rows, smooth


def plot_profile(
    ax: plt.Axes,
    rr_major_deproj: np.ndarray,
    intensity_major: np.ndarray,
    rr_minor_deproj: np.ndarray,
    intensity_minor: np.ndarray,
    bar_sma_deproj_arcsec: float,
    title: str,
) -> None:
    ax.semilogy(rr_major_deproj, intensity_major, color="#1f77b4", label="bar major")
    ax.semilogy(
        rr_minor_deproj,
        intensity_minor,
        color="#d62728",
        linestyle="--",
        label="bar minor",
    )
    ax.axvline(0, color="0.35", linestyle=":", linewidth=0.9)
    ax.axvline(bar_sma_deproj_arcsec, color="#1f77b4", linewidth=1.1)
    ax.axvline(-bar_sma_deproj_arcsec, color="#1f77b4", linewidth=1.1)
    ax.set_xlabel("deprojected radius [arcsec]")
    ax.set_ylabel("intensity")
    ax.set_title(title)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.tick_params(labelsize=8)


def _plot_dotted_replacement_segments(
    ax: plt.Axes,
    radius: np.ndarray,
    values: np.ndarray,
    replaced: np.ndarray,
    *,
    color: str,
    linestyle: str,
) -> None:
    """Draw dotted bridge segments, including adjacent measured endpoints."""
    replaced = np.asarray(replaced, dtype=bool)
    if not np.any(replaced):
        return

    indices = np.flatnonzero(replaced)
    start = int(indices[0])
    previous = int(indices[0])
    runs: list[tuple[int, int]] = []
    for index in indices[1:]:
        index = int(index)
        if index > previous + 1:
            runs.append((start, previous))
            start = index
        previous = index
    runs.append((start, previous))

    dotted_style = (0, (1.0, 1.5)) if linestyle == "-" else (0, (1.0, 1.4))
    for start, stop in runs:
        draw_start = max(0, start - 1)
        draw_stop = min(values.size - 1, stop + 1)
        segment = slice(draw_start, draw_stop + 1)
        ax.semilogy(
            radius[segment],
            values[segment],
            color=color,
            linestyle=dotted_style,
            linewidth=1.8,
        )


def plot_profile_with_bridges(
    ax: plt.Axes,
    rr_major_deproj: np.ndarray,
    intensity_major: np.ndarray,
    major_replaced: np.ndarray,
    rr_minor_deproj: np.ndarray,
    intensity_minor: np.ndarray,
    minor_replaced: np.ndarray,
    bar_sma_deproj_arcsec: float,
    title: str,
) -> None:
    measured_major = np.array(intensity_major, copy=True)
    measured_major[major_replaced] = np.nan
    measured_minor = np.array(intensity_minor, copy=True)
    measured_minor[minor_replaced] = np.nan

    ax.semilogy(rr_major_deproj, measured_major, color="#1f77b4", label="bar major")
    ax.semilogy(
        rr_minor_deproj,
        measured_minor,
        color="#d62728",
        linestyle="--",
        label="bar minor",
    )
    _plot_dotted_replacement_segments(
        ax,
        rr_major_deproj,
        intensity_major,
        major_replaced,
        color="#1f77b4",
        linestyle="-",
    )
    _plot_dotted_replacement_segments(
        ax,
        rr_minor_deproj,
        intensity_minor,
        minor_replaced,
        color="#d62728",
        linestyle="--",
    )
    ax.axvline(0, color="0.35", linestyle=":", linewidth=0.9)
    ax.axvline(bar_sma_deproj_arcsec, color="#1f77b4", linewidth=1.1)
    ax.axvline(-bar_sma_deproj_arcsec, color="#1f77b4", linewidth=1.1)
    ax.set_xlabel("deprojected radius [arcsec]")
    ax.set_ylabel("intensity")
    ax.set_title(title)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.tick_params(labelsize=8)


def profile_mask_at_pa(
    mask: np.ndarray,
    xc: float,
    yc: float,
    pa_deg: float,
    radius_pix: int,
    *,
    width: int,
) -> np.ndarray:
    """Return profile samples touched by masked image pixels."""
    _, mask_fraction = s4g_plot.profile_at_pa(
        mask.astype(float), xc, yc, pa_deg, radius_pix, width=width
    )
    return np.isfinite(mask_fraction) & (mask_fraction > 0.0)


def _merge_boolean_runs(masked: np.ndarray, max_gap: int) -> np.ndarray:
    """Merge masked stretches separated by short unmasked islands."""
    merged = np.asarray(masked, dtype=bool).copy()
    if max_gap <= 0 or not np.any(merged):
        return merged

    indices = np.flatnonzero(merged)
    start = int(indices[0])
    previous = int(indices[0])
    runs: list[tuple[int, int]] = []
    for index in indices[1:]:
        index = int(index)
        if index - previous > max_gap + 1:
            runs.append((start, previous))
            start = index
        previous = index
    runs.append((start, previous))

    merged[:] = False
    for start, stop in runs:
        merged[start : stop + 1] = True
    return merged


def fill_masked_profile_with_log_linear_bridges(
    values: np.ndarray,
    masked_samples: np.ndarray,
    *,
    merge_gap_samples: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Fill only masked samples, using merged stretches to choose bridge endpoints."""
    profile = np.asarray(values, dtype=float)
    filled = np.array(profile, copy=True)
    replacement_mask = ~np.isfinite(profile) | (profile <= 0)
    bridge_seed = np.asarray(masked_samples, dtype=bool) | replacement_mask
    bridge_context = _merge_boolean_runs(bridge_seed, merge_gap_samples)
    x = np.arange(profile.size)

    index = 0
    while index < profile.size:
        if not bridge_context[index]:
            index += 1
            continue

        start = index
        while index + 1 < profile.size and bridge_context[index + 1]:
            index += 1
        stop = index

        left = start - 1
        while left >= 0 and (~np.isfinite(profile[left]) or profile[left] <= 0):
            left -= 1
        right = stop + 1
        while right < profile.size and (~np.isfinite(profile[right]) or profile[right] <= 0):
            right += 1

        fill_indices = x[start : stop + 1][replacement_mask[start : stop + 1]]
        if fill_indices.size == 0:
            index += 1
            continue
        if left >= 0 and right < profile.size:
            log_left = math.log(float(profile[left]))
            log_right = math.log(float(profile[right]))
            weight = (fill_indices - left) / (right - left)
            filled[fill_indices] = np.exp(log_left + weight * (log_right - log_left))
        elif left >= 0:
            filled[fill_indices] = profile[left]
        elif right < profile.size:
            filled[fill_indices] = profile[right]
        index += 1

    return filled, replacement_mask


def set_shared_profile_limits(axes: list[plt.Axes], intensities: list[np.ndarray]) -> None:
    finite = np.concatenate(
        [values[np.isfinite(values) & (values > 0)] for values in intensities]
    )
    if finite.size == 0:
        return
    ymin = np.nanpercentile(finite, 2)
    ymax = np.nanmax(finite)
    if ymin > 0 and ymax > ymin:
        for ax in axes:
            ax.set_ylim(ymin * 0.8, ymax * 1.35)


def make_report(args: argparse.Namespace) -> Path:
    row = read_row(args.manifest, "ESO120-012")
    geometry = s4g_plot.required_geometry(row)
    if geometry is None:
        raise ValueError("ESO120-012 has incomplete geometry in the manifest.")

    image_path = Path(row["image_path"])
    data = np.squeeze(fits.getdata(image_path).astype(float))
    if data.ndim != 2:
        raise ValueError(f"Expected a 2D FITS image, got shape {data.shape}.")

    mask, kept_rows, smooth_model = build_mask_products(
        data,
        geometry,
        smooth_sigma_pixels=args.smooth_sigma_pixels,
        detection_nsigma=args.detection_nsigma,
        npixels=args.npixels,
        dilation_radius_pixels=args.dilation_radius_pixels,
        max_area=args.max_area,
        max_elongation=args.max_elongation,
        exclude_center_radius_pixels=args.exclude_center_radius_pixels,
    )
    masked_data = np.where(mask, np.nan, data)

    xc = geometry["xc"]
    yc = geometry["yc"]
    disk_pa = geometry["disk_pa"]
    inclination = geometry["inclination"]
    bar_pa = geometry["bar_pa"]
    bar_sma = geometry["bar_sma"]
    pixel_scale = geometry["pixel_scale"]
    minor_pa = angles.minoraxis(bar_pa, disk_pa, inclination)
    radius_pix = profile_radius_pixels(data, geometry)
    plot_radius_arcsec = min(pixel_scale * radius_pix, max(2.8 * bar_sma, 45.0))

    smoothed = median_filter(data, size=3)
    subimage, x_arcsec, y_arcsec = s4g_plot.extract_centered_subimage(
        smoothed, xc, yc, pixel_scale, plot_radius_arcsec
    )
    log_subimage, contour_levels = s4g_plot.robust_log_image(subimage)
    extent = [x_arcsec[0], x_arcsec[-1], y_arcsec[0], y_arcsec[-1]]

    rr_major_pix, intensity_major = s4g_plot.profile_at_pa(
        data, xc, yc, bar_pa, radius_pix, width=args.profile_width
    )
    rr_minor_pix, intensity_minor = s4g_plot.profile_at_pa(
        data, xc, yc, minor_pa, radius_pix, width=args.profile_width
    )
    _, intensity_major_masked = s4g_plot.profile_at_pa(
        masked_data, xc, yc, bar_pa, radius_pix, width=args.profile_width
    )
    _, intensity_minor_masked = s4g_plot.profile_at_pa(
        masked_data, xc, yc, minor_pa, radius_pix, width=args.profile_width
    )
    mask_major = profile_mask_at_pa(
        mask, xc, yc, bar_pa, radius_pix, width=args.profile_width
    )
    mask_minor = profile_mask_at_pa(
        mask, xc, yc, minor_pa, radius_pix, width=args.profile_width
    )
    intensity_major_filled, major_replaced = fill_masked_profile_with_log_linear_bridges(
        intensity_major_masked,
        mask_major,
        merge_gap_samples=args.bridge_merge_gap_samples,
    )
    intensity_minor_filled, minor_replaced = fill_masked_profile_with_log_linear_bridges(
        intensity_minor_masked,
        mask_minor,
        merge_gap_samples=args.bridge_merge_gap_samples,
    )

    rr_major_deproj = s4g_plot.deprojected_profile_radius(
        bar_pa, disk_pa, inclination, rr_major_pix * pixel_scale
    )
    rr_minor_deproj = s4g_plot.deprojected_profile_radius(
        minor_pa, disk_pa, inclination, rr_minor_pix * pixel_scale
    )
    bar_deproj_factor = angles.deprojectr(bar_pa - disk_pa, inclination, 1.0)
    bar_sma_deproj_arcsec = bar_deproj_factor * bar_sma
    try:
        photutils_version = importlib.metadata.version("photutils")
    except importlib.metadata.PackageNotFoundError:
        photutils_version = "unknown"

    fig = plt.figure(figsize=(8.27, 11.69))
    gridspec = fig.add_gridspec(
        5,
        1,
        height_ratios=[1.05, 0.83, 0.83, 0.83, 0.7],
        left=0.11,
        right=0.95,
        bottom=0.055,
        top=0.93,
        hspace=0.55,
    )
    fig.suptitle(
        f"ESO120-012 foreground-mask profile comparison   bar PA={bar_pa:.1f} deg",
        fontsize=13,
    )

    ax_image = fig.add_subplot(gridspec[0])
    ax_image.imshow(
        log_subimage,
        origin="lower",
        extent=extent,
        cmap="Greys",
        vmin=contour_levels[0],
        vmax=contour_levels[-1],
        interpolation="nearest",
    )
    ax_image.contour(
        x_arcsec,
        y_arcsec,
        log_subimage,
        levels=contour_levels,
        colors="0.25",
        linewidths=0.42,
    )
    line_radius = min(plot_radius_arcsec * 0.82, max(1.5 * bar_sma, bar_sma + 15.0))
    s4g_plot.draw_pa_line(ax_image, bar_pa, line_radius, color="#1f77b4", linewidth=1.5)
    s4g_plot.draw_pa_line(
        ax_image,
        bar_pa,
        bar_sma,
        color="#1f77b4",
        linewidth=1.7,
        alpha=0.75,
        marker=True,
    )
    s4g_plot.draw_pa_line(
        ax_image,
        minor_pa,
        line_radius,
        color="#d62728",
        linestyle="--",
        linewidth=1.3,
    )
    for kept in kept_rows:
        x_mask_arcsec = pixel_scale * (float(kept["x_centroid"]) + 1 - xc)
        y_mask_arcsec = pixel_scale * (float(kept["y_centroid"]) + 1 - yc)
        radius_arcsec = pixel_scale * math.sqrt(float(kept["area"]) / math.pi)
        radius_arcsec += pixel_scale * args.dilation_radius_pixels
        radius_arcsec = max(radius_arcsec, 2.2 * pixel_scale)
        if extent[0] <= x_mask_arcsec <= extent[1] and extent[2] <= y_mask_arcsec <= extent[3]:
            ax_image.add_patch(
                Circle(
                    (x_mask_arcsec, y_mask_arcsec),
                    radius_arcsec,
                    edgecolor="red",
                    facecolor="none",
                    linewidth=1.0,
                    alpha=0.9,
                )
            )
    ax_image.axhline(0, color="0.55", linewidth=0.5)
    ax_image.axvline(0, color="0.55", linewidth=0.5)
    ax_image.set_aspect("equal", adjustable="box")
    ax_image.set_xlabel("arcsec")
    ax_image.set_ylabel("arcsec")
    ax_image.set_title("S4G 3.6 micron isophotes with masked objects circled")
    ax_image.tick_params(labelsize=8)

    ax_original = fig.add_subplot(gridspec[1])
    ax_masked = fig.add_subplot(gridspec[2], sharex=ax_original)
    ax_interpolated = fig.add_subplot(gridspec[3], sharex=ax_original)
    ax_parameters = fig.add_subplot(gridspec[4])
    plot_profile(
        ax_original,
        rr_major_deproj,
        intensity_major,
        rr_minor_deproj,
        intensity_minor,
        bar_sma_deproj_arcsec,
        "Original major/minor-axis cuts",
    )
    plot_profile(
        ax_masked,
        rr_major_deproj,
        intensity_major_masked,
        rr_minor_deproj,
        intensity_minor_masked,
        bar_sma_deproj_arcsec,
        "Masked major/minor-axis cuts",
    )
    plot_profile_with_bridges(
        ax_interpolated,
        rr_major_deproj,
        intensity_major_filled,
        major_replaced,
        rr_minor_deproj,
        intensity_minor_filled,
        minor_replaced,
        bar_sma_deproj_arcsec,
        "Masked cuts with straight log-linear bridges",
    )
    set_shared_profile_limits(
        [ax_original, ax_masked, ax_interpolated],
        [
            intensity_major,
            intensity_minor,
            intensity_major_masked,
            intensity_minor_masked,
            intensity_major_filled,
            intensity_minor_filled,
        ],
    )
    ax_parameters.axis("off")
    parameter_rows = [
        ("Masking model", f"photutils segmentation on residual image; photutils {photutils_version}"),
        ("Residual image", "science image - Gaussian-smoothed galaxy model"),
        ("Detection threshold", f"{args.detection_nsigma:g} sigma above residual median"),
        ("Smooth sigma", f"{args.smooth_sigma_pixels:g} px"),
        ("Connected-pixel minimum", f"{args.npixels} px"),
        ("Dilation radius", f"{args.dilation_radius_pixels} px"),
        ("Max segment area", f"{args.max_area} px"),
        ("Max elongation", f"{args.max_elongation:g}"),
        ("Central exclusion radius", f"{args.exclude_center_radius_pixels:g} px"),
        ("Profile width", f"{args.profile_width} px"),
        ("Applied mask", f"{len(kept_rows)} source segments; {int(np.count_nonzero(mask))} pixels ignored"),
        ("Filled-profile panel", "solid=measured data; fine dotted=samples filled by straight log-intensity bridge"),
        ("Bridge merge gap", f"{args.bridge_merge_gap_samples} profile samples"),
    ]
    table = ax_parameters.table(
        cellText=parameter_rows,
        colLabels=["Parameter", "Value"],
        cellLoc="left",
        colLoc="left",
        colWidths=[0.28, 0.72],
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    table.scale(1.0, 0.72)
    for (row_index, _), cell in table.get_celld().items():
        cell.set_linewidth(0.25)
        if row_index == 0:
            cell.set_text_props(weight="bold")
            cell.set_facecolor("0.92")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output)
    plt.close(fig)
    return args.output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the ESO120-012 portrait foreground-mask comparison PDF."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--profile-width", type=int, default=3)
    parser.add_argument("--smooth-sigma-pixels", type=float, default=15.0)
    parser.add_argument("--detection-nsigma", type=float, default=3.5)
    parser.add_argument("--npixels", type=int, default=8)
    parser.add_argument("--dilation-radius-pixels", type=int, default=3)
    parser.add_argument("--max-area", type=int, default=500)
    parser.add_argument("--max-elongation", type=float, default=6.0)
    parser.add_argument("--exclude-center-radius-pixels", type=float, default=12.0)
    parser.add_argument("--bridge-merge-gap-samples", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    output = make_report(parse_args())
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
