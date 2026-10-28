"""Render galaxy-scale Photutils models from saved trial profiles, without refitting."""
import csv,hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.visualization import simple_norm
from photutils.isophote import IsophoteList,build_ellipse_model
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
base=Path(__file__).resolve().parent;script_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
for job in json.loads((base/'jobs.json').read_text()):
 folder=Path(job['request']).parent;request=json.loads(Path(job['request']).read_text());result=json.loads((folder/'result.json').read_text());row=request['row'];oid=job['object_id'];b=int(result['codex_binning']);x0=row['manual_centre_x_pix'];y0=row['manual_centre_y_pix']
 with fits.open(row['fits_path'],memmap=True) as hd:
  ny,nx=hd[0].shape;rseg=np.sqrt(float(request['segmentation_area'])/np.pi);radius=min(max(nx,ny),int(max(4*rseg+40,80)));xa=max(0,int(x0-radius));xb=min(nx,int(x0+radius+1));ya=max(0,int(y0-radius));yb=min(ny,int(y0+radius+1));raw=np.array(hd[0].section[ya:yb,xa:xb],dtype=float)
 ys,xs=np.array(raw.shape)//b;raw=raw[:ys*b,:xs*b];blocks=raw.reshape(ys,b,xs,b);count=np.isfinite(blocks).sum(axis=(1,3));data=np.nansum(blocks,axis=(1,3))/np.maximum(count,1);invalid=count<max(1,b*b*.7);med,_,noise=sigma_clipped_stats(data[~invalid][::max(1,int((~invalid).sum()/200000))]);data-=med;noise=max(float(noise),1e-12)
 with (folder/'profiles'/f'Euclid_{oid}_MER_VIS_ellipse_profile.csv').open(encoding='utf-8-sig') as stream:profile=[p for p in csv.DictReader(stream) if p['used_for_geometry'].lower()=='true']
 profile.sort(key=lambda p:float(p['sma_fit_pix']));rad=np.array([float(p['sma_fit_pix']) for p in profile]);intens=np.array([float(p['intensity']) for p in profile]);grad=np.gradient(intens,rad);isos=[]
 for i,p in enumerate(profile):isos.append(SimpleNamespace(sma=rad[i],intens=intens[i],eps=float(p['ellipticity']),pa=np.radians(float(p['pa_pixel_deg'])),x0=(float(p['x_original_pix'])-xa+.5)/b-.5,y0=(float(p['y_original_pix'])-ya+.5)/b-.5,grad=grad[i],a3=0.,b3=0.,a4=0.,b4=0.))
 model=build_ellipse_model(data.shape,IsophoteList(isos),fill=np.nan);science=np.where(invalid,np.nan,data);residual=science-model;norm=simple_norm(science[np.isfinite(science)],stretch='asinh',vmin=float(np.nanpercentile(science,2)),vmax=float(np.nanpercentile(science,99.7)));cx=(x0-xa+.5)/b-.5;cy=(y0-ya+.5)/b-.5;half=max(12,1.25*max(rad))
 fig,axes=plt.subplots(1,3,figsize=(12,4),layout='constrained')
 for i,(ax,array,title) in enumerate(zip(axes,[science,model,residual],['Science','Photutils elliptical model','Science − model (±5 sky noise)'])):
  if i==2:ax.imshow(array,origin='lower',cmap='coolwarm',vmin=-5*noise,vmax=5*noise)
  else:ax.imshow(array,origin='lower',cmap='gray',norm=norm)
  ax.plot(cx,cy,'+',color='#ffd35c',markersize=8);ax.set_xlim(max(-.5,cx-half),min(xs-.5,cx+half));ax.set_ylim(max(-.5,cy-half),min(ys-.5,cy+half));ax.set_title(title,fontsize=11);ax.set_axis_off()
 fig.suptitle(f'{oid} · same reference and scale; white = outside model/invalid pixels',fontsize=11);fig.savefig(folder/'diagnostics'/f'Euclid_{oid}_MER_VIS_model_residual.png',dpi=125);plt.close(fig)
 result.update(centre_diagnostic_renderer_sha256=script_hash,centre_diagnostic_note='Rebuilt from saved accepted isophotes; science and residual use finite original working pixels, including any real structure or contaminating sources. White is outside fitted model coverage or invalid science.')
 (folder/'result.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(oid+' diagnostic redrawn',flush=True)
