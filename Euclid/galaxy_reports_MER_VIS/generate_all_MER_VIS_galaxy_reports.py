"""Generate all MER VIS report PNGs, separating quality issues and resumable metadata."""
from pathlib import Path
import argparse,json,hashlib,math,time
from concurrent.futures import ProcessPoolExecutor,as_completed
import pandas as pd
from make_MER_VIS_galaxy_report_cards import make_card

def safe(v):
 if isinstance(v,dict):return {k:safe(x) for k,x in v.items()}
 if isinstance(v,list):return [safe(x) for x in v]
 if isinstance(v,float) and not math.isfinite(v):return None
 return v

def worker(job):
 r,profiles,out,ordinal=job
 flags=r.get('codex_quality_flags','');flags='' if pd.isna(flags) else str(flags)
 qi=bool(flags or r.get('codex_fit_status')!='provisional_fit' or str(r.get('cutout_partial')).lower()=='true')
 sub=out/('png_QI' if qi else 'png_NoQI');meta=out/'metadata'/f'{r["object_id"]}.json'
 if meta.exists():
  existing=json.loads(meta.read_text(encoding='utf8'))
  if existing.get('report_version')=='QI_v1' and (out/existing['relative_png']).exists():return existing
 result=safe(make_card(r,profiles,sub,ordinal));assert result['quality_issue']==qi
 result['relative_png']=str(Path(sub.name)/result['png']);result['report_version']='QI_v1'
 temp=meta.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf8');temp.replace(meta)
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-root',type=Path,default=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid'));p.add_argument('--workers',type=int,default=2);p.add_argument('--limit',type=int);a=p.parse_args();out=a.data_root/'MER_VIS_galaxy_reports'/'all_2777';out.mkdir(exist_ok=True,parents=True)
 for sub in ['png_QI','png_NoQI','metadata','pdf_QI','pdf_NoQI']:(out/sub).mkdir(exist_ok=True)
 source=a.data_root/'Euclid_MER_VIS_geometry'/'MER_VIS_local_geometry_manifest.csv';d=pd.read_csv(source,dtype={'object_id':str});records=d.to_dict('records');records=records[:a.limit] if a.limit else records;results=[];errors=[];start=time.monotonic()
 (out/'MER_VIS_report_run.json').write_text(json.dumps({'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'targets':len(records),'workers':a.workers,'QI_rule':'Any geometry flag, fit status other than provisional_fit, or partial requested coverage. NoQI is not scientific approval.','report_version':'QI_v1'},indent=2))
 jobs=[(r,a.data_root/'Euclid_MER_VIS_geometry'/'profiles',out,k) for k,r in enumerate(records,1)]
 with ProcessPoolExecutor(max_workers=a.workers) as pool:
  futures={pool.submit(worker,job):job[0]['object_id'] for job in jobs}
  for f in as_completed(futures):
   try:results.append(f.result())
   except Exception as e:errors.append({'object_id':futures[f],'error':str(e)});print('ERROR',futures[f],str(e),flush=True)
   done=len(results)+len(errors)
   if done%50==0 or done==len(jobs):print(f'{done}/{len(jobs)} reports; {len(errors)} errors; elapsed {time.monotonic()-start:.0f}s',flush=True)
 results.sort(key=lambda x:x['order']);(out/'MER_VIS_report_manifest.json').write_text(json.dumps(results,indent=2,allow_nan=False),encoding='utf8');(out/'MER_VIS_report_errors.json').write_text(json.dumps(errors,indent=2),encoding='utf8')
 summary={'requested':len(records),'completed':len(results),'QI':sum(r['quality_issue'] for r in results),'NoQI':sum(not r['quality_issue'] for r in results),'errors':errors,'elapsed_seconds':round(time.monotonic()-start,1)};(out/'MER_VIS_report_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
