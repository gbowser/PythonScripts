import json,csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
out=Path('MER_VIS_report_work');s=json.loads((out/'statistics.json').read_text())
rows=list(csv.DictReader(Path(s['source']).open(newline='',encoding='utf-8')))
fit=[r for r in rows if r['codex_fit_status']=='provisional_fit'];clean=[r for r in fit if not r['codex_quality_flags']]
def stats(a):
 a=np.array(a)
 return dict(n=len(a),median_absolute=float(np.median(abs(a))),p90_absolute=float(np.percentile(abs(a),90)),within10=int((abs(a)<=10).sum()),within20=int((abs(a)<=20).sum()))
def d(a,b):return (a-b+90)%180-90
audit=[]
for r in fit:
 audit.append(dict(object_id=r['object_id'],unflagged=not bool(r['codex_quality_flags']),
                  fitted_disc_pa_deg=r['codex_disc_pa_sky_deg'],euclid_raw_pa_deg=r['euclid_detection_pa_pixel_deg'],
                  original_converted_pa_deg=r['euclid_detection_pa_sky_deg'],
                  legacy_difference_deg=d(float(r['codex_disc_pa_sky_deg']),float(r['euclid_detection_pa_sky_deg'])),
                  raw_as_sky_hypothesis_difference_deg=d(float(r['codex_disc_pa_sky_deg']),float(r['euclid_detection_pa_pixel_deg'])),
                  converted_plus90_hypothesis_difference_deg=d(float(r['codex_disc_pa_sky_deg']),float(r['euclid_detection_pa_sky_deg'])+90)))
s['pa_convention_audit']={label:{key:stats([r[key] for r in rs]) for key in ['legacy_difference_deg','raw_as_sky_hypothesis_difference_deg','converted_plus90_hypothesis_difference_deg']} for label,rs in [('all_fit',audit),('unflagged',[r for r in audit if r['unflagged']])]}
with (out/'PA_convention_audit.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
(out/'statistics.json').write_text(json.dumps(s,indent=2),encoding='utf-8')
fig,axes=plt.subplots(1,2,figsize=(10.5,3))
for ax,key,title in zip(axes,['legacy_difference_deg','converted_plus90_hypothesis_difference_deg'],['Stored conversion','Quarter turn diagnostic only']):
 ax.hist([r[key] for r in audit],bins=np.arange(-90,96,6),histtype='step',color='#acbfc8',label='All 2207 fits')
 ax.hist([r[key] for r in audit if r['unflagged']],bins=np.arange(-90,96,6),histtype='step',lw=1.8,color='#205c79',label='546 unflagged fits')
 ax.set(xlabel='Fitted disc PA minus catalogue direction (degrees)',ylabel='Galaxies',title=title);ax.legend(fontsize=8)
fig.tight_layout();fig.savefig(out/'pa_audit.png',dpi=180);plt.close(fig)
print(json.dumps(s['pa_convention_audit'],indent=2))
