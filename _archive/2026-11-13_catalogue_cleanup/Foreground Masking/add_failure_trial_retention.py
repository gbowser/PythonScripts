from pathlib import Path
p=Path('MER_VIS_pipeline_v2/fit_adaptive_MER_VIS_geometry.py');s=p.read_text(encoding='utf-8-sig')
s=s.replace("VERSION='MER_VIS_adaptive_v2_2026-10-20'","VERSION='MER_VIS_adaptive_v2_recovery_2026-10-20'")
s=s.replace("if len(good)>len(best_good):best=p;best_good=good;chosen=", "if len(good)>len(best_good) or (len(good)==len(best_good)==0 and (sum(accepted(z,True) for z in p),len(p))>(sum(accepted(z,True) for z in best),len(best))):best=p;best_good=good;chosen=")
# This recovery preserves a diagnostic candidate even when none passed strict cuts.
Path('MER_VIS_pipeline_v2/recover_failed_MER_VIS_geometry.py').write_text(s,encoding='utf8')
p=Path('MER_VIS_pipeline_v2/finalize_MER_VIS_geometry.py');s=p.read_text(encoding='utf-8-sig')
needle="old={r['object_id']:r for r in csv.DictReader(a.baseline.open(encoding='utf-8-sig'))};assert"
repl="""old={r['object_id']:r for r in csv.DictReader(a.baseline.open(encoding='utf-8-sig'))}
# Retry only failed targets, retaining trial profiles with zero strict samples so
# explicitly relaxed recovery has actual samples to assess. Successful fits unchanged.
from recover_failed_MER_VIS_geometry import measure as recover
segpath=Path(__file__).parent.parent/'datalabs_MER_VIS'/'MER_VIS_datalabs_manifest.csv'
seg={z['object_id']:z.get('segmentation_area','') for z in csv.DictReader(segpath.open(encoding='utf-8-sig'))}
retried=[]
for i,r in enumerate(rows):
 if r['codex_fit_status']=='fit_failed':
  updated=recover((r,str(Path(r['fits_path']).parent),str(a.geometry_dir),seg.get(r['object_id'])))
  retried.append(dict(object_id=r['object_id'],before=r['codex_error'],after_status=updated['codex_fit_status'],after_error=updated['codex_error']))
  rows[i]=updated
(a.geometry_dir/'MER_VIS_failed_recovery_audit.json').write_text(json.dumps(dict(retry_script_sha256=hashlib.sha256((Path(__file__).parent/'recover_failed_MER_VIS_geometry.py').read_bytes()).hexdigest(),targets=retried),indent=2))
assert"""
s=s.replace(needle,repl);p.write_text(s,encoding='utf8')
