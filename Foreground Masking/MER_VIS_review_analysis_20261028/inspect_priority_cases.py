import json
from pathlib import Path
rows=json.loads(Path('MER_VIS_review_analysis_20261028/review_audit.json').read_text())['galaxies']
for r in rows:
 if r['decisions']['disc']=='usable' and r['final']['pa_scatter'] is not None and r['final']['pa_scatter']>10:
  print(json.dumps({'id':r['id'],'n':r['final']['n_disc'],'RMS':r['final']['pa_scatter'],'face_on':r['final']['face_on'],'PA':r['final']['disc_pa'],'inc':r['final']['inclination'],'issues':r['final']['issues'],'notes':r['notes']}))
print('UNCERTAIN')
for r in rows:
 if 'uncertain' in r['decisions'].values():print(json.dumps({'id':r['id'],'decisions':r['decisions'],'notes':r['notes']}))
