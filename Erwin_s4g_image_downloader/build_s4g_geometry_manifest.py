"""Codex-created script for linking S4G images to geometry parameters.

The Erwin et al. paper describes using centre coordinates, disc PA/inclination,
and bar PA/size. This script joins the local Erwin project table to public S4G
catalogues and writes a manifest that links each downloaded FITS file to the
available geometry parameters.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits
from astropy.table import Table
from astroquery.vizier import Vizier


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from machine_paths import PC_RESEARCH_FOLDERS, erwin_folder  # noqa: E402

BARPROFILES_DATA_DIR = PROJECT_ROOT / "Erwin_barprofiles_paper_GB_working_copy" / "data"
DEFAULT_SCRAMBLED_MAP = BARPROFILES_DATA_DIR / "scrambled_map.txt"
DEFAULT_S4G_TABLE = BARPROFILES_DATA_DIR / "s4gbars_table.dat"
DEFAULT_PC = "Laptop"
DEFAULT_IMAGE_DIR = erwin_folder(DEFAULT_PC) / "s4g_images_36um"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "geometry_output"
DEFAULT_CACHE_DIR = Path(__file__).resolve().parent / "geometry_catalog_cache"

HERRERA_CATALOG = "J/A+A/582/A86"
HERRERA_BAR_TABLE = "J/A+A/582/A86/table2"
SALO_CATALOG = "J/ApJS/219/4"
SALO_GALAXY_TABLE = "J/ApJS/219/4/galaxies"
DIAZ_CATALOG = "J/A+A/587/A160"
DIAZ_FOURIER_TABLE = "J/A+A/587/A160/tablea3"

MISSING_NUMBER_CODES = {-99.0, -999.0, -999.999}
S4G_ZERO_IS_MISSING_COLUMNS = {
    "sma",
    "sma_kpc",
    "sma_ell_kpc",
    "sma_dp_kpc",
    "sma_dp_kpc2",
    "sma_ell_dp_kpc2",
    "ell_dp",
}
S4G_POSITIVE_SIZE_COLUMNS = {
    "sma",
    "sma_kpc",
    "sma_ell_kpc",
    "sma_dp_kpc",
    "sma_dp_kpc2",
    "sma_ell_dp_kpc2",
}

S4G_COLUMNS_TO_KEEP = [
    "logmstar",
    "dist",
    "sma",
    "sma_kpc",
    "sma_ell_kpc",
    "sma_dp_kpc",
    "sma_dp_kpc2",
    "sma_ell_dp_kpc2",
    "bar_strength",
    "A2",
    "A4",
    "ell_dp",
    "inclination",
    "R25",
    "R25_kpc",
    "Re",
    "Re_kpc",
    "h_kpc",
    "V_rot",
    "t_s4g",
    "t_leda",
]

OUTPUT_FIELDS = [
    "i_scrambled",
    "i_orig",
    "name",
    "image_exists",
    "image_path",
    "image_naxis1",
    "image_naxis2",
    "pixel_scale_arcsec_x",
    "pixel_scale_arcsec_y",
    "crpix1",
    "crpix2",
    "crval1_deg",
    "crval2_deg",
    "image_pa_axis2_deg",
    "center_x_pix",
    "center_y_pix",
    "disk_pa_deg",
    "salo_disk_ellipticity",
    "salo_disk_Rmin_pix",
    "salo_disk_Rmax_pix",
    "inclination_deg",
    "bar_pa_deg",
    "bar_sma_arcsec",
    "herrera_bar_ellipticity",
    "herrera_bar_sma_ell_arcsec",
    "bar_sma_kpc",
    "bar_sma_deproj_kpc",
    "bar_sma_deproj_legacy_kpc",
    "bar_sma_deproj_ellipticity_based_kpc",
    "bar_sma_deproj_source",
    "bar_ellipticity_deproj",
    "bar_strength",
    "bar_A2",
    "bar_A4",
    "logmstar",
    "dist_mpc",
    "R25_arcsec",
    "R25_kpc",
    "Re_arcsec",
    "Re_kpc",
    "disk_scale_length_h_kpc",
    "V_rot",
    "t_s4g",
    "t_leda",
    "catalog_sources",
    "geometry_notes",
]


def clean_value(value: str, column: str | None = None) -> float | str | None:
    try:
        number = float(value)
    except ValueError:
        return value
    if any(math.isclose(number, missing) for missing in MISSING_NUMBER_CODES):
        return None
    if column in S4G_ZERO_IS_MISSING_COLUMNS and math.isclose(number, 0.0):
        return None
    if column in S4G_POSITIVE_SIZE_COLUMNS and number <= 0:
        return None
    return number


def read_scrambled_map(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            rows.append(
                {
                    "i_scrambled": int(parts[0]),
                    "i_orig": int(parts[1]),
                    "name": parts[2],
                }
            )
    return rows


def read_s4g_table(path: Path) -> dict[str, dict[str, Any]]:
    header: list[str] | None = None
    rows: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                candidate = line[1:].strip().split()
                if candidate and candidate[0] == "name":
                    header = candidate
                continue
            if header is None:
                raise ValueError(f"No header found before data rows in {path}")
            values = line.split()
            row = {
                column: clean_value(values[index], column)
                for index, column in enumerate(header)
            }
            rows[str(row["name"])] = row
    return rows


def table_value(value: Any) -> Any:
    if np.ma.is_masked(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return value


def read_cached_or_fetch_table(
    catalog: str,
    table_key: str,
    cache_dir: Path,
    use_cache: bool,
) -> Table:
    cache_dir.mkdir(exist_ok=True)
    cache_file = cache_dir / f"{table_key.replace('/', '_')}.ecsv"
    if use_cache and cache_file.exists():
        return Table.read(cache_file, format="ascii.ecsv")

    vizier = Vizier(columns=["**"], row_limit=-1)
    tables = vizier.get_catalogs(catalog)
    table = tables[table_key]
    table.write(cache_file, format="ascii.ecsv", overwrite=True)
    return table


def keyed_table(table: Table, name_column: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in table:
        name = str(table_value(row[name_column])).strip()
        rows[name] = {column: table_value(row[column]) for column in table.colnames}
    return rows


def keyed_herrera_bars(table: Table) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in table:
        if str(table_value(row["Type"])).strip().lower() != "bar":
            continue
        name = str(table_value(row["Name"])).strip()
        rows[name] = {column: table_value(row[column]) for column in table.colnames}
    return rows


def fetch_catalog_geometry(
    cache_dir: Path,
    use_cache: bool,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    herrera = read_cached_or_fetch_table(
        HERRERA_CATALOG, HERRERA_BAR_TABLE, cache_dir, use_cache
    )
    salo = read_cached_or_fetch_table(
        SALO_CATALOG, SALO_GALAXY_TABLE, cache_dir, use_cache
    )
    diaz = read_cached_or_fetch_table(
        DIAZ_CATALOG, DIAZ_FOURIER_TABLE, cache_dir, use_cache
    )
    return keyed_herrera_bars(herrera), keyed_table(salo, "Name"), keyed_table(diaz, "Galaxy")


def fits_metadata(image_path: Path) -> dict[str, Any]:
    if not image_path.exists():
        return {
            "image_exists": False,
            "image_path": str(image_path),
        }

    header = fits.getheader(image_path)
    return {
        "image_exists": True,
        "image_path": str(image_path),
        "image_naxis1": header.get("NAXIS1"),
        "image_naxis2": header.get("NAXIS2"),
        "pixel_scale_arcsec_x": header.get("PXSCAL1"),
        "pixel_scale_arcsec_y": header.get("PXSCAL2"),
        "crpix1": header.get("CRPIX1"),
        "crpix2": header.get("CRPIX2"),
        "crval1_deg": header.get("CRVAL1"),
        "crval2_deg": header.get("CRVAL2"),
        "image_pa_axis2_deg": header.get("PA"),
    }


def build_manifest(
    scrambled_map: Path,
    s4g_table: Path,
    image_dir: Path,
    herrera_bars: dict[str, dict[str, Any]] | None = None,
    salo_galaxies: dict[str, dict[str, Any]] | None = None,
    diaz_fourier: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    scrambled_rows = read_scrambled_map(scrambled_map)
    s4g_rows = read_s4g_table(s4g_table)
    herrera_bars = herrera_bars or {}
    salo_galaxies = salo_galaxies or {}
    diaz_fourier = diaz_fourier or {}

    manifest: list[dict[str, Any]] = []
    for row in scrambled_rows:
        name = row["name"]
        image_path = image_dir / f"{name}.phot.1.fits"
        s4g = s4g_rows.get(name, {})
        herrera = herrera_bars.get(name, {})
        salo = salo_galaxies.get(name, {})
        diaz = diaz_fourier.get(name, {})
        notes = []
        if not s4g:
            notes.append("No matching row in s4gbars_table.dat")
        if not herrera:
            notes.append("No matching Herrera-Endoqui bar row")
        if not salo:
            notes.append("No matching Salo galaxy row")
        if not diaz:
            notes.append("No matching Diaz-Garcia Fourier row")
        legacy_deproj = s4g.get("sma_dp_kpc")
        if legacy_deproj is None:
            notes.append("Legacy local sma_dp_kpc value is missing or non-positive")
        notes.append("Erwin et al. manual revisions are not represented unless present in local project data")

        output_row: dict[str, Any] = {field: None for field in OUTPUT_FIELDS}
        output_row.update(row)
        output_row.update(fits_metadata(image_path))
        output_row.update(
            {
                "center_x_pix": salo.get("xc"),
                "center_y_pix": salo.get("yc"),
                "disk_pa_deg": salo.get("PA"),
                "salo_disk_ellipticity": salo.get("Ell"),
                "salo_disk_Rmin_pix": salo.get("Rmin"),
                "salo_disk_Rmax_pix": salo.get("Rmax"),
                "inclination_deg": s4g.get("inclination"),
                "bar_pa_deg": herrera.get("PA"),
                "bar_sma_arcsec": herrera.get("sma") or s4g.get("sma"),
                "herrera_bar_ellipticity": herrera.get("Ell"),
                "herrera_bar_sma_ell_arcsec": herrera.get("smaEll"),
                "bar_sma_kpc": s4g.get("sma_kpc"),
                "bar_sma_deproj_kpc": s4g.get("sma_dp_kpc2"),
                "bar_sma_deproj_legacy_kpc": legacy_deproj,
                "bar_sma_deproj_ellipticity_based_kpc": s4g.get("sma_ell_dp_kpc2"),
                "bar_sma_deproj_source": "s4gbars_table.dat sma_dp_kpc2",
                "bar_ellipticity_deproj": diaz.get("Ell") or s4g.get("ell_dp"),
                "bar_strength": s4g.get("bar_strength"),
                "bar_A2": diaz.get("A2") or s4g.get("A2"),
                "bar_A4": diaz.get("A4") or s4g.get("A4"),
                "logmstar": s4g.get("logmstar"),
                "dist_mpc": s4g.get("dist"),
                "R25_arcsec": s4g.get("R25"),
                "R25_kpc": s4g.get("R25_kpc"),
                "Re_arcsec": s4g.get("Re"),
                "Re_kpc": s4g.get("Re_kpc"),
                "disk_scale_length_h_kpc": s4g.get("h_kpc"),
                "V_rot": s4g.get("V_rot"),
                "t_s4g": s4g.get("t_s4g"),
                "t_leda": s4g.get("t_leda"),
                "catalog_sources": "Herrera-Endoqui+2015 table2; Salo+2015 galaxies; Diaz-Garcia+2016 tablea3; local s4gbars_table.dat",
                "geometry_notes": "; ".join(notes),
            }
        )
        manifest.append(output_row)

    return manifest


def write_manifest(rows: list[dict[str, Any]], output_csv: Path) -> None:
    output_csv.parent.mkdir(exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Link downloaded S4G FITS files to available geometry parameters."
    )
    parser.add_argument(
        "--pc",
        choices=sorted(PC_RESEARCH_FOLDERS),
        default=DEFAULT_PC,
        help="Select which Dropbox research-folder location to use for default paths.",
    )
    parser.add_argument("--scrambled-map", type=Path, default=DEFAULT_SCRAMBLED_MAP)
    parser.add_argument("--s4g-table", type=Path, default=DEFAULT_S4G_TABLE)
    parser.add_argument("--image-dir", type=Path, default=None)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument(
        "--no-vizier",
        action="store_true",
        help="Do not fetch/merge VizieR geometry catalogues; use only local data.",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Refetch VizieR catalogues even if cached copies exist.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "s4g_image_geometry_manifest.csv",
    )
    args = parser.parse_args()
    if args.image_dir is None:
        args.image_dir = erwin_folder(args.pc) / "s4g_images_36um"
    return args


def main() -> int:
    args = parse_args()
    herrera_bars = salo_galaxies = diaz_fourier = None
    if not args.no_vizier:
        herrera_bars, salo_galaxies, diaz_fourier = fetch_catalog_geometry(
            args.cache_dir.resolve(),
            use_cache=not args.refresh_cache,
        )
    rows = build_manifest(
        args.scrambled_map.resolve(),
        args.s4g_table.resolve(),
        args.image_dir.resolve(),
        herrera_bars=herrera_bars,
        salo_galaxies=salo_galaxies,
        diaz_fourier=diaz_fourier,
    )
    write_manifest(rows, args.output_csv.resolve())
    image_count = sum(1 for row in rows if row["image_exists"])
    print(f"Wrote {len(rows)} rows to {args.output_csv.resolve()}")
    print(f"Linked {image_count} downloaded FITS images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
