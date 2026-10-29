import csv,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path('MER_VIS_review_tool').resolve()))
from centre_policy_MER_VIS import centre_measurement,numerical_acceptance
from review_policy_MER_VIS import centre_confirmation,adoption_status
base=Path('MER_VIS_adoption_2026_10_29');source=json.loads((base/'source_reviews.json').read_text())
snapshot=json.loads((base/'galaxies.json').read_text());trials=json.loads((base/'sensitivity/sensitivity_trials.json').read_text())
for oid,g in snapshot['galaxies'].items():
    g['centre_visually_confirmed']=centre_confirmation(source[oid],source[oid]['settings']['refit_id'],g['centre_reference'])
    g['saved_adoption']=adoption_status(source[oid],confirmation=g['centre_visually_confirmed'])
def number(v):
    try:
        n=float(v);return n if math.isfinite(n) else None
    except (ValueError,TypeError):return None
fixtures=[]
for t in trials:
    folder=Path(t['folder']);oid=t['id'];g=snapshot['galaxies'][oid];result=json.loads((folder/'result.json').read_text())
    ref=dict(x=result['centre_reference_x_pix'],y=result['centre_reference_y_pix'],provenance='sensitivity_probe_not_adopted')
    with (folder/'profiles'/f'Euclid_{oid}_MER_VIS_ellipse_profile.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    profile=[]
    for raw in rows:
        p={k:number(v) for k,v in raw.items()}
        for k in ('valid','used_for_geometry','selected_disc','selected_bar'):p[k]=raw.get(k,'').lower()=='true'
        p.update(centre_measurement(p,(ref['x'],ref['y']),g['pixel_scale_arcsec']),
                 numerically_accepted_strict=numerical_acceptance(p),numerically_accepted_relaxed=numerical_acceptance(p,True))
        p['marginal']=p['numerically_accepted_relaxed'];profile.append(p)
    fixtures.append(dict(id=oid,label=t['probe'],profile=profile,reference=ref,status=result['codex_fit_status'],folder=str(folder)))
(base/'experiment_input.json').write_text(json.dumps(dict(source=source,snapshot=snapshot,probes=fixtures),indent=2))
print('Prepared 19 baseline fits and 20 centre probes')
