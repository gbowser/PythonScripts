import json,csv
from pathlib import Path
b=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid');r=list(csv.DictReader((b/'Euclid_MER_VIS_geometry_v2/MER_VIS_local_geometry_manifest.csv').open(encoding='utf8')));f=[x for x in r if x['codex_fit_status']=='provisional_fit'];z=max(f,key=lambda x:float(x['codex_centre_offset_arcsec']));m=json.loads((b/'MER_VIS_galaxy_reports/all_2777_v2/metadata'/f"{z['object_id']}.json").read_text());print(z['object_id'],z['codex_centre_offset_arcsec'],z['codex_quality_flags']);print(b/'MER_VIS_galaxy_reports/all_2777_v2'/m['relative_png'])
Path('MER_VIS_pipeline_v2/centre_review_card_path.txt').write_text(str(b/'MER_VIS_galaxy_reports/all_2777_v2'/m['relative_png']))
