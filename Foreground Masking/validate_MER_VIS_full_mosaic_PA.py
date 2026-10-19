from pathlib import Path
import sys,json,csv,hashlib
import numpy as np,pandas as pd
from astropy.io import fits
from astropy.wcs import WCS
from astropy.nddata import Cutout2D
from astropy.coordinates import SkyCoord
import astropy.units as u
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
sys.path.insert(0,str(Path('../Euclid/datalabs_MER_VIS').resolve()))
from MER_VIS_geometry_transforms import local_pixel_matrix
out=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\MER_VIS_PA_validation')
f='EUC_MER_BGSUB-MOSAIC-VIS_TILE102023983-8D3C9A_20241018T181958.121344Z_00.00.fits';full=out/f;part=out/(f+'.part')
if not full.exists():part.replace(full)
id='-619395065457031576';cutpath=out.parent/'Euclid_MER_VIS_cutouts'/f'Euclid_{id}_MER_VIS_cutout.fits'
manifest=pd.read_csv(out.parent/'Euclid_MER_VIS_geometry'/'MER_VIS_local_geometry_manifest.csv',dtype={'object_id':str});r=manifest[manifest.object_id.eq(id)].iloc[0]
cat=next(out.glob('*FINAL-CAT*'));cr=fits.getdata(cat,1);cr=cr[cr['OBJECT_ID']==int(id)][0];theta=float(cr['POSITION_ANGLE']);q=1-float(cr['ELLIPTICITY']);a=float(cr['SEMIMAJOR_AXIS'])
with fits.open(full,memmap=True) as mh,fits.open(cutpath,memmap=True) as ch:
 mw=WCS(mh[0].header).celestial;cw=WCS(ch[0].header).celestial;sky=SkyCoord(float(cr['RIGHT_ASCENSION'])*u.deg,float(cr['DECLINATION'])*u.deg);mx,my=mw.world_to_pixel(sky);cx,cy=cw.world_to_pixel(sky)
 fresh=Cutout2D(mh[0].data,sky,ch[0].data.shape,wcs=mw,mode='partial',fill_value=np.nan)
 same=np.array_equal(fresh.data,ch[0].data,equal_nan=True);maxdiff=float(np.nanmax(np.abs(fresh.data-ch[0].data)))
 pts=np.array([[0,0],[100,0],[0,100],[ch[0].data.shape[1]-1,ch[0].data.shape[0]-1]],float);p1=fresh.wcs.pixel_to_world(pts[:,0],pts[:,1]);p2=cw.pixel_to_world(pts[:,0],pts[:,1]);wcssep=p1.separation(p2).arcsec
 mat=local_pixel_matrix(mw,sky,mx,my)
 def pa_end(angle,length=10):
  rad=np.deg2rad(angle);p0=mw.pixel_to_world(mx,my);p1=mw.pixel_to_world(mx+length*np.cos(rad),my+length*np.sin(rad));return p0.position_angle(p1).deg%180
 converted=pa_end(theta);v=mat@np.array([np.cos(np.deg2rad(theta)),np.sin(np.deg2rad(theta))]);vectorpa=np.degrees(np.arctan2(-v[0],v[1]))%180
 profile=pd.read_csv(out.parent/'Euclid_MER_VIS_geometry'/'profiles'/f'Euclid_{id}_MER_VIS_ellipse_profile.csv');disc=profile[profile.sma_arcsec.between(r.codex_disc_min_arcsec,r.codex_disc_max_arcsec)&profile.valid&profile.stop_code.eq(0)&(profile.sampled_fraction>=.7)&(profile.intensity>5*profile.intensity_error.clip(lower=1e-12))]
 pixelmean=np.degrees(np.angle(np.mean(np.exp(2j*np.deg2rad(disc.pa_pixel_deg))))/2)%180
 # matching science pixels, not rotated or interpolated
 patch=Cutout2D(mh[0].data,sky,(600,600),wcs=mw);x,y=patch.wcs.world_to_pixel(sky);data=patch.data;noise=np.nanstd(data[:60,:60]);scaled=np.arcsinh(data/max(noise,1e-9))
 fig,axes=plt.subplots(1,2,figsize=(11,5.5))
 for ax,ang,title in zip(axes,[theta,theta+90],['Catalogue angle interpreted as CCW from pixel x','Diagnostic perpendicular angle  not an adopted correction']):
  ax.imshow(scaled,origin='lower',cmap='gray',vmin=0,vmax=np.arcsinh(np.nanpercentile(data,99.5)/noise));ax.add_patch(Ellipse((x,y),2*3*a,2*3*a*q,angle=ang,fill=False,color='#ffb13b',lw=2));ax.plot(x,y,'r+',ms=7);ax.set_title(title,fontsize=10);ax.set(xlim=(x-240,x+240),ylim=(y-240,y+240));ax.set_xticks([]);ax.set_yticks([])
  for _,z in disc.iloc[::2].iterrows():ax.add_patch(Ellipse((x,y),2*z.sma_arcsec/.1,2*z.sma_arcsec*(1-z.ellipticity)/.1,angle=z.pa_pixel_deg,fill=False,color='#40d9d2',lw=1))
 fig.suptitle(f'Euclid {id}   Native pixels from the full VIS mosaic',fontsize=12);fig.text(.5,.02,'Orange: catalogue shape at 3 times its scale. Cyan: selected fitted disc ellipses. Native pixel y increases upwards.',ha='center',fontsize=9);fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(out/'MER_VIS_PA_overlay_comparison.png',dpi=170);plt.close(fig)
 small=mh[0].data[::24,::24];fig,ax=plt.subplots(figsize=(8,8));ax.imshow(np.arcsinh(small/max(noise,1e-9)),origin='lower',cmap='gray',vmin=0,vmax=4);ax.plot(mx/24,my/24,'o',mfc='none',mec='red',ms=17);ax.annotate('Page 7 galaxy',(mx/24,my/24),xytext=(mx/24+70,my/24+50),color='red',arrowprops={'arrowstyle':'->','color':'red'});ax.set_title('Full VIS mosaic  Tile 102023983  19200 by 19200 pixels');ax.set_xlabel('Downsampled native pixel x');ax.set_ylabel('Downsampled native pixel y');fig.tight_layout();fig.savefig(out/'MER_VIS_full_mosaic_locator.png',dpi=150);plt.close(fig)
 result=dict(object_id=id,source_mosaic=str(full),cutout=str(cutpath),catalogue=str(cat),full_shape=list(mh[0].data.shape),mosaic_centre_pixel_zero_based=[float(mx),float(my)],cutout_centre_pixel_zero_based=[float(cx),float(cy)],cutout_exact_pixel_match=same,cutout_max_abs_difference=maxdiff,wcs_test_max_difference_arcsec=float(max(wcssep)),euclid_position_angle_original_fits_deg=theta,euclid_position_angle_tap_deg=49.91947937011719,catalogue_vis_det=int(cr['VIS_DET']),catalogue_semimajor_axis_pix=a,catalogue_ellipticity=1-q,independent_two_position_sky_pa_deg=converted,vector_conversion_sky_pa_deg=float(vectorpa),stored_euclid_detection_pa_sky_deg=float(r.euclid_detection_pa_sky_deg),fitted_disc_pa_sky_deg=float(r.codex_disc_pa_sky_deg),fitted_disc_pixel_pa_deg=float(pixelmean),perpendicular_diagnostic_sky_pa_deg=pa_end(theta+90),archive_md5='bb20bec6eea0750a1c97cb002d33147e',downloaded_md5=hashlib.file_digest(full.open('rb'),'md5').hexdigest(),fits_checksums_present=False,detection_mosaic_public=False)
 (out/'MER_VIS_PA_validation_results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
