from pathlib import Path
from PIL import Image
import json
base=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\MER_VIS_galaxy_reports\all_2777_sampling_review');r=next(r for r in json.loads((base/'MER_VIS_report_manifest.json').read_text()) if r.get('catalogue_name'))
im=Image.open(base/r['relative_png']);im.crop((0,0,im.width,450)).save('MER_VIS_pipeline_v2/named_header_example.png');print(r['object_id'],r['catalogue_name'],r['catalogue_match_separation_arcsec'])
