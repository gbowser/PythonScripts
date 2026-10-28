from pathlib import Path
import json,hashlib,shutil
root=Path('MER_VIS_centre_policy_v3');archive=root/'round_output'/'provenance';archive.mkdir(exist_ok=True)
engine=Path('MER_VIS_review_tool/fit_manual_centre_MER_VIS.py');oldhash=hashlib.sha256(engine.read_bytes()).hexdigest();shutil.copy2(engine,archive/f'fit_engine_{oldhash[:12]}.py')
s=engine.read_text(encoding='utf8').replace('elif dscatter>10:', 'if dscatter>10:');engine.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/refit_MER_VIS.py');s=p.read_text(encoding='utf8');s=s.replace("reference_provenance=payload.get('reference_provenance','manual_selection'),", "reference_provenance=payload.get('reference_provenance','manual_selection'),\n                           policy_sha256=hashlib.sha256((HERE/'centre_policy_MER_VIS.py').read_bytes()).hexdigest(),",1)
s=s.replace("codex_quality_rule_version='manual_centre_existing_screens_2026-10-21'", "codex_quality_rule_version='independent_PA_sampling_screens_2026-10-28'")
s=s.replace("else 'sparse' if len(disc)<6 or span<=0 or gap>.5*span\n                      else 'PA_varies' if result['codex_disc_pa_scatter_deg']>10 else 'adequate_sampling'", "else '+'.join(([\"sparse\"] if len(disc)<6 or span<=0 or gap>.5*span else [])+([\"PA_varies\"] if result['codex_disc_pa_scatter_deg']>10 else [])) or 'adequate_sampling'")
p.write_text(s,encoding='utf8')
# Numerical trial fits are preserved; independent flags are updated explicitly as postprocessing.
post_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
for job in json.loads((root/'jobs.json').read_text()):
 folder=Path(job['request']).parent;p=folder/'result.json';r=json.loads(p.read_text());flags=r.get('codex_quality_flags','').split(';');flags=[x for x in flags if x]
 if float(r.get('codex_disc_axis_ratio') or 0)<=.9 and float(r.get('codex_disc_pa_scatter_deg') or 0)>10 and 'disc_PA_unstable' not in flags:flags.append('disc_PA_unstable')
 r.update(codex_quality_flags=';'.join(flags),codex_quality_rule_version='independent_PA_sampling_screens_2026-10-28',quality_postprocess_sha256=post_hash)
 p.write_text(json.dumps(r,indent=2),encoding='utf8')
 import csv
 manifest=folder/'MER_VIS_manual_refit_manifest.csv'
 with manifest.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(r));w.writeheader();w.writerow(r)
p=Path('MER_VIS_review_tool/app.js');s=p.read_text(encoding='utf8').replace('and a relaxed centre tolerance.', 'and the same centre acceptance rule.').replace("c.face_on?'Informational — nearly face-on exemption':r.sparse_enabled", "c.n_disc<3?'Provisional PA; inclination unavailable':c.face_on?'Informational — nearly face-on exemption':r.sparse_enabled");p.write_text(s,encoding='utf8')
