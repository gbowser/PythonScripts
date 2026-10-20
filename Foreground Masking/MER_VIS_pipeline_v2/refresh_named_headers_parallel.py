from pathlib import Path
import csv,json,sys
from concurrent.futures import ProcessPoolExecutor,as_completed
sys.path.insert(0,str(Path(__file__).parent/'review_code'))
from make_MER_VIS_galaxy_report_cards import make_card
BASE=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid');OUT=BASE/'MER_VIS_galaxy_reports/all_2777_sampling_review';GEO=BASE/'Euclid_MER_VIS_geometry'
def worker(job):
 k,r,relative=job
 return make_card(r,GEO/'profiles',OUT/Path(relative).parent,k)
if __name__=='__main__':
 records=json.loads((OUT/'MER_VIS_report_manifest.json').read_text());byid={r['object_id']:r for r in records};rows=list(csv.DictReader((GEO/'MER_VIS_local_geometry_manifest.csv').open(encoding='utf8')))
 jobs=[(k,r,byid[r['object_id']]['relative_png']) for k,r in enumerate(rows,1) if r['catalogue_name']]
 with ProcessPoolExecutor(max_workers=4) as pool:
  for k,f in enumerate(as_completed([pool.submit(worker,j) for j in jobs]),1):
   fresh=f.result();rec=byid[fresh['object_id']];rec.update(fresh);(OUT/'metadata'/f"{fresh['object_id']}.json").write_text(json.dumps(rec,indent=2),encoding='utf8')
   if k%50==0:print(k,len(jobs),flush=True)
 (OUT/'MER_VIS_report_manifest.json').write_text(json.dumps(records,indent=2),encoding='utf8');print('Named headers finished',len(jobs),flush=True)
