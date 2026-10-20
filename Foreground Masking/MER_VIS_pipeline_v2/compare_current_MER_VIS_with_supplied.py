from pathlib import Path
import pandas as pd,numpy as np,json,hashlib
out=Path(__file__).parent/'current_report'/'comparison';out.mkdir(exist_ok=True,parents=True)
a_path=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry\MER_VIS_local_geometry_manifest.csv');b_path=Path(r'C:\Users\gordo\Downloads\Euclid_VIS_disc_bar_PA_manifest.csv')
a=pd.read_csv(a_path,dtype={'object_id':str});b=pd.read_csv(b_path,dtype={'object_id':str});m=a.merge(b,on='object_id',how='outer',indicator=True,suffixes=('_codex','_supplied'),validate='one_to_one')
def num(c):return pd.to_numeric(m[c],errors='coerce')
def axial(x,y):return (x-y+90)%180-90
m['disc_PA_delta_deg']=axial(num('codex_disc_pa_sky_deg'),num('disc_PA_deg'));m['bar_PA_delta_deg']=axial(num('codex_bar_pa_sky_deg'),num('bar_PA_deg'));m['inclination_delta_deg']=num('codex_inclination_deg')-num('inclination_deg')
flags=m.codex_quality_flags.fillna('').str.split(';').apply(lambda xs:set(x for x in xs if x))
m['codex_revised_flag_count']=[len((f-{'nearly_face_on_PA_uncertain','disc_PA_unstable'}) if 'nearly_face_on_PA_uncertain' in f else f-{'nearly_face_on_PA_uncertain'}) for f in flags]
common=m.codex_fit_status.eq('provisional_fit')&m.status.eq('ok');clean=common&m.codex_revised_flag_count.eq(0);bothclean=clean&m['flags'].fillna('').eq('')
def stats(series):
 x=series.dropna();v=x.abs()
 return dict(n=len(x),median_signed=float(x.median()),median_abs=float(v.median()),p90_abs=float(v.quantile(.9)),within5=int((v<=5).sum()),within10=int((v<=10).sum()),over20=int((v>20).sum()),over45=int((v>45).sum())) if len(x) else dict(n=0)
summary=dict(rows_codex=len(a),rows_supplied=len(b),match_counts=m['_merge'].value_counts().to_dict(),status_crosstab=pd.crosstab(m.codex_fit_status,m.status).to_dict(),supplied_methods=b.method.fillna('').value_counts().to_dict(),supplied_bar_quality=b.bar_quality.fillna('').value_counts().to_dict(),statistics={})
for label,mask in [('common',common),('codex_revised_unflagged',clean),('both_unflagged',bothclean),('supplied_bar_A',common&m.bar_quality.eq('A')),('codex_original_unflagged',common&m.codex_quality_flags.fillna('').eq('')),('non_face_on',common&~m.codex_information.fillna('').str.contains('nearly_face_on'))]:summary['statistics'][label]={c:stats(m.loc[mask,c]) for c in ['disc_PA_delta_deg','bar_PA_delta_deg','inclination_delta_deg']}
summary['angle_convention_diagnostics']={}
for name,ours,theirs in [('disc','codex_disc_pa_sky_deg','disc_PA_deg'),('bar','codex_bar_pa_sky_deg','bar_PA_deg')]:
 summary['angle_convention_diagnostics'][name]={k:stats(axial(num(ours)[common],v[common])) for k,v in [('direct',num(theirs)),('plus90',num(theirs)+90),('negate',-num(theirs)),('90_minus',90-num(theirs))]}
summary['position_max_difference_arcsec']=dict(ra=float((num('ra_deg_codex')-num('ra_deg_supplied')).abs().max()*3600),dec=float((num('dec_deg_codex')-num('dec_deg_supplied')).abs().max()*3600))
summary['identical_filenames']=int((m.fits_filename==m.file).sum())
summary['supplied_inclination_vs_own_eps']=stats(num('inclination_deg')-np.degrees(np.arccos((1-num('disc_eps')).clip(0,1))))
summary['supplied_inclination_q0_02_residual']=stats(num('inclination_deg')-np.degrees(np.arccos(np.sqrt((((1-num('disc_eps'))**2-.04)/.96).clip(0,1)))))
summary['radial_range_differences_arcsec']={k:stats(num(x)-num(y)) for k,x,y in [('disc_min','codex_disc_min_arcsec','disc_sma_min_arcsec'),('disc_max','codex_disc_max_arcsec','disc_sma_max_arcsec')]}
summary['largest_disc_differences']=m.loc[common].assign(absdelta=lambda z:z.disc_PA_delta_deg.abs()).nlargest(10,'absdelta')[['object_id','codex_disc_pa_sky_deg','disc_PA_deg','disc_PA_delta_deg','codex_quality_flags','flags']].fillna('').to_dict('records')
summary['largest_bar_differences']=m.loc[common].assign(absdelta=lambda z:z.bar_PA_delta_deg.abs()).nlargest(10,'absdelta')[['object_id','codex_bar_pa_sky_deg','bar_PA_deg','bar_PA_delta_deg','bar_quality']].fillna('').to_dict('records')
summary['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [a_path,b_path]}
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
m.to_csv(out/'galaxy_by_galaxy_comparison.csv',index=False)
print(json.dumps({k:v for k,v in summary.items() if k not in ['largest_disc_differences','largest_bar_differences','source_sha256']},indent=2))

