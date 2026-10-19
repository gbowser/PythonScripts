from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
ids=['-619395065457031576','-522170446265172635','-649721665463331687','2712797183679302869','2694350108673052592','2700333019674601903','2760587364650641854','-642703864460081959']
p=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry\profiles')
canvas=Image.new('RGB',(1600,1800),'white')
for j,i in enumerate(ids):
 im=Image.open(p/f'Euclid_{i}_MER_VIS_geometry_review.png'); im.thumbnail((800,440));canvas.paste(im,((j%2)*800,(j//2)*450))
canvas.save('MER_VIS_report_work/candidates.png')
