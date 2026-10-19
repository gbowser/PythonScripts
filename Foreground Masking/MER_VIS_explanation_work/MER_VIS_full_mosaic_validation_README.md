# Full mosaic validation of the page 7 galaxy

Checked 19 October 2026. Galaxy OBJECT_ID: -619395065457031576. Tile: 102023983.

## Downloaded files

The full native VIS background-subtracted science mosaic is saved here as:
`EUC_MER_BGSUB-MOSAIC-VIS_TILE102023983-8D3C9A_20241018T181958.121344Z_00.00.fits`

It has 19200 by 19200 pixels and occupies 1474565760 bytes (1.373 GiB).
The original main catalogue for this tile is also saved here:
`EUC_MER_FINAL-CAT_TILE102023983-E45A86_20241018T230719.293669Z_00.00.fits`
It occupies 37206720 bytes. The target is VIS-detected (VIS_DET = 1).

## Confirmed results

1. Recreating the cutout from the downloaded full mosaic using its WCS and the original catalogue centre reproduces EVERY original cutout pixel exactly, including nonfinite pixels. Maximum absolute difference is zero. There is no cutout rotation, reflection or interpolation.
2. The recreated cutout and existing cutout WCS give exactly matching sky coordinates at four separated test positions.
3. The original catalogue FITS POSITION_ANGLE is 49.91947937011719 degrees, identical to the TAP value. The difference does not originate in a TAP transcription of this value.
4. Treating that angle as counterclockwise from native FITS pixel x and using two positions along that direction gives sky PA 140.12367882 degrees.
5. The existing vector conversion gives 140.12367890 degrees and the stored euclid_detection_pa_sky_deg is 140.12367889 degrees. The independent calculation agrees to better than a millionth of a degree. This validates the arithmetic for the assumed input frame, not the input-frame assumption itself.
6. The fitted outer-disc PA is 43.47150642 degrees; the fitted pixel-axis PA is 133.26725445 degrees modulo 180. Its shortest axis-angle separation from the catalogue direction interpreted through the VIS mosaic WCS is 83.35 degrees.

## What the overlay shows

Open `MER_VIS_PA_overlay_comparison.png`. Both panels use the same native science pixels from the full mosaic; neither is rotated. Cyan ellipses are fitted disc isophotes. Orange uses the catalogue axis ratio and three times its semi-major axis to make the direction easier to compare; this scale is illustrative, not a measurement of the disc edge.

Left: using POSITION_ANGLE directly as CCW from native pixel x places the orange long axis roughly across the galaxy's short direction.
Right: adding 90 degrees makes the orange ellipse approximately follow the galaxy. This is a diagnostic hypothesis ONLY, not an adopted correction.

A sign reversal of the input angle gives a sky PA of about 40.28 degrees, which also agrees reasonably well with the fitted disc. For a galaxy near a diagonal, sign reversal and a 90 degree change can both look plausible. This galaxy alone cannot distinguish them. The second fitted library galaxy on this tile gives the same broad ambiguity. The exact alternatives are tabulated in `MER_VIS_same_tile_hypothesis_checks.csv`; the two objects must not be treated as a statistically decisive sample.

## What remains unresolved

ESA explicitly states that MERDetectionMosaic was not distributed in Q1:
https://euclid.esac.esa.int/dr/q1/dpdd/merdpd/merintro.html

The downloaded file is the exact SCIENCE mosaic used for our cutout, not the unavailable detection mosaic. Consequently this test rules out a cutout orientation problem and a WCS arithmetic problem, but cannot verify the original detection pixel frame. An undocumented sign/frame difference, an angle convention discrepancy, or a catalogue/pipeline issue remain possible. No cause has been established and no blanket 90 degree or sign correction has been applied. Existing geometry manifests and science cutouts remain unchanged.

The next authoritative check is to ask the Euclid archive or MER team to confirm which image coordinate system and handedness Q1 POSITION_ANGLE refers to, quoting this OBJECT_ID, tile, exact source filename, original angle, WCS and overlay. If possible, request the detection image header or the detection product itself. No message has been sent on your behalf.

## Download integrity note

The downloaded file has a valid FITS structure and the expected byte count. Its MD5 is 5e4c6a52e2b0b2bfd579eb19ef8bb513; TAP mosaic metadata lists bb20bec6eea0750a1c97cb002d33147e. These do not match. The file contains no embedded FITS CHECKSUM or DATASUM. The cause of the metadata mismatch has not been established; archive checksum validation must not be claimed.

Independent HTTP range requests reproduce its first and last 5760-byte blocks exactly. More importantly for this experiment, its entire galaxy cutout matches the existing independently obtained Datalabs cutout exactly. Those checks support the local galaxy comparison but do not replace a full-file authoritative checksum match. Details are in `MER_VIS_download_range_checks.json` and `MER_VIS_PA_validation_results.json`.

## Locating the galaxy in the full image

The catalogue centre maps to zero-based pixel x = 16786.774303, y = 2272.458362. In FITS one-based coordinates that is x = 16787.774303, y = 2273.458362. Image viewers may flip the displayed vertical axis. Use WCS coordinates RA = 61.939506578634386 degrees, Dec = -45.70315766741444 degrees when available. `MER_VIS_full_mosaic_locator.png` marks the target on a downsampled full-tile view.

## Reproducibility

Validation code is saved in the project's `Euclid/validation_MER_VIS` folder. The source FITS images and this note are in the local `MER_VIS_PA_validation` data folder. Queries used the public ESA TAP service and filename download service. All angles are degrees; sky axes are east of north modulo 180 degrees. This experiment does not validate a single global physical disc PA for every radius.
