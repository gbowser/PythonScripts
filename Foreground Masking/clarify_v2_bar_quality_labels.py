from pathlib import Path
p=Path('MER_VIS_pipeline_v2/report_code/make_MER_VIS_galaxy_report_cards.py');s=p.read_text(encoding='utf-8-sig').replace("'weak_ellipse_bar_signature':'Weak ellipse bar signature'", "'weak_ellipse_bar_signature':'Accepted class-B bar signature'");p.write_text(s,encoding='utf8')
p=Path('MER_VIS_pipeline_v2/build_current_MER_VIS_documents.py');s=p.read_text(encoding='utf-8-sig');s=s.replace('A weaker accepted bar is labelled B and receives a quality flag.', 'A weaker accepted bar is labelled B and receives a quality flag. The old unstable-bar-PA category is not carried forward as an accepted bar: unstable plateaus are rejected by the new bar test.')
p.write_text(s,encoding='utf8')
