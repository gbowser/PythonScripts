from pathlib import Path
p=Path('MER_VIS_pipeline_v2/prepare_current_MER_VIS_report_data.py');s=p.read_text(encoding='utf-8-sig');s=s.replace("full_card=str(src)","full_card=str(src).replace('all_2777_v2','all_2777')");p.write_text(s,encoding='utf8')
