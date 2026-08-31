#!/usr/bin/env python3
"""Physically motivated source injections for S4G foreground-mask testing.

The model follows the experimental principles in Haigh et al. (2021): point
sources are convolved with the survey PSF, galaxies are PSF-convolved Sersic
models, and truth is tied to the local noise rather than a fixed fraction of
the source peak.  It is deliberately independent of SEP and MTObjects.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Iterable

import numpy as np
from scipy import ndimage


MODEL_VERSION = "haigh-aligned-s4g-empty-field-injections-v2"
IRAC_36_PSF_FWHM_ARCSEC = 1.66
DEFAULT_TRUTH_SIGMA = 1.0


def _nan_gaussian(data: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian smoothing that does not bleed invalid mosaic pixels inward."""
    values = np.asarray(data, dtype=float)
    finite = np.isfinite(values)
    numerator = ndimage.gaussian_filter(np.where(finite, values, 0.0), sigma=sigma, mode="constant")
    denominator = ndimage.gaussian_filter(finite.astype(float), sigma=sigma, mode="constant")
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(denominator > 0.2, numerator / denominator, np.nan)


def quiet_placement_region(
    data: np.ndarray,
    analysis_region: np.ndarray,
    geometry: dict[str, float],
    *,
    structure_sigma: float = 1.5,
    compact_sigma: float = 3.0,
    clearance_arcsec: float = 5.0,
) -> tuple[np.ndarray, np.ndarray, dict[str, float | int | str]]:
    """Return empty-field-like source-centre positions inside the displayed frame.

    Bright, smoothly varying target-galaxy structure and compact positive
    residuals already present in the science frame are excluded, then buffered.
    Background statistics are measured in the outer part of the displayed
    region so that the target galaxy does not define its own background.
    """
    image = np.asarray(data, dtype=float)
    region = np.asarray(analysis_region, dtype=bool) & np.isfinite(image)
    yy, xx = np.indices(image.shape, dtype=float)
    xc = float(geometry["xc"]) - 1.0
    yc = float(geometry["yc"]) - 1.0
    equivalent_radius = math.sqrt(max(1, int(np.count_nonzero(region))) / math.pi)
    outer = region & (np.hypot(xx - xc, yy - yc) >= 0.58 * equivalent_radius)
    if np.count_nonzero(outer) < 200:
        outer = region

    smooth = _nan_gaussian(image, sigma=3.0)
    outer_smooth = smooth[outer & np.isfinite(smooth)]
    background = float(np.median(outer_smooth)) if outer_smooth.size else float(np.nanmedian(smooth[region]))
    smooth_noise = robust_sigma(outer_smooth) if outer_smooth.size else robust_sigma(smooth[region])
    broad_structure = region & (smooth > background + float(structure_sigma) * smooth_noise)

    high_pass = image - _nan_gaussian(image, sigma=2.0)
    residual_noise = robust_sigma(high_pass[outer & np.isfinite(high_pass)])
    compact_existing = region & (high_pass > float(compact_sigma) * residual_noise)

    # Always reserve the central target region even when its surface brightness
    # happens to be weak relative to a structured outer mosaic.
    central = region & (np.hypot(xx - xc, yy - yc) < 0.12 * equivalent_radius)
    excluded = broad_structure | compact_existing | central
    allowed_truth_region = region & ~excluded
    pixel_scale = float(geometry["pixel_scale"])
    clearance_pixels = max(2, int(math.ceil(float(clearance_arcsec) / pixel_scale)))
    excluded = ndimage.binary_dilation(excluded, iterations=clearance_pixels)
    boundary_distance = ndimage.distance_transform_edt(region)
    eligible = region & ~excluded & (boundary_distance > clearance_pixels)
    metadata: dict[str, float | int | str] = {
        "definition": (
            "displayed finite region excluding target-galaxy smooth light, "
            "pre-existing compact positive residuals, central target area, and safety buffers"
        ),
        "structure_threshold_sigma": float(structure_sigma),
        "compact_source_threshold_sigma": float(compact_sigma),
        "clearance_arcsec": float(clearance_arcsec),
        "clearance_pixels": clearance_pixels,
        "eligible_centre_pixels": int(np.count_nonzero(eligible)),
        "displayed_region_pixels": int(np.count_nonzero(region)),
        "eligible_fraction": float(np.count_nonzero(eligible) / max(1, np.count_nonzero(region))),
    }
    return eligible, allowed_truth_region, metadata


@dataclass(frozen=True)
class InjectedSource:
    # These fields retain compatibility with the existing optimiser loaders.
    image_name: str
    toy_id: int
    object_type: str
    x: float
    y: float
    peak_sigma: float
    fwhm_pixels: float
    axis_ratio: float
    pa_deg: float
    truth_pixels: int
    # Additional provenance used by the revised reviewer and reports.
    model_family: str
    effective_radius_arcsec: float | None
    effective_radius_pixels: float | None
    sersic_index: float | None
    psf_fwhm_arcsec: float
    psf_fwhm_pixels: float
    truth_sigma_threshold: float
    truth_definition: str

    def manifest_record(self) -> dict[str, object]:
        return asdict(self)


def robust_sigma(data: np.ndarray) -> float:
    finite = np.asarray(data, dtype=float)
    finite = finite[np.isfinite(finite)]
    if not finite.size:
        return 1.0
    median = float(np.median(finite))
    value = 1.4826 * float(np.median(np.abs(finite - median)))
    if not math.isfinite(value) or value <= 0:
        value = float(np.std(finite))
    return value if math.isfinite(value) and value > 0 else 1.0


def source_count_for_region(region_pixels: int, pixels_per_source: int = 5000,
                            minimum: int = 1, maximum: int = 5) -> int:
    """Scale source count with usable displayed-frame area, bounded at 1--5."""
    if region_pixels <= 0:
        return 0
    return int(np.clip(round(region_pixels / max(1, pixels_per_source)), minimum, maximum))


def gaussian_psf(shape: tuple[int, int], x0: float, y0: float, fwhm_pixels: float) -> np.ndarray:
    yy, xx = np.indices(shape, dtype=float)
    sigma = max(0.25, float(fwhm_pixels) / 2.354820045)
    return np.exp(-0.5 * (((xx - x0) / sigma) ** 2 + ((yy - y0) / sigma) ** 2))


def irac_star_model(shape: tuple[int, int], x0: float, y0: float, peak: float,
                    psf_fwhm_pixels: float, wing_fraction: float = 0.04) -> np.ndarray:
    """Approximate the IRAC PRF with a measured-width core plus faint wings."""
    core = gaussian_psf(shape, x0, y0, psf_fwhm_pixels)
    wings = gaussian_psf(shape, x0, y0, psf_fwhm_pixels * 3.2)
    model = (1.0 - wing_fraction) * core + wing_fraction * wings
    return model * (float(peak) / float(np.max(model)))


def sersic_model(shape: tuple[int, int], x0: float, y0: float, effective_radius_pixels: float,
                  sersic_index: float, axis_ratio: float, pa_deg: float) -> np.ndarray:
    """Return a unit-central-amplitude elliptical Sersic profile."""
    yy, xx = np.indices(shape, dtype=float)
    theta = math.radians(float(pa_deg))
    dx, dy = xx - float(x0), yy - float(y0)
    major = dx * math.cos(theta) + dy * math.sin(theta)
    minor = -dx * math.sin(theta) + dy * math.cos(theta)
    radius = np.sqrt(major * major + (minor / max(0.05, float(axis_ratio))) ** 2)
    n = float(sersic_index)
    bn = 2.0 * n - 1.0 / 3.0 + 4.0 / (405.0 * n) + 46.0 / (25515.0 * n * n)
    exponent = -bn * np.power(radius / max(0.05, float(effective_radius_pixels)), 1.0 / n)
    # Clip before exp to avoid underflow warnings in large FITS mosaics.
    return np.exp(np.clip(exponent, -745.0, 0.0))


def background_galaxy_model(shape: tuple[int, int], x0: float, y0: float, peak: float,
                            effective_radius_pixels: float, sersic_index: float,
                            axis_ratio: float, pa_deg: float,
                            psf_fwhm_pixels: float) -> np.ndarray:
    intrinsic = sersic_model(
        shape, x0, y0, effective_radius_pixels, sersic_index, axis_ratio, pa_deg
    )
    sigma_psf = max(0.25, psf_fwhm_pixels / 2.354820045)
    convolved = ndimage.gaussian_filter(intrinsic, sigma=sigma_psf, mode="constant", cval=0.0)
    maximum = float(np.max(convolved))
    return convolved * (float(peak) / maximum) if maximum > 0 else convolved


def noise_truth(model: np.ndarray, noise_sigma: float, threshold_sigma: float,
                *, encircled_energy_cap: float | None = None) -> np.ndarray:
    """Truth where source light exceeds local noise, optionally capped by flux."""
    truth = np.asarray(model >= float(threshold_sigma) * float(noise_sigma), dtype=bool)
    if encircled_energy_cap is None or not np.any(truth):
        return truth
    flat = np.asarray(model, dtype=float).ravel()
    order = np.argsort(flat)[::-1]
    cumulative = np.cumsum(flat[order])
    total = float(cumulative[-1])
    if total <= 0:
        return np.zeros(model.shape, dtype=bool)
    keep_count = int(np.searchsorted(cumulative, encircled_energy_cap * total, side="left")) + 1
    cap = np.zeros(flat.size, dtype=bool)
    cap[order[:keep_count]] = True
    return truth & cap.reshape(model.shape)


def _well_separated(candidate: np.ndarray, existing: np.ndarray, separation_pixels: int) -> bool:
    if not np.any(existing):
        return True
    expanded = ndimage.binary_dilation(existing, iterations=max(1, int(separation_pixels)))
    return not np.any(candidate & expanded)


def _source_types(count: int, rng: np.random.Generator, galaxy_fraction: float) -> list[str]:
    types = ["background_galaxy" if rng.random() < galaxy_fraction else "foreground_star" for _ in range(count)]
    # Medium/large frames always exercise the rarer galaxy morphology without
    # forcing a galaxy into every very small frame. Stars remain stochastic.
    if count >= 3 and "background_galaxy" not in types:
        types[int(rng.integers(0, count))] = "background_galaxy"
    rng.shuffle(types)
    return types


def inject_sources(
    name: str,
    data: np.ndarray,
    geometry: dict[str, float],
    analysis_region: np.ndarray,
    rng: np.random.Generator,
    *,
    requested_count: int | None = None,
    pixels_per_source: int = 5000,
    maximum_sources: int = 5,
    galaxy_fraction: float = 0.25,
    peak_sigma_min: float = 6.0,
    peak_sigma_max: float = 30.0,
    truth_sigma: float = DEFAULT_TRUTH_SIGMA,
    minimum_separation_pixels: int = 4,
    placement_region: np.ndarray | None = None,
    allowed_truth_region: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[InjectedSource]]:
    """Inject a deterministic mixture of IRAC stars and Haigh-like galaxies."""
    if not 0 < peak_sigma_min < peak_sigma_max:
        raise ValueError("Peak-sigma bounds must satisfy 0 < minimum < maximum.")
    pixel_scale = float(geometry["pixel_scale"])
    if pixel_scale <= 0:
        raise ValueError(f"{name}: invalid pixel scale {pixel_scale}")
    psf_fwhm_pixels = IRAC_36_PSF_FWHM_ARCSEC / pixel_scale
    count = requested_count if requested_count is not None else source_count_for_region(
        int(np.count_nonzero(analysis_region)), pixels_per_source, maximum=maximum_sources
    )
    count = int(np.clip(count, 1, maximum_sources))
    noise = robust_sigma(data)
    injected = np.asarray(data, dtype=float).copy()
    truth_mask = np.zeros(data.shape, dtype=bool)
    truth_labels = np.zeros(data.shape, dtype=np.int32)
    sources: list[InjectedSource] = []
    source_centres = analysis_region if placement_region is None else placement_region
    source_centres = np.asarray(source_centres, dtype=bool) & np.asarray(analysis_region, dtype=bool)
    valid_y, valid_x = np.nonzero(source_centres)
    margin = max(8, int(math.ceil(5.0 * psf_fwhm_pixels)))
    keep = (
        (valid_x >= margin) & (valid_x < data.shape[1] - margin)
        & (valid_y >= margin) & (valid_y < data.shape[0] - margin)
    )
    valid_y, valid_x = valid_y[keep], valid_x[keep]
    if not valid_x.size:
        raise ValueError(f"{name}: no valid source positions inside the displayed analysis region")

    for source_type in _source_types(count, rng, galaxy_fraction):
        chosen = None
        for _ in range(10000):
            index = int(rng.integers(0, valid_x.size))
            x0, y0 = float(valid_x[index]), float(valid_y[index])
            peak_sigma = float(rng.uniform(peak_sigma_min, peak_sigma_max))
            if source_type == "foreground_star":
                model = irac_star_model(data.shape, x0, y0, peak_sigma * noise, psf_fwhm_pixels)
                truth = noise_truth(model, noise, truth_sigma, encircled_energy_cap=0.95)
                effective_radius_arcsec = None
                effective_radius_pixels = None
                sersic_index = None
                axis_ratio, pa_deg = 1.0, 0.0
            else:
                effective_radius_arcsec = float(rng.uniform(0.5, 3.5))
                effective_radius_pixels = effective_radius_arcsec / pixel_scale
                sersic_index = float(rng.uniform(2.0, 4.0))
                axis_ratio = float(rng.uniform(0.3, 1.0))
                pa_deg = float(rng.uniform(0.0, 180.0))
                model = background_galaxy_model(
                    data.shape, x0, y0, peak_sigma * noise, effective_radius_pixels,
                    sersic_index, axis_ratio, pa_deg, psf_fwhm_pixels,
                )
                truth = noise_truth(model, noise, truth_sigma)
            if not np.any(truth) or np.any(truth & ~analysis_region):
                continue
            if allowed_truth_region is not None and np.any(truth & ~np.asarray(allowed_truth_region, dtype=bool)):
                continue
            if not _well_separated(truth, truth_mask, minimum_separation_pixels):
                continue
            chosen = (
                x0, y0, peak_sigma, model, truth, effective_radius_arcsec,
                effective_radius_pixels, sersic_index, axis_ratio, pa_deg,
            )
            break
        if chosen is None:
            # Area-dependent count is a target, not a reason to invalidate a
            # galaxy. Retain every successfully placed source and stop here.
            break
        (x0, y0, peak_sigma, model, truth, effective_radius_arcsec,
         effective_radius_pixels, sersic_index, axis_ratio, pa_deg) = chosen
        injected[np.isfinite(injected)] += model[np.isfinite(injected)]
        toy_id = len(sources) + 1
        truth_mask |= truth
        truth_labels[truth] = toy_id
        sources.append(InjectedSource(
            image_name=name, toy_id=toy_id, object_type=("star" if source_type == "foreground_star" else "galaxy"),
            x=x0, y=y0, peak_sigma=peak_sigma,
            fwhm_pixels=psf_fwhm_pixels if source_type == "foreground_star" else 2.0 * float(effective_radius_pixels),
            axis_ratio=axis_ratio, pa_deg=pa_deg, truth_pixels=int(np.count_nonzero(truth)),
            model_family="IRAC-3.6-PSF" if source_type == "foreground_star" else "PSF-convolved-Sersic",
            effective_radius_arcsec=effective_radius_arcsec,
            effective_radius_pixels=effective_radius_pixels, sersic_index=sersic_index,
            psf_fwhm_arcsec=IRAC_36_PSF_FWHM_ARCSEC, psf_fwhm_pixels=psf_fwhm_pixels,
            truth_sigma_threshold=truth_sigma,
            truth_definition=("local-noise threshold intersected with 95% model flux" if source_type == "foreground_star"
                              else "model surface brightness >= local-noise threshold"),
        ))
    if not sources:
        raise ValueError(f"{name}: unable to place any revised sources")
    return injected, truth_mask, truth_labels, sources


def summarise_sources(sources: Iterable[InjectedSource]) -> dict[str, int]:
    values = list(sources)
    return {
        "total": len(values),
        "foreground_stars": sum(source.object_type == "star" for source in values),
        "background_galaxies": sum(source.object_type == "galaxy" for source in values),
    }
