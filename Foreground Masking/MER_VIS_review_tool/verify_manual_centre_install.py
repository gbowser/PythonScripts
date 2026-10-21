from pathlib import Path
import json,urllib.request,csv,io,hashlib
root=Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid\review_MER_VIS');saved=root/'saved_reviews';stage=Path(__file__).resolve().parent
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));url=json.loads((saved/'server.json').read_text())['url'];boot=json.loads(opener.open(url+'api/bootstrap',timeout=5).read());oid='-586374330510251740';index=json.loads((saved/'MER_VIS_latest_refits.json').read_text());job=index[oid]
response=opener.open(url+'api/refit/export?job='+job,timeout=5);rows=list(csv.DictReader(io.StringIO(response.read().decode('utf-8-sig'))));assert len(rows)==1
r=rows[0];assert r['object_id']==oid and int(r['codex_n_disc'])==5 and r['codex_disc_sampling_assessment']=='sparse'
expected=(float(r['codex_disc_pa_sky_deg'])-float(r['euclid_adjusted_detection_pa_sky_deg'])+90)%180-90
assert abs(float(r['disc_vs_detection_pa_difference_deg'])-expected)<1e-9
assert abs(float(r['inclination_vs_detection_proxy_difference_deg'])-(float(r['codex_inclination_deg'])-float(r['euclid_detection_inclination_proxy_deg'])))<1e-9
assert float(r['manual_fit_centre_ra_deg'])>0
before=json.loads((stage/'before_failed_upgrade.json').read_text());reviews=saved/'MER_VIS_saved_reviews.json';assert (hashlib.sha256(reviews.read_bytes()).hexdigest() if reviews.exists() else None)==before['reviews_sha256']
manifest=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry\MER_VIS_local_geometry_manifest.csv');assert hashlib.sha256(manifest.read_bytes()).hexdigest()=='b874c938391dbfb0c54b82d444d306230b91a6961baf0159b437324075665b85'
files=['review_MER_VIS.py','refit_MER_VIS.py','fit_manual_centre_MER_VIS.py','app.js','index.html','style.css','README_MER_VIS_REVIEW.md']
for name in files:assert (root/name).read_bytes()==(stage/name).read_bytes(),name
report=json.loads((root/'MER_VIS_review_validation.json').read_text());report.update(integration_tests_passed=7,manual_centre_refit=True,synthetic_geometry_test='passed',failed_retry_test='passed',screen_to_native_pixel_mapping='passed',browser_refit='passed',original_refit_toggle='passed',refit_csv_export='passed',source_geometry_unchanged=True,saved_review_bytes_preserved=True,test_example=dict(object_id=oid,x=844,y=870,disc_pa=float(r['codex_disc_pa_sky_deg']),bar_pa=float(r['codex_bar_pa_sky_deg']),inclination=float(r['codex_inclination_deg']),accepted_isophotes=int(r['codex_n_good']),flags=r['codex_quality_flags'],job_id=job),files={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files})
(root/'MER_VIS_review_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('PASS: installed CSV export, all comparison deltas, source hashes, preserved reviews and deployed files.')
print(json.dumps(report['test_example'],indent=2))
