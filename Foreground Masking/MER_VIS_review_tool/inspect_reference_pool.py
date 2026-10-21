import csv,json,collections
from pathlib import Path
rows=list(csv.DictReader(open(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry\MER_VIS_local_geometry_manifest.csv',encoding='utf8')));byid={r['object_id']:r for r in rows};sample=json.loads(Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid\review_MER_VIS\saved_reviews\MER_VIS_review_sample.json').read_text())['sample'];used={r['object_id'] for r in sample}
control=[r for r in sample if r['category']=='control'];eligible=[r for r in rows if r['codex_fit_status']=='provisional_fit' and not r['codex_quality_flags'] and r['cutout_partial'].lower()!='true'];face=lambda r:'nearly_face_on' in r.get('codex_information','')
print('Current references',[(r['object_id'],face(byid[r['object_id']])) for r in control]);print('Available new references',collections.Counter('face_on' if face(r) else 'inclined' for r in eligible if r['object_id'] not in used))
