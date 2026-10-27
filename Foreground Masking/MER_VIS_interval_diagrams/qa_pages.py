from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
from pypdf import PdfReader
folder=Path('MER_VIS_interval_diagrams/render')
pages=sorted(folder.glob('page-*.png'),key=lambda p:int(p.stem.split('-')[-1]))
for start in range(0,len(pages),6):
    sheet=Image.new('RGB',(1200,1680),'#aaaaaa');draw=ImageDraw.Draw(sheet)
    for n,p in enumerate(pages[start:start+6]):
        im=Image.open(p);im.thumbnail((580,520));x=(n%2)*600+(600-im.width)//2;y=(n//2)*560+25
        sheet.paste(im,(x,y));draw.text((x,y-20),p.stem,fill='black')
    sheet.save(folder/f'contact_{start//6+1}.png')
print('Pages',len(pages))
for path in folder.glob('*.pdf'):
    pdf=PdfReader(path).pages
    for i,page in enumerate(pdf):
        text=page.extract_text(); print(i+1,len(text),text[:95].replace('\n',' | '))


