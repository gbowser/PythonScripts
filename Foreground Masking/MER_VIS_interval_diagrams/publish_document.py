from pathlib import Path
from zipfile import ZipFile
import shutil,json,hashlib
base=Path('MER_VIS_interval_diagrams');source=Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid\reports\MER_VIS_current\Euclid_MER_VIS_disc_PA_and_inclination_explained_clarified.docx');revised=base/'Euclid_MER_VIS_disc_PA_and_inclination_explained_illustrated.docx'
with ZipFile(source) as a,ZipFile(revised) as b:
 media=[n for n in a.namelist() if n.startswith('word/media/')];assert len(media)==7
 assert all(a.read(n)==b.read(n) for n in media)
 assert len([n for n in b.namelist() if n.startswith('word/media/')])==9
shutil.copy2(source,base/'source_before_diagrams.docx')
try:
 shutil.copy2(revised,source);dest=source;locked=False
except PermissionError:
 dest=source.with_name(revised.name);shutil.copy2(revised,dest);locked=True
assert hashlib.sha256(dest.read_bytes()).hexdigest()==hashlib.sha256(revised.read_bytes()).hexdigest()
report=dict(output=str(dest),original_was_locked=locked,rendered_pages=17,illustrated_pages=[3,4,5],original_images_preserved=7,new_figures=2,example=json.loads((base/'measured_example.json').read_text()),sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
(base/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='example'},indent=2))
