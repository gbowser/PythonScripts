from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
root=Path('MER_VIS_pipeline_v2/current_report');qa=root/'qa';qa.mkdir(exist_ok=True)
for folder,prefix,cols,rows in [('render_summary','summary',2,1),('render_explained','explained',2,1),('renders','slides',2,2)]:
 files=sorted((root/folder).glob('*.png'),key=lambda p:int(p.stem.split('-')[-1]));n=cols*rows
 for start in range(0,len(files),n):
  imgs=[Image.open(p).convert('RGB') for p in files[start:start+n]];w=max(im.width for im in imgs);h=max(im.height for im in imgs);canvas=Image.new('RGB',(w*cols,h*rows),'#ddd')
  for j,im in enumerate(imgs):canvas.paste(im,((j%cols)*w,(j//cols)*h))
  canvas.save(qa/f'{prefix}_{start//n+1}.png')
print([p.name for p in qa.glob('*.png')])
