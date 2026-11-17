"""Bounded DR1 science-cutout to PixInsight-style AutoSTF preview benchmark.

Download mode measures this machine and HTTP service; datalabs mode measures
mounted-mosaic section reads on ESA. Neither performs detection or science fits.
"""
import argparse,csv,hashlib,io,json,math,os,platform,statistics,sys,time,urllib.request,zipfile
from pathlib import Path
START=time.perf_counter()
import numpy as np
from PIL import Image,ImageDraw
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from astropy.coordinates import SkyCoord
from astropy.nddata import Cutout2D
import astropy.units as u
import astropy
IMPORT_SECONDS=time.perf_counter()-START

def autostretch(data,shadows=-2.8,target=.25,gamma=1.):
    """Same AutoSTF calculation as Euclid/masking_review/masking_core.preview."""
    finite=data[np.isfinite(data)]
    if not finite.size:raise ValueError('No finite science pixels')
    median=float(np.median(finite));lo=float(finite.min());hi=float(finite.max())
    sigma=float(1.4826*np.median(np.abs(finite-median)));span=hi-lo
    def mtf(m,x):
        m=np.clip(m,np.finfo(float).eps,1-np.finfo(float).eps);x=np.clip(x,0,1)
        return np.clip(((m-1)*x)/((2*m-1)*x-m),0,1)
    if span<=np.finfo(float).eps:value=np.zeros_like(data)
    else:
        centre=(median-lo)/span
        black=float(np.clip(centre+np.clip(shadows,-20,0)*sigma/span,0,1))
        after_black=np.clip((centre-black)/max(1-black,np.finfo(float).eps),0,1)
        midtones=mtf(np.clip(target,.01,.99),after_black)
        low=lo+black*span
        value=mtf(midtones,(np.nan_to_num(data,nan=low)-low)/max(hi-low,np.finfo(float).eps))
    value=np.where(np.isfinite(data),value,0)**(1/float(np.clip(gamma,.2,3)))
    return np.asarray(np.rint(255*value),dtype=np.uint8)

def load(path):
    with Path(path).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def write_csv(path,rows):
    if not rows:return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    temp=Path(str(path)+'.tmp')
    with temp.open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    temp.replace(path)
def digest(data):return hashlib.sha256(data).hexdigest()
def downloaded(row,max_bytes):
    req=urllib.request.Request(row['cutout_url'],headers={'User-Agent':'Euclid-DR1-preview-pilot/1.0'})
    chunks=[];n=0
    with urllib.request.urlopen(req,timeout=90) as response:
        if int(response.headers.get('Content-Length','0'))>max_bytes:raise ValueError('Download exceeds byte bound')
        content_type=response.headers.get('Content-Type','')
        while True:
            chunk=response.read(1024*1024)
            if not chunk:break
            n+=len(chunk)
            if n>max_bytes:raise ValueError('Download exceeds byte bound')
            chunks.append(chunk)
    body=b''.join(chunks)
    if body[:2]==b'PK':
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            entries=[i for i in z.infolist() if i.filename.lower().endswith(('.fits','.fit'))]
            if len(entries)!=1:raise ValueError('Expected exactly one FITS in cutout response')
            if entries[0].file_size>max_bytes:raise ValueError('Uncompressed FITS exceeds byte bound')
            science=z.read(entries[0])
    else:science=body
    return science,dict(download_bytes=n,response_content_type=content_type,download_sha256=digest(body),fits_sha256=digest(science))
def decoded(science,row):
    with fits.open(io.BytesIO(science),memmap=False) as hdul:
        image=next(h for h in hdul if len(h.shape or ())==2)
        return image.data.astype(np.float64),image.header.copy()
def mounted(row):
    source=Path(row['datalabs_source_file'])
    target=SkyCoord(float(row['ra_deg'])*u.deg,float(row['dec_deg'])*u.deg)
    with fits.open(source,memmap=True) as hdul:
        image=next(h for h in hdul if len(h.shape or ())==2)
        wcs=WCS(image.header).celestial
        if any([wcs.cpdis1,wcs.cpdis2,wcs.det2im1,wcs.det2im2]):raise ValueError('Lookup-table WCS unsupported')
        scales=np.abs(proj_plane_pixel_scales(wcs))*3600
        nx,ny=[int(math.ceil(float(row['requested_width_arcsec'])/s)) for s in scales]
        x,y=wcs.world_to_pixel(target)
        # Read only the bounded mosaic section, rather than materialising the whole mosaic.
        x0=max(0,int(math.floor(x-nx/2))-2);x1=min(image.shape[1],int(math.ceil(x+nx/2))+3)
        y0=max(0,int(math.floor(y-ny/2))-2);y1=min(image.shape[0],int(math.ceil(y+ny/2))+3)
        if x1<=x0 or y1<=y0:raise ValueError('Requested centre outside mosaic')
        section=image.section[y0:y1,x0:x1].astype(np.float64)
        section_wcs=wcs.slice((slice(y0,y1),slice(x0,x1)))
        cut=Cutout2D(section,target,(ny,nx),wcs=section_wcs,mode='partial',fill_value=np.nan,copy=True)
        h=image.header.copy();h.update(cut.wcs.to_header(relax=True))
        return cut.data,h
def summary(records,out,population_total):
    ok=[r for r in records if r.get('status')=='created']
    stats={}
    for key in ['download_seconds','read_wcs_seconds','autostretch_seconds','png_seconds','total_seconds','cpu_seconds','pixels','png_bytes']:
        vals=[float(r[key]) for r in ok if key in r]
        if vals:stats[key]=dict(mean=statistics.mean(vals),median=statistics.median(vals),p90=float(np.percentile(vals,90)),minimum=min(vals),maximum=max(vals))
    report=dict(success=len(ok),errors=sum(r.get('status')=='error' for r in records),timing=stats,population_total=population_total,
        sequential_estimated_hours=population_total*stats['total_seconds']['mean']/3600 if ok and population_total else None,
        extrapolation_caution='Pilot is first IDs, not a size/random sample; HTTP cache, image sizes, rate limits and ESA environment differ. No segmentation, fitting or masking included.')
    (out/'timing_summary.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    return report
def contact_sheet(records,out):
    ok=[r for r in records if r.get('status')=='created']
    for start in range(0,len(ok),25):
        canvas=Image.new('RGB',(1200,1325),'#161616');draw=ImageDraw.Draw(canvas)
        for j,r in enumerate(ok[start:start+25]):
            image=Image.open(out/r['png_file']).convert('RGB');image.thumbnail((232,232))
            x=(j%5)*240;y=(j//5)*265;canvas.paste(image,(x+(240-image.width)//2,y+(232-image.height)//2))
            draw.text((x+3,y+235),r['object_id'],fill='white');draw.text((x+3,y+249),f"{float(r['total_seconds']):.2f}s",fill='#bbbbbb')
        canvas.save(out/f'contact_sheet_{start//25+1:02}.png')
def run(manifest,output,limit=100,source_mode='download',keep_fits=False,population_total=0):
    if not 1<=limit<=100:raise ValueError('Pilot limited to 1 to 100 objects')
    rows=load(manifest)[:limit];out=Path(output);out.mkdir(parents=True,exist_ok=True);(out/'png').mkdir(exist_ok=True)
    path=out/'image_timings.csv';records=load(path) if path.exists() else []
    previous={r['object_id']:r for r in records};manifest_hash=digest(Path(manifest).read_bytes())
    config=dict(manifest_sha256=manifest_hash,source_mode=source_mode,selection_policy='provisional_two_answer_disc',shadows=-2.8,target=.25,gamma=1.,preview_max_side=1536,
                imports_seconds=IMPORT_SECONDS,python=sys.version,platform=platform.platform(),processor=platform.processor(),numpy=np.__version__,astropy=astropy.__version__,max_download_bytes=128*1024**2,keep_fits=keep_fits)
    if (out/'configuration.json').exists():
        old=json.loads((out/'configuration.json').read_text())
        if any(old[k]!=config[k] for k in ['manifest_sha256','source_mode','shadows','target','gamma','preview_max_side','keep_fits']):raise ValueError('Output folder belongs to another configuration')
    (out/'configuration.json').write_text(json.dumps(config,indent=2),encoding='utf8')
    for i,row in enumerate(rows,1):
        ident=row['object_id'];png_file=f'png/DR1_{ident}.png'
        if previous.get(ident,{}).get('status')=='created' and (out/png_file).exists():continue
        rec=dict(object_id=ident,source_mode=source_mode,png_file=png_file,status='',error='',width_arcsec=row['requested_width_arcsec'])
        t=time.perf_counter();cpu=time.process_time()
        try:
            width=float(row['requested_width_arcsec'])
            if not math.isfinite(width) or not 0<width<=300:raise ValueError('Width outside pilot bound')
            a=time.perf_counter()
            if source_mode=='download':
                science,meta=downloaded(row,128*1024**2);rec.update(meta);rec['download_seconds']=time.perf_counter()-a;a=time.perf_counter();data,h=decoded(science,row)
            else:rec['download_seconds']=0.;data,h=mounted(row)
            if data.size>20_000_000:raise ValueError('Decoded array outside pilot bound')
            wcs=WCS(h).celestial;scales=np.abs(proj_plane_pixel_scales(wcs))*3600
            target=SkyCoord(float(row['ra_deg'])*u.deg,float(row['dec_deg'])*u.deg);cx,cy=wcs.world_to_pixel(target)
            if not (math.isfinite(cx) and math.isfinite(cy) and 0<=cx<data.shape[1] and 0<=cy<data.shape[0]):raise ValueError('Catalogue centre is outside returned WCS')
            rec.update(read_wcs_seconds=time.perf_counter()-a,naxis1=data.shape[1],naxis2=data.shape[0],pixels=data.size,finite_fraction=float(np.isfinite(data).mean()),pixel_scale_arcsec=float(np.mean(scales)),centre_x_pix=float(cx),centre_y_pix=float(cy))
            a=time.perf_counter();display=autostretch(data);rec['autostretch_seconds']=time.perf_counter()-a
            a=time.perf_counter();im=Image.fromarray(np.flipud(display));im.thumbnail((1536,1536),Image.Resampling.LANCZOS);im.save(out/png_file);rec['png_seconds']=time.perf_counter()-a;rec['png_bytes']=(out/png_file).stat().st_size
            if keep_fits:
                dest=out/f'DR1_{ident}_cutout.fits'
                if source_mode=='download':dest.write_bytes(science)
                else:fits.PrimaryHDU(data.astype(np.float32),h).writeto(dest,overwrite=False,checksum=True)
            wh={k:h[k] for k in h if k.startswith(('CTYPE','CRPIX','CRVAL','CDELT','CD1_','CD2_','PC1_','PC2_'))}
            (out/'png'/f'DR1_{ident}_wcs.json').write_text(json.dumps(dict(object_id=ident,requested_ra_deg=row['ra_deg'],requested_dec_deg=row['dec_deg'],native_fits_wcs=wh,fits_header_text=h.tostring(sep='\n'),png_flipud=True,png_size=im.size,native_shape=data.shape,preview_is_science=False),indent=2),encoding='utf8')
            rec['status']='created'
        except Exception as e:rec.update(status='error',error=str(e))
        rec['total_seconds']=time.perf_counter()-t;rec['cpu_seconds']=time.process_time()-cpu
        previous[ident]=rec;records=list(previous.values());write_csv(path,records);summary(records,out,population_total)
        print(f'[{i}/{len(rows)}] {ident}: {rec["status"]} {rec["total_seconds"]:.3f}s {rec["error"]}',flush=True)
    contact_sheet(records,out)
    return summary(records,out,population_total)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--limit',type=int,default=100);p.add_argument('--source-mode',choices=['download','datalabs'],default='download');p.add_argument('--keep-fits',action='store_true');p.add_argument('--population-total',type=int,default=0)
    a=p.parse_args();print(json.dumps(run(a.manifest,a.output,a.limit,a.source_mode,a.keep_fits,a.population_total),indent=2))
