"""Fill the catalogue comparison manifest by fitting the saved Datalabs cutouts."""
import csv,math
from pathlib import Path
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from fit_MER_VIS_geometry_portable import fit_one,sky_pa
from MER_VIS_geometry_transforms import local_pixel_matrix,transform_cutout

def load(path):
 with Path(path).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def numeric(x):
 try:
  v=float(x)
  return v if np.isfinite(v) else None
 except (ValueError,TypeError):return None
def save(path,rows):
 fields=list(dict.fromkeys(k for row in rows for k in row))
 temp=path.with_suffix('.tmp')
 with temp.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 temp.replace(path)
def axial_difference(a,b):return (a-b+90)%180-90

def run(template,cutout_dir,output_dir,limit=5,make_aligned=False,retry_failures=False):
 """Checkpoint every fit, preserve every target, skip completed fits on rerun."""
 out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
 diagnostics=out/'profiles';diagnostics.mkdir(exist_ok=True)
 destination=out/'MER_VIS_geometry_comparison_manifest.csv'
 rows=load(template)
 if destination.exists():
  previous={r['object_id']:r for r in load(destination)}
  for row in rows:
   if row['object_id'] in previous:row.update(previous[row['object_id']])
 selected=rows if limit is None else rows[:limit]
 for i,row in enumerate(selected,1):
  path=Path(cutout_dir)/row['fits_filename']
  row['fits_path']=str(path)
  try:
   if not path.is_file():raise FileNotFoundError(f'Cutout missing: {path}')
   header=fits.getheader(path)
   if str(header.get('GALID',''))!=row['object_id']:raise ValueError('FITS galaxy ID mismatch')
   row['cutout_partial']=header.get('PARTIAL','')
   wcs=WCS(header).celestial
   xc,yc=float(header['CENX'])-1,float(header['CENY'])-1
   matrix=local_pixel_matrix(wcs,wcs.pixel_to_world(xc,yc),xc,yc)
   pa=numeric(row['euclid_detection_pa_pixel_deg'])
   if pa is not None:
    row['euclid_detection_pa_sky_deg']=sky_pa(np.radians(pa),matrix)
    row['euclid_detection_pa_conversion_status']='THETA_IMAGE_direction_through_cutout_WCS_same_MER_grid'
   sma=numeric(row['euclid_detection_semimajor_axis_pix'])
   if sma is not None and pa is not None:
    direction=matrix@np.array([np.cos(np.radians(pa)),np.sin(np.radians(pa))])
    row['euclid_detection_semimajor_axis_arcsec']=float(np.linalg.norm(direction))*sma
   status=row['codex_fit_status']
   completed=status in ('provisional_fit','reviewed_ranges')
   if not completed and (status!='fit_failed' or retry_failures):
    fit=fit_one(path,diagnostics,q0=0.,previews=False)
    for old,new in [('bar_pa_deg','codex_bar_pa_sky_deg'),('disk_pa_deg','codex_disc_pa_sky_deg'),('inclination_deg','codex_inclination_deg'),
                    ('quality_flags','codex_quality_flags'),('disc_axis_ratio','codex_disc_axis_ratio'),('radius_arcsec','codex_radius_arcsec'),
                    ('disc_pa_scatter_deg','codex_disc_pa_scatter_deg'),('bar_pa_scatter_deg','codex_bar_pa_scatter_deg'),
                    ('bar_min_arcsec','codex_bar_min_arcsec'),('bar_max_arcsec','codex_bar_max_arcsec'),('disc_min_arcsec','codex_disc_min_arcsec'),('disc_max_arcsec','codex_disc_max_arcsec')]:
     row[new]=fit[old]
    row['codex_fit_status']='provisional_fit'
    row['codex_error']=''
   if numeric(row['codex_disc_pa_sky_deg']) is not None and numeric(row['euclid_detection_pa_sky_deg']) is not None:
    row['disc_vs_detection_pa_difference_deg']=axial_difference(float(row['codex_disc_pa_sky_deg']),float(row['euclid_detection_pa_sky_deg']))
    row['inclination_vs_detection_proxy_difference_deg']=float(row['codex_inclination_deg'])-float(row['euclid_detection_inclination_proxy_deg']) if numeric(row['euclid_detection_inclination_proxy_deg']) is not None else ''
   if make_aligned and row['codex_fit_status']=='provisional_fit' and not row['codex_quality_flags']:
    geometry=dict(disk_pa_deg=row['codex_disc_pa_sky_deg'],inclination_deg=row['codex_inclination_deg'],bar_pa_deg=row['codex_bar_pa_sky_deg'],radius_arcsec=row['codex_radius_arcsec'],geometry_source='Photutils isophotes; provisional estimate, q0=0')
    candidate=path.with_name(path.stem.removesuffix('_cutout')+'_bar_aligned.fits')
    if candidate.exists():
     h=fits.getheader(candidate)
     assert str(h.get('GALID'))==row['object_id'] and h.get('GEOMSTAT')=='PROVISIONAL','Existing aligned file must be inspected'
     assert all(abs(float(h[k])-float(geometry[g]))<1e-7 for k,g in [('DISKPA','disk_pa_deg'),('INCL','inclination_deg'),('BARPA','bar_pa_deg')]),'Aligned geometry differs'
    else:
     candidate=transform_cutout(path,geometry)
     with fits.open(candidate,mode='update') as hdul:
      hdul[0].header['GEOMSTAT']='PROVISIONAL';hdul[0].header['Q0']=0.;hdul[0].add_checksum()
    row['aligned_fits_path']=str(candidate);row['alignment_status']='provisional_aligned'
   elif row['codex_fit_status']=='provisional_fit':
    row['alignment_status']='withheld_quality_flags' if row['codex_quality_flags'] else 'not_requested'
  except Exception as error:
   if row.get('codex_fit_status')=='provisional_fit':row['alignment_status']='error'
   else:row['codex_fit_status']='fit_failed'
   row['codex_error']=str(error)
  save(destination,rows)
  print(f"[{i}/{len(selected)}] {row['object_id']}: {row['codex_fit_status']} {row.get('codex_error','')}",flush=True)
 print('Saved',len(rows),'rows:',destination)
 return destination
