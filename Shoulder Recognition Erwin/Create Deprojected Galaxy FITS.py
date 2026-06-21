#!/usr/bin/env python3
"""Create centred, face-on, bar-aligned FITS images for the Erwin sample.

The sample selection and geometry inputs are the same as those used by
``Real Galaxy Shoulder Quantification v0.69.py``.  Position angles follow the
pixel convention used by ``plot_s4g_isophote_axes.py``.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path

import numpy as np
from astropy.io import fits
from scipy.ndimage import affine_transform


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESEARCH_ROOT = Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research")
ERWIN_DATA = RESEARCH_ROOT / "Erwin" / "perwin-barprofiles_paper-a7cd6f5" / "data"
IMAGE_DIR = RESEARCH_ROOT / "Erwin" / "s4g_images_36um"
MANIFEST = (
    PROJECT_ROOT
    / "Erwin_s4g_image_downloader"
    / "geometry_output"
    / "s4g_image_geometry_manifest.csv"
)
OUTPUT_DIR = RESEARCH_ROOT / "Shoulder_Recognition_Erwin" / "Deprojected_Images"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--image-dir", type=Path, default=IMAGE_DIR)
    parser.add_argument("--erwin-data", type=Path, default=ERWIN_DATA)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--order",
        type=int,
        choices=range(0, 6),
        default=3,
        metavar="N",
        help="spline interpolation order (0--5; default: 3)",
    )
    parser.add_argument(
        "--no-overwrite", action="store_true", help="skip existing output FITS files"
    )
    parser.add_argument(
        "--all-manifest",
        action="store_true",
        help="process every manifest galaxy instead of the classified Erwin sample",
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="process only the first N selected galaxies (useful for test runs)",
    )
    parser.add_argument(
        "--galaxy",
        action="append",
        metavar="NAME",
        help="process a named galaxy; repeat this option for multiple galaxies",
    )
    return parser.parse_args()


def finite_float(value: str | None) -> float | None:
    try:
        result = float(value) if value not in (None, "") else None
    except ValueError:
        return None
    return result if result is not None and math.isfinite(result) else None


def read_manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


def read_descramble_map(path: Path) -> dict[int, str]:
    mapping: dict[int, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip() and not line.startswith("#"):
                fields = line.split()
                mapping[int(fields[0])] = fields[2]
    return mapping


def read_classified_names(data_dir: Path) -> list[str]:
    descramble = read_descramble_map(data_dir / "scrambled_map.txt")
    names: set[str] = set()
    for filename in ("classifications_pe.txt", "classifications_vd_revised.txt"):
        with (data_dir / filename).open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip() or line.startswith("#"):
                    continue
                fields = line.split()
                if len(fields) > 1 and fields[1] != "?":
                    names.add(descramble[int(fields[0])])
    return sorted(names)


def geometry(row: dict[str, str], shape: tuple[int, int]) -> dict[str, float]:
    values = {
        "xc": finite_float(row.get("center_x_pix")),
        "yc": finite_float(row.get("center_y_pix")),
        "crpix1": finite_float(row.get("crpix1")),
        "crpix2": finite_float(row.get("crpix2")),
        "disk_pa": finite_float(row.get("disk_pa_deg")),
        "inclination": finite_float(row.get("inclination_deg")),
        "bar_pa": finite_float(row.get("bar_pa_deg")),
        "pixel_scale_x": finite_float(row.get("pixel_scale_arcsec_x")),
        "pixel_scale_y": finite_float(row.get("pixel_scale_arcsec_y")),
    }
    required = ("xc", "yc", "disk_pa", "inclination", "bar_pa")
    if any(values[key] is None for key in required):
        raise ValueError("missing required centre/PA/inclination geometry")

    xc, yc = values["xc"], values["yc"]
    assert xc is not None and yc is not None
    if not (1 <= xc <= shape[1] and 1 <= yc <= shape[0]):
        xc, yc = values["crpix1"], values["crpix2"]
        if xc is None or yc is None or not (1 <= xc <= shape[1] and 1 <= yc <= shape[0]):
            raise ValueError("catalogue centre is outside image and CRPIX fallback is invalid")

    inclination = values["inclination"]
    assert inclination is not None
    if not 0 <= inclination < 90:
        raise ValueError(f"inclination must be in [0, 90) degrees, got {inclination}")

    return {
        "xc": xc,
        "yc": yc,
        "disk_pa": values["disk_pa"] % 180.0,  # type: ignore[operator]
        "inclination": inclination,
        "bar_pa": values["bar_pa"] % 180.0,  # type: ignore[operator]
        "pixel_scale_x": abs(values["pixel_scale_x"] or 0.75),
        "pixel_scale_y": abs(values["pixel_scale_y"] or 0.75),
    }


def image_transform(disk_pa: float, inclination: float, bar_pa: float) -> np.ndarray:
    """Map observed (column, row) offsets to face-on, bar-aligned offsets."""
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


def output_shape_and_center(
    shape: tuple[int, int], center_xy: np.ndarray, transform_xy: np.ndarray
) -> tuple[tuple[int, int], np.ndarray]:
    ny, nx = shape
    corners = np.array(
        [[0, 0], [nx - 1, 0], [0, ny - 1], [nx - 1, ny - 1]], dtype=float
    )
    transformed = (transform_xy @ (corners - center_xy).T).T
    radius_x, radius_y = np.ceil(np.max(np.abs(transformed), axis=0)).astype(int)
    return (2 * radius_y + 1, 2 * radius_x + 1), np.array([radius_x, radius_y])


def resample(
    data: np.ndarray, geom: dict[str, float], order: int
) -> tuple[np.ndarray, np.ndarray]:
    center_xy = np.array([geom["xc"] - 1.0, geom["yc"] - 1.0])
    transform_xy = image_transform(
        geom["disk_pa"], geom["inclination"], geom["bar_pa"]
    )
    output_shape, output_center_xy = output_shape_and_center(
        data.shape, center_xy, transform_xy
    )

    # scipy.ndimage uses (row, column), whereas the geometry above uses (x, y).
    swap = np.array([[0.0, 1.0], [1.0, 0.0]])
    matrix_rc = swap @ np.linalg.inv(transform_xy) @ swap
    center_in_rc = center_xy[::-1]
    center_out_rc = output_center_xy[::-1]
    offset_rc = center_in_rc - matrix_rc @ center_out_rc
    valid = np.isfinite(data)
    filled = np.where(valid, data, 0.0)
    result = affine_transform(
        filled,
        matrix_rc,
        offset=offset_rc,
        output_shape=output_shape,
        order=order,
        mode="constant",
        cval=0.0,
        prefilter=order > 1,
    )
    # Spline prefiltering an array containing NaNs contaminates every spline
    # coefficient.  Transform a validity map separately and use it both to
    # normalise edge pixels and to restore blank regions to NaN.
    support = affine_transform(
        valid.astype(float),
        matrix_rc,
        offset=offset_rc,
        output_shape=output_shape,
        order=1,
        mode="constant",
        cval=0.0,
        prefilter=False,
    )
    result = np.divide(
        result,
        support,
        out=np.full(output_shape, np.nan, dtype=float),
        where=support > 1.0e-3,
    )
    return result, output_center_xy


_WCS_KEY = re.compile(
    r"^(CRPIX|CRVAL|CTYPE|CUNIT|CDELT|CROTA|CD|PC|PV|PS|WCSAXES|LONPOLE|LATPOLE)"
)


def output_header(
    source: fits.Header,
    geom: dict[str, float],
    center_xy: np.ndarray,
    source_name: str,
    order: int,
) -> fits.Header:
    header = source.copy()
    for key in list(header):
        if _WCS_KEY.match(key):
            del header[key]
    header["CRPIX1"] = (center_xy[0] + 1.0, "Galaxy centre, FITS pixel coordinate")
    header["CRPIX2"] = (center_xy[1] + 1.0, "Galaxy centre, FITS pixel coordinate")
    header["CRVAL1"] = (0.0, "Offset at galaxy centre")
    header["CRVAL2"] = (0.0, "Offset at galaxy centre")
    header["CTYPE1"] = ("X---LINEAR", "Deprojected bar-major coordinate")
    header["CTYPE2"] = ("Y---LINEAR", "Deprojected bar-minor coordinate")
    header["CUNIT1"] = "arcsec"
    header["CUNIT2"] = "arcsec"
    header["CDELT1"] = geom["pixel_scale_x"]
    header["CDELT2"] = geom["pixel_scale_y"]
    header["GALAXY"] = source_name
    header["DISKPA"] = (geom["disk_pa"], "Input disk PA [deg]")
    header["BARPA"] = (geom["bar_pa"], "Input observed bar PA [deg]")
    header["INCL"] = (geom["inclination"], "Input disk inclination [deg]")
    header["DEPROJ"] = (True, "Disk deprojected to face-on")
    header["BARALIGN"] = (True, "Deprojected bar aligned with +X/-X")
    header["INTERP"] = (order, "scipy spline interpolation order")
    header.add_history("Centred, disk-deprojected, and bar-aligned by this script.")
    header.add_history("Surface-brightness pixel values were interpolated, not flux-scaled.")
    return header


def process_galaxy(
    name: str,
    row: dict[str, str],
    image_dir: Path,
    output_dir: Path,
    order: int,
    overwrite: bool,
) -> str:
    output_path = output_dir / f"{name}_deprojected_bar_aligned.fits"
    if output_path.exists() and not overwrite:
        return "skipped (already exists)"

    image_path = Path(row.get("image_path") or "")
    if not image_path.is_file():
        image_path = image_dir / f"{name}.phot.1.fits"
    if not image_path.is_file():
        raise FileNotFoundError("S4G 3.6-micron FITS image not found")

    with fits.open(image_path, memmap=False) as hdul:
        data = np.squeeze(np.asarray(hdul[0].data, dtype=float))
        source_header = hdul[0].header
    if data.ndim != 2:
        raise ValueError("primary FITS image is not two-dimensional after squeeze")

    geom = geometry(row, data.shape)
    transformed, center_xy = resample(data, geom, order)
    header = output_header(source_header, geom, center_xy, name, order)
    fits.PrimaryHDU(transformed.astype(np.float32), header).writeto(
        output_path, overwrite=overwrite, checksum=True
    )
    return f"wrote {output_path.name} ({transformed.shape[1]} x {transformed.shape[0]})"


def main() -> int:
    args = parse_args()
    rows = read_manifest(args.manifest)
    if args.galaxy:
        names = list(dict.fromkeys(args.galaxy))
    else:
        names = sorted(rows) if args.all_manifest else read_classified_names(args.erwin_data)
    if args.limit is not None:
        if args.limit < 1:
            raise SystemExit("--limit must be at least 1")
        names = names[: args.limit]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    failures: list[tuple[str, str]] = []
    for index, name in enumerate(names, start=1):
        row = rows.get(name)
        if row is None:
            failures.append((name, "missing geometry manifest row"))
            print(f"[{index}/{len(names)}] {name}: FAILED - missing geometry manifest row")
            continue
        try:
            message = process_galaxy(
                name,
                row,
                args.image_dir,
                args.output_dir,
                args.order,
                overwrite=not args.no_overwrite,
            )
        except Exception as exc:  # continue the batch and report every unusable galaxy
            failures.append((name, str(exc)))
            message = f"FAILED - {exc}"
        print(f"[{index}/{len(names)}] {name}: {message}")

    print(f"\nCompleted: {len(names) - len(failures)}/{len(names)} galaxies")
    if failures:
        print("Failures:")
        for name, reason in failures:
            print(f"  {name}: {reason}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
