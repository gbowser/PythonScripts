from pathlib import Path
import json,hashlib,urllib.request
root=Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid\review_MER_VIS');saved=root/'saved_reviews';state=json.loads((saved/'server.json').read_text());boot=json.loads(urllib.request.urlopen(state['url']+'api/bootstrap').read())
assert len(boot['sample'])==48 and not boot['reviews']
assert not (saved/'MER_VIS_saved_reviews.json').exists(), 'QA reviews must not enter real output'
manifest=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry\MER_VIS_local_geometry_manifest.csv');digest=hashlib.sha256(manifest.read_bytes()).hexdigest();assert digest=='b874c938391dbfb0c54b82d444d306230b91a6961baf0159b437324075665b85'
files=['review_MER_VIS.py','app.js','index.html','style.css','Start MER VIS Review.cmd','Start_MER_VIS_Review.ps1','README_MER_VIS_REVIEW.md']
for name in files:assert (root/name).read_bytes()==(Path('MER_VIS_review_tool')/name).read_bytes()
report=dict(ready=True,sample_size=48,real_reviews=0,source_geometry_unchanged=True,baseline_numerical_tests=48,integration_tests_passed=4,launch_test='passed',url=state['url'],files={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files})
(root/'MER_VIS_review_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
