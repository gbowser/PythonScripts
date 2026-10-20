from pathlib import Path
p=Path('MER_VIS_pipeline_v2/build_current_MER_VIS_documents.py');s=p.read_text(encoding='utf-8-sig');s=s.replace("{e['centre_offset'] if e['centre_offset'] is not None else 'unavailable'}", "{format(e['centre_offset'],'.3f') if e['centre_offset'] is not None else 'unavailable'}")
s=s.replace('The manifest stores both pixel positions, their angular offset', 'The manifest stores both zero-based pixel positions, their angular offset')
p.write_text(s,encoding='utf8')
