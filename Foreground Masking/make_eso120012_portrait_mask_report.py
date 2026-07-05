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
    return mask, kept_rows


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


def set_shared_profile_limits(axes: list[plt.Axes], intensities: list[np.ndarray]) -> None:
    finite = np.concatenate(
        [values[np.isfinite(values) & (values > 0)] for values in intensities]
    )
    if finite.size == 0:
        return
    ymin, ymax = np.nanpercentile(finite, [2, 99.5])
    if ymin > 0 and ymax > ymin:
        for ax in axes:
            ax.set_ylim(ymin * 0.8, ymax * 1.25)


def make_report(args: argparse.Namespace) -> Path:
    row = read_row(args.manifest, "ESO120-012")
    geometry = s4g_plot.required_geometry(row)
    if geometry is None:
        raise ValueError("ESO120-012 has incomplete geometry in the manifest.")

    image_path = Path(row["image_path"])
    data = np.squeeze(fits.getdata(image_path).astype(float))
    if data.ndim != 2:
        raise ValueError(f"Expected a 2D FITS image, got shape {data.shape}.")

    mask, kept_rows = build_mask_products(
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
        3,
        1,
        height_ratios=[1.15, 1.0, 1.0],
        left=0.11,
        right=0.95,
        bottom=0.115,
        top=0.93,
        hspace=0.42,
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

    ax_original = fig.add_subplot(gridspec[1])
    ax_masked = fig.add_subplot(gridspec[2], sharex=ax_original)
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
    set_shared_profile_limits(
        [ax_original, ax_masked],
        [intensity_major, intensity_minor, intensity_major_masked, intensity_minor_masked],
    )
    parameter_text = (
        f"Masking model: photutils segmentation on residual image "
        f"(image - Gaussian-smoothed galaxy model; photutils {photutils_version}). "
        f"Parameters: smooth sigma={args.smooth_sigma_pixels:g} px; "
        f"detection threshold={args.detection_nsigma:g} sigma above residual median; "
        f"minimum connected pixels={args.npixels}; dilation radius={args.dilation_radius_pixels} px; "
        f"max segment area={args.max_area} px; max elongation={args.max_elongation:g}; "
        f"central exclusion radius={args.exclude_center_radius_pixels:g} px; "
        f"profile width={args.profile_width} px. "
        f"Applied mask: {len(kept_rows)} source segments, {int(np.count_nonzero(mask))} pixels ignored."
    )
    fig.text(
        0.11,
        0.035,
        parameter_text,
        ha="left",
        va="bottom",
        fontsize=8,
        wrap=True,
    )

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
    return parser.parse_args()


def main() -> int:
    output = make_report(parse_args())
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
