import json
from pathlib import Path
p=Path('MER_VIS_centre_recheck_20261028/centre_acceptance_audit.json');d=json.loads(p.read_text());focus={'-663928688473758026','2756030807655229287','-595029565493921205','-537890362287224823'}
for r in d['galaxies']:
 if r['id'] in focus:
  disc=[p for p in r['selected'] if p['selected_disc']];trial=r['trials'][1]
  print(json.dumps({'id':r['id'],'decision':r['reviewed_decisions']['disc'],'N':r['current']['n_disc'],'RMS':r['current']['pa_scatter'],'PA':r['current']['disc_pa'],'inclination':r['current']['inclination'],'disc_offset_arcsec':[round(p['offset_arcsec'],3) for p in disc],'disc_fraction_percent':[round(p['offset_fraction_radius']*100,1) for p in disc],'ellipse_PAs':[round(p['PA'],2) for p in disc],'ellipticities':[round(p['ellipticity'],3) for p in disc],'trialN':trial['final']['n_disc'],'trialRMS':trial['final']['pa_scatter'],'trialPA':trial['final']['disc_pa']},ensure_ascii=False))
print('Offsets above .3 arcsec:',sum(p['offset_arcsec']>.3 for r in d['galaxies'] for p in r['selected'] if p['selected_disc']), 'of',sum(r['current']['n_disc'] for r in d['galaxies']))
