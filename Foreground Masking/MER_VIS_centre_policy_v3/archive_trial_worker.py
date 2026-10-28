from pathlib import Path
import hashlib,json
base=Path('MER_VIS_centre_policy_v3');jobs=json.loads((base/'jobs.json').read_text());expected=json.loads(Path(jobs[0]['request']).read_text())['worker_sha256'];s=Path('MER_VIS_review_tool/refit_MER_VIS.py').read_text(encoding='utf8')
s=s.replace("                           policy_sha256=hashlib.sha256((HERE/'centre_policy_MER_VIS.py').read_bytes()).hexdigest(),\n",'')
s=s.replace("codex_quality_rule_version='independent_PA_sampling_screens_2026-10-28'","codex_quality_rule_version='manual_centre_existing_screens_2026-10-21'")
s=s.replace("else '+'.join(([\"sparse\"] if len(disc)<6 or span<=0 or gap>.5*span else [])+([\"PA_varies\"] if result['codex_disc_pa_scatter_deg']>10 else [])) or 'adequate_sampling'", "else 'sparse' if len(disc)<6 or span<=0 or gap>.5*span\n                      else 'PA_varies' if result['codex_disc_pa_scatter_deg']>10 else 'adequate_sampling'")
actual=hashlib.sha256(s.encode('utf8')).hexdigest();assert actual==expected,(actual,expected)
(base/'round_output'/'provenance'/f'worker_{actual[:12]}.py').write_text(s,encoding='utf8')
print('Archived exact trial worker source matching recorded hash.')
