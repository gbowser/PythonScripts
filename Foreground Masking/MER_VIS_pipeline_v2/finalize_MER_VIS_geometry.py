"""Finalize geometry metadata and validate the new run before report generation."""
import csv,json,math,hashlib,shutil
from pathlib import Path
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from fit_adaptive_MER_VIS_geometry import write_csv,axial_diff,VERSION
from collections import Counter
import argparse
p=argparse.ArgumentParser();p.add_argument('--geometry-dir',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--recovery-cache-dir',type=Path);a=p.parse_args();dest=a.geometry_dir/'MER_VIS_local_geometry_manifest.csv';rows=list(csv.DictReader(dest.open(encoding='utf-8-sig')));old={r['object_id']:r for r in csv.DictReader(a.baseline.open(encoding='utf-8-sig'))}
# Retry only failed targets, retaining trial profiles with zero strict samples so
# explicitly relaxed recovery has actual samples to assess. Successful fits unchanged.
from recover_failed_MER_VIS_geometry import measure as recover
segpath=Path(__file__).parent.parent/'datalabs_MER_VIS'/'MER_VIS_datalabs_manifest.csv'
seg={z['object_id']:z.get('segmentation_area','') for z in csv.DictReader(segpath.open(encoding='utf-8-sig'))}
retried=[]
cache={}
if a.recovery_cache_dir:
 cache_config=json.loads((a.recovery_cache_dir/'MER_VIS_v2_run.json').read_text())
 assert cache_config['code_sha256']==hashlib.sha256((Path(__file__).parent/'recover_failed_MER_VIS_geometry.py').read_bytes()).hexdigest(),'Recovery cache algorithm mismatch'
 cache={z['object_id']:z for z in csv.DictReader((a.recovery_cache_dir/'MER_VIS_local_geometry_manifest.csv').open(encoding='utf8'))}
 assert set(cache).issubset({z['object_id'] for z in rows if z['codex_fit_status']=='fit_failed'})
for i,r in enumerate(rows):
 if r['codex_fit_status']=='fit_failed':
  if r['object_id'] in cache:
   updated=dict(r);updated.update(cache[r['object_id']])
   pp=a.recovery_cache_dir/'profiles'/f"Euclid_{r['object_id']}_MER_VIS_ellipse_profile.csv"
   if pp.exists():shutil.copyfile(pp,a.geometry_dir/'profiles'/pp.name)
  else:updated=recover((r,str(Path(r['fits_path']).parent),str(a.geometry_dir),seg.get(r['object_id'])))
  retried.append(dict(object_id=r['object_id'],before=r['codex_error'],after_status=updated['codex_fit_status'],after_error=updated['codex_error']))
  rows[i]=updated
(a.geometry_dir/'MER_VIS_failed_recovery_audit.json').write_text(json.dumps(dict(retry_script_sha256=hashlib.sha256((Path(__file__).parent/'recover_failed_MER_VIS_geometry.py').read_bytes()).hexdigest(),targets=retried),indent=2))
override_path=Path(__file__).parent/'MER_VIS_geometry_review_overrides.csv'
review_audit=[]
if override_path.exists():
 overrides={z['object_id']:z for z in csv.DictReader(override_path.open(encoding='utf-8-sig'))}
 for r in rows:
  override=overrides.get(r['object_id'])
  if not override:continue
  if override['action']!='reject_geometry':raise ValueError('Unknown review action')
  review_audit.append(dict(object_id=r['object_id'],candidate_status=r['codex_fit_status'],reason=override['reason']))
  for key in ['disc_pa_sky_deg','bar_pa_sky_deg','inclination_deg','disc_axis_ratio','disc_pa_scatter_deg','bar_pa_scatter_deg','bar_min_arcsec','bar_max_arcsec','disc_min_arcsec','disc_max_arcsec','fit_centre_x_pix','fit_centre_y_pix','centre_offset_arcsec','centre_scatter_arcsec']:
   r['codex_'+key]=''
  r.update(codex_fit_status='fit_failed',codex_bar_status='not_measured',codex_quality_flags='',codex_information='',codex_error=override['reason'],codex_n_good=0,codex_review_action='reject_geometry',codex_review_reason=override['reason'])
  pp=a.geometry_dir/'profiles'/f"Euclid_{r['object_id']}_MER_VIS_ellipse_profile.csv"
  if pp.exists():
   diagnostic=list(csv.DictReader(pp.open(encoding='utf8')))
   for z in diagnostic:z.update(used_for_geometry=False,selected_disc=False,selected_bar=False)
   write_csv(pp,diagnostic)
(a.geometry_dir/'MER_VIS_visual_review_audit.json').write_text(json.dumps(dict(overrides_sha256=hashlib.sha256(override_path.read_bytes()).hexdigest() if override_path.exists() else None,decisions=review_audit),indent=2))

assert len(rows)==2777 and len({r['object_id'] for r in rows})==2777
for r in rows:
 with fits.open(r['fits_path'],memmap=True) as hd:
  h=hd[0].header;w=WCS(h).celestial;x=float(h['CENX'])-1;y=float(h['CENY'])-1;c=w.pixel_to_world(x,y);theta=math.radians(float(r['euclid_detection_pa_pixel_deg']));d=w.pixel_to_world(x+math.cos(theta),y+math.sin(theta));e,n=c.spherical_offsets_to(d);r['euclid_detection_pa_sky_deg']=float(math.degrees(math.atan2(e.arcsec,n.arcsec))%180);r['euclid_adjusted_detection_pa_sky_deg']=(r['euclid_detection_pa_sky_deg']+90)%180;r['euclid_detection_pa_conversion_status']='native_WCS_then_adopted_additional_sky_plus90';r['cutout_partial']=h.get('PARTIAL',False)
 if r['codex_fit_status']=='provisional_fit':
  assert 0<=float(r['codex_disc_pa_sky_deg'])<180 and 0<=float(r['codex_inclination_deg'])<=90
  r['disc_vs_detection_pa_difference_deg']=float(axial_diff(float(r['codex_disc_pa_sky_deg']),r['euclid_adjusted_detection_pa_sky_deg']))
  for proxy,key in [('euclid_detection_inclination_proxy_deg','inclination_vs_detection_proxy_difference_deg'),('euclid_sersic_inclination_proxy_deg','inclination_vs_sersic_proxy_difference_deg')]:
   try:r[key]=float(r['codex_inclination_deg'])-float(r[proxy])
   except:r[key]=''
write_csv(dest,rows)
fitsrows=[r for r in rows if r['codex_fit_status']=='provisional_fit'];fail=[r for r in rows if r['codex_fit_status']=='fit_failed'];flags=Counter(f for r in fitsrows for f in r['codex_quality_flags'].split(';') if f);mult=Counter(sum(bool(f) for f in r['codex_quality_flags'].split(';')) for r in fitsrows)
def stat(key):
 vals=np.array([float(r[key]) for r in fitsrows if r.get(key,'')!='']);return {'n':len(vals),'median_abs':float(np.median(abs(vals))),'median_signed':float(np.median(vals)),'within10':int((abs(vals)<=10).sum())} if len(vals) else {'n':0}
summary=dict(version=VERSION,total=len(rows),fits=len(fitsrows),failures=len(fail),flags=dict(flags),flag_multiplicity=dict(sorted(mult.items())),methods=dict(Counter(r.get('codex_method','') for r in rows)),bar_status=dict(Counter(r['codex_bar_status'] for r in rows)),informational_face_on=sum('nearly_face_on' in r['codex_information'] for r in fitsrows),recovered_original_failures=sum(old[r['object_id']]['codex_fit_status']=='fit_failed' for r in fitsrows),new_failures_from_original_fits=sum(old[r['object_id']]['codex_fit_status']=='provisional_fit' for r in fail),failures_detail=[{'object_id':r['object_id'],'error':r['codex_error']} for r in fail],comparisons={k:stat(k) for k in ['disc_vs_detection_pa_difference_deg','inclination_vs_detection_proxy_difference_deg','inclination_vs_sersic_proxy_difference_deg']},centre_offset_arcsec=stat('codex_centre_offset_arcsec'),centre_flag_threshold='offset > max(0.3 arcsec,0.15*r_seg); scatter > max(0.3 arcsec,0.1*r_seg)',source_manifest_sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
(a.geometry_dir/'MER_VIS_v2_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps(summary,indent=2))
