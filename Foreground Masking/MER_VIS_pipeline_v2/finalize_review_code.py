from pathlib import Path
p=Path('MER_VIS_pipeline_v2/review_code/make_MER_VIS_galaxy_report_cards.py');s=p.read_text(encoding='utf8').replace('def make_card(r,profiles,out,ordinal):','def _render_card(r,profiles,out,ordinal):')
wrapper='''def make_card(r,profiles,out,ordinal):
 result=_render_card(r,profiles,out,ordinal)
 for key in ['catalogue_name','catalogue_match_status','catalogue_match_source','catalogue_match_separation_arcsec','catalogue_match_url']:
  value=r.get(key,'');result[key]='' if str(value)=='nan' else value
 return result

'''
s=s.replace('def main():',wrapper+'def main():');p.write_text(s,encoding='utf8')
p=Path('MER_VIS_pipeline_v2/review_code/generate_all_MER_VIS_galaxy_reports.py');s=p.read_text(encoding='utf8').replace('QI_adaptive_v2','QI_sampling_review_2026-10-20');p.write_text(s,encoding='utf8')
