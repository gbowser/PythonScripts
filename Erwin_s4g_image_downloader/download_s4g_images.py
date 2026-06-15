"""User-provided/ChatGPT-origin downloader, organized for this repo by Codex.

Download S4G 3.6 micron FITS images for galaxies in scrambled_map.txt.

By default this reads the scrambled-map file from the converted bar-profiles
project and writes FITS files into the S4G image folder under the Erwin Dropbox
research directory.
"""

import argparse
from pathlib import Path

import requests


DEFAULT_GALAXY_LIST = (
    Path(__file__).resolve().parents[1]
    / "Erwin_barprofiles_paper_GB_working_copy"
    / "data"
    / "scrambled_map.txt"
)
DEFAULT_BASE_URL = "https://irsa.ipac.caltech.edu/data/SPITZER/S4G/galaxies"
DEFAULT_ERWIN_DIR = Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Erwin")
DEFAULT_OUTDIR = DEFAULT_ERWIN_DIR / "s4g_images_36um"

SETTINGS = {
    "galaxy_list": DEFAULT_GALAXY_LIST,
    "outdir": DEFAULT_OUTDIR,
    "base_url": DEFAULT_BASE_URL,
    "limit": None,      # Use a number like 5 for testing, or None for all galaxies.
    "timeout": 60,
    "dry_run": False,   # Use True to print planned downloads without contacting the server.
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download S4G 3.6 micron FITS images from IRSA."
    )
    parser.add_argument(
        "--galaxy-list",
        type=Path,
        default=SETTINGS["galaxy_list"],
        help="Path to the scrambled_map.txt galaxy list.",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=SETTINGS["outdir"],
        help="Directory where FITS files will be written.",
    )
    parser.add_argument(
        "--base-url",
        default=SETTINGS["base_url"],
        help="Base URL for S4G galaxy data.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=SETTINGS["limit"],
        help="Download only the first N galaxies.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=SETTINGS["timeout"],
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=SETTINGS["dry_run"],
        help="Print planned downloads without contacting the server.",
    )
    return parser.parse_args()


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
    timeout: float,
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


def main() -> int:
    args = parse_args()
    galaxy_list_file = args.galaxy_list.resolve()
    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    galaxies = read_galaxy_names(galaxy_list_file)
    if args.limit is not None:
        galaxies = galaxies[: args.limit]

    print(f"Galaxy list: {galaxy_list_file}")
    print(f"Output folder: {outdir}")
    print(f"Found {len(galaxies)} galaxies")

    for name in galaxies:
        print(
            download_image(
                name,
                args.base_url,
                outdir,
                args.timeout,
                args.dry_run,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
