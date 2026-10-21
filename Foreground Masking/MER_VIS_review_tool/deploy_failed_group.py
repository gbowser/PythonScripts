from pathlib import Path
import json,urllib.request,shutil,re,hashlib
stage=Path(__file__).resolve().parent;root=Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid\review_MER_VIS');saved=root/'saved_reviews'
reviews=saved/'MER_VIS_saved_reviews.json';before=hashlib.sha256(reviews.read_bytes()).hexdigest() if reviews.exists() else None
sample=json.loads((saved/'MER_VIS_review_sample.json').read_text())['sample']
(stage/'before_failed_upgrade.json').write_text(json.dumps(dict(reviews_sha256=before,ids=[s['object_id'] for s in sample])))
state=json.loads((saved/'server.json').read_text());url=state['url'];assert re.fullmatch(r'http://127\.0\.0\.1:\d+/',url)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try: boot=json.loads(opener.open(url+'api/bootstrap',timeout=5).read())
except OSError: boot=None
if boot:
 assert Path(boot['output']).resolve()==saved.resolve() and boot['app']=='MER_VIS_sample_review_v1'
 req=urllib.request.Request(url+'api/stop',data=b'{}',headers={'Origin':url.rstrip('/'),'X-Review-Token':boot['token'],'Content-Type':'application/json'})
 opener.open(req,timeout=5).read()
for name in ['review_MER_VIS.py','app.js','README_MER_VIS_REVIEW.md','test_review_MER_VIS.py']:
 shutil.copy2(stage/name,root/name)
print('Installed failed-galaxy group; previous review fingerprints recorded.')
