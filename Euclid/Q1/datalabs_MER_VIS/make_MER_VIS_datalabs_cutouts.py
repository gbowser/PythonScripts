"""Create native MER VIS science cutouts from Datalabs-mounted Q1 mosaics."""
import csv,math,shutil
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales

def load(path):
    with Path(path).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def preflight(manifest):
    rows=load(manifest)
    if not rows:raise ValueError('Empty manifest')
    if len({r['object_id'] for r in rows})!=len(rows):raise ValueError('Duplicate object IDs')
    paths={r['datalabs_source_file'] for r in rows}
    missing=[p for p in sorted(paths) if not Path(p).is_file()]
    # A science-only estimate at nominal 0.1 arcsec/pixel, including small header allowance.
    estimate=sum(math.ceil(float(r['cutout_width_arcsec'])/.1)**2*4+10000 for r in rows)
    print(f'{len(rows)} galaxies; {len(paths)} mosaics; {len(missing)} missing mounted paths')
    print(f'Approximate science-only output: {estimate/2**30:.2f} GiB; allow extra space.')
    if missing:print('First missing path:',missing[0])
    return dict(galaxies=len(rows),mosaics=len(paths),missing_paths=missing,estimated_GiB=estimate/2**30)

def make_one(row, output):
    source=Path(row['datalabs_source_file'])
    centre=SkyCoord(float(row['ra_deg'])*u.deg,float(row['dec_deg'])*u.deg)
    with fits.open(source,memmap=True) as hdul:
        image=next(h for h in hdul if len(h.shape or ())==2)
        wcs=WCS(image.header).celestial
        if wcs.cpdis1 or wcs.cpdis2 or wcs.det2im1 or wcs.det2im2:
            raise ValueError('Lookup-table WCS distortion requires a specialist cutout method')
        scale=abs(proj_plane_pixel_scales(wcs))*3600
        nx,ny=[int(math.ceil(float(row['cutout_width_arcsec'])/s)) for s in scale]
        cut=Cutout2D(image.data,centre,(ny,nx),wcs=wcs,mode='partial',fill_value=np.nan,copy=True)
        header=image.header.copy();header.update(cut.wcs.to_header(relax=True))
        for key in ('CHECKSUM','DATASUM','EXTNAME','XTENSION','PCOUNT','GCOUNT'):
            if key in header:del header[key]
        header['OBJECT']=row['name'];header['GALID']=row['object_id']
        header['GALRA']=float(row['ra_deg']);header['GALDEC']=float(row['dec_deg'])
        x,y=cut.wcs.world_to_pixel(centre)
        if not (0<=x<nx and 0<=y<ny):raise ValueError('Centre is outside output cutout')
        header['CENX']=float(x)+1;header['CENY']=float(y)+1
        input_height,input_width=image.shape
        cx,cy=wcs.world_to_pixel(centre)
        partial=cut.slices_original[0].stop-cut.slices_original[0].start<ny or cut.slices_original[1].stop-cut.slices_original[1].start<nx
        header['PARTIAL']=partial;header['VIEWWID']=float(row['cutout_width_arcsec'])
        header['SRCFILE']=row['mosaic_file_name'];header['TILEID']=int(row['mosaic_tile_index'])
        header.add_history('Native MER VIS background-subtracted science cutout on ESA Datalabs.')
        header.add_history('Size from catalogue display width. No rotation or deprojection.')
        header.add_history('Outside mosaic footprint padded with NaN. Science only; no auxiliary maps.')
        temp=output.with_suffix('.partial.fits')
        fits.PrimaryHDU(cut.data.astype(np.float32),header).writeto(temp,overwrite=True,checksum=True)
        temp.replace(output)
        return dict(partial=str(partial),naxis1=nx,naxis2=ny,finite_fraction=float(np.isfinite(cut.data).mean()))

def checkpoint(path, records):
    fields=['object_id','output_file','status','partial','naxis1','naxis2','finite_fraction','error','checked_utc']
    temp=path.with_suffix('.tmp')
    with temp.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records.values())
    temp.replace(path)

def run(manifest, output_dir, limit=5):
    rows=load(manifest)
    if limit is not None:rows=rows[:limit]
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    report=out/'MER_VIS_processing_manifest.csv'
    records={r['object_id']:r for r in load(report)} if report.exists() else {}
    # Process nearby objects from the same source consecutively.
    rows.sort(key=lambda r:r['datalabs_source_file'])
    for i,row in enumerate(rows,1):
        dest=out/f"Euclid_{row['object_id']}_MER_VIS_cutout.fits"
        rec=dict(object_id=row['object_id'],output_file=str(dest),status='',partial='',naxis1='',naxis2='',finite_fraction='',error='',checked_utc=datetime.now(timezone.utc).isoformat())
        try:
            if dest.exists():
                with fits.open(dest,checksum=True) as hdul:
                    h=hdul[0]
                    if str(h.header.get('GALID'))!=row['object_id'] or h.verify_checksum()!=1 or h.verify_datasum()!=1:
                        raise ValueError('Existing file identity/checksum failed; inspect it before rerunning')
                    rec.update(status='existing_verified',partial=str(h.header['PARTIAL']),naxis1=h.shape[1],naxis2=h.shape[0],finite_fraction=float(np.isfinite(h.data).mean()))
            else:
                required=math.ceil(float(row['cutout_width_arcsec'])/.1)**2*4
                if shutil.disk_usage(out).free<required+2**30:raise OSError('Less than 1 GiB filesystem reserve; stopping')
                rec.update(make_one(row,dest),status='created')
        except Exception as error:
            rec.update(status='error',error=str(error))
        records[row['object_id']]=rec;checkpoint(report,records)
        print(f"[{i}/{len(rows)}] {row['object_id']}: {rec['status']} {rec['error']}",flush=True)
        if rec['status']=='error' and isinstance(rec['error'],str) and 'reserve' in rec['error']:break
    print('Saved processing report:',report)
    return report
