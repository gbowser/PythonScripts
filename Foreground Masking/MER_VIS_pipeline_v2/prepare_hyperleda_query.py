from pathlib import Path
p=Path('MER_VIS_pipeline_v2/query_catalogue_names.py');s=p.read_text(encoding='utf8').replace("'cat2':'simbad'","'cat2':'vizier:VII/237/pgc'").replace('SIMBAD_candidates_5arcsec.csv','HyperLEDA_candidates_5arcsec.csv');Path('MER_VIS_pipeline_v2/query_hyperleda_names.py').write_text(s,encoding='utf8')
