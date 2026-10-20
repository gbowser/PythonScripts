from pathlib import Path
p=Path('MER_VIS_pipeline_v2/current_report/output')
for name in ['Euclid_MER_VIS_outcomes_summary.pptx','Euclid_MER_VIS_outcomes_summary_delivery.pptx']:
 target=p/name
 assert target.resolve().parent==p.resolve()
 if target.exists():target.unlink()
(p/'Euclid_MER_VIS_outcomes_summary_reviewed.pptx').rename(p/'Euclid_MER_VIS_outcomes_summary.pptx')
# Stale slide previews beyond the 14-slide delivered deck are obsolete.
for i in [15,16,17]:
 target=Path('MER_VIS_pipeline_v2/current_report/renders')/f'slide-{i}.png'
 if target.exists():target.unlink()
print('Removed obsolete working deck copies and stale slide previews')
