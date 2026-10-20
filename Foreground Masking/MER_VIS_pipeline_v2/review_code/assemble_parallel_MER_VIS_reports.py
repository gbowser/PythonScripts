"""Build independent MER VIS PDF batches in parallel, then write one complete index."""
from pathlib import Path
import argparse,csv,json,math,time,shutil
from concurrent.futures import ProcessPoolExecutor,as_completed
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

def render_batch(job):
 root,label,number,records=job;root=Path(root);path=root/f'pdf_{label}'/f'MER_VIS_galaxy_reports_{number:03d}_{label}.pdf';temp=path.with_suffix('.partial.pdf');width,height=A4;margin=12;gap=8;cw=(width-2*margin-gap)/2;ch=cw*7/8;top=height-34;pages=math.ceil(len(records)/6)
 c=canvas.Canvas(str(temp),pagesize=A4);c.setTitle(f'Euclid MER VIS galaxy geometry reports {label} batch {number}')
 for start in range(0,len(records),6):
  page=start//6+1;c.setFont('Helvetica-Bold',10);c.drawString(margin,height-17,'Euclid MER VIS galaxy geometry reports');c.setFont('Helvetica',8);c.drawRightString(width-margin,height-17,f'{label}  Batch {number:03d}  Page {page}/{pages}')
  for j,r in enumerate(records[start:start+6]):
   x=margin+(j%2)*(cw+gap);y=top-(j//2)*(ch+gap)-ch;c.drawImage(ImageReader(str(root/r['relative_png'])),x,y,width=cw,height=ch,mask='auto');c.setStrokeColorRGB(.83,.86,.88);c.setLineWidth(.35);c.rect(x,y,cw,ch,stroke=1,fill=0)
  c.setFont('Helvetica',7);footer='QI: flags, failed fit or partial coverage' if label=='QI' else 'NoQI: no automatic issue; physical review still required';c.drawString(margin,12,footer+' | Euclid PA includes adopted +90 degree adjustment');c.showPage()
 c.save()
 for retry in range(10):
  try:temp.replace(path);break
  except PermissionError:
   try:shutil.copyfile(temp,path);temp.unlink();break
   except PermissionError:
    if retry==9:raise
    time.sleep(1)
 return dict(group=label,pdf=str(path.relative_to(root)),galaxies=len(records),pages=pages)

def main():
 p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--workers',type=int,default=4);a=p.parse_args();root=a.input_dir;records=json.loads((root/'MER_VIS_report_manifest.json').read_text());jobs=[];index=[]
 for qi,label in [(True,'QI'),(False,'NoQI')]:
  group=[r for r in records if r['quality_issue']==qi]
  for start in range(0,len(group),60):
   batch=group[start:start+60];number=start//60+1;jobs.append((str(root),label,number,batch));name=f'pdf_{label}/MER_VIS_galaxy_reports_{number:03d}_{label}.pdf'
   for j,r in enumerate(batch):index.append(dict(object_id=r['object_id'],quality_issue=qi,fit_status=r['status'],quality_flags=';'.join(r['quality_flags']),partial_coverage=r['partial'],catalogue_name=r.get('catalogue_name',''),png=r['relative_png'],pdf=name,pdf_page=j//6+1,position_on_page=j%6+1))
 result=[]
 with ProcessPoolExecutor(max_workers=a.workers) as pool:
  for f in as_completed([pool.submit(render_batch,j) for j in jobs]):
   b=f.result();result.append(b);print(len(result),'/',len(jobs),b['pdf'],flush=True)
 result.sort(key=lambda b:(b['group']!='QI',b['pdf']))
 with (root/'MER_VIS_report_review_index.csv').open('w',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(index[0]));w.writeheader();w.writerows(index)
 (root/'MER_VIS_pdf_batches.json').write_text(json.dumps(result,indent=2),encoding='utf8');print('COMPLETE',len(result),'PDFs',len(index),'galaxies',flush=True)
if __name__=='__main__':main()
