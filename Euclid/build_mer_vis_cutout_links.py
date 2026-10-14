"""Identify public Q1 MER VIS science mosaics and build galaxy-centred cutout URLs.

Metadata queries only; this script never downloads image pixels. The input
contains exact string object IDs, ICRS centres, display widths and tile indices.
"""
import argparse
import csv
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests
from astropy.table import Table

TAP = 'https://eas.esac.esa.int/tap-server/tap/sync'
CUTOUT = 'https://eas.esac.esa.int/sas-cutout/cutout'
QUERY = """SELECT DISTINCT t.object_id, m.mosaic_product_oid, m.tile_index,
m.file_name, m.file_path, m.release_name, m.product_type, m.category
FROM TAP_UPLOAD.targets AS t, sedm.mosaic_product AS m
WHERE m.instrument_name = 'VIS'
AND m.product_type = 'DpdMerBksMosaic'
AND m.category = 'SCIENCE'
AND m.release_name = 'Q1_R1'
AND m.fov IS NOT NULL
AND CONTAINS(POINT('ICRS', t.ra_deg, t.dec_deg), m.fov) = 1
"""


def save_csv(path, rows, fields=None):
    fields = fields or list(rows[0])
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--targets-csv', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, default=here/'q1_mer_vis_cutouts')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    with args.targets_csv.open(newline='', encoding='utf-8-sig') as handle:
        targets = list(csv.DictReader(handle))
    if not targets: parser.error('Empty target catalogue')
    ids = set()
    for t in targets:
        if t['object_id'] in ids: parser.error('Duplicate object_id')
        ids.add(t['object_id'])
        ra, dec, width = (float(t[k]) for k in ('ra_deg','dec_deg','cutout_width_arcsec'))
        if not all(math.isfinite(v) for v in (ra,dec,width)) or not (0<=ra<360 and -90<=dec<=90 and 0<width<=3600):
            parser.error(f"Invalid coordinates or cutout width for {t['object_id']}")
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.overwrite:
        parser.error('Output directory not empty; use --overwrite')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    table = Table(rows=[(t['object_id'],float(t['ra_deg']),float(t['dec_deg'])) for t in targets],
                  names=['object_id','ra_deg','dec_deg'])
    upload = io.BytesIO(); table.write(upload, format='votable');upload.seek(0)
    print(f'Querying MER science mosaics for {len(targets)} galaxy centres',flush=True)
    response = requests.post(TAP, data={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv',
                             'QUERY':QUERY,'MAXREC':'1000000','UPLOAD':'targets,param:targets'},
                             files={'targets':('targets.xml',upload,'application/x-votable+xml')},timeout=(30,180))
    response.raise_for_status()
    reader=csv.DictReader(io.StringIO(response.text))
    if 'mosaic_product_oid' not in (reader.fieldnames or []):
        raise ValueError(f'Unexpected TAP response: {response.text[:1000]}')
    matches=list(reader)
    if len(matches)>=1000000: raise ValueError('Potential truncated TAP result')
    save_csv(args.output_dir/'all_mosaic_matches.csv',matches,list(reader.fieldnames))
    by_id={}
    for match in matches: by_id.setdefault(match['object_id'],[]).append(match)
    records=[];links=['# Q1 MER VIS galaxy cutout links','',
        'One link per galaxy. Public Q1 background-subtracted SCIENCE mosaics.',
        'Cutout centres and widths come from the morphology catalogue; widths are not measured bar sizes.',
        'A centre footprint match does not guarantee full cutout coverage or usable pixels.',
        'Images are observed projections, without deprojection, rotation or foreground masking.','']
    checked=datetime.now(timezone.utc).isoformat()
    for t in targets:
        options=by_id.get(t['object_id'],[])
        record=dict(t,status='no_mosaic_centre_match',mosaic_match_count=len(options),
                    mosaic_product_oid='',mosaic_tile_index='',catalogue_tile_match='',
                    mosaic_file_name='',mosaic_file_path='',product_type='',category='',
                    release_name='',cutout_radius_deg=float(t['cutout_width_arcsec'])/7200,
                    cutout_url='',suggested_output_file='',checked_utc=checked)
        if options:
            best=min(options,key=lambda m:(m['tile_index']!=t['tile_index'],int(m['mosaic_product_oid'])))
            if not best['file_name'].startswith('EUC_MER_BGSUB-MOSAIC-VIS_'):
                raise ValueError(f'Unexpected science filename {best["file_name"]}')
            remote=best['file_path'].rstrip('/')+'/'+best['file_name']
            params={'filepath':remote,'collection':'VIS','tileindex':best['tile_index'],
                    'POS':f"CIRCLE,{float(t['ra_deg']):.12f},{float(t['dec_deg']):.12f},{record['cutout_radius_deg']:.12f}"}
            url=CUTOUT+'?'+urlencode(params)
            record.update(status='mosaic_centre_match',mosaic_product_oid=best['mosaic_product_oid'],
                          mosaic_tile_index=best['tile_index'],catalogue_tile_match=best['tile_index']==t['tile_index'],
                          mosaic_file_name=best['file_name'],mosaic_file_path=best['file_path'],
                          product_type=best['product_type'],category=best['category'],release_name=best['release_name'],
                          cutout_url=url,suggested_output_file=f"Euclid_{t['object_id']}_MER_VIS_cutout.fits")
            links.append(f"- [{t['name']} — {float(t['cutout_width_arcsec']):.1f} arcsec wide]({url})")
        records.append(record)
    save_csv(args.output_dir/'mer_vis_cutout_manifest.csv',records)
    (args.output_dir/'MER_VIS_CUTOUT_LINKS.md').write_text('\n'.join(links)+'\n',encoding='utf-8')
    (args.output_dir/'mosaic_match_query.sql').write_text(QUERY,encoding='utf-8')
    matched=[r for r in records if r['cutout_url']]
    summary=dict(targets=len(targets),matched_galaxies=len(matched),
                 distinct_selected_mosaics=len({r['mosaic_file_name'] for r in matched}),
                 no_centre_match=len(records)-len(matched),
                 catalogue_tile_matches=sum(r['catalogue_tile_match'] is True for r in matched),
                 checked_utc=checked,images_downloaded=0)
    (args.output_dir/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    (args.output_dir/'README.md').write_text('''# Q1 MER VIS galaxy cutouts

The manifest identifies DpdMerBksMosaic, VIS, SCIENCE, Q1_R1 products from
sedm.mosaic_product and generates URLs using the documented ESA cutout service.
It uses actual archive paths, not inferred filenames. Each centre is inside
the selected footprint. Prefer the catalogue tile; otherwise choose the lowest
mosaic product ID. All alternatives are retained in all_mosaic_matches.csv.

Open MER_VIS_CUTOUT_LINKS.md in VS Code and press Ctrl+Shift+V, then click
individual links for manual download. The response can be a ZIP containing a
FITS cutout: extract it and use suggested_output_file from the manifest to
identify the galaxy. The link asks for a CIRCLE with radius equal to half the
catalogue display width, in degrees; the service returns an image cutout, not
a circularly masked galaxy. Inspect actual size, WCS and coverage after download.

One cutout request per galaxy differs from downloading whole mosaics: shared
mosaics still generate separate centred cutout files. No bulk images are
downloaded by this generator. Centre coverage is metadata evidence, not a
complete-pixel or full-galaxy guarantee. Mosaics are already combined and
background-subtracted but are not face-on or bar-aligned. The catalogue width
is a display size, not a scientific aperture. Check background treatment before
measuring faint outer-disc light. Use native celestial WCS when fitting geometry.

Regenerate from PythonScripts:

```powershell
& '.\\.venv\\Scripts\\python.exe' '.\\Euclid\\build_mer_vis_cutout_links.py' `
  --targets-csv '.\\Foreground Masking\\q1_full_candidate_audit\\morphology_candidates.csv' `
  --overwrite
```

The SQL uses TAP_UPLOAD.targets, so it requires an uploaded coordinate table;
it is not a standalone query to paste into a console without that upload.

Sources:
- https://astroquery.readthedocs.io/en/latest/esa/euclid/euclid.html
- https://euclid.esac.esa.int/dr/q1/dpdd/merdpd/dpcards/mer_bksmosaic.html
''',encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__': main()
