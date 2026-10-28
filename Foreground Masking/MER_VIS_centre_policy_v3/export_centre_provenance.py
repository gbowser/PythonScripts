from pathlib import Path
p=Path('MER_VIS_review_tool/review_MER_VIS.py');s=p.read_text(encoding='utf8');needle='        with self.lock:\n            updated = dict(self.reviews); updated[oid] = clean(record)'
addition='''        reference=self.galaxy(oid,settings.get('refit_id')).get('centre_reference',{})
        rules=settings.get('rules',{});calc=payload.get('calculation') or {}
        record.update(review_campaign=(self.campaign or {}).get('campaign_id','original'),
                      centre_policy_version=settings.get('centre_policy_version',''),centre_reference_x_pix=reference.get('x'),centre_reference_y_pix=reference.get('y'),centre_reference_provenance=reference.get('provenance'),
                      centre_cap_native_pixels=rules.get('centre_cap_native'),centre_fraction_radius=rules.get('centre_fraction'),centre_floor_native_pixels=rules.get('centre_floor_native'),centre_screen_enabled=rules.get('centre_enabled'),refit_id=settings.get('refit_id'),
                      centre_rejected_disc_n=len(calc.get('centre_rejected_disc',[])),centre_rejected_bar_n=len(calc.get('centre_rejected_bar',[])),trial_disc_pa_provisional=calc.get('disc_pa_provisional'))
'''
assert needle in s;s=s.replace(needle,addition+needle,1)
s=s.replace('"trial_disc_eps_span","settings_json","source_manifest_sha256"]', '"trial_disc_eps_span","settings_json","source_manifest_sha256","review_campaign","refit_id","centre_policy_version","centre_reference_x_pix","centre_reference_y_pix","centre_reference_provenance","centre_cap_native_pixels","centre_fraction_radius","centre_floor_native_pixels","centre_screen_enabled","centre_rejected_disc_n","centre_rejected_bar_n","trial_disc_pa_provisional"]',1)
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_review_tool/README_MER_VIS_REVIEW.md');s=p.read_text(encoding='utf8');s='''> Active centre-acceptance re-review: the usual launcher now opens a separate 19-galaxy round. Read [CENTRE_POLICY_MER_VIS_REVIEW.md](CENTRE_POLICY_MER_VIS_REVIEW.md) for the new reference-centre checks, comparison columns and residual diagnostics. Earlier reviews and notes remain under `saved_reviews`; the new round uses `saved_reviews_centre_v3`. Use `Start Original MER VIS Review.cmd` to reopen the completed original review.

'''+s;p.write_text(s,encoding='utf8')
