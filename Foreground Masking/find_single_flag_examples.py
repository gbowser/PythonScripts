import csv,collections,json
from pathlib import Path
base=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid')
rows=list(csv.DictReader(open(base/'Euclid_MER_VIS_geometry/MER_VIS_local_geometry_manifest.csv',encoding='utf-8-sig')))
groups=collections.defaultdict(list)
for r in rows:
 fs=set(filter(None,r['codex_quality_flags'].split(';')))
 original=fs.copy()
 if 'nearly_face_on_PA_uncertain' in fs:fs.discard('disc_PA_unstable')
 fs.discard('nearly_face_on_PA_uncertain')
 if r['codex_fit_status']=='provisional_fit' and len(fs)==1 and r['cutout_partial'].lower()!='true':groups[next(iter(fs))].append(r)
 if r['codex_fit_status']=='fit_failed':
  if 'Insufficient bar/disc' in r['codex_error']:groups['failed_interval'].append(r)
  elif 'reliable isophotes' in r['codex_error']:groups['failed_short'].append(r)
print({k:len(v) for k,v in groups.items()})
Path('MER_VIS_summary_build/example_candidates.json').write_text(json.dumps(groups),encoding='utf-8')
