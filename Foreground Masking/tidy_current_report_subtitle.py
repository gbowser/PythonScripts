from pathlib import Path
p=Path('MER_VIS_pipeline_v2/build_current_MER_VIS_documents.py');s=p.read_text(encoding='utf-8-sig').replace('Independent adaptive Photutils pipeline with image-based centre checks','Adaptive Photutils pipeline with image-based centre checks');p.write_text(s,encoding='utf8')
