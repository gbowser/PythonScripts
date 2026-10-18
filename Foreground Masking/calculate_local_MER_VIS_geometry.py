"""Fit local MER VIS cutouts and compare geometry with cached Euclid morphology.

Run from PythonScripts with .venv/Scripts/python.exe. No image or metadata
downloads occur. The catalogue snapshot is the exact-ID Q1 comparison manifest.
"""
import argparse
import contextlib
import csv
import hashlib
import io
import json
import os
import sys
import time
import warnings
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUPPORT = HERE/'datalabs_MER_VIS'
DEFAULT_INPUT = Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_cutouts')
FIT_COLUMNS = {
    'bar_pa_deg':'codex_bar_pa_sky_deg', 'disk_pa_deg':'codex_disc_pa_sky_deg',
    'inclination_deg':'codex_inclination_deg', 'quality_flags':'codex_quality_flags',
    'disc_axis_ratio':'codex_disc_axis_ratio', 'radius_arcsec':'codex_radius_arcsec',
    'disc_pa_scatter_deg':'codex_disc_pa_scatter_deg', 'bar_pa_scatter_deg':'codex_bar_pa_scatter_deg',
    'bar_min_arcsec':'codex_bar_min_arcsec', 'bar_max_arcsec':'codex_bar_max_arcsec',
    'disc_min_arcsec':'codex_disc_min_arcsec', 'disc_max_arcsec':'codex_disc_max_arcsec',
}

def load(path):
    with Path(path).open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def save(path, rows):
    fields=list(dict.fromkeys(key for row in rows for key in row))
    temporary=path.with_suffix('.tmp')
    with temporary.open('w', newline='', encoding='utf-8') as f:
        writer=csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    # Dropbox and Windows indexing can briefly hold a newly written CSV open.
    for attempt in range(6):
        try:
            temporary.replace(path)
            return
        except PermissionError as error:
            if attempt==5:
                raise PermissionError(f'Close {path.name} in Excel or other programs, then resume this run. Checkpoint is in {temporary}.') from error
            time.sleep(min(.5*2**attempt,4))

def number(value):
    import math
    try:
        result=float(value)
        return result if math.isfinite(result) else None
    except (ValueError,TypeError):
        return None

def calculate(task):
    """One independent galaxy; called in a separate process when workers > 1."""
    row, input_dir, output_dir, ranges = task
    row=dict(row)
    started=time.monotonic()
    # Keep each process within its CPU allocation.
    for variable in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
        os.environ[variable]='1'
    sys.path.insert(0,str(SUPPORT))
    from astropy.io import fits
    from astropy.wcs import WCS
    import numpy as np
    from fit_MER_VIS_geometry_portable import fit_one, sky_pa
    from MER_VIS_geometry_transforms import local_pixel_matrix
    path=Path(input_dir)/row['fits_filename']
    row.update(fits_path=str(path),codex_fit_status='fit_failed',codex_error='')
    for name in FIT_COLUMNS.values(): row[name]=''
    log=io.StringIO()
    try:
        stat=path.stat()
        row['input_size_bytes']=stat.st_size; row['input_mtime_ns']=stat.st_mtime_ns
        with fits.open(path,memmap=True) as hdul:
            header=hdul[0].header.copy()
            if str(header.get('GALID',''))!=row['object_id']:
                raise ValueError('FITS GALID differs from catalogue object_id')
            if len(hdul[0].shape or ())!=2: raise ValueError('Expected a 2D primary SCI image')
        row['cutout_partial']=header.get('PARTIAL','')
        wcs=WCS(header).celestial
        xc,yc=float(header['CENX'])-1,float(header['CENY'])-1
        matrix=local_pixel_matrix(wcs,wcs.pixel_to_world(xc,yc),xc,yc)
        angle=number(row.get('euclid_detection_pa_pixel_deg'))
        if angle is not None:
            row['euclid_detection_pa_sky_deg']=sky_pa(np.radians(angle),matrix)
            row['euclid_detection_pa_conversion_status']='THETA_IMAGE_through_native_MER_cutout_WCS'
        sma=number(row.get('euclid_detection_semimajor_axis_pix'))
        if sma is not None and angle is not None:
            direction=matrix@np.array([np.cos(np.radians(angle)),np.sin(np.radians(angle))])
            row['euclid_detection_semimajor_axis_arcsec']=sma*float(np.linalg.norm(direction))
        with warnings.catch_warnings(record=True) as caught, contextlib.redirect_stdout(log):
            warnings.simplefilter('always')
            fit=fit_one(path,Path(output_dir)/'profiles',q0=0.,ranges=ranges,previews=False)
        row['codex_fit_warnings']='; '.join(dict.fromkeys(str(w.message) for w in caught))
        for source,target in FIT_COLUMNS.items():row[target]=fit[source]
        row['codex_fit_status']='reviewed_ranges' if fit['status']=='reviewed_ranges' else 'provisional_fit'
        row['disc_vs_detection_pa_difference_deg']=(float(row['codex_disc_pa_sky_deg'])-float(row['euclid_detection_pa_sky_deg'])+90)%180-90 if number(row.get('euclid_detection_pa_sky_deg')) is not None else ''
        for proxy,label in [('euclid_detection_inclination_proxy_deg','inclination_vs_detection_proxy_difference_deg'),('euclid_sersic_inclination_proxy_deg','inclination_vs_sersic_proxy_difference_deg')]:
            row[label]=float(row['codex_inclination_deg'])-float(row[proxy]) if number(row.get(proxy)) is not None else ''
    except Exception as error:
        row['codex_error']=f'{type(error).__name__}: {error}'
    finally:
        row['calculation_seconds']=round(time.monotonic()-started,3)
        row['calculated_utc']=datetime.now(timezone.utc).isoformat()
        (Path(output_dir)/'logs'/f"Euclid_{row['object_id']}_MER_VIS_fit.log").write_text(log.getvalue()+('\n'+row['codex_error'] if row['codex_error'] else ''),encoding='utf-8')
    return row

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,default=DEFAULT_INPUT)
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--catalogue-csv',type=Path,default=SUPPORT/'MER_VIS_geometry_comparison_manifest.csv')
    parser.add_argument('--workers',type=int,default=2,help='Parallel galaxy fits, default 2')
    parser.add_argument('--limit',type=int,help='Pilot: process only the first N catalogue objects; retain all manifest rows')
    parser.add_argument('--retry-failures',action='store_true')
    parser.add_argument('--ranges-csv',type=Path,help='Optional reviewed bar/disc ranges in arcseconds')
    args=parser.parse_args()
    if args.workers<1 or (args.limit is not None and args.limit<1):parser.error('workers and limit must be positive')
    rows=load(args.catalogue_csv)
    if not rows or len({r['object_id'] for r in rows})!=len(rows):parser.error('Empty catalogue or duplicate object IDs')
    if not args.input_dir.is_dir():parser.error(f'Input folder missing: {args.input_dir}')
    for row in rows:
        if Path(row['fits_filename']).name!=row['fits_filename']:parser.error('Expected simple FITS filenames')
        row['fits_path']=str((args.input_dir/row['fits_filename']).resolve())
        row['codex_fit_status']='not_processed_local'
        for field in FIT_COLUMNS.values():row[field]=''
    out=args.output_dir or args.input_dir.parent/'Euclid_MER_VIS_geometry'
    out.mkdir(parents=True,exist_ok=True)
    (out/'profiles').mkdir(exist_ok=True);(out/'logs').mkdir(exist_ok=True)
    destination=out/'MER_VIS_local_geometry_manifest.csv'
    config_path=out/'MER_VIS_local_geometry_run.json'
    ranges={}
    if args.ranges_csv:
        ranges={r['object_id']:r for r in load(args.ranges_csv)}
    # Resume only against the same algorithm, catalogue and range choices.
    config=dict(input_dir=str(args.input_dir.resolve()),q0=0,
                catalogue_sha256=hashlib.sha256(args.catalogue_csv.read_bytes()).hexdigest(),
                fitter_sha256=hashlib.sha256((SUPPORT/'fit_MER_VIS_geometry_portable.py').read_bytes()).hexdigest(),
                ranges=ranges)
    if destination.exists():
        if not config_path.exists() or json.loads(config_path.read_text(encoding='utf-8'))!=config:
            parser.error('Existing run configuration differs. Select a new --output-dir to preserve those results.')
        previous={r['object_id']:r for r in load(destination)}
        if set(previous)!={r['object_id'] for r in rows}:parser.error('Existing manifest IDs differ')
        for row in rows:row.update(previous[row['object_id']])
    else:
        config_path.write_text(json.dumps(config,indent=2),encoding='utf-8')
    by_id={r['object_id']:r for r in rows}
    selected=rows if args.limit is None else rows[:args.limit]
    tasks=[]
    for row in selected:
        path=args.input_dir/row['fits_filename']
        unchanged=path.is_file() and str(path.stat().st_size)==str(row.get('input_size_bytes','')) and str(path.stat().st_mtime_ns)==str(row.get('input_mtime_ns',''))
        if unchanged and row['codex_fit_status'] in ('provisional_fit','reviewed_ranges'):continue
        if unchanged and row['codex_fit_status']=='fit_failed' and not args.retry_failures:continue
        tasks.append((row.copy(),str(args.input_dir),str(out),ranges.get(row['object_id'])))
    save(destination,rows)
    print(f'{len(rows)} manifest rows; {len(tasks)} fits to run; workers={args.workers}',flush=True)
    print(f'Manifest: {destination}',flush=True)
    started=time.monotonic(); completed=0
    try:
        if args.workers==1:
            results=map(calculate,tasks)
            for result in results:
                by_id[result['object_id']].update(result);completed+=1
                print(f"[{completed}/{len(tasks)}] {result['object_id']}: {result['codex_fit_status']} {result['codex_error']}",flush=True)
                if completed%5==0:save(destination,rows)
        else:
            with ProcessPoolExecutor(max_workers=args.workers) as executor:
                futures={executor.submit(calculate,task):task[0]['object_id'] for task in tasks}
                for future in as_completed(futures):
                    result=future.result()
                    by_id[result['object_id']].update(result);completed+=1
                    print(f"[{completed}/{len(tasks)}] {result['object_id']}: {result['codex_fit_status']} {result['codex_error']}",flush=True)
                    if completed%5==0:save(destination,rows)
    finally:
        save(destination,rows)
        summary=dict(total_galaxies=len(rows),statuses=dict(Counter(r['codex_fit_status'] for r in rows)),
                     fitted_without_quality_flags=sum(r['codex_fit_status'] in ('provisional_fit','reviewed_ranges') and not r['codex_quality_flags'] for r in rows),
                     elapsed_this_run_seconds=round(time.monotonic()-started,2),manifest=str(destination))
        (out/'MER_VIS_local_geometry_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
    main()
