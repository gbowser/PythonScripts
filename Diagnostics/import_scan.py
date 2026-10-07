import ast
import pathlib
import importlib

root = pathlib.Path('.').resolve()
exclude = {'.venv', '__pycache__', '.git', 'node_modules', 'build', 'dist'}
imports = {}
files = []
for p in root.rglob('*.py'):
    if any(part in exclude for part in p.parts):
        continue
    files.append(p)
    try:
        text = p.read_text(encoding='utf-8', errors='replace')
    except Exception:
        continue
    try:
        tree = ast.parse(text, filename=str(p))
    except Exception:
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                name = n.name.split('.')[0]
                if name:
                    imports.setdefault(name, set()).add(str(p))
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                name = node.module.split('.')[0]
                if name:
                    imports.setdefault(name, set()).add(str(p))
missing = []
for mod, paths in sorted(imports.items()):
    if mod in ('__future__',):
        continue
    try:
        importlib.import_module(mod)
    except Exception as e:
        missing.append((mod, str(e), len(paths), sorted(paths)[:5]))
print(f'TOTAL_FILES={len(files)}')
print(f'TOTAL_TOPLEVEL_IMPORTS={len(imports)}')
for mod, err, count, sample in missing:
    print(f'MISSING:{mod}:{count}:{err}')
