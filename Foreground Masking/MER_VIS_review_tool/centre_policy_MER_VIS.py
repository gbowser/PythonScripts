"""Consistent native-pixel centre screening for MER VIS fits and review."""
from __future__ import annotations
import math
POLICY_VERSION = 'MER_VIS_centre_policy_v3_pilot_2026-10-28'
DEFAULT_POLICY = dict(cap_native_pixels=3.0, fraction_radius=0.05, floor_native_pixels=1.0)

def checked_policy(policy=None):
    p=dict(DEFAULT_POLICY, **(policy or {}))
    for key,low,high in [('cap_native_pixels',.5,20),('fraction_radius',.005,.5),('floor_native_pixels',0,5)]:
        value=p[key]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:
            raise ValueError('Invalid centre policy '+key)
        p[key]=float(value)
    if p['floor_native_pixels']>p['cap_native_pixels']:raise ValueError('Centre floor exceeds cap')
    return p

def centre_measurement(point,reference,pixel_scale_arcsec,policy=None):
    p=checked_policy(policy)
    try:
        x,y=float(point['x_original_pix']),float(point['y_original_pix'])
        rx,ry=map(float,reference);scale=float(pixel_scale_arcsec);radius=float(point['sma_arcsec'])
        if not all(math.isfinite(v) for v in [x,y,rx,ry,scale,radius]) or scale<=0 or radius<=0:raise ValueError()
    except (KeyError,TypeError,ValueError):
        return dict(centre_accepted=False,centre_rejection_reason='Centre/radius coordinates unavailable',centre_policy_version=POLICY_VERSION)
    offset_native=math.hypot(x-rx,y-ry)
    limit_native=min(p['cap_native_pixels'],max(p['floor_native_pixels'],p['fraction_radius']*radius/scale))
    accepted=offset_native<=limit_native+1e-9
    return dict(centre_offset_native_pix=offset_native,centre_offset_arcsec=offset_native*scale,
                centre_offset_fraction_radius=offset_native*scale/radius,centre_limit_native_pix=limit_native,
                centre_limit_arcsec=limit_native*scale,centre_accepted=accepted,
                centre_rejection_reason='' if accepted else f'Centre displacement {offset_native:.3f} native px ({offset_native*scale:.3f} arcsec) exceeds {limit_native:.3f} native px ({limit_native*scale:.3f} arcsec)',
                centre_reference_x_pix=rx,centre_reference_y_pix=ry,centre_policy_version=POLICY_VERSION)

def numerical_acceptance(p,relaxed=False):
    def finite(key):
        try:return math.isfinite(float(p[key]))
        except (KeyError,TypeError,ValueError):return False
    return bool(p.get('valid') and p.get('stop_code') in ((0,2) if relaxed else (0,))
                and finite('sampled_fraction') and p['sampled_fraction']>=(.5 if relaxed else .65)
                and finite('ellipticity_error') and p['ellipticity_error']<(.2 if relaxed else .1)
                and finite('pa_error_deg') and p['pa_error_deg']<(20 if relaxed else 10)
                and finite('intensity') and p['intensity']>0)
