from pathlib import Path
import json,numpy as np,pandas as pd
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u
out=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\MER_VIS_PA_validation');full=next(out.glob('*BGSUB*.fits'));w=WCS(fits.getheader(full)).celestial;cat=fits.getdata(next(out.glob('*FINAL-CAT*')),1);ids=set(str(x) for x in cat['OBJECT_ID']);d=pd.read_csv(out.parent/'Euclid_MER_VIS_geometry'/'MER_VIS_local_geometry_manifest.csv',dtype={'object_id':str});d=d[d.object_id.isin(ids)&d.codex_fit_status.eq('provisional_fit')];res=[]
def diff(a,b):return abs((a-b+90)%180-90)
for _,r in d.iterrows():
 c=cat[cat['OBJECT_ID']==int(r.object_id)][0];sky=SkyCoord(c['RIGHT_ASCENSION']*u.deg,c['DECLINATION']*u.deg);x,y=w.world_to_pixel(sky);theta=float(c['POSITION_ANGLE'])
 def pa(t):
  p=w.pixel_to_world(x+10*np.cos(np.deg2rad(t)),y+10*np.sin(np.deg2rad(t)));return sky.position_angle(p).deg%180
 z=dict(object_id=r.object_id,catalogue_theta_deg=theta,fitted_disc_sky_pa_deg=r.codex_disc_pa_sky_deg,disc_scatter_deg=r.codex_disc_pa_scatter_deg,quality_flags=r.codex_quality_flags)
 for name,t in [('documented_ccw_x',theta),('reversed_sign',-theta),('perpendicular',theta+90)]:z[name+'_sky_deg']=pa(t);z[name+'_abs_difference_deg']=diff(pa(t),r.codex_disc_pa_sky_deg)
 z['raw_as_sky_abs_difference_deg']=diff(theta%180,r.codex_disc_pa_sky_deg);res.append(z)
pd.DataFrame(res).to_csv(out/'MER_VIS_same_tile_hypothesis_checks.csv',index=False)
a=pd.DataFrame(res);print('tile fits',len(a),'no flags',a.quality_flags.isna().sum());print(a[['object_id','catalogue_theta_deg','fitted_disc_sky_pa_deg','documented_ccw_x_abs_difference_deg','reversed_sign_abs_difference_deg','perpendicular_abs_difference_deg']].to_string(index=False));print('median differences',a.filter(like='abs_difference').median().to_dict())
