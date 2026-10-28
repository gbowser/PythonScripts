"""Isolated, asynchronous manual-centre fits; original science files stay read-only."""
from pathlib import Path
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
import threading
import time
import uuid

HERE = Path(__file__).resolve().parent


class ReviewRefits:
    def refit_status(self, job_id):
        if not isinstance(job_id, str) or len(job_id) != 32 or any(c not in '0123456789abcdef' for c in job_id):
            raise ValueError('Invalid refit identifier')
        folder = self.output / 'refits' / job_id
        path = folder / 'status.json'
        if not path.exists():
            raise ValueError('Refit not found')
        result = json.loads(path.read_text(encoding='utf8'))
        if result['status'] == 'complete':
            result['galaxy'] = self.galaxy(result['object_id'], job_id)
        return result

    def start_refit(self, payload):
        oid = str(payload.get('object_id', ''))
        if oid not in self.byid:
            raise ValueError('Unknown galaxy')
        x, y = payload.get('x'), payload.get('y')
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in [x, y]):
            raise ValueError('Enter finite centre coordinates')
        galaxy = self.galaxy(oid)
        ny, nx = galaxy['shape']
        if not (0 <= x <= nx-1 and 0 <= y <= ny-1):
            raise ValueError('Centre must be inside the original FITS image')
        locked = payload.get('lock_centre', True)
        if not isinstance(locked, bool):
            raise ValueError('Invalid centre-lock setting')
        with self.lock:
            if getattr(self, '_refit_running', False):
                raise ValueError('A fit is already running. Wait for it to finish.')
            self._refit_running = True
        job_id = uuid.uuid4().hex
        folder = self.output / 'refits' / job_id
        try:
            folder.mkdir(parents=True)
            area = None
            candidates=[HERE.parent/'datalabs_MER_VIS'/'MER_VIS_datalabs_manifest.csv', HERE.parent.parent/'Euclid'/'datalabs_MER_VIS'/'MER_VIS_datalabs_manifest.csv']
            segpath=next((p for p in candidates if p.exists()),candidates[0])
            if segpath.exists():
                with segpath.open(encoding='utf-8-sig') as stream:
                    area = next((r.get('segmentation_area') for r in csv.DictReader(stream) if r['object_id'] == oid), None)
            if area is None:
                raise ValueError('The segmentation size catalogue is missing; restore datalabs_MER_VIS/MER_VIS_datalabs_manifest.csv')
            row = dict(self.byid[oid], manual_centre_x_pix=x, manual_centre_y_pix=y)
            request = dict(object_id=oid, row=row, segmentation_area=area, lock_centre=locked,
                           source_manifest_sha256=self.digest,
                           centre_policy=__import__('centre_policy_MER_VIS').checked_policy(payload.get('centre_policy')),
                           reference_provenance=payload.get('reference_provenance','manual_selection'),
                           engine_sha256=hashlib.sha256((HERE/'fit_manual_centre_MER_VIS.py').read_bytes()).hexdigest(),
                           worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                           requested_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
            (folder/'request.json').write_text(json.dumps(request, indent=2), encoding='utf8')
            self._write_job(folder, dict(job_id=job_id, object_id=oid, status='running', message='Fitting new ellipses from the selected centre…'))
        except Exception:
            self._refit_running = False
            raise
        def run():
            try:
                with (folder/'worker.log').open('w', encoding='utf8') as log:
                    result = subprocess.run([sys.executable, str(HERE/'refit_MER_VIS.py'), str(folder/'request.json')],
                                            stdout=log, stderr=subprocess.STDOUT, timeout=600,
                                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if result.returncode != 0:
                    raise RuntimeError('Fit process failed. Details are in '+str(folder/'worker.log'))
                self._write_job(folder, dict(job_id=job_id, object_id=oid, status='complete', message='Refit finished; inspect its status and quality flags.'))
                with self.lock:
                    index_path=self.output/'MER_VIS_latest_refits.json'
                    index=json.loads(index_path.read_text(encoding='utf8')) if index_path.exists() else {}
                    index[oid]=job_id
                    temp=index_path.with_suffix('.tmp');temp.write_text(json.dumps(index,indent=2),encoding='utf8');temp.replace(index_path)
            except Exception as exc:
                self._write_job(folder, dict(job_id=job_id, object_id=oid, status='error', message=str(exc)))
            finally:
                self._refit_running = False
        threading.Thread(target=run, daemon=True).start()
        return dict(job_id=job_id, object_id=oid, status='running')

    @staticmethod
    def _write_job(folder, status):
        temp=folder/'status.tmp'
        temp.write_text(json.dumps(status, indent=2), encoding='utf8')
        temp.replace(folder/'status.json')


def worker(request_path):
    import fit_manual_centre_MER_VIS as engine
    path=Path(request_path); request=json.loads(path.read_text(encoding='utf8')); folder=path.parent
    engine.MANUAL_LOCK=request['lock_centre']
    from centre_policy_MER_VIS import checked_policy
    engine.CENTRE_POLICY=checked_policy(request.get('centre_policy'))
    row=dict(request['row']); row['fits_filename']=Path(row['fits_path']).name
    # Do not carry stale geometry, flags or comparisons into a new measurement.
    for key in row:
        if key.startswith('codex_') or key.endswith('_difference_deg'):
            row[key]=''
    result=engine.measure((row, str(Path(row['fits_path']).parent), str(folder), request['segmentation_area']))
    result.update(manual_centre_x_pix=row['manual_centre_x_pix'], manual_centre_y_pix=row['manual_centre_y_pix'],
                  manual_centre_locked=request['lock_centre'], source_manifest_sha256=request['source_manifest_sha256'],
                  manual_refit_engine_sha256=request['engine_sha256'],
                  manual_refit_worker_sha256=request.get('worker_sha256',''),
                  manual_refit_requires_visual_review=True,centre_reference_provenance=request.get('reference_provenance','manual_selection'),centre_policy=engine.CENTRE_POLICY)
    # Failed intermediate centres and angles must never be presented as adopted geometry.
    if result['codex_fit_status']=='fit_failed':
        for key in ['codex_fit_centre_x_pix','codex_fit_centre_y_pix','codex_disc_pa_sky_deg','codex_bar_pa_sky_deg','codex_inclination_deg']:
            result[key]=''
        result['codex_disc_sampling_assessment']='fit_failed'
    else:
        def numeric(value):
            try:
                n=float(value)
                return n if math.isfinite(n) else None
            except (ValueError,TypeError):
                return None
        for key, left, right, axial in [
            ('disc_vs_detection_pa_difference_deg','codex_disc_pa_sky_deg','euclid_adjusted_detection_pa_sky_deg',True),
            ('inclination_vs_detection_proxy_difference_deg','codex_inclination_deg','euclid_detection_inclination_proxy_deg',False),
            ('inclination_vs_sersic_proxy_difference_deg','codex_inclination_deg','euclid_sersic_inclination_proxy_deg',False)]:
            a,b=numeric(result.get(left)),numeric(result.get(right))
            result[key]=('' if a is None or b is None else float(engine.axial_diff(a,b)) if axial else a-b)
        profile_path=folder/'profiles'/f"Euclid_{request['object_id']}_MER_VIS_ellipse_profile.csv"
        with profile_path.open(encoding='utf-8-sig') as stream:
            disc=[float(p['sma_arcsec']) for p in csv.DictReader(stream) if p.get('selected_disc','').lower()=='true']
        disc.sort();span=disc[-1]-disc[0] if len(disc)>1 else 0
        gap=max((b-a for a,b in zip(disc,disc[1:])),default=0)
        result.update(codex_disc_sampling_n=len(disc),codex_disc_sampling_span_arcsec=span,
                      codex_disc_sampling_max_gap_fraction=gap/span if span>0 else '',
                      codex_disc_sampling_assessment='nearly_face_on_information' if result['codex_disc_axis_ratio']>.9
                      else 'sparse' if len(disc)<6 or span<=0 or gap>.5*span
                      else 'PA_varies' if result['codex_disc_pa_scatter_deg']>10 else 'adequate_sampling',
                      codex_quality_rule_version='manual_centre_existing_screens_2026-10-21')
        from astropy.io import fits
        from astropy.wcs import WCS
        with fits.open(row['fits_path'],memmap=True) as hd:
            sky=WCS(hd[0].header).celestial.pixel_to_world(result['codex_fit_centre_x_pix'],result['codex_fit_centre_y_pix'])
            result.update(manual_fit_centre_ra_deg=float(sky.ra.deg),manual_fit_centre_dec_deg=float(sky.dec.deg))
    result.update(codex_review_action='manual_centre_refit_pending_review',
                  codex_review_reason='Human-selected centre; new geometry is provisional and needs visual review.')
    (folder/'result.json').write_text(json.dumps(result, indent=2, default=str), encoding='utf8')
    engine.write_csv(folder/'MER_VIS_manual_refit_manifest.csv', [result])


if __name__=='__main__':
    worker(sys.argv[1])
