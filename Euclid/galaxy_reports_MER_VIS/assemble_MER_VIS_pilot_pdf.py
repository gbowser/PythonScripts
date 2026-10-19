from pathlib import Path
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
base=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\MER_VIS_galaxy_reports\pilot_10');rows=json.loads((base/'MER_VIS_report_sample_data.json').read_text());out=Path('MER_VIS_report_work/pilot_png_qa');out.mkdir(exist_ok=True,parents=True)
pdf=out/'MER_VIS_pilot_10_six_per_page.pdf';c=canvas.Canvas(str(pdf),pagesize=A4);c.setTitle('Euclid MER VIS pilot galaxy geometry reports');width,height=A4
margin=12;gap=8;card_w=(width-2*margin-gap)/2;card_h=card_w*7/8;top=height-34
for start in range(0,len(rows),6):
 c.setFont('Helvetica-Bold',10);c.drawString(margin,height-17,'Euclid MER VIS galaxy geometry reports');c.setFont('Helvetica',8);c.drawRightString(width-margin,height-17,f'Pilot sample  {start//6+1} / 2')
 for j,r in enumerate(rows[start:start+6]):
  x=margin+(j%2)*(card_w+gap);y=top-(j//2)*(card_h+gap)-card_h;c.drawImage(ImageReader(str(base/r['png'])),x,y,width=card_w,height=card_h,mask='auto');c.setStrokeColorRGB(.83,.86,.88);c.setLineWidth(.35);c.rect(x,y,card_w,card_h,stroke=1,fill=0)
 c.setFont('Helvetica',7);c.drawString(margin,12,'19 October 2026  |  Existing fits  |  Euclid PA includes adopted +90 degree adjustment');c.showPage()
c.save();print(pdf.resolve())
