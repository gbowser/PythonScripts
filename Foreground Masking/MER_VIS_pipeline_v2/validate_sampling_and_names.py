from pathlib import Path
import csv,json,hashlib,math
base=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid');manifest=base/'Euclid_MER_VIS_geometry/MER_VIS_local_geometry_manifest.csv';current=list(csv.DictReader(manifest.open(encoding='utf8')));before={r['object_id']:r for r in csv.DictReader(open('MER_VIS_pipeline_v2/review_audit/before_sampling_review_manifest.csv',encoding='utf8'))}
for r in current:
 b=before[r['object_id']]
 for k in ['codex_disc_pa_sky_deg','codex_bar_pa_sky_deg','codex_inclination_deg','codex_fit_centre_x_pix','codex_fit_centre_y_pix','codex_fit_status','codex_bar_status','euclid_adjusted_detection_pa_sky_deg']:
  assert r[k]==b[k],(r['object_id'],k)
 if r['catalogue_name']:assert r['catalogue_match_status']=='secure_positional_match' and float(r['catalogue_match_separation_arcsec'])<=2
 flags=r['codex_quality_flags'].split(';');assert not ('disc_PA_sparse_sampling' in flags and 'disc_PA_unstable' in flags)
 if 'disc_PA_unstable' in flags:assert int(r['codex_disc_sampling_n'])>=6 and float(r['codex_disc_sampling_max_gap_fraction'])<=.5 and float(r['codex_disc_pa_scatter_deg'])>10
 if 'nearly_face_on' in r['codex_information']:assert 'disc_PA_unstable' not in flags and 'disc_PA_sparse_sampling' not in flags
assert len(current)==2777
names=[r for r in current if r['catalogue_name']];assert len(names)==227
records=json.loads((base/'MER_VIS_galaxy_reports/all_2777_sampling_review/MER_VIS_report_manifest.json').read_text());byid={r['object_id']:r for r in records}
for r in current:assert byid[r['object_id']]['catalogue_name']==r['catalogue_name']
result=dict(targets=len(current),angles_centres_and_fit_status_unchanged=True,sparse_and_variation_flags_mutually_exclusive=True,face_on_exempt=True,catalogue_annotations=227,manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest())
Path('MER_VIS_pipeline_v2/review_audit/review_consistency_checks.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
