from pathlib import Path
import json,hashlib
p=Path('MER_VIS_review_tool/fit_manual_centre_MER_VIS.py');s=p.read_text(encoding='utf8').replace('min_cut=float(np.percentile(finite_data,2)),max_cut=float(np.percentile(finite_data,99.7))','vmin=float(np.percentile(finite_data,2)),vmax=float(np.percentile(finite_data,99.7))');p.write_text(s,encoding='utf8')
engine=hashlib.sha256(p.read_bytes()).hexdigest()
for job in json.loads(Path('MER_VIS_centre_policy_v3/jobs.json').read_text()):
 path=Path(job['request']);doc=json.loads(path.read_text());doc['engine_sha256']=engine;path.write_text(json.dumps(doc,indent=2),encoding='utf8')
