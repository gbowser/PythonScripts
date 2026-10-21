from pathlib import Path
import json,time,hashlib
from review_MER_VIS import Store,DEFAULT_DATA
folder=Path(__file__).resolve().parent/'refit_test_state'/'real_galaxy';folder.mkdir(parents=True,exist_ok=True)
store=Store(DEFAULT_DATA,folder);oid='-586374330510251740';source=Path(store.byid[oid]['fits_path']);before=hashlib.sha256(source.read_bytes()).hexdigest()
job=store.start_refit(dict(object_id=oid,x=844.,y=870.,lock_centre=True));print('Started example centre retry',job['job_id'],flush=True)
for i in range(200):
 time.sleep(1);status=store.refit_status(job['job_id'])
 if status['status']!='running':break
 if i%15==0:print('Still fitting',i+1,'seconds',flush=True)
assert status['status']=='complete',status
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
assert hashlib.sha256(store.manifest.read_bytes()).hexdigest()==store.digest
g=status['galaxy'];assert g['pipeline_original']['status']=='fit_failed';assert g['refit']['x']==844 and g['refit']['lock_centre']
if g['original']['status']=='provisional_fit':
 assert abs(g['centre'][0]-844)<1e-8 and abs(g['centre'][1]-870)<1e-8
 assert any(p['selected_disc'] for p in g['profile'])
 raw=json.loads((folder/'refits'/job['job_id']/'result.json').read_text());assert raw['codex_disc_sampling_n']==g['original']['n_disc'];assert raw['codex_disc_sampling_assessment']=='sparse';assert raw['manual_fit_centre_ra_deg']>0
 expected=(g['original']['disc_pa']-g['euclid']['disc_pa']+90)%180-90;assert abs(raw['disc_vs_detection_pa_difference_deg']-expected)<1e-9
 assert Store(DEFAULT_DATA,folder).galaxy(oid)['latest_refit_id']==job['job_id']
else:assert g['centre']==[None,None]
(folder/'returned_galaxy.json').write_text(json.dumps(g),encoding='utf8')
print(json.dumps(dict(status=g['original']['status'],geometry=g['original'],error=g['fit_error'],profile_rows=len(g['profile'])),indent=2),flush=True)
# The original endpoint remains unchanged even after a completed retry.
assert store.galaxy(oid)['original']['status']=='fit_failed'
for bad in [dict(object_id=oid,x=-1,y=2),dict(object_id=oid,x=float('nan'),y=2),dict(object_id='unknown',x=2,y=2)]:
 try:store.start_refit(bad)
 except (ValueError,KeyError):pass
 else:raise AssertionError('Bad centre accepted')
print('PASS: async refit, locked centre, baseline comparison, profile refresh, invalid inputs and read-only sources.',flush=True)

