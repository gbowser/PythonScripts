from PIL import Image
from pathlib import Path
p=Path('MER_VIS_pipeline_v2/current_report/render_summary_sampling/page-3.png');im=Image.open(p);im.crop((0,1600,im.width,im.height)).save(p.parent/'page3_bottom.png')
