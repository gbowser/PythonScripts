"""Query ESA from a PC, download a server-made cutout, and save two previews.

Run from the PythonScripts repository root in VS Code's terminal:
.venv/Scripts/python.exe Euclid/DR1/galaxy_cutouts/Galaxy_image_remote.py
Install packages into the existing uv environment first:
uv pip install -r Euclid/DR1/galaxy_cutouts/requirements.txt
"""

# Path builds Windows paths. PurePosixPath builds paths on ESA's Linux server.
from pathlib import Path, PurePosixPath
import shutil  # Copy a downloaded FITS out of a ZIP without loading it all into RAM.
import zipfile  # ESA sometimes wraps its cutout response in a ZIP archive.

import numpy as np  # Work with the image's two-dimensional array of numbers.
import requests  # Send the cutout request over HTTPS.
from astroquery.esa.euclid import Euclid  # Query ESA's catalogue of image products.
from astropy.coordinates import SkyCoord  # Resolve a name into sky coordinates.
from astropy import units as u  # Keep angular quantities explicitly labelled.
from astropy.io import fits  # Read and validate astronomical FITS files.
from astropy.wcs import WCS  # Convert sky coordinates to image pixel coordinates.
from astropy.visualization import simple_norm  # Make the original asinh preview.

import matplotlib
matplotlib.use("Agg")  # Save PNGs without requiring a graphical Python backend.
import matplotlib.pyplot as plt


# -------------------- SETTINGS YOU CAN CHANGE --------------------
NAME = "NGC 1365"
RADIUS = 6 * u.arcmin  # Half-width: the requested square is about 12 arcmin wide.
RESEARCH_FOLDER = Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research")
OUTPUT_FOLDER = RESEARCH_FOLDER / "Euclid" / "DR1" / "galaxy_cutouts"
OPEN_PREVIEWS = True  # Open the two PNGs in your PC's default image viewer.

# Limit the network response to 500 MiB; do not accidentally download a mosaic.
MAX_DOWNLOAD_BYTES = 500 * 1024 * 1024
CUTOUT_SERVICE = "https://eas.esac.esa.int/sas-cutout/cutout"


def midtones_transfer(m, x):
    """Map brightness x (0 to 1) through a midtones adjustment m."""
    epsilon = np.finfo(float).eps  # Tiny positive number for safe arithmetic.
    m = np.clip(m, epsilon, 1 - epsilon)  # Avoid problematic exact endpoints.
    x = np.clip(x, 0, 1)  # Values below black/above white are clipped.
    result = ((m - 1) * x) / ((2 * m - 1) * x - m)
    return np.clip(result, 0, 1)


def autostretch(data, shadows=-2.8, target=0.25):
    """Create a PixInsight-style grayscale AutoSTF preview, without altering data."""
    valid = np.isfinite(data)  # Exclude missing (NaN) and infinite pixels.
    pixels = data[valid].astype(float)  # Floating-point copy of usable values.
    if pixels.size == 0:
        raise ValueError("The image contains no usable pixels.")

    median = np.median(pixels)  # Less sensitive to bright stars than the mean.
    minimum = pixels.min()
    maximum = pixels.max()
    span = maximum - minimum
    epsilon = np.finfo(float).eps
    if span <= epsilon:
        return np.zeros(data.shape)  # A constant image contains no contrast.

    # Median absolute deviation estimates the spread around the background.
    mad = np.median(np.abs(pixels - median))
    sigma = 1.4826 * mad  # Gaussian-equivalent estimate of the variation.
    centre = (median - minimum) / span  # Put the median on a 0-to-1 scale.
    noise = sigma / span
    black = np.clip(centre + shadows * noise, 0, 1)
    background = np.clip((centre - black) / max(1 - black, epsilon), 0, 1)
    midtones = midtones_transfer(target, background)
    low = minimum + black * span  # Black point in the original pixel units.

    # All display changes happen on this separate copy of the cutout.
    display = np.array(data, dtype=float, copy=True)
    display[~valid] = low  # ~ reverses the True/False mask: select bad pixels.
    display = (display - low) / max(maximum - low, epsilon)
    display = midtones_transfer(midtones, display)
    display[~valid] = 0  # Missing pixels appear black.
    return display


def download_cutout(parameters, destination):
    """Download only the server cutout; handle either plain FITS or ZIP."""
    # Temporary downloads live beside the final file in the research archive.
    temporary = destination.with_suffix(".download")
    unpacked = destination.with_suffix(".unpacked")
    total = 0
    try:
        # params builds the URL safely; stream avoids a large in-memory response.
        # Timeout values are seconds: connection timeout, then read timeout.
        with requests.get(CUTOUT_SERVICE, params=parameters, stream=True,
                          timeout=(30, 300)) as response:
            response.raise_for_status()  # Stop on HTTP errors such as 404 or 500.
            with temporary.open("wb") as output:  # wb means write binary bytes.
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        raise ValueError("Cutout exceeded the 500 MiB download limit.")
                    output.write(chunk)

        if zipfile.is_zipfile(temporary):
            # Read the single FITS member directly; do not extract arbitrary paths.
            with zipfile.ZipFile(temporary) as archive:
                members = [item for item in archive.infolist()
                           if item.filename.lower().endswith((".fits", ".fit"))]
                if len(members) != 1:
                    raise ValueError("Expected exactly one FITS image in the ZIP.")
                if members[0].file_size > MAX_DOWNLOAD_BYTES:
                    raise ValueError("Uncompressed cutout exceeds 500 MiB.")
                with archive.open(members[0]) as source, unpacked.open("wb") as output:
                    shutil.copyfileobj(source, output)
        else:
            temporary.replace(unpacked)  # Plain FITS needs no ZIP extraction.

        # Validate before replacing an existing science file with the download.
        with fits.open(unpacked) as hdul:
            # ESA may return a nonstandard EXTNAME card. Report header warnings
            # without rejecting usable science pixels or rewriting the FITS.
            hdul.verify("warn")
            if not any(hdu.header.get("NAXIS") == 2 for hdu in hdul):
                raise ValueError("The response contains no two-dimensional image.")
        unpacked.replace(destination)
    finally:
        # Clean up only these two temporary files, including after errors.
        temporary.unlink(missing_ok=True)
        unpacked.unlink(missing_ok=True)
    print(f"Downloaded {total / 1024**2:.1f} MiB from ESA.")


def main():
    # Do not silently create a substitute archive if Dropbox is unavailable.
    if not RESEARCH_FOLDER.is_dir():
        raise SystemExit(f"Dropbox research folder unavailable: {RESEARCH_FOLDER}")
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    position = SkyCoord.from_name(NAME)  # Online name lookup, not hard-coded RA.
    print("Galaxy:", NAME)
    print("RA:", position.ra.deg, "Dec:", position.dec.deg)

    # Query metadata only. file_path is ESA's server path, not a PC file path.
    # An f-string inserts Python values at each {...} inside the ADQL text.
    query = f"""
    SELECT TOP 1 file_name, file_path, tile_index,
           DISTANCE(POINT('ICRS', {position.ra.deg}, {position.dec.deg}),
                    POINT('ICRS', ra, dec)) AS centre_distance
    FROM dr1.mosaic_product
    WHERE data_set_release = 'DR1_R2'
    AND product_type = 'DpdMerBksMosaic'
    AND instrument_name = 'VIS'
    AND category = 'SCIENCE'
    AND CONTAINS(POINT('ICRS', {position.ra.deg}, {position.dec.deg}), fov) = 1
    ORDER BY centre_distance
    """
    print("Searching ESA for a DR1 MER VIS mosaic...")
    job = Euclid.launch_job(query)
    if job is None:
        raise SystemExit("The archive query failed.")
    images = job.get_results()
    if len(images) == 0:
        raise SystemExit(f"No matching DR1 MER VIS image found for {NAME}.")

    image = images[0]  # Python counts from zero: select the first returned row.
    server_file = str(PurePosixPath(str(image["file_path"])) / str(image["file_name"]))
    prefix = NAME.replace(" ", "_")
    fits_output = OUTPUT_FOLDER / f"{prefix}_cutout.fits"
    basic_output = OUTPUT_FOLDER / f"{prefix}_cutout.png"
    auto_output = OUTPUT_FOLDER / f"{prefix}_autostretch.png"

    # These parameters tell ESA to make the cutout BEFORE sending the FITS.
    # POS expects RA, Dec and radius in DEGREES, not arcminutes or pixels.
    parameters = {
        "filepath": server_file,
        "collection": "VIS",
        "tileindex": str(image["tile_index"]),
        "POS": f"CIRCLE,{position.ra.deg},{position.dec.deg},{RADIUS.to_value(u.deg)}",
    }
    print("Requesting a server-side cutout from tile", image["tile_index"])
    download_cutout(parameters, fits_output)

    # Read the small returned image, not the original mosaic.
    with fits.open(fits_output, memmap=False) as hdul:
        image_hdu = next(hdu for hdu in hdul if hdu.header.get("NAXIS") == 2)
        data = image_hdu.data.copy()
        wcs = WCS(image_hdu.header).celestial

    # Confirm that the resolved galaxy centre falls inside the returned image.
    x, y = wcs.world_to_pixel(position)
    height, width = data.shape
    if not (-0.5 <= x < width - 0.5 and -0.5 <= y < height - 0.5):
        raise ValueError("The galaxy centre is outside the returned cutout.")
    print(f"Returned image: {width} x {height} pixels.")
    print(f"Finite pixels: {100 * np.isfinite(data).mean():.2f}%")
    # The server cuts a single tile; edges or missing pixels need visual review.

    # BASIC PNG: the same asinh preview used in the Datalabs script.
    normalisation = simple_norm(data, stretch="asinh", percent=99.5)
    plt.figure(figsize=(8, 8))
    plt.imshow(data, origin="lower", cmap="gray", norm=normalisation)
    plt.title(f"{NAME} — MER VIS — basic preview")
    plt.axis("off")
    plt.savefig(basic_output, dpi=150, bbox_inches="tight")
    plt.close()

    # ADDITIONAL PNG: AutoSTF-style display; original FITS pixels stay unchanged.
    stretched = autostretch(data, shadows=-2.8, target=0.25)
    plt.figure(figsize=(8, 8))
    plt.imshow(stretched, origin="lower", cmap="gray", vmin=0, vmax=1)
    plt.title(f"{NAME} — MER VIS — PixInsight-style AutoSTF")
    plt.axis("off")
    plt.savefig(auto_output, dpi=150, bbox_inches="tight")
    plt.close()

    print("Saved:", fits_output)
    print("Saved:", basic_output)
    print("Saved:", auto_output)

    # On Windows, ask the default image viewer to open both saved PNGs.
    if OPEN_PREVIEWS:
        import os
        if os.name == "nt":
            os.startfile(basic_output)
            os.startfile(auto_output)


# Execute main when running this file, but not when importing its functions.
if __name__ == "__main__":
    main()
