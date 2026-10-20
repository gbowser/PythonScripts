"""Assemble six-per-page MER VIS reports in separate QI and NoQI PDF batches."""
from pathlib import Path
import argparse,csv,json,math,gc,time,shutil
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input-dir',type=Path,default=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\MER_VIS_galaxy_reports\all_2777'));p.add_argument('--only-batches',nargs='*');p.add_argument('--batch-size',type=int,default=60);a=p.parse_args();base=a.input_dir
 if a.batch_size<=0 or a.batch_size%6:raise ValueError('Batch size must be a positive multiple of six')
 records=json.loads((base/'MER_VIS_report_manifest.json').read_text(encoding='utf8'));errors=json.loads((base/'MER_VIS_report_errors.json').read_text());assert not errors
 width,height=A4;margin=12;gap=8;card_w=(width-2*margin-gap)/2;card_h=card_w*7/8;top=height-34;index=[];batches=[]
 for qi,label in [(True,'QI'),(False,'NoQI')]:
  group=[r for r in records if r['quality_issue']==qi]
  # Keep the catalogue order within each distinct review group.
  for start in range(0,len(group),a.batch_size):
   selected=group[start:start+a.batch_size];batch_no=start//a.batch_size+1;name=f'MER_VIS_galaxy_reports_{batch_no:03d}_{label}.pdf';path=base/f'pdf_{label}'/name;temp=path.with_suffix('.partial.pdf');pages=math.ceil(len(selected)/6)
   if a.only_batches and name not in a.only_batches:
    if not path.is_file():raise FileNotFoundError(path)
    for j,r in enumerate(selected):index.append(dict(object_id=r['object_id'],quality_issue=qi,fit_status=r['status'],quality_flags=';'.join(r['quality_flags']),partial_coverage=r['partial'],png=r['relative_png'],pdf=str(path.relative_to(base)),pdf_page=j//6+1,position_on_page=j%6+1))
    batches.append(dict(group=label,pdf=str(path.relative_to(base)),galaxies=len(selected),pages=pages))
    continue
   c=canvas.Canvas(str(temp),pagesize=A4);c.setTitle(f'Euclid MER VIS galaxy geometry reports {label} batch {batch_no}');c.setAuthor('')
   for page_start in range(0,len(selected),6):
    page=page_start//6+1;c.setFont('Helvetica-Bold',10);c.drawString(margin,height-17,'Euclid MER VIS galaxy geometry reports');c.setFont('Helvetica',8);c.drawRightString(width-margin,height-17,f'{label}  Batch {batch_no:03d}  Page {page}/{pages}')
    for j,r in enumerate(selected[page_start:page_start+6]):
     x=margin+(j%2)*(card_w+gap);y=top-(j//2)*(card_h+gap)-card_h
     c.drawImage(ImageReader(str(base/r['relative_png'])),x,y,width=card_w,height=card_h,mask='auto');c.setStrokeColorRGB(.83,.86,.88);c.setLineWidth(.35);c.rect(x,y,card_w,card_h,stroke=1,fill=0)
     index.append(dict(object_id=r['object_id'],quality_issue=qi,fit_status=r['status'],quality_flags=';'.join(r['quality_flags']),partial_coverage=r['partial'],png=r['relative_png'],pdf=str(path.relative_to(base)),pdf_page=page,position_on_page=j+1))
    c.setFont('Helvetica',7);footer='QI: flags, failed fit or partial coverage' if qi else 'NoQI: no automatic issue; physical review still required';c.drawString(margin,12,footer+' | Euclid PA includes adopted +90 degree adjustment');c.showPage()
   c.save()
   for retry in range(9):
    try:temp.replace(path);break
    except PermissionError:
     if retry>=2:
      # Cloud sync can deny delete/rename while still allowing ordinary writes.
      # The verified staging collection is not promoted until every PDF reopens.
      try:
       shutil.copyfile(temp,path)
       try:temp.unlink()
       except PermissionError:pass
       break
      except PermissionError:pass
     if retry==8:raise
     time.sleep(min(.5*2**retry,8))
   batches.append(dict(group=label,pdf=str(path.relative_to(base)),galaxies=len(selected),pages=pages));print('Saved',name,len(selected),'galaxies',pages,'pages',flush=True);gc.collect()
 with (base/'MER_VIS_report_review_index.csv').open('w',newline='',encoding='utf8') as f:
  w=csv.DictWriter(f,fieldnames=list(index[0]));w.writeheader();w.writerows(index)
 (base/'MER_VIS_pdf_batches.json').write_text(json.dumps(batches,indent=2),encoding='utf8');print('COMPLETE',len(batches),'PDF files;',len(index),'galaxies',flush=True)
if __name__=='__main__':main()
