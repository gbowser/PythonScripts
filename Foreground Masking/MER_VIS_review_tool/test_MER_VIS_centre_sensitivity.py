"""Read-only sensitivity experiment: isolated fixed-centre trials at +/-1 native pixel.

Does not update saved reviews, latest-refit indexes or master geometry. The offsets
are probes of numerical sensitivity, not calibrated centre errors.
"""
import argparse, contextlib, hashlib, json, time, uuid
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

TARGETS=['2681494150647395085','-524824554283124036','-599118107493216367',
         '-537890362287224823','-663928688473758026']

def one(task):
    source, root, output, oid, label, dx, dy = task
    from refit_MER_VIS import worker
    review=source[oid]; old=Path(root)/'refits'/review['settings']['refit_id']
    request=json.loads((old/'request.json').read_text(encoding='utf8'))
    folder=Path(output)/'trials'/oid/label;folder.mkdir(parents=True,exist_ok=True)
    if (folder/'result.json').exists():
        return dict(id=oid,probe=label,folder=str(folder),cached=True)
    request['row']['manual_centre_x_pix']=review['centre_reference_x_pix']+dx
    request['row']['manual_centre_y_pix']=review['centre_reference_y_pix']+dy
    request.update(lock_centre=True,reference_provenance='sensitivity_probe_not_adopted',
                   requested_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                   engine_sha256=hashlib.sha256(Path(__file__).with_name('fit_manual_centre_MER_VIS.py').read_bytes()).hexdigest(),
                   worker_sha256=hashlib.sha256(Path(__file__).with_name('refit_MER_VIS.py').read_bytes()).hexdigest(),
                   sensitivity_offset_native_pix=[dx,dy],baseline_review_refit=review['settings']['refit_id'])
    (folder/'request.json').write_text(json.dumps(request,indent=2),encoding='utf8')
    try:
        with (folder/'console.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
            worker(folder/'request.json')
        result=json.loads((folder/'result.json').read_text())
        return dict(id=oid,probe=label,folder=str(folder),status=result['codex_fit_status'])
    except Exception as exc:
        return dict(id=oid,probe=label,folder=str(folder),error=f'{type(exc).__name__}: {exc}')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reviews',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--workers',type=int,default=2);a=p.parse_args()
    source=json.loads((a.reviews/'MER_VIS_saved_reviews.json').read_text());a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'source_reviews.json').write_text(json.dumps(source,indent=2))
    tasks=[(source,str(a.reviews),str(a.output),oid,label,dx,dy) for oid in TARGETS
           for label,dx,dy in [('xminus',-1,0),('xplus',1,0),('yminus',0,-1),('yplus',0,1)]]
    done=[]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for f in as_completed([pool.submit(one,t) for t in tasks]):
            done.append(f.result());(a.output/'progress.json').write_text(json.dumps(done,indent=2))
            print(f'[{len(done)}/{len(tasks)}] {done[-1]}',flush=True)
    (a.output/'sensitivity_trials.json').write_text(json.dumps(done,indent=2))

if __name__=='__main__':main()
