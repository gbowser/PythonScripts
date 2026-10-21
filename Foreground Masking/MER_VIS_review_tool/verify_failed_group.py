from pathlib import Path
import urllib.request,json,hashlib
root=Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid\review_MER_VIS');saved=root/'saved_reviews';stage=Path(__file__).resolve().parent
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));url=json.loads((saved/'server.json').read_text())['url'];boot=json.loads(opener.open(url+'api/bootstrap',timeout=8).read());before=json.loads((stage/'before_failed_upgrade.json').read_text())
review=saved/'MER_VIS_saved_reviews.json';assert (hashlib.sha256(review.read_bytes()).hexdigest() if review.exists() else None)==before['reviews_sha256']
assert set(before['ids'])<={r['object_id'] for r in boot['sample']}
failed=[r for r in boot['sample'] if r['category']=='failed'];assert len(failed)==4 and len(boot['sample'])==58
assert {r['object_id'] for r in failed}=={r['object_id'] for r in boot['catalogue'] if r['status']=='fit_failed'}
galaxies=[json.loads(opener.open(url+'api/galaxy?id='+r['object_id'],timeout=8).read()) for r in failed]
assert all(g['centre']==[None,None] and g['fit_error'] and g['original']['disc_pa'] is None for g in galaxies)
(stage/'test_failed_galaxies.json').write_text(json.dumps(galaxies),encoding='utf8')
manifest=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry\MER_VIS_local_geometry_manifest.csv');assert hashlib.sha256(manifest.read_bytes()).hexdigest()=='b874c938391dbfb0c54b82d444d306230b91a6961baf0159b437324075665b85'
report=json.loads((root/'MER_VIS_review_validation.json').read_text());report.update(sample_size=58,failed_galaxies=4,integration_tests_passed=6,saved_review_bytes_preserved=True,previous_sample_ids_preserved=True)
(root/'MER_VIS_review_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('Verified: all 4 failures included; 58 total; prior reviews and source manifest unchanged.')
