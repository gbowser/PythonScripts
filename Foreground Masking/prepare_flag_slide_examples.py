import json,csv
from pathlib import Path
from PIL import Image
base=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid'); root=Path('MER_VIS_summary_build');out=root/'examples';out.mkdir(exist_ok=True)
g=json.loads((root/'example_candidates.json').read_text());idx={r['object_id']:r for r in csv.DictReader(open(base/'MER_VIS_galaxy_reports/all_2777/MER_VIS_report_review_index.csv',encoding='utf-8-sig'))}
keys=['small_bar_sensitive_to_resolution','disc_PA_unstable','disc_axis_ratio_unstable','bar_PA_unstable','weak_ellipse_bar_signature','failed_interval','failed_short']
selected=[]
def num(r,k):
 try:return float(r[k])
 except:return 0
for key in keys:
 pool=g[key]
 # Prefer original singleton flags and full coverage, so examples need no reinterpretation.
 pool=sorted(pool,key=lambda r:(len(list(filter(None,r['codex_quality_flags'].split(';'))))!=1,r['cutout_partial'].lower()=='true'))
 if key=='failed_short':pool=sorted(pool,key=lambda r:('Only 8 ' not in r['codex_error'] and 'Only 9 ' not in r['codex_error'],r['cutout_partial'].lower()=='true'))
 picks=pool[:2];examples=[]
 for r in picks:
  oid=r['object_id'];source=base/'MER_VIS_galaxy_reports/all_2777'/idx[oid]['png'];im=Image.open(source);im.crop((50,230,1950,1080)).save(out/f'{oid}.png')
  profile=base/'Euclid_MER_VIS_geometry/profiles'/f'Euclid_{oid}_MER_VIS_ellipse_profile.csv'
  pr=list(csv.DictReader(open(profile))) if profile.exists() else []
  good=[z for z in pr if z['valid'].lower()=='true' and z['stop_code']=='0' and num(z,'sampled_fraction')>=.7 and num(z,'intensity')>0 and num(z,'intensity')>5*max(num(z,'intensity_error'),1e-12)]
  if key=='small_bar_sensitive_to_resolution':detail=f"Bar interval upper bound: {num(r,'codex_bar_max_arcsec'):.2f} arcsec (threshold <1.5)."
  elif key in ['disc_PA_unstable','bar_PA_unstable']:detail=f"{'Disc' if key.startswith('disc') else 'Bar'} PA radial scatter: {num(r,'codex_disc_pa_scatter_deg' if key.startswith('disc') else 'codex_bar_pa_scatter_deg'):.1f}° (threshold >10°)."
  elif key=='disc_axis_ratio_unstable':
   q=[num(z,'ellipticity') for z in good if num(r,'codex_disc_min_arcsec')<=num(z,'sma_arcsec')<=num(r,'codex_disc_max_arcsec')];detail=f"Disc ellipticity span: {max(q)-min(q):.3f} (threshold >0.15)."
  elif key=='weak_ellipse_bar_signature':
   import statistics
   q=[num(z,'ellipticity') for z in good if num(r,'codex_bar_min_arcsec')<=num(z,'sma_arcsec')<=num(r,'codex_bar_max_arcsec')];detail=f"Median bar ellipticity: {statistics.median(q):.3f} (threshold <0.25)."
  else:detail=r['codex_error'].replace('ValueError: ','')+f'. Reliable ellipses overall: {len(good)}.'
  examples.append(dict(id=oid,image=f'examples/{oid}.png',detail=detail,original_flags=r['codex_quality_flags'],source=str(source),partial=r['cutout_partial']))
 selected.append(dict(key=key,examples=examples))
(root/'example_selection.json').write_text(json.dumps(selected,indent=2),encoding='utf-8');print(json.dumps(selected,indent=2))


