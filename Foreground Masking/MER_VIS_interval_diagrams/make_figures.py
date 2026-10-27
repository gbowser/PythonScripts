from pathlib import Path
import csv,json,math,statistics
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse,Arc
from astropy.io import fits
from astropy.wcs import WCS
import astropy.units as u
OUT=Path('MER_VIS_interval_diagrams');ROOT=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.titlesize':12,'axes.labelsize':11,'xtick.labelsize':9,'ytick.labelsize':9,'figure.facecolor':'white','savefig.facecolor':'white'})
ORANGE='#c67c08';GREEN='#23834c';BLUE='#236c9a';GREY='#a8adb3'
def shade(ax,bar,disc):
 ax.axvspan(*bar,color='#f4c36f',alpha=.32,zorder=0);ax.axvspan(*disc,color='#8cc59d',alpha=.26,zorder=0);ax.grid(alpha=.18)
def dim(ax,p1,p2,text,color,offset=(0,0)):
 ax.annotate('',xy=p2,xytext=p1,arrowprops=dict(arrowstyle='<->',color=color,lw=1.5));m=(np.array(p1)+p2)/2+offset;ax.text(*m,text,color=color,fontsize=11,ha='center',va='center',bbox=dict(facecolor='white',edgecolor='none',alpha=.88,pad=1))
# Explanatory geometry, with explicit synthetic values.
fig=plt.figure(figsize=(8.2,4.65),layout='constrained');gs=fig.add_gridspec(2,2,width_ratios=[1,1.25]);ax=fig.add_subplot(gs[:,0]);ep=fig.add_subplot(gs[0,1]);pa=fig.add_subplot(gs[1,1]);ax.set_aspect('equal');ax.set_xlim(-11.5,11.5);ax.set_ylim(-10,11.5);ax.axis('off');ax.set_title('Illustration only — not a measured galaxy',fontsize=11)
theta=np.deg2rad(145);btheta=np.deg2rad(110);disc_dir=np.array([np.cos(theta),np.sin(theta)]);bar_dir=np.array([np.cos(btheta),np.sin(btheta)])
for r in [5,6.2,7.5,8.7,10]:ax.add_patch(Ellipse((0,0),2*r,2*r*.65,angle=145,fill=False,edgecolor=GREEN,lw=1.3,alpha=.7))
for r in [1.8,2.1,2.4,2.7,3.0]:ax.add_patch(Ellipse((0,0),2*r,2*r*.42,angle=110,fill=False,edgecolor=ORANGE,lw=1.5))
ax.plot(0,0,'k+',ms=8);ax.text(.5,-.8,'Centre',fontsize=10)
dim(ax,np.array([0.,0.]),disc_dir*10,'r_out = 10″',GREEN,offset=(-.8,-1.6));dim(ax,np.array([0.,0.]),-bar_dir*3,'r_bar = 3″',ORANGE,offset=(2.5,-1.2))
ax.annotate('Selected disc ellipses',xy=disc_dir*8.7,xytext=(-1.0,9.7),fontsize=10,color=GREEN,ha='center',arrowprops=dict(arrowstyle='->',color=GREEN))
ax.text(-10,-9.5,'Radii run from the centre to one end\nof an ellipse’s long axis, not across its diameter.',fontsize=9.7)
ax.annotate('',xy=(8,9),xytext=(8,5.5),arrowprops=dict(arrowstyle='->',color='black'));ax.text(8,9.4,'N',ha='center',fontsize=10);ax.annotate('',xy=(4.5,5.5),xytext=(8,5.5),arrowprops=dict(arrowstyle='->',color='black'));ax.text(4,5.5,'E',fontsize=10,ha='right',va='center')
r=np.array([.5,.9,1.3,1.8,2.1,2.4,2.7,3,3.5,4,4.5,5,6,7,8,9,10]);eps=np.array([.12,.28,.42,.56,.59,.60,.59,.56,.48,.40,.35,.35,.35,.35,.35,.35,.35]);pas=np.array([35,28,24,18,20,22,21,19,30,42,52,55,54,55,56,55,54]);bar=(1.8,3);disc=(5,10)
for a in [ep,pa]:shade(a,bar,disc);a.set_xlim(.0,10.5)
ep.plot(r,eps,'o-',color=BLUE,ms=3.4,lw=1.2);ep.set_ylim(0,.85);ep.set_ylabel('Ellipticity ε');ep.set_title('Bar plateau and outward drop',fontsize=11);ep.annotate('Bar plateau',xy=(2.4,.6),xytext=(.7,.77),color=ORANGE,fontsize=10,arrowprops=dict(arrowstyle='->',color=ORANGE));ep.plot([2.4,4.5],[.6,.6],':',color=GREY);ep.annotate('',xy=(4.5,.35),xytext=(4.5,.6),arrowprops=dict(arrowstyle='<->',color='#9b3b3b'));ep.text(5,.58,'Drop = 0.25',color='#9b3b3b',fontsize=10);ep.text(6,.73,'Selected disc',color=GREEN,fontsize=10);ep.tick_params(labelbottom=False)
pa.plot(r,pas,'o-',color=BLUE,ms=3.4,lw=1.2);pa.set_ylim(0,85);pa.set_ylabel('Sky PA (degrees)');pa.set_xlabel('Ellipse semi-major axis (arcsec)');pa.text(1.5,69,'Similar angles\nin the plateau',color=ORANGE,fontsize=10);pa.text(6,69,'Outer disc\nangles',color=GREEN,fontsize=10)
fig.savefig(OUT/'disc_bar_concept.png',dpi=240);plt.close(fig)
# Actual stored fit, no rerunning or changing geometry.
oid='-639567775462084647';rows={r['object_id']:r for r in csv.DictReader((ROOT/'MER_VIS_local_geometry_manifest.csv').open(encoding='utf-8-sig'))};row=rows[oid]
raw=list(csv.DictReader((ROOT/'profiles'/f'Euclid_{oid}_MER_VIS_ellipse_profile.csv').open(encoding='utf-8-sig')))
fields=['sma_arcsec','ellipticity','pa_sky_deg','pa_pixel_deg','x_original_pix','y_original_pix']
ps=[{**r,**{k:float(r[k]) for k in fields}} for r in raw];good=[p for p in ps if p['used_for_geometry'].lower()=='true'];bars=[p for p in good if p['selected_bar'].lower()=='true'];discs=[p for p in good if p['selected_disc'].lower()=='true'];rout=max(p['sma_arcsec'] for p in discs);rbar=max(p['sma_arcsec'] for p in bars);dstart=max(.5*rout,1.25*rbar)
search=[p for p in good if .5<=p['sma_arcsec']<=.7*rout];smooth=[statistics.median([search[max(0,i-1)]['ellipticity'],p['ellipticity'],search[min(len(search)-1,i+1)]['ellipticity']]) for i,p in enumerate(search)]
candidates=[]
for i,p in enumerate(search):
 if smooth[i]<.2 or smooth[i]<max(smooth[max(0,i-2):i+3]):continue
 left=right=i
 while left>0 and smooth[left-1]>=smooth[i]-.05 and i-left<12:left-=1
 while right<len(search)-1 and smooth[right+1]>=smooth[i]-.05 and right-i<12:right+=1
 if [z['sma_arcsec'] for z in search[left:right+1]]!=[z['sma_arcsec'] for z in bars]:continue
 beyond=[z for z in good if p['sma_arcsec']<z['sma_arcsec']<=max(2.5*p['sma_arcsec'],p['sma_arcsec']+1)]
 low=min(beyond,key=lambda z:z['ellipticity']);drop=smooth[i]-low['ellipticity']
 if abs(drop-float(row['codex_bar_eps_drop']))<1e-9:candidates.append((p['sma_arcsec'],smooth[i],low))
peak_r,peak_eps,low=max(candidates,key=lambda p:p[0]);assert len(bars)==5 and len(discs)==6
with fits.open(row['fits_path'],memmap=True) as hd:
 h=hd[0].header;w=WCS(h).celestial;scale=float(np.sqrt(abs(np.linalg.det(w.pixel_scale_matrix)))*3600);cx=float(row['codex_fit_centre_x_pix']);cy=float(row['codex_fit_centre_y_pix']);rad=rout*1.36/scale;x0=max(0,int(cx-rad));x1=min(h['NAXIS1'],int(cx+rad+1));y0=max(0,int(cy-rad));y1=min(h['NAXIS2'],int(cy+rad+1));cut=np.array(hd[0].section[y0:y1,x0:x1],float)
 finite=cut[np.isfinite(cut)];lo_v,hi_v=np.percentile(finite,[15,99.8]);display=np.arcsinh(12*np.clip((cut-lo_v)/(hi_v-lo_v),0,1))/np.arcsinh(12)
fig=plt.figure(figsize=(8.2,4.65),layout='constrained');gs=fig.add_gridspec(2,2,width_ratios=[1,1.25]);ax=fig.add_subplot(gs[:,0]);ep=fig.add_subplot(gs[0,1]);pa=fig.add_subplot(gs[1,1]);ax.imshow(display,origin='lower',cmap='gray',extent=(x0-.5,x1-.5,y0-.5,y1-.5),interpolation='nearest');ax.set_title('Actual fitted isophotes',fontsize=11);ax.set_xticks([]);ax.set_yticks([])
for group,col in [(discs,GREEN),(bars,ORANGE)]:
 for p in group:
  a=p['sma_arcsec']/scale;ax.add_patch(Ellipse((p['x_original_pix'],p['y_original_pix']),2*a,2*a*(1-p['ellipticity']),angle=p['pa_pixel_deg'],fill=False,edgecolor=col,lw=1.1,alpha=.85))
ax.plot(cx,cy,'+',color='white',ms=7);lastbar=max(bars,key=lambda p:p['sma_arcsec']);lastdisc=max(discs,key=lambda p:p['sma_arcsec'])
for p,label,col,frac in [(lastbar,'r_bar = 1.724″',ORANGE,1),(lastdisc,'r_out = 3.812″',GREEN,-1)]:
 a=p['sma_arcsec']/scale;angle=np.deg2rad(p['pa_pixel_deg']);end=np.array([p['x_original_pix'],p['y_original_pix']])+frac*a*np.array([np.cos(angle),np.sin(angle)])
 ax.annotate(label,xy=end,xycoords='data',xytext=(.96,.12) if col==GREEN else (.04,.94),textcoords='axes fraction',color=col,fontsize=10,ha='right' if col==GREEN else 'left',arrowprops=dict(arrowstyle='->',color=col),bbox=dict(facecolor='black',alpha=.7,edgecolor='none',pad=2))
sky=w.pixel_to_world(cx,cy);anchor=np.array([x0+rad*.40,y0+rad*.32])
for angle,label in [(0,'N'),(90,'E')]:
 ex,ey=w.world_to_pixel(sky.directional_offset_by(angle*u.deg,1*u.arcsec));vec=np.array([ex-cx,ey-cy]);vec=vec/np.linalg.norm(vec)*rad*.22;ax.annotate('',xy=anchor+vec,xytext=anchor,arrowprops=dict(arrowstyle='->',color='white',lw=1));ax.text(*(anchor+vec*1.3),label,color='white',fontsize=9,ha='center',va='center')
for a in [ep,pa]:shade(a,(min(p['sma_arcsec'] for p in bars),rbar),(dstart,rout));a.set_xlim(0,rout*1.17)
for a,field in [(ep,'ellipticity'),(pa,'pa_sky_deg')]:
 segments=[];current=[]
 for p in ps:
  if p not in good or p['sma_arcsec']>rout*1.17 or (current and field=='pa_sky_deg' and abs(current[-1][field]-p[field])>90):
   if current:segments.append(current)
   current=[]
   if p not in good:continue
  if p['sma_arcsec']<=rout*1.17:current.append(p)
 if current:segments.append(current)
 for seg in segments:a.plot([p['sma_arcsec'] for p in seg],[p[field] for p in seg],color=BLUE,lw=1.1,zorder=2)
 a.scatter([p['sma_arcsec'] for p in good],[p[field] for p in good],s=15,color=BLUE,zorder=3)
 rej=[p for p in ps if p not in good];a.scatter([p['sma_arcsec'] for p in rej],[p[field] for p in rej],s=8,color=GREY,zorder=1)
 a.scatter([p['sma_arcsec'] for p in bars],[p[field] for p in bars],s=31,facecolor=ORANGE,edgecolor='white',linewidth=.45,zorder=4)
 a.scatter([p['sma_arcsec'] for p in discs],[p[field] for p in discs],s=31,facecolor=GREEN,edgecolor='white',linewidth=.45,zorder=4)
ep.plot([p['sma_arcsec'] for p in search],smooth,color='#774ca3',ls='--',lw=1.0,label='Smoothed search profile');ep.set_ylim(0,1);ep.set_ylabel('Ellipticity ε');ep.set_title('Same ellipses as points on the profiles',fontsize=11);ep.tick_params(labelbottom=False)
ep.plot([peak_r,low['sma_arcsec']],[peak_eps,peak_eps],':',color='#9b3b3b',lw=1);ep.annotate('',xy=(low['sma_arcsec'],low['ellipticity']),xytext=(low['sma_arcsec'],peak_eps),arrowprops=dict(arrowstyle='<->',color='#9b3b3b',lw=1.4));ep.text(2.65,.69,'Drop = 0.260',fontsize=10,color='#9b3b3b');ep.text(.8,.88,'Bar plateau',fontsize=10,color=ORANGE);ep.text(2.7,.88,'Disc interval',fontsize=10,color=GREEN)
pa.set_ylim(20,80);pa.set_ylabel('Sky PA (degrees)');pa.set_xlabel('Ellipse semi-major axis (arcsec)');pa.text(.75,25,'Five bar angles\nRMS = 1.55°',color=ORANGE,fontsize=10);pa.text(2.65,69,'Six disc angles',color=GREEN,fontsize=10)
fig.savefig(OUT/'disc_bar_measured.png',dpi=240);plt.close(fig)
meta=dict(object_id=oid,r_out=rout,r_bar=rbar,disc_lower_bound=dstart,selected_disc_inner=min(p['sma_arcsec'] for p in discs),peak_radius=peak_r,smoothed_peak=peak_eps,outward_low_radius=low['sma_arcsec'],outward_low_eps=low['ellipticity'],drop=float(row['codex_bar_eps_drop']),bar_rms=float(row['codex_bar_pa_scatter_deg']),bar_pa=float(row['codex_bar_pa_sky_deg']),disc_pa=float(row['codex_disc_pa_sky_deg']),bar_points=[{k:p[k] for k in ['sma_arcsec','ellipticity','pa_sky_deg']} for p in bars])
(OUT/'measured_example.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))


