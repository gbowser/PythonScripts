from pathlib import Path
import json,math,hashlib
import pandas as pd
from PIL import Image
from pypdf import PdfReader
out=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\MER_VIS_galaxy_reports\pilot_10');rows=json.loads((out/'MER_VIS_report_sample_data.json').read_text());d=pd.read_csv(out.parent.parent/'Euclid_MER_VIS_geometry'/'MER_VIS_local_geometry_manifest.csv',dtype={'object_id':str}).set_index('object_id');assert len(rows)==10
for r in rows:
 assert Image.open(out/r['png']).size==(2000,1750)
 a=d.loc[r['object_id']];assert math.isclose(r['euclid_adjusted_detection_pa_deg'],(a.euclid_detection_pa_sky_deg+90)%180,abs_tol=1e-9)
 if a.codex_fit_status=='fit_failed':assert r['photutils_disc_pa_deg'] is None and r['delta_disc_pa_deg']=='—'
 else:assert math.isclose(r['photutils_disc_pa_deg'],a.codex_disc_pa_sky_deg,abs_tol=1e-9)
assert len(PdfReader('MER_VIS_report_work/pilot_png_qa/MER_VIS_pilot_10_six_per_page.pdf').pages)==2
print('Verified 10 PNG dimensions, catalogue adjustments, fitted values, failed-fit blanks, and two PDF pages.')
