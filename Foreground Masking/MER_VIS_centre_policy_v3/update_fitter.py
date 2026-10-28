from pathlib import Path
p=Path('MER_VIS_review_tool/fit_manual_centre_MER_VIS.py');s=p.read_text(encoding='utf8')
s=s.replace("VERSION='MER_VIS_manual_centre_review_v1_2026-10-21'", "VERSION='MER_VIS_centre_constrained_v3_2026-10-28'\nfrom centre_policy_MER_VIS import POLICY_VERSION, DEFAULT_POLICY, checked_policy, centre_measurement, numerical_acceptance\nCENTRE_POLICY=dict(DEFAULT_POLICY)\nREFERENCE_CENTRE=None\nNATIVE_SCALE=None")
s=s.replace(' return out\n\ndef accepted', " for point in out:\n  point.update(centre_measurement(point,REFERENCE_CENTRE,NATIVE_SCALE,CENTRE_POLICY))\n  point.update(numerically_accepted_strict=numerical_acceptance(point),numerically_accepted_relaxed=numerical_acceptance(point,True))\n return out\n\ndef accepted",1)
a=s.index('def accepted(p,relaxed=False):');b=s.index('\ndef measure(',a)
s=s[:a]+'''def accepted(p,relaxed=False):
 # A relaxed numerical fit never relaxes the common centre-eligibility rule.
 return numerical_acceptance(p,relaxed) and p.get('centre_accepted',False)
''' +s[b:]
s=s.replace('def measure(task):\n', 'def measure(task):\n global REFERENCE_CENTRE,NATIVE_SCALE\n',1)
s=s.replace("wcs=WCS(h).celestial;scale=np.sqrt(abs(np.linalg.det(wcs.pixel_scale_matrix)))*3600", "wcs=WCS(h).celestial;scale=np.sqrt(abs(np.linalg.det(wcs.pixel_scale_matrix)))*3600\n   REFERENCE_CENTRE=(x0,y0);NATIVE_SCALE=float(scale)\n   r.update(centre_reference_x_pix=x0,centre_reference_y_pix=y0,centre_policy_version=POLICY_VERSION,centre_policy=checked_policy(CENTRE_POLICY))",1)
s=s.replace("if len(good)>len(best_good):best=p;best_good=good;", "if (len(good),sum(numerical_acceptance(z,True) for z in p),len(p))>(len(best_good),sum(numerical_acceptance(z,True) for z in best),len(best)):best=p;best_good=good;",1)
s=s.replace('if inner and not MANUAL_LOCK:', 'if False: # Explicit reference stays fixed; inner ellipses cannot redefine it.')
# Remove the obsolete displacement-referencing block rather than leave unreachable code.
a=s.index('    if False: # Explicit reference');b=s.index('    if len(best_good)<8:',a)
s=s[:a]+s[b:]
s=s.replace('codex_fit_centre_x_pix=centre_x,codex_fit_centre_y_pix=centre_y', 'codex_fit_centre_x_pix=x0,codex_fit_centre_y_pix=y0')
s=s.replace("  if len(good)<3:raise ValueError", "  for z in profile:z.update(used_for_geometry=bool(accepted(z,relaxed)),selected_disc=False,selected_bar=False)\n  r.update(codex_fit_centre_x_pix=x0,codex_fit_centre_y_pix=y0,centre_reference_x_pix=x0,centre_reference_y_pix=y0,centre_policy_version=POLICY_VERSION)\n  if len(good)<3:raise ValueError",1)
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/refit_MER_VIS.py');s=p.read_text(encoding='utf8');s=s.replace("    engine.MANUAL_LOCK=request['lock_centre']", "    engine.MANUAL_LOCK=request['lock_centre']\n    from centre_policy_MER_VIS import checked_policy\n    engine.CENTRE_POLICY=checked_policy(request.get('centre_policy'))")
s=s.replace("source_manifest_sha256=self.digest,\n                           engine_sha256", "source_manifest_sha256=self.digest,\n                           centre_policy=__import__('centre_policy_MER_VIS').checked_policy(payload.get('centre_policy')),\n                           reference_provenance=payload.get('reference_provenance','manual_selection'),\n                           engine_sha256",1)
s=s.replace("manual_refit_requires_visual_review=True)", "manual_refit_requires_visual_review=True,centre_reference_provenance=request.get('reference_provenance','manual_selection'),centre_policy=engine.CENTRE_POLICY)",1)
p.write_text(s,encoding='utf8')
