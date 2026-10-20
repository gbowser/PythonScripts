from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
for folder in Path('MER_VIS_pipeline_v2/bar_class_update').glob('render_*'):
 pages=list(folder.glob('page-*.png'));pages.sort(key=lambda p:int(p.stem.split('-')[-1]))
 sheet=Image.new('RGB',(1000,330*((len(pages)+3)//4)),'#cccccc')
 for i,p in enumerate(pages):
  im=Image.open(p);im.thumbnail((245,305));sheet.paste(im,((i%4)*250,(i//4)*330));ImageDraw.Draw(sheet).text(((i%4)*250,(i//4)*330+306),p.stem,fill='black')
 sheet.save(folder/'contact.png');print(folder,len(pages))
