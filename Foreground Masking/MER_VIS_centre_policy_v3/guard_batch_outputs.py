from pathlib import Path
p=Path('MER_VIS_review_tool/fit_centred_MER_VIS_geometry.py');s=p.read_text(encoding='utf8');s=s.replace('def run_one(task):','def _run_one(task):',1);pos=s.index('\ndef main():');s=s[:pos]+'''
def run_one(task):
 try:return _run_one(task)
 except Exception as exc:
  row=dict(task[0])
  for key in row:
   if key.startswith('codex_') or key.endswith('_difference_deg'):row[key]=''
  row.update(codex_fit_status='fit_failed',codex_error=f'{type(exc).__name__}: {exc}',centre_batch_requires_review=True)
  return row
''' +s[pos:];s=s.replace("if a.catalogue.resolve()==(a.output_dir/'MER_VIS_centre_constrained_manifest.csv').resolve():", "if (a.output_dir/'MER_VIS_centre_constrained_manifest.json').exists():parser.error('Choose a new output folder to preserve previous trials')\n if a.catalogue.resolve()==(a.output_dir/'MER_VIS_centre_constrained_manifest.csv').resolve():");p.write_text(s,encoding='utf8')
