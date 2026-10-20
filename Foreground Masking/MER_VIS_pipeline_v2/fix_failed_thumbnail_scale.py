from pathlib import Path
p=Path('MER_VIS_pipeline_v2/review_code/make_MER_VIS_galaxy_report_cards.py');s=p.read_text();s=s.replace("segpath=Path(__file__).resolve().parent.parent/'datalabs_MER_VIS'/'MER_VIS_datalabs_manifest.csv'", "segpath=Path(__file__).resolve().parent.parent/'datalabs_MER_VIS'/'MER_VIS_datalabs_manifest.csv'\n  if not segpath.is_file():segpath=Path(r'C:\\Users\\gordo\\Documents\\Github\\PythonScripts\\Euclid\\datalabs_MER_VIS\\MER_VIS_datalabs_manifest.csv')")
p.write_text(s,encoding='utf8')
