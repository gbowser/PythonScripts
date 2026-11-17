"""Internal bounded metadata retrieval used by build_dr1_full_manifest.py."""
from build_dr1_full_manifest import *
def run_batch(survey,kind,ids,batch,evidence=None,reuse=True,suffix=''):
    cols={
        'positions':'right_ascension AS ra_deg,declination AS dec_deg,tile_index,segmentation_area,semimajor_axis AS semimajor_axis_pix,ellipticity,vis_det,mag_stargal_sep,basic_download_data_oid AS catalogue_product_oid',
        'corners':','.join(f'corner_{i}_{a}' for i in range(4) for a in ['ra','dec']),
        'photoz':'data_set_release AS phz_release,phz_median,phz_flags,phz_classification,phz_weight,phz_70_int,phz_90_int,phz_95_int,phz_mode_1,phz_mode_2,phz_mode_1_area,phz_mode_2_area',
        'specz':'data_set_release AS spe_release,spe_z,spe_z_err,spe_z_rel,spe_z_prob,spe_rank',
        'spec_quality':'data_set_release AS spe_quality_release,spe_warning_flag,spe_error_flag,spe_gal_warning_flag,spe_gal_error_flag,spe_class_warning_flag,spe_class_error_flag'}
    spec='wide_survey' if survey=='wide_survey' else 'deep'
    table=('mer_catalogue_'+survey if kind=='positions' else 'mer_cutouts_'+survey if kind=='corners' else 'phz_photo_z_'+('wide' if survey=='wide_survey' else 'deep_survey') if kind=='photoz' else 'spectro_z_spe_galaxy_candidates_'+spec if kind=='specz' else 'spectro_z_spe_quality_'+spec)
    q=f"SELECT object_id,{cols[kind]} FROM dr1.{table} WHERE data_set_release='DR1_R2' AND object_id IN ("+','.join(ids)+')'
    if kind=='corners':
        fields='m.object_id,'+','.join('k.'+f'corner_{i}_{a}' for i in range(4) for a in ['ra','dec'])
        q=f'SELECT {fields} FROM dr1.mer_morphology_{survey} m JOIN dr1.mer_cutouts_{survey} k ON m.object_id=k.object_id AND m.data_set_release=k.data_set_release WHERE '+predicate('m','DR1_R2','provisional-two-answer')+f' AND m.object_id >= {min(map(int,ids))} AND m.object_id <= {max(map(int,ids))}'
    if kind=='specz':q+=' AND spe_rank=1'
    if evidence is None:raise ValueError('Pass the requested output evidence directory')
    rows=fetch(evidence/'batches',f'{survey}_{kind}_{batch:03}{suffix}',q,reuse)
    if kind in ['positions','corners'] and (len(rows)!=len(ids) or {r['object_id'] for r in rows}!=set(ids)):
        if len(ids)<=100:raise ValueError('Metadata missing even in a small bounded batch')
        mid=len(ids)//2
        print(f'{survey} {kind} batch{batch}{suffix}: split incomplete response',flush=True)
        rows=run_batch(survey,kind,ids[:mid],batch,evidence,reuse,suffix+'a')+run_batch(survey,kind,ids[mid:],batch,evidence,reuse,suffix+'b')
    return rows
def collect(evidence,name,selected,reuse):
    survey='wide_survey' if name.startswith('wide_survey') else 'deep_survey'
    kind=name[len(survey)+1:];ids=sorted((r['object_id'] for r in selected),key=int)
    batches=[ids[:10000]]+[ids[start:start+25000] for start in range(10000,len(ids),25000)]
    rows=[]
    for i,chunk in enumerate(batches):rows.extend(run_batch(survey,kind,chunk,i,evidence,reuse))
    return rows
