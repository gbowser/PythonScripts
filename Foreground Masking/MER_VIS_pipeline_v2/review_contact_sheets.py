from pathlib import Path
from PIL import Image,ImageDraw
root=Path('MER_VIS_pipeline_v2/current_report')
for folder in [root/'render_summary_sampling',root/'render_explained_sampling',root/'renders']:
 pages=list(folder.glob('page-*.png' if 'render_' in folder.name else 'slide-*.png'));pages.sort(key=lambda p:int(p.stem.split('-')[-1]));sheet=Image.new('RGB',(1200,340*((len(pages)+3)//4)),'#ccc')
 for i,p in enumerate(pages):
  im=Image.open(p);im.thumbnail((295,310));sheet.paste(im,((i%4)*300,(i//4)*340));ImageDraw.Draw(sheet).text(((i%4)*300,(i//4)*340+310),p.stem,fill='black')
 sheet.save(folder/'sampling_contact.png');print(folder,len(pages))
