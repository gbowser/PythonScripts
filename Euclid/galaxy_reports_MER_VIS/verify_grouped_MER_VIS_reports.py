from pathlib import Path
import json,csv,math,hashlib
from collections import Counter
import pandas as pd
from PIL import Image
from pypdf import PdfReader
base=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\MER_VIS_galaxy_reports\all_2777');rows=json.loads((base/'MER_VIS_report_manifest.json').read_text());assert len(rows)==2777 and len({r['object_id'] for r in rows})==2777
source_df=pd.read_csv(base.parent.parent/'Euclid_MER_VIS_geometry'/'MER_VIS_local_geometry_manifest.csv',dtype={'object_id':str}).set_index('object_id')
actual=Counter();dims=Counter()
for r in rows:
 source=source_df.loc[r['object_id']];assert math.isclose(r['euclid_adjusted_detection_pa_deg'],(source.euclid_detection_pa_sky_deg+90)%180,abs_tol=1e-8)
 if r['status']=='provisional_fit':assert math.isclose(r['photutils_disc_pa_deg'],source.codex_disc_pa_sky_deg,abs_tol=1e-8) and math.isclose(r['photutils_bar_pa_deg'],source.codex_bar_pa_sky_deg,abs_tol=1e-8) and math.isclose(r['photutils_inclination_deg'],source.codex_inclination_deg,abs_tol=1e-8)
 p=base/r['relative_png'];assert p.exists();qi=bool(r['quality_flags'] or r['status']!='provisional_fit' or r['partial']);assert qi==r['quality_issue'];assert p.stem.endswith('_QI')==qi;assert p.parent.name==('png_QI' if qi else 'png_NoQI');actual['QI' if qi else 'NoQI']+=1;dims[Image.open(p).size]+=1
 if r['status']=='fit_failed':assert r['photutils_disc_pa_deg'] is None and r['delta_disc_pa_deg']=='—'
assert actual=={'QI':2250,'NoQI':527};assert dims=={(2000,1750):2777}
batches=json.loads((base/'MER_VIS_pdf_batches.json').read_text());assert len(batches)==47;pages=0;images=0
for batch in batches:
 pdf=PdfReader(base/batch['pdf']);assert len(pdf.pages)==batch['pages'];pages+=len(pdf.pages)
 for j,page in enumerate(pdf.pages):
  expected=min(6,batch['galaxies']-j*6);objects=page['/Resources']['/XObject'];n=sum(1 for obj in objects.values() if obj.get_object().get('/Subtype')=='/Image');assert n==expected,(batch['pdf'],j,n,expected);images+=n
assert images==2777
index=list(csv.DictReader((base/'MER_VIS_report_review_index.csv').open(encoding='utf8')));assert len(index)==2777;assert len({r['object_id'] for r in index})==2777
run=json.loads((base/'MER_VIS_report_run.json').read_text());unchanged=hashlib.sha256(Path(run['source']).read_bytes()).hexdigest()==run['sha256'];assert unchanged
report={'galaxies':2777,'PNG_QI':2250,'PNG_NoQI':527,'PDF_files':47,'PDF_pages':pages,'PDF_embedded_cards':images,'index_rows':len(index),'all_PNG_dimensions':'2000 x 1750','source_manifest_unchanged':unchanged};(base/'MER_VIS_report_verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

