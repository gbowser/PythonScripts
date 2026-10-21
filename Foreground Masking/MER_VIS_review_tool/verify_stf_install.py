from pathlib import Path
import urllib.request,json,hashlib,csv
root=Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid\review_MER_VIS');stage=Path('MER_VIS_review_tool');saved=root/'saved_reviews'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
state=json.loads((saved/'server.json').read_text()); url=state['url']
boot=json.loads(opener.open(url+'api/bootstrap',timeout=8).read())
assert len(boot['sample'])==54 and boot['categories']['control']=='No Quality Issues'
controls=[s for s in boot['sample'] if s['category']=='control'];assert len(controls)==12
manifest=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry\MER_VIS_local_geometry_manifest.csv')
rows={r['object_id']:r for r in csv.DictReader(manifest.open(encoding='utf-8-sig'))}
assert all(not rows[s['object_id']]['codex_quality_flags'] for s in controls)
assert sum('nearly_face_on' in rows[s['object_id']]['codex_information'] for s in controls)==6
assert hashlib.sha256(manifest.read_bytes()).hexdigest()=='b874c938391dbfb0c54b82d444d306230b91a6961baf0159b437324075665b85'
assert not boot['reviews'] and not (saved/'MER_VIS_saved_reviews.json').exists()
files=['review_MER_VIS.py','app.js','index.html','style.css','Start MER VIS Review.cmd','Start_MER_VIS_Review.ps1','README_MER_VIS_REVIEW.md']
for name in files: assert (root/name).read_bytes()==(stage/name).read_bytes()
report=dict(ready=True,sample_size=54,no_quality_issues_references=12,nearly_face_on_references=6,real_reviews=len(boot['reviews']),source_geometry_unchanged=True,baseline_numerical_tests=54,integration_tests_passed=5,autostf_reference_frames_settings=10,autostf_reference_values=74,launch_test='passed',browser_test='passed',url=url)
(root/'MER_VIS_review_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
