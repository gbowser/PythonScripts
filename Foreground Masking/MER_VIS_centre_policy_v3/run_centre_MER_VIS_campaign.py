import concurrent.futures,json,os,subprocess,sys,time
from pathlib import Path
base=Path(__file__).resolve().parent;app=base.parent/'MER_VIS_review_tool';jobs=json.loads((base/'jobs.json').read_text());started=time.monotonic()
def run(job):
 folder=Path(job['request']).parent;env=dict(os.environ);env['MPLCONFIGDIR']=str(folder/'mplconfig')
 try:
  with (folder/'worker.log').open('w',encoding='utf8') as log:
   p=subprocess.run([sys.executable,str(app/'refit_MER_VIS.py'),job['request']],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=240,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  if p.returncode:raise RuntimeError('Worker exit '+str(p.returncode))
  result=json.loads((folder/'result.json').read_text());status=dict(job_id=job['job'],object_id=job['object_id'],status='complete',message='Centre-policy trial complete; visual review required')
  summary=dict(id=job['object_id'],status=result['codex_fit_status'],method=result.get('codex_method'),n_disc=result.get('codex_n_disc'),n_bar=result.get('codex_n_bar'),error=result.get('codex_error'),diagnostic=bool(result.get('centre_diagnostic_png')),diagnostic_error=result.get('centre_diagnostic_error'))
 except Exception as e:status=dict(job_id=job['job'],object_id=job['object_id'],status='error',message=str(e));summary=dict(id=job['object_id'],status='worker_error',error=str(e))
 (folder/'status.json').write_text(json.dumps(status,indent=2),encoding='utf8');print(json.dumps(summary),flush=True);return summary
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for result in pool.map(run,jobs):results.append(result)
(base/'trial_run_summary.json').write_text(json.dumps(dict(seconds=time.monotonic()-started,results=results),indent=2),encoding='utf8');print('Campaign trials finished',flush=True)
