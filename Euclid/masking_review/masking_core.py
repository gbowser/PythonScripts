"""Native-pixel Euclid masking, MTO detection and provisional fixed-centre fits.

No display dependency. MTO is run in isolated worker processes because its
ctypes classes and relative library paths are process-global.
"""
from __future__ import annotations

import csv
import ctypes
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from scipy import ndimage

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DEFAULT_CATALOGUE = HERE.parent / 'reports/MER_VIS_review_2026-10-29/MER_VIS_reviewed_adoption_manifest.csv'
PROCESSING_POLICY = 'fit_galaxy_crop_v1'
DEFAULTS = dict(move_factor=0.5, dilation=2, minarea=5,
                alpha=1e-6, min_distance=0., gaussian_fwhm=1.,
                bg_mean=None, bg_variance=None, gain=1., soft_bias=0.,
                detect_on='original', residual_sigma=3., residual_max_area=100)
BOUNDS = dict(move_factor=(0, 1), dilation=(0, 30),
              minarea=(1, 100000), alpha=(1e-10, 1e-2), min_distance=(0, 1e9),
              gaussian_fwhm=(0, 15), gain=(1e-9, 1e9), soft_bias=(-1e15, 1e15),
              bg_mean=(-1e15, 1e15), bg_variance=(1e-20, 1e30), residual_sigma=(1,30), residual_max_area=(1,100000))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_write(path, value):
    def clean(v):
        if isinstance(v, dict):
            return {str(k): clean(x) for k, x in v.items()}
        if isinstance(v, (tuple, list)):
            return [clean(x) for x in v]
        if isinstance(v, (np.integer, np.bool_)):
            return v.item()
        if isinstance(v, (float, np.floating)):
            return float(v) if math.isfinite(v) else None
        return v
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(clean(value), indent=2, allow_nan=False), encoding='utf8')
    temporary.replace(path)


def parameters(values):
    unknown = set(values) - set(DEFAULTS)
    if unknown:
        raise ValueError(f'Unknown parameters: {sorted(unknown)}')
    result = dict(DEFAULTS, **values)
    for key, value in result.items():
        if key=='detect_on':
            if value not in ('original','original+residual'):
                raise ValueError('Unknown detection image mode')
            continue
        if key in ('bg_mean', 'bg_variance') and value in (None, ''):
            result[key] = None
            continue
        if isinstance(value, bool):
            raise ValueError(f'{key} must be numeric')
        value = float(value)
        lo, hi = BOUNDS[key]
        if not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError(f'{key} must be between {lo} and {hi}')
        if key in ('dilation', 'minarea', 'residual_max_area'):
            if not value.is_integer():
                raise ValueError(f'{key} must be an integer')
            value = int(value)
        result[key] = value
    if result['alpha'] != 1e-6:
        raise ValueError('The installed MTO significance test supports alpha=1e-6 only')
    return result


def number(row, *keys, default=None):
    for key in keys:
        try:
            value = float(row.get(key, ''))
            if math.isfinite(value):
                return value
        except (TypeError, ValueError):
            pass
    return default


def catalogue(path, all_targets=False):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    selected = [r for r in rows if all_targets or
                r.get('adoption_status') == 'reviewed_supported' or
                r['object_id'] == '-599118107493216367']
    if not selected:
        raise ValueError('No pilot targets in this catalogue; use --all-targets for another catalogue')
    # Put the explicitly requested close-pair test first.
    return sorted(selected, key=lambda r: (r['object_id'] != '-599118107493216367', r['object_id']))


def source_path(row, fits_dir=None):
    if fits_dir:
        return Path(fits_dir) / Path(row['fits_filename']).name
    for key in ('review_fits_path', 'fits_path'):
        if row.get(key) and Path(row[key]).is_file():
            return Path(row[key])
    raise FileNotFoundError('Science FITS not found. Supply --fits-dir for this computer.')


def load_image(row, fits_dir=None):
    path = source_path(row, fits_dir).resolve()
    with fits.open(path, memmap=False) as hd:
        data = np.array(hd[0].data, dtype=float)
        header = hd[0].header.copy()
        if data.ndim != 2:
            raise ValueError('Expected a two-dimensional primary science image')
        if 'GALID' in header and str(header['GALID']) != row['object_id']:
            raise ValueError('GALID does not match the selected target')
        bad = ~np.isfinite(data)
        if 'FLG' in hd:
            # Same rejection bits as the existing Euclid cutout fitter.
            reject = sum(1 << bit for bit in list(range(20)) + [21, 22])
            bad |= (np.asarray(hd['FLG'].data, dtype=np.int64) & reject) != 0
    wcs = WCS(header).celestial
    scale = float(np.sqrt(abs(np.linalg.det(wcs.pixel_scale_matrix))) * 3600)
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('A valid celestial WCS is required')
    x = number(row, 'review_reference_x_pix', 'codex_fit_centre_x_pix', default=float(header['CENX']) - 1)
    y = number(row, 'review_reference_y_pix', 'codex_fit_centre_y_pix', default=float(header['CENY']) - 1)
    if not (0 <= x < data.shape[1] and 0 <= y < data.shape[0]):
        raise ValueError('Reviewed centre lies outside the science image')
    a = number(row, 'codex_disc_max_arcsec')
    # Use the exact human-selected outer interval when available.
    refit = row.get('review_refit_id', '')
    reviews = HERE.parent / 'reports/MER_VIS_review_2026-10-29/source_reviews_completed.json'
    disc_min = number(row, 'codex_disc_min_arcsec')
    bar_min = number(row, 'codex_bar_min_arcsec')
    bar_max = number(row, 'codex_bar_max_arcsec')
    # The export records angles but not interval edges; consult the matching saved review.
    if reviews.exists() and refit:
        saved = json.loads(reviews.read_text(encoding='utf8'))
        records = saved.values() if isinstance(saved, dict) else saved
        for record in records:
            if isinstance(record, dict) and str(record.get('object_id')) == row['object_id']:
                # Exact format is handled only when explicit radial bounds are present.
                settings = record.get('settings', {})
                if settings.get('refit_id') == refit:
                    if isinstance(settings.get('disc'), list):
                        disc_min, a = map(float, settings['disc'])
                    if isinstance(settings.get('bar'), list):
                        bar_min, bar_max = map(float, settings['bar'])
                break
    if a is None or a <= 0:
        raise ValueError('No outer-disc radius: review the disc interval before masking')
    q = number(row, 'codex_disc_axis_ratio', default=0.7)
    inc = number(row, 'adopted_inclination_deg', 'review_selected_inclination')
    if inc is not None:
        q = math.cos(math.radians(inc))  # current catalogue q0=0
    q = float(np.clip(q, 0.05, 1))
    pa = number(row, 'adopted_disc_pa_deg', 'review_selected_disc_pa', 'codex_disc_pa_sky_deg')
    if pa is None:
        raise ValueError('No disc position angle')
    world = wcs.pixel_to_world(x, y)
    from astropy import units as u
    endpoint = world.directional_offset_by(pa * u.deg, 1 * u.arcsec)
    ex, ey = wcs.world_to_pixel(endpoint)
    theta = math.atan2(ey - y, ex - x)
    geometry = dict(x=x, y=y, a=a / scale, q=q, theta=theta, scale=scale,
                    disc_min=disc_min, disc_max=a, bar_min=bar_min, bar_max=bar_max,
                    disc_pa_sky=pa, centre_provenance=row.get('review_centre_provenance', 'catalogue_fit'))
    try:
        profile, profile_path = measured_profile(row, path)
        geometry['outer_disc'] = outer_disc_ellipse(profile, geometry)
    except ValueError:
        pass  # An unavailable outer contour must not block rectangular processing.
    return data, bad, header, geometry, path


def measured_profile(row, science_path=None):
    name = f'Euclid_{row["object_id"]}_MER_VIS_ellipse_profile.csv'
    refit = row.get('review_refit_id', '')
    if refit:
        if len(refit) != 32 or any(c not in '0123456789abcdef' for c in refit):
            raise ValueError('Invalid reviewed refit identifier')
        path = HERE.parent / 'review_MER_VIS/saved_reviews_centre_v3/refits' / refit / 'profiles' / name
    else:
        path = Path(science_path or source_path(row)).parent.parent / 'Euclid_MER_VIS_geometry/profiles' / name
    if not path.is_file():
        raise ValueError('Measured disc profile unavailable; an outer-disc boundary cannot be established')
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream)), path


def outer_disc_ellipse(profile, geometry):
    candidates = []
    for point in profile:
        if str(point.get('used_for_geometry', '')).lower() != 'true':
            continue
        radius = number(point, 'sma_arcsec')
        if radius is None:
            continue
        reviewed_disc = (geometry.get('disc_min') is not None and
                         geometry['disc_min'] <= radius <= geometry['disc_max'])
        automatic_disc = str(point.get('selected_disc', '')).lower() == 'true'
        # An inner representative interval must not shrink the full-disc envelope.
        if not (reviewed_disc or automatic_disc) or radius <= (geometry.get('bar_max') or 0):
            continue
        values = [number(point, key) for key in ('x_original_pix', 'y_original_pix', 'ellipticity', 'pa_pixel_deg')]
        if any(v is None for v in values) or not 0 <= values[2] < 1:
            continue
        candidates.append(dict(x=values[0], y=values[1], a=radius/geometry['scale'], q=1-values[2],
                               theta=math.radians(values[3]), sma_arcsec=radius,
                               source='automatic_outer_disc' if automatic_disc else 'reviewed_disc'))
    if not candidates:
        raise ValueError('No accepted outer disc ellipse beyond the bar is available. Review the outer disc before masking; an inner/bar-sized boundary has not been substituted.')
    return max(candidates, key=lambda e: e['a'])


def ellipse_region(shape, geometry, margin=1.):
    yy, xx = np.indices(shape)
    dx, dy = xx - geometry['x'], yy - geometry['y']
    c, s = math.cos(geometry['theta']), math.sin(geometry['theta'])
    u, v = c * dx + s * dy, -s * dx + c * dy
    a = geometry['a'] * margin
    return (u / a) ** 2 + (v / (a * geometry['q'])) ** 2 <= 1


def fit_galaxy_bounds(shape, geometry):
    """The fixed rectangular Fit galaxy preset, independent of display pan/zoom."""
    g = geometry.get('outer_disc', geometry)
    half = max(50., g['a'] * 2.6)  # Preserve the existing Fit galaxy framing.
    ny, nx = shape
    return dict(x0=max(0, math.floor(g['x']-half)), x1=min(nx, math.ceil(g['x']+half)),
                y0=max(0, math.floor(g['y']-half)), y1=min(ny, math.ceil(g['y']+half)))


def processing_region(shape, bounds):
    region = np.zeros(shape, dtype=bool)
    region[bounds['y0']:bounds['y1'], bounds['x0']:bounds['x1']] = True
    return region


def detect_fit_galaxy(data, bad, geometry, params, root):
    bounds = fit_galaxy_bounds(data.shape, geometry)
    x0, x1, y0, y1 = [bounds[k] for k in ('x0','x1','y0','y1')]
    local = dict(geometry, x=geometry['x']-x0, y=geometry['y']-y0)
    cropped, background = run_mto(data[y0:y1,x0:x1], bad[y0:y1,x0:x1], local, params, root)
    background['detection_mode']=params['detect_on']
    if params['detect_on']=='original+residual':
        raw=data[y0:y1,x0:x1]
        valid=~bad[y0:y1,x0:x1]
        sigma=params['residual_sigma']
        smooth=ndimage.gaussian_filter(np.where(valid,raw,0),sigma)
        weight=ndimage.gaussian_filter(valid.astype(float),sigma)
        residual=raw-smooth/np.maximum(weight,1e-12)
        residual_params=dict(params,bg_mean=None,bg_variance=None)
        extra,residual_background=run_mto(residual,~valid,local,residual_params,root)
        centre=int(cropped[min(cropped.shape[0]-1,round(local['y'])),min(cropped.shape[1]-1,round(local['x']))])
        ids,counts=np.unique(cropped,return_counts=True)
        original_choices=ids[(ids>0)&(ids!=centre)&(counts>=params['minarea'])]
        original_mask=np.isin(cropped,original_choices)
        # Add all residual labels, including those at the nucleus and in the bar.
        # Retain ordinary source wings; residual sublabels inherit the old proposal
        # by majority overlap, and remain independently selectable by the reviewer.
        combined=cropped.copy()
        original_max=int(cropped.max())
        use=extra>0
        combined[use]=extra[use]+original_max
        ids,counts=np.unique(combined,return_counts=True)
        selected_counts=np.bincount(combined[original_mask].ravel(),minlength=int(combined.max())+1)
        background['proposed_mask_labels']=[int(label) for label,count in zip(ids,counts)
                    if label>0 and count>=params['minarea'] and
                    (selected_counts[label]>.5*count or
                     (label>original_max and count<=params['residual_max_area']))]
        background['residual_first_label']=original_max+1
        background['residual_background']=residual_background
        background['residual_sigma']=sigma
        cropped=combined
    segmentation = np.zeros(data.shape, dtype=np.int32)
    segmentation[y0:y1,x0:x1] = cropped
    return segmentation, background, bounds


def run_mto(data, bad, geometry, params, root):
    """Use raw MTO segmentation; do not apply the old star-only size filters."""
    root = Path(root).resolve()
    if not (root / 'mtolib').is_dir():
        raise ValueError('MTO checkout not found; set --mtobjects-root')
    background = ~bad
    if background.sum() < 100:
        raise ValueError('Fewer than 100 valid pixels in the Fit galaxy processing area')
    mean, _, sigma = sigma_clipped_stats(data[background], sigma=3, maxiters=8)
    variance = float(sigma) ** 2 if params['bg_variance'] is None else params['bg_variance']
    mean = float(mean) if params['bg_mean'] is None else params['bg_mean']
    if not math.isfinite(variance) or variance <= 0 or not math.isfinite(mean):
        raise ValueError('Background estimation failed; enter a finite mean and positive variance')
    safe = np.ascontiguousarray(np.where(bad, mean, data), dtype=np.float64)
    dll_handles = []
    if os.name == 'nt':
        for candidate in [os.environ.get('MTOBJECTS_DLL_DIR'), 'C:/msys64/ucrt64/bin', 'C:/msys64/mingw64/bin']:
            if candidate and Path(candidate).is_dir():
                dll_handles.append(os.add_dll_directory(candidate))
    previous = Path.cwd()
    sys.path.insert(0, str(root))
    try:
        os.chdir(root)
        from mtolib import _ctype_classes, maxtree
        from mtolib.preprocessing import preprocess_image
        from mtolib.tree_filtering import init_double_filtering, filter_tree
        p = SimpleNamespace(filename=None, out='unused.png', par_out='unused.csv',
                            soft_bias=params['soft_bias'], gain=params['gain'],
                            bg_mean=mean, bg_variance=variance, alpha=params['alpha'],
                            move_factor=params['move_factor'], min_distance=params['min_distance'],
                            verbosity=0, d_type=ctypes.c_double)
        init_double_filtering(p)
        if not getattr(_ctype_classes.MtImageLocation, '_fields_', None):
            _ctype_classes.init_classes(ctypes.c_double)
        processed = preprocess_image(safe, p, gaussian_blur=params['gaussian_fwhm'] > 0,
                                     n=params['gaussian_fwhm'])
        tree = maxtree.OriginalMaxTree(processed, 0, p)
        try:
            tree.flood()
            raw, _ = filter_tree(tree, processed, p)
        finally:
            tree.free_objects()
        # Same sorted positive relabelling, without importing skimage just for
        # the unused colour-label helper in MTO's postprocessing module.
        raw = np.asarray(raw)
        ids = np.unique(raw[raw >= 0])
        segmentation = np.zeros(raw.shape, dtype=np.int32)
        valid = raw >= 0
        segmentation[valid] = np.searchsorted(ids, raw[valid]) + 1
    finally:
        os.chdir(previous)
        for handle in dll_handles:
            handle.close()
    segmentation[bad | (segmentation < 0)] = 0
    return segmentation, dict(mean=mean, variance=variance, sigma=math.sqrt(variance),
                              background_pixels=int(background.sum()), gain=params['gain'])


def object_summary(segmentation, geometry, params):
    labels, counts = np.unique(segmentation, return_counts=True)
    cy = min(segmentation.shape[0] - 1, int(round(geometry['y'])))
    cx = min(segmentation.shape[1] - 1, int(round(geometry['x'])))
    centre_label = int(segmentation[cy, cx])
    region = processing_region(segmentation.shape, fit_galaxy_bounds(segmentation.shape, geometry))
    overlaps = set(map(int, np.unique(segmentation[region])))
    rows = []
    for label, count in zip(labels, counts):
        if label == 0:
            continue
        rows.append(dict(label=int(label), pixels=int(count), target=bool(label == centre_label),
                         intersects_aoi=int(label) in overlaps,
                         mask=bool(label != centre_label and count >= params['minarea'])))
    return rows, centre_label


def build_mask(segmentation, bad, selected, target, dilation):
    labels = set(map(int, selected))
    existing = set(map(int, np.unique(segmentation))) - {0}
    if not labels <= existing:
        raise ValueError('Invalid selected labels')
    mask = np.isin(segmentation, list(labels))
    if dilation:
        yy, xx = np.ogrid[-dilation:dilation + 1, -dilation:dilation + 1]
        mask = ndimage.binary_dilation(mask, structure=xx * xx + yy * yy <= dilation * dilation)
    # A contaminant can overlap the target: retain the overlapping mask wings.
    return mask | bad


def preview(data, mode='autostf', gamma=1., shadows=-2.8, target=.25, stats=None):
    """PixInsight-style monochrome AutoSTF + gamma; never mutate science values."""
    finite = data[np.isfinite(data)]
    if not finite.size:
        raise ValueError('No finite science pixels')
    if stats is None:
        median = float(np.median(finite))
        stats = dict(minimum=float(finite.min()), maximum=float(finite.max()), median=median,
                     robust_sigma=float(1.4826*np.median(np.abs(finite-median))))
    lo, hi = stats['minimum'], stats['maximum']
    span = hi-lo
    def mtf(m, x):
        m = np.clip(m, np.finfo(float).eps, 1-np.finfo(float).eps)
        x = np.clip(x, 0, 1)
        return np.clip(((m-1)*x)/((2*m-1)*x-m), 0, 1)
    if span <= np.finfo(float).eps:
        value = np.zeros_like(data)
    elif mode == 'autostf':
        centre = (stats['median']-lo)/span
        black = float(np.clip(centre+np.clip(shadows, -20, 0)*stats['robust_sigma']/span, 0, 1))
        after_black = np.clip((centre-black)/max(1-black, np.finfo(float).eps), 0, 1)
        midtones = mtf(np.clip(target, .01, .99), after_black)
        low = lo+black*span
        value = mtf(midtones, (np.nan_to_num(data, nan=low)-low)/max(hi-low, np.finfo(float).eps))
    else:
        value = np.clip((np.nan_to_num(data, nan=lo)-lo)/span, 0, 1)
        if mode == 'asinh':
            value = np.arcsinh(15*value)/np.arcsinh(15)
    value = np.where(np.isfinite(data), value, 0)**(1/float(np.clip(gamma, .2, 3)))
    return np.asarray(np.rint(255*value), dtype=np.uint8)


def display_pixels(data, bad, max_side=1536):
    """Float preview for display transforms; fitting/detection stay native."""
    step = max(1, math.ceil(max(data.shape) / max_side))
    pixels = np.array(data[::step, ::step], dtype='<f4', copy=True)
    pixels[bad[::step, ::step]] = np.nan
    values = pixels[np.isfinite(pixels)]
    if not values.size:
        raise ValueError('No valid pixels for the display')
    median = float(np.median(values))
    stats = dict(minimum=float(values.min()), maximum=float(values.max()), median=median,
                 robust_sigma=float(1.4826 * np.median(np.abs(values - median))))
    return pixels, dict(width=pixels.shape[1], height=pixels.shape[0], factor=step, stats=stats)


def proposed_ellipses(row, geometry):
    """Read measured shapes from the exact reviewed refit, never invent a bar q."""
    try:
        profile, _ = measured_profile(row)
    except ValueError:
        return []
    ellipses = []
    for r in profile:
            if r.get('used_for_geometry', '').lower() != 'true':
                continue
            values = {k: number(r, k) for k in ('sma_arcsec', 'ellipticity', 'pa_pixel_deg', 'x_original_pix', 'y_original_pix')}
            if any(v is None for v in values.values()) or not 0 <= values['ellipticity'] < 1:
                continue
            ellipses.append(dict(x=values['x_original_pix'], y=values['y_original_pix'],
                                 a=values['sma_arcsec'] / geometry['scale'],
                                 q=1-values['ellipticity'], theta=math.radians(values['pa_pixel_deg']),
                                 sma_arcsec=values['sma_arcsec']))
    return ellipses


def fit_geometry(data, bad, header, geometry, bounds, output, background_mean=None):
    """Fit the approved mask at native resolution; intervals are explicit inputs."""
    from photutils.isophote import Ellipse, EllipseGeometry
    sys.path.insert(0, str(HERE.parent / 'review_MER_VIS'))
    from centre_policy_MER_VIS import numerical_acceptance
    from fit_manual_centre_MER_VIS import axial_mean, scatter, inclination
    wcs = WCS(header).celestial
    x, y = geometry['x'], geometry['y']
    dm, dx, bm, bx = [float(bounds[k]) for k in ('disc_min', 'disc_max', 'bar_min', 'bar_max')]
    if not (0 < bm < bx and 0 < dm < dx):
        raise ValueError('Each interval must have 0 < minimum < maximum (arcsec)')
    radius = min(max(dx, bx) / geometry['scale'] * 1.2, x, y, data.shape[1] - 1 - x, data.shape[0] - 1 - y)
    if radius * geometry['scale'] < max(dx, bx):
        raise ValueError('A selected interval extends beyond the available image')
    if background_mean is None:
        _, background, _ = sigma_clipped_stats(data[~bad & ~ellipse_region(data.shape, geometry, 1.3)])
    else:
        background = float(background_mean)
    image = np.ma.array(data - background, mask=bad)
    seed = max(2., min(geometry['a'] * .4, radius * .5))
    ellipse = Ellipse(image, geometry=EllipseGeometry(x, y, seed, np.clip(1 - geometry['q'], .05, .8), geometry['theta']))
    clip_key = 'n_clip' if 'n_clip' in inspect.signature(ellipse.fit_image).parameters else 'nclip'
    isos = ellipse.fit_image(minsma=1, maxsma=radius, step=.08, maxit=60,
                            fix_center=True, sclip=2.5, fflag=.5, maxgerr=1., **{clip_key: 3})
    rows = []
    for iso in isos:
        center = wcs.pixel_to_world(iso.x0, iso.y0)
        end = wcs.pixel_to_world(iso.x0 + math.cos(iso.pa), iso.y0 + math.sin(iso.pa))
        east, north = center.spherical_offsets_to(end)
        n = iso.n_data if hasattr(iso, 'n_data') else iso.ndata
        nf = iso.n_flag if hasattr(iso, 'n_flag') else iso.nflag
        row = dict(sma_arcsec=float(iso.sma * geometry['scale']), ellipticity=float(iso.eps),
                   pa_sky_deg=float(np.degrees(np.arctan2(east.arcsec, north.arcsec)) % 180),
                   pa_pixel_deg=float(np.degrees(iso.pa) % 180), intensity=float(iso.intens),
                   ellipticity_error=float(iso.ellip_err) if iso.ellip_err is not None else float('nan'),
                   pa_error_deg=float(np.degrees(iso.pa_err)) if iso.pa_err is not None else float('nan'),
                   valid=bool(iso.valid), stop_code=int(iso.stop_code), sampled_fraction=float(n / max(1, n + nf)))
        row['accepted'] = numerical_acceptance(row)
        rows.append(row)
    def selection(low, high):
        return [r for r in rows if r['accepted'] and low <= r['sma_arcsec'] <= high]
    disc, bar = selection(dm, dx), selection(bm, bx)
    result = dict(status='provisional_requires_review', fixed_centre=True, q0=0,
                  centre_x=x, centre_y=y, bounds=bounds, n_disc=len(disc), n_bar=len(bar),
                  disc_pa_deg=None, inclination_deg=None, disc_ellipticity=None, bar_pa_deg=None,
                  cautions=['Fixed centre is imposed, not independently recovered.',
                            'Adjacent ellipses are correlated; this is not an uncertainty estimate.'])
    if bx > dm:
        result['cautions'].append('Bar interval extends into or beyond the disc interval; review the physical assignments before deprojection.')
    if len(disc) >= 3:
        q = float(np.median([1 - r['ellipticity'] for r in disc]))
        result.update(disc_pa_deg=axial_mean([r['pa_sky_deg'] for r in disc]),
                      inclination_deg=inclination(q), disc_ellipticity=1 - q,
                      disc_pa_scatter_deg=scatter([r['pa_sky_deg'] for r in disc]))
        result['disc_eps_span'] = float(np.ptp([r['ellipticity'] for r in disc]))
        radii = np.sort([r['sma_arcsec'] for r in disc])
        result['disc_max_gap_fraction'] = float(np.max(np.diff(radii)) / np.ptp(radii))
        if result['disc_pa_scatter_deg'] > 10 and q <= .9:
            result['cautions'].append('Disc PA scatter exceeds 10 degrees; inspect radial variation.')
        if result['disc_eps_span'] > .15:
            result['cautions'].append('Disc ellipticity span exceeds 0.15; inspect radial variation.')
        if len(disc) < 6:
            result['cautions'].append('Fewer than six accepted disc ellipses: sparse sampling.')
        if q > .9:
            result['cautions'].append('Nearly face-on: disc PA is weakly constrained.')
    else:
        result['cautions'].append('Fewer than three accepted disc ellipses: no complete disc geometry.')
    if len(bar) >= 3:
        result['bar_pa_deg'] = axial_mean([r['pa_sky_deg'] for r in bar])
    else:
        result['cautions'].append('Fewer than three accepted bar ellipses: no numerical bar PA.')
    result['proposed_ellipses'] = [dict(x=x, y=y, a=r['sma_arcsec']/geometry['scale'],
                                      q=1-r['ellipticity'], theta=math.radians(r['pa_pixel_deg']),
                                      sma_arcsec=r['sma_arcsec']) for r in rows if r['accepted']]
    output = Path(output)
    with (output / 'ellipse_profile.csv').open('w', newline='', encoding='utf8') as stream:
        if rows:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Ellipse as PatchEllipse
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    axes[0].imshow(preview(np.where(bad, np.nan, data)), origin='lower', cmap='gray')
    for iso, row in zip(isos, rows):
        if row['accepted']:
            axes[0].add_patch(PatchEllipse((x, y), 2 * iso.sma, 2 * iso.sma * (1 - iso.eps),
                                          angle=np.degrees(iso.pa), fill=False, linewidth=.6, color='cyan'))
    axes[0].plot(x, y, '+', color='yellow')
    half = radius * 1.15
    axes[0].set(xlim=(x-half, x+half), ylim=(y-half, y+half),
                xlabel='Native X (pixel)', ylabel='Native Y (pixel)')
    for ax, key, label in [(axes[1], 'ellipticity', 'Ellipticity'), (axes[2], 'pa_sky_deg', 'Sky PA (deg E of N, mod 180)')]:
        ax.plot([r['sma_arcsec'] for r in rows], [r[key] for r in rows], '.', color='gray', label='All fits')
        ax.plot([r['sma_arcsec'] for r in rows if r['accepted']], [r[key] for r in rows if r['accepted']], '.', color='black', label='Accepted')
        ax.axvspan(dm, dx, alpha=.15, color='green', label='Disc')
        ax.axvspan(bm, bx, alpha=.15, color='blue', label='Bar')
        ax.set(xlabel='Semimajor axis (arcsec)', ylabel=label)
    axes[1].legend(fontsize=8)
    axes[0].set_title('Approved mask; fixed-centre isophotes')
    fig.suptitle('Provisional refit - visual review required')
    fig.tight_layout()
    fig.savefig(output / 'geometry.png', dpi=120)
    plt.close(fig)
    return result
