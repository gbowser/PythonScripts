from pathlib import Path
import csv,json
root=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry'); rows={r['object_id']:r for r in csv.DictReader((root/'MER_VIS_local_geometry_manifest.csv').open(encoding='utf-8-sig'))}
for oid in ['-623118358499243253','-527683439283031054','-639567775462084647','2652188688676008031']:
 r=rows[oid];p=list(csv.DictReader((root/'profiles'/f'Euclid_{oid}_MER_VIS_ellipse_profile.csv').open(encoding='utf-8-sig')))
 print(json.dumps({k:r[k] for k in ['object_id','codex_disc_pa_sky_deg','codex_bar_pa_sky_deg','codex_inclination_deg','codex_bar_min_arcsec','codex_bar_max_arcsec','codex_disc_min_arcsec','codex_disc_max_arcsec','codex_bar_eps_drop','codex_bar_pa_scatter_deg','codex_n_bar','codex_n_disc','codex_quality_flags','codex_radius_arcsec']}))
 print('bar points',[(z['sma_arcsec'],z['ellipticity'],z['pa_sky_deg']) for z in p if z['selected_bar'].lower()=='true'])
