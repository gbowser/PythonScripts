"""Fetch Euclid shapes and Zoobot values for the existing exact-ID MER shortlist."""
import csv,io,json,math
from pathlib import Path
from datetime import datetime,timezone
import requests
from astropy.table import Table

HERE=Path(__file__).resolve().parent
def write(path,rows):
 with path.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def number(value):
 try:
  x=float(value)
  return x if math.isfinite(x) else None
 except (ValueError,TypeError):return None
def inclination(q):
 q=number(q)
 return math.degrees(math.acos(q)) if q is not None and 0<q<=1 else ''
def main():
 out=HERE/'datalabs_MER_VIS';out.mkdir(exist_ok=True)
 targets=list(csv.DictReader((out/'MER_VIS_datalabs_manifest.csv').open(newline='',encoding='utf-8-sig')))
 fields=['position_angle','position_angle_err','ellipticity','ellipticity_err','semimajor_axis','semimajor_axis_err']
 morph=['sersic_angle','sersic_angle_err','sersic_sersic_vis_axis_ratio','sersic_sersic_vis_axis_ratio_err','sersic_sersic_vis_radius','sersic_visnir_flags','disk_sersic_angle','disk_sersic_disk_axis_ratio','disk_sersic_flags','bar_strong','bar_weak','bar_no']
 query='SELECT t.object_id, c.object_id AS main_match_id, m.object_id AS morphology_match_id, '+', '.join('c.'+k for k in fields)+', '+', '.join('m.'+k for k in morph)+''' FROM TAP_UPLOAD.targets t LEFT OUTER JOIN catalogue.mer_catalogue c ON t.object_id=c.object_id LEFT OUTER JOIN catalogue.mer_morphology m ON t.object_id=m.object_id'''
 buf=io.BytesIO();Table(rows=[(int(t['object_id']),) for t in targets],names=['object_id']).write(buf,format='votable');buf.seek(0)
 with requests.Session() as s:
  r=s.post('https://eas.esac.esa.int/tap-server/tap/sync',data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':query,'MAXREC':'100000','UPLOAD':'targets,param:targets'},files={'targets':('targets.xml',buf,'application/x-votable+xml')},timeout=(30,180));r.raise_for_status()
  raw=list(csv.DictReader(io.StringIO(r.text)))
  assert len(raw)==len(targets) and len({r['object_id'] for r in raw})==len(targets),r.text[:1000]
  meta=s.get('https://zenodo.org/api/records/15106473',timeout=60).json()
  versions=s.get('https://zenodo.org/api/records/15106473/versions',timeout=60).json()['hits']['hits']
  versions=sorted(versions,key=lambda v:v['created'])
  ordinal=next((i+1 for i,v in enumerate(versions) if str(v['id'])=='15106473'),'')
 (out/'euclid_morphology_raw.csv').write_text(r.text,encoding='utf-8')
 (out/'euclid_morphology_query.sql').write_text(query,encoding='utf-8')
 (out/'zenodo_15106473_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
 lookup={r['object_id']:r for r in raw};rows=[]
 for t in targets:
  m=lookup[t['object_id']]
  row=dict(object_id=t['object_id'],fits_filename=t['suggested_output_file'],ra_deg=t['ra_deg'],dec_deg=t['dec_deg'],
           codex_bar_pa_sky_deg='',codex_disc_pa_sky_deg='',codex_inclination_deg='',codex_fit_status='not_run_on_Datalabs_cutout',codex_quality_flags='',
           euclid_bar_pa_sky_deg='',euclid_bar_pa_status='not_provided_by_Q1_morphology',
           euclid_detection_pa_pixel_deg=m['position_angle'],euclid_detection_pa_sky_deg='',
           euclid_detection_ellipticity=m['ellipticity'],euclid_detection_semimajor_axis_pix=m['semimajor_axis'],
           euclid_detection_q_proxy='',euclid_detection_inclination_proxy_deg='',
           euclid_sersic_angle_raw_deg=m['sersic_angle'],euclid_sersic_q_vis=m['sersic_sersic_vis_axis_ratio'],
           euclid_sersic_inclination_proxy_deg=inclination(m['sersic_sersic_vis_axis_ratio']),
           euclid_disk_sersic_angle_raw_deg=m['disk_sersic_angle'],euclid_disk_sersic_q=m['disk_sersic_disk_axis_ratio'],
           euclid_disk_sersic_inclination_deg=inclination(m['disk_sersic_disk_axis_ratio']),
           euclid_sersic_flags=m['sersic_visnir_flags'],euclid_disk_sersic_flags=m['disk_sersic_flags'],
           euclid_detection_pa_error_deg=m['position_angle_err'],euclid_detection_ellipticity_error=m['ellipticity_err'],
           euclid_sersic_pa_error_deg=m['sersic_angle_err'],euclid_sersic_q_error=m['sersic_sersic_vis_axis_ratio_err'],
           euclid_sersic_radius_arcsec=m['sersic_sersic_vis_radius'],
           euclid_main_match=bool(m['main_match_id']),euclid_morphology_match=bool(m['morphology_match_id']),
           euclid_zoobot_bar_strong_dirichlet=m['bar_strong'],euclid_zoobot_bar_weak_dirichlet=m['bar_weak'],euclid_zoobot_bar_no_dirichlet=m['bar_no'],
           euclid_zoobot_bar_strong_fraction='',euclid_zoobot_bar_weak_fraction='',euclid_zoobot_bar_no_fraction='',euclid_zoobot_bar_any_fraction='',
           zenodo_bar_strong_fraction=t['strong_bar_fraction'],zenodo_bar_weak_fraction=t['weak_bar_fraction'],zenodo_bar_any_fraction=t['bar_fraction'],
           zenodo_record_id='15106473',zenodo_record_doi=meta['doi'],zenodo_version_label=meta['metadata'].get('version',''),
           zenodo_version_ordinal=ordinal,zenodo_record_updated=meta['updated'],zenodo_csv_checksum=next(f['checksum'] for f in meta['files'] if f['key']=='morphology_catalogue.csv'),
           angle_convention='sky_PA_deg_east_of_north_mod180;inclination_deg_faceon0',q0=0,
           euclid_detection_pa_conversion_status='requires_cutout_WCS',geometry_note='Euclid detection/Sersic values describe whole-object shape, not bar or isolated outer disc',
           catalogue_checked_utc=datetime.now(timezone.utc).isoformat())
  e=number(m['ellipticity'])
  if e is not None and 0<=e<1:
   row['euclid_detection_q_proxy']=1-e;row['euclid_detection_inclination_proxy_deg']=inclination(1-e)
  alpha=[number(m[k]) for k in ('bar_strong','bar_weak','bar_no')]
  if all(x is not None and x>0 for x in alpha):
   total=sum(alpha)
   for label,x in zip(('strong','weak','no'),alpha):row[f'euclid_zoobot_bar_{label}_fraction']=x/total
   row['euclid_zoobot_bar_any_fraction']=(alpha[0]+alpha[1])/total
  rows.append(row)
 write(out/'MER_VIS_geometry_comparison_manifest.csv',rows)
 summary=dict(targets=len(rows),main_matches=sum(r['euclid_main_match'] for r in rows),morphology_matches=sum(r['euclid_morphology_match'] for r in rows),
              populated_disk_axis_ratios=sum(number(r['euclid_disk_sersic_q']) is not None for r in rows),
              populated_sersic_axis_ratios=sum(number(r['euclid_sersic_q_vis']) is not None for r in rows),
              populated_zoobot_bars=sum(number(r['euclid_zoobot_bar_any_fraction']) is not None for r in rows),zenodo_version_ordinal=ordinal)
 (out/'geometry_catalogue_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
