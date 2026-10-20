from pathlib import Path
import csv,json,hashlib,ast
base=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid');out=base/'MER_VIS_galaxy_reports/all_2777';manifest=base/'Euclid_MER_VIS_geometry/MER_VIS_local_geometry_manifest.csv';rows={r['object_id']:r for r in csv.DictReader(manifest.open(encoding='utf8'))};cards=json.loads((out/'MER_VIS_report_manifest.json').read_text());assert len(cards)==len(rows)==2777
for card in cards:
 row=rows[card['object_id']];assert set(card['quality_flags'])==set(filter(None,row['codex_quality_flags'].split(';')));assert card.get('catalogue_name','')==row['catalogue_name']
assert len(list(out.rglob('*.png')))==2777 and len(list(out.rglob('*.pdf')))==47
assert not list(out.rglob('*.partial*'))
project=Path(r'C:\Users\gordo\Documents\Github\PythonScripts\Euclid');published=project/'reports/MER_VIS_current';stage=Path('MER_VIS_pipeline_v2/current_report/output')
for name in ['Euclid_MER_VIS_outcomes_summary.docx','Euclid_MER_VIS_disc_PA_and_inclination_explained.docx','Euclid_MER_VIS_outcomes_summary.pptx']:
 assert hashlib.sha256((published/name).read_bytes()).digest()==hashlib.sha256((stage/name).read_bytes()).digest()
assert len(list(published.glob('*.docx')))==2 and len(list(published.glob('*.pptx')))==1
for name in ['fit_adaptive_MER_VIS_geometry.py','make_MER_VIS_galaxy_report_cards.py','generate_all_MER_VIS_galaxy_reports.py','assemble_parallel_MER_VIS_reports.py']:ast.parse((project/'adaptive_MER_VIS'/name).read_text(encoding='utf-8-sig'))
print('Final values, flags, catalogue names, file counts, document hashes and syntax verified. No obsolete published copies remain.')
