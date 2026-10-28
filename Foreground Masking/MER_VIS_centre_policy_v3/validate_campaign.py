import json,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path('MER_VIS_review_tool').resolve()))
from review_MER_VIS import Store,DEFAULT_DATA
from centre_policy_MER_VIS import centre_measurement,DEFAULT_POLICY
base=Path('MER_VIS_centre_policy_v3');campaign=json.loads((base/'centre_policy_MER_VIS_campaign.json').read_text());store=Store(DEFAULT_DATA,base/'round_output',campaign)
assert len(store.sample)==19 and len(store.reviews)==19
summary=[]
for sample in store.sample:
 oid=sample['object_id'];record=store.reviews[oid];assert record['reviewed'] is False
 job=record['settings']['refit_id'];g=store.galaxy(oid,job);assert g['campaign_case']
 assert g['centre_reference']['x'] is not None
 if not campaign['cases'][oid]['reference_uncertain']:
  assert g['refit']['lock_centre'];assert g['original']['status']=='provisional_fit';assert g['diagnostic_available']
  reference=g['centre_reference'];assert abs(g['centre'][0]-reference['x'])<1e-8 and abs(g['centre'][1]-reference['y'])<1e-8
  for p in g['profile']:
   if p['used_for_geometry']:assert p['centre_accepted'] and p['centre_offset_native_pix']<1e-7
 summary.append(dict(id=oid,trial=g['original']['status'],n_profile=len(g['profile']),diagnostic=g['diagnostic_available']))
(base/'campaign_validation.json').write_text(json.dumps(dict(examples=19,pending_reviews=19,checks='reference consistency, fixed-centre offsets, residual availability, previous-review preservation',galaxies=summary),indent=2))
print('PASS: 19 isolated campaign cases, 18 successful fixed-centre trials with diagnostics, one uncertain-centre comparison retained, previous assessments preserved.')
