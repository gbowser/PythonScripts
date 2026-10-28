"""Centre-constrained MER VIS batch fitting; writes new trials, never the source manifest.

Use --ids or --limit for validation; --all is an explicit full-library operation.
Verified reference centres may be supplied by --references JSON keyed by object_id.
"""
from pathlib import Path
import argparse,csv,hashlib,json,math,sys,time,uuid
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent

def _run_one(task):
 row,area,output,references,policy=task
 import numpy as np
 from scipy.ndimage import gaussian_filter
 from astropy.io import fits
 from refit_MER_VIS import worker
 oid=row['object_id'];path=Path(row['fits_path']);out=Path(output);reference=references.get(oid)
 if reference:
  x=float(reference['x']);y=float(reference['y']);provenance=reference.get('provenance','supplied_reference_requires_validation')
 else:
  with fits.open(path,memmap=True) as hd:
   ny,nx=hd[0].shape;xcat=float(hd[0].header['CENX'])-1;ycat=float(hd[0].header['CENY'])-1;rseg=math.sqrt(float(area)/math.pi);search=max(4,.15*rseg);margin=int(math.ceil(search+8));xa=max(0,int(xcat-margin));xb=min(nx,int(xcat+margin+1));ya=max(0,int(ycat-margin));yb=min(ny,int(ycat+margin+1));image=np.array(hd[0].section[ya:yb,xa:xb],dtype=float)
  smooth=gaussian_filter(np.where(np.isfinite(image),image,0),1.5);yy,xx=np.indices(image.shape);valid=np.isfinite(image)&(np.hypot(xx+xa-xcat,yy+ya-ycat)<=search);iy,ix=np.unravel_index(np.argmax(np.where(valid,smooth,-np.inf)),smooth.shape);x=float(ix+xa);y=float(iy+ya);provenance='catalogue_nearby_smoothed_peak_unverified'
 stages=[]
 for locked in [False,True]:
  job=uuid.uuid4().hex;folder=out/'refits'/job;folder.mkdir(parents=True);request=dict(object_id=oid,row=dict(row,manual_centre_x_pix=x,manual_centre_y_pix=y),segmentation_area=area,lock_centre=locked,centre_policy=policy,reference_provenance=provenance,source_manifest_sha256=row['_source_manifest_sha256'],engine_sha256=hashlib.sha256((HERE/'fit_manual_centre_MER_VIS.py').read_bytes()).hexdigest(),worker_sha256=hashlib.sha256((HERE/'refit_MER_VIS.py').read_bytes()).hexdigest(),requested_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
  (folder/'request.json').write_text(json.dumps(request,indent=2),encoding='utf8');worker(folder/'request.json');result=json.loads((folder/'result.json').read_text());stages.append((job,result))
  rejected=False
  profile=folder/'profiles'/f'Euclid_{oid}_MER_VIS_ellipse_profile.csv'
  if profile.exists():
   with profile.open(encoding='utf-8-sig') as f:rejected=any(p.get('numerically_accepted_relaxed','').lower()=='true' and p.get('centre_accepted','').lower()!='true' for p in csv.DictReader(f))
  if not locked and result['codex_fit_status']=='provisional_fit' and not rejected:break
 chosen=next(((job,r) for job,r in reversed(stages) if r['codex_fit_status']=='provisional_fit'),stages[-1]);job,result=chosen
 result.update(centre_batch_trial_job=job,centre_batch_stages=[dict(job=j,status=r['codex_fit_status'],fixed=r['manual_centre_locked']) for j,r in stages],centre_batch_requires_review=True)
 return result

def run_one(task):
 try:return _run_one(task)
 except Exception as exc:
  row=dict(task[0])
  for key in row:
   if key.startswith('codex_') or key.endswith('_difference_deg'):row[key]=''
  row.update(codex_fit_status='fit_failed',codex_error=f'{type(exc).__name__}: {exc}',centre_batch_requires_review=True)
  return row

def main():
 from centre_policy_MER_VIS import DEFAULT_POLICY,checked_policy
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--catalogue',type=Path,required=True);parser.add_argument('--segmentation',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True);parser.add_argument('--references',type=Path);parser.add_argument('--workers',type=int,default=2);group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--ids',nargs='+');group.add_argument('--limit',type=int);group.add_argument('--all',action='store_true');a=parser.parse_args()
 if not 1<=a.workers<=8:parser.error('Use 1–8 workers')
 digest=hashlib.sha256(a.catalogue.read_bytes()).hexdigest();rows=list(csv.DictReader(a.catalogue.open(encoding='utf-8-sig')));areas={r['object_id']:r['segmentation_area'] for r in csv.DictReader(a.segmentation.open(encoding='utf-8-sig'))};references=json.loads(a.references.read_text()) if a.references else {};rows=[r for r in rows if not a.ids or r['object_id'] in a.ids];rows=rows[:a.limit] if a.limit else rows;a.output_dir.mkdir(parents=True,exist_ok=True)
 if (a.output_dir/'MER_VIS_centre_constrained_manifest.json').exists():parser.error('Choose a new output folder to preserve previous trials')
 if a.catalogue.resolve()==(a.output_dir/'MER_VIS_centre_constrained_manifest.csv').resolve():parser.error('Output must not overwrite source catalogue')
 tasks=[]
 for row in rows:row['_source_manifest_sha256']=digest;tasks.append((row,areas[row['object_id']],str(a.output_dir),references,checked_policy(DEFAULT_POLICY)))
 with ProcessPoolExecutor(max_workers=a.workers) as pool:results=list(pool.map(run_one,tasks))
 (a.output_dir/'MER_VIS_centre_constrained_manifest.json').write_text(json.dumps(results,indent=2),encoding='utf8')
 from fit_manual_centre_MER_VIS import write_csv
 write_csv(a.output_dir/'MER_VIS_centre_constrained_manifest.csv',results);print(f'Saved {len(results)} new trial rows; visual validation required.')
if __name__=='__main__':main()
