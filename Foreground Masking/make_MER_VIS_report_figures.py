import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.visualization import simple_norm
from matplotlib.patches import Ellipse

out=Path('MER_VIS_report_work');s=json.loads((out/'statistics.json').read_text())
rows=list(csv.DictReader(Path(s['source']).open()))
fit=[r for r in rows if r['codex_fit_status']=='provisional_fit'];clean=[r for r in fit if not r['codex_quality_flags']]
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(1,2,figsize=(7,2.8))
ax[0].bar(['Unflagged','Flagged','Failed'],[546,1661,570],color=['#28715a','#c28e2c','#a34f4b']);ax[0].set_ylabel('Galaxies')
for rs,col,label in [(fit,'#a7bfce','All fits'),(clean,'#205c79','Unflagged')]:
 ax[1].hist([float(r['codex_inclination_deg']) for r in rs],bins=np.arange(0,91,5),histtype='step',lw=1.7,color=col,label=label)
ax[1].set(xlabel='Inclination (degrees)',ylabel='Galaxies');ax[1].legend(fontsize=8)
fig.tight_layout();fig.savefig(out/'outcomes_compact.png',dpi=200);plt.close(fig)
fig,ax=plt.subplots(1,2,figsize=(7,3))
for rs,color in [(fit,'#b6c9d4'),(clean,'#205c79')]:
 for a,key in zip(ax,['euclid_detection_inclination_proxy_deg','euclid_sersic_inclination_proxy_deg']):
  a.scatter([float(r[key]) for r in rs],[float(r['codex_inclination_deg']) for r in rs],s=4,color=color,alpha=.45)
for a,title in zip(ax,['Detection proxy','Single Sérsic proxy']):a.plot([0,90],[0,90],'k--',lw=.8);a.set(xlim=(0,90),ylim=(0,90),xlabel='Euclid proxy (degrees)',ylabel='Calculated tilt (degrees)',title=title)
fig.tight_layout();fig.savefig(out/'inclination_compact.png',dpi=200);plt.close(fig)
fig,ax=plt.subplots(1,2,figsize=(7,2.8))
for a,key,title in zip(ax,['disc_vs_detection_pa_difference_deg','quarter'],['Stored conversion','Quarter turn diagnostic']):
 for rs,col,label in [(fit,'#9fb9ca','All fits'),(clean,'#205c79','Unflagged')]:
  delta=[float(r['disc_vs_detection_pa_difference_deg']) for r in rs]
  if key=='quarter':delta=[(v-90+90)%180-90 for v in delta]
  a.hist(delta,bins=np.arange(-90,96,6),histtype='step',lw=1.5,color=col,label=label)
 a.set(xlabel='Axial PA difference (degrees)',ylabel='Galaxies',title=title);a.legend(fontsize=8)
fig.tight_layout();fig.savefig(out/'pa_compact.png',dpi=200);plt.close(fig)
fig,ax=plt.subplots(1,3,figsize=(7,2.7))
for a,key in zip(ax,['strong','weak','any']):
 subset=[r for r in rows if r['euclid_zoobot_bar_'+key+'_fraction']]
 a.scatter([float(r['zenodo_bar_'+key+'_fraction']) for r in subset],[float(r['euclid_zoobot_bar_'+key+'_fraction']) for r in subset],s=3,alpha=.3,color='#205c79');a.plot([0,1],[0,1],'k--',lw=.8);a.set(xlim=(0,1),ylim=(0,1),xlabel='Zenodo fraction',title=key.capitalize())
ax[0].set_ylabel('Euclid fraction')
fig.tight_layout();fig.savefig(out/'zoobot_compact.png',dpi=200);plt.close(fig)
for name,oid in [('unflagged','2731221676651025355'),('flagged','-515488559271594427')]:
 row=next(r for r in rows if r['object_id']==oid)
 image=fits.getdata(row['fits_path']);header=fits.getheader(row['fits_path'])
 profile=Path(s['source']).parent/'profiles'/row['fits_filename'].replace('_cutout.fits','_ellipse_profile.csv')
 pp=list(csv.DictReader(profile.open()))
 fig,ax=plt.subplots(1,2,figsize=(7,3))
 x,y=float(header['CENX'])-1,float(header['CENY'])-1
 radius=float(row['codex_disc_max_arcsec'])/.1*1.3
 ax[0].imshow(image,origin='lower',cmap='gray',norm=simple_norm(image,'asinh',percent=99.7))
 for k,r in enumerate(pp):
  if k%5==0:
   a=float(r['sma_arcsec'])/.1
   ax[0].add_patch(Ellipse((x,y),2*a,2*a*(1-float(r['ellipticity'])),angle=float(r['pa_pixel_deg']),fill=False,color='cyan',lw=.6))
 ax[0].set(xlim=(x-radius,x+radius),ylim=(y-radius,y+radius),xlabel='Native x pixel',ylabel='Native y pixel')
 use=[r for r in pp if r['valid']=='True' and r['stop_code']=='0']
 a=[float(r['sma_arcsec']) for r in use]
 ax[1].plot(a,[float(r['pa_sky_deg']) for r in use],'.-',color='#205c79',ms=3)
 ax[1].axvspan(float(row['codex_bar_min_arcsec']),float(row['codex_bar_max_arcsec']),color='orange',alpha=.25)
 ax[1].axvspan(float(row['codex_disc_min_arcsec']),float(row['codex_disc_max_arcsec']),color='green',alpha=.15)
 ax[1].set(xlabel='Semi major axis (arcsec)',ylabel='Sky PA (degrees)',ylim=(0,180))
 fig.tight_layout();fig.savefig(out/f'case_{name}.png',dpi=200);plt.close(fig)
print('Report figures ready')
