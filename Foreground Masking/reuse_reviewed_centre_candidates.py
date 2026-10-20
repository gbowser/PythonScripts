from pathlib import Path
p=Path('MER_VIS_pipeline_v2/finalize_MER_VIS_geometry.py');s=p.read_text(encoding='utf-8-sig').replace('import csv,json,math,hashlib','import csv,json,math,hashlib,shutil')
s=s.replace("p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()", "p.add_argument('--baseline',type=Path,required=True);p.add_argument('--recovery-cache-dir',type=Path);a=p.parse_args()")
s=s.replace('retried=[]\nfor i,r in enumerate(rows):',"""retried=[]
cache={}
if a.recovery_cache_dir:
 cache_config=json.loads((a.recovery_cache_dir/'MER_VIS_v2_run.json').read_text())
 assert cache_config['code_sha256']==hashlib.sha256((Path(__file__).parent/'recover_failed_MER_VIS_geometry.py').read_bytes()).hexdigest(),'Recovery cache algorithm mismatch'
 cache={z['object_id']:z for z in csv.DictReader((a.recovery_cache_dir/'MER_VIS_local_geometry_manifest.csv').open(encoding='utf8'))}
 assert set(cache).issubset({z['object_id'] for z in rows if z['codex_fit_status']=='fit_failed'})
for i,r in enumerate(rows):""")
s=s.replace("updated=recover((r,str(Path(r['fits_path']).parent),str(a.geometry_dir),seg.get(r['object_id'])))", """if r['object_id'] in cache:
   updated=dict(r);updated.update(cache[r['object_id']])
   pp=a.recovery_cache_dir/'profiles'/f\"Euclid_{r['object_id']}_MER_VIS_ellipse_profile.csv\"
   if pp.exists():shutil.copyfile(pp,a.geometry_dir/'profiles'/pp.name)
  else:updated=recover((r,str(Path(r['fits_path']).parent),str(a.geometry_dir),seg.get(r['object_id'])))""")
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_pipeline_v2/report_code/assemble_grouped_MER_VIS_reports.py');s=p.read_text(encoding='utf-8-sig');s=s.replace("p.add_argument('--batch-size'", "p.add_argument('--only-batches',nargs='*');p.add_argument('--batch-size'")
needle="   c=canvas.Canvas(str(temp)";insert="""   if a.only_batches and name not in a.only_batches:
    if not path.is_file():raise FileNotFoundError(path)
    for j,r in enumerate(selected):index.append(dict(object_id=r['object_id'],quality_issue=qi,fit_status=r['status'],quality_flags=';'.join(r['quality_flags']),partial_coverage=r['partial'],png=r['relative_png'],pdf=str(path.relative_to(base)),pdf_page=j//6+1,position_on_page=j%6+1))
    batches.append(dict(group=label,pdf=str(path.relative_to(base)),galaxies=len(selected),pages=pages))
    continue
""";assert needle in s;s=s.replace(needle,insert+needle);p.write_text(s,encoding='utf8')
