from pathlib import Path
import numpy as np,json,csv
from astropy.io import fits
from astropy.wcs import WCS
import astropy.units as u
root=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_cutouts')
rows=[]
for f in sorted(root.glob('*.fits')):
 h=fits.getheader(f);w=WCS(h).celestial
 x=float(h.get('CENX',(h['NAXIS1']+1)/2))-1;y=float(h.get('CENY',(h['NAXIS2']+1)/2))-1
 c=w.pixel_to_world(x,y);xx,yy=w.world_to_pixel(c.directional_offset_by(0*u.deg,1*u.arcsec))
 tilt=float(np.degrees(np.arctan2(xx-x,yy-y)))
 m=w.pixel_scale_matrix
 rows.append(dict(file=f.name,tile=h.get('TILEID'),north_tilt_from_pixel_up_deg=tilt,linear_grid_rotation_deg=float(np.degrees(np.arctan2(m[0,1],m[1,1]))),crval1=float(w.wcs.crval[0]),crval2=float(w.wcs.crval[1])))
a=np.array([r['north_tilt_from_pixel_up_deg'] for r in rows]);b=np.array([r['linear_grid_rotation_deg'] for r in rows])
result=dict(count=len(rows),signed_range_deg=[float(a.min()),float(a.max())],absolute_percentiles_deg={str(p):float(np.percentile(abs(a),p)) for p in [0,50,90,95,99,100]},linear_rotation_abs_max_deg=float(abs(b).max()),worst=rows[int(np.argmax(abs(a)))])
Path('MER_VIS_north_orientation_audit.json').write_text(json.dumps(result,indent=2))
with open('MER_VIS_north_orientation_audit.csv','w',newline='') as out:
 writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
print(json.dumps(result,indent=2))
