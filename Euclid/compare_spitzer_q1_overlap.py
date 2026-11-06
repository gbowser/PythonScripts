"""Coordinate cross-match of the used S4G library, current Q1 selection and Q1 footprint.

--check-footprint makes one public metadata query for all library galaxy centres;
no image download and no modification of source catalogues or science FITS.
"""
from pathlib import Path
import argparse
import collections
import csv
from datetime import datetime,timezone
import hashlib
import io
import json
import math
import re
import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales

ROOT=Path(__file__).resolve().parent.parent
Q1_QUERY="""SELECT DISTINCT t.name, m.mosaic_product_oid, m.tile_index,
m.file_name, m.file_path, m.release_name, m.product_type, m.category
FROM TAP_UPLOAD.targets AS t, sedm.mosaic_product AS m
WHERE m.instrument_name = 'VIS'
AND m.product_type = 'DpdMerBksMosaic'
AND m.category = 'SCIENCE'
AND m.release_name = 'Q1_R1'
AND m.fov IS NOT NULL
AND CONTAINS(POINT('ICRS', t.ra_deg, t.dec_deg), m.fov) = 1
"""


def read(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        return list(csv.DictReader(stream))


def write(path,rows,fields):
    with Path(path).open('w',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-footprint',action='store_true')
    parser.add_argument('--output',type=Path,default=ROOT/'Euclid/comparisons/spitzer_q1_20261029')
    args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    spath=ROOT/'Euclid/library_queries/galaxy_cones.csv'
    epath=ROOT/'Euclid/reports/MER_VIS_review_2026-10-29/MER_VIS_reviewed_adoption_manifest.csv'
    manifest=ROOT/'Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv'
    s,e=read(spath),read(epath)
    assert {r['name'] for r in s}=={r['name'] for r in read(manifest)}
    a=SkyCoord([float(r['ra_deg']) for r in s]*u.deg,[float(r['dec_deg']) for r in s]*u.deg)
    b=SkyCoord([float(r['ra_deg']) for r in e]*u.deg,[float(r['dec_deg']) for r in e]*u.deg)
    index,separation,_=a.match_to_catalog_sky(b)
    nearest=[]
    for k,row in enumerate(s):
        target=e[index[k]]
        nearest.append(dict(spitzer_name=row['name'],spitzer_ra_deg=row['ra_deg'],spitzer_dec_deg=row['dec_deg'],
                            euclid_object_id=target['object_id'],euclid_ra_deg=target['ra_deg'],euclid_dec_deg=target['dec_deg'],
                            separation_arcsec=float(separation[k].arcsec),match_within_10_arcsec=bool(separation[k].arcsec<=10)))
    nearest.sort(key=lambda r:r['separation_arcsec'])
    write(out/'nearest_current_q1.csv',nearest,list(nearest[0]))
    write(out/'matches_current_q1.csv',[r for r in nearest if r['match_within_10_arcsec']],list(nearest[0]))
    summary=dict(checked_utc=datetime.now(timezone.utc).isoformat(),spitzer_library=len(s),current_q1_selection=len(e),
        matching_radius_arcsec=10,matches=sum(r['match_within_10_arcsec'] for r in nearest),
        matches_within_60_arcsec=int((separation.arcsec<=60).sum()),nearest_pair=nearest[0],
        source_hashes={str(p):sha(p) for p in (spath,epath,manifest)},
        scope='182 galaxies actually used versus the selected 2777 Q1 targets; not the complete S4G survey')
    euclid_root=Path(r'D:/Dropbox/Public Documents/UCLAN/MSc Research/Euclid')
    existing=euclid_root/'Clean_Galaxy_Output/euclid_geometry_manifest.csv'
    common=[];spitzer={r['name']:r for r in read(manifest)}
    if existing.exists():
        for row in read(existing):
            if row['name'] not in spitzer:continue
            observed=Path(row['image_path']);spitzer_image=Path(spitzer[row['name']]['image_path'])
            if not observed.is_file() or not spitzer_image.is_file():continue
            spitzer_header=fits.getheader(spitzer_image)
            if not any('-SIP' in spitzer_header.get(f'CTYPE{k}','') for k in (1,2)):
                for key in list(spitzer_header):
                    if re.fullmatch(r'(A|B|AP|BP)_(ORDER|DMAX|\d+_\d+)',key):del spitzer_header[key]
            spitzer_scales=proj_plane_pixel_scales(WCS(spitzer_header).celestial)*3600
            h=fits.getheader(observed);x=float(row['center_x_pix'])-1;y=float(row['center_y_pix'])-1
            with fits.open(observed,memmap=True) as hd:
                patch=np.array(hd[0].section[round(y)-3:round(y)+4,round(x)-3:round(x)+4],dtype=float)
            common.append(dict(name=row['name'],spitzer_image=str(spitzer_image),euclid_observed_image=str(observed),
                euclid_source_image=row['source_euclid_image'],ra_deg=row['center_ra_deg'],dec_deg=row['center_dec_deg'],
                spitzer_pixel_scale_arcsec=float(spitzer_scales[0]),
                euclid_pixel_scale_arcsec=abs(float(row['pixel_scale_arcsec_x'])),
                centre_inside_image=bool(0<=x<h['NAXIS1'] and 0<=y<h['NAXIS2']),
                centre_patch_finite_fraction=float(np.isfinite(patch).mean()),
                release_in_header=h.get('RELEASE','not recorded'),in_current_q1_selection=False))
    if common:write(out/'existing_spitzer_euclid_comparison_targets.csv',common,list(common[0]))
    summary['existing_common_images']=common
    if args.check_footprint:
        from urllib.request import Request,urlopen
        import uuid
        control='__Q1_SELECTION_CONTROL__'
        upload_rows=[(r['name'],float(r['ra_deg']),float(r['dec_deg'])) for r in s]
        upload_rows.append((control,float(e[0]['ra_deg']),float(e[0]['dec_deg'])))
        table=Table(rows=upload_rows,names=['name','ra_deg','dec_deg'])
        stream=io.BytesIO();table.write(stream,format='votable');stream.seek(0)
        (out/'q1_mosaic_footprint_query.sql').write_text(Q1_QUERY,encoding='utf8')
        try:
            boundary='----EuclidMetadata'+uuid.uuid4().hex
            parts=[]
            for key,value in dict(REQUEST='doQuery',LANG='ADQL',FORMAT='csv',QUERY=Q1_QUERY,MAXREC='10000',UPLOAD='targets,param:targets').items():
                parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n').encode())
            parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="targets"; filename="targets.xml"\r\nContent-Type: application/x-votable+xml\r\n\r\n').encode()+stream.getvalue()+b'\r\n')
            parts.append(f'--{boundary}--\r\n'.encode())
            request=Request('https://eas.esac.esa.int/tap-server/tap/sync',data=b''.join(parts),
                            headers={'Content-Type':'multipart/form-data; boundary='+boundary})
            with urlopen(request,timeout=45) as response:text=response.read().decode('utf-8-sig')
            reader=csv.DictReader(io.StringIO(text))
            if 'mosaic_product_oid' not in (reader.fieldnames or []):raise ValueError(text[:500])
            matches=list(reader)
            if len(matches)>=10000:raise ValueError('Potentially truncated footprint query')
            control_matches=[r for r in matches if r['name']==control]
            if not control_matches:raise ValueError('Known Q1 target positive control did not match; zero library matches is inconclusive')
            write(out/'q1_positive_control.csv',control_matches,list(reader.fieldnames))
            matches=[r for r in matches if r['name']!=control]
            write(out/'public_q1_mosaic_centre_matches.csv',matches,list(reader.fieldnames))
            summary['public_q1_mosaic_footprint']=dict(status='checked',matching_galaxies=sorted({r['name'] for r in matches}),
                metadata_rows=len(matches),positive_control_rows=len(control_matches),
                note='Centre coverage only; does not guarantee full usable galaxy coverage.')
        except Exception as exc:
            summary['public_q1_mosaic_footprint']=dict(status='query_failed',error=str(exc))
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('source_hashes','existing_common_images')},indent=2))
    print('Existing two-survey comparison images:',[r['name'] for r in common])


if __name__=='__main__':main()
