from pathlib import Path
p=Path('MER_VIS_pipeline_v2/review_code/make_MER_VIS_galaxy_report_cards.py');s=p.read_text(encoding='utf8').replace("fig.text(.045,.848,f'Catalogue:","fig.text(.045,.855,f'Catalogue:").replace("arcsec)',fontsize=10.2,color='#20577c')","arcsec)',fontsize=8.5,color='#20577c')");p.write_text(s,encoding='utf8')
