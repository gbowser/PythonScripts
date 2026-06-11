"""Codex-created S4G isophote/profile diagnostic plotting script."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
import warnings
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from matplotlib.backends.backend_pdf import PdfPages
from scipy.ndimage import median_filter
from skimage.measure import profile_line


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BARPROFILES_DIR = PROJECT_ROOT / "barprofiles_paper_GB_working_copy"
if str(BARPROFILES_DIR) not in sys.path:
    sys.path.append(str(BARPROFILES_DIR))

import angle_utils as angles  # noqa: E402


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MANIFEST = SCRIPT_DIR / "geometry_output" / "s4g_image_geometry_manifest.csv"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "isophote_output"
DEFAULT_COMBINED_PDF = DEFAULT_OUTPUT_DIR / "s4g_isophote_axes_all.pdf"


def parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    return number


def safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def pa_endpoint(pa_deg: float, radius: float) -> tuple[float, float]:
    """Return endpoint for a PA measured counter-clockwise from image +y."""
    return (
        -radius * math.sin(math.radians(pa_deg)),
        radius * math.cos(math.radians(pa_deg)),
    )


def draw_pa_line(
    ax: plt.Axes,
    pa_deg: float,
    radius: float,
    *,
    color: str,
    linestyle: str = "-",
    linewidth: float = 1.4,
    alpha: float = 0.9,
    marker: bool = False,
) -> None:
    dx, dy = pa_endpoint(pa_deg, radius)
    ax.plot(
        [dx, -dx],
        [dy, -dy],
        color=color,
        linestyle=linestyle,
        linewidth=linewidth,
        alpha=alpha,
    )
    if marker:
        ax.plot([dx, -dx], [dy, -dy], "o", color=color, ms=4.0, alpha=alpha)


def extract_centered_subimage(
    data: np.ndarray,
    xc: float,
    yc: float,
    pixel_scale: float,
    radius_arcsec: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    y_size, x_size = data.shape
    radius_pix = max(8, int(math.ceil(radius_arcsec / pixel_scale)))
    x0 = max(0, int(math.floor(xc - 1 - radius_pix)))
    x1 = min(x_size, int(math.ceil(xc - 1 + radius_pix + 1)))
    y0 = max(0, int(math.floor(yc - 1 - radius_pix)))
    y1 = min(y_size, int(math.ceil(yc - 1 + radius_pix + 1)))
    subimage = data[y0:y1, x0:x1]
    x_arcsec = pixel_scale * (np.arange(x0, x1) + 1 - xc)
    y_arcsec = pixel_scale * (np.arange(y0, y1) + 1 - yc)
    return subimage, x_arcsec, y_arcsec


def profile_at_pa(
    data: np.ndarray,
    xc: float,
    yc: float,
    pa_deg: float,
    radius_pix: int,
    *,
    width: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract a profile along PA. Coordinates use FITS/IRAF 1-based x,y."""
    dx, dy = pa_endpoint(pa_deg, radius_pix)
    start = (yc - dy - 1, xc - dx - 1)
    end = (yc + dy - 1, xc + dx - 1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        values = profile_line(
            data,
            start,
            end,
            linewidth=width,
            reduce_func=np.nanmean,
            mode="constant",
            cval=np.nan,
        )
    radii_pix = np.linspace(-radius_pix, radius_pix, len(values))
    return radii_pix, values


def robust_log_image(data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    finite = data[np.isfinite(data)]
    positive = finite[finite > 0]
    if len(positive) == 0:
        positive = np.array([1.0])
    floor = np.nanpercentile(positive, 1)
    if not math.isfinite(floor) or floor <= 0:
        floor = float(np.nanmin(positive))
    clipped = np.where(data > floor, data, floor)
    log_data = np.log10(clipped)
    valid = log_data[np.isfinite(log_data)]
    if len(valid) < 2:
        value = float(valid[0]) if len(valid) else 0.0
        lo, hi = value - 0.5, value + 0.5
    else:
        lo, hi = np.nanpercentile(valid, [8, 99.5])
    if not math.isfinite(lo) or not math.isfinite(hi) or lo >= hi:
        lo, hi = float(np.nanmin(valid)), float(np.nanmax(valid))
    if lo >= hi:
        hi = lo + 1.0
    levels = np.linspace(lo, hi, 16)
    return log_data, levels


def deprojected_profile_radius(
    pa_deg: float,
    disk_pa_deg: float,
    inclination_deg: float,
    radii_arcsec: np.ndarray,
) -> np.ndarray:
    factor = angles.deprojectr(pa_deg - disk_pa_deg, inclination_deg, 1.0)
    return factor * radii_arcsec


def required_geometry(row: dict[str, str]) -> dict[str, float] | None:
    keys = {
        "xc": "center_x_pix",
        "yc": "center_y_pix",
        "crpix1": "crpix1",
        "crpix2": "crpix2",
        "disk_pa": "disk_pa_deg",
        "inclination": "inclination_deg",
        "bar_pa": "bar_pa_deg",
        "bar_sma": "bar_sma_arcsec",
        "pixel_scale": "pixel_scale_arcsec_y",
    }
    values = {name: parse_float(row.get(column)) for name, column in keys.items()}
    required = ["xc", "yc", "disk_pa", "inclination", "bar_pa", "bar_sma", "pixel_scale"]
    if any(values[value] is None for value in required):
        return None
    values["pixel_scale"] = abs(values["pixel_scale"]) or 0.75
    values["bar_pa"] = angles.RectifyPA(values["bar_pa"], 180.0)
    values["disk_pa"] = angles.RectifyPA(values["disk_pa"], 180.0)
    return values  # type: ignore[return-value]


def make_plot(
    row: dict[str, str],
    *,
    output_pdf: Path | None = None,
    pdf_pages: PdfPages | None = None,
    profile_width: int = 3,
) -> bool:
    geometry = required_geometry(row)
    image_path = Path(row["image_path"])
    if geometry is None or not image_path.exists():
        return False

    data = fits.getdata(image_path).astype(float)
    data = np.squeeze(data)
    if data.ndim != 2:
        return False

    xc = geometry["xc"]
    yc = geometry["yc"]
    center_note = "catalogue centre"
    if not (1 <= xc <= data.shape[1] and 1 <= yc <= data.shape[0]):
        crpix1 = geometry.get("crpix1")
        crpix2 = geometry.get("crpix2")
        if crpix1 is None or crpix2 is None:
            return False
        xc = crpix1
        yc = crpix2
        center_note = "FITS CRPIX centre fallback"
    disk_pa = geometry["disk_pa"]
    inclination = geometry["inclination"]
    bar_pa = geometry["bar_pa"]
    bar_sma = geometry["bar_sma"]
    pixel_scale = geometry["pixel_scale"]
    minor_pa = angles.minoraxis(bar_pa, disk_pa, inclination)

    max_radius_pix = int(
        max(
            20,
            min(
                xc - 1,
                yc - 1,
                data.shape[1] - xc,
                data.shape[0] - yc,
            )
        )
    )
    target_radius_arcsec = max(3.0 * bar_sma, 45.0)
    profile_radius_pix = min(max_radius_pix, int(math.ceil(target_radius_arcsec / pixel_scale)))
    profile_radius_pix = max(profile_radius_pix, int(math.ceil(1.4 * bar_sma / pixel_scale)))
    plot_radius_arcsec = min(pixel_scale * profile_radius_pix, max(2.8 * bar_sma, 45.0))

    smoothed = median_filter(data, size=3)
    subimage, x_arcsec, y_arcsec = extract_centered_subimage(
        smoothed, xc, yc, pixel_scale, plot_radius_arcsec
    )
    log_subimage, contour_levels = robust_log_image(subimage)

    fig, (ax_image, ax_profile) = plt.subplots(
        1,
        2,
        figsize=(11, 4.6),
        gridspec_kw={"width_ratios": [1, 1.18]},
    )
    fig.suptitle(
        f"{row['name']}   bar PA={bar_pa:.1f} deg   minor PA={minor_pa:.1f} deg   {center_note}",
        fontsize=12,
    )

    extent = [x_arcsec[0], x_arcsec[-1], y_arcsec[0], y_arcsec[-1]]
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
        linewidths=0.45,
    )
    line_radius = min(plot_radius_arcsec * 0.82, max(1.5 * bar_sma, bar_sma + 15.0))
    draw_pa_line(ax_image, bar_pa, line_radius, color="#1f77b4", linewidth=1.6)
    draw_pa_line(ax_image, bar_pa, bar_sma, color="#1f77b4", linewidth=1.8, alpha=0.75, marker=True)
    draw_pa_line(ax_image, minor_pa, line_radius, color="#d62728", linestyle="--", linewidth=1.4)
    ax_image.axhline(0, color="0.55", linewidth=0.5)
    ax_image.axvline(0, color="0.55", linewidth=0.5)
    ax_image.set_aspect("equal", adjustable="box")
    ax_image.set_xlabel("arcsec")
    ax_image.set_ylabel("arcsec")
    ax_image.set_title("S4G 3.6 micron isophotes")

    rr_major_pix, intensity_major = profile_at_pa(
        data, xc, yc, bar_pa, profile_radius_pix, width=profile_width
    )
    rr_minor_pix, intensity_minor = profile_at_pa(
        data, xc, yc, minor_pa, profile_radius_pix, width=profile_width
    )
    rr_major_arcsec = rr_major_pix * pixel_scale
    rr_minor_arcsec = rr_minor_pix * pixel_scale
    rr_major_deproj = deprojected_profile_radius(
        bar_pa, disk_pa, inclination, rr_major_arcsec
    )
    rr_minor_deproj = deprojected_profile_radius(
        minor_pa, disk_pa, inclination, rr_minor_arcsec
    )

    ax_profile.semilogy(rr_major_deproj, intensity_major, color="#1f77b4", label="bar major")
    ax_profile.semilogy(rr_minor_deproj, intensity_minor, color="#d62728", linestyle="--", label="bar minor")
    bar_deproj_factor = angles.deprojectr(bar_pa - disk_pa, inclination, 1.0)
    bar_sma_deproj_arcsec = bar_deproj_factor * bar_sma
    ax_profile.axvline(0, color="0.35", linestyle=":", linewidth=0.9)
    ax_profile.axvline(bar_sma_deproj_arcsec, color="#1f77b4", linewidth=1.1)
    ax_profile.axvline(-bar_sma_deproj_arcsec, color="#1f77b4", linewidth=1.1)
    ax_profile.set_xlabel("deprojected radius [arcsec]")
    ax_profile.set_ylabel("intensity")
    ax_profile.set_title("major/minor-axis cuts")
    ax_profile.legend(frameon=False, fontsize=9)
    finite_intensity = np.concatenate(
        [
            intensity_major[np.isfinite(intensity_major) & (intensity_major > 0)],
            intensity_minor[np.isfinite(intensity_minor) & (intensity_minor > 0)],
        ]
    )
    if len(finite_intensity) > 0:
        ymin, ymax = np.nanpercentile(finite_intensity, [2, 99.5])
        if ymin > 0 and ymax > ymin:
            ax_profile.set_ylim(ymin * 0.8, ymax * 1.25)

    fig.tight_layout(rect=[0, 0, 1, 0.94])
    if pdf_pages is not None:
        pdf_pages.savefig(fig)
    if output_pdf is not None:
        output_pdf.parent.mkdir(exist_ok=True)
        try:
            fig.savefig(output_pdf)
        except PermissionError:
            fallback_pdf = output_pdf.with_name(f"{output_pdf.stem}_replacement{output_pdf.suffix}")
            fig.savefig(fallback_pdf)
            print(f"Could not overwrite {output_pdf.name}; wrote {fallback_pdf.name}")
    plt.close(fig)
    return True


def selected_rows(rows: list[dict[str, str]], names: set[str], limit: int | None) -> list[dict[str, str]]:
    if names:
        rows = [row for row in rows if row["name"] in names]
    if limit is not None:
        rows = rows[:limit]
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create Figure-1-style S4G isophote plots with bar major/minor axes."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--combined-pdf", type=Path, default=DEFAULT_COMBINED_PDF)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--names", nargs="*", default=[])
    parser.add_argument("--profile-width", type=int, default=3)
    parser.add_argument(
        "--no-individual",
        action="store_true",
        help="Only write the combined multi-page PDF.",
    )
    parser.add_argument(
        "--no-combined",
        action="store_true",
        help="Only write individual per-galaxy PDFs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = selected_rows(read_manifest(args.manifest), set(args.names), args.limit)
    args.output_dir.mkdir(exist_ok=True)
    individual_dir = args.output_dir / "individual"
    made = 0
    skipped: list[str] = []

    pdf_pages: PdfPages | None = None
    try:
        if not args.no_combined:
            args.combined_pdf.parent.mkdir(exist_ok=True)
            pdf_pages = PdfPages(args.combined_pdf)
        for row in rows:
            output_pdf = None
            if not args.no_individual:
                output_pdf = individual_dir / f"{safe_filename(row['name'])}_isophote_axes.pdf"
            try:
                ok = make_plot(
                    row,
                    output_pdf=output_pdf,
                    pdf_pages=pdf_pages,
                    profile_width=args.profile_width,
                )
            except Exception as exc:  # Keep long batches moving, but report the galaxy.
                print(f"Failed {row['name']}: {exc}")
                ok = False
            if ok:
                made += 1
            else:
                skipped.append(row["name"])
    finally:
        if pdf_pages is not None:
            pdf_pages.close()

    print(f"Made {made} isophote plots")
    if not args.no_combined:
        print(f"Combined PDF: {args.combined_pdf.resolve()}")
    if not args.no_individual:
        print(f"Individual PDFs: {individual_dir.resolve()}")
    if skipped:
        print(f"Skipped {len(skipped)} galaxies: {', '.join(skipped)}")
    return 0 if made else 1


if __name__ == "__main__":
    raise SystemExit(main())
