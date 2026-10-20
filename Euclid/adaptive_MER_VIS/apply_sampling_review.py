from pathlib import Path
import csv,json,hashlib,collections,math,shutil
import numpy as np
base=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid');geo=base/'Euclid_MER_VIS_geometry';dest=geo/'MER_VIS_local_geometry_manifest.csv'
backup=Path(__file__).parent/'review_audit';backup.mkdir(exist_ok=True)
shutil.copyfile(dest,backup/'before_sampling_review_manifest.csv')
rows=list(csv.DictReader(dest.open(encoding='utf-8-sig')));changes=[]
for r in rows:
 if r['codex_fit_status']!='provisional_fit':continue
 pp=geo/'profiles'/f"Euclid_{r['object_id']}_MER_VIS_ellipse_profile.csv"
 ps=list(csv.DictReader(pp.open(encoding='utf-8-sig')))
 disc=[z for z in ps if z.get('selected_disc','').lower()=='true' and z.get('used_for_geometry','').lower()=='true']
 assert len(disc)==int(r['codex_n_disc']),(r['object_id'],len(disc),r['codex_n_disc'])
 radii=np.sort([float(z['sma_arcsec']) for z in disc]);span=float(np.ptp(radii));gap=float(np.max(np.diff(radii))) if len(radii)>1 else 0
 ratio=gap/span if span>0 else 1
 prior=r['codex_quality_flags'];flags=[f for f in prior.split(';') if f and f not in ['disc_PA_unstable','disc_PA_sparse_sampling']]
 face=float(r['codex_disc_axis_ratio'])>.9
 sparse=len(disc)<6 or span<=0 or ratio>.5
 if not face:
  if sparse:flags.append('disc_PA_sparse_sampling')
  elif float(r['codex_disc_pa_scatter_deg'])>10:flags.append('disc_PA_unstable')
 r['codex_quality_flags']=';'.join(flags)
 r.update(codex_disc_sampling_n=len(disc),codex_disc_sampling_span_arcsec=span,codex_disc_sampling_max_gap_fraction=ratio,codex_disc_sampling_assessment='face_on_information' if face else 'sparse' if sparse else 'adequate_for_PA_scatter_screen',codex_quality_rule_version='MER_VIS_sampling_review_2026-10-20')
 if prior!=r['codex_quality_flags']:changes.append(dict(object_id=r['object_id'],before=prior,after=r['codex_quality_flags'],n=len(disc),max_gap_fraction=ratio))
keys=list(dict.fromkeys(k for r in rows for k in r))
with dest.open('w',newline='',encoding='utf8') as f:
 w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
sfile=geo/'MER_VIS_v2_summary.json';s=json.loads(sfile.read_text());shutil.copyfile(sfile,backup/'before_sampling_review_summary.json')
fits=[r for r in rows if r['codex_fit_status']=='provisional_fit'];s['flags']=dict(collections.Counter(f for r in fits for f in r['codex_quality_flags'].split(';') if f));s['flag_multiplicity']=dict(collections.Counter(str(len(list(filter(None,r['codex_quality_flags'].split(';'))))) for r in fits));s['source_manifest_sha256']=hashlib.sha256(dest.read_bytes()).hexdigest();s['disc_sampling_rule']='For non-face-on discs, require >=6 selected accepted ellipses and largest radial gap <=50% of span before flagging PA scatter >10 degrees; otherwise flag sparse sampling. Operational thresholds, not calibrated confidence.';sfile.write_text(json.dumps(s,indent=2))
audit=dict(rule=s['disc_sampling_rule'],changed=len(changes),changes=changes,source_sha256=s['source_manifest_sha256']);(geo/'MER_VIS_sampling_review_audit.json').write_text(json.dumps(audit,indent=2));(backup/'sampling_review_audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps(dict(changed=len(changes),flags=s['flags']),indent=2))
