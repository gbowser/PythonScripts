from pathlib import Path
import json
from PIL import Image,ImageDraw
base=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\MER_VIS_galaxy_reports\all_2777_sampling_review');rows=json.loads((base/'MER_VIS_report_manifest.json').read_text());ids=['-518633776290631360','-601121275504424227','-586374330510251740','-524824554283124036'];sheet=Image.new('RGB',(1600,1400),'white')
for i,oid in enumerate(ids):
 r=next(r for r in rows if r['object_id']==oid);im=Image.open(base/r['relative_png']);im.thumbnail((800,700));sheet.paste(im,((i%2)*800,(i//2)*700))
sheet.save('MER_VIS_pipeline_v2/sampling_card_examples.png')
