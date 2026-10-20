from pathlib import Path
import csv,json,sys
sys.path.insert(0,str(Path(__file__).parent/'review_code'))
from make_MER_VIS_galaxy_report_cards import make_card
base=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid');geo=base/'Euclid_MER_VIS_geometry';cards=base/'MER_VIS_galaxy_reports/all_2777_sampling_review';out=Path(__file__).parent/'failed_review_cards';out.mkdir(exist_ok=True)
for k,r in enumerate(csv.DictReader((geo/'MER_VIS_local_geometry_manifest.csv').open()),1):
 if r['codex_fit_status']=='fit_failed':make_card(r,geo/'profiles',out,k);print(k,r['object_id'])
