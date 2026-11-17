"""Export all provisional DR1 barred candidates and redshift/distance metadata.

Catalogue HTTPS requests only. This program has no FITS or cutout download code.
Requires numpy, astropy and scipy; companion build_dr1_manifest.py owns the
unchanged morphology predicate and extraction-size calculation.
"""
import argparse,ast,concurrent.futures,csv,hashlib,io,json,math,time,urllib.parse,urllib.request
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from astropy.cosmology import Planck18
import astropy,scipy
from build_dr1_manifest import TAP,GROUPS,predicate,read,write,compile_rows

RELEASE='DR1_R2';POLICY='provisional-two-answer'
def fetch(out,name,sql,reuse):
    out.mkdir(parents=True,exist_ok=True)
    target=out/(name+'.csv');meta=out/(name+'_query.json')
    sha=hashlib.sha256(sql.encode()).hexdigest()
    if reuse and target.exists() and meta.exists():
        info=json.loads(meta.read_text())
        if info['sql_sha256']==sha and info['response_sha256']==hashlib.sha256(target.read_bytes()).hexdigest():return read(target)
    (out/(name+'.sql')).write_text(sql,encoding='utf8');start=time.perf_counter()
    req=urllib.request.Request(TAP,data=urllib.parse.urlencode(dict(REQUEST='doQuery',LANG='ADQL',FORMAT='csv',QUERY=sql,MAXREC=500000)).encode())
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=150) as response:body=response.read(256*1024*1024+1)
            break
        except Exception:
            if attempt==2:raise
            time.sleep(5)
    if len(body)>256*1024*1024:raise ValueError('Catalogue response exceeds safety bound')
    if body.lstrip().startswith(b'<'):raise ValueError('TAP XML/error response: '+body[:2000].decode(errors='replace'))
    rows=list(csv.DictReader(io.StringIO(body.decode('utf-8-sig'))))
    if len(rows)>=500000:raise ValueError('Possible TAP truncation: increase ceiling or partition query')
    temp=target.with_suffix('.tmp');temp.write_bytes(body);temp.replace(target)
    meta.write_text(json.dumps(dict(endpoint=TAP,sql_sha256=sha,response_sha256=hashlib.sha256(body).hexdigest(),rows=len(rows),seconds=time.perf_counter()-start,utc=datetime.now(timezone.utc).isoformat()),indent=2),encoding='utf8')
    print(f'{name}: {len(rows):,} rows ({time.perf_counter()-start:.1f}s)',flush=True)
    return rows

def queries(s):
    where=predicate('m',RELEASE,POLICY);join=f' FROM dr1.mer_morphology_{s} m JOIN '
    fields='m.object_id,m.data_set_release,'+','.join('m.'+f for g in GROUPS for f in g)
    yield s+'_selected',f'SELECT {fields} FROM dr1.mer_morphology_{s} m WHERE '+where
    yield s+'_count',f'SELECT COUNT(*) AS candidate_rows, COUNT(DISTINCT m.object_id) AS distinct_objects FROM dr1.mer_morphology_{s} m WHERE '+where
    fields='m.object_id,c.right_ascension AS ra_deg,c.declination AS dec_deg,c.tile_index,c.segmentation_area,c.semimajor_axis AS semimajor_axis_pix,c.ellipticity,c.vis_det,c.mag_stargal_sep,c.basic_download_data_oid AS catalogue_product_oid'
    yield s+'_positions',f'SELECT {fields}'+join+f'dr1.mer_catalogue_{s} c ON m.object_id=c.object_id AND m.data_set_release=c.data_set_release WHERE '+where
    fields='m.object_id,'+','.join(f'k.corner_{i}_{axis}' for i in range(4) for axis in ['ra','dec'])
    yield s+'_corners',f'SELECT {fields}'+join+f'dr1.mer_cutouts_{s} k ON m.object_id=k.object_id AND m.data_set_release=k.data_set_release WHERE '+where
    photo='wide' if s=='wide_survey' else 'deep_survey'
    fields='m.object_id,p.data_set_release AS phz_release,'+','.join('p.'+f for f in ['phz_median','phz_flags','phz_classification','phz_weight','phz_70_int','phz_90_int','phz_95_int','phz_mode_1','phz_mode_2','phz_mode_1_area','phz_mode_2_area'])
    yield s+'_photoz',f'SELECT {fields}'+join+f'dr1.phz_photo_z_{photo} p ON m.object_id=p.object_id AND m.data_set_release=p.data_set_release WHERE '+where
    spec='wide_survey' if s=='wide_survey' else 'deep'
    fields='m.object_id,s.data_set_release AS spe_release,'+','.join('s.'+f for f in ['spe_z','spe_z_err','spe_z_rel','spe_z_prob','spe_rank'])
    yield s+'_specz',f'SELECT {fields}'+join+f'dr1.spectro_z_spe_galaxy_candidates_{spec} s ON m.object_id=s.object_id AND m.data_set_release=s.data_set_release WHERE '+where+' AND s.spe_rank=1'
    fields='m.object_id,q.data_set_release AS spe_quality_release,'+','.join('q.'+f for f in ['spe_warning_flag','spe_error_flag','spe_gal_warning_flag','spe_gal_error_flag','spe_class_warning_flag','spe_class_error_flag'])
    yield s+'_spec_quality',f'SELECT {fields}'+join+f'dr1.spectro_z_spe_quality_{spec} q ON m.object_id=q.object_id AND m.data_set_release=q.data_set_release WHERE '+where

def number(value):
    try:
        v=float(value)
        return v if math.isfinite(v) else None
    except (ValueError,TypeError):return None

def interval(value):
    try:
        parts=str(value).strip('()[] ').split(',')
        if len(parts)!=2:return None
        lo,hi=map(number,parts)
        if lo is not None and hi is not None and 0<=lo<=hi<=6:return lo,hi
    except (ValueError,TypeError):pass
    return None

def index(rows):
    result=defaultdict(list)
    for row in rows:result[row['object_id']].append(row)
    return result

def distance_values(z):
    # Exactly evaluate unique requested redshifts, without interpolation.
    zz=np.array(sorted(z),dtype=float)
    dc=Planck18.comoving_distance(zz).value
    da=dc/(1+zz);dl=dc*(1+zz)
    lookback=Planck18.lookback_time(zz).value
    return {float(v):dict(comoving_distance_mpc=float(c),angular_diameter_distance_mpc=float(a),luminosity_distance_mpc=float(l),lookback_time_gyr=float(t),kpc_per_arcsec=float(a*1000*np.pi/(180*3600))) for v,c,a,l,t in zip(zz,dc,da,dl,lookback)}

SUMMARY_FIELDS=['manifest_rank','object_id','survey','data_set_release','ra_deg','dec_deg','tile_index','requested_width_arcsec','disc_fraction','not_edge_on_fraction','spiral_fraction','bar_fraction','redshift','redshift_source','redshift_quality','redshift_70_lower','redshift_70_upper','phz_flags','phz_classification','spe_z','spe_z_err','spe_z_rel','spe_quality_status','comoving_distance_mpc','angular_diameter_distance_mpc','luminosity_distance_mpc','lookback_time_gyr','kpc_per_arcsec','distance_quality','metadata_status','selection_policy']

def run(output,reuse=True,workers=3):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);evidence=output/'query_evidence'
    tasks=[]
    def export_checked(name,sql):
        if name.endswith(('_selected','_count')):return fetch(evidence,name,sql,reuse)
        control_sql='SELECT COUNT(*) AS n'+sql[sql.index(' FROM '):]
        controls=fetch(evidence,name+'_control',control_sql,reuse)
        expected=int(controls[0]['n']);target=evidence/(name+'.csv');meta=evidence/(name+'_query.json')
        cache_valid=reuse and target.exists() and meta.exists() and json.loads(meta.read_text()).get('response_sha256')==hashlib.sha256(target.read_bytes()).hexdigest()
        existing=read(target) if cache_valid else []
        selected=read(evidence/(name.split('_',2)[0]+'_'+name.split('_',2)[1]+'_selected.csv'))
        selected_ids={r['object_id'] for r in selected}
        if cache_valid and len(existing)==expected and all(r['object_id'] in selected_ids for r in existing):
            validation=dict(method='server_count_reconciled',expected_rows=expected,exported_rows=len(existing),selected_id_membership_verified=True)
        else:
            from direct_batches import collect
            existing=collect(evidence,name,selected,reuse)
            if len(existing)!=expected:raise ValueError(f'{name}: incomplete export ({len(existing)} versus {expected})')
            if len({r['object_id'] for r in existing})!=len(existing):raise ValueError('Duplicate direct metadata IDs')
            if not all(r['object_id'] in selected_ids for r in existing):raise ValueError('Unexpected metadata ID')
            write(target,existing)
            reference=evidence/(name+'.sql')
            if reference.exists():reference.replace(evidence/(name+'_reference_join.sql'))
            validation=dict(method='bounded_direct_batches_server_count_reconciled',expected_rows=expected,exported_rows=len(existing),selected_id_membership_verified=True)
            meta.write_text(json.dumps(dict(response_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),rows=len(existing),completion_method=validation['method'],batch_queries='batches/'+name+'_*.sql',utc=datetime.now(timezone.utc).isoformat()),indent=2))
        (evidence/(name+'_validation.json')).write_text(json.dumps(validation,indent=2))
    # ID lists and control counts must be available before bounded metadata retrieval.
    for survey in ['wide_survey','deep_survey']:
        for name,sql in queries(survey):
            if name.endswith(('_selected','_count')):export_checked(name,sql)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for survey in ['wide_survey','deep_survey']:
            for name,sql in queries(survey):
                if not name.endswith(('_selected','_count')):tasks.append(pool.submit(export_checked,name,sql))
        for future in concurrent.futures.as_completed(tasks):future.result()
    records=[];count_controls={};duplicate_metadata=[]
    for survey in ['wide_survey','deep_survey']:
        selected=read(evidence/(survey+'_selected.csv'))
        control=read(evidence/(survey+'_count.csv'))[0]
        assert len(selected)==len({r['object_id'] for r in selected})==int(control['distinct_objects'])==int(control['candidate_rows']), 'Export/control counts differ'
        count_controls[survey]=len(selected)
        indices={kind:index(read(evidence/(survey+'_'+kind+'.csv'))) for kind in ['positions','corners','photoz','specz','spec_quality']}
        for r in selected:
            row=dict(r,survey=survey,selection_policy=POLICY,q1_training_warning_equivalence='unavailable; not imposed',cosmology='Astropy Planck18',sky_frame='ICRS')
            statuses=[]
            for kind,idx in indices.items():
                matches=idx.get(r['object_id'],[]);row[kind+'_match_count']=len(matches)
                if len(matches)==1:row.update({k:v for k,v in matches[0].items() if k!='object_id'})
                elif len(matches)>1:
                    duplicate_metadata.extend(dict(survey=survey,metadata_kind=kind,**m) for m in matches)
                    statuses.append('ambiguous_'+kind)
                elif kind=='positions':statuses.append('missing_positions')
            if row.get('positions_match_count')==1:
                try:row=compile_rows([row],[],POLICY)[0]
                except ValueError:statuses.append('invalid_position_or_model')
            else:
                for name,fields,n in [('disc_fraction',GROUPS[0][:2],1),('not_edge_on_fraction',GROUPS[1],1),('spiral_fraction',GROUPS[2],1),('bar_fraction',GROUPS[3],2)]:
                    vals=[float(row[f]) for f in fields];row[name]=sum(vals[:n])/sum(vals)
            row.pop('pilot_rank',None);row.pop('mosaic_candidates',None);row.pop('mosaic_selection_status',None)
            for confidence in [70,90,95]:
                bounds=interval(row.get(f'phz_{confidence}_int'))
                row[f'redshift_{confidence}_lower']=bounds[0] if bounds else ''
                row[f'redshift_{confidence}_upper']=bounds[1] if bounds else ''
                row[f'phz_{confidence}_interval_status']='valid' if bounds else 'missing_or_invalid'
            z=number(row.get('phz_median'))
            if z is not None and 0<z<=6:
                quality='photoz_flags_zero' if number(row.get('phz_flags'))==0 else 'photoz_flagged_or_flags_missing'
                if number(row.get('phz_classification'))!=2:quality+=';classification_requires_review'
                row.update(redshift=z,redshift_source='photometric_phz_median',redshift_quality=quality,distance_quality='photometric_estimate_check_flags_classification_and_intervals')
            else:row.update(redshift='',redshift_source='unavailable',redshift_quality='no_valid_positive_photoz',distance_quality='unavailable_no_valid_photoz')
            # Rank-one spectra are candidates, not accepted measurements. No
            # uncalibrated SPE reliability threshold silently overrides photo-z.
            row['spe_quality_status']='candidate_requires_review' if row.get('specz_match_count')==1 else 'ambiguous_candidates' if row.get('specz_match_count',0)>1 else 'no_matching_rank1_spectrum'
            row['metadata_status']=';'.join(statuses) if statuses else 'matched'
            records.append(row)
    # Cross-survey ID equality only; not angular/physical source deduplication.
    ids=defaultdict(list)
    for row in records:ids[row['object_id']].append(row)
    overlap=sum(len(v)>1 for v in ids.values())
    if overlap:raise ValueError('Shared survey IDs need explicit merge policy; records retained in evidence')
    records.sort(key=lambda r:int(r['object_id']))
    zs=set()
    for row in records:
        if row['redshift']!='':
            zs.add(row['redshift'])
            for field in ['redshift_70_lower','redshift_70_upper']:
                if row[field]!='':zs.add(float(row[field]))
    print(f'Computing Planck18 distances at {len(zs):,} unique redshifts',flush=True)
    distances=distance_values(zs) if zs else {}
    for rank,row in enumerate(records,1):
        row['manifest_rank']=rank
        if row['redshift']!='':
            row.update(distances[row['redshift']])
            for bound in ['lower','upper']:
                z=row['redshift_70_'+bound]
                if z!='':
                    for field in ['comoving_distance_mpc','luminosity_distance_mpc','lookback_time_gyr']:
                        row[field+'_70_'+bound]=distances[float(z)][field]
    write(output/'DR1_all_qualifying_detail.csv',records)
    summary=[{f:r.get(f,'') for f in SUMMARY_FIELDS} for r in records]
    write(output/'DR1_all_qualifying_summary.csv',summary,SUMMARY_FIELDS)
    if duplicate_metadata:write(output/'DR1_ambiguous_metadata.csv',duplicate_metadata)
    totals=[]
    for survey in ['wide_survey','deep_survey','ALL']:
        rr=[r for r in records if survey=='ALL' or r['survey']==survey]
        totals.append(dict(survey=survey,qualifying_ids=len(rr),position_matches=sum(r['positions_match_count']==1 for r in rr),photoz_matches=sum(r['photoz_match_count']==1 for r in rr),valid_positive_photoz=sum(r['redshift']!='' for r in rr),photoz_flags_zero=sum(number(r.get('phz_flags'))==0 for r in rr),rank1_spectrum_matches=sum(r['specz_match_count']==1 for r in rr),usable_cutout_size=sum(number(r.get('requested_width_arcsec')) is not None for r in rr)))
    write(output/'DR1_population_summary.csv',totals)
    report=dict(utc=datetime.now(timezone.utc).isoformat(),release=RELEASE,policy=POLICY,counts=count_controls,overlap_ids=overlap,total_ids=len(records),population_summary=totals,cosmology=str(Planck18),astropy_version=astropy.__version__,scipy_version=scipy.__version__,distance_redshift_policy='Photometric median baseline only, including flagged estimates with explicit flags. Rank-one spectra retained as candidates; no unvalidated automatic preference.',fits_downloaded=0,physical_source_deduplication=False)
    (output/'DR1_manifest_summary.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--refresh',action='store_true');p.add_argument('--workers',type=int,choices=[1,2,3],default=3)
    a=p.parse_args();run(a.output_dir,not a.refresh,a.workers)
