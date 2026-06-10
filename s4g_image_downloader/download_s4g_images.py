"""Download S4G 3.6 micron FITS images for galaxies in scrambled_map.txt.

By default this reads the scrambled-map file from the converted bar-profiles
project and writes FITS files into ``s4g_images_36um`` beside this script.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import requests


DEFAULT_GALAXY_LIST = (
    Path(__file__).resolve().parents[1]
    / "barprofiles_paper_GB_working_copy"
    / "data"
    / "scrambled_map.txt"
)
DEFAULT_BASE_URL = "https://irsa.ipac.caltech.edu/data/SPITZER/S4G/galaxies"
DEFAULT_OUTDIR = Path(__file__).resolve().parent / "s4g_images_36um"


def read_galaxy_names(galaxy_list_file: Path) -> list[str]:
    galaxies: list[str] = []
    with galaxy_list_file.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                galaxies.append(parts[2])
    return galaxies


def download_image(
    name: str,
    base_url: str,
    outdir: Path,
    timeout: int,
    dry_run: bool,
) -> str:
    url = f"{base_url}/{name}/P1/{name}.phot.1.fits"
    outfile = outdir / f"{name}.phot.1.fits"

    if outfile.exists():
        return f"Already have {outfile.name}"

    if dry_run:
        return f"Would download {url}"

    response = requests.get(url, timeout=timeout)
    if response.status_code == 200 and len(response.content) > 1000:
        outfile.write_bytes(response.content)
        return f"Saved {outfile}"

    return f"NOT FOUND: {url} (status={response.status_code}, bytes={len(response.content)})"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download S4G 3.6 micron FITS images from IRSA."
    )
    parser.add_argument(
        "--galaxy-list",
        type=Path,
        default=DEFAULT_GALAXY_LIST,
        help=f"Path to scrambled_map.txt. Default: {DEFAULT_GALAXY_LIST}",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_OUTDIR,
        help=f"Output folder for downloaded FITS files. Default: {DEFAULT_OUTDIR}",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"S4G base URL. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N galaxies. Useful for testing.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds. Default: 60.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned downloads without contacting the server.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    galaxy_list_file = args.galaxy_list.resolve()
    outdir = args.outdir.resolve()
    outdir.mkdir(exist_ok=True)

    galaxies = read_galaxy_names(galaxy_list_file)
    if args.limit is not None:
        galaxies = galaxies[: args.limit]

    print(f"Galaxy list: {galaxy_list_file}")
    print(f"Output folder: {outdir}")
    print(f"Found {len(galaxies)} galaxies")

    for name in galaxies:
        print(download_image(name, args.base_url, outdir, args.timeout, args.dry_run))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
