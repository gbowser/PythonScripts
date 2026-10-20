"""Render per-galaxy MER VIS geometry review cards from existing fits.
No fitting is run. Euclid detection sky PA adopts (stored sky PA + 90) % 180.
"""
import argparse,json,math,textwrap
from pathlib import Path
import numpy as np,pandas as pd
from astropy.io import fits
from astropy.wcs import WCS
from astropy.stats import sigma_clipped_stats
import astropy.units as u
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse,Rectangle
DEFAULT_IDS=['-619395065457031576','2760587364650641854','-642703864460081959','2694350108673052592','-520196615291310590','-515488559271594427','-518289171291708573','-519246610291156594','-518633776290631360','-518659917291205827']
FLAG_LABELS={'disc_PA_sparse_sampling':'Disc PA uncertain: sparse sampling','disc_PA_unstable':'Disc PA varies across radius','bar_PA_unstable':'Bar PA unstable','disc_axis_ratio_unstable':'Disc axis ratio unstable','nearly_face_on_PA_uncertain':'Nearly face on: PA uncertain','high_inclination':'High inclination','weak_ellipse_bar_signature':'Class B: weaker bar-profile evidence','axis_ratio_below_thickness':'Axis ratio below assumed thickness','small_bar_sensitive_to_resolution':'Bar uncertain: small selected interval','relaxed_fit':'Relaxed recovery','iteration_limited_samples':'Iteration-limited samples','short_accepted_profile':'Short accepted profile','disc_range_fallback':'Disc interval fallback','bar_disc_ranges_close':'Bar/disc intervals close','small_disc':'Small disc','star_mask_removed':'Star mask removed in retry','neighbour_mask_removed':'Neighbour mask removed in recovery','no_bar_detected':'No accepted bar; disc retained','centre_offset_large':'Centre offset from catalogue','centre_unstable':'Centre varies across disc'}
def number(v):
 try:return float(v)
 except (TypeError,ValueError):return np.nan
def fmt(v):return f'{v:.1f}' if np.isfinite(v) else 'Unavailable'
def delta(a,b,axial=False):
 if not(np.isfinite(a) and np.isfinite(b)):return '—'
 v=(a-b+90)%180-90 if axial else a-b
 return f'{0.0 if abs(v)<.05 else v:+.1f}'
def reliable(pr):
 if 'used_for_geometry' in pr.columns:return pr.used_for_geometry.astype(str).str.lower().eq('true')
 return pr['valid'].astype(str).str.lower().eq('true')&pr.stop_code.eq(0)&(pr.sampled_fraction>=.7)&(pr.intensity>0)&(pr.intensity>5*pr.intensity_error.clip(lower=1e-12))
def _render_card(r,profiles,out,ordinal):
 oid=r['object_id'];path=Path(r['fits_path']);raw,h=fits.getdata(path,header=True);w=WCS(h).celestial;x=number(r.get('codex_fit_centre_x_pix'));y=number(r.get('codex_fit_centre_y_pix'));x=x if np.isfinite(x) else h['CENX']-1;y=y if np.isfinite(y) else h['CENY']-1
 # Use local celestial pixel scale, not a hardcoded native scale.
 scale=float(np.sqrt(abs(np.linalg.det(w.pixel_scale_matrix)))*3600)
 pp=profiles/f'Euclid_{oid}_MER_VIS_ellipse_profile.csv';pr=pd.read_csv(pp) if pp.exists() else pd.DataFrame();g=pr[reliable(pr)] if len(pr) else pr
 bounds=[number(r.get('codex_'+key)) for key in ['bar_min_arcsec','bar_max_arcsec','disc_min_arcsec','disc_max_arcsec']];candidate=False;v2=str(r.get('codex_pipeline_version','')).startswith('MER_VIS_adaptive_v2')
 if not all(np.isfinite(bounds)) and len(g) and not v2:
  a=g.sma_arcsec.to_numpy();e=g.ellipticity.to_numpy();inner=np.flatnonzero((a>.12*a.max())&(a<.55*a.max()))
  if len(inner):
   peak=inner[np.argmax(e[inner])];b0,b1=.75*a[peak],1.15*a[peak];bounds=[b0,b1,max(1.25*b1,.65*a.max()),a.max()*1.001];candidate=True
 b0,b1,d0,d1=bounds
 nb=int(g.sma_arcsec.between(b0,b1).sum()) if len(g) and np.isfinite(b0) else 0;nd=int(g.sma_arcsec.between(d0,d1).sum()) if len(g) and np.isfinite(d0) else 0
 flags=str(r.get('codex_quality_flags',''));flags='' if flags=='nan' else flags;flaglist=[f for f in flags.split(';') if f];failed=r['codex_fit_status']=='fit_failed';partial=str(r.get('cutout_partial','')).lower()=='true'
 status='FIT FAILED — geometry unavailable' if failed else f'PROVISIONAL FIT — {len(flaglist)} quality flag'+('s' if len(flaglist)!=1 else '') if flaglist else 'PROVISIONAL FIT — no automatic quality flags'
 color,bg=('#a32626','#fcecec') if failed else ('#8a4a00','#fff1db') if flaglist or partial else ('#20577c','#eaf2f8')
 fig=plt.figure(figsize=(8,7),facecolor='white');fig.text(.045,.968,f'{ordinal:02d}  Galaxy {oid}',fontsize=15,weight='bold',va='top');fig.text(.045,.932,path.name,fontsize=10.5,va='top')
 fig.add_artist(Rectangle((.04,.875),.92,.038,transform=fig.transFigure,color=bg,zorder=0));fig.text(.055,.894,status,fontsize=12,color=color,weight='bold',va='center')
 name=str(r.get('catalogue_name','')).strip()
 if name and name!='nan':fig.text(.045,.855,f'Catalogue: {name}   ({r.get("catalogue_match_source","")}; {float(r["catalogue_match_separation_arcsec"]):.2f} arcsec)',fontsize=8.5,color='#20577c')
 im=fig.add_axes([.045,.44,.415,.38]);ep=fig.add_axes([.575,.655,.37,.17]);pa=fig.add_axes([.575,.44,.37,.145])
 if len(g) and not failed:maxa=float(g.sma_arcsec.max())
 elif len(pr) and not failed:maxa=float(pr.sma_arcsec.max())
 else:
  # Failed fits need a target-scale view rather than an entire large sky cutout.
  segpath=Path(__file__).resolve().parent.parent/'datalabs_MER_VIS'/'MER_VIS_datalabs_manifest.csv'
  if not segpath.is_file():segpath=Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid\datalabs_MER_VIS\MER_VIS_datalabs_manifest.csv')
  if segpath.is_file():
   catalog=pd.read_csv(segpath,dtype={'object_id':str}).set_index('object_id')
   maxa=max(3,1.8*np.sqrt(float(catalog.loc[oid,'segmentation_area'])/np.pi)*scale)
  else:maxa=min(raw.shape)*scale*.25
 if not np.isfinite(maxa) or maxa<=0:maxa=min(raw.shape)*scale*.25
 radius=max(3,maxa*1.22)/scale
 xa=max(0,int(x-radius));xb=min(raw.shape[1],int(x+radius)+1);ya=max(0,int(y-radius));yb=min(raw.shape[0],int(y+radius)+1);patch=raw[ya:yb,xa:xb];xc,yc=x-xa,y-ya
 finite=patch[np.isfinite(patch)];sample=finite[::max(1,len(finite)//100000)];med,_,noise=sigma_clipped_stats(sample);noise=max(float(noise),1e-12);display=np.arcsinh((patch-med)/noise);vmax=max(float(np.nanpercentile(display,99.6)),2)
 im.imshow(display,origin='lower',cmap='gray',vmin=0,vmax=vmax)
 overlay=pr.iloc[:0] if failed else g if len(g) else pr
 if len(overlay):
  selected=overlay.iloc[::max(1,len(overlay)//14)]
  for _,z in selected.iterrows():
   c='#26934d' if d0<=z.sma_arcsec<=d1 else '#da8500' if b0<=z.sma_arcsec<=b1 else '#39b9cb';im.add_patch(Ellipse((number(z.get('x_original_pix'))-xa,number(z.get('y_original_pix'))-ya) if 'x_original_pix' in z else (xc,yc),2*z.sma_arcsec/scale,2*z.sma_arcsec*(1-z.ellipticity)/scale,angle=z.pa_pixel_deg,fill=False,color=c,lw=.8))
 if not failed:
  im.plot(h['CENX']-1-xa,h['CENY']-1-ya,'x',color='white',ms=4,mew=.8);im.plot(xc,yc,'+',color='#f34848',ms=6,mew=1.1)
 im.set_xticks([]);im.set_yticks([]);im.set_title('Native image: no adopted geometry' if failed else 'Native pixels and fitted ellipses',fontsize=12,pad=5)
 # WCS compass plotted in the native pixel frame.
 centre=w.pixel_to_world(x,y);anchor=np.array([patch.shape[1]*.16,patch.shape[0]*.16]);alen=min(patch.shape)*.105
 for ang,label in [(0,'N'),(90,'E')]:
  px,py=w.world_to_pixel(centre.directional_offset_by(ang*u.deg,1*u.arcsec));v=np.array([px-x,py-y]);v=v/np.linalg.norm(v)*alen;im.annotate('',xy=anchor+v,xytext=anchor,arrowprops={'arrowstyle':'->','color':'white','lw':.9});im.text(*(anchor+v*1.25),label,color='white',ha='center',va='center',fontsize=9)
 for ax,field in [(ep,'ellipticity'),(pa,'pa_sky_deg')]:
  if len(pr):ax.plot(pr.sma_arcsec,pr[field],'.',color='.72',ms=3,zorder=1)
  if len(g):
   values=g[field].to_numpy();rad=g.sma_arcsec.to_numpy()
   # Break at the 0/180 boundary rather than drawing a spurious vertical jump.
   if field=='pa_sky_deg':
    rr=[];vv=[]
    for j,(a,v) in enumerate(zip(rad,values)):
     if j and (abs(v-values[j-1])>90 or np.any((pr.sma_arcsec.to_numpy()>rad[j-1])&(pr.sma_arcsec.to_numpy()<a)&(~reliable(pr).to_numpy()))):rr.append(np.nan);vv.append(np.nan)
     rr.append(a);vv.append(v)
    ax.plot(rr,vv,'-',color='#2c6c9a',lw=.9)
   else:
    # Avoid implying measured continuity across rejected radial samples.
    rr=[];vv=[];allrad=pr.sma_arcsec.to_numpy()
    for j,(a,v) in enumerate(zip(rad,values)):
     if j and np.any((allrad>rad[j-1])&(allrad<a)&(~reliable(pr).to_numpy())):rr.append(np.nan);vv.append(np.nan)
     rr.append(a);vv.append(v)
    ax.plot(rr,vv,'-',color='#2c6c9a',lw=.9)
   ax.plot(rad,values,'o',color='#2c6c9a',ms=3,zorder=2)
  if np.isfinite(b0):ax.axvspan(b0,b1,color='orange',alpha=.18)
  if np.isfinite(d0):ax.axvspan(d0,d1,color='green',alpha=.14)
  ax.set_xlim(0,maxa*1.08);ax.tick_params(labelsize=10);ax.grid(alpha=.18)
 ep.set(ylabel='Ellipticity',ylim=(0,1),yticks=[0,.5,1]);ep.set_ylabel('Ellipticity',fontsize=12);ep.tick_params(labelbottom=False)
 pa.set(ylim=(0,180),yticks=[0,90,180]);pa.set_ylabel('Sky PA (°)',fontsize=12);pa.set_xlabel('Semi-major axis (arcsec)',fontsize=11)
 legend='Orange: candidate bar   Green: disc   Blue: accepted   Grey: excluded'
 if failed:legend='No adopted centre or ellipses. Grey samples, if present, are rejected.'
 if candidate:legend='Candidate ranges only (failed fit)   Orange: bar   Green: disc'
 fig.text(.045,.365,legend,fontsize=10.5);fig.text(.045,.342,f'Accepted ellipses: {len(g)} total; {nb} bar; {nd} disc.  Native orientation.',fontsize=10.2)
 disc=number(r.get('codex_disc_pa_sky_deg'));bar=number(r.get('codex_bar_pa_sky_deg'));inc=number(r.get('codex_inclination_deg'));eu=(number(r.get('euclid_detection_pa_sky_deg'))+90)%180;ei=number(r.get('euclid_detection_inclination_proxy_deg'));si=number(r.get('euclid_sersic_inclination_proxy_deg'))
 vals=[['Disc PA',fmt(disc),fmt(eu),delta(disc,eu,True)],['Bar PA',fmt(bar),'Not provided','—'],['Inclination',fmt(inc),fmt(ei)+'  detection',delta(inc,ei)],['Inclination',fmt(inc),fmt(si)+'  Sérsic',delta(inc,si)]]
 tax=fig.add_axes([.04,.171,.92,.157]);tax.axis('off');t=tax.table(cellText=vals,colLabels=['Geometry (°)','Photutils','Euclid','Δ fit − Euclid'],colWidths=[.23,.20,.34,.23],bbox=[0,0,1,1],cellLoc='left');t.auto_set_font_size(False);t.set_fontsize(11.5)
 for (row,col),cell in t.get_celld().items():cell.set_linewidth(.45);cell.set_edgecolor('#cdd6dc');cell.set_facecolor('#e8eef3' if row==0 else '#f7f9fb' if row%2==0 else 'white');cell.PAD=.055
 for j in range(4):t[0,j].set_text_props(weight='bold')
 fig.text(.045,.15,'Euclid Q1_R1 PA: adopted +90° adjustment. Inclinations: thin-disc proxies (q₀ = 0).',fontsize=9.8)
 fig.text(.045,.131,'Δ PA is signed and wraps at 180°. Euclid bar PA unavailable; detection shape is whole-object.',fontsize=9.2)
 issues=[]
 if failed:
  err=str(r.get('codex_error','')).replace('ValueError: ','');issues=['FIT FAILED: '+err,'No adopted geometry. Empty quality flags do not mean a good fit.']
 elif flaglist:issues=['QUALITY: '+'; '.join(FLAG_LABELS.get(f,f) for f in flaglist)]
 else:issues=['QUALITY: No automatic flags. Physical disc and bar identification still needs review.']
 info=str(r.get('codex_information',''));info='' if info=='nan' else info
 if info:issues.append('INFO: Nearly face-on; disc PA uncertain, not a quality defect.')
 centreoffset=number(r.get('codex_centre_offset_arcsec'));method=str(r.get('codex_method',''))
 if not failed and np.isfinite(centreoffset):issues.append(f'Centre offset {centreoffset:.2f} arcsec; method {method}. Red + fitted; white x catalogue.')
 if partial:issues.append('COVERAGE: requested cutout is PARTIAL; inspect galaxy coverage.')
 wrapped=[]
 for issue in issues:wrapped.extend(textwrap.wrap(issue,width=88,break_long_words=False))
 fig.add_artist(Rectangle((.04,.013),.92,.104,transform=fig.transFigure,color=bg,zorder=0))
 for j,line in enumerate(wrapped):fig.text(.052,.100-j*.021,line,fontsize=9.6,color=color,va='top',weight='bold' if j==0 else 'normal')
 quality_issue=bool(failed or flaglist or partial)
 suffix='_QI' if quality_issue else ''
 name=f'{ordinal:04d}_Euclid_{oid}_MER_VIS_geometry_report{suffix}.png';fig.savefig(out/name,dpi=250);plt.close(fig)
 return dict(order=ordinal,object_id=oid,png=name,quality_issue=quality_issue,fits_filename=path.name,status=r['codex_fit_status'],quality_flags=flaglist,partial=partial,centre_offset_arcsec=centreoffset if np.isfinite(centreoffset) else None,method=method,bar_status=str(r.get('codex_bar_status','')),photutils_disc_pa_deg=disc if np.isfinite(disc) else None,photutils_bar_pa_deg=bar if np.isfinite(bar) else None,photutils_inclination_deg=inc if np.isfinite(inc) else None,euclid_adjusted_detection_pa_deg=eu,euclid_detection_inclination_proxy_deg=ei,euclid_sersic_inclination_proxy_deg=si,euclid_bar_pa_deg=None,delta_disc_pa_deg=delta(disc,eu,True),delta_inclination_detection_deg=delta(inc,ei),delta_inclination_sersic_deg=delta(inc,si),bar_range=[b0,b1] if np.isfinite(b0) else None,disc_range=[d0,d1] if np.isfinite(d0) else None,candidate_ranges_only=candidate,reliable_samples=len(g),bar_samples=nb,disc_samples=nd)
def make_card(r,profiles,out,ordinal):
 result=_render_card(r,profiles,out,ordinal)
 for key in ['catalogue_name','catalogue_match_status','catalogue_match_source','catalogue_match_separation_arcsec','catalogue_match_url']:
  value=r.get(key,'');result[key]='' if str(value)=='nan' else value
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-root',type=Path,default=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid'));p.add_argument('--output-dir',type=Path);p.add_argument('--ids',nargs='+',default=DEFAULT_IDS);args=p.parse_args();base=args.data_root;out=args.output_dir or base/'MER_VIS_galaxy_reports'/'pilot_10';out.mkdir(parents=True,exist_ok=True)
 d=pd.read_csv(base/'Euclid_MER_VIS_geometry'/'MER_VIS_local_geometry_manifest.csv',dtype={'object_id':str}).set_index('object_id',drop=False);results=[]
 for k,oid in enumerate(args.ids,1):results.append(make_card(d.loc[oid].to_dict(),base/'Euclid_MER_VIS_geometry'/'profiles',out,k));print(k,oid,results[-1]['status'],flush=True)
 (out/'MER_VIS_report_sample_data.json').write_text(json.dumps(results,indent=2,allow_nan=False),encoding='utf8');print('Saved',len(results),'cards in',out)
if __name__=='__main__':main()


