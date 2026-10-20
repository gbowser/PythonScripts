from pathlib import Path
p=Path('MER_VIS_pipeline_v2/review_code/make_MER_VIS_galaxy_report_cards.py');s=p.read_text(encoding='utf8');s=s.replace('if len(g):maxa=float(g.sma_arcsec.max())','if len(g) and not failed:maxa=float(g.sma_arcsec.max())').replace('elif len(pr):maxa=float(pr.sma_arcsec.max())','elif len(pr) and not failed:maxa=float(pr.sma_arcsec.max())');p.write_text(s,encoding='utf8')
