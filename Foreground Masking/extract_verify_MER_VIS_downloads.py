"""Extract downloaded MER VIS batches, verify hashes, then remove only those ZIPs."""
import csv
import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

downloads = Path(r'C:\Users\gordo\Downloads').resolve()
output = Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_cutouts').resolve()

def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(8*1024*1024), b''):
            result.update(chunk)
    return result.hexdigest()

def read_csv(path):
    with path.open(newline='', encoding='utf-8-sig') as handle:
        return list(csv.DictReader(handle))

def main():
    index = read_csv(downloads/'MER_VIS_zip_index.csv')
    files = read_csv(downloads/'MER_VIS_file_checksums.csv')
    targets = read_csv(downloads/'MER_VIS_datalabs_manifest.csv')
    expected_names = {f"Euclid_{r['object_id']}_MER_VIS_cutout.fits" for r in targets}
    archives = sorted(p for p in downloads.glob('MER_VIS_batch_*.zip')
                      if re.fullmatch(r'MER_VIS_batch_\d{3}\.zip', p.name))
    assert len(index)==30 and len(archives)==30, 'Expected exactly 30 ZIP batches'
    assert {p.name for p in archives}=={r['zip_filename'] for r in index}, 'ZIP index mismatch'
    assert len(files)==2777 and len(expected_names)==2777, 'Expected 2777 distinct FITS files'
    assert {r['filename'] for r in files}==expected_names, 'Manifest/checksum filename mismatch'
    assert len({r['filename'] for r in files})==len(files), 'Duplicate FITS entries'
    by_archive={r['zip_filename']:r for r in index}
    checksums={r['filename']:r for r in files}
    required=sum(int(r['size_bytes']) for r in files)
    output.mkdir(parents=True,exist_ok=True)
    metadata=output/'transfer_verification';metadata.mkdir(exist_ok=True)
    assert shutil.disk_usage(output).free>required+2**30, 'Insufficient space with 1 GiB reserve'
    print(f'Found {len(archives)} batches; {len(files)} FITS; {required/2**30:.2f} GiB uncompressed',flush=True)
    verified=[];archive_stats={};seen=set()
    for number,path in enumerate(archives,1):
        assert path.resolve().parent==downloads and re.fullmatch(r'MER_VIS_batch_\d{3}\.zip',path.name)
        row=by_archive[path.name]
        stat=path.stat();archive_stats[path.name]=(stat.st_size,stat.st_mtime_ns)
        assert stat.st_size==int(row['size_bytes']), f'Archive size mismatch: {path.name}'
        print(f'[{number}/30] Verifying ZIP SHA256: {path.name}',flush=True)
        assert digest(path)==row['sha256'], f'Archive SHA256 mismatch: {path.name}'
        with zipfile.ZipFile(path) as archive:
            entries=json.loads(archive.read('batch_file_checksums.json'))
            names=[e['filename'] for e in entries]
            assert len(names)==int(row['file_count']) and len(set(names))==len(names)
            assert {i.filename for i in archive.infolist()}==set(names)|{'batch_file_checksums.json'}
            for entry in entries:
                name=entry['filename']
                assert re.fullmatch(r'Euclid_-?\d+_MER_VIS_cutout\.fits',name), 'Unexpected archive filename'
                assert name in expected_names and name not in seen, f'Unexpected/duplicate FITS: {name}'
                expected=checksums[name]
                assert expected['zip_filename']==path.name
                assert entry['sha256']==expected['sha256'] and int(entry['size_bytes'])==int(expected['size_bytes'])
                destination=output/name
                assert destination.resolve().parent==output, 'Unsafe extraction path'
                if destination.exists():
                    assert destination.stat().st_size==int(expected['size_bytes']) and digest(destination)==expected['sha256'], f'Existing file differs: {name}'
                else:
                    temporary=destination.with_suffix('.partial')
                    checksum=hashlib.sha256();length=0
                    with archive.open(name) as source,temporary.open('wb') as target:
                        for chunk in iter(lambda:source.read(8*1024*1024),b''):
                            checksum.update(chunk);target.write(chunk);length+=len(chunk)
                    assert length==int(expected['size_bytes']) and checksum.hexdigest()==expected['sha256'], f'FITS SHA256 mismatch: {name}'
                    # Verify the file actually stored on the destination before deleting its source ZIP.
                    assert digest(temporary)==expected['sha256'], f'Destination verification failed: {name}'
                    temporary.replace(destination)
                seen.add(name)
                verified.append(dict(filename=name,sha256=expected['sha256'],size_bytes=int(expected['size_bytes']),zip_filename=path.name))
            (metadata/f'{path.stem}_file_checksums.json').write_text(json.dumps(entries,indent=2),encoding='utf-8')
        print(f'[{number}/30] Extracted and verified {len(entries)} FITS; cumulative {len(seen)}/2777',flush=True)
    assert seen==expected_names
    for name in ('MER_VIS_zip_index.csv','MER_VIS_file_checksums.csv','MER_VIS_datalabs_manifest.csv'):
        destination=output/name
        if destination.exists():
            assert digest(destination)==digest(downloads/name), f'Existing metadata differs: {name}'
        else:shutil.copy2(downloads/name,destination)
    report=dict(verified_utc=datetime.now(timezone.utc).isoformat(),fits_verified=len(verified),
                sha256_verified=True,destination=str(output),archives_verified=[p.name for p in archives],
                archives_deleted=[],files=verified)
    report_path=metadata/'extraction_verification.json'
    report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    # All products and metadata are verified before any archive is removed.
    for path in archives:
        assert path.resolve().parent==downloads
        stat=path.stat()
        assert (stat.st_size,stat.st_mtime_ns)==archive_stats[path.name], 'ZIP changed during extraction'
    print('All 2777 FITS verified. Deleting the 30 verified MER VIS ZIP batches from Downloads.',flush=True)
    for path in archives:
        path.unlink()
        report['archives_deleted'].append(path.name)
        report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f'COMPLETE: {len(seen)} verified FITS in {output}; {len(report["archives_deleted"])} ZIPs deleted.',flush=True)

if __name__=='__main__':main()
