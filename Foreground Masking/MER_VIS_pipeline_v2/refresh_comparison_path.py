from pathlib import Path
p=Path('MER_VIS_pipeline_v2/compare_current_MER_VIS_with_supplied.py');s=p.read_text(encoding='utf8').replace('Euclid_MER_VIS_geometry_v2','Euclid_MER_VIS_geometry');p.write_text(s,encoding='utf8')
