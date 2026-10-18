"""Package generated MER VIS cutouts in resumable ZIP batches for browser download."""
import csv
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime, timezone


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(4*1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path, rows):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def package(work, max_files=100, max_mib=1024):
    """Keep native FITS files unchanged. Reuse verified completed batches."""
    work = Path(work).resolve()
    manifest = work/'MER_VIS_datalabs_manifest.csv'
    with manifest.open(newline='', encoding='utf-8-sig') as handle:
        targets = list(csv.DictReader(handle))
    if not targets or len({r['object_id'] for r in targets}) != len(targets):
        raise ValueError('Manifest empty or object IDs duplicated')
    if max_files < 1 or max_mib < 1:
        raise ValueError('Batch limits must be positive')
    files = [work/'cutouts'/f"Euclid_{r['object_id']}_MER_VIS_cutout.fits" for r in targets]
    missing = [p.name for p in files if not p.is_file()]
    if missing:
        raise FileNotFoundError(f'{len(missing)} missing cutouts; first: {missing[:3]}')
    if any(p.stat().st_size == 0 for p in files):
        raise ValueError('An empty cutout file was found')
    groups=[]; group=[]; size=0; max_bytes=int(max_mib*2**20)
    for path in files:
        length=path.stat().st_size
        if group and (len(group)>=max_files or size+length>max_bytes):
            groups.append(group);group=[];size=0
        group.append(path);size+=length
    if group:groups.append(group)
    folder=work/'download_batches';folder.mkdir(exist_ok=True)
    print(f'{len(files)} FITS files; {len(groups)} ZIP batches',flush=True)
    print(f'Native files total {sum(p.stat().st_size for p in files)/2**30:.2f} GiB.',flush=True)
    print('Check your personal quota: ZIP copies need additional space. Originals are retained.',flush=True)
    archive_rows=[];file_rows=[]
    for index,group in enumerate(groups,1):
        output=folder/f'MER_VIS_batch_{index:03d}.zip'
        sidecar=output.with_suffix('.json')
        expected=[dict(filename=p.name,size_bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns) for p in group]
        if output.exists():
            if not sidecar.exists():raise ValueError(f'Existing ZIP has no verification record: {output}')
            record=json.loads(sidecar.read_text(encoding='utf-8'))
            if record['input_files']!=expected or sha256(output)!=record['sha256']:
                raise ValueError(f'Existing batch changed; inspect before replacing: {output}')
            print(f'[{index}/{len(groups)}] Reused verified {output.name}',flush=True)
        else:
            needed=sum(p.stat().st_size for p in group)
            if shutil.disk_usage(folder).free<needed+2**30:
                raise OSError('Insufficient filesystem free space with 1 GiB reserve')
            temporary=output.with_suffix('.partial.zip')
            entries=[]
            with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as archive:
                for path in group:
                    digest=hashlib.sha256()
                    with path.open('rb') as source, archive.open(path.name,'w',force_zip64=True) as target:
                        for chunk in iter(lambda: source.read(4*1024*1024),b''):
                            digest.update(chunk);target.write(chunk)
                    entries.append(dict(filename=path.name,size_bytes=path.stat().st_size,sha256=digest.hexdigest()))
                archive.writestr('batch_file_checksums.json',json.dumps(entries,indent=2))
            temporary.replace(output)
            record=dict(input_files=expected,files=entries,sha256=sha256(output),created_utc=datetime.now(timezone.utc).isoformat())
            sidecar.write_text(json.dumps(record,indent=2),encoding='utf-8')
            print(f'[{index}/{len(groups)}] Created {output.name}: {output.stat().st_size/2**20:.1f} MiB',flush=True)
        archive_rows.append(dict(zip_filename=output.name,file_count=len(group),size_bytes=output.stat().st_size,sha256=record['sha256']))
        file_rows.extend(dict(zip_filename=output.name,**entry) for entry in record['files'])
        # Preserve a usable index after every completed batch.
        write_csv(folder/'MER_VIS_zip_index.csv',archive_rows)
        write_csv(folder/'MER_VIS_file_checksums.csv',file_rows)
    # A static copy records which catalogue entries these packages cover.
    (folder/'MER_VIS_datalabs_manifest.csv').write_bytes(manifest.read_bytes())
    print('Finished. Download the ZIPs plus MER_VIS_zip_index.csv and MER_VIS_file_checksums.csv.',flush=True)
    return folder


def show_links(work):
    """Display links relative to the currently open Jupyter notebook folder."""
    from IPython.display import FileLink, display
    import os
    folder=Path(work).resolve()/'download_batches'
    for path in sorted(folder.glob('MER_VIS_batch_*.zip')):
        display(FileLink(os.path.relpath(path,Path.cwd())))
    for name in ('MER_VIS_zip_index.csv','MER_VIS_file_checksums.csv','MER_VIS_datalabs_manifest.csv'):
        path=folder/name
        if path.exists():display(FileLink(os.path.relpath(path,Path.cwd())))
