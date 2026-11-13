from pathlib import Path
p=Path('MER_VIS_pipeline_v2/report_code/assemble_grouped_MER_VIS_reports.py');s=p.read_text(encoding='utf-8-sig');s=s.replace('import argparse,csv,json,math,gc','import argparse,csv,json,math,gc,time')
s=s.replace('c.save();temp.replace(path);batches.append',"""c.save()
   for retry in range(9):
    try:temp.replace(path);break
    except PermissionError:
     if retry==8:raise
     time.sleep(min(.5*2**retry,8))
   batches.append""")
p.write_text(s,encoding='utf8')
