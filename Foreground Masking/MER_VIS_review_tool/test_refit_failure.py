from pathlib import Path
import json,subprocess,sys
base=Path(__file__).resolve().parent;source=base/'refit_test_state/synthetic/request.json';r=json.loads(source.read_text());out=base/'refit_test_state/failed_centre';out.mkdir(parents=True,exist_ok=True)
r['row'].update(manual_centre_x_pix=0.,manual_centre_y_pix=0.,codex_disc_pa_sky_deg=77,codex_inclination_deg=66,codex_n_disc=20,codex_bar_pa_sky_deg=55,disc_vs_detection_pa_difference_deg=44)
(out/'request.json').write_text(json.dumps(r));p=subprocess.run([sys.executable,str(base/'refit_MER_VIS.py'),str(out/'request.json')],capture_output=True,text=True,timeout=100);assert p.returncode==0,p.stderr
result=json.loads((out/'result.json').read_text());assert result['codex_fit_status']=='fit_failed'
for k in ['codex_disc_pa_sky_deg','codex_bar_pa_sky_deg','codex_inclination_deg','codex_fit_centre_x_pix','disc_vs_detection_pa_difference_deg']:assert result.get(k,'')=='',k
assert result['codex_disc_sampling_assessment']=='fit_failed'
print('PASS: failed centre retry suppresses old angles, centres and differences; records failure reason:',result['codex_error'])
