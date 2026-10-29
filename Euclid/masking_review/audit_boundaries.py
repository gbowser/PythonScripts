"""Read-only outer-disc eligibility audit across the entire exported catalogue."""
import csv
import json
from pathlib import Path
import masking_core as core


def main():
    rows = core.catalogue(core.DEFAULT_CATALOGUE, all_targets=True)
    saved = json.loads((core.HERE.parent / 'reports/MER_VIS_review_2026-10-29/source_reviews_completed.json').read_text(encoding='utf8'))
    findings = []
    for row in rows:
        geometry = dict(scale=1., disc_min=core.number(row,'codex_disc_min_arcsec'),
                        disc_max=core.number(row,'codex_disc_max_arcsec'), bar_max=core.number(row,'codex_bar_max_arcsec'))
        record = saved.get(row['object_id'], {})
        settings = record.get('settings', {})
        if row.get('review_refit_id') and settings.get('refit_id') == row['review_refit_id']:
            if settings.get('disc'):
                geometry['disc_min'], geometry['disc_max'] = settings['disc']
            if settings.get('bar'):
                geometry['bar_max'] = settings['bar'][1]
        finding = dict(object_id=row['object_id'], previous_interval_edge_arcsec=geometry['disc_max'],
                       outer_disc_arcsec='', boundary_arcsec='', source='', status='', reason='')
        try:
            profile, path = core.measured_profile(row)
            ellipse = core.outer_disc_ellipse(profile, geometry)
            finding.update(outer_disc_arcsec=ellipse['sma_arcsec'],boundary_arcsec=ellipse['sma_arcsec']*1.3,
                           source=ellipse['source'], status='available')
        except (ValueError, OSError, KeyError) as exc:
            finding.update(status='requires_outer_disc_review', reason=str(exc))
        findings.append(finding)
    output = core.HERE / 'validation_output/boundary_audit'
    output.mkdir(parents=True,exist_ok=True)
    with (output/'boundary_audit.csv').open('w',newline='',encoding='utf8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(findings[0]));writer.writeheader();writer.writerows(findings)
    summary=dict(total=len(findings), available=sum(r['status']=='available' for r in findings),
                 requires_outer_disc_review=sum(r['status']!='available' for r in findings),
                 expanded_from_measurement_interval=sum(r['status']=='available' and
                       r['outer_disc_arcsec']>float(r['previous_interval_edge_arcsec'] or 0)+1e-8 for r in findings),
                 policy='historical_outer_disc_audit')
    core.json_write(output/'summary.json',summary)
    print(summary,flush=True)


if __name__=='__main__':
    main()
