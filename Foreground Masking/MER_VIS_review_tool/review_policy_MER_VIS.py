"""Effective review/adoption status; raw measurements and warnings remain intact."""
import math

VERSION = 'MER_VIS_review_adoption_2026-10-29'

def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)

def centre_confirmation(review, refit_id, reference):
    """A confirmation belongs to an exact fit and physical reference, not an ID alone."""
    if not review or not review.get('reviewed') or review.get('centre_decision') != 'looks_correct':
        return False
    reviewed_id = review.get('refit_id', review.get('settings', {}).get('refit_id'))
    if reviewed_id != refit_id:
        return False
    for axis in ('x', 'y'):
        before = review.get(f'centre_reference_{axis}_pix')
        after = reference.get(axis)
        if not finite(before) or not finite(after) or abs(before-after) > 1e-6:
            return False
    return True

def adoption_status(review, calculation=None, confirmation=False):
    """Visual approval permits provisional values, not unsupported automatic transforms."""
    c = calculation if calculation is not None else (review or {}).get('calculation', {})
    raw = list(c.get('issues', []))
    effective = [i for i in raw if not (confirmation and i.startswith('Centre reference unverified'))]
    out = dict(review_policy_version=VERSION, centre_visually_confirmed=confirmation,
               raw_issues=raw, effective_issues=effective, automatic_deprojection_ready=False,
               adopted_disc_pa_deg=None, adopted_inclination_deg=None, adopted_bar_pa_deg=None)
    if not review or not review.get('reviewed'):
        return dict(out, adoption_status='unreviewed', adoption_reason='No completed visual assessment')
    if review.get('disc_decision') != 'usable':
        return dict(out, adoption_status='withheld_disc_uncertain', adoption_reason='Disc not visually approved for quantitative geometry')
    if not confirmation:
        return dict(out, adoption_status='withheld_centre_unconfirmed', adoption_reason='Current fit/reference lacks a matching positive centre assessment')
    if not finite(c.get('disc_pa')) or not finite(c.get('inclination')):
        return dict(out, adoption_status='provisional_incomplete_disc', adoption_reason='Disc visible, but insufficient selected samples for complete disc geometry')
    out.update(adopted_disc_pa_deg=c['disc_pa'], adopted_inclination_deg=c['inclination'])
    if review.get('bar_decision') == 'convincing' and finite(c.get('bar_pa')):
        out['adopted_bar_pa_deg'] = c['bar_pa']
    cautions = [i for i in effective if 'informational' not in i]
    if c.get('face_on'):
        cautions.append('Face-on PA sensitivity requires checking before automatic transformation')
    if out['adopted_bar_pa_deg'] is None:
        cautions.append('No supported quantitative bar PA')
    if cautions:
        return dict(out, adoption_status='reviewed_provisional', adoption_reason='; '.join(cautions))
    return dict(out, adoption_status='reviewed_supported', adoption_reason='Visual approval and current numerical screens passed', automatic_deprojection_ready=True)
