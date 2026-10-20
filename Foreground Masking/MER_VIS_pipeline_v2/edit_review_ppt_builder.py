from pathlib import Path
s=Path('MER_VIS_pipeline_v2/finish_review_builders.py').read_text(encoding='utf-8-sig');s='from pathlib import Path\n'+s[s.index("p=Path('MER_VIS_pipeline_v2/build_current_MER_VIS_presentation.mjs')"):];s=s.replace('p.write_text(s)','p.write_text(s,encoding="utf8")');exec(compile(s,'ppt_edits','exec'))
