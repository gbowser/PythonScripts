from pathlib import Path
import json
p=Path('MER_VIS_pipeline_v2/build_current_MER_VIS_presentation.mjs');s=p.read_text(encoding='utf8').replace('current_report/finalizer-delivery','current_report/finalizer-sampling');p.write_text(s,encoding='utf8')
d=json.loads(Path('MER_VIS_pipeline_v2/current_report/report_data.json').read_text());print('Slides',6+len(d['example_groups']),[(x['title'],[e['id'] for e in x['examples']]) for x in d['example_groups']])
