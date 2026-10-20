from pathlib import Path
p=Path('MER_VIS_pipeline_v2/report_code/assemble_grouped_MER_VIS_reports.py');s=p.read_text(encoding='utf-8-sig').replace('import argparse,csv,json,math,gc,time','import argparse,csv,json,math,gc,time,shutil')
s=s.replace("if retry==8:raise\n     time.sleep", """if retry>=2:
      # Cloud sync can deny delete/rename while still allowing ordinary writes.
      # The verified staging collection is not promoted until every PDF reopens.
      try:
       shutil.copyfile(temp,path)
       try:temp.unlink()
       except PermissionError:pass
       break
      except PermissionError:pass
     if retry==8:raise
     time.sleep""")
p.write_text(s,encoding='utf8')
