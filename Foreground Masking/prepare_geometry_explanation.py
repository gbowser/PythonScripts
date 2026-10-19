from pathlib import Path
import pandas as pd,numpy as np,json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
root=Path('MER_VIS_explanation_work');root.mkdir(exist_ok=True)
base=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry');d=pd.read_csv(base/'MER_VIS_local_geometry_manifest.csv',dtype={'object_id':str}).fillna('')
ids=['-619395065457031576','-522170446265172635','2760587364650641854','-642703864460081959','-515488559271594427','-519246610291156594']; records=[]
plt.rcParams.update({'font.size':9,'axes.titlesize':10})
for k,i in enumerate(ids):
 r=d[d.object_id.eq(i)].iloc[0].to_dict();pr=pd.read_csv(base/'profiles'/f'Euclid_{i}_MER_VIS_ellipse_profile.csv')
 good=pr['valid'].astype(str).str.lower().eq('true') & pr.stop_code.eq(0) & (pr.sampled_fraction>=.7)&(pr.intensity>0)&(pr.intensity>5*pr.intensity_error.clip(lower=1e-12))
 g=pr[good];a=g.sma_arcsec.to_numpy();e=g.ellipticity.to_numpy()
 if r['codex_disc_min_arcsec']!='':lo=float(r['codex_disc_min_arcsec']);hi=float(r['codex_disc_max_arcsec']);b0=float(r['codex_bar_min_arcsec']);b1=float(r['codex_bar_max_arcsec'])
 else:
  inner=np.where((a>.12*a.max())&(a<.55*a.max()))[0];peak=inner[np.argmax(e[inner])];b0,b1=.75*a[peak],1.15*a[peak];lo,hi=max(1.25*b1,.65*a.max()),a.max()*1.001
 dg=g[g.sma_arcsec.between(lo,hi)];bg=g[g.sma_arcsec.between(b0,b1)]
 r.update(n_good=len(g),n_disc=len(dg),n_bar=len(bg),eps_span=float(dg.ellipticity.max()-dg.ellipticity.min()),disc_samples=dg[['sma_arcsec','ellipticity','pa_sky_deg']].round(5).to_dict('records'),plot_disc_min=lo,plot_disc_max=hi,plot_bar_min=b0,plot_bar_max=b1)
 raw,h=fits.getdata(r['fits_path'],header=True);x,y=h['CENX']-1,h['CENY']-1
 fig=plt.figure(figsize=(7,4.2));gs=fig.add_gridspec(2,2,width_ratios=[1,1.12],wspace=.28,hspace=.36);im=fig.add_subplot(gs[:,0]);ep=fig.add_subplot(gs[0,1]);pa=fig.add_subplot(gs[1,1])
 valid=raw[np.isfinite(raw)];med,_,noise=sigma_clipped_stats(valid[::8]);scale=max(float(noise),1e-9)
 im.imshow(np.arcsinh((raw-med)/scale),origin='lower',cmap='gray',vmin=0,vmax=np.arcsinh(max(float(np.nanpercentile(raw,99.7)-med)/scale,2)))
 pixscale=.1
 for _,z in pr.iloc[::3].iterrows():
  color='#209349' if lo<=z.sma_arcsec<=hi else '#d68414' if b0<=z.sma_arcsec<=b1 else '#37bcd2'
  im.add_patch(Ellipse((x,y),2*z.sma_arcsec/pixscale,2*z.sma_arcsec*(1-z.ellipticity)/pixscale,angle=z.pa_pixel_deg,fill=False,edgecolor=color,lw=.65))
 lim=min(g.sma_arcsec.max()*1.22/.1,x,y,raw.shape[1]-1-x,raw.shape[0]-1-y);im.set(xlim=(x-lim,x+lim),ylim=(y-lim,y+lim),title='Native cutout and fitted ellipses');im.plot(x,y,'r+',ms=5);im.set_xticks([]);im.set_yticks([])
 for ax,field in [(ep,'ellipticity'),(pa,'pa_sky_deg')]:
  ax.plot(pr.sma_arcsec,pr[field],'.',color='0.75',ms=3);ax.plot(g.sma_arcsec,g[field],'o-',color='#286ca2',ms=3,lw=.8)
  ax.axvspan(b0,b1,color='orange',alpha=.2);ax.axvspan(lo,hi,color='green',alpha=.16);ax.grid(alpha=.2)
 ep.set(ylabel='Ellipticity  1 − b/a',ylim=(0,1));pa.set(ylabel='Sky PA (degrees)',xlabel='Semi major axis (arcsec)',ylim=(0,180),yticks=[0,45,90,135,180]);ep.tick_params(labelbottom=False)
 fig.subplots_adjust(left=.02,right=.98,top=.93,bottom=.13);fig.savefig(root/f'example_{k+1}.png',dpi=190);plt.close(fig);records.append(r)
(root/'examples.json').write_text(json.dumps(records,indent=2,default=str))
print(json.dumps([{k:r[k] for k in ['object_id','codex_disc_axis_ratio','codex_inclination_deg','codex_disc_pa_sky_deg','codex_disc_pa_scatter_deg','codex_quality_flags','codex_error','n_good','n_disc','n_bar','eps_span']} for r in records],indent=2))
# Geometry schematic
fig,axes=plt.subplots(1,3,figsize=(7,2.25))
for ax,q,lab in zip(axes,[1,.6,.25],['Face on  i = 0°','Tilted  i = 53.1°','More inclined  i = 75.5°']):
 ax.add_patch(Ellipse((0,0),2,2*q,fill=False,lw=2,color='#286ca2'));ax.plot([-1,1],[0,0],color='0.5',lw=1);ax.plot([0,0],[-q,q],color='0.5',lw=1);ax.text(.45,.08,'a');ax.text(.06,q/2,'b');ax.set(xlim=(-1.2,1.2),ylim=(-1.2,1.2),title=lab,aspect='equal');ax.axis('off');ax.text(0,-1.15,f'b/a = {q:g}',ha='center')
fig.tight_layout();fig.savefig(root/'inclination.png',dpi=180);plt.close(fig)
