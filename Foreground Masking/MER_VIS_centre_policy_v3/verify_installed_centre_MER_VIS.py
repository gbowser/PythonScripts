from pathlib import Path
import hashlib,json,urllib.request
root=Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid\review_MER_VIS');source=Path('MER_VIS_review_tool');campaign=json.loads((root/'centre_policy_MER_VIS_campaign.json').read_text());install=json.loads((root/'centre_policy_MER_VIS_installation.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'saved_reviews'/'MER_VIS_saved_reviews.json')==campaign['source_review_sha256']
assert sha(Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry\MER_VIS_local_geometry_manifest.csv'))==campaign['source_manifest_sha256']
for name in install['installed_files']:assert sha(root/name)==sha(source/name),name
state=json.loads((root/'saved_reviews_centre_v3'/'server.json').read_text())
with urllib.request.urlopen(state['url']+'api/bootstrap') as f:boot=json.load(f)
assert len(boot['sample'])==19 and not any(r.get('reviewed',True) for r in boot['reviews'].values());assert boot['campaign']['campaign_id']==campaign['campaign_id']
install.update(installed_files={name:sha(root/name) for name in install['installed_files']},url=state['url'],numeric_cross_language_vectors=35,synthetic_fit='passed',batch_entry_test='passed',review_persistence_tests='passed',API_security_tests='passed',campaign_cases_checked=19,successful_new_fixed_centre_fits=18,residual_PNGs=18,old_reviews_and_master_unchanged=True,browser_automation='unavailable; API, SVG generation and diagnostic images checked')
(root/'centre_policy_MER_VIS_installation.json').write_text(json.dumps(install,indent=2),encoding='utf8')
# Shut down only the temporary QA server; leave both user-facing rounds available.
with urllib.request.urlopen('http://127.0.0.1:8788/api/bootstrap') as f:qa=json.load(f)
req=urllib.request.Request('http://127.0.0.1:8788/api/stop',data=b'{}',headers={'Content-Type':'application/json','X-Review-Token':qa['token']})
with urllib.request.urlopen(req) as f:assert json.load(f)['stopped']
print(json.dumps(dict(ready=True,url=state['url'],pending_reviews=19,old_reviews_unchanged=True,source_geometry_unchanged=True,temporary_QA_server_stopped=True)))
