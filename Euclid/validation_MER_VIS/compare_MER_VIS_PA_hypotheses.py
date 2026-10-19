"""Compare experimental Euclid PA interpretations using native MER VIS WCS.
Preserves the original manifest. Outputs hypothesis columns, figures and JSON.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
from astropy.io import fits
from astropy.wcs import WCS
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

def difference(a,b): return np.abs((np.asarray(a)-np.asarray(b)+90)%180-90)
def endpoint_pa(w,x,y,t):
 t=np.deg2rad(t);origin=w.pixel_to_world(x,y);end=w.pixel_to_world(x+10*np.cos(t),y+10*np.sin(t));return float(origin.position_angle(end).deg%180)
def stats(frame):
 result={'n':len(frame)}
 for key in ['current','plus90','reverse_sign','raw_as_sky']:
  z=frame['experimental_'+key+'_abs_difference_deg'].dropna().to_numpy();result[key]={'n':len(z),'median_abs_difference_deg':float(np.median(z)) if len(z) else None,'p90_abs_difference_deg':float(np.percentile(z,90)) if len(z) else None,'within10':int((z<=10).sum())}
 return result

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-root',type=Path,default=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid'));args=parser.parse_args();base=args.data_root;out=base/'MER_VIS_PA_validation'/'non_diagonal_tests';out.mkdir(parents=True,exist_ok=True)
 source=base/'Euclid_MER_VIS_geometry'/'MER_VIS_local_geometry_manifest.csv';original_hash=hashlib.sha256(source.read_bytes()).hexdigest();d=pd.read_csv(source,dtype={'object_id':str});original_columns=d.columns.tolist();errors=[]
 for index,r in d.iterrows():
  try:
   theta=float(r.euclid_detection_pa_pixel_deg)
   if not np.isfinite(theta):raise ValueError('No finite Euclid angle')
   h=fits.getheader(r.fits_path);w=WCS(h).celestial;x,y=h['CENX']-1,h['CENY']-1
   hypotheses={'current':endpoint_pa(w,x,y,theta),'plus90':endpoint_pa(w,x,y,theta+90),'reverse_sign':endpoint_pa(w,x,y,-theta),'raw_as_sky':theta%180}
   for key,val in hypotheses.items():d.loc[index,'experimental_'+key+'_sky_pa_deg']=val;d.loc[index,'experimental_'+key+'_abs_difference_deg']=difference(val,r.codex_disc_pa_sky_deg)
   d.loc[index,'experimental_current_vs_stored_difference_deg']=difference(hypotheses['current'],r.euclid_detection_pa_sky_deg)
   d.loc[index,'experimental_90_vs_sign_separation_deg']=difference(hypotheses['plus90'],hypotheses['reverse_sign'])
   d.loc[index,'experimental_pa_status']='hypotheses_only_not_adopted'
  except Exception as e:
   d.loc[index,'experimental_pa_status']='calculation_failed';errors.append({'object_id':r.object_id,'error':str(e)})
  if (index+1)%500==0:print('Checked',index+1,'headers',flush=True)
 fit=d[d.codex_fit_status.eq('provisional_fit')];clean=fit[fit.codex_quality_flags.isna()];axisdist=np.minimum(clean.codex_disc_pa_sky_deg%90,90-clean.codex_disc_pa_sky_deg%90)
 decisive=clean[(axisdist<=15)&(~clean.cutout_partial)&clean.codex_inclination_deg.between(40,70)&(clean.codex_disc_pa_scatter_deg<3)&(clean.codex_bar_max_arcsec>2)].copy()
 decisive['selection_axis_group']=np.where(np.minimum(decisive.codex_disc_pa_sky_deg,180-decisive.codex_disc_pa_sky_deg)<45,'near_north_south','near_east_west')
 chosen=pd.concat([g.nlargest(3,'codex_bar_max_arcsec') for _,g in decisive.groupby('selection_axis_group')]);chosen['selection_reason']='Unflagged; complete; inclination 40–70; disc scatter <3; bar upper bound >2 arcsec; disc PA within15 of cardinal axis; three largest bar bounds in each axis group'
 d.to_csv(out/'MER_VIS_experimental_PA_manifest.csv',index=False);chosen.to_csv(out/'MER_VIS_selected_non_diagonal_examples.csv',index=False)
 for k,(_,r) in enumerate(chosen.iterrows(),1):
  raw,h=fits.getdata(r.fits_path,header=True);x,y=h['CENX']-1,h['CENY']-1;w=WCS(h).celestial;theta=float(r.euclid_detection_pa_pixel_deg);lim=float(r.codex_disc_max_arcsec)*1.35/.1
  # Crop natively; no interpolation or reorientation.
  xa=max(0,int(x-lim));xb=min(raw.shape[1],int(x+lim)+1);ya=max(0,int(y-lim));yb=min(raw.shape[0],int(y+lim)+1);patch=raw[ya:yb,xa:xb];xc,yc=x-xa,y-ya
  noise=max(float(np.nanstd(patch[:max(4,len(patch)//10),:max(4,patch.shape[1]//10)])),1e-9);display=np.arcsinh(patch/noise);vmax=max(float(np.nanpercentile(display,99.5)),2)
  a=float(r.euclid_detection_semimajor_axis_pix)*3;q=float(r.euclid_detection_q_proxy)
  pr=pd.read_csv(base/'Euclid_MER_VIS_geometry'/'profiles'/f'Euclid_{r.object_id}_MER_VIS_ellipse_profile.csv');disc=pr[pr.sma_arcsec.between(r.codex_disc_min_arcsec,r.codex_disc_max_arcsec)&pr.valid&pr.stop_code.eq(0)&(pr.sampled_fraction>=.7)&(pr.intensity>5*pr.intensity_error.clip(lower=1e-12))]
  fig,axes=plt.subplots(1,3,figsize=(12,4.5))
  for ax,key,angle,label in zip(axes,['current','plus90','reverse_sign'],[theta,theta+90,-theta],['Current CCW from x','Experimental +90 degrees','Experimental reversed sign']):
   ax.imshow(display,origin='lower',cmap='gray',vmin=0,vmax=vmax);ax.add_patch(Ellipse((xc,yc),2*a,2*a*q,angle=angle,fill=False,color='#ffb13b',lw=1.8))
   for _,z in disc.iloc[::2].iterrows():ax.add_patch(Ellipse((xc,yc),2*z.sma_arcsec/.1,2*z.sma_arcsec*(1-z.ellipticity)/.1,angle=z.pa_pixel_deg,fill=False,color='#39d6d1',lw=1))
   ax.plot(xc,yc,'r+',ms=5);ax.set_xticks([]);ax.set_yticks([]);ax.set_title(label+'\nSky PA '+f'{r["experimental_"+key+"_sky_pa_deg"]:.1f}°; difference '+f'{r["experimental_"+key+"_abs_difference_deg"]:.1f}°',fontsize=10)
  fig.suptitle(f'Galaxy {r.object_id}   Photutils disc sky PA {r.codex_disc_pa_sky_deg:.2f}°',fontsize=12);fig.text(.5,.015,'Orange: catalogue ellipse at 3 times its scale. Cyan: reliable selected disc ellipses. Native FITS rows plotted bottom up.',ha='center',fontsize=9);fig.tight_layout(rect=(0,.04,1,.93));fig.savefig(out/f'MER_VIS_PA_example_{k}_{r.object_id}.png',dpi=160);plt.close(fig)
 summary={'source_manifest':str(source),'original_manifest_sha256':original_hash,'original_manifest_unchanged':original_hash==hashlib.sha256(source.read_bytes()).hexdigest(),'original_columns_retained':all(d[c].equals(pd.read_csv(source,dtype={'object_id':str})[c]) for c in original_columns),'rows':len(d),'errors':errors,'all_fits':stats(fit),'unflagged_fits':stats(clean),'non_diagonal_screened':stats(decisive),'six_visual_examples':stats(chosen),'max_independent_vs_stored_difference_deg':float(d.experimental_current_vs_stored_difference_deg.max()),'selection':'Unflagged, complete, inclination 40–70 degrees, disc scatter <3 degrees, bar_max>2 arcsec, disc PA within15 degrees of N–S or E–W. Visual examples: top3 by bar_max per orientation group. Not selected by Euclid agreement.','selected_object_ids':chosen.object_id.tolist()}
 (out/'MER_VIS_PA_hypothesis_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
 fig,axes=plt.subplots(1,2,figsize=(10,3.5))
 for ax,subset,title in zip(axes,[clean,decisive],['All unflagged fits','Preselected non diagonal discs']):
  for key,label in [('current','Current'),('plus90','+90 degrees'),('reverse_sign','Reverse sign')]:
   z=np.sort(subset['experimental_'+key+'_abs_difference_deg'].dropna());ax.plot(z,np.arange(1,len(z)+1)/max(len(z),1),label=label)
  ax.set(title=title,xlabel='Absolute difference from Photutils disc PA (degrees)',ylabel='Fraction of galaxies',xlim=(0,90),ylim=(0,1));ax.grid(alpha=.2);ax.legend(fontsize=8)
 fig.tight_layout();fig.savefig(out/'MER_VIS_PA_hypothesis_comparison.png',dpi=170);plt.close(fig)
 print(chosen[['object_id','codex_disc_pa_sky_deg','experimental_plus90_abs_difference_deg','experimental_reverse_sign_abs_difference_deg']].to_string(index=False))
if __name__=='__main__':main()
