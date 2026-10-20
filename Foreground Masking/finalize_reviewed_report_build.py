from pathlib import Path
p=Path('MER_VIS_pipeline_v2/build_current_MER_VIS_presentation.mjs');s=p.read_text(encoding='utf-8-sig').replace("'current_report/finalizer-polished'","'current_report/finalizer-delivery'").replace("'current_report/output/Euclid_MER_VIS_outcomes_summary_polished.pptx'","'current_report/output/Euclid_MER_VIS_outcomes_summary_delivery.pptx'");p.write_text(s,encoding='utf8')
