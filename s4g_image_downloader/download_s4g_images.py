"""User-provided/ChatGPT-origin downloader, organized for this repo by Codex.

Download S4G 3.6 micron FITS images for galaxies in scrambled_map.txt.

By default this reads the scrambled-map file from the converted bar-profiles
project and writes FITS files into ``s4g_images_36um`` beside this script.
"""

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

SETTINGS = {
    "galaxy_list": DEFAULT_GALAXY_LIST,
    "outdir": DEFAULT_OUTDIR,
    "base_url": DEFAULT_BASE_URL,
    "limit": None,      # Use a number like 5 for testing, or None for all galaxies.
    "timeout": 60,
    "dry_run": False,   # Use True to print planned downloads without contacting the server.
}


def read_galaxy_names(galaxy_list_file):
    galaxies = []
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
    name,
    base_url,
    outdir,
    timeout,
    dry_run,
):
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


def main():
    args = SETTINGS
    galaxy_list_file = args["galaxy_list"].resolve()
    outdir = args["outdir"].resolve()
    outdir.mkdir(exist_ok=True)

    galaxies = read_galaxy_names(galaxy_list_file)
    if args["limit"] is not None:
        galaxies = galaxies[: args["limit"]]

    print(f"Galaxy list: {galaxy_list_file}")
    print(f"Output folder: {outdir}")
    print(f"Found {len(galaxies)} galaxies")

    for name in galaxies:
        print(
            download_image(
                name,
                args["base_url"],
                outdir,
                args["timeout"],
                args["dry_run"],
            )
        )

    return 0


if __name__ == "__main__":
    main()
