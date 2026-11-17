"""Query DR1 candidate totals and at most 100 ordered galaxies, with cutout metadata.

Uses public TAP metadata only. strict-three-answer is the default; the
provisional two-answer policy requires an explicit CLI choice.
"""
import argparse,concurrent.futures,csv,hashlib,io,json,math,re,time,urllib.error,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
TAP='https://eas.esac.esa.int/tap-server/tap/sync'
GROUPS=[['smooth_or_featured_featured_or_disk','smooth_or_featured_smooth','smooth_or_featured_artifact_star_zoom'],['disk_edge_on_no','disk_edge_on_yes'],['has_spiral_arms_yes','has_spiral_arms_no'],['bar_strong','bar_weak','bar_no']]

def predicate(alias,release,policy):
    conditions=[f"{alias}.data_set_release='{release}'"]
    for i,all_fields in enumerate(GROUPS):
        fields=all_fields[:2] if i==0 and policy=='provisional-two-answer' else all_fields
        den=' + '.join(alias+'.'+f for f in fields)
        num=' + '.join(alias+'.'+f for f in (fields[:2] if i==3 else fields[:1]))
        # Explicit finite/positive denominator guards exclude missing/NaN/zero models.
        # This ADQL engine treats NaN > 0 as true; >0 alone is insufficient.
        conditions.extend([f'({den}) > 0',f'({den}) < 1.0E100'])
        conditions.extend(alias+'.'+f+' >= 0' for f in fields)
        conditions.append(f'({num}) - 0.8 * ({den}) >= 0')
    return '\nAND '.join(conditions)
def read(path):
    with Path(path).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def write(path,rows,fields=None):
    if fields is None:fields=list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def fetch(out,name,sql,reuse=False):
    (out/(name+'.sql')).write_text(sql,encoding='utf8')
    result=out/(name+'.csv');meta=out/(name+'_query.json');sha=hashlib.sha256(sql.encode()).hexdigest()
    if reuse and result.exists() and meta.exists() and json.loads(meta.read_text())['sql_sha256']==sha:return read(result)
    started=time.perf_counter()
    request=urllib.request.Request(TAP,data=urllib.parse.urlencode({'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':sql,'MAXREC':'20000'}).encode())
    try:
        with urllib.request.urlopen(request,timeout=180) as r:body=r.read()
    except urllib.error.HTTPError as e:
        detail=e.read().decode(errors='replace');(out/(name+'_error.txt')).write_text(detail,encoding='utf8');raise RuntimeError(detail) from e
    text=body.decode('utf8')
    if text.lstrip().startswith('<'):raise RuntimeError('TAP returned an XML error rather than CSV')
    rows=list(csv.DictReader(io.StringIO(text)))
    if len(rows)>=20000:raise RuntimeError('Potential TAP truncation')
    result.write_bytes(body)
    meta.write_text(json.dumps(dict(endpoint=TAP,sql_sha256=sha,response_sha256=hashlib.sha256(body).hexdigest(),rows=len(rows),seconds=time.perf_counter()-started,utc=datetime.now(timezone.utc).isoformat()),indent=2),encoding='utf8')
    return rows
def compile_rows(rows,mosaics,policy):
    compiled=[]
    for rank,r in enumerate(rows,1):
        row=dict(r,pilot_rank=rank,selection_policy=policy,q1_training_warning_equivalence='unavailable; no equivalent warning flag imposed')
        for name,fields,i in [('disc_fraction',GROUPS[0][:2] if policy=='provisional-two-answer' else GROUPS[0],1),('not_edge_on_fraction',GROUPS[1],1),('spiral_fraction',GROUPS[2],1),('bar_fraction',GROUPS[3],2)]:
            values=[float(r[f]) for f in fields]
            if not all(math.isfinite(v) and v>=0 for v in values) or sum(values)<=0:raise ValueError('Invalid model values')
            row[name]=sum(values[:i])/sum(values)
            if row[name]<.8-1e-12:raise ValueError('Returned row fails local fraction verification')
        ra,dec=float(r['ra_deg']),float(r['dec_deg'])
        if not 0<=ra<360 or not -90<=dec<=90:raise ValueError('Invalid sky coordinates')
        row['sky_frame']='ICRS'
        try:
            corners=[(float(r[f'corner_{i}_ra']),float(r[f'corner_{i}_dec'])) for i in range(4)]
            if not all(math.isfinite(v) for c in corners for v in c):raise ValueError('Invalid corners')
            dx=[((a-ra+180)%360-180)*math.cos(math.radians(dec))*3600 for a,b in corners];dy=[(b-dec)*3600 for a,b in corners]
            extent=2*max(max(map(abs,dx)),max(map(abs,dy)))
            requested=min(300.,max(30.,extent*1.2))
            row.update(catalogue_box_width_arcsec=extent,requested_width_arcsec=requested,width_capped=extent*1.2>300,size_status='catalogue corner box; 20 percent padding, 30 to 300 arcsec; not a bar measurement')
        except (KeyError,TypeError,ValueError):
            row.update(catalogue_box_width_arcsec='',requested_width_arcsec='',width_capped='',size_status='missing catalogue corners; manual size required')
        matches=[m for m in mosaics if m['tile_index']==r['tile_index'] and m['processing_mode']==('WIDE' if r['survey']=='wide_survey' else 'DEEP')]
        row['mosaic_candidates']=len(matches)
        if matches and row['requested_width_arcsec']:
            m=min(matches,key=lambda z:int(z['mosaic_product_oid']))
            row.update({'mosaic_'+k:v for k,v in m.items()})
            row['datalabs_source_file']=m['datalabs_path'].rstrip('/')+'/'+m['file_name']
            params={'filepath':m['file_path'].rstrip('/')+'/'+m['file_name'],'collection':'VIS','tileindex':m['tile_index'],'POS':f'CIRCLE,{ra:.12f},{dec:.12f},{row["requested_width_arcsec"]/7200:.12f}'}
            row['cutout_url']='https://eas.esac.esa.int/sas-cutout/cutout?'+urllib.parse.urlencode(params)
            row['mosaic_selection_status']='catalogue tile match; verify returned WCS and coverage'
        else:row['mosaic_selection_status']='missing usable size or mosaic'
        compiled.append(row)
    return compiled

def run(out,limit=100,release='DR1_R2',policy='strict-three-answer',reuse=False):
    if not 1<=limit<=100:raise ValueError('Pilot limit must be 1 to 100')
    if not re.fullmatch(r'DR1_R\d+',release):raise ValueError('Invalid release identifier')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    schema=fetch(out,'DR1_schema',"SELECT table_name,column_name,datatype,unit,description FROM TAP_SCHEMA.columns WHERE table_name IN ('dr1.mer_catalogue_wide_survey','dr1.mer_morphology_wide_survey','dr1.mer_catalogue_deep_survey','dr1.mer_morphology_deep_survey','dr1.mer_cutouts_wide_survey','dr1.mer_cutouts_deep_survey','dr1.mosaic_product')",reuse)
    counts={};choices={};artifact_available={}
    for survey in ['wide_survey','deep_survey']:
        validity=fetch(out,survey+'_artifact_field_check',f"SELECT COUNT(*) AS n FROM dr1.mer_morphology_{survey} m WHERE m.data_set_release='{release}' AND m.smooth_or_featured_artifact_star_zoom >= 0 AND m.smooth_or_featured_artifact_star_zoom < 1.0E100",reuse)
        artifact_available[survey]=int(validity[0]['n'])
        where=predicate('m',release,policy)
        c=fetch(out,survey+'_count',f'SELECT COUNT(*) AS candidate_rows, COUNT(DISTINCT m.object_id) AS distinct_objects FROM dr1.mer_morphology_{survey} m WHERE '+where,reuse)[0]
        counts[survey]=dict(rows=int(c['candidate_rows']),distinct_objects=int(c['distinct_objects']))
        ids=fetch(out,survey+'_first_ids',f'SELECT TOP {limit} m.object_id FROM dr1.mer_morphology_{survey} m WHERE '+where+' ORDER BY m.object_id',reuse)
        for r in ids:choices.setdefault(r['object_id'],survey)
    overlap=int(fetch(out,'overlap_count','SELECT COUNT(DISTINCT w.object_id) AS overlapping_candidates FROM dr1.mer_morphology_wide_survey w JOIN dr1.mer_morphology_deep_survey d ON w.object_id=d.object_id WHERE '+predicate('w',release,policy)+'\nAND '+predicate('d',release,policy),reuse)[0]['overlapping_candidates'])
    selected=sorted(choices,key=int)[:limit];rows=[]
    for survey in ['wide_survey','deep_survey']:
        ids=[x for x in selected if choices[x]==survey]
        if not ids:continue
        fields='m.object_id,c.right_ascension AS ra_deg,c.declination AS dec_deg,c.tile_index,c.segmentation_area,c.semimajor_axis AS semimajor_axis_pix,c.ellipticity,c.vis_det,c.mag_stargal_sep,c.basic_download_data_oid AS catalogue_product_oid,m.data_set_release'
        fields+=', '+', '.join('m.'+f for group in GROUPS for f in group)
        fields+=', '+', '.join(f'k.corner_{i}_{ax}' for i in range(4) for ax in ['ra','dec'])
        sql=f"SELECT {fields} FROM dr1.mer_morphology_{survey} m JOIN dr1.mer_catalogue_{survey} c ON m.object_id=c.object_id AND m.data_set_release=c.data_set_release LEFT OUTER JOIN dr1.mer_cutouts_{survey} k ON m.object_id=k.object_id AND m.data_set_release=k.data_set_release WHERE m.data_set_release='{release}' AND m.object_id IN ("+','.join(str(int(x)) for x in ids)+') ORDER BY m.object_id'
        rr=fetch(out,survey+'_metadata',sql,reuse)
        if len(rr)!=len(ids) or len({r['object_id'] for r in rr})!=len(ids):raise ValueError('Missing or duplicate metadata rows; do not silently alter pilot selection')
        rows.extend(dict(r,survey=survey) for r in rr)
    rows.sort(key=lambda r:int(r['object_id']))
    mosaics=[]
    if rows:
        tiles=sorted({int(r['tile_index']) for r in rows})
        sql="SELECT mosaic_product_oid,product_id,tile_index,file_name,file_path,datalabs_path,release_name,data_set_release,processing_mode,product_type,category,instrument_name FROM dr1.mosaic_product WHERE product_type='DpdMerBksMosaic' AND instrument_name='VIS' AND category='SCIENCE' AND data_set_release='"+release+"' AND tile_index IN ("+','.join(map(str,tiles))+')'
        mosaics=fetch(out,'pilot_mosaic_metadata',sql,reuse)
    records=compile_rows(rows,mosaics,policy)
    write(out/'DR1_first100_manifest.csv',records,list(dict.fromkeys(k for r in records for k in r)) if records else ['object_id','selection_policy'])
    report=dict(release=release,selection_policy=policy,confidence_threshold=.8,counts=counts,artifact_answer_populated_rows=artifact_available,selection_status='blocked_missing_artifact_answer' if policy=='strict-three-answer' and not any(artifact_available.values()) else 'provisional_not_Q1_equivalent' if policy=='provisional-two-answer' else 'selected',overlap_object_ids=overlap,total_distinct_objects=sum(c['distinct_objects'] for c in counts.values())-overlap,pilot_rows=len(records),pilot_order='ascending signed integer object_id across Wide and Deep survey, repeat/mode/visit products excluded; not a random/size representative sample',q1_training_warning_equivalence='not available; no equivalent flag imposed',count_scope='unique model-qualified catalogue IDs before image coverage checks; different IDs can still represent the same physical galaxy',utc=datetime.now(timezone.utc).isoformat())
    (out/'DR1_selection_counts.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2),flush=True)
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--limit',type=int,default=100);p.add_argument('--release',default='DR1_R2');p.add_argument('--disc-policy',choices=['strict-three-answer','provisional-two-answer'],default='strict-three-answer');p.add_argument('--reuse',action='store_true')
    a=p.parse_args();run(a.output_dir,a.limit,a.release,a.disc_policy,a.reuse)
