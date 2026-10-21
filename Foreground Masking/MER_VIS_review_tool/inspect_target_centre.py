from pathlib import Path
import csv,json,numpy as np
from astropy.io import fits
from PIL import Image,ImageDraw
root=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid')
rows=list(csv.DictReader((root/'Euclid_MER_VIS_geometry/MER_VIS_local_geometry_manifest.csv').open(encoding='utf-8-sig')))
r=next(r for r in rows if r['object_id']=='-586374330510251740')
with fits.open(r['fits_path']) as hd:
 data=hd[0].data;h=hd[0].header;print('shape',data.shape,'catalogue',h['CENX']-1,h['CENY']-1)
 cx=int(h['CENX']-1);cy=int(h['CENY']-1);x0=cx-160;y0=cy-160;cut=np.array(data[y0:cy+160,x0:cx+160],float)
finite=cut[np.isfinite(cut)];lo,hi=np.percentile(finite,[10,99.8]);v=np.arcsinh(8*np.clip((cut-lo)/(hi-lo),0,1))/np.arcsinh(8)
im=Image.fromarray(np.uint8(255*np.flipud(v))).convert('RGB').resize((800,800));d=ImageDraw.Draw(im)
for x in range((x0//20+1)*20,x0+320,20):
 px=(x-x0)*2.5;d.line((px,0,px,800),fill='#666622',width=1);d.text((px+2,5),str(x),fill='yellow')
for y in range((y0//20+1)*20,y0+320,20):
 py=(y0+320-y)*2.5;d.line((0,py,800,py),fill='#666622',width=1);d.text((5,py+2),str(y),fill='yellow')
im.save('MER_VIS_review_tool/centre_test_target.png')
