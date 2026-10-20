from pathlib import Path
p=Path('MER_VIS_pipeline_v2/finalize_MER_VIS_geometry.py');s=p.read_text(encoding='utf-8-sig');needle="assert len(rows)==2777";add="""override_path=Path(__file__).parent/'MER_VIS_geometry_review_overrides.csv'
review_audit=[]
if override_path.exists():
 overrides={z['object_id']:z for z in csv.DictReader(override_path.open(encoding='utf-8-sig'))}
 for r in rows:
  override=overrides.get(r['object_id'])
  if not override:continue
  if override['action']!='reject_geometry':raise ValueError('Unknown review action')
  review_audit.append(dict(object_id=r['object_id'],candidate_status=r['codex_fit_status'],reason=override['reason']))
  for key in ['disc_pa_sky_deg','bar_pa_sky_deg','inclination_deg','disc_axis_ratio','disc_pa_scatter_deg','bar_pa_scatter_deg','bar_min_arcsec','bar_max_arcsec','disc_min_arcsec','disc_max_arcsec','fit_centre_x_pix','fit_centre_y_pix','centre_offset_arcsec','centre_scatter_arcsec']:
   r['codex_'+key]=''
  r.update(codex_fit_status='fit_failed',codex_bar_status='not_measured',codex_quality_flags='',codex_information='',codex_error=override['reason'],codex_n_good=0,codex_review_action='reject_geometry',codex_review_reason=override['reason'])
  pp=a.geometry_dir/'profiles'/f\"Euclid_{r['object_id']}_MER_VIS_ellipse_profile.csv\"
  if pp.exists():
   diagnostic=list(csv.DictReader(pp.open(encoding='utf8')))
   for z in diagnostic:z.update(used_for_geometry=False,selected_disc=False,selected_bar=False)
   write_csv(pp,diagnostic)
(a.geometry_dir/'MER_VIS_visual_review_audit.json').write_text(json.dumps(dict(overrides_sha256=hashlib.sha256(override_path.read_bytes()).hexdigest() if override_path.exists() else None,decisions=review_audit),indent=2))
""";assert needle in s;s=s.replace(needle,add+'\n'+needle);p.write_text(s,encoding='utf8')
# Include all warnings in current reports, including final mask removal review.
p=Path('MER_VIS_pipeline_v2/build_current_MER_VIS_documents.py');s=p.read_text(encoding='utf-8-sig');s=s.replace("A returned result is provisional, not proof", "The final recovery pass includes visual exclusions for a foreground-star switch and an unresolved core. A returned result is provisional, not proof")
s=s.replace("A final retry can remove a fragmented neighbour mask with mild smoothing;", "A broader extended-light peak is also tested for failed cases, rather than accepting a nearby bright knot. Candidate centres still require checking for foreground-star switches and unresolved cores. Two such candidates were excluded by explicit visual-review overrides in this run. A final retry can remove a fragmented neighbour mask with mild smoothing;")
p.write_text(s,encoding='utf8')
