import json
from pathlib import Path
s=json.loads(Path('MER_VIS_pipeline_v2/current_report/comparison/summary.json').read_text())
print('Current vs supplied:',s['statistics']['common'])
