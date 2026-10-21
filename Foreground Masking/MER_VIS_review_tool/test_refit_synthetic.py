from pathlib import Path
import numpy as np,json,subprocess,sys
from astropy.io import fits
from astropy.wcs import WCS
base=Path(__file__).resolve().parent;out=base/'refit_test_state'/'synthetic';out.mkdir(parents=True,exist_ok=True)
y,x=np.indices((241,241));cx=cy=120.;theta=.6;u=(x-cx)*np.cos(theta)+(y-cy)*np.sin(theta);v=-(x-cx)*np.sin(theta)+(y-cy)*np.cos(theta)
r=np.hypot(u,v/.65);image=5*np.exp(-r/20)+np.random.default_rng(7).normal(0,.008,r.shape)
w=WCS(naxis=2);w.wcs.crpix=[121,121];w.wcs.crval=[52,-28];w.wcs.cdelt=[-.1/3600,.1/3600];w.wcs.ctype=['RA---TAN','DEC--TAN'];h=w.to_header();h['CENX']=129.;h['CENY']=116.;h['GALID']='test';path=out/'synthetic.fits';fits.writeto(path,image.astype('f4'),h,overwrite=True)
row=dict(object_id='test',fits_filename=path.name,fits_path=str(path),manual_centre_x_pix=cx,manual_centre_y_pix=cy)
request=dict(object_id='test',row=row,segmentation_area=5000,lock_centre=True,source_manifest_sha256='synthetic',engine_sha256='test')
(out/'request.json').write_text(json.dumps(request))
r=subprocess.run([sys.executable,str(base/'refit_MER_VIS.py'),str(out/'request.json')],capture_output=True,text=True,timeout=150)
assert r.returncode==0,r.stdout+r.stderr
result=json.loads((out/'result.json').read_text());assert result['codex_fit_status']=='provisional_fit',result['codex_error']
assert abs(result['codex_fit_centre_x_pix']-cx)<1e-8 and abs(result['codex_fit_centre_y_pix']-cy)<1e-8
assert abs(result['codex_inclination_deg']-np.degrees(np.arccos(.65)))<2
assert abs(result['codex_disc_pa_sky_deg']-(90+np.degrees(theta)))<2
assert result['codex_centre_offset_arcsec']>.8
print(json.dumps({k:result.get(k) for k in ['codex_fit_status','codex_disc_pa_sky_deg','codex_inclination_deg','codex_disc_axis_ratio','codex_n_disc','codex_centre_offset_arcsec','codex_quality_flags']},indent=2))

