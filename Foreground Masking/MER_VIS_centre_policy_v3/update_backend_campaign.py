from pathlib import Path
p=Path('MER_VIS_review_tool/fit_manual_centre_MER_VIS.py');s=p.read_text(encoding='utf8');s=s.replace('# Re-reference centre from inner converged isophotes, then explicitly relax.', '# Keep the explicit reference; only numerical criteria may be relaxed.').replace("method='recentred_relaxed' if inner else 'relaxed'", "method='relaxed_same_reference'")
s=s.replace('np.hypot(centre_x-catalogue_x,centre_y-catalogue_y)', 'np.hypot(x0-catalogue_x,y0-catalogue_y)').replace("(z['x_original_pix']-centre_x)**2+(z['y_original_pix']-centre_y)**2", "(z['x_original_pix']-x0)**2+(z['y_original_pix']-y0)**2")
s=s.replace('codex_centre_scatter_arcsec=centre_scatter)', 'codex_centre_scatter_arcsec=centre_scatter,measured_disc_centre_median_x_pix=centre_x,measured_disc_centre_median_y_pix=centre_y)',1)
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/review_MER_VIS.py');s=p.read_text(encoding='utf8');s=s.replace('from refit_MER_VIS import ReviewRefits', 'from refit_MER_VIS import ReviewRefits\nfrom centre_policy_MER_VIS import POLICY_VERSION,DEFAULT_POLICY,centre_measurement,numerical_acceptance')
s=s.replace('def __init__(self, data_root, output):','def __init__(self, data_root, output, campaign=None):',1)
s=s.replace('self.data_root, self.output = data_root, output','self.data_root, self.output = data_root, output\n        self.campaign = campaign',1)
s=s.replace('if sample_path.exists():','if campaign:\n            self.sample_document=dict(app=APP_ID,source_sha256=self.digest,sample=campaign["sample"],campaign=campaign["campaign_id"])\n            self.sample=self.sample_document["sample"]\n            atomic_json(sample_path,self.sample_document)\n        elif sample_path.exists():',1)
s=s.replace('compass=compass, compass_pixel_basis=compass_pixel_basis, default_window=window, original=original,', 'compass=compass, compass_pixel_basis=compass_pixel_basis, default_window=window, original=original,\n                          centre_reference=dict(x=row.get("centre_reference_x_pix",centre[0]),y=row.get("centre_reference_y_pix",centre[1]),provenance=row.get("centre_reference_provenance","legacy_fit_disc_median"),version=POLICY_VERSION,policy=DEFAULT_POLICY),\n                          previous_review=(self.campaign or {}).get("previous_reviews",{}).get(oid),\n                          campaign_case=(self.campaign or {}).get("cases",{}).get(oid),',1)
# Annotate profiles per response, since cached raw profiles also serve original/selected refits.
needle='        profile = self.profile_cache[cache_key]'
s=s.replace(needle,'''        reference=[number(row.get('centre_reference_x_pix')),number(row.get('centre_reference_y_pix'))]
        if any(v is None for v in reference):reference=centre
        profile=[dict(p,**centre_measurement(p,reference,float(scale)),numerically_accepted_strict=numerical_acceptance(p),numerically_accepted_relaxed=numerical_acceptance(p,True)) for p in self.profile_cache[cache_key]]
''',1)
s=s.replace('x=row.get("centre_reference_x_pix",centre[0]),y=row.get("centre_reference_y_pix",centre[1])','x=reference[0],y=reference[1]')
s=s.replace('categories=CATEGORIES,rules=DEFAULT_RULES,reviews=', 'categories=(self.server.store.campaign or {}).get("categories",CATEGORIES),rules=DEFAULT_RULES,centre_policy=dict(version=POLICY_VERSION,**DEFAULT_POLICY),campaign=self.server.store.campaign,reviews=',1)
s=s.replace('p.add_argument("--port",type=int,default=8768)', 'p.add_argument("--port",type=int,default=8768)\n    p.add_argument("--campaign",type=Path)')
s=s.replace('a=p.parse_args(); store=Store(a.data_root,a.output)', 'a=p.parse_args(); campaign=json.loads(a.campaign.read_text(encoding="utf8")) if a.campaign else None; store=Store(a.data_root,a.output,campaign)')
p.write_text(s,encoding='utf8')
