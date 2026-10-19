from pathlib import Path
from astropy.io import fits
p=Path(r'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\MER_VIS_PA_validation');cat=next(p.glob('*FINAL-CAT*'))
with fits.open(cat) as h:
 print(h.info(output=False));d=h[1].data;print([n for n in d.names if any(x in n for x in ['ANGLE','ELLIP','AXIS','CENTROID','SOURCE','VIS_DET'])]);r=d[d['OBJECT_ID']==-619395065457031576];print('ROWS',len(r));print({n:r[n].tolist() for n in d.names if any(x in n for x in ['ANGLE','ELLIP','AXIS','VIS_DET'])});print([n for n in d.names if n.startswith('X') or n.startswith('Y')])
