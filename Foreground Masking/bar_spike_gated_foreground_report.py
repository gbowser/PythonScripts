#!/usr/bin/env python3
"""Create portrait bar-spike-gated foreground-candidate profile PDFs."""

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
from scipy.ndimage import map_coordinates, median_filter


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
DEFAULT_OUTPUT_DIR = Path(
    r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\calibrated spike_rule"
)
DEFAULT_OUTPUT = (
    SCRIPT_DIR
    / "ESO120-012_portrait_mask_report"
    / "ESO120-012_foreground_removed.pdf"
)


def read_row(manifest: Path, galaxy_name: str) -> dict[str, str]:
    with manifest.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["name"] == galaxy_name:
                return row
    raise ValueError(f"{galaxy_name} was not found in {manifest}.")


def read_rows(manifest: Path) -> list[dict[str, str]]:
    with manifest.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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


def build_mask_from_residual(
    data: np.ndarray,
    residual: np.ndarray,
    geometry: dict[str, float],
    *,
    detection_nsigma: float,
    npixels: int,
    dilation_radius_pixels: int,
    max_area: int,
    max_elongation: float,
    exclude_center_radius_pixels: float,
):
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


def _expand_boolean_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    expanded = np.asarray(mask, dtype=bool).copy()
    if radius <= 0 or not np.any(expanded):
        return expanded

    indices = np.flatnonzero(expanded)
    for index in indices:
        start = max(0, int(index) - radius)
        stop = min(expanded.size, int(index) + radius + 1)
        expanded[start:stop] = True
    return expanded


def detect_profile_spikes(
    radii_arcsec: np.ndarray,
    values: np.ndarray,
    *,
    excess_fraction: float,
    neighbour_inner_arcsec: float,
    neighbour_outer_arcsec: float,
    side_offset_samples: int,
    side_drop_fraction: float,
    center_exclusion_arcsec: float,
) -> np.ndarray:
    """Detect narrow positive spikes above neighbouring profile samples."""
    radii = np.asarray(radii_arcsec, dtype=float)
    profile = np.asarray(values, dtype=float)
    spikes = np.zeros(profile.size, dtype=bool)
    good = np.isfinite(profile) & (profile > 0)
    if np.count_nonzero(good) < 12:
        return spikes

    side_offset_samples = max(1, int(side_offset_samples))
    for index in range(side_offset_samples, profile.size - side_offset_samples):
        if not good[index]:
            continue
        if abs(radii[index]) < center_exclusion_arcsec:
            continue
        if profile[index] < profile[index - 1] or profile[index] < profile[index + 1]:
            continue

        distance = np.abs(radii - radii[index])
        neighbour = good & (distance >= neighbour_inner_arcsec) & (distance <= neighbour_outer_arcsec)
        left_neighbour = neighbour & (radii < radii[index])
        right_neighbour = neighbour & (radii > radii[index])
        if np.count_nonzero(left_neighbour) >= 2 and np.count_nonzero(right_neighbour) >= 2:
            neighbour_values = np.concatenate([profile[left_neighbour], profile[right_neighbour]])
        elif np.count_nonzero(neighbour) >= 4:
            neighbour_values = profile[neighbour]
        else:
            continue

        neighbour_level = np.nanmedian(neighbour_values)
        if not np.isfinite(neighbour_level) or neighbour_level <= 0:
            continue
        if profile[index] < (1.0 + excess_fraction) * neighbour_level:
            continue

        side_level = np.nanmedian(
            [profile[index - side_offset_samples], profile[index + side_offset_samples]]
        )
        if not np.isfinite(side_level) or side_level <= 0:
            continue
        if profile[index] < (1.0 + side_drop_fraction) * side_level:
            continue

        spikes[index] = True
    return spikes


def _filter_segment_rows_by_labels(rows: list[dict[str, float | int | bool]], labels: set[int]):
    return [row for row in rows if int(row["label"]) in labels]


def build_spike_gated_mask_from_residual(
    data: np.ndarray,
    residual: np.ndarray,
    geometry: dict[str, float],
    *,
    detection_nsigma: float,
    npixels: int,
    dilation_radius_pixels: int,
    max_area: int,
    max_elongation: float,
    exclude_center_radius_pixels: float,
    profile_width: int,
    spike_excess_fraction: float,
    spike_neighbour_inner_arcsec: float,
    spike_neighbour_outer_arcsec: float,
    spike_side_offset_samples: int,
    spike_side_drop_fraction: float,
    spike_center_exclusion_arcsec: float,
    spike_window_samples: int,
):
    """Mask only compact sources that intersect narrow spikes in the bar-major profile."""
    xc = geometry["xc"]
    yc = geometry["yc"]
    bar_pa = geometry["bar_pa"]
    radius_pix = profile_radius_pixels(data, geometry)
    rr_major_pix, intensity_major = s4g_plot.profile_at_pa(
        data, xc, yc, bar_pa, radius_pix, width=profile_width
    )
    rr_major_deproj = s4g_plot.deprojected_profile_radius(
        bar_pa, geometry["disk_pa"], geometry["inclination"], rr_major_pix * geometry["pixel_scale"]
    )
    spike_samples = detect_profile_spikes(
        rr_major_deproj,
        intensity_major,
        excess_fraction=spike_excess_fraction,
        neighbour_inner_arcsec=spike_neighbour_inner_arcsec,
        neighbour_outer_arcsec=spike_neighbour_outer_arcsec,
        side_offset_samples=spike_side_offset_samples,
        side_drop_fraction=spike_side_drop_fraction,
        center_exclusion_arcsec=spike_center_exclusion_arcsec,
    )
    spike_samples = _expand_boolean_mask(spike_samples, spike_window_samples)
    if not np.any(spike_samples):
        return np.zeros(data.shape, dtype=bool), [], spike_samples

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
        galaxy_center=(xc - 1, yc - 1),
        exclude_center_radius_pixels=exclude_center_radius_pixels,
    )
    if filtered_segm is None or len(filtered_segm.labels) == 0:
        return np.zeros(data.shape, dtype=bool), [], spike_samples

    selected_labels: set[int] = set()
    for label in filtered_segm.labels:
        label_mask = np.asarray(filtered_segm.data) == int(label)
        label_mask = fgmask.dilate_mask(label_mask, dilation_radius_pixels)
        label_profile = profile_mask_at_pa(
            label_mask, xc, yc, bar_pa, radius_pix, width=profile_width
        )
        if np.any(label_profile & spike_samples):
            selected_labels.add(int(label))

    if not selected_labels:
        return np.zeros(data.shape, dtype=bool), [], spike_samples

    selected_raw_mask = np.isin(np.asarray(filtered_segm.data), list(selected_labels))
    mask = fgmask.dilate_mask(selected_raw_mask, dilation_radius_pixels)
    return mask, _filter_segment_rows_by_labels(candidate_rows, selected_labels), spike_samples


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
    mask, kept_rows = build_mask_from_residual(
        data,
        residual,
        geometry,
        detection_nsigma=detection_nsigma,
        npixels=npixels,
        dilation_radius_pixels=dilation_radius_pixels,
        max_area=max_area,
        max_elongation=max_elongation,
        exclude_center_radius_pixels=exclude_center_radius_pixels,
    )
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


def image_transform(disk_pa: float, inclination: float, bar_pa: float) -> np.ndarray:
    """Map observed x/y offsets to face-on, bar-aligned x/y offsets."""
    disk = np.radians(disk_pa)
    bar = np.radians(bar_pa)
    disk_major = np.array([-np.sin(disk), np.cos(disk)])
    disk_minor = np.array([np.cos(disk), np.sin(disk)])
    deproject = np.outer(disk_major, disk_major) + np.outer(
        disk_minor, disk_minor
    ) / np.cos(np.radians(inclination))

    observed_bar = np.array([-np.sin(bar), np.cos(bar)])
    face_on_bar = deproject @ observed_bar
    angle = math.atan2(face_on_bar[1], face_on_bar[0])
    rotate = np.array(
        [[math.cos(angle), math.sin(angle)], [-math.sin(angle), math.cos(angle)]]
    )
    return rotate @ deproject


def deproject_bar_aligned_cutout(
    data: np.ndarray,
    geometry: dict[str, float],
    radius_arcsec: float,
    *,
    order: int = 1,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Sample a face-on, bar-aligned cutout on a regular arcsec grid."""
    pixel_scale = geometry["pixel_scale"]
    radius_pix = max(8, int(math.ceil(radius_arcsec / pixel_scale)))
    offsets_pix = np.arange(-radius_pix, radius_pix + 1, dtype=float)
    xx_pix, yy_pix = np.meshgrid(offsets_pix, offsets_pix)

    transform_xy = image_transform(
        geometry["disk_pa"], geometry["inclination"], geometry["bar_pa"]
    )
    inverse_xy = np.linalg.inv(transform_xy)
    input_offsets = inverse_xy @ np.vstack([xx_pix.ravel(), yy_pix.ravel()])
    input_x = (geometry["xc"] - 1.0) + input_offsets[0].reshape(xx_pix.shape)
    input_y = (geometry["yc"] - 1.0) + input_offsets[1].reshape(yy_pix.shape)

    valid = np.isfinite(data)
    filled = np.where(valid, data, 0.0)
    sampled = map_coordinates(
        filled,
        [input_y, input_x],
        order=order,
        mode="constant",
        cval=0.0,
        prefilter=order > 1,
    )
    support = map_coordinates(
        valid.astype(float),
        [input_y, input_x],
        order=1,
        mode="constant",
        cval=0.0,
        prefilter=False,
    )
    deprojected = np.divide(
        sampled,
        support,
        out=np.full_like(sampled, np.nan, dtype=float),
        where=support > 1.0e-3,
    )
    axis_arcsec = offsets_pix * pixel_scale
    return deprojected, axis_arcsec, axis_arcsec, transform_xy


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


def profile_spike_score(values: np.ndarray, ignore: np.ndarray | None = None) -> float:
    """Return a robust score for narrow positive spikes in log-intensity space."""
    profile = np.asarray(values, dtype=float)
    ignored = np.zeros(profile.size, dtype=bool) if ignore is None else np.asarray(ignore, dtype=bool)
    good = np.isfinite(profile) & (profile > 0)
    if np.count_nonzero(good) < 12:
        return 0.0

    x = np.arange(profile.size)
    log_profile = np.full(profile.size, np.nan, dtype=float)
    log_profile[good] = np.log(profile[good])
    log_profile[~good] = np.interp(x[~good], x[good], log_profile[good])
    smooth = median_filter(log_profile, size=9, mode="nearest")
    residual = log_profile - smooth
    residual[ignored] = np.nan
    residual = residual[np.isfinite(residual)]
    if residual.size == 0:
        return 0.0
    mad = np.median(np.abs(residual - np.median(residual)))
    scale = 1.4826 * mad if mad > 0 else np.nanstd(residual)
    if not np.isfinite(scale) or scale <= 0:
        return 0.0
    return float(np.nanmax(residual) / scale)


def choose_detection_nsigma(
    data: np.ndarray,
    residual: np.ndarray,
    geometry: dict[str, float],
    *,
    candidate_nsigmas: list[float],
    profile_width: int,
    npixels: int,
    dilation_radius_pixels: int,
    max_area: int,
    max_elongation: float,
    exclude_center_radius_pixels: float,
    bridge_merge_gap_samples: int,
) -> tuple[float, list[dict[str, float]]]:
    """Select a conservative threshold that reduces profile spikes without overmasking."""
    xc = geometry["xc"]
    yc = geometry["yc"]
    bar_pa = geometry["bar_pa"]
    radius_pix = profile_radius_pixels(data, geometry)
    _, original_major = s4g_plot.profile_at_pa(
        data, xc, yc, bar_pa, radius_pix, width=profile_width
    )
    original_score = profile_spike_score(original_major)
    image_size = float(data.size)

    evaluations: list[dict[str, float]] = []
    best_score = math.inf
    best_nsigma = candidate_nsigmas[0]

    for nsigma in candidate_nsigmas:
        mask, _ = build_mask_from_residual(
            data,
            residual,
            geometry,
            detection_nsigma=nsigma,
            npixels=npixels,
            dilation_radius_pixels=dilation_radius_pixels,
            max_area=max_area,
            max_elongation=max_elongation,
            exclude_center_radius_pixels=exclude_center_radius_pixels,
        )
        masked_data = np.where(mask, np.nan, data)
        _, masked_major = s4g_plot.profile_at_pa(
            masked_data, xc, yc, bar_pa, radius_pix, width=profile_width
        )
        mask_major = profile_mask_at_pa(mask, xc, yc, bar_pa, radius_pix, width=profile_width)
        filled_major, replaced_major = fill_masked_profile_with_log_linear_bridges(
            masked_major,
            mask_major,
            merge_gap_samples=bridge_merge_gap_samples,
        )
        score = profile_spike_score(filled_major, ignore=replaced_major)
        replaced_fraction = float(np.count_nonzero(replaced_major) / replaced_major.size)
        mask_fraction = float(np.count_nonzero(mask) / image_size)
        improvement = max(0.0, original_score - score)
        penalty = score + 12.0 * replaced_fraction + 35.0 * mask_fraction

        evaluations.append(
            {
                "nsigma": float(nsigma),
                "spike_score": float(score),
                "replaced_fraction": replaced_fraction,
                "mask_fraction": mask_fraction,
                "improvement": float(improvement),
                "penalty": float(penalty),
            }
        )
        excessive_mask = mask_fraction > 0.10 or replaced_fraction > 0.45
        if not excessive_mask and score < best_score:
            best_score = score
            best_nsigma = nsigma

    # Prefer a more conservative threshold only when its spike score is essentially as good.
    for evaluation in evaluations:
        excessive_mask = evaluation["mask_fraction"] > 0.10 or evaluation["replaced_fraction"] > 0.45
        if not excessive_mask and evaluation["spike_score"] <= best_score * 1.03 + 0.1:
            best_nsigma = evaluation["nsigma"]
            break

    return float(best_nsigma), evaluations


def choose_spike_gated_detection_nsigma(
    data: np.ndarray,
    residual: np.ndarray,
    geometry: dict[str, float],
    *,
    candidate_nsigmas: list[float],
    profile_width: int,
    npixels: int,
    dilation_radius_pixels: int,
    max_area: int,
    max_elongation: float,
    exclude_center_radius_pixels: float,
    spike_excess_fraction: float,
    spike_neighbour_inner_arcsec: float,
    spike_neighbour_outer_arcsec: float,
    spike_side_offset_samples: int,
    spike_side_drop_fraction: float,
    spike_center_exclusion_arcsec: float,
    spike_window_samples: int,
) -> tuple[float, list[dict[str, float]]]:
    """Choose the most conservative threshold that intersects every detected spike."""
    evaluations: list[dict[str, float]] = []
    best_nsigma = candidate_nsigmas[-1]
    for nsigma in candidate_nsigmas:
        mask, kept_rows, spike_samples = build_spike_gated_mask_from_residual(
            data,
            residual,
            geometry,
            detection_nsigma=nsigma,
            npixels=npixels,
            dilation_radius_pixels=dilation_radius_pixels,
            max_area=max_area,
            max_elongation=max_elongation,
            exclude_center_radius_pixels=exclude_center_radius_pixels,
            profile_width=profile_width,
            spike_excess_fraction=spike_excess_fraction,
            spike_neighbour_inner_arcsec=spike_neighbour_inner_arcsec,
            spike_neighbour_outer_arcsec=spike_neighbour_outer_arcsec,
            spike_side_offset_samples=spike_side_offset_samples,
            spike_side_drop_fraction=spike_side_drop_fraction,
            spike_center_exclusion_arcsec=spike_center_exclusion_arcsec,
            spike_window_samples=spike_window_samples,
        )
        xc = geometry["xc"]
        yc = geometry["yc"]
        bar_pa = geometry["bar_pa"]
        radius_pix = profile_radius_pixels(data, geometry)
        mask_profile = profile_mask_at_pa(mask, xc, yc, bar_pa, radius_pix, width=profile_width)
        spike_count = int(np.count_nonzero(spike_samples))
        covered_count = int(np.count_nonzero(spike_samples & mask_profile))
        coverage = 1.0 if spike_count == 0 else covered_count / spike_count
        mask_fraction = float(np.count_nonzero(mask) / float(data.size))
        evaluations.append(
            {
                "nsigma": float(nsigma),
                "spike_count": float(spike_count),
                "coverage": float(coverage),
                "mask_fraction": mask_fraction,
                "segments": float(len(kept_rows)),
            }
        )
        if spike_count == 0:
            best_nsigma = nsigma
            break
        if coverage >= 0.999 and mask_fraction <= 0.025:
            best_nsigma = nsigma
            break
        if coverage >= 0.999:
            best_nsigma = nsigma
            break
    return float(best_nsigma), evaluations


def make_report(args: argparse.Namespace, row: dict[str, str], output: Path) -> Path:
    galaxy_name = row["name"]
    geometry = s4g_plot.required_geometry(row)
    if geometry is None:
        raise ValueError(f"{galaxy_name} has incomplete geometry in the manifest.")

    image_path = Path(row["image_path"])
    data = np.squeeze(fits.getdata(image_path).astype(float))
    if data.ndim != 2:
        raise ValueError(f"Expected a 2D FITS image, got shape {data.shape}.")

    smooth_model = fgmask.make_smooth_galaxy_model(data, args.smooth_sigma_pixels)
    residual = fgmask.make_residual_image(data, smooth_model)
    tuning_rows: list[dict[str, float]] = []
    detection_nsigma = args.detection_nsigma
    if args.auto_tune:
        if args.masking_mode == "spike-gated":
            detection_nsigma, tuning_rows = choose_spike_gated_detection_nsigma(
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
        else:
            detection_nsigma, tuning_rows = choose_detection_nsigma(
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
                bridge_merge_gap_samples=args.bridge_merge_gap_samples,
            )

    if args.masking_mode == "spike-gated":
        mask, kept_rows, spike_samples = build_spike_gated_mask_from_residual(
            data,
            residual,
            geometry,
            detection_nsigma=detection_nsigma,
            npixels=args.npixels,
            dilation_radius_pixels=args.dilation_radius_pixels,
            max_area=args.max_area,
            max_elongation=args.max_elongation,
            exclude_center_radius_pixels=args.exclude_center_radius_pixels,
            profile_width=args.profile_width,
            spike_excess_fraction=args.spike_excess_fraction,
            spike_neighbour_inner_arcsec=args.spike_neighbour_inner_arcsec,
            spike_neighbour_outer_arcsec=args.spike_neighbour_outer_arcsec,
            spike_side_offset_samples=args.spike_side_offset_samples,
            spike_side_drop_fraction=args.spike_side_drop_fraction,
            spike_center_exclusion_arcsec=args.spike_center_exclusion_arcsec,
            spike_window_samples=args.spike_window_samples,
        )
    else:
        mask, kept_rows = build_mask_from_residual(
            data,
            residual,
            geometry,
            detection_nsigma=detection_nsigma,
            npixels=args.npixels,
            dilation_radius_pixels=args.dilation_radius_pixels,
            max_area=args.max_area,
            max_elongation=args.max_elongation,
            exclude_center_radius_pixels=args.exclude_center_radius_pixels,
        )
        spike_samples = np.zeros(1, dtype=bool)
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
    plot_radius_arcsec = min(pixel_scale * radius_pix, max(2.8 * bar_sma, 55.0))
    smoothed = median_filter(data, size=3)
    subimage, x_arcsec, y_arcsec = s4g_plot.extract_centered_subimage(
        smoothed, xc, yc, pixel_scale, plot_radius_arcsec
    )
    log_subimage, contour_levels = s4g_plot.robust_log_image(subimage)
    extent = [x_arcsec[0], x_arcsec[-1], y_arcsec[0], y_arcsec[-1]]
    deproj_image, x_deproj, y_deproj, transform_xy = deproject_bar_aligned_cutout(
        smoothed, geometry, plot_radius_arcsec, order=1
    )
    log_deproj_image, deproj_contour_levels = s4g_plot.robust_log_image(deproj_image)
    deproj_extent = [x_deproj[0], x_deproj[-1], y_deproj[0], y_deproj[-1]]

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
    title_mode = (
        "bar-spike-gated foreground-candidate"
        if args.masking_mode == "spike-gated"
        else "global Photutils foreground-candidate"
    )
    fig.suptitle(
        f"{galaxy_name} {title_mode} profile comparison   bar PA={bar_pa:.1f} deg",
        fontsize=13,
    )

    top_grid = gridspec[0].subgridspec(1, 2, wspace=0.22)
    ax_image = fig.add_subplot(top_grid[0])
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
    dx_major, dy_major = s4g_plot.pa_endpoint(bar_pa, line_radius)
    ax_image.annotate(
        "",
        xy=(0.72 * dx_major, 0.72 * dy_major),
        xytext=(0.18 * dx_major, 0.18 * dy_major),
        arrowprops={
            "arrowstyle": "-|>",
            "color": "white",
            "linewidth": 3.2,
            "mutation_scale": 13,
            "shrinkA": 0,
            "shrinkB": 0,
        },
        zorder=6,
    )
    ax_image.annotate(
        "",
        xy=(0.72 * dx_major, 0.72 * dy_major),
        xytext=(0.18 * dx_major, 0.18 * dy_major),
        arrowprops={
            "arrowstyle": "-|>",
            "color": "#1f77b4",
            "linewidth": 1.7,
            "mutation_scale": 13,
            "shrinkA": 0,
            "shrinkB": 0,
        },
        zorder=6,
    )
    label_kwargs = {
        "color": "#1f77b4",
        "fontsize": 8,
        "fontweight": "bold",
        "ha": "center",
        "va": "center",
        "bbox": {
            "boxstyle": "round,pad=0.15",
            "facecolor": "white",
            "edgecolor": "none",
            "alpha": 0.75,
        },
        "zorder": 7,
    }
    ax_image.text(1.06 * dx_major, 1.06 * dy_major, "+r", **label_kwargs)
    ax_image.text(-1.06 * dx_major, -1.06 * dy_major, "-r", **label_kwargs)
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
    ax_image.set_title("Observed sky plane", fontsize=10)
    ax_image.tick_params(labelsize=8)

    ax_deproj = fig.add_subplot(top_grid[1])
    ax_deproj.imshow(
        log_deproj_image,
        origin="lower",
        extent=deproj_extent,
        cmap="Greys",
        vmin=deproj_contour_levels[0],
        vmax=deproj_contour_levels[-1],
        interpolation="nearest",
    )
    ax_deproj.contour(
        x_deproj,
        y_deproj,
        log_deproj_image,
        levels=deproj_contour_levels,
        colors="0.25",
        linewidths=0.42,
    )
    line_radius_deproj = min(
        plot_radius_arcsec * 0.82,
        max(1.5 * bar_sma_deproj_arcsec, bar_sma_deproj_arcsec + 15.0),
    )
    ax_deproj.axhline(0, color="#1f77b4", linewidth=1.5)
    ax_deproj.plot(
        [-bar_sma_deproj_arcsec, bar_sma_deproj_arcsec],
        [0, 0],
        "o",
        color="#1f77b4",
        ms=4.0,
        alpha=0.75,
    )
    ax_deproj.axvline(0, color="#d62728", linestyle="--", linewidth=1.3)
    ax_deproj.annotate(
        "",
        xy=(0.72 * line_radius_deproj, 0),
        xytext=(0.18 * line_radius_deproj, 0),
        arrowprops={
            "arrowstyle": "-|>",
            "color": "white",
            "linewidth": 3.2,
            "mutation_scale": 13,
            "shrinkA": 0,
            "shrinkB": 0,
        },
        zorder=6,
    )
    ax_deproj.annotate(
        "",
        xy=(0.72 * line_radius_deproj, 0),
        xytext=(0.18 * line_radius_deproj, 0),
        arrowprops={
            "arrowstyle": "-|>",
            "color": "#1f77b4",
            "linewidth": 1.7,
            "mutation_scale": 13,
            "shrinkA": 0,
            "shrinkB": 0,
        },
        zorder=6,
    )
    ax_deproj.text(line_radius_deproj, 0, "+r", **label_kwargs)
    ax_deproj.text(-line_radius_deproj, 0, "-r", **label_kwargs)
    for kept in kept_rows:
        x_mask_arcsec = pixel_scale * (float(kept["x_centroid"]) + 1 - xc)
        y_mask_arcsec = pixel_scale * (float(kept["y_centroid"]) + 1 - yc)
        x_mask_deproj, y_mask_deproj = transform_xy @ np.array([x_mask_arcsec, y_mask_arcsec])
        radius_arcsec = pixel_scale * math.sqrt(float(kept["area"]) / math.pi)
        radius_arcsec += pixel_scale * args.dilation_radius_pixels
        radius_arcsec = max(radius_arcsec, 2.2 * pixel_scale)
        if (
            deproj_extent[0] <= x_mask_deproj <= deproj_extent[1]
            and deproj_extent[2] <= y_mask_deproj <= deproj_extent[3]
        ):
            ax_deproj.add_patch(
                Circle(
                    (x_mask_deproj, y_mask_deproj),
                    radius_arcsec,
                    edgecolor="red",
                    facecolor="none",
                    linewidth=1.0,
                    alpha=0.9,
                )
            )
    ax_deproj.set_xlim(deproj_extent[0], deproj_extent[1])
    ax_deproj.set_ylim(deproj_extent[2], deproj_extent[3])
    ax_deproj.set_aspect("equal", adjustable="box")
    ax_deproj.set_xlabel("deprojected arcsec")
    ax_deproj.set_ylabel("deprojected arcsec")
    ax_deproj.set_title("Deprojected, bar-aligned", fontsize=10)
    ax_deproj.tick_params(labelsize=8)

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
        ("Masking model", f"{args.masking_mode}; photutils segmentation on residual image; photutils {photutils_version}"),
        ("Residual image", "science image - Gaussian-smoothed galaxy model"),
        ("Detection threshold", f"{detection_nsigma:g} sigma above residual median"),
        ("Profile spike gate", f"{int(np.count_nonzero(spike_samples))} bar-major spike samples"),
        (
            "Spike rule",
            f"peak >= {100 * args.spike_excess_fraction:.0f}% above "
            f"{args.spike_neighbour_inner_arcsec:g}-{args.spike_neighbour_outer_arcsec:g} arcsec neighbours; "
            f">= {100 * args.spike_side_drop_fraction:.0f}% above +/-{args.spike_side_offset_samples} samples; "
            f"|r| >= {args.spike_center_exclusion_arcsec:g} arcsec",
        ),
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
    if tuning_rows:
        tuning_grid = ", ".join(f"{row['nsigma']:g}" for row in tuning_rows)
        parameter_rows.append(("Auto-tune grid", f"{tuning_grid} sigma; selected {detection_nsigma:g} sigma"))
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

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create portrait bar-spike-gated foreground-candidate comparison PDFs."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--names", nargs="*", default=[])
    parser.add_argument("--all", action="store_true", help="Process every galaxy in the manifest.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--profile-width", type=int, default=3)
    parser.add_argument("--smooth-sigma-pixels", type=float, default=15.0)
    parser.add_argument("--detection-nsigma", type=float, default=3.5)
    parser.add_argument(
        "--masking-mode",
        choices=["spike-gated", "global"],
        default="spike-gated",
        help="spike-gated masks only source segments intersecting bar-major profile spikes.",
    )
    parser.add_argument(
        "--auto-tune",
        action="store_true",
        help="Choose detection threshold per galaxy from --auto-tune-nsigmas.",
    )
    parser.add_argument(
        "--auto-tune-nsigmas",
        type=float,
        nargs="*",
        default=[5.0, 4.5, 4.0, 3.5],
        help="Candidate detection thresholds, ordered from conservative to aggressive.",
    )
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
    rows = read_rows(args.manifest)
    if args.all:
        selected = rows
    elif args.names:
        wanted = set(args.names)
        selected = [row for row in rows if row["name"] in wanted]
    else:
        selected = [read_row(args.manifest, "ESO120-012")]

    if args.limit is not None:
        selected = selected[: args.limit]

    if not selected:
        print("No galaxies selected.")
        return 1

    made = 0
    failed: list[tuple[str, str]] = []
    multiple = len(selected) > 1 or args.all or bool(args.names)
    for row in selected:
        galaxy_name = row["name"]
        output = (
            args.output_dir / f"{s4g_plot.safe_filename(galaxy_name)}_foreground_removed.pdf"
            if multiple
            else args.output
        )
        try:
            written = make_report(args, row, output)
        except Exception as exc:
            failed.append((galaxy_name, str(exc)))
            print(f"Failed {galaxy_name}: {exc}")
            continue
        made += 1
        print(f"Wrote {written}")

    print(f"Made {made} foreground-removal reports")
    if failed:
        print(f"Failed {len(failed)} galaxies:")
        for name, message in failed:
            print(f"  {name}: {message}")
    return 0 if made else 1


if __name__ == "__main__":
    raise SystemExit(main())
