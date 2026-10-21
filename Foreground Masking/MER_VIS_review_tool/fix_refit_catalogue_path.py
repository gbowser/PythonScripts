from pathlib import Path
p=Path('MER_VIS_review_tool/refit_MER_VIS.py');s=p.read_text(encoding='utf8');s=s.replace("            segpath = HERE.parent / 'datalabs_MER_VIS' / 'MER_VIS_datalabs_manifest.csv'", "            candidates=[HERE.parent/'datalabs_MER_VIS'/'MER_VIS_datalabs_manifest.csv', HERE.parent.parent/'Euclid'/'datalabs_MER_VIS'/'MER_VIS_datalabs_manifest.csv']\n            segpath=next((p for p in candidates if p.exists()),candidates[0])")
p.write_text(s,encoding='utf8')
