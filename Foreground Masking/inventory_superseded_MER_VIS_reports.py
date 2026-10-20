from pathlib import Path
import json
root=Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid\reports').resolve()
old=[]
for name in ['MER_VIS_geometry_explained_2026-10-19','MER_VIS_outcomes_summary_2026-10-19','geometry_manifest_comparison_2026-10-20']:
 p=(root/name).resolve();assert p.parent==root
 old.append(dict(directory=str(p),files=[str(x) for x in p.rglob('*') if x.is_file()]))
Path('MER_VIS_pipeline_v2/superseded_report_inventory.json').write_text(json.dumps(old,indent=2),encoding='utf8');print('Inventoried',sum(len(x['files']) for x in old),'superseded report files; no deletion yet')
