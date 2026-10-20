from pathlib import Path
import csv,json,sys,hashlib
sys.path.insert(0,str(Path(__file__).parent/'review_code'))
from make_MER_VIS_galaxy_report_cards import make_card
base=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid');geo=base/'Euclid_MER_VIS_geometry';out=base/'MER_VIS_galaxy_reports/all_2777_sampling_review';source=geo/'MER_VIS_local_geometry_manifest.csv'
records=json.loads((out/'MER_VIS_report_manifest.json').read_text());byid={r['object_id']:r for r in records};updated=0
for k,r in enumerate(csv.DictReader(source.open(encoding='utf8')),1):
 record=byid[r['object_id']]
 if r['catalogue_name'] or r['codex_fit_status']=='fit_failed':
  fresh=make_card(r,geo/'profiles',out/Path(record['relative_png']).parent,k);record.update(fresh);updated+=1
 for key in ['catalogue_name','catalogue_match_status','catalogue_match_source','catalogue_match_separation_arcsec','catalogue_match_url']:record[key]=r[key]
 record['report_version']='QI_sampling_review_2026-10-20'
 (out/'metadata'/f"{r['object_id']}.json").write_text(json.dumps(record,indent=2,allow_nan=False),encoding='utf8')
 if updated and updated%25==0:print('Updated',updated,flush=True)
(out/'MER_VIS_report_manifest.json').write_text(json.dumps(records,indent=2,allow_nan=False),encoding='utf8')
run=json.loads((out/'MER_VIS_report_run.json').read_text());run.update(sha256=hashlib.sha256(source.read_bytes()).hexdigest(),report_version='QI_sampling_review_2026-10-20');(out/'MER_VIS_report_run.json').write_text(json.dumps(run,indent=2),encoding='utf8');print('Refreshed',updated,'cards')
