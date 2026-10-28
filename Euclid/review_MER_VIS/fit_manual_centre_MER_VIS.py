"""Adaptive, independent MER VIS ellipse geometry v2. Preserve native science data.
Observed PAs: North towards East modulo180, local WCS. q0=0 by default.
Stop2 is iteration-limited, never called normally converged. Outputs retain provenance.
"""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import csv,json,math,time,warnings,hashlib,argparse,traceback
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.stats import sigma_clipped_stats
from scipy.ndimage import gaussian_filter,label,binary_dilation,median_filter
from photutils.isophote import Ellipse,EllipseGeometry
import inspect
VERSION='MER_VIS_centre_constrained_v3_2026-10-28'
from centre_policy_MER_VIS import POLICY_VERSION, DEFAULT_POLICY, checked_policy, centre_measurement, numerical_acceptance
CENTRE_POLICY=dict(DEFAULT_POLICY)
REFERENCE_CENTRE=None
NATIVE_SCALE=None
MANUAL_LOCK=True
def axial_mean(a,w=None):
 a=np.asarray(a);w=np.ones(len(a)) if w is None else np.asarray(w)
 return float(np.degrees(np.angle(np.sum(w*np.exp(2j*np.radians(a)))))/2%180)
def axial_diff(a,b):return (np.asarray(a)-b+90)%180-90
def scatter(a):return float(np.sqrt(np.mean(axial_diff(a,axial_mean(a))**2)))
def inclination(q,q0=0):return float(np.degrees(np.arccos(np.sqrt(np.clip((q*q-q0*q0)/(1-q0*q0),0,1)))))
def write_csv(p,rows):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 fields=list(dict.fromkeys(k for r in rows for k in r));tmp=p.with_suffix('.tmp')
 with tmp.open('w',newline='',encoding='utf8') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 for t in range(8):
  try:tmp.replace(p);break
  except PermissionError:
   if t==7:raise
   time.sleep(.25*(t+1))
def run_ellipse(data,mask,x,y,sma,eps,pa,maxsma,fixed=False):
 e=Ellipse(np.ma.array(data,mask=mask),geometry=EllipseGeometry(x,y,sma,eps,pa))
 clip='n_clip' if 'n_clip' in inspect.signature(e.fit_image).parameters else 'nclip'
 return list(e.fit_image(minsma=1,maxsma=maxsma,step=.12,maxit=45,fix_center=(fixed or MANUAL_LOCK),sclip=2.5,fflag=.5,maxgerr=1.,**{clip:3}))
def profile_rows(isos,wcs,xref,yref,xa,ya,b):
 out=[]
 for iso in isos:
  n=getattr(iso,'n_data',getattr(iso,'ndata',0));nf=getattr(iso,'n_flag',getattr(iso,'nflag',0));angle=float(iso.pa)
  x=xa+b*(iso.x0+.5)-.5;y=ya+b*(iso.y0+.5)-.5
  c=wcs.pixel_to_world(x,y);end=wcs.pixel_to_world(x+math.cos(angle),y+math.sin(angle));east,north=c.spherical_offsets_to(end)
  # Isophote errors can be absent for failed samples.
  def val(k):
   try:return float(getattr(iso,k))
   except:return float('nan')
  out.append(dict(sma_arcsec=float(iso.sma*b*np.sqrt(abs(np.linalg.det(wcs.pixel_scale_matrix)))*3600),ellipticity=float(iso.eps),pa_pixel_deg=float(np.degrees(angle)%180),pa_sky_deg=float(np.degrees(np.arctan2(east.arcsec,north.arcsec))%180),ellipticity_error=val('ellip_err'),pa_error_deg=float(np.degrees(val('pa_err'))),intensity=val('intens'),intensity_error=val('int_err'),stop_code=int(iso.stop_code),valid=bool(iso.valid),sampled_fraction=float(n/max(1,n+nf)),centre_offset_fit_pix=float(np.hypot(iso.x0-xref,iso.y0-yref)),x_original_pix=x,y_original_pix=y,sma_fit_pix=float(iso.sma)))
 for point in out:
  point.update(centre_measurement(point,REFERENCE_CENTRE,NATIVE_SCALE,CENTRE_POLICY))
  point.update(numerically_accepted_strict=numerical_acceptance(point),numerically_accepted_relaxed=numerical_acceptance(point,True))
 return out
def accepted(p,relaxed=False):
 # A relaxed numerical fit never relaxes the common centre-eligibility rule.
 return numerical_acceptance(p,relaxed) and p.get('centre_accepted',False)

def measure(task):
 global REFERENCE_CENTRE,NATIVE_SCALE
 r,input_dir,out_dir,area=task;r=dict(r);out=Path(out_dir);oid=r['object_id'];start=time.monotonic();log=[]
 keys=['bar_pa_sky_deg','disc_pa_sky_deg','inclination_deg','disc_axis_ratio','radius_arcsec','disc_pa_scatter_deg','bar_pa_scatter_deg','bar_min_arcsec','bar_max_arcsec','disc_min_arcsec','disc_max_arcsec']
 for k in keys:r['codex_'+k]=''
 r.update(codex_fit_status='fit_failed',codex_quality_flags='',codex_information='',codex_error='',codex_pipeline_version=VERSION,codex_method='',codex_bar_status='not_measured',q0=0)
 path=Path(input_dir)/r['fits_filename'];profile=[]
 try:
  with fits.open(path,memmap=True) as hd:
   h=hd[0].header.copy();ny,nx=hd[0].shape;catalogue_x=float(h['CENX'])-1;catalogue_y=float(h['CENY'])-1;x0=float(r['manual_centre_x_pix']);y0=float(r['manual_centre_y_pix'])
   if str(h.get('GALID'))!=oid:raise ValueError('GALID mismatch')
   wcs=WCS(h).celestial;scale=np.sqrt(abs(np.linalg.det(wcs.pixel_scale_matrix)))*3600
   REFERENCE_CENTRE=(x0,y0);NATIVE_SCALE=float(scale)
   r.update(centre_reference_x_pix=x0,centre_reference_y_pix=y0,centre_policy_version=POLICY_VERSION,centre_policy=checked_policy(CENTRE_POLICY))
   rseg=np.sqrt(float(area)/np.pi) if area else min(nx,ny)/8
   radius=min(max(nx,ny),int(max(4*rseg+40,80)))
   xa=max(0,int(x0-radius));xb=min(nx,int(x0+radius+1));ya=max(0,int(y0-radius));yb=min(ny,int(y0+radius+1))
   # Only read the selected section, avoiding a full-image float64 copy.
   raw=np.array(hd[0].data[ya:yb,xa:xb],dtype=np.float64)
  b=max(1,int(np.ceil(rseg/100)));ys,xs=np.array(raw.shape)//b
  raw=raw[:ys*b,:xs*b];blocks=raw.reshape(ys,b,xs,b);count=np.isfinite(blocks).sum(axis=(1,3));data=np.nansum(blocks,axis=(1,3))/np.maximum(count,1);mask=count<max(1,b*b*.7)
  x=(x0-xa+.5)/b-.5;y=(y0-ya+.5)/b-.5;rrseg=rseg/b
  med,_,noise=sigma_clipped_stats(data[~mask][::max(1,int((~mask).sum()/200000))]);noise=max(float(noise),1e-12);data-=med
  smooth=gaussian_filter(np.where(mask,0,data),1.5);yy,xx=np.indices(data.shape);near=np.hypot(xx-x,yy-y)<=max(4,.15*rrseg)
  xc=float(x);yc=float(y) # Explicit user centre; never snap to a different peak.
  segments,n=label((smooth>1.5*noise)&~mask);target=segments[int(round(yc)),int(round(xc))]
  if target==0:raise ValueError('No detected target near catalogue centre')
  neighbour=(segments>0)&(segments!=target);mask_neighbours=mask|binary_dilation(neighbour,iterations=2)
  high=data-gaussian_filter(np.where(mask,0,data),8);compact,nc=label((high>8*noise)&~mask_neighbours);stars=np.zeros(data.shape,bool)
  for lab in range(1,nc+1):
   sy,sx=np.where(compact==lab)
   if len(sx)<2 or len(sx)>150:continue
   if np.max(high[sy,sx])<40*noise:continue
   cx=float(np.mean(sx));cy=float(np.mean(sy));width=2.355*np.sqrt(np.mean((sx-cx)**2+(sy-cy)**2)/2)
   if np.hypot(cx-xc,cy-yc)<max(4,.15*rrseg) or width>4/b+1.5:continue
   radius_star=float(np.clip(3+np.log10(max(np.max(high[sy,sx])/noise,1))*2,4,18));stars|=(xx-cx)**2+(yy-cy)**2<radius_star**2
  masks=[('full_mask',mask_neighbours|binary_dilation(stars,iterations=2)),('neighbour_mask',mask_neighbours)]
  weights=np.where((segments==target)&~mask_neighbours,np.maximum(data,0),0);dx=xx-xc;dy=yy-yc
  cov=np.array([[np.sum(weights*dx*dx),np.sum(weights*dx*dy)],[np.sum(weights*dx*dy),np.sum(weights*dy*dy)]]);ev,vec=np.linalg.eigh(cov);pa=float(np.arctan2(vec[1,-1],vec[0,-1])%np.pi);eps=float(np.clip(1-np.sqrt(max(ev[0],1e-9)/max(ev[1],1e-9)),.08,.8))
  margin=min(xc,yc,data.shape[1]-1-xc,data.shape[0]-1-yc);maxsma=min(.95*margin,max(12,3.2*rrseg));best=[];best_isos=[];best_good=[];chosen='';chosen_mask=masks[0][1]
  with warnings.catch_warnings(record=True) as caught:
   warnings.simplefilter('always')
   # Maximise normally converged, reliable isophotes rather than total returned length.
   for maskname,maskuse in masks:
    for frac,e0,fixed in [(.5,eps,False),(.35,.2,False),(.8,eps,False),(.25,eps,True)]:
     seed=max(2,min(frac*rrseg,maxsma*.6))
     try:isos=run_ellipse(data,maskuse,xc,yc,seed,e0,pa,maxsma,fixed)
     except Exception as e:log.append(str(e));continue
     p=profile_rows(isos,wcs,xc,yc,xa,ya,b);good=[z for z in p if accepted(z)]
     if (len(good),sum(numerical_acceptance(z,True) for z in p),len(p))>(len(best_good),sum(numerical_acceptance(z,True) for z in best),len(best)):best=p;best_isos=isos;best_good=good;chosen=maskname+('_fixed_centre' if fixed else '');chosen_mask=maskuse
     if len(good)>=15:break
    if len(best_good)>=15:break
   if len(best_good)>=3:
    last=max(best_good,key=lambda z:z['sma_fit_pix']);outer=max(1.3*rrseg,1.2*last['sma_fit_pix'])
    if outer<maxsma*.95:
     try:
      isos=run_ellipse(data,chosen_mask,xc,yc,outer,last['ellipticity'],np.radians(last['pa_pixel_deg']),maxsma)
      extra=[z for z in profile_rows(isos,wcs,xc,yc,xa,ya,b) if z['sma_fit_pix']>=outer]
      if sum(accepted(z) for z in extra)>=2:best_isos=[iso for iso in best_isos if iso.sma<outer]+[iso for iso in isos if iso.sma>=outer];best=[z for z in best if z['sma_fit_pix']<outer]+extra;best_good=[z for z in best if accepted(z)];chosen+='_outer_pass'
     except Exception as e:log.append('Outer pass: '+str(e))
   method='standard';relaxed=False
   if len(best_good)<8:
    # Keep the explicit reference; only numerical criteria may be relaxed.
    inner=[z for z in best if z['valid'] and z['stop_code']==0 and z['sma_fit_pix']<max(10,.5*rrseg)]
    if len(best_good)<8:
     relaxed=True;method='relaxed_same_reference';best_good=[z for z in best if accepted(z,True)]
   if len(best_good)<3:
    relaxed=True;method='smoothed_relaxed'
    try:
     isos=run_ellipse(gaussian_filter(data,1),chosen_mask,xc,yc,max(2,min(.5*rrseg,maxsma*.5)),eps,pa,maxsma,True);p=profile_rows(isos,wcs,xc,yc,xa,ya,b);g=[z for z in p if accepted(z,True)]
     if len(g)>len(best_good):best=p;best_isos=isos;best_good=g
    except Exception as e:log.append('Smoothed retry: '+str(e))
   profile=sorted(best,key=lambda z:z['sma_arcsec']);r['codex_fit_warnings']='; '.join(dict.fromkeys(str(z.message) for z in caught))[:2000]
  good=sorted(best_good,key=lambda z:z['sma_arcsec']);r.update(codex_method=method,codex_mask_method=chosen,codex_n_good=len(good),codex_n_isophotes=len(profile),codex_binning=b,cutout_partial=h.get('PARTIAL',False),fits_path=str(path),codex_fit_centre_x_pix=xa+b*(xc+.5)-.5,codex_fit_centre_y_pix=ya+b*(yc+.5)-.5,codex_masked_fraction=float(chosen_mask.mean()))
  for z in profile:z.update(used_for_geometry=bool(accepted(z,relaxed)),selected_disc=False,selected_bar=False)
  r.update(codex_fit_centre_x_pix=x0,codex_fit_centre_y_pix=y0,centre_reference_x_pix=x0,centre_reference_y_pix=y0,centre_policy_version=POLICY_VERSION)
  if len(good)<3:raise ValueError(f'Only {len(good)} accepted isophotes after recovery; need at least 3')
  bright=[z for z in good if z['intensity']>(.2 if relaxed else 1)*noise]
  if len(bright)<5:bright=[z for z in good if z['intensity']>.5*noise]
  if len(bright)<3:bright=good[-3:];method+='_faint_disc_fallback';r['codex_method']=method
  rout=max(z['sma_arcsec'] for z in bright);pre=[z for z in bright if z['sma_arcsec']>=.6*rout];pre=pre or bright[-3:];prepa=axial_mean([z['pa_sky_deg'] for z in pre]);search=[z for z in good if .5<=z['sma_arcsec']<=.7*rout];candidates=[]
  if len(search)>=4:
   es=median_filter(np.array([z['ellipticity'] for z in search]),size=3,mode='nearest')
   for i,z in enumerate(search):
    if es[i]<.2 or es[i]<max(es[max(0,i-2):i+3]):continue
    left=i;right=i
    while left>0 and es[left-1]>=es[i]-.05 and i-left<12:left-=1
    while right<len(search)-1 and es[right+1]>=es[i]-.05 and right-i<12:right+=1
    plateau=search[left:right+1]
    if len(plateau)<3:continue
    aps=[p['pa_sky_deg'] for p in plateau];sc=scatter(aps)
    beyond=[p for p in good if z['sma_arcsec']<p['sma_arcsec']<=max(2.5*z['sma_arcsec'],z['sma_arcsec']+1)]
    if not beyond:continue
    drop=es[i]-min(p['ellipticity'] for p in beyond);twist=max(abs(axial_diff(p['pa_sky_deg'],z['pa_sky_deg'])) for p in beyond);bp=axial_mean(aps,[1/max(p['pa_error_deg'],.3)**2 for p in plateau]);offset=abs(axial_diff(bp,prepa))
    if sc<=10 and (drop>=.08 or (drop>=.04 and max(twist,offset)>=10)):
     grade='A' if drop>=.1 and sc<=5 and es[i]>=.3 else 'B';candidates.append((grade,float(es[i]),z['sma_arcsec'],plateau,bp,float(drop),sc))
  bar=sorted(candidates,key=lambda x:(x[0]=='A',x[1],x[2]),reverse=True)[0] if candidates else None
  barend=max(z['sma_arcsec'] for z in bar[3]) if bar else 0
  disc=[z for z in bright if max(.5*rout,1.25*barend)<=z['sma_arcsec']<=rout];range_fallback=len(disc)<3
  if range_fallback:disc=bright[-3:]
  centre_x=float(np.median([z['x_original_pix'] for z in disc]));centre_y=float(np.median([z['y_original_pix'] for z in disc]));centre_offset=float(np.hypot(x0-catalogue_x,y0-catalogue_y)*scale);centre_scatter=float(np.sqrt(np.mean([(z['x_original_pix']-x0)**2+(z['y_original_pix']-y0)**2 for z in disc]))*scale)
  r.update(codex_catalogue_centre_x_pix=catalogue_x,codex_catalogue_centre_y_pix=catalogue_y,codex_fit_centre_x_pix=x0,codex_fit_centre_y_pix=y0,codex_centre_offset_arcsec=centre_offset,codex_centre_scatter_arcsec=centre_scatter,measured_disc_centre_median_x_pix=centre_x,measured_disc_centre_median_y_pix=centre_y)
  dpa=axial_mean([z['pa_sky_deg'] for z in disc],[1/max(z['pa_error_deg'],.3)**2 for z in disc]);q=1-float(np.median([z['ellipticity'] for z in disc]));dscatter=scatter([z['pa_sky_deg'] for z in disc]);epsspan=float(np.ptp([z['ellipticity'] for z in disc]));flags=[];info=[]
  if centre_offset>max(.3,.15*rseg*scale):flags.append('centre_offset_large')
  if centre_scatter>max(.3,.1*rseg*scale):flags.append('centre_unstable')
  if q>.9:info.append('nearly_face_on_disc_PA_uncertain')
  else:
   radii=np.sort([z['sma_arcsec'] for z in disc]);span=float(np.ptp(radii));gap=float(np.max(np.diff(radii))) if len(radii)>1 else float('inf')
   sparse=len(disc)<6 or span<=0 or gap>0.5*span
   if sparse:flags.append('disc_PA_sparse_sampling')
   if dscatter>10:flags.append('disc_PA_unstable')
  if epsspan>.15:flags.append('disc_axis_ratio_unstable')
  if relaxed:flags.append('relaxed_fit')
  used=disc+(bar[3] if bar else [])
  if any(z['stop_code']==2 for z in used):flags.append('iteration_limited_samples')
  if len(good)<10:flags.append('short_accepted_profile')
  if range_fallback:flags.append('disc_range_fallback')
  if min(z['sma_arcsec'] for z in disc)<1.2*barend:flags.append('bar_disc_ranges_close')
  if rout<2:flags.append('small_disc')
  if 'neighbour_mask' in chosen:flags.append('star_mask_removed')
  if inclination(q)>=80:flags.append('high_inclination')
  if bar:
   if bar[0]=='B':flags.append('weak_ellipse_bar_signature')
   if barend<1.5:flags.append('small_bar_sensitive_to_resolution')
   r.update(codex_bar_status='detected_'+bar[0],codex_bar_pa_sky_deg=bar[4],codex_bar_pa_scatter_deg=bar[6],codex_bar_min_arcsec=min(z['sma_arcsec'] for z in bar[3]),codex_bar_max_arcsec=barend,codex_bar_eps_drop=bar[5],codex_n_bar=len(bar[3]))
  else:r['codex_bar_status']='no_bar_detected';flags.append('no_bar_detected')
  r.update(codex_fit_status='provisional_fit',codex_disc_pa_sky_deg=dpa,codex_inclination_deg=inclination(q),codex_disc_axis_ratio=q,codex_disc_pa_scatter_deg=dscatter,codex_disc_min_arcsec=min(z['sma_arcsec'] for z in disc),codex_disc_max_arcsec=max(z['sma_arcsec'] for z in disc),codex_radius_arcsec=rout,codex_n_disc=len(disc),codex_quality_flags=';'.join(flags),codex_information=';'.join(info),codex_disc_eps_span=epsspan,codex_disc_pa_error_deg=max(dscatter,float(np.median([z['pa_error_deg'] for z in disc]))))
  ids={id(z) for z in good};discs={id(z) for z in disc};bars={id(z) for z in bar[3]} if bar else set()
  for z in profile:z.update(used_for_geometry=id(z) in ids,selected_disc=id(z) in discs,selected_bar=id(z) in bars)
 except Exception as e:r['codex_error']=f'{type(e).__name__}: {e}';log.append(traceback.format_exc())
 finally:
  if profile:write_csv(out/'profiles'/f'Euclid_{oid}_MER_VIS_ellipse_profile.csv',profile)
  if profile and 'best_isos' in locals() and len(best_isos)>=3:
   try:
    from photutils.isophote import build_ellipse_model,IsophoteList
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from astropy.visualization import simple_norm
    radii={round(z['sma_fit_pix'],8) for z in profile if accepted(z,relaxed)}
    retained=[iso for iso in best_isos if round(float(iso.sma),8) in radii]
    if len(retained)>=3:
     model=build_ellipse_model(data.shape,IsophoteList(sorted(retained,key=lambda z:z.sma)),fill=np.nan)
     science=np.where(chosen_mask,np.nan,data);residual=np.where(chosen_mask,np.nan,data-model)
     finite_data=science[np.isfinite(science)];norm=simple_norm(finite_data,stretch='asinh',vmin=float(np.percentile(finite_data,2)),vmax=float(np.percentile(finite_data,99.7)))
     fig,axes=plt.subplots(1,3,figsize=(12,4),layout='constrained')
     for ax,array,title in zip(axes,[science,model,residual],['Background-subtracted science','Photutils elliptical model','Science − model (±5 sky noise)']):
      if ax is axes[2]:ax.imshow(array,origin='lower',cmap='coolwarm',vmin=-5*noise,vmax=5*noise)
      else:ax.imshow(array,origin='lower',cmap='gray',norm=norm)
      ax.plot((x0-xa+.5)/b-.5,(y0-ya+.5)/b-.5,'+',color='#ffd35c',markersize=8);ax.set_title(title,fontsize=10);cx=(x0-xa+.5)/b-.5;cy=(y0-ya+.5)/b-.5;half=max(12,1.25*max(float(iso.sma) for iso in retained));ax.set_xlim(max(-.5,cx-half),min(data.shape[1]-.5,cx+half));ax.set_ylim(max(-.5,cy-half),min(data.shape[0]-.5,cy+half));ax.set_axis_off()
     fig.suptitle(f'{oid} · fixed reference; residual structure can include real bars/arms',fontsize=11)
     dest=out/'diagnostics';dest.mkdir(exist_ok=True);fig.savefig(dest/f'Euclid_{oid}_MER_VIS_model_residual.png',dpi=125);plt.close(fig)
     r['centre_diagnostic_png']=str(dest/f'Euclid_{oid}_MER_VIS_model_residual.png');r['centre_model_isophotes']=len(retained)
   except Exception as diagnostic_error:log.append('Model diagnostic: '+str(diagnostic_error));r['centre_diagnostic_error']=str(diagnostic_error)

  r['calculation_seconds']=round(time.monotonic()-start,3)
  (out/'logs').mkdir(exist_ok=True);(out/'logs'/f'{oid}.log').write_text('\n'.join(log),encoding='utf8')
 return r

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--catalogue',type=Path,required=True);p.add_argument('--segmentation',type=Path,required=True);p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--workers',type=int,default=4);p.add_argument('--ids',nargs='*');p.add_argument('--limit',type=int);a=p.parse_args();out=a.output_dir;out.mkdir(parents=True,exist_ok=True);(out/'logs').mkdir(exist_ok=True);(out/'profiles').mkdir(exist_ok=True)
 rows=list(csv.DictReader(a.catalogue.open(encoding='utf-8-sig')));seg={r['object_id']:r.get('segmentation_area','') for r in csv.DictReader(a.segmentation.open(encoding='utf-8-sig'))};rows=[r for r in rows if not a.ids or r['object_id'] in a.ids];rows=rows[:a.limit] if a.limit else rows
 config=dict(version=VERSION,code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),catalogue_sha256=hashlib.sha256(a.catalogue.read_bytes()).hexdigest(),segmentation_sha256=hashlib.sha256(a.segmentation.read_bytes()).hexdigest(),q0=0)
 cfg=out/'MER_VIS_v2_run.json'
 if cfg.exists() and json.loads(cfg.read_text())!=config:raise ValueError('Different algorithm/configuration: choose another output directory')
 cfg.write_text(json.dumps(config,indent=2));dest=out/'MER_VIS_local_geometry_manifest.csv';previous={r['object_id']:r for r in csv.DictReader(dest.open(encoding='utf-8-sig'))} if dest.exists() else {};results=dict(previous);todo=[r for r in rows if r['object_id'] not in results]
 print(f'{len(rows)} targets; {len(todo)} pending; {a.workers} workers',flush=True)
 with ProcessPoolExecutor(max_workers=a.workers) as pool:
  fs={pool.submit(measure,(r,str(a.input_dir),str(out),seg.get(r['object_id']))):r['object_id'] for r in todo}
  for f in as_completed(fs):
   r=f.result();results[r['object_id']]=r;print(f"[{len(results)}/{len(rows)}] {r['object_id']} {r['codex_fit_status']} {r.get('codex_n_good',0)} {r['codex_error']}",flush=True)
   if len(results)%10==0:write_csv(dest,[results[r['object_id']] for r in rows if r['object_id'] in results])
 write_csv(dest,[results[r['object_id']] for r in rows]);print('COMPLETE',flush=True)
if __name__=='__main__':main()
