#!/usr/bin/env python3
"""Break Gaia zero-score ties with 2MASS, weak Gaia, and image evidence."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS
import astropy.units as u
from astroquery.ipac.irsa import Irsa


SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
for folder in (PROJECT_ROOT, FOREGROUND_ROOT / "Shared", SCRIPT_DIR):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))

import foreground_display_helpers as display  # noqa: E402
import rank_clean_galaxies_2d as image_rank  # noqa: E402


def load_fits(path: Path) -> tuple[np.ndarray, fits.Header]:
    with fits.open(path) as hdul:
        return np.squeeze(np.asarray(hdul[0].data, dtype=float)), hdul[0].header.copy()


def cached_2mass(center: SkyCoord, radius: u.Quantity, cache: Path) -> Table:
    if cache.exists():
        return Table.read(cache, format="ascii.ecsv")
    table = Irsa.query_region(center, catalog="fp_psc", spatial="Cone", radius=radius)
    cache.parent.mkdir(parents=True, exist_ok=True)
    table.write(cache, format="ascii.ecsv", overwrite=True)
    return table


def clean_2mass_row(row) -> bool:
    ph_qual = str(row["ph_qual"])
    cc_flg = str(row["cc_flg"])
    k_quality = ph_qual[2] if len(ph_qual) >= 3 else "X"
    k_clean = cc_flg[2] == "0" if len(cc_flg) >= 3 else False
    return k_quality in "ABC" and k_clean and int(row["use_src"]) == 1 and float(row["k_snr"]) >= 5.0


def local_residual_products(image: np.ndarray, geometry: dict[str, float]):
    yy, xx = np.indices(image.shape)
    x0, y0 = geometry["xc"] - 1.0, geometry["yc"] - 1.0
    radius = np.hypot(xx - x0, yy - y0)
    aperture = max(12.0, 3.0 * geometry["bar_sma"] / geometry["pixel_scale"])
    center = max(3.0, 0.35 * geometry["bar_sma"] / geometry["pixel_scale"])
    model = image_rank.nan_gaussian(image, 5.0)
    residual = image - model
    annulus = (radius <= aperture) & (radius >= center) & np.isfinite(residual)
    location, sigma = image_rank.robust_location_scale(residual, annulus)
    for _ in range(3):
        location, sigma = image_rank.robust_location_scale(residual, annulus & (np.abs(residual - location) < 4 * sigma))
    z = (residual - location) / sigma
    model_sky = float(np.percentile(model[annulus & np.isfinite(model)], 20))
    underlying = np.maximum((model - model_sky) / sigma, 0.0)
    return z, underlying, aperture, center


def sample_catalog(table: Table, wcs: WCS, z: np.ndarray, underlying: np.ndarray, x0: float, y0: float, aperture: float, center: float, kind: str):
    if not len(table):
        return []
    ra_name, dec_name = ("ra", "dec") if "dec" in table.colnames else ("ra", "decl")
    coords = SkyCoord(np.asarray(table[ra_name]) * u.deg, np.asarray(table[dec_name]) * u.deg)
    xs, ys = wcs.world_to_pixel(coords)
    found = []
    for row, x, y in zip(table, xs, ys):
        ix, iy = int(round(float(x))), int(round(float(y)))
        if ix < 2 or iy < 2 or ix >= z.shape[1] - 2 or iy >= z.shape[0] - 2:
            continue
        distance = float(np.hypot(x - x0, y - y0))
        if distance < center or distance > aperture:
            continue
        local = z[iy - 2 : iy + 3, ix - 2 : ix + 3]
        if not np.any(np.isfinite(local)):
            continue
        peak = float(np.nanmax(local))
        if not math.isfinite(peak):
            continue
        if peak < 2.5:
            continue
        structure = 0.25 + 0.75 / (1.0 + float(underlying[iy, ix]) / 5.0)
        if kind == "2mass":
            if not clean_2mass_row(row):
                continue
            k_mag = float(row["k_m"])
            brightness = np.clip((16.0 - k_mag) / 5.0, 0.1, 1.5)
            score = structure * brightness * math.log1p(peak - 2.5)
        else:
            parallax_sig = abs(float(row["parallax_over_error"])) if np.isfinite(row["parallax_over_error"]) else 0.0
            score = 0.12 * structure * min(parallax_sig / 3.0, 1.0) * math.log1p(peak - 2.5)
        found.append({"x": float(x), "y": float(y), "score": float(score), "peak": peak})
    return sorted(found, key=lambda item: item["score"], reverse=True)


def save_sheet(results: list[dict], output: Path) -> None:
    cols, rows = 5, math.ceil(len(results) / 5)
    fig, axes = plt.subplots(rows, cols, figsize=(16, 3.2 * rows), squeeze=False)
    for ax in axes.ravel():
        ax.set_axis_off()
    for rank, (ax, result) in enumerate(zip(axes.ravel(), results), start=1):
        image, radius = result["image"], int(math.ceil(result["aperture"]))
        x0, y0 = int(round(result["x0"])), int(round(result["y0"]))
        x1, x2 = max(0, x0 - radius), min(image.shape[1], x0 + radius + 1)
        y1, y2 = max(0, y0 - radius), min(image.shape[0], y0 + radius + 1)
        view = image[y1:y2, x1:x2]
        lo, hi = np.percentile(view[np.isfinite(view)], [5, 99.5])
        ax.imshow(view, origin="lower", cmap="gray", vmin=lo, vmax=hi)
        for source in result["two_mass"][:5]:
            ax.add_patch(plt.Circle((source["x"] - x1, source["y"] - y1), 4, fill=False, color="#ff3b30", lw=0.9))
        for source in result["weak_gaia"][:5]:
            ax.add_patch(plt.Circle((source["x"] - x1, source["y"] - y1), 3, fill=False, color="#ffcc00", lw=0.7))
        ax.set_title(f"{rank}. {result['name']}\nscore {result['hybrid_score']:.2f}; 2MASS={len(result['two_mass'])}", fontsize=8)
    fig.suptitle("Gaia-zero hybrid ranking (red: 2MASS; yellow: weak Gaia)")
    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)


def save_review_panel(result: dict, output: Path) -> None:
    """Write a wide, galaxy-centred panel matching the masking diagnostics."""
    image, z, geometry = result["image"], result["z_image"], result["geometry"]
    radius_arcsec = display.profile_radius_pixels(image, geometry) * geometry["pixel_scale"]
    view, x_axis, y_axis = display.deproject_bar_aligned_cutout(image, geometry, radius_arcsec)
    zview, _, _ = display.deproject_bar_aligned_cutout(z, geometry, radius_arcsec)
    extent = [x_axis[0], x_axis[-1], y_axis[0], y_axis[-1]]
    lo, hi = display.robust_limits(view, low=1.0, high=99.5)
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.6))
    axes[0].imshow(view, origin="lower", cmap="gist_gray_r", vmin=lo, vmax=hi, extent=extent)
    axes[0].set_title("Galaxy-centred original (negative)")
    axes[1].imshow(zview, origin="lower", cmap="coolwarm", vmin=-5, vmax=10, extent=extent)
    axes[1].set_title("Centred Gaussian residual (σ)")
    axes[2].imshow(view, origin="lower", cmap="gist_gray_r", vmin=lo, vmax=hi, extent=extent)
    axes[2].set_title("Centred original + catalogue candidates")
    transform = display.image_transform(geometry["disk_pa"], geometry["inclination"], geometry["bar_pa"])
    x0, y0 = result["x0"], result["y0"]

    def centred_position(source: dict) -> tuple[float, float]:
        offset = transform @ np.array([source["x"] - x0, source["y"] - y0])
        return float(offset[0] * geometry["pixel_scale"]), float(offset[1] * geometry["pixel_scale"])

    for source in result["two_mass"][:5]:
        axes[2].add_patch(plt.Circle(centred_position(source), 2.0, fill=False, color="#ff3b30", lw=1.5))
    for source in result["weak_gaia"][:5]:
        axes[2].add_patch(plt.Circle(centred_position(source), 1.5, fill=False, color="#ffcc00", lw=1.2))
    for axis in axes:
        axis.axvline(0, color="#e53935", linestyle="--", linewidth=0.7, alpha=0.75)
        axis.axhline(0, color="#1976d2", linestyle="--", linewidth=0.7, alpha=0.75)
        axis.set_xlabel("bar-aligned arcsec")
        axis.set_ylabel("deprojected arcsec")
    fig.suptitle(
        f"{result['name']} — hybrid score {result['hybrid_score']:.3f}; "
        f"2MASS={len(result['two_mass'])}; weak Gaia={len(result['weak_gaia'])}"
    )
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gaia-ranking", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=display.DEFAULT_MANIFEST)
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--gaia-cache", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--include-nonzero", action="store_true",
        help="Select positive-score Gaia rows instead of exact-zero rows.",
    )
    parser.add_argument("--limit", type=int, help="Keep only the first N selected Gaia-ranking rows.")
    parser.add_argument(
        "--exclude-decisions", type=Path,
        help="Exclude galaxy names already present in this reviewer decisions CSV.",
    )
    parser.add_argument(
        "--names-file", type=Path,
        help="Optional CSV with a name column. This overrides Gaia zero/nonzero selection and preserves its order.",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with args.gaia_ranking.open(newline="", encoding="utf-8") as handle:
        ranking_rows = list(csv.DictReader(handle))
    if args.names_file:
        with args.names_file.open(newline="", encoding="utf-8") as handle:
            selected_names = [row["name"] for row in csv.DictReader(handle)]
    elif args.include_nonzero:
        selected_names = [row["name"] for row in ranking_rows if float(row["pollution_score"]) > 0.0]
    else:
        selected_names = [row["name"] for row in ranking_rows if float(row["pollution_score"]) == 0.0]
    if args.exclude_decisions and args.exclude_decisions.exists():
        with args.exclude_decisions.open(newline="", encoding="utf-8") as handle:
            excluded = {row["name"] for row in csv.DictReader(handle)}
        selected_names = [name for name in selected_names if name not in excluded]
    if args.limit is not None:
        selected_names = selected_names[: args.limit]
    manifest = {row["name"]: row for row in display.read_manifest(args.manifest)}
    results = []
    for index, name in enumerate(selected_names, start=1):
        row = manifest[name]
        geometry = display.required_geometry(row)
        if geometry is None:
            continue
        image, header = load_fits(args.image_dir / f"{name}.phot.1.fits")
        wcs = WCS(header).celestial
        x0, y0 = geometry["xc"] - 1.0, geometry["yc"] - 1.0
        center_coord = wcs.pixel_to_world(x0, y0)
        radius = 3.0 * geometry["bar_sma"] * u.arcsec
        two_mass_table = cached_2mass(center_coord, radius, args.output_dir / "twomass_cache" / f"{name}.ecsv")
        gaia_path = args.gaia_cache / f"{name}_v3.ecsv"
        gaia_table = Table.read(gaia_path, format="ascii.ecsv") if gaia_path.exists() else Table()
        z, underlying, aperture, center = local_residual_products(image, geometry)
        two_mass = sample_catalog(two_mass_table, wcs, z, underlying, x0, y0, aperture, center, "2mass")
        weak_gaia = sample_catalog(gaia_table, wcs, z, underlying, x0, y0, aperture, center, "gaia")
        # Catalogue evidence dominates. A very small image-only term breaks any
        # remaining ties without recreating the original morphology bias.
        image_metrics, _, _ = image_rank.score_image(
            image, geometry, blur_sigma=5, threshold=7, min_pixels=8,
            aperture_bar_radii=3, aperture_r25_radii=0, center_bar_radii=0.35,
            max_segment_fraction=0.02, galaxy_downweight_nsigma=3,
            max_scored_sources=3, inside_galaxy_weight=0.15,
            detector="dao", dao_fwhm=2.5,
        )
        hybrid = sum(item["score"] for item in two_mass[:5]) + sum(item["score"] for item in weak_gaia[:5]) + 0.01 * float(image_metrics["pollution_score"])
        results.append({"name": name, "hybrid_score": hybrid, "twomass_count": len(two_mass), "weak_gaia_count": len(weak_gaia), "image_tiebreak_score": image_metrics["pollution_score"], "image": image, "z_image": z, "two_mass": two_mass, "weak_gaia": weak_gaia, "aperture": aperture, "x0": x0, "y0": y0, "geometry": geometry})
        print(f"[{index}/{len(selected_names)}] {name}: {hybrid:.3f} (2MASS={len(two_mass)}, weak Gaia={len(weak_gaia)})", flush=True)
    results.sort(key=lambda item: item["hybrid_score"])
    fields = ["rank", "name", "hybrid_score", "twomass_count", "weak_gaia_count", "image_tiebreak_score"]
    with (args.output_dir / "gaia_zero_hybrid_ranking.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for rank, result in enumerate(results, start=1):
            writer.writerow({"rank": rank, **result})
    save_sheet(results, args.output_dir / "gaia_zero_hybrid_contact_sheet.png")
    candidate_fields = ["rank", "name", "catalogue", "candidate_rank", "x", "y", "score", "peak"]
    with (args.output_dir / "hybrid_candidates.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=candidate_fields)
        writer.writeheader()
        for rank, result in enumerate(results, start=1):
            for catalogue, candidates in (("2MASS", result["two_mass"]), ("weak_Gaia", result["weak_gaia"])):
                for candidate_rank, candidate in enumerate(candidates, start=1):
                    writer.writerow({"rank": rank, "name": result["name"], "catalogue": catalogue, "candidate_rank": candidate_rank, **candidate})
            save_review_panel(result, args.output_dir / "review_panels" / f"{result['name']}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
