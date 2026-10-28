from pathlib import Path
import csv,json,subprocess,sys,uuid
base=Path('MER_VIS_centre_policy_v3')/'batch_test';base.mkdir(exist_ok=True);science=Path('MER_VIS_review_tool/refit_test_state/synthetic/synthetic.fits').resolve()
row=dict(object_id='test',fits_filename=science.name,fits_path=str(science))
for name,rows in [('catalogue.csv',[row]),('segmentation.csv',[dict(object_id='test',segmentation_area=5000)])]:
 with (base/name).open('w',newline='',encoding='utf8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(base/'references.json').write_text(json.dumps({'test':dict(x=120,y=120,provenance='synthetic_known_centre')}))
out=base/uuid.uuid4().hex
args=[sys.executable,'MER_VIS_review_tool/fit_centred_MER_VIS_geometry.py','--catalogue',str(base/'catalogue.csv'),'--segmentation',str(base/'segmentation.csv'),'--references',str(base/'references.json'),'--output-dir',str(out),'--limit','1','--workers','1']
r=subprocess.run(args,capture_output=True,text=True,timeout=180);assert r.returncode==0,r.stdout+r.stderr
result=json.loads((out/'MER_VIS_centre_constrained_manifest.json').read_text())[0];assert result['codex_fit_status']=='provisional_fit',result.get('codex_error');assert abs(result['codex_fit_centre_x_pix']-120)<1e-9;assert abs(result['codex_fit_centre_y_pix']-120)<1e-9;assert result['centre_reference_provenance']=='synthetic_known_centre';assert result['centre_batch_requires_review'];assert len(result['centre_batch_stages'])>=1
print('PASS: new batch entry point uses explicit references, writes isolated manifests, preserves reference centre, and records free/fixed trial provenance.')
