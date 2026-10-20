"""Verify every v2 card and PDF against source values, allowing absent bar PA."""
from pathlib import Path
from collections import Counter
import json,csv,math,hashlib,argparse
from PIL import Image
from pypdf import PdfReader
p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--geometry-dir',type=Path,required=True);a=p.parse_args();base=a.input_dir;rows=json.loads((base/'MER_VIS_report_manifest.json').read_text());source={r['object_id']:r for r in csv.DictReader((a.geometry_dir/'MER_VIS_local_geometry_manifest.csv').open(encoding='utf8'))};assert len(rows)==len(source)==2777 and len({r['object_id'] for r in rows})==2777;counts=Counter()
for r in rows:
 z=source[r['object_id']];assert (base/r['relative_png']).is_file();assert Image.open(base/r['relative_png']).size==(2000,1750)
 for key,col in [('photutils_disc_pa_deg','codex_disc_pa_sky_deg'),('photutils_bar_pa_deg','codex_bar_pa_sky_deg'),('photutils_inclination_deg','codex_inclination_deg')]:
  v=z.get(col,'');assert (r[key] is None and v=='') or (r[key] is not None and v!='' and math.isclose(r[key],float(v),abs_tol=1e-8)),(r['object_id'],key)
 assert r['euclid_adjusted_detection_pa_deg'] is not None and math.isclose(r['euclid_adjusted_detection_pa_deg'],float(z['euclid_adjusted_detection_pa_sky_deg']),abs_tol=1e-7)
 assert r['quality_issue']==bool(r['quality_flags'] or r['status']!='provisional_fit' or r['partial']);assert Path(r['relative_png']).stem.endswith('_QI')==r['quality_issue'];counts['QI' if r['quality_issue'] else 'NoQI']+=1
batches=json.loads((base/'MER_VIS_pdf_batches.json').read_text());pages=0;images=0
for b in batches:
 pdf=PdfReader(base/b['pdf']);assert len(pdf.pages)==b['pages'];pages+=len(pdf.pages)
 for j,page in enumerate(pdf.pages):
  n=sum(o.get_object().get('/Subtype')=='/Image' for o in page['/Resources']['/XObject'].values());assert n==min(6,b['galaxies']-j*6);images+=n
assert images==2777;index=list(csv.DictReader((base/'MER_VIS_report_review_index.csv').open()));assert len(index)==2777
run=json.loads((base/'MER_VIS_report_run.json').read_text());assert hashlib.sha256(Path(run['source']).read_bytes()).hexdigest()==run['sha256']
s=dict(galaxies=2777,groups=dict(counts),PDF_files=len(batches),PDF_pages=pages,PDF_embedded_cards=images,index_rows=len(index),source_manifest_unchanged=True);(base/'MER_VIS_report_verification.json').write_text(json.dumps(s,indent=2));print(json.dumps(s,indent=2))
