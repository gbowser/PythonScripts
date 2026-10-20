from pathlib import Path
import sys,numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from fit_adaptive_MER_VIS_geometry import measure,axial_diff
from astropy.io import fits
from astropy.wcs import WCS
root=Path(__file__).parent/'synthetic_check';root.mkdir(exist_ok=True);(root/'logs').mkdir(exist_ok=True)
y,x=np.indices((181,181));xc=93.;yc=88.;theta=np.radians(30);u=(x-xc)*np.cos(theta)+(y-yc)*np.sin(theta);v=-(x-xc)*np.sin(theta)+(y-yc)*np.cos(theta);q=.6;r=np.sqrt(u*u+(v/q)**2);im=20*np.exp(-r/12)+np.random.default_rng(42).normal(0,.02,r.shape)
w=WCS(naxis=2);w.wcs.crpix=[91,91];w.wcs.cd=np.array([[-.1/3600,0],[0,.1/3600]]);w.wcs.crval=[52,-29];w.wcs.ctype=['RA---TAN','DEC--TAN'];h=w.to_header();h['CENX']=91.;h['CENY']=91.;h['GALID']='synthetic';fits.writeto(root/'synthetic.fits',im.astype('f4'),h,overwrite=True)
z=measure((dict(object_id='synthetic',fits_filename='synthetic.fits'),str(root),str(root),'4000'))
print({k:v for k,v in z.items() if k in ['codex_fit_status','codex_fit_centre_x_pix','codex_fit_centre_y_pix','codex_disc_pa_sky_deg','codex_inclination_deg','codex_error']})
assert z['codex_fit_status']=='provisional_fit',z['codex_error'];assert np.hypot(z['codex_fit_centre_x_pix']-xc,z['codex_fit_centre_y_pix']-yc)<1
assert abs(axial_diff(z['codex_disc_pa_sky_deg'],120))<3
assert abs(z['codex_inclination_deg']-np.degrees(np.arccos(q)))<3
print('PASS: known centre recovered and PA/inclination within 3 degrees')
