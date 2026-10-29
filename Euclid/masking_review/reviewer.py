"""Local interactive Euclid MTO masking reviewer. Run --help for options."""
from __future__ import annotations

import argparse
import base64
import csv
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import traceback
from urllib.parse import urlparse, parse_qs
import uuid
import webbrowser

LOCAL_DEPENDENCIES = Path(__file__).resolve().parent / 'dependencies'
if LOCAL_DEPENDENCIES.is_dir():
    sys.path.insert(0, str(LOCAL_DEPENDENCIES))

import numpy as np
from astropy.io import fits
from PIL import Image

import masking_core as core

HERE = Path(__file__).resolve().parent
APP_ID = 'euclid_mto_masking_v1'


def utc():
    return datetime.now(timezone.utc).isoformat()


def png_bytes(array):
    buffer = io.BytesIO()
    Image.fromarray(np.flipud(array)).save(buffer, format='PNG')
    return buffer.getvalue()


def worker(request_path):
    request_path = Path(request_path).resolve()
    request = json.loads(request_path.read_text(encoding='utf8'))
    folder = request_path.parent
    data, bad, header, geometry, path = core.load_image(request['row'], request.get('fits_dir'))
    if core.digest(path) != request['source_sha256']:
        raise ValueError('Science FITS changed since this request was created')
    if request['action'] == 'detect':
        params = core.parameters(request['params'])
        segmentation, background, processing_bounds = core.detect_fit_galaxy(data, bad, geometry, params, request['mtobjects_root'])
        objects, target = core.object_summary(segmentation, geometry, params)
        if 'proposed_mask_labels' in background:
            choices=set(background['proposed_mask_labels'])
            for obj in objects:
                obj['mask']=obj['label'] in choices
                obj['origin']='residual' if obj['label']>=background['residual_first_label'] else 'original'
        np.savez_compressed(folder / 'detection.npz', segmentation=segmentation, bad=bad)
        (folder / 'image.png').write_bytes(png_bytes(core.preview(np.where(bad, np.nan, data))))
        (folder / 'labels.bin').write_bytes(segmentation.astype('<u4').tobytes())
        result = dict(object_id=request['row']['object_id'], run_id=folder.name,
                      processing_policy=core.PROCESSING_POLICY, processing_bounds=processing_bounds,
                      params=params, background=background, geometry=geometry,
                      shape=list(data.shape), target=target, objects=objects,
                      source_sha256=request['source_sha256'])
        core.json_write(folder / 'result.json', result)
    elif request['action'] == 'refit':
        review = json.loads(Path(request['review']).read_text(encoding='utf8'))
        mask_path = Path(request['mask'])
        if core.digest(mask_path) != request['mask_sha256']:
            raise ValueError('Approved mask changed since the fit was requested')
        mask = fits.getdata(mask_path, memmap=False).astype(bool)
        if mask.shape != data.shape:
            raise ValueError('Mask shape does not match science FITS')
        result = core.fit_geometry(data, mask | bad, header, geometry, request['bounds'], folder,
                                   background_mean=review['background']['mean'])
        result.update(object_id=request['row']['object_id'], mask_review_id=review['review_id'],
                      source_sha256=request['source_sha256'], mask_sha256=request['mask_sha256'],
                      original_geometry={k: request['row'].get(k) for k in
                                         ('adopted_disc_pa_deg', 'adopted_inclination_deg',
                                          'adopted_bar_pa_deg', 'review_selected_disc_pa',
                                          'review_selected_inclination', 'review_selected_bar_pa')})
        core.json_write(folder / 'result.json', result)
    else:
        raise ValueError('Unknown worker action')


class Application:
    def __init__(self, args):
        self.args = args
        self.output = args.output.resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.rows = core.catalogue(args.catalogue, args.all_targets)
        self.byid = {r['object_id']: r for r in self.rows}
        self.catalogue_hash = core.digest(args.catalogue)
        self.lock = threading.Lock()
        self.job = None

    def folder(self, kind, identifier):
        if kind not in ('runs', 'reviews', 'refits') or not re.fullmatch(r'[0-9a-f]{32}', identifier):
            raise ValueError('Invalid artifact identifier')
        folder = self.output / kind / identifier
        if not folder.is_dir():
            raise ValueError('Artifact not found')
        return folder

    def config(self):
        return dict(app=APP_ID, defaults=core.DEFAULTS, output=str(self.output),
                    targets=[dict(object_id=r['object_id'], status=r.get('adoption_status', ''),
                                  name=r.get('catalogue_name', ''),
                                  challenge=r['object_id'].endswith('16367')) for r in self.rows])

    def galaxy(self, oid):
        row = self.byid[oid]
        data, bad, header, geometry, path = core.load_image(row, self.args.fits_dir)
        # Lightweight preview permits initial inspection before MTO runs.
        latest_path = self.output / f'latest_{oid}.json'
        latest = json.loads(latest_path.read_text(encoding='utf8')) if latest_path.exists() else None
        return dict(object_id=oid, shape=list(data.shape), geometry=geometry, latest=latest,
                    processing_bounds=core.fit_galaxy_bounds(data.shape, geometry),
                    proposed_ellipses=core.proposed_ellipses(row, geometry),
                    original={k: row.get(k) for k in ('adopted_disc_pa_deg', 'adopted_bar_pa_deg',
                              'adopted_inclination_deg', 'adoption_status')})

    def display_image(self, oid):
        data, bad, *_ = core.load_image(self.byid[oid], self.args.fits_dir)
        pixels, meta = core.display_pixels(data, bad)
        return pixels.tobytes(), meta

    def start_job(self, payload):
        action = payload.get('action', 'detect')
        oid = str(payload.get('object_id', ''))
        if oid not in self.byid:
            raise ValueError('Unknown target')
        if action not in ('detect', 'sweep', 'refit'):
            raise ValueError('Unknown action')
        params = core.parameters(payload.get('params', {}))
        path = core.source_path(self.byid[oid], self.args.fits_dir)
        request = dict(action='detect', row=self.byid[oid], params=params, fits_dir=str(self.args.fits_dir) if self.args.fits_dir else None,
                       mtobjects_root=str(self.args.mtobjects_root.resolve()), source_sha256=core.digest(path),
                       catalogue_sha256=self.catalogue_hash, requested_utc=utc(),
                       core_sha256=core.digest(HERE / 'masking_core.py'), worker_sha256=core.digest(__file__))
        if action == 'refit':
            review_folder = self.folder('reviews', payload.get('review_id', ''))
            review = json.loads((review_folder / 'review.json').read_text(encoding='utf8'))
            if review['object_id'] != oid or review['source_sha256'] != request['source_sha256']:
                raise ValueError('Approved review does not match this target or current science file')
            if review.get('processing_policy') != core.PROCESSING_POLICY:
                raise ValueError('Run MTO and save a new Fit galaxy crop review before refitting.')
            bounds = payload.get('bounds', {})
            if set(bounds) != {'disc_min', 'disc_max', 'bar_min', 'bar_max'}:
                raise ValueError('Enter both disc and bar radial intervals')
            bounds = {k: float(v) for k, v in bounds.items()}
            if not all(np.isfinite(v) for v in bounds.values()):
                raise ValueError('Intervals must be finite')
            if not (0 < bounds['bar_min'] < bounds['bar_max'] and 0 < bounds['disc_min'] < bounds['disc_max']):
                raise ValueError('Each interval must have 0 < minimum < maximum')
            request.update(action='refit', review=str(review_folder / 'review.json'),
                           mask=str(review_folder / 'mask.fits'), bounds=bounds,
                           mask_sha256=core.digest(review_folder / 'mask.fits'))
        with self.lock:
            if self.job and self.job['status'] == 'running':
                raise ValueError('A calculation is already running')
            job = dict(job_id=uuid.uuid4().hex, action=action, object_id=oid, status='running', progress='', results=[])
            self.job = job
        threading.Thread(target=self._calculate, args=(job, request), daemon=True).start()
        return dict(job)

    def _calculate(self, job, request):
        try:
            moves = [.1, .3, .5, .7, .9] if job['action'] == 'sweep' else [request['params']['move_factor']]
            for move in moves:
                kind = 'refits' if job['action'] == 'refit' else 'runs'
                identifier = uuid.uuid4().hex
                folder = self.output / kind / identifier
                folder.mkdir(parents=True)
                req = dict(request, params=dict(request['params'], move_factor=move))
                core.json_write(folder / 'request.json', req)
                with self.lock:
                    job['progress'] = f'{job["action"]}: move_factor {move:g}'
                with (folder / 'worker.log').open('w', encoding='utf8') as log:
                    process = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker',
                                              str(folder / 'request.json')], stdout=log, stderr=subprocess.STDOUT,
                                             timeout=600, cwd=HERE, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if process.returncode:
                    detail = (folder / 'worker.log').read_text(encoding='utf8')[-3000:]
                    raise RuntimeError(f'Calculation failed. Log: {folder / "worker.log"}\n{detail}')
                result = json.loads((folder / 'result.json').read_text(encoding='utf8'))
                result['artifact_id'] = identifier
                with self.lock:
                    job['results'].append(result)
            with self.lock:
                job['status'] = 'complete'
        except Exception as exc:
            with self.lock:
                job.update(status='failed', error=str(exc))

    def mask(self, payload):
        folder = self.folder('runs', payload.get('run_id', ''))
        result = json.loads((folder / 'result.json').read_text(encoding='utf8'))
        if result.get('processing_policy') != core.PROCESSING_POLICY:
            raise ValueError('Run MTO again to process the Fit galaxy crop; earlier files are preserved.')
        if result['object_id'] not in self.byid:
            raise ValueError('Run target is outside this catalogue selection')
        selected = payload.get('selected')
        if not isinstance(selected, list) or any(isinstance(x, bool) or not isinstance(x, int) for x in selected):
            raise ValueError('Selected objects must be integer labels')
        with np.load(folder / 'detection.npz') as arrays:
            mask = core.build_mask(arrays['segmentation'], arrays['bad'], selected,
                                   result['target'], result['params']['dilation'])
        region = core.processing_region(mask.shape, result['processing_bounds'])
        mask |= ~region  # Unprocessed pixels cannot enter downstream measurements.
        rgba = np.zeros((*mask.shape, 4), dtype=np.uint8)
        rgba[mask] = [255, 65, 90, 155]
        rgba[~region] = [80, 90, 105, 150]
        return folder, result, mask, dict(png=base64.b64encode(png_bytes(rgba)).decode(),
                                         masked_fraction=float(mask.mean()),
                                         aoi_masked_fraction=float(mask[region].mean()))

    def save(self, payload):
        folder, result, mask, summary = self.mask(payload)
        if payload.get('confirm') is not True:
            raise ValueError('Confirm that the mask has been visually reviewed')
        path = core.source_path(self.byid[result['object_id']], self.args.fits_dir)
        if core.digest(path) != result['source_sha256']:
            raise ValueError('Science FITS changed since detection; run MTO again')
        identifier = uuid.uuid4().hex
        output = self.output / 'reviews' / identifier
        output.mkdir(parents=True)
        header = fits.getheader(path)
        header['MASKTYPE'] = ('BAD=1', '1 means exclude pixel; native science grid')
        header['MTMOVE'] = result['params']['move_factor']
        header['REVIEWID'] = identifier
        fits.PrimaryHDU(mask.astype(np.uint8), header=header).writeto(output / 'mask.fits')
        display = payload.get('display', {})
        mode = display.get('stretch', 'autostf')
        if mode not in ('autostf', 'asinh', 'linear'):
            mode = 'autostf'
        def display_number(key, default, low, high):
            try:
                value = float(display.get(key, default))
                return float(np.clip(value, low, high)) if np.isfinite(value) else default
            except (TypeError, ValueError):
                return default
        display = dict(stretch=mode, gamma=display_number('gamma', 1, .2, 3),
                       shadows=display_number('shadows', -2.8, -20, 0), target=display_number('target', .25, .01, .99))
        review = dict(review_id=identifier, object_id=result['object_id'], run_id=folder.name,
                      processing_policy=core.PROCESSING_POLICY, processing_bounds=result['processing_bounds'],
                      selected=sorted(set(payload['selected'])), params=result['params'],
                      target=result['target'], geometry=result['geometry'], background=result['background'],
                      source_sha256=result['source_sha256'], source_path=str(path.resolve()),
                      mask_sha256=core.digest(output / 'mask.fits'), catalogue_sha256=self.catalogue_hash,
                      notes=str(payload.get('notes', ''))[:10000], reviewed_utc=utc(),
                      confirmed=True, display=display, masked_fraction=summary['masked_fraction'], aoi_masked_fraction=summary['aoi_masked_fraction'])
        core.json_write(output / 'review.json', review)
        # A portable review image accompanies the mask and provenance.
        data = fits.getdata(path, memmap=False).astype(float)
        with np.load(folder / 'detection.npz') as arrays:
            data[arrays['bad']] = np.nan
        _, display_meta = core.display_pixels(data, ~np.isfinite(data))
        base = Image.open(io.BytesIO(png_bytes(core.preview(data, mode=display['stretch'], gamma=display['gamma'],
                     shadows=display['shadows'], target=display['target'], stats=display_meta['stats'])))).convert('RGBA')
        overlay = Image.open(io.BytesIO(base64.b64decode(summary['png']))).convert('RGBA')
        base = Image.alpha_composite(base, overlay)
        base.convert('RGB').save(output / 'mask_review.png')
        core.json_write(self.output / f'latest_{result["object_id"]}.json', review)
        return review


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def send(self, value, mime='application/json', code=200, headers=None):
        data = json.dumps(value, allow_nan=False).encode() if mime == 'application/json' else value
        self.send_response(code)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        try:
            route = urlparse(self.path)
            args = parse_qs(route.query)
            app = self.server.app
            if route.path in ('/', '/app.js', '/style.css'):
                file, mime = {'/': ('index.html', 'text/html; charset=utf-8'),
                              '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}[route.path]
                return self.send((HERE / file).read_bytes(), mime)
            if route.path == '/api/config':
                return self.send(app.config())
            if route.path == '/api/health':
                return self.send(dict(app=APP_ID, output=str(app.output)))
            if route.path == '/api/galaxy':
                return self.send(app.galaxy(args['id'][0]))
            if route.path == '/api/display':
                pixels, meta = app.display_image(args['id'][0])
                return self.send(pixels, 'application/octet-stream', headers={'X-Image-Meta': json.dumps(meta)})
            if route.path == '/api/job':
                with app.lock:
                    return self.send(app.job or dict(status='idle'))
            if route.path == '/api/result':
                folder = app.folder('runs', args['id'][0])
                return self.send(json.loads((folder / 'result.json').read_text(encoding='utf8')))
            if route.path == '/api/file':
                kind, identifier, name = args['kind'][0], args['id'][0], args['name'][0]
                allowed = {'runs': {'image.png', 'labels.bin'},
                           'reviews': {'mask.fits', 'review.json', 'mask_review.png'},
                           'refits': {'geometry.png', 'ellipse_profile.csv', 'result.json'}}
                if name not in allowed.get(kind, set()):
                    raise ValueError('Unknown artifact')
                file = app.folder(kind, identifier) / name
                mime = 'image/png' if name.endswith('.png') else 'application/octet-stream'
                return self.send(file.read_bytes(), mime)
            self.send(dict(error='Not found'), code=404)
        except Exception as exc:
            self.send(dict(error=str(exc)), code=400)

    def do_POST(self):
        try:
            # Local browser only: reject cross-origin form/script submissions.
            host = self.headers.get('Host', '')
            origin = self.headers.get('Origin')
            if not host.startswith('127.0.0.1:') or (origin and origin != 'http://' + host):
                raise ValueError('Only same-origin local requests are accepted')
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('JSON request required')
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= 2_000_000:
                raise ValueError('Invalid request size')
            payload = json.loads(self.rfile.read(length))
            app = self.server.app
            if self.path == '/api/job':
                return self.send(app.start_job(payload))
            if self.path == '/api/mask':
                return self.send(app.mask(payload)[3])
            if self.path == '/api/save':
                return self.send(app.save(payload))
            self.send(dict(error='Not found'), code=404)
        except Exception as exc:
            self.send(dict(error=str(exc)), code=400)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalogue', type=Path, default=core.DEFAULT_CATALOGUE)
    parser.add_argument('--fits-dir', type=Path)
    parser.add_argument('--mtobjects-root', type=Path, default=Path(os.environ.get('MTOBJECTS_ROOT', core.ROOT / 'mtobjects')))
    parser.add_argument('--output', type=Path, default=HERE / 'saved_reviews')
    parser.add_argument('--all-targets', action='store_true')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    args.catalogue = args.catalogue.resolve()
    if args.fits_dir:
        args.fits_dir = args.fits_dir.resolve()
    app = Application(args)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.app = app
    url = f'http://127.0.0.1:{server.server_port}/'
    core.json_write(app.output / 'server.json', dict(url=url, pid=os.getpid(), app=APP_ID))
    print(f'Euclid masking reviewer: {url}', flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        try:
            worker(sys.argv[2])
        except Exception:
            traceback.print_exc()
            sys.exit(1)
    else:
        main()
