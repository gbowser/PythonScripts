"""Opt-in native MTO pilot validation; writes only to validation_output/<uuid>."""
import argparse
import json
from pathlib import Path
import time
import uuid

import masking_core as core
from reviewer import Application


def wait(app):
    deadline = time.monotonic() + 620
    while app.job['status'] == 'running':
        if time.monotonic() > deadline:
            raise TimeoutError('Validation job did not finish')
        time.sleep(.2)
    if app.job['status'] != 'complete':
        raise RuntimeError(app.job.get('error', 'Job failed'))
    return app.job['results']


def main():
    root = Path(__file__).resolve().parent
    output = root / 'validation_output' / uuid.uuid4().hex
    args = argparse.Namespace(output=output, catalogue=core.DEFAULT_CATALOGUE,
                              all_targets=False, fits_dir=None, mtobjects_root=core.ROOT / 'mtobjects')
    app = Application(args)
    report = dict(output=str(output), detections=[], sweep=[], refit=None)
    for row in app.rows:
        oid = row['object_id']
        print('Detect', oid, flush=True)
        app.start_job(dict(action='detect', object_id=oid, params={}))
        results = wait(app)
        r = results[0]
        report['detections'].append(dict(object_id=oid, run_id=r['run_id'],
                                         objects=len(r['objects']), target=r['target'],
                                         target_pixels=next(o['pixels'] for o in r['objects'] if o['target'])))
        if row.get('adoption_status') == 'reviewed_supported' and report['refit'] is None:
            selected = [o['label'] for o in r['objects'] if o['mask']]
            review = app.save(dict(run_id=r['run_id'], selected=selected, confirm=True,
                                   notes='AUTOMATED VALIDATION ONLY; not an adopted scientific review'))
            g = r['geometry']
            bounds = {k: g[k] for k in ('bar_min', 'bar_max', 'disc_min', 'disc_max')}
            print('Save/reload and masked refit', oid, bounds, flush=True)
            app.start_job(dict(action='refit', object_id=oid, params={}, review_id=review['review_id'], bounds=bounds))
            fit = wait(app)[0]
            report['refit'] = fit
            restored = app.galaxy(oid)['latest']
            assert restored['review_id'] == review['review_id']
            assert core.digest(core.source_path(row)) == r['source_sha256']
    print('Five-value sweep on close pair', flush=True)
    app.start_job(dict(action='sweep', object_id=app.rows[0]['object_id'], params={}))
    report['sweep'] = [dict(move_factor=r['params']['move_factor'], objects=len(r['objects']), run_id=r['run_id']) for r in wait(app)]
    core.json_write(output / 'validation.json', report)
    print('PASS', output / 'validation.json', flush=True)


if __name__ == '__main__':
    main()
