from pathlib import Path
p=Path('MER_VIS_pipeline_v2/prepare_current_MER_VIS_report_data.py');s=p.read_text(encoding='utf-8-sig');s=s.replace("result=dict(summary=summary", "availability={key:sum(flags(r)==[key] and str(r['cutout_partial']).lower()!='true' for r in fits) for key in summary['flags']}\nsummary['isolated_example_availability']=availability\nresult=dict(summary=summary")
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_pipeline_v2/build_current_MER_VIS_presentation.mjs');s=p.read_text(encoding='utf-8-sig');s=s.replace('Next slides use current examples. Old fixed-centre images and failure examples are superseded.', 'Next slides use current examples. Recovery warnings may co-occur; isolated examples are shown only where available.')
s=s.replace("s=slide('Updated review collection',6);", "s=slide('Updated review collection',6);")
s=s.replace("const fmt=x=>", "s.speakerNotes.text+=' Isolated example counts (full coverage): '+JSON.stringify(q.isolated_example_availability)+'. Flags without two isolated cases are not represented as single-flag examples. Original unstable-bar-PA examples are obsolete because current bar acceptance requires a stable plateau.';\nconst fmt=x=>")
p.write_text(s,encoding='utf8')
