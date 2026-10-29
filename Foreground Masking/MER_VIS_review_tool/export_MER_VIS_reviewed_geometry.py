"""Overlay reviewed adoption decisions on the full library; retain original columns.

Writes a new manifest. Unreviewed objects retain measurements but are not silently
promoted to visually approved geometry. Sensitivity results, when supplied, can
downgrade automatic readiness; they never override a human assessment.
"""
import argparse,csv,hashlib,json
from pathlib import Path
from review_policy_MER_VIS import centre_confirmation,adoption_status

def export(catalogue, reviews, output, sensitivity=None):
    catalogue=Path(catalogue);reviews=Path(reviews);output=Path(output)
    if output.resolve()==catalogue.resolve():raise ValueError('Use a new output path')
    source=json.loads((reviews/'MER_VIS_saved_reviews.json').read_text())
    experiments={r['id']:r for r in (sensitivity or [])}
    with catalogue.open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
    for row in rows:
        r=source.get(row['object_id']);c=(r or {}).get('calculation',{})
        ref=dict(x=(r or {}).get('centre_reference_x_pix'),y=(r or {}).get('centre_reference_y_pix'))
        job=(r or {}).get('settings',{}).get('refit_id')
        # Compare with actual stored geometry, not a reference copied from the review itself.
        if job:
            result=json.loads((reviews/'refits'/job/'result.json').read_text())
            ref=dict(x=float(result.get('centre_reference_x_pix',result['codex_fit_centre_x_pix'])),
                     y=float(result.get('centre_reference_y_pix',result['codex_fit_centre_y_pix'])))
        status=adoption_status(r,confirmation=centre_confirmation(r,job,ref))
        experiment=experiments.get(row['object_id'])
        if experiment and experiment.get('sensitivity_requires_attention'):
            status['automatic_deprojection_ready']=False
            if status['adoption_status']=='reviewed_supported':status['adoption_status']='reviewed_provisional'
            status['adoption_reason']+='; sensitivity experiment requires attention'
        row.update(status)
        for key in ('raw_issues','effective_issues'):row[key]='; '.join(row[key])
        row.update(reviewed=bool(r and r.get('reviewed')),review_disc_decision=(r or {}).get('disc_decision','not_assessed'),
                   review_bar_decision=(r or {}).get('bar_decision','not_assessed'),review_centre_decision=(r or {}).get('centre_decision','not_assessed'),
                   review_notes=(r or {}).get('notes',''),review_refit_id=job or '',
                   review_reference_x_pix=ref.get('x'),review_reference_y_pix=ref.get('y'),
                   review_centre_provenance=(r or {}).get('centre_reference_provenance',''),
                   review_fits_path=row.get('fits_path',''),review_source_sha256=hashlib.sha256((reviews/'MER_VIS_saved_reviews.json').read_bytes()).hexdigest())
        for k in ('disc_pa','bar_pa','inclination','n_disc','n_bar','pa_scatter','eps_span','span_arcsec','max_gap_fraction','face_on'):
            row['review_selected_'+k]=c.get(k)
        row['sensitivity_summary_json']=json.dumps(experiment) if experiment else ''
    fields=list(dict.fromkeys(k for row in rows for k in row))
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    output.with_suffix('.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--catalogue',type=Path,required=True)
    p.add_argument('--reviews',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--sensitivity',type=Path);a=p.parse_args()
    result=export(a.catalogue,a.reviews,a.output,json.loads(a.sensitivity.read_text()) if a.sensitivity else None)
    from collections import Counter
    print(dict(Counter(r['adoption_status'] for r in result)))
