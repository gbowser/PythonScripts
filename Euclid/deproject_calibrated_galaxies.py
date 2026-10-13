"""Deproject native galaxy cutouts using explicit, recorded geometry."""
import csv
import math
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from extract_euclid_bars import display, local_pixel_matrix


def transform_cutout(path, geometry, overwrite=False):
    disk, inclination, bar = (float(geometry[key]) for key in ("disk_pa_deg", "inclination_deg", "bar_pa_deg"))
    if not all(math.isfinite(v) for v in (disk, inclination, bar)) or not 0 <= inclination < 85:
        raise ValueError("Geometry must be finite, with inclination in [0,85) degrees")
    radius = float(geometry["radius_arcsec"])
    if not math.isfinite(radius) or not 0 < radius <= 600:
        raise ValueError("Radius must be >0 and <=600 arcsec")
    output = path.with_name(path.stem.removesuffix("_cutout") + "_bar_aligned.fits")
    if output.exists() and not overwrite:
        raise FileExistsError(output)
    with fits.open(path) as hdul:
        data = hdul[0].data.astype(float)
        original = hdul[0].header
        wcs = WCS(original).celestial
        xc, yc = float(original["CENX"]) - 1, float(original["CENY"]) - 1
        sky = wcs.pixel_to_world(xc, yc)
        matrix = local_pixel_matrix(wcs, sky, xc, yc)
        scale = float(np.linalg.norm(matrix[:, 1]))
        transform = display.image_transform(disk, inclination, bar) @ (matrix / scale)
        sign = 1 if transform[1, 1] >= 0 else -1
        transform *= sign
        inverse = np.linalg.inv(transform)
        r = math.ceil(radius / scale)
        offsets = np.arange(-r, r + 1, dtype=float)
        shape = (len(offsets), len(offsets))
        science = np.full(shape, np.nan, dtype=np.float32)
        coverage = np.zeros(shape, dtype=np.float32)
        rms_out = np.full(shape, np.nan, dtype=np.float32) if "RMS" in hdul else None
        flag_out = np.zeros(shape, dtype=hdul["FLG"].data.dtype) if "FLG" in hdul else None
        for start in range(0, len(offsets), 128):
            xx, yy = np.meshgrid(offsets, offsets[start:start + 128])
            mapped = inverse @ np.vstack((xx.ravel(), yy.ravel()))
            x, y = mapped[0].reshape(xx.shape) + xc, mapped[1].reshape(xx.shape) + yc
            x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
            dx, dy = x - x0, y - y0
            total = np.zeros(xx.shape)
            weights = np.zeros(xx.shape)
            variance = np.zeros(xx.shape)
            flags = np.zeros(xx.shape, dtype=flag_out.dtype) if flag_out is not None else None
            for ox, oy, weight in ((0,0,(1-dx)*(1-dy)),(1,0,dx*(1-dy)),(0,1,(1-dx)*dy),(1,1,dx*dy)):
                ix, iy = x0 + ox, y0 + oy
                inside = (ix >= 0) & (iy >= 0) & (ix < data.shape[1]) & (iy < data.shape[0])
                ix, iy = np.clip(ix,0,data.shape[1]-1), np.clip(iy,0,data.shape[0]-1)
                valid = inside & np.isfinite(data[iy,ix])
                w = np.where(valid,weight,0)
                total += w * np.where(valid,data[iy,ix],0)
                weights += w
                if rms_out is not None:
                    variance += w**2 * np.where(valid,hdul["RMS"].data[iy,ix]**2,0)
                if flags is not None:
                    flags |= np.where(w>0,hdul["FLG"].data[iy,ix],0).astype(flags.dtype)
            sl = slice(start,start+xx.shape[0])
            usable = weights > 0.999999
            science[sl] = np.divide(total,weights,out=np.full(xx.shape,np.nan),where=usable)
            coverage[sl] = weights
            if rms_out is not None:
                rms_out[sl] = np.divide(np.sqrt(variance),weights,out=np.full(xx.shape,np.nan),where=usable)
            if flags is not None:
                flag_out[sl] = flags
    header = fits.Header()
    for axis in (1,2):
        header[f"CTYPE{axis}"] = "LINEAR"
        header[f"CUNIT{axis}"] = "arcsec"
        header[f"CRPIX{axis}"] = r+1
        header[f"CRVAL{axis}"] = 0.
        header[f"CDELT{axis}"] = scale
    for key in ("OBJECT","GALID","GALRA","GALDEC","SRCFILE","SRCEXT","BUNIT"):
        if key in original:
            header[key] = original[key]
    header["DISKPA"],header["INCL"],header["BARPA"] = disk,inclination,bar
    header["VIEWRAD"] = radius
    header["GEOMSRC"] = geometry.get("geometry_source", "user supplied")
    header["ORIENT"] = sign
    header.add_history("Disc minor axis expanded by 1/cos(i); bar aligned to x.")
    header.add_history("Bilinear SCI; RMS variance assumes independent input pixels.")
    header.add_history("FLG is bitwise OR of contributors; COVERAGE records input support.")
    products = [fits.PrimaryHDU(science,header)]
    if rms_out is not None:
        products.append(fits.ImageHDU(rms_out,header.copy(),name="RMS"))
    if flag_out is not None:
        flag_header=header.copy()
        if "BUNIT" in flag_header: del flag_header["BUNIT"]
        products.append(fits.ImageHDU(flag_out,flag_header,name="FLG"))
    support_header=header.copy()
    if "BUNIT" in support_header: del support_header["BUNIT"]
    products.append(fits.ImageHDU(coverage,support_header,name="COVERAGE"))
    fits.HDUList(products).writeto(output,overwrite=overwrite,checksum=True)
    return output


def process_existing(folder, geometry_csv, overwrite=False):
    with geometry_csv.open(newline="",encoding="utf-8-sig") as handle:
        rows=list(csv.DictReader(handle))
    geometries={row["object_id"]:row for row in rows}
    paths=sorted(folder.glob("*_cutout.fits"))
    if not paths: raise ValueError("No native *_cutout.fits files found")
    for path in paths:
        object_id=str(fits.getheader(path)["GALID"])
        if object_id not in geometries: raise ValueError(f"Missing geometry for {object_id}")
        row=geometries[object_id]
        if any(not row.get(key,"" ).strip() for key in ("disk_pa_deg","inclination_deg","bar_pa_deg","radius_arcsec")):
            raise ValueError(f"Disc PA, inclination, bar PA and radius required for {object_id}")
    for path in paths:
        row=geometries[str(fits.getheader(path)["GALID"])]
        print(f"Saved {transform_cutout(path,row,overwrite)}",flush=True)
