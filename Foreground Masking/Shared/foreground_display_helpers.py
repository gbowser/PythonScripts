"""Shared manifest, geometry, deprojection, and plotting helpers for foreground masking tools."""

from __future__ import annotations

import csv
import math
import os
from pathlib import Path
import re
import sys

import numpy as np
from scipy.ndimage import map_coordinates


SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
SUPPORT_DIRS = tuple(FOREGROUND_ROOT / name for name in ("Batch tools", "PhotUtils", "Interactive tools", "Shared", "Utilities"))
S4G_PLOTTER_DIR = PROJECT_ROOT / "Erwin_s4g_image_downloader"
BARPROFILES_DIR = PROJECT_ROOT / "Erwin_barprofiles_paper_GB_working_copy"
for path in (PROJECT_ROOT, SCRIPT_DIR, S4G_PLOTTER_DIR, BARPROFILES_DIR):
    if str(path) not in sys.path:
        sys.path.append(str(path))

import angle_utils as angles  # noqa: E402
from machine_paths import erwin_folder  # noqa: E402


DEFAULT_MANIFEST = S4G_PLOTTER_DIR / "geometry_output" / "s4g_image_geometry_manifest.csv"
DEFAULT_PROFILE_WIDTH_PIXELS = 3


def finite_float(value: str | float | int | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in value)


def image_path_for_pc(row: dict[str, str], pc_name: str) -> Path:
    machine_path = erwin_folder(pc_name) / "s4g_images_36um" / f"{row['name']}.phot.1.fits"
    if machine_path.exists():
        return machine_path
    manifest_path = Path(row.get("image_path", ""))
    if os.name != "nt":
        match = re.match(r"^([A-Za-z]):[\\/](.*)$", str(manifest_path))
        if match:
            drive, remainder = match.groups()
            wsl_path = Path(f"/mnt/{drive.lower()}") / Path(remainder.replace("\\", "/"))
            if wsl_path.exists():
                return wsl_path
    return manifest_path


def rows_with_images_for_pc(rows: list[dict[str, str]], pc_name: str) -> list[dict[str, str]]:
    return sorted(
        [row for row in rows if image_path_for_pc(row, pc_name).exists()],
        key=lambda row: row["name"].casefold(),
    )


def required_geometry(row: dict[str, str]) -> dict[str, float] | None:
    keys = {
        "xc": "center_x_pix",
        "yc": "center_y_pix",
        "disk_pa": "disk_pa_deg",
        "inclination": "inclination_deg",
        "bar_pa": "bar_pa_deg",
        "bar_sma": "bar_sma_arcsec",
        "pixel_scale": "pixel_scale_arcsec_y",
    }
    values = {name: finite_float(row.get(column)) for name, column in keys.items()}
    required = ["xc", "yc", "disk_pa", "inclination", "bar_pa", "bar_sma", "pixel_scale"]
    if any(values[name] is None for name in required):
        return None
    values["pixel_scale"] = abs(values["pixel_scale"]) or 0.75
    values["bar_pa"] = angles.RectifyPA(values["bar_pa"], 180.0)
    values["disk_pa"] = angles.RectifyPA(values["disk_pa"], 180.0)
    return values  # type: ignore[return-value]


def profile_radius_pixels(data: np.ndarray, geometry: dict[str, float]) -> int:
    xc = geometry["xc"]
    yc = geometry["yc"]
    bar_sma = geometry["bar_sma"]
    pixel_scale = geometry["pixel_scale"]
    max_radius_pix = int(max(20, min(xc - 1, yc - 1, data.shape[1] - xc, data.shape[0] - yc)))
    target_radius_arcsec = max(3.0 * bar_sma, 45.0)
    radius = min(max_radius_pix, int(math.ceil(target_radius_arcsec / pixel_scale)))
    return max(radius, int(math.ceil(1.4 * bar_sma / pixel_scale)))


def bar_sma_deprojected_arcsec(geometry: dict[str, float]) -> float:
    return float(
        angles.deprojectr(
            geometry["bar_pa"] - geometry["disk_pa"],
            geometry["inclination"],
            1.0,
        )
        * geometry["bar_sma"]
    )


def image_transform(disk_pa: float, inclination: float, bar_pa: float) -> np.ndarray:
    disk = np.radians(disk_pa)
    bar = np.radians(bar_pa)
    disk_major = np.array([-np.sin(disk), np.cos(disk)])
    disk_minor = np.array([np.cos(disk), np.sin(disk)])
    deproject = np.outer(disk_major, disk_major) + np.outer(disk_minor, disk_minor) / np.cos(
        np.radians(inclination)
    )
    observed_bar = np.array([-np.sin(bar), np.cos(bar)])
    face_on_bar = deproject @ observed_bar
    angle = math.atan2(face_on_bar[1], face_on_bar[0])
    rotate = np.array([[math.cos(angle), math.sin(angle)], [-math.sin(angle), math.cos(angle)]])
    return rotate @ deproject


def deproject_bar_aligned_cutout(
    data: np.ndarray,
    geometry: dict[str, float],
    radius_arcsec: float,
    *,
    order: int = 1,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pixel_scale = geometry["pixel_scale"]
    radius_pix = max(8, int(math.ceil(radius_arcsec / pixel_scale)))
    offsets_pix = np.arange(-radius_pix, radius_pix + 1, dtype=float)
    xx_pix, yy_pix = np.meshgrid(offsets_pix, offsets_pix)
    transform_xy = image_transform(geometry["disk_pa"], geometry["inclination"], geometry["bar_pa"])
    inverse_xy = np.linalg.inv(transform_xy)
    input_offsets = inverse_xy @ np.vstack([xx_pix.ravel(), yy_pix.ravel()])
    input_x = (geometry["xc"] - 1.0) + input_offsets[0].reshape(xx_pix.shape)
    input_y = (geometry["yc"] - 1.0) + input_offsets[1].reshape(yy_pix.shape)
    valid = np.isfinite(data)
    filled = np.where(valid, data, 0.0)
    sampled = map_coordinates(filled, [input_y, input_x], order=order, mode="constant", cval=0.0)
    support = map_coordinates(valid.astype(float), [input_y, input_x], order=0, mode="constant", cval=0.0)
    cutout = np.divide(
        sampled,
        support,
        out=np.full_like(sampled, np.nan, dtype=float),
        where=support > 0.5,
    )
    axis_arcsec = offsets_pix * pixel_scale
    return cutout, axis_arcsec, axis_arcsec


def robust_limits(data: np.ndarray, low: float = 1.0, high: float = 99.5) -> tuple[float, float]:
    finite = np.asarray(data)[np.isfinite(data)]
    if finite.size == 0:
        return 0.0, 1.0
    vmin, vmax = np.percentile(finite, [low, high])
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
        vmin, vmax = float(np.nanmin(finite)), float(np.nanmax(finite))
    if vmin == vmax:
        vmax = vmin + 1.0
    return float(vmin), float(vmax)


def robust_log_image(data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    finite = np.asarray(data, dtype=float)[np.isfinite(data)]
    positive = finite[finite > 0]
    if positive.size == 0:
        positive = np.array([1.0])
    floor = float(np.nanpercentile(positive, 1))
    if not math.isfinite(floor) or floor <= 0:
        floor = float(np.nanmin(positive))
    log_data = np.log10(np.where(data > floor, data, floor))
    valid = log_data[np.isfinite(log_data)]
    if valid.size < 2:
        lo, hi = -0.5, 0.5
    else:
        lo, hi = np.nanpercentile(valid, [8, 99.5])
    if not math.isfinite(lo) or not math.isfinite(hi) or lo >= hi:
        lo, hi = float(np.nanmin(valid)), float(np.nanmax(valid))
    if lo >= hi:
        hi = lo + 1.0
    return log_data, np.linspace(lo, hi, 16)


def bar_major_axis_profile(
    image: np.ndarray,
    x_axis: np.ndarray,
    y_axis: np.ndarray,
    half_width_arcsec: float,
) -> tuple[np.ndarray, np.ndarray]:
    aperture_rows = np.abs(y_axis) <= half_width_arcsec
    if not np.any(aperture_rows):
        aperture_rows[np.argmin(np.abs(y_axis))] = True
    samples = np.asarray(image, dtype=float)[aperture_rows, :]
    finite_counts = np.count_nonzero(np.isfinite(samples), axis=0)
    summed = np.nansum(samples, axis=0)
    profile = np.divide(
        summed,
        finite_counts,
        out=np.full(x_axis.shape, np.nan, dtype=float),
        where=finite_counts > 0,
    )
    return x_axis, profile
