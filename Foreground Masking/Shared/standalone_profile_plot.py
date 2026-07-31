"""Write consistently sized bar-major profile PNGs for later composition."""

from __future__ import annotations

import math
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np


FIGURE_SIZE_INCHES = (6.0, 4.0)
FIGURE_DPI = 200
AXES_RECT = (0.145, 0.155, 0.825, 0.790)


def common_y_limits(original_profile: np.ndarray) -> tuple[float, float]:
    """Return stable log limits based only on the unprocessed galaxy profile."""
    values = np.asarray(original_profile, dtype=float)
    positive = values[np.isfinite(values) & (values > 0)]
    if positive.size == 0:
        return 1.0, 10.0
    ymin = max(float(np.nanpercentile(positive, 2)) * 0.8, np.finfo(float).tiny)
    ymax = float(np.nanmax(positive)) * 1.25
    if not math.isfinite(ymin) or not math.isfinite(ymax) or ymax <= ymin:
        return 1.0, 10.0
    return ymin, ymax


def _true_runs(values: np.ndarray) -> list[tuple[int, int]]:
    indices = np.flatnonzero(np.asarray(values, dtype=bool))
    if indices.size == 0:
        return []
    splits = np.where(np.diff(indices) > 1)[0] + 1
    return [(int(group[0]), int(group[-1])) for group in np.split(indices, splits)]


def save_profile_png(
    path: Path,
    *,
    radii: np.ndarray,
    original_profile: np.ndarray,
    processed_profile: np.ndarray,
    replaced_samples: np.ndarray,
    bar_sma: float,
    central_exclusion_arcsec: float,
    title: str,
) -> Path:
    """Save one profile using geometry shared by every masking method."""
    radii = np.asarray(radii, dtype=float)
    original_profile = np.asarray(original_profile, dtype=float)
    processed_profile = np.asarray(processed_profile, dtype=float)
    replaced_samples = np.asarray(replaced_samples, dtype=bool)

    figure = Figure(figsize=FIGURE_SIZE_INCHES, dpi=FIGURE_DPI)
    FigureCanvasAgg(figure)
    ax = figure.add_axes(AXES_RECT)

    displayed = np.array(original_profile, copy=True)
    displayed[replaced_samples] = np.nan
    ax.semilogy(radii, displayed, color="#1f77b4", linewidth=1.4)

    bridge_label = "log-linear interpolation"
    for start, stop in _true_runs(replaced_samples):
        ax.axvspan(radii[start], radii[stop], color="#f4a6b8", alpha=0.28, linewidth=0)
        plot_start = max(0, start - 1)
        plot_stop = min(processed_profile.size - 1, stop + 1)
        section = slice(plot_start, plot_stop + 1)
        good = (
            np.isfinite(radii[section])
            & np.isfinite(processed_profile[section])
            & (processed_profile[section] > 0)
        )
        if np.count_nonzero(good) >= 2:
            ax.semilogy(
                radii[section][good],
                processed_profile[section][good],
                color="#1f77b4",
                linestyle="--",
                linewidth=1.4,
                label=bridge_label,
            )
            bridge_label = "_nolegend_"

    ax.axvline(-bar_sma, color="#1f77b4", linewidth=1.0)
    ax.axvline(bar_sma, color="#1f77b4", linewidth=1.0)
    if central_exclusion_arcsec > 0:
        ax.axvline(-central_exclusion_arcsec, color="#b59b00", linestyle="--", linewidth=1.0)
        ax.axvline(central_exclusion_arcsec, color="#b59b00", linestyle="--", linewidth=1.0)
    ax.axvline(0.0, color="0.6", linewidth=0.7)

    finite_radii = np.abs(radii[np.isfinite(radii)])
    radius_limit = float(np.nanmax(finite_radii)) if finite_radii.size else 1.0
    ax.set_xlim(-radius_limit, radius_limit)
    ax.set_ylim(*common_y_limits(original_profile))
    ax.set_xlabel("deprojected bar-major radius [arcsec]")
    ax.set_ylabel("intensity")
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.2)
    if np.any(replaced_samples):
        ax.legend(loc="best", fontsize=8)

    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=FIGURE_DPI, facecolor="white")
    return path
