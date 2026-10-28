import csv,hashlib,json,shutil,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path('MER_VIS_review_tool').resolve()))
from review_MER_VIS import Store,DEFAULT_DATA,LocalReviewServer,Handler
base=Path('MER_VIS_centre_policy_v3');campaign=json.loads((base/'centre_policy_MER_VIS_campaign.json').read_text());source=Path(campaign['original_output'])/'MER_VIS_saved_reviews.json';before=hashlib.sha256(source.read_bytes()).hexdigest();oid=campaign['sample'][0]['object_id'];pending=json.loads((base/'round_output'/'MER_VIS_saved_reviews.json').read_text())[oid];job=pending['settings']['refit_id']
with tempfile.TemporaryDirectory(prefix='MER_VIS_centre_round_') as tmp:
 out=Path(tmp);shutil.copytree(base/'round_output'/'refits'/job,out/'refits'/job)
 store=Store(DEFAULT_DATA,out,campaign);result=store.save(dict(object_id=oid,disc_decision='uncertain',bar_decision='convincing',centre_decision='looks_correct',rule_action='keep',notes='QA: separate round only',settings=pending['settings'],calculation=dict(n_disc=3,n_bar=5,disc_pa=61.3,inclination=27.1,disc_pa_provisional=False,centre_rejected_disc=[],centre_rejected_bar=[])))
 saved=result['review'];assert saved['review_campaign']==campaign['campaign_id'];assert saved['centre_policy_version']==campaign['policy_version'];assert saved['centre_reference_x_pix']==campaign['cases'][oid]['reference_centre'][0];assert saved['centre_screen_enabled'] is True
 resumed=Store(DEFAULT_DATA,out,campaign);assert resumed.reviews[oid]['notes']=='QA: separate round only';assert resumed.galaxy(oid,job)['previous_review']==campaign['previous_reviews'][oid]
 with (out/'MER_VIS_saved_reviews.csv').open(encoding='utf-8-sig') as f:row=next(csv.DictReader(f));assert row['review_campaign']==campaign['campaign_id'];assert row['centre_policy_version']==campaign['policy_version']
 assert hashlib.sha256(source.read_bytes()).hexdigest()==before
server=LocalReviewServer(('127.0.0.1',0),Handler);port=server.server_port
try:
 try:collision=LocalReviewServer(('127.0.0.1',port),Handler)
 except OSError:pass
 else:collision.server_close();raise AssertionError('Review rounds must not share a socket')
finally:server.server_close()
print('PASS: new-round assessment save/resume/export preserves centre provenance and previous notes; original reviews unchanged; exclusive port isolation verified.')
