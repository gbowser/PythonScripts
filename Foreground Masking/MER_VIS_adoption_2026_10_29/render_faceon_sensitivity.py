"""Diagnostic previews only: same science pixels, shared output grid and stretch."""
import importlib.util,json,math
from pathlib import Path
import numpy as np
from scipy.ndimage import map_coordinates
from astropy.io import fits
from astropy.wcs import WCS
from astropy.visualization import simple_norm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

base=Path('MER_VIS_adoption_2026_10_29');oid='-663928688473758026'
source=json.loads((base/'source_reviews.json').read_text());g=json.loads((base/'galaxies.json').read_text())['galaxies'][oid]
test=next(r for r in json.loads((base/'MER_VIS_sensitivity_results.json').read_text()) if r['id']==oid)
module_path=Path('C:/Users/gordo/Documents/Github/PythonScripts/Euclid/datalabs_MER_VIS/MER_VIS_geometry_transforms.py')
spec=importlib.util.spec_from_file_location('mer_transforms',module_path);transforms=importlib.util.module_from_spec(spec);spec.loader.exec_module(transforms)
review_root=Path('C:/Users/gordo/Documents/Github/PythonScripts/Euclid/review_MER_VIS/saved_reviews_centre_v3')
result=json.loads((review_root/'refits'/source[oid]['settings']['refit_id']/'result.json').read_text())
with fits.open(result['fits_path'],memmap=True) as hd:
    data=np.array(hd[0].data,dtype=float);w=WCS(hd[0].header).celestial
scale=g['pixel_scale_arcsec'];radius=source[oid]['settings']['disc'][1]*1.25;n=math.ceil(radius/scale)
yy,xx=np.mgrid[-n:n+1,-n:n+1];offsets=np.vstack([xx.ravel(),yy.ravel()])
cases=[dict(probe='Reviewed selection',calculation=test['baseline'],reference=g['centre_reference'])]+test['centre_trials']
baseline_transform=None;baseline_map=None;arrays=[];metrics=[]
for case in cases:
    c=case['calculation'];ref=case['reference']
    if any(c.get(k) is None for k in ['disc_pa','inclination','bar_pa']):
        arrays.append(None);metrics.append(dict(probe=case['probe'],status='No complete geometry'));continue
    sky=w.pixel_to_world(ref['x'],ref['y']);pixel_matrix=transforms.local_pixel_matrix(w,sky,ref['x'],ref['y'])
    transform=transforms.image_transform(c['disc_pa'],c['inclination'],c['bar_pa'])@(pixel_matrix/scale)
    if baseline_transform is None:baseline_transform=transform.copy()
    elif np.dot(transform[0],baseline_transform[0])<0:transform=-transform
    native=np.linalg.solve(transform,offsets)+np.array([[ref['x']],[ref['y']]])
    if baseline_map is None:baseline_map=native.copy()
    shift=np.hypot(*(native-baseline_map));mask=xx.ravel()**2+yy.ravel()**2<=n*n
    arrays.append(map_coordinates(data,[native[1],native[0]],order=1,mode='constant',cval=np.nan).reshape(xx.shape))
    metrics.append(dict(probe=case['probe'],disc_pa_deg=c['disc_pa'],inclination_deg=c['inclination'],bar_pa_deg=c['bar_pa'],
                        maximum_input_mapping_change_native_pixels=float(shift[mask].max()),
                        rms_input_mapping_change_native_pixels=float(np.sqrt(np.mean(shift[mask]**2)))))
v=arrays[0][np.isfinite(arrays[0])];norm=simple_norm(v,stretch='asinh',asinh_a=.02,vmin=float(np.percentile(v,2)),vmax=float(np.percentile(v,99.7)))
fig,axes=plt.subplots(1,5,figsize=(17,4.6));extent=[-n*scale,n*scale,-n*scale,n*scale]
for ax,case,array,metric in zip(axes,cases,arrays,metrics):
    if array is not None:
        ax.imshow(array,origin='lower',cmap='gray',norm=norm,extent=extent);c=case['calculation']
        ax.set_title(f"{case['probe']}\nDisc PA {c['disc_pa']:.1f}°, i {c['inclination']:.1f}°",fontsize=10)
        ax.axhline(0,color='#33bbcc',ls=':',lw=.6);ax.set_xlabel('Bar-aligned offset (arcsec)')
    else:
        ax.text(.5,.5,'Fewer than 3 disc samples\nNo inclination; no transformation',ha='center',va='center',transform=ax.transAxes,fontsize=9)
        ax.set_title(case['probe']);ax.set_xlim(-radius,radius);ax.set_ylim(-radius,radius)
    ax.set_aspect('equal')
axes[0].set_ylabel('Face-on offset (arcsec)')
fig.suptitle(f'{oid}: reviewed fit versus ±1 native-pixel centre probes\nSame output grid and stretch; diagnostic trials only, no adopted FITS replaced',fontsize=12)
fig.tight_layout(rect=[0,0,1,.87]);fig.savefig(base/'MER_VIS_near_face_on_sensitivity.png',dpi=170);plt.close(fig)
(base/'MER_VIS_near_face_on_mapping.json').write_text(json.dumps(dict(radius_arcsec=n*scale,metrics=metrics),indent=2))
print(json.dumps(metrics,indent=2))
