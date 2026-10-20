from pathlib import Path
p=Path('MER_VIS_pipeline_v2/build_current_MER_VIS_presentation.mjs');s=p.read_text(encoding='utf-8-sig');needle="txt(s,'Recovery and missing-bar warnings are counted."
s=s.replace(needle,"txt(s,`Failed: ${q.failures} (${pct(q.failures)})`,870,574,345,35,22,'#a43c38',true);"+needle)
p.write_text(s,encoding='utf8')
