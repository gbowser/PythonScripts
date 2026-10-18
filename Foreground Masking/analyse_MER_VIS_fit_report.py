import csv,json,hashlib
from collections import Counter
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SOURCE=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry')
OUT=Path('MER_VIS_report_work');OUT.mkdir(exist_ok=True)
rows=list(csv.DictReader((SOURCE/'MER_VIS_local_geometry_manifest.csv').open(newline='',encoding='utf-8-sig')))
assert len(rows)==2777 and len({r['object_id'] for r in rows})==2777
fit=[r for r in rows if r['codex_fit_status'] in ('provisional_fit','reviewed_ranges')]
clean=[r for r in fit if not r['codex_quality_flags'].strip()]
failed=[r for r in rows if r['codex_fit_status']=='fit_failed']
def num(v):
 try:
  n=float(v)
  return n if np.isfinite(n) else None
 except:return None
def describe(a):
 a=np.asarray(a,dtype=float)
 return dict(n=len(a),median=float(np.median(a)),p10=float(np.percentile(a,10)),p90=float(np.percentile(a,90)),minimum=float(a.min()),maximum=float(a.max())) if len(a) else dict(n=0)
def values(rs,key):return [num(r[key]) for r in rs if num(r.get(key)) is not None]
def compare(rs,left,right,axial=False):
 pairs=np.array([(num(r[left]),num(r[right])) for r in rs if num(r.get(left)) is not None and num(r.get(right)) is not None])
 if not len(pairs):return dict(n=0)
 delta=pairs[:,0]-pairs[:,1]
 if axial:delta=(delta+90)%180-90
 return dict(n=len(delta),median_signed=float(np.median(delta)),median_absolute=float(np.median(abs(delta))),p90_absolute=float(np.percentile(abs(delta),90)),within10=int((abs(delta)<=10).sum()),within20=int((abs(delta)<=20).sum()))
error_counts=Counter(r['codex_error'] for r in failed)
flags=Counter(flag for r in fit for flag in r['codex_quality_flags'].split(';') if flag)
stats=dict(total=len(rows),statuses=dict(Counter(r['codex_fit_status'] for r in rows)),fits=len(fit),clean=len(clean),flagged=len(fit)-len(clean),
 errors=dict(error_counts),flags=dict(flags),source=str(SOURCE/'MER_VIS_local_geometry_manifest.csv'),source_sha256=hashlib.sha256((SOURCE/'MER_VIS_local_geometry_manifest.csv').read_bytes()).hexdigest(),
 partial_all=sum(r.get('cutout_partial')=='True' for r in rows),partial_fit=sum(r.get('cutout_partial')=='True' for r in fit),partial_clean=sum(r.get('cutout_partial')=='True' for r in clean),
 main_matches=sum(r.get('euclid_main_match')=='True' for r in rows),morphology_matches=sum(r.get('euclid_morphology_match')=='True' for r in rows),
 disk_q_available=len(values(rows,'euclid_disk_sersic_q')),sersic_q_available=len(values(rows,'euclid_sersic_q_vis')),
 euclid_bars_available=len(values(rows,'euclid_zoobot_bar_any_fraction')),
 timing=describe(values(rows,'calculation_seconds')),first_calculated=min(r['calculated_utc'] for r in rows),last_calculated=max(r['calculated_utc'] for r in rows),
 unique_q0=sorted({r['q0'] for r in rows}),
 distributions={group:{key:describe(values(rs,key)) for key in ['codex_bar_pa_sky_deg','codex_disc_pa_sky_deg','codex_inclination_deg','codex_disc_axis_ratio','codex_bar_pa_scatter_deg','codex_disc_pa_scatter_deg']} for group,rs in [('all_fit',fit),('unflagged',clean)]},
 comparisons={group:dict(pa=compare(rs,'codex_disc_pa_sky_deg','euclid_detection_pa_sky_deg',True),incl_detection=compare(rs,'codex_inclination_deg','euclid_detection_inclination_proxy_deg'),incl_sersic=compare(rs,'codex_inclination_deg','euclid_sersic_inclination_proxy_deg')) for group,rs in [('all_fit',fit),('unflagged',clean)]},
 zoobot={key:compare(rows,'euclid_zoobot_bar_'+key+'_fraction','zenodo_bar_'+key+'_fraction') for key in ['strong','weak','any']})
stats['euclid_bars_below_selection_threshold']=sum(float(r['euclid_zoobot_bar_any_fraction'])<.8 for r in rows if num(r.get('euclid_zoobot_bar_any_fraction')) is not None)
def score(r):return abs(float(r['disc_vs_detection_pa_difference_deg']))
ranked=sorted([r for r in clean if num(r.get('disc_vs_detection_pa_difference_deg')) is not None],key=score)
examples=[('agreement',ranked[len(ranked)//4]),('unflagged_outlier',ranked[-1]),('flagged_outlier',max([r for r in fit if r['codex_quality_flags'] and num(r.get('disc_vs_detection_pa_difference_deg')) is not None],key=score))]
stats['examples']=[dict(kind=k,object_id=r['object_id'],bar_pa=r['codex_bar_pa_sky_deg'],disc_pa=r['codex_disc_pa_sky_deg'],inclination=r['codex_inclination_deg'],euclid_pa=r['euclid_detection_pa_sky_deg'],pa_difference=r['disc_vs_detection_pa_difference_deg'],flags=r['codex_quality_flags'],plot=str(SOURCE/'profiles'/r['fits_filename'].replace('_cutout.fits','_geometry_review.png'))) for k,r in examples]
(OUT/'statistics.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(1,3,figsize=(11,3.1))
ax[0].bar(['Unflagged\nfit','Flagged\nfit','Failed'],[len(clean),len(fit)-len(clean),len(failed)],color=['#28715a','#c28e2c','#a34f4b']);ax[0].set_ylabel('Galaxies');ax[0].set_title('Fitting outcomes')
ax[1].hist(values(fit,'codex_inclination_deg'),bins=np.arange(0,91,5),color='#b7cbd7',label=f'All fits n={len(fit)}');ax[1].hist(values(clean,'codex_inclination_deg'),bins=np.arange(0,91,5),histtype='step',lw=2,color='#184c6c',label=f'Unflagged n={len(clean)}');ax[1].set(xlabel='Calculated inclination (degrees)',ylabel='Galaxies');ax[1].legend(fontsize=8)
ax[2].barh(list(flags)[::-1],list(flags.values())[::-1],color='#617c8c');ax[2].tick_params(axis='y',labelsize=7);ax[2].set(xlabel='Fits carrying flag',title='Overlapping quality flags')
fig.tight_layout();fig.savefig(OUT/'outcomes.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(1,3,figsize=(11,3.1))
for rs,color,label in [(fit,'#c7d3db','All fits'),(clean,'#205c79','Unflagged')]:
 pa=values(rs,'disc_vs_detection_pa_difference_deg');ax[0].hist(pa,bins=np.arange(-90,96,6),histtype='step',color=color,lw=1.8,label=label)
 for a,key in zip(ax[1:],['euclid_detection_inclination_proxy_deg','euclid_sersic_inclination_proxy_deg']):
  pairs=np.array([(float(r[key]),float(r['codex_inclination_deg'])) for r in rs if num(r.get(key)) is not None]);a.scatter(pairs[:,0],pairs[:,1],s=5,color=color,alpha=.5,rasterized=True)
ax[0].set(xlabel='Disc PA minus detection PA (degrees)',ylabel='Galaxies');ax[0].legend(fontsize=8)
for a,label in zip(ax[1:],['Detection','Sérsic']):a.plot([0,90],[0,90],'--',color='black',lw=.8);a.set(xlim=(0,90),ylim=(0,90),xlabel=f'{label} inclination proxy (degrees)',ylabel='Calculated inclination (degrees)')
fig.tight_layout();fig.savefig(OUT/'comparisons.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(1,3,figsize=(11,3.1))
for a,key in zip(ax,['strong','weak','any']):
 pairs=np.array([(float(r['zenodo_bar_'+key+'_fraction']),float(r['euclid_zoobot_bar_'+key+'_fraction'])) for r in rows if num(r.get('euclid_zoobot_bar_'+key+'_fraction')) is not None]);a.scatter(pairs[:,0],pairs[:,1],s=5,alpha=.4,color='#205c79');a.plot([0,1],[0,1],'--',color='black',lw=.8);a.set(xlim=(0,1),ylim=(0,1),xlabel='Zenodo fraction',ylabel='Euclid fraction',title=key.capitalize()+' bar')
fig.tight_layout();fig.savefig(OUT/'zoobot.png',dpi=180);plt.close(fig)
print(json.dumps({k:v for k,v in stats.items() if k!='distributions'},indent=2))
