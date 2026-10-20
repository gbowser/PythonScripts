from pathlib import Path
fixes={'\u00c2\u00b0':'°','\u00e2\u20ac\u201c':'–','\u00e2\u20ac\u201d':'—','\u00e2\u02c6\u2019':'−','\u00ce\u201d':'Δ','\u00c3\u00a9':'é','\u00e2\u201a\u20ac':'₀','\u00e2\u2030\u00a5':'≥','\u00e2\u2030\u00a4':'≤','\u00e2\u20ac\u00a6':'…','\u00e2\u2020\u2019':'→'}
for p in [Path('MER_VIS_pipeline_v2/review_code/make_MER_VIS_galaxy_report_cards.py'),Path('MER_VIS_pipeline_v2/build_current_MER_VIS_presentation.mjs')]:
 s=p.read_text(encoding='utf8')
 for a,b in fixes.items():s=s.replace(a,b)
 p.write_text(s,encoding='utf8')
 print(p,[(hex(ord(c)),s.count(c)) for c in ['Â','Ã','â','Î'] if c in s])
