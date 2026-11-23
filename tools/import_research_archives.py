"""Inspect four reviewed research ZIPs; --apply places hash-verified members.

Existing differing files are preserved. Active source wins; old archive versions
go into archive_imports beside the source/data. Original ZIPs are retained.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import zipfile
import uuid

REPO = Path(__file__).resolve().parents[1]
PILOT = Path('Euclid/DR1/barred_galaxy_pilot')
Q1 = Path('Euclid/Q1/datalabs_MER_VIS/source_extraction_pilot')
NAMES = {'DR1_All_Qualifying_Manifests.zip', 'DR1_Manifests.zip',
         'DR1_Barred_Galaxy_Pilot.zip', 'ESA_Source_Extraction_Pilot.zip'}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def contained(root, relative):
    root = root.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError(f'Unsafe destination: {relative}')
    return path


def source_member(name):
    p = PurePosixPath(name)
    return len(p.parts) == 1 and (p.suffix in {'.py', '.ipynb', '.md'}
                                  or p.name == 'requirements.txt')


def ensure_file(target, expected, writer, apply):
    if target.exists():
        if not target.is_file() or sha(target) != expected:
            raise ValueError(f'Existing destination differs: {target}')
        return 'verified_existing'
    if apply:
        target.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation never replaces an existing file.
        with target.open('xb') as stream:
            writer(stream)
        if sha(target) != expected:
            raise ValueError(f'Written hash mismatch: {target}')
    return 'created' if apply else 'would_create'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research-root', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    research = args.research_root.resolve(strict=True)
    maintenance = research / 'Repository_maintenance'
    archives = sorted(maintenance.rglob('*.zip'))
    if len(archives) != 4 or {p.name for p in archives} != NAMES:
        raise ValueError('ZIP inventory changed; review before extending this import')
    report = dict(research_root=str(research), apply=args.apply, archives=[],
                  relocations=[], entries=[])
    # Keep each generated pilot tree intact, including gallery-relative links.
    pilot = REPO / PILOT
    generated = [p for name in ('preview_results', 'query_evidence')
                 for p in (pilot / name).rglob('*') if p.is_file()]
    generated += [pilot / name for name in ('gallery.html', 'benchmark_manifest.csv',
                  'DR1_first100_review.csv', 'SHA256.json') if (pilot / name).is_file()]
    moves = []
    for old in sorted(generated):
        old = contained(REPO, old.relative_to(REPO))
        new = contained(research, old.relative_to(REPO))
        digest = sha(old)
        if new.exists() and sha(new) != digest:
            raise ValueError(f'Relocation conflict: {new}')
        moves.append((old, new, digest))
    # Validate every archive path and CRC before modifying anything.
    for archive in archives:
        with zipfile.ZipFile(archive) as z:
            seen = set()
            for i in z.infolist():
                name = PurePosixPath(i.filename)
                if (name.is_absolute() or '..' in name.parts or '\\' in i.filename
                        or ':' in i.filename or stat.S_ISLNK(i.external_attr >> 16)
                        or i.filename.casefold() in seen):
                    raise ValueError(f'Unsafe/duplicate ZIP member: {i.filename}')
                seen.add(i.filename.casefold())
            bad = z.testzip()
            if bad:
                raise ValueError(f'Corrupt ZIP member: {bad}')
    for old, new, digest in moves:
        result = ensure_file(new, digest,
                             lambda stream, p=old: copy_path(p, stream), args.apply)
        report['relocations'].append(dict(source=str(old), destination=str(new),
                                         sha256=digest, bytes=old.stat().st_size,
                                         status=result))
        if args.apply:
            # Recheck both exact files immediately before removing source.
            if sha(old) != digest or sha(new) != digest:
                raise ValueError('Relocation changed during verification')
            old.unlink()
    for archive in archives:
        full = archive.name in {'DR1_All_Qualifying_Manifests.zip', 'DR1_Manifests.zip'}
        base = Q1 if archive.name.startswith('ESA_') else PILOT / ('full_manifest' if full else '')
        report['archives'].append(dict(path=str(archive), sha256=sha(archive),
                                        bytes=archive.stat().st_size))
        with zipfile.ZipFile(archive) as z:
            for i in z.infolist():
                if i.is_dir():
                    continue
                data = z.read(i)
                digest = hashlib.sha256(data).hexdigest()
                source = source_member(i.filename)
                root = REPO if source else research
                target = contained(root, base / i.filename)
                historical = target.exists() and sha(target) != digest
                if historical:
                    target = contained(root, base / 'archive_imports' / archive.stem / i.filename)
                result = ensure_file(target, digest,
                                     lambda stream, b=data: stream.write(b), args.apply)
                report['entries'].append(dict(archive=archive.name, member=i.filename,
                    destination=str(target), sha256=digest, bytes=len(data),
                    historical_version=historical, status=result))
    report['summary'] = dict(archives=len(archives), members=len(report['entries']),
        status_counts=dict(Counter(r['status'] for r in report['entries'])),
        historical_members=sum(r['historical_version'] for r in report['entries']),
        relocated_files=len(moves), relocated_bytes=sum(r['bytes'] for r in report['relocations']))
    if args.apply:
        audit = maintenance / '2026-11-23_archive_import'
        audit.mkdir(exist_ok=True)
        manifest = audit / 'import_manifest.json'
        if manifest.exists():
            manifest = audit / f'import_manifest_{uuid.uuid4().hex}.json'
        with manifest.open('x', encoding='utf8') as stream:
            json.dump(report, stream, indent=2)
    print(json.dumps(report['summary'], indent=2))
    for r in report['entries']:
        if r['historical_version']:
            print('PRESERVE HISTORICAL', r['destination'])


def copy_path(path, stream):
    with path.open('rb') as source:
        shutil.copyfileobj(source, stream)


if __name__ == '__main__':
    main()
