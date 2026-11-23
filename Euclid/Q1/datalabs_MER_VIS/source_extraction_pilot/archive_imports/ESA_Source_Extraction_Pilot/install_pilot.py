"""Workspace-only SEP and MTObjects installer. Run from the supplied notebook."""
from pathlib import Path
import importlib.metadata as md
import json, os, platform, shutil, subprocess, sys, venv

def install(root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if platform.system() != 'Linux':
        raise RuntimeError('This installer targets Linux ESA Datalabs, not Windows.')
    env = root / 'environment'
    if not (env / 'bin/python').exists():
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(env)
    python = env / 'bin/python'
    # Reuse the Euclid scientific stack and constrain its core versions.
    constraints = root / 'base_constraints.txt'
    versions = {}
    for name in ('numpy', 'scipy', 'astropy', 'matplotlib', 'Pillow'):
        versions[name] = md.version(name)  # fail clearly if wrong kernel selected
    constraints.write_text(''.join(f'{k}=={v}\n' for k,v in versions.items()))
    def run(args, cwd=None, quiet=False, environment=None):
        result = subprocess.run([str(x) for x in args], cwd=cwd, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=environment)
        if not quiet or result.returncode:
            print(result.stdout, flush=True)
        if result.returncode:
            raise RuntimeError(f'Command failed ({result.returncode}): {args}')
        return result.stdout
    run([python, '-m', 'pip', 'install', '-c', constraints, 'sep', 'scikit-image'])
    run([python, '-c', 'import numpy, scipy, astropy, matplotlib, sep, skimage; print("Scientific imports OK; SEP", sep.__version__)'])
    source = root / 'mtobjects'
    info = dict(python=str(python), base_versions=versions, mtobjects_ready=False)
    try:
        for command in ('git', 'gcc'):
            if not shutil.which(command):
                raise RuntimeError(f'{command} is not available; SEP can still run.')
        url = 'https://github.com/CarolineHaigh/mtobjects.git'
        if not source.exists():
            run(['git', 'clone', url, source])
        elif not (source / '.git').is_dir():
            raise RuntimeError('Existing mtobjects folder is not a Git checkout; inspect it.')
        remote = run(['git', 'remote', 'get-url', 'origin'], source).strip()
        if remote.removesuffix('.git') != url.removesuffix('.git'):
            raise RuntimeError('Unexpected MTObjects remote; inspect before proceeding.')
        # Existing checkout is deliberately not pulled or reset on rerun.
        info['mtobjects_commit'] = run(['git', 'rev-parse', 'HEAD'], source).strip()
        lib = source / 'mtolib/lib'; lib.mkdir(exist_ok=True)
        src = source / 'mtolib/src'
        # MTObjects includes gsl/gsl_cdf.h: headers AND linked libraries are required.
        gsl = root / 'gsl-runtime'
        if not (gsl / 'include/gsl/gsl_cdf.h').is_file():
            conda = shutil.which('conda') or str(Path(sys.base_prefix) / 'bin/conda')
            if not Path(conda).is_file():
                raise RuntimeError('Conda not found; cannot install workspace GSL dependency')
            conda_env = os.environ.copy()
            conda_env['CONDA_PKGS_DIRS'] = str(root / 'conda_packages')
            run([conda, 'create', '--yes', '--prefix', gsl, '--override-channels',
                 '--channel', 'conda-forge', 'gsl'], environment=conda_env)
        if not (gsl / 'include/gsl/gsl_cdf.h').is_file():
            raise RuntimeError('GSL installation did not provide gsl_cdf.h')
        info['gsl_prefix'] = str(gsl)
        native_env = os.environ.copy()
        native_env['LD_LIBRARY_PATH'] = str(gsl / 'lib') + os.pathsep + native_env.get('LD_LIBRARY_PATH', '')
        # Record the exact native dependency versions alongside the Python packages.
        info['gsl_environment'] = json.loads(run([conda, 'list', '--prefix', gsl, '--json'], quiet=True)) if 'conda' in locals() else [
            json.loads(p.read_text()) for p in sorted((gsl / 'conda-meta').glob('*.json'))]
        for suffix, header in (('', 'main.h'), ('_double', 'main_double.h')):
            for name, files in (('mt_objects', ['mt_objects.c','mt_heap.c','mt_node_test_4.c']),
                                ('maxtree', ['maxtree.c','mt_stack.c','mt_heap.c'])):
                run(['gcc', '-shared', '-fPIC', '-I', gsl / 'include', '-include', header,
                     '-o', lib / f'{name}{suffix}.so', *files, '-L', gsl / 'lib',
                     '-Wl,--disable-new-dtags,-rpath,' + str(gsl / 'lib'),
                     '-lgsl', '-lgslcblas', '-lm'], src)
        run([python, '-c', 'import mtolib.main; print("MTObjects native imports OK")'], source, environment=native_env)
        info['mtobjects_ready'] = True
    except Exception as error:
        info['mtobjects_setup_error'] = str(error)
        print('MTObjects setup incomplete:', error)
    info['packages'] = json.loads(run([python,'-m','pip','list','--format=json'], quiet=True))
    (root / 'installation.json').write_text(json.dumps(info, indent=2))
    print('Installation record:', root / 'installation.json')
    return info
