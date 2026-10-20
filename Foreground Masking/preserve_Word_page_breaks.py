from pathlib import Path
p=Path('MER_VIS_pipeline_v2/build_current_MER_VIS_documents.py');s=p.read_text(encoding='utf-8-sig');s=s.replace("run.text=run.text.replace('modulo180'", "updated=run.text.replace('modulo180'")
s=s.replace(".replace('maximum0.604','maximum 0.604')\n d.core_properties", ".replace('maximum0.604','maximum 0.604')\n   if updated!=run.text:run.text=updated\n d.core_properties")
p.write_text(s,encoding='utf8')
