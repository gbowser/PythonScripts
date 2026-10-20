from pathlib import Path
p=Path('MER_VIS_pipeline_v2/prepare_current_MER_VIS_report_data.py');s=p.read_text(encoding='utf-8-sig');s=s.replace("summary['paired_supplied_comparison']=paired", "summary['paired_supplied_comparison']=paired\nsummary['original_face_on_count']=sum('nearly_face_on_PA_uncertain' in r.get('codex_quality_flags','') for r in old.values())")
p.write_text(s,encoding='utf8')
p=Path('MER_VIS_pipeline_v2/build_current_MER_VIS_documents.py');s=p.read_text(encoding='utf-8-sig');needle="Their bars may still be useful for analysis.\")";s=s.replace(needle,"Their bars may still be useful for analysis. The original run had {s['original_face_on_count']} such markers; the current number changes because disc axis ratios have been remeasured with different radial selections.\")")
p.write_text(s,encoding='utf8')
