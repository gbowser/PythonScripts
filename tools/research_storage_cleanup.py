"""Audit large local files and relocate the reviewed 2026-11-17 data set.

Run from the repository root. Default is read-only; --move writes a hash-checked
manifest in the research archive and removes only verified source copies.
Installed libraries/environments are inventoried but stay in place.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research')
AUDIT = ARCHIVE / 'Repository_maintenance/2026-11-17_git_storage'
FULL = 'Euclid/DR1/barred_galaxy_pilot/full_manifest'
FILES = [
    'Complete-Python-3-Bootcamp-master/Complete-Python-3-Bootcamp-master.zip',
    'outputs/tesla-20261007/Tesla_Battery_Savings_2026.xlsx.inspect.ndjson',
    'Euclid/reports/MER_VIS_review_2026-10-29/MER_VIS_reviewed_adoption_manifest.json',
    'Foreground Masking/MER_VIS_adoption_2026_10_29/MER_VIS_reviewed_adoption_manifest.json',
]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def scan():
    tracked = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0'))
    large, errors, folders = [], [], {}
    for base, dirs, files in os.walk(ROOT, onerror=lambda e: errors.append(str(e))):
        dirs[:] = [d for d in dirs if d != '.git']
        for name in files:
            p = Path(base) / name
            try:
                size = p.stat().st_size
            except OSError as exc:
                errors.append(str(exc))
                continue
            rel = p.relative_to(ROOT).as_posix()
            top = rel.split('/')[0]
            folders[top] = folders.get(top, 0) + size
            if size > 20_000_000:
                large.append(dict(path=rel, bytes=size, tracked=rel in tracked))
    return dict(threshold_bytes=20_000_000, large=large, folder_bytes=folders, errors=errors)


def candidates():
    paths = [ROOT / name for name in FILES]
    paths += [p for p in (ROOT / FULL).rglob('*') if p.is_file()
              and p.suffix.lower() not in {'.py', '.md', '.txt'}
              and '__pycache__' not in p.parts]
    paths += [p for p in (ROOT / 'Euclid/masking_review/validation_output').rglob('*') if p.is_file()]
    return sorted(set(p for p in paths if p.exists()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--move', action='store_true')
    args = parser.parse_args()
    report = scan()
    paths = candidates()
    report['planned_files'] = len(paths)
    report['planned_bytes'] = sum(p.stat().st_size for p in paths)
    if not args.move:
        print(json.dumps(report, indent=2))
        return
    if not ARCHIVE.is_dir():
        raise RuntimeError(f'Research storage unavailable: {ARCHIVE}')
    AUDIT.mkdir(parents=True, exist_ok=True)
    (AUDIT / 'before.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    records = []
    # Preflight every destination before moving anything; never overwrite a
    # different existing research result.
    for source in paths:
        rel = source.relative_to(ROOT)
        target = ARCHIVE / rel
        if not source.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError(source)
        if not target.resolve().is_relative_to(ARCHIVE.resolve()):
            raise ValueError(target)
        sha = digest(source)
        if target.exists() and digest(target) != sha:
            raise FileExistsError(f'Different archive copy already exists: {target}')
        records.append(dict(path=rel.as_posix(), bytes=source.stat().st_size, sha256=sha))
    manifest = AUDIT / 'moves.json'
    manifest.write_text(json.dumps(records, indent=2), encoding='utf8')
    for record in records:
        source, target = ROOT / record['path'], ARCHIVE / record['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(source, target)
        if digest(target) != record['sha256'] or digest(source) != record['sha256']:
            raise RuntimeError(f'Hash mismatch: {source}')
        source.unlink()
    (AUDIT / 'after.json').write_text(json.dumps(scan(), indent=2), encoding='utf8')
    print(json.dumps(dict(moved_files=len(records), moved_bytes=sum(r['bytes'] for r in records),
                          manifest=str(manifest)), indent=2))


if __name__ == '__main__':
    main()
